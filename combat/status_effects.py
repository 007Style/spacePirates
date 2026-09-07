"""combat/status_effects.py — Status effect definitions."""
from __future__ import annotations


class StatusEffect:
    """Base class for all status effects."""
    NAME     = "unknown"
    DURATION = 3.0  # seconds

    def __init__(self, duration: float | None = None):
        self.remaining = duration if duration is not None else self.DURATION

    def tick(self, dt: float, ship) -> None:
        """Called every frame while active."""
        self.remaining -= dt

    @property
    def expired(self) -> bool:
        return self.remaining <= 0

    def on_apply(self, ship) -> None:
        ship.apply_status(self.NAME, self.remaining)

    def on_expire(self, ship) -> None:
        pass


class BurningEffect(StatusEffect):
    NAME     = "burning"
    DURATION = 4.0
    DPS      = 8.0

    def tick(self, dt, ship):
        super().tick(dt, ship)
        ship.take_damage(self.DPS * dt, ignore_shield=True)


class EMPEffect(StatusEffect):
    NAME     = "emp"
    DURATION = 3.0

    def on_apply(self, ship):
        super().on_apply(ship)
        # Disable weapons temporarily — tracked via status flag on ship
        ship.apply_status("weapons_offline", self.DURATION)


class HullBreachEffect(StatusEffect):
    NAME     = "hull_breach"
    DURATION = 6.0
    DPS      = 5.0

    def tick(self, dt, ship):
        super().tick(dt, ship)
        ship.take_damage(self.DPS * dt, ignore_shield=True)
        ship.shield = max(0.0, ship.shield - 2 * dt)


class BoardedEffect(StatusEffect):
    NAME     = "boarded"
    DURATION = 999.0  # removed when boarding combat ends

    def on_apply(self, ship):
        super().on_apply(ship)
        ship.apply_status("movement_offline", 2.0)


class SystemOfflineEffect(StatusEffect):
    NAME     = "system_offline"
    DURATION = 5.0

    def __init__(self, station: str, duration: float | None = None):
        super().__init__(duration)
        self.station = station

    def on_apply(self, ship):
        super().on_apply(ship)
        ship.apply_status(f"station_offline_{self.station}", self.DURATION)

    def on_expire(self, ship):
        key = f"station_offline_{self.station}"
        ship.status_effects.pop(key, None)


class ShieldDrainEffect(StatusEffect):
    NAME     = "shield_drain"
    DURATION = 3.0
    DPS      = 15.0

    def tick(self, dt, ship):
        super().tick(dt, ship)
        ship.shield = max(0.0, ship.shield - self.DPS * dt)


class SlowEffect(StatusEffect):
    NAME     = "slow"
    DURATION = 3.0
    FACTOR   = 0.5

    def on_apply(self, ship):
        super().on_apply(ship)
        ship._slow_factor = self.FACTOR

    def on_expire(self, ship):
        ship._slow_factor = 1.0


# Registry: effect name → class
EFFECT_REGISTRY: dict[str, type] = {
    "burning":      BurningEffect,
    "emp":          EMPEffect,
    "hull_breach":  HullBreachEffect,
    "boarded":      BoardedEffect,
    "system_offline": SystemOfflineEffect,
    "shield_drain": ShieldDrainEffect,
    "slow":         SlowEffect,
}


def make_effect(name: str, **kwargs) -> StatusEffect | None:
    cls = EFFECT_REGISTRY.get(name)
    if cls is None:
        return None
    return cls(**kwargs)
