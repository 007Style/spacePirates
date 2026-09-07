"""fleet/orders.py — Ship order constants and autonomous simulation."""
from __future__ import annotations
import random
from entities.ship import Ship
from core.events   import bus


class Order:
    FOLLOW          = "follow"
    GUARD_BASE      = "guard_base"
    PATROL_COLLECT  = "patrol_collect"
    MISSION         = "mission"
    STANDBY         = "standby"
    WANDER          = "wander"   # alias for PATROL_COLLECT — patrols, kills enemies, collects resources

    ALL = [FOLLOW, GUARD_BASE, PATROL_COLLECT, MISSION, STANDBY, WANDER]


class MissionDef:
    def __init__(self, mission_id: str, title: str, duration: float,
                 difficulty: int, rewards: dict):
        self.mission_id  = mission_id
        self.title       = title
        self.duration    = duration      # seconds
        self.difficulty  = difficulty    # 1–5
        self.rewards     = rewards       # {credits, metal, xp_bonus}
        self.elapsed     = 0.0
        self.assigned_ship: Ship | None = None
        self.complete    = False
        self.failed      = False

    @property
    def progress_pct(self) -> float:
        return min(1.0, self.elapsed / max(self.duration, 1))

    def success_chance(self) -> float:
        if not self.assigned_ship:
            return 0.2
        crew_power = sum(
            c.stats.get("combat", 0) + c.stats.get("gunnery", 0)
            for c in self.assigned_ship.crew
        )
        ship_power = self.assigned_ship.max_hull / 100
        raw = (crew_power / 10 + ship_power) / (self.difficulty * 5)
        return max(0.1, min(0.95, raw))

    def to_dict(self) -> dict:
        return {
            "mission_id": self.mission_id,
            "title":      self.title,
            "duration":   self.duration,
            "elapsed":    self.elapsed,
            "complete":   self.complete,
            "failed":     self.failed,
            "ship_id":    self.assigned_ship.id if self.assigned_ship else None,
        }


# ── Autonomous patrol simulation ──────────────────────────────────────────────

class PatrolSimulator:
    TICK_INTERVAL   = 30.0   # seconds between patrol events
    RESOURCE_CHANCE = 0.6
    KILL_CHANCE     = 0.4
    AMBUSH_CHANCE   = 0.15

    def __init__(self):
        self._timers: dict[str, float] = {}  # ship_id → seconds until next tick

    def tick(self, dt: float, ship: Ship, fleet_admiral_bonus: float = 0.0
             ) -> list[dict]:
        """Simulate one time step for a patrolling ship. Returns events."""
        events: list[dict] = []
        sid = ship.id
        self._timers[sid] = self._timers.get(sid, self.TICK_INTERVAL)
        self._timers[sid] -= dt
        if self._timers[sid] > 0:
            return events
        self._timers[sid] = self.TICK_INTERVAL

        luck = fleet_admiral_bonus

        # Resource find
        if random.random() < self.RESOURCE_CHANCE + luck * 0.1:
            amount = random.randint(5, 30)
            rtype  = random.choice(["metal", "fuel", "supplies"])
            events.append({"type": "resource_found", "ship_id": sid,
                           "resource": rtype, "amount": amount})

        # Enemy kill
        if random.random() < self.KILL_CHANCE + luck * 0.1:
            xp_gain = random.randint(10, 50)
            # Award XP to all crew
            for crew in ship.crew:
                crew.add_xp(xp_gain)
            events.append({"type": "patrol_kill", "ship_id": sid, "xp": xp_gain})
            bus.publish("enemy_killed", ship=None, kills=1)  # counts toward progression

        # Ambush check
        if random.random() < self.AMBUSH_CHANCE:
            dmg = random.randint(10, 40)
            ship.take_damage(float(dmg))
            events.append({"type": "patrol_ambush", "ship_id": sid, "damage": dmg})
            bus.publish("notification",
                        msg=f"⚠ {ship.custom_name} is under attack on patrol!",
                        color=(255, 180, 40))

        return events
