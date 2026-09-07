"""base/raiders.py — Base raider wave logic."""
from __future__ import annotations
import random
import json
import os
from entities.ship import Ship
from entities.weapon import Weapon
from settings import DATA_DIR
from core.events import bus

# Warning time before raiders arrive (5 minutes = 300 seconds)
RAID_WARNING_TIME = 300.0


class RaiderWave:
    def __init__(self, wave_number: int, ships: list[Ship]):
        self.wave_number = wave_number
        self.ships       = ships
        self.defeated    = False
        self.active      = True

    @property
    def strength(self) -> int:
        return sum(s.max_hull for s in self.ships)


class RaiderManager:
    BASE_INTERVAL = 600.0    # seconds between waves
    MIN_INTERVAL  = 120.0

    def __init__(self, wanted_level_ref=None):
        self._wanted_level_ref = wanted_level_ref
        self._timer            = self.BASE_INTERVAL
        self._wave_number      = 0
        self.active_wave: RaiderWave | None = None
        self._ships_data:   list[dict] = []
        self._weapons_data: list[dict] = []
        self._load_data()

        # Warning state
        self._raid_warning      = False   # True during the 5-minute countdown
        self._warning_timer     = 0.0     # counts DOWN from RAID_WARNING_TIME to 0
        self._pending_wave_data: list[dict] | None = None  # ships pre-rolled for incoming wave

    def _load_data(self) -> None:
        try:
            with open(os.path.join(DATA_DIR, "ships.json")) as f:
                self._ships_data = json.load(f)
            with open(os.path.join(DATA_DIR, "weapons.json")) as f:
                self._weapons_data = json.load(f)
        except Exception:
            pass

    def _interval(self) -> float:
        wanted = self._wanted_level_ref() if callable(self._wanted_level_ref) else 1
        return max(self.MIN_INTERVAL, self.BASE_INTERVAL - wanted * 80)

    def update(self, dt: float) -> bool:
        """Returns True if a new raid warning just started."""
        if self.active_wave and self.active_wave.active:
            return False  # Already raiding

        # ── Warning countdown phase ───────────────────────────────────────────
        if self._raid_warning:
            self._warning_timer -= dt
            if self._warning_timer <= 0:
                self._raid_warning = False
                self._warning_timer = 0.0
                self._spawn_wave()
                return False
            return False

        # ── Normal timer until next warning ──────────────────────────────────
        self._timer -= dt
        if self._timer <= 0:
            self._timer = self._interval()
            self._start_warning()
            return True   # warning started — notify caller
        return False

    def _start_warning(self) -> None:
        """Begin the 5-minute warning countdown before raiders arrive."""
        self._raid_warning  = True
        self._warning_timer = RAID_WARNING_TIME
        # Pre-roll the ships so the warning message can say how many are coming
        self._pending_wave_data = self._roll_ship_configs()
        count = len(self._pending_wave_data)
        bus.publish("raid_warning_started",
                    seconds=RAID_WARNING_TIME,
                    ship_count=count)

    def warning_seconds_left(self) -> float:
        """Seconds remaining on the current warning timer (0 if no warning)."""
        return max(0.0, self._warning_timer) if self._raid_warning else 0.0

    def _roll_ship_configs(self) -> list[dict]:
        wanted    = self._wanted_level_ref() if callable(self._wanted_level_ref) else 1
        wave_num  = self._wave_number
        # Scaling ship count: each 3 waves adds an extra raider
        count = max(1, wanted + wave_num // 3 + random.randint(0, 2))
        configs = []
        for _ in range(count):
            pool = [s for s in self._ships_data
                    if s.get("rarity") in ("common", "uncommon")]
            if not pool:
                pool = self._ships_data
            configs.append(random.choice(pool))
        return configs

    def _spawn_wave(self) -> None:
        configs = self._pending_wave_data or self._roll_ship_configs()
        self._pending_wave_data = None
        wave_num = self._wave_number + 1  # +1 because we increment after
        # Hull scaling factor: 15% harder per wave
        hull_scale = 2.0 * (1 + wave_num * 0.15)
        ships = []
        mk_tier  = max(1, min(wave_num, 5))
        for cfg in configs:
            ship = Ship(cfg)
            # Scale hull AND shield for tougher raiders
            shield_scale = 1.5 * (1 + wave_num * 0.10)
            ship.hull      = ship.hull      * hull_scale
            ship.max_hull  = ship.max_hull  * hull_scale
            ship.shield    = ship.shield    * shield_scale
            ship.max_shield= ship.max_shield* shield_scale
            # Long shield recharge lock like sector enemies
            ship._enemy_shield_mode = True
            ship.color_scheme = (200, 60, 60)
            ship.custom_name  = f"Raider Mk{mk_tier}"
            if self._weapons_data:
                w = random.choice(self._weapons_data[:3])
                ship.add_weapon(Weapon(w))
            ships.append(ship)

        self._wave_number += 1
        self.active_wave = RaiderWave(self._wave_number, ships)
        bus.publish("base_raid_started", wave=self.active_wave)

    def resolve_wave(self, survived_ships: list[Ship]) -> dict:
        """Call when base combat ends. Returns damage report."""
        if not self.active_wave:
            return {}
        destroyed = [s for s in self.active_wave.ships
                     if s.is_destroyed]
        self.active_wave.defeated = True
        self.active_wave.active   = False
        bus.publish("base_raid_ended", wave=self.active_wave,
                    raiders_destroyed=len(destroyed))
        return {
            "wave":             self.active_wave.wave_number,
            "raiders_total":    len(self.active_wave.ships),
            "raiders_defeated": len(destroyed),
        }

    def to_dict(self) -> dict:
        return {
            "timer":         self._timer,
            "wave_number":   self._wave_number,
            "raid_warning":  self._raid_warning,
            "warning_timer": self._warning_timer,
        }

    def load_from_dict(self, data: dict) -> None:
        self._timer         = data.get("timer",         self.BASE_INTERVAL)
        self._wave_number   = data.get("wave_number",   0)
        self._raid_warning  = data.get("raid_warning",  False)
        self._warning_timer = data.get("warning_timer", 0.0)
