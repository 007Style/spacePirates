"""combat/boarding.py — Turn-based room-by-room boarding combat."""
from __future__ import annotations
import random
from entities.ship import Ship
from entities.crew import Crew


class BoardingRoom:
    def __init__(self, name: str, defenders: list[Crew]):
        self.name       = name
        self.defenders  = list(defenders)
        self.cleared    = False
        self.hp: dict[str, float] = {c.id: float(c.stats.get("combat", 10) * 5)
                                      for c in defenders}

    @property
    def is_cleared(self) -> bool:
        return all(self.hp.get(c.id, 0) <= 0 for c in self.defenders)


class BoardingAction:
    ATTACK   = "attack"
    ABILITY  = "ability"
    RETREAT  = "retreat"
    HOSTAGE  = "take_hostage"


class BoardingResult:
    ONGOING   = "ongoing"
    CAPTURED  = "captured"
    RETREATED = "retreated"
    REPELLED  = "repelled"


class BoardingCombat:
    """Turn-based boarding combat.

    Usage:
        bc = BoardingCombat(attacker_ship, defender_ship)
        bc.start_boarding([crew1, crew2])        # choose troops
        while bc.result == BoardingResult.ONGOING:
            action = bc.get_available_actions()  # show to player
            bc.take_action(BoardingAction.ATTACK, ...)
        outcome = bc.result  # captured / retreated / repelled
    """

    def __init__(self, attacker_ship: Ship, defender_ship: Ship):
        self.attacker_ship = attacker_ship
        self.defender_ship = defender_ship
        self.result        = BoardingResult.ONGOING

        # Build room list from defender ship stations
        self._build_rooms()
        self.current_room_idx = 0

        self.attackers: list[Crew]   = []
        self.attacker_hp: dict[str, float] = {}
        self.hostages:   list[Crew]  = []
        self.turn:       int         = 0

        # Log of events for UI display
        self.log: list[str] = []

    # ── Room generation ───────────────────────────────────────────────────────
    def _build_rooms(self) -> None:
        """Generate rooms, distributing ALL ship crew as defenders across rooms."""
        station_order = [
            "brig", "repair_station", "engine_room",
            "gun_turret", "drone_bay", "cockpit",
        ]
        self.rooms: list[BoardingRoom] = []

        # Collect all crew on the defender ship
        all_crew = list(self.defender_ship.crew)

        # Build a pool to distribute — station-assigned crew go to their room,
        # unassigned crew are spread across remaining rooms
        assigned_ids: set = set()
        station_crew: dict = {}
        for station in station_order:
            c = self.defender_ship.station_assignments.get(station)
            if c:
                station_crew[station] = [c]
                assigned_ids.add(c.id)
            else:
                station_crew[station] = []

        unassigned = [c for c in all_crew if c.id not in assigned_ids]
        # Distribute unassigned crew round-robin across rooms
        import random as _r
        _r.shuffle(unassigned)
        room_count = len(station_order)
        for i, c in enumerate(unassigned):
            station_crew[station_order[i % room_count]].append(c)

        for station in station_order:
            defenders = station_crew[station]
            self.rooms.append(BoardingRoom(station.replace("_", " ").title(),
                                            defenders))

    # ── Starting boarding ─────────────────────────────────────────────────────
    def start_boarding(self, troops: list[Crew]) -> None:
        self.attackers = list(troops)
        for c in troops:
            # Combat stat × 5 = HP pool
            self.attacker_hp[c.id] = float(c.stats.get("combat", 10) * 5)
        self.log.append(f"Boarding party of {len(troops)} launched!")

    # ── Actions ───────────────────────────────────────────────────────────────
    def get_available_actions(self) -> list[str]:
        actions = [BoardingAction.ATTACK, BoardingAction.RETREAT]
        room = self.current_room
        if room and not room.is_cleared and room.defenders:
            actions.append(BoardingAction.HOSTAGE)
        return actions

    @property
    def current_room(self) -> BoardingRoom | None:
        if self.current_room_idx < len(self.rooms):
            return self.rooms[self.current_room_idx]
        return None

    def take_action(self, action: str, target_id: str = "") -> dict:
        """Process one player turn. Returns dict with event info."""
        if self.result != BoardingResult.ONGOING:
            return {"event": "combat_over"}

        self.turn += 1
        events: list[str] = []

        if action == BoardingAction.RETREAT:
            self.result = BoardingResult.RETREATED
            self.log.append("Boarding party retreated!")
            return {"event": "retreat"}

        room = self.current_room
        if room is None:
            # All rooms cleared — ship captured!
            self._capture_ship()
            return {"event": "captured"}

        if action == BoardingAction.ATTACK:
            events += self._resolve_attack_round(room)

        elif action == BoardingAction.HOSTAGE:
            events += self._take_hostage(room)

        # Defenders counter-attack
        if room.defenders and not room.is_cleared:
            events += self._defender_counter(room)

        # Check if attackers are all down
        if all(self.attacker_hp.get(c.id, 0) <= 0 for c in self.attackers):
            self.result = BoardingResult.REPELLED
            events.append("All boarders defeated! Repelled!")

        # Advance to next room if cleared
        elif room.is_cleared:
            self.current_room_idx += 1
            if self.current_room_idx >= len(self.rooms):
                self._capture_ship()
                events.append("Ship captured!")

        self.log.extend(events)
        return {"event": "round", "messages": events}

    # ── Attack resolution ─────────────────────────────────────────────────────
    # ── Rich log helpers ──────────────────────────────────────────────────────
    _HIT_WORDS  = ["slashes", "shoots", "tackles", "fires on", "strikes", "flanks"]
    _CRIT_WORDS = ["CRITICALLY HITS", "DECIMATES", "BLASTS", "DEMOLISHES"]
    _MISS_WORDS = ["misses", "grazes", "barely scratches"]

    def _resolve_attack_round(self, room: BoardingRoom) -> list[str]:
        events = []
        room_flavour = {
            "Brig":            "in the cramped brig",
            "Repair Station":  "near the sparking repair bay",
            "Engine Room":     "amid roaring engines",
            "Gun Turret":      "at the weapons station",
            "Drone Bay":       "between charging drone racks",
            "Cockpit":         "on the bridge",
        }
        loc = room_flavour.get(room.name, f"in {room.name}")
        if self.turn == 1:
            events.append(f"Your squad breaches {room.name}! ({len([d for d in room.defenders if room.hp.get(d.id,0)>0])} defenders {loc})")

        for attacker in self.attackers:
            if self.attacker_hp.get(attacker.id, 0) <= 0:
                continue
            alive_defs = [d for d in room.defenders if room.hp.get(d.id, 0) > 0]
            if not alive_defs:
                break
            target_def = random.choice(alive_defs)
            atk_power  = attacker.stats.get("combat", 10)
            # Infiltrator path bonus
            if attacker.chosen_path == "B":
                atk_power = int(atk_power * 1.4)
            # Morale modifier
            morale_mod = (attacker.morale - 50) / 200.0
            atk_power  = int(atk_power * (1 + morale_mod))
            # Roll with crit chance (15%)
            is_crit = random.random() < 0.15
            dmg     = random.randint(max(1, atk_power - 3), atk_power + 5)
            if is_crit:
                dmg = int(dmg * 1.8)
            room.hp[target_def.id] = max(0.0, room.hp[target_def.id] - dmg)
            verb = random.choice(self._CRIT_WORDS if is_crit else self._HIT_WORDS)
            crit_tag = " [CRIT!]" if is_crit else ""
            events.append(f"  {attacker.name} {verb} {target_def.name} for {dmg} dmg{crit_tag}")
            if room.hp[target_def.id] <= 0:
                events.append(f"  ✓ {target_def.name} is DOWN — neutralised!")
                # Chance attacker gains morale
                attacker.change_morale(random.randint(2, 5))
        # Room cleared?
        if room.is_cleared:
            events.append(f"  Room '{room.name}' cleared!")
        return events

    def _defender_counter(self, room: BoardingRoom) -> list[str]:
        events = []
        alive_defs = [d for d in room.defenders if room.hp.get(d.id, 0) > 0]
        alive_atk  = [a for a in self.attackers if self.attacker_hp.get(a.id, 0) > 0]
        for defender in alive_defs:
            if not alive_atk:
                break
            target = random.choice(alive_atk)
            def_power = defender.stats.get("combat", 10)
            is_crit = random.random() < 0.10
            dmg = random.randint(max(1, def_power - 2), def_power + 3)
            if is_crit:
                dmg = int(dmg * 1.6)
            self.attacker_hp[target.id] = max(0.0, self.attacker_hp[target.id] - dmg)
            verb = random.choice(self._CRIT_WORDS if is_crit else self._HIT_WORDS)
            crit_tag = " [CRIT!]" if is_crit else ""
            events.append(f"  [DEF] {defender.name} {verb} {target.name} for {dmg}{crit_tag}")
            if self.attacker_hp[target.id] <= 0:
                target.injure(ticks=200)
                events.append(f"  ✗ {target.name} goes DOWN — injured!")
                target.change_morale(-10)
        # Low-morale check: chance of retreat warning
        squad_morale = (sum(a.morale for a in self.attackers if self.attacker_hp.get(a.id, 0) > 0)
                        / max(1, sum(1 for a in self.attackers if self.attacker_hp.get(a.id, 0) > 0)))
        if squad_morale < 30:
            events.append("  ⚠ Squad morale is LOW — troops are shaken!")
        return events

    # ── Hostage mechanic ──────────────────────────────────────────────────────
    def _take_hostage(self, room: BoardingRoom) -> list[str]:
        events = []
        alive_defs = [d for d in room.defenders if room.hp.get(d.id, 0) > 0]
        if not alive_defs:
            return ["No one to take hostage here."]
        target = alive_defs[0]
        # Chance based on attacker combat vs defender
        lead_atk = max(self.attackers,
                       key=lambda c: c.stats.get("combat", 0), default=None)
        chance = 0.5
        if lead_atk:
            ratio = lead_atk.stats.get("combat", 10) / max(
                target.stats.get("combat", 1), 1)
            chance = min(0.9, 0.3 + ratio * 0.2)
        if random.random() < chance:
            self.hostages.append(target)
            # Mark hostage as "extracted" via a separate set so is_cleared
            # is NOT falsely triggered — the room still has other defenders.
            # We remove them from the active defenders list instead.
            room.defenders = [d for d in room.defenders if d.id != target.id]
            if target.id in room.hp:
                del room.hp[target.id]
            events.append(f"{target.name} taken hostage!")
        else:
            events.append(f"{target.name} resisted capture!")
        return events

    # ── Ship capture ──────────────────────────────────────────────────────────
    def _capture_ship(self) -> None:
        self.result = BoardingResult.CAPTURED
        self.log.append(f"'{self.defender_ship.custom_name}' has been captured!")

    # ── Post-capture choices ──────────────────────────────────────────────────
    def resolve_capture(self, choice: str) -> dict:
        """choice: 'keep' | 'sell' | 'strip'"""
        ship = self.defender_ship
        if choice == "sell":
            credits = int(ship.price * (ship.hull / max(ship.max_hull, 1)) * 0.6)
            return {"choice": "sell", "credits": credits, "ship": ship}
        elif choice == "strip":
            # Return weapon list
            parts = [w.to_dict() for w in ship.weapons]
            parts += [m.to_dict() for m in ship.modules]
            return {"choice": "strip", "parts": parts}
        else:  # keep
            return {"choice": "keep", "ship": ship}

    # ── Summary ───────────────────────────────────────────────────────────────
    def summary(self) -> dict:
        alive_atk = [c for c in self.attackers
                     if self.attacker_hp.get(c.id, 0) > 0]
        # Crew on the defender ship available for capture
        capturable_crew = list(self.defender_ship.crew)
        return {
            "result":           self.result,
            "turns":            self.turn,
            "survivors":        [c.name for c in alive_atk],
            "hostages":         [c.name for c in self.hostages],
            "capturable_crew":  capturable_crew,
            "log":              self.log[-10:],
        }
