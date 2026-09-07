"""fleet/fleet.py — Fleet manager: owns all player ships and coordinates orders."""
from __future__ import annotations
import random
import json
import os
from entities.ship   import Ship
from entities.crew   import Crew
from fleet.orders    import Order, MissionDef, PatrolSimulator
from fleet.scrapper  import ScrapperManager
from settings        import MAX_FLEET_SLOTS_BASE, DATA_DIR
from core.events     import bus


# ── Static mission pool ───────────────────────────────────────────────────────
MISSION_POOL = [
    {"id": "m_patrol",     "title": "Patrol Run",          "duration": 120, "difficulty": 1, "rewards": {"credits": 300,  "metal": 20,  "xp_bonus": 30}},
    {"id": "m_trade_run",  "title": "Trade Run",           "duration": 180, "difficulty": 1, "rewards": {"credits": 600,  "metal": 5,   "xp_bonus": 20}},
    {"id": "m_rescue",     "title": "Rescue Mission",      "duration": 240, "difficulty": 3, "rewards": {"credits": 1000, "metal": 30,  "xp_bonus": 60}},
    {"id": "m_bounty",     "title": "Bounty Contract",     "duration": 300, "difficulty": 4, "rewards": {"credits": 2000, "metal": 50,  "xp_bonus": 100}},
    {"id": "m_deep_recon", "title": "Deep Sector Recon",   "duration": 360, "difficulty": 5, "rewards": {"credits": 3000, "metal": 100, "xp_bonus": 150}},
]


class Fleet:
    def __init__(self, home_base=None, meta_prog=None):
        self.ships:          list[Ship]    = []
        self.active_ship:    Ship | None   = None
        self.fleet_admiral:  Crew | None   = None
        self.home_base                     = home_base
        self.meta_prog                     = meta_prog

        # Mercenaries: temporary ships (removed after sector/mission)
        self.mercenaries:    list[Ship]    = []

        # Captured enemy ships (via boarding)
        self.captured_ships: list[Ship]    = []

        # Active timed missions
        self.active_missions: list[MissionDef] = []

        # Available missions on the board
        self.mission_board: list[MissionDef] = self._generate_missions()

        # Crew available to hire after successful missions (post-mission hire pool)
        self.hire_pool: list[dict] = []

        self.patrol_sim   = PatrolSimulator()
        self.scrapper_mgr = ScrapperManager(home_base)

        # Max fleet slots (base + meta upgrades)
        self._base_slots  = MAX_FLEET_SLOTS_BASE

    # ── Slots ─────────────────────────────────────────────────────────────────
    @property
    def max_slots(self) -> int:
        meta_bonus = 0
        if self.meta_prog:
            meta_bonus = self.meta_prog.get_upgrade_value("fleet_slots", 0)
        return self._base_slots + meta_bonus

    # ── Ship management ───────────────────────────────────────────────────────
    def add_ship(self, ship: Ship) -> bool:
        if len(self.ships) >= self.max_slots:
            return False
        self.ships.append(ship)
        if self.active_ship is None:
            self.active_ship = ship
        return True

    def remove_ship(self, ship: Ship) -> None:
        if ship in self.ships:
            self.ships.remove(ship)
        if self.active_ship is ship:
            self.active_ship = self.ships[0] if self.ships else None

    def set_active(self, ship: Ship) -> bool:
        if ship in self.ships:
            self.active_ship = ship
            return True
        return False

    # ── Orders ────────────────────────────────────────────────────────────────
    def set_order(self, ship: Ship, order: str) -> bool:
        if order not in Order.ALL:
            return False
        ship.fleet_order = order
        return True

    # ── Fleet Admiral ─────────────────────────────────────────────────────────
    def set_fleet_admiral(self, crew: Crew) -> None:
        self.fleet_admiral = crew

    def admiral_bonus(self) -> float:
        if not self.fleet_admiral:
            return 0.0
        return self.fleet_admiral.stats.get("piloting", 0) * 0.01

    # ── Mission board ─────────────────────────────────────────────────────────
    def _generate_missions(self) -> list[MissionDef]:
        return [
            MissionDef(m["id"], m["title"], m["duration"],
                       m["difficulty"], m["rewards"])
            for m in MISSION_POOL
        ]

    def refresh_missions(self) -> None:
        self.mission_board = self._generate_missions()

    def assign_mission(self, mission_idx: int, ship: Ship) -> dict:
        if mission_idx >= len(self.mission_board):
            return {"ok": False, "reason": "Invalid mission"}
        if ship not in self.ships:
            return {"ok": False, "reason": "Ship not in fleet"}
        mission = self.mission_board.pop(mission_idx)
        mission.assigned_ship = ship
        ship.fleet_order      = Order.MISSION
        self.active_missions.append(mission)
        return {"ok": True, "mission": mission.title}

    # ── Update ────────────────────────────────────────────────────────────────
    def update(self, dt: float) -> list[dict]:
        events: list[dict] = []
        admiral_bonus = self.admiral_bonus()

        # Carrier healing: carriers on FOLLOW order heal all fleet ships by 2 HP/sec
        carrier_ships = [s for s in self.ships
                         if getattr(s, "ship_class", "") == "carrier"
                         and s.fleet_order == Order.FOLLOW
                         and s is not self.active_ship]
        if carrier_ships:
            for ship in self.ships:
                if not ship.is_destroyed:
                    ship.hull = min(ship.max_hull, ship.hull + 2.0 * dt * len(carrier_ships))

        for ship in self.ships:
            if ship is self.active_ship:
                continue

            # WANDER is an alias for PATROL_COLLECT
            if ship.fleet_order in (Order.PATROL_COLLECT, Order.WANDER):
                patrol_events = self.patrol_sim.tick(dt, ship, admiral_bonus)
                for ev in patrol_events:
                    if ev["type"] == "resource_found" and self.home_base:
                        self.home_base.add_resource(ev["resource"], ev["amount"])
                events.extend(patrol_events)

        # Active missions
        for mission in list(self.active_missions):
            mission.elapsed += dt
            if mission.elapsed >= mission.duration:
                result = self._resolve_mission(mission)
                events.append(result)
                self.active_missions.remove(mission)
                if mission.assigned_ship:
                    mission.assigned_ship.fleet_order = Order.STANDBY

        # Scrapper
        recovery_events = self.scrapper_mgr.update(dt)
        events.extend(recovery_events)

        return events

    def _resolve_mission(self, mission: MissionDef) -> dict:
        import random
        success = random.random() < mission.success_chance()
        if success:
            r = mission.rewards
            if self.home_base:
                self.home_base.add_resource("credits", r.get("credits", 0))
                self.home_base.add_resource("metal",   r.get("metal",   0))
            # XP to assigned ship's crew
            if mission.assigned_ship:
                for c in mission.assigned_ship.crew:
                    c.add_xp(r.get("xp_bonus", 20))
            # Post-mission: add 1-2 crew to hire pool
            self._add_post_mission_crew(random.randint(1, 2))
            bus.publish("notification",
                        msg=f"✓ Mission '{mission.title}' succeeded!",
                        color=(60, 200, 80))
            return {"type": "mission_complete", "mission": mission, "success": True}
        else:
            # Partial damage on failure
            if mission.assigned_ship:
                mission.assigned_ship.take_damage(
                    random.randint(10, 40) * mission.difficulty
                )
                bus.publish("notification",
                            msg=f"✗ Mission '{mission.title}' failed. Ship damaged.",
                            color=(220, 60, 60))
            return {"type": "mission_complete", "mission": mission, "success": False}

    def _add_post_mission_crew(self, count: int = 1) -> None:
        """Add random crew from data/crew.json to the hire pool."""
        try:
            with open(os.path.join(DATA_DIR, "crew.json")) as f:
                crew_data = json.load(f)
            for _ in range(count):
                entry = random.choice(crew_data)
                self.hire_pool.append(dict(entry))
            # Cap pool at 6 entries
            if len(self.hire_pool) > 6:
                self.hire_pool = self.hire_pool[-6:]
        except Exception:
            pass

    # ── Wreck registration ────────────────────────────────────────────────────
    def register_destroyed_ship(self, ship: Ship, sector_id: str) -> None:
        if ship in self.ships and ship is not self.active_ship:
            self.scrapper_mgr.register_wreck(ship, sector_id)
            self.remove_ship(ship)

    # ── Mercenaries ───────────────────────────────────────────────────────────
    def hire_mercenary(self, ship: Ship, cost: int) -> bool:
        if self.home_base and not self.home_base.spend_resource("credits", cost):
            return False
        ship.fleet_order = Order.FOLLOW
        self.mercenaries.append(ship)
        return True

    def dismiss_mercenaries(self) -> None:
        self.mercenaries.clear()

    # ── All combat ships (player + followers + mercs) ─────────────────────────
    def combat_wing(self) -> list[Ship]:
        followers = [s for s in self.ships
                     if s.fleet_order == Order.FOLLOW and s is not self.active_ship]
        return ([self.active_ship] if self.active_ship else []) + \
               followers + list(self.mercenaries)

    # ── Serialization ─────────────────────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "active_ship_id":    self.active_ship.id if self.active_ship else None,
            "fleet_admiral_id":  self.fleet_admiral.id if self.fleet_admiral else None,
            "ships":             [s.to_dict() for s in self.ships],
            "active_missions":   [m.to_dict() for m in self.active_missions],
        }

    def load_from_dict(self, data: dict) -> None:
        """Restore fleet state from a saved dict (called during game load)."""
        import json
        import os
        from settings import DATA_DIR
        try:
            with open(os.path.join(DATA_DIR, "ships.json")) as f:
                ship_templates: list[dict] = json.load(f)
        except Exception:
            ship_templates = []
        tpl_map = {t["id"]: t for t in ship_templates}

        self.ships.clear()
        self.captured_ships.clear()
        active_id = data.get("active_ship_id")
        for sdata in data.get("ships", []):
            sid = sdata.get("id", "")
            tpl = tpl_map.get(sid, {})
            merged = {**tpl, **{k: v for k, v in sdata.items() if v is not None}}
            ship = Ship(merged)
            # Restore custom name, hull, shield
            ship.custom_name = sdata.get("custom_name", ship.name)
            ship.hull        = float(sdata.get("hull",  ship.max_hull))
            ship.shield      = float(sdata.get("shield", ship.max_shield))
            self.ships.append(ship)
            if sid == active_id:
                self.active_ship = ship
        if not self.active_ship and self.ships:
            self.active_ship = self.ships[0]
