"""fleet/scrapper.py — Scrapper ship recovery logic."""
from __future__ import annotations
import random
from entities.ship import Ship
from core.events   import bus


class WreckRecord:
    def __init__(self, ship: Ship, sector_id: str):
        self.ship      = ship
        self.sector_id = sector_id
        self.despawn_timer = 300.0   # 5 minutes before wreck despawns
        self.recovered = False

    def tick(self, dt: float) -> bool:
        """Returns True if wreck despawned."""
        if self.recovered:
            return False
        self.despawn_timer -= dt
        return self.despawn_timer <= 0


class ScrapperManager:
    def __init__(self, home_base=None):
        self.scrapper_ships: list[Ship] = []
        self.wrecks:         list[WreckRecord] = []
        self.home_base       = home_base
        self._travel_timers: dict[str, float] = {}  # wreck_id → travel time

    def add_scrapper(self, ship: Ship) -> None:
        ship.fleet_order = "scrapper"
        self.scrapper_ships.append(ship)

    def register_wreck(self, ship: Ship, sector_id: str) -> None:
        record = WreckRecord(ship, sector_id)
        self.wrecks.append(record)
        bus.publish("notification",
                    msg=f"Wreck detected: {ship.custom_name}. "
                        f"{'Scrapper dispatched.' if self.scrapper_ships else 'No scrapper available!'}",
                    color=(255, 160, 40))

    def update(self, dt: float) -> list[dict]:
        """Simulate scrapper travel and recovery. Returns recovery events."""
        events: list[dict] = []

        # Tick despawn timers
        for wreck in list(self.wrecks):
            if wreck.tick(dt):
                self.wrecks.remove(wreck)
                bus.publish("notification",
                            msg=f"Wreck of {wreck.ship.custom_name} has drifted away.",
                            color=(120, 120, 120))

        if not self.scrapper_ships:
            return events

        for wreck in [w for w in self.wrecks if not w.recovered]:
            wreck_key = id(wreck)
            if wreck_key not in self._travel_timers:
                # Dispatch a scrapper — travel time 20–60 sec
                self._travel_timers[wreck_key] = random.uniform(20, 60)

            self._travel_timers[wreck_key] -= dt
            if self._travel_timers[wreck_key] <= 0:
                wreck.recovered = True
                del self._travel_timers[wreck_key]
                recovery = self._recover_wreck(wreck)
                events.append(recovery)

        return events

    def _recover_wreck(self, wreck: WreckRecord) -> dict:
        ship = wreck.ship

        # Recover surviving crew (50% chance per crew member)
        recovered_crew = []
        for c in ship.crew:
            if random.random() < 0.5:
                c.injure(ticks=random.randint(100, 300))
                recovered_crew.append(c)

        # Hull condition determines repair cost
        hull_pct = ship.hull / max(ship.max_hull, 1)
        repair_cost = int(ship.price * (1.0 - hull_pct) * 0.3)

        # Reset ship to repairable state
        ship.hull = max(1.0, ship.hull)  # ensure it has at least 1 HP

        bus.publish("notification",
                    msg=f"Scrapper recovered {ship.custom_name}! "
                        f"{len(recovered_crew)} crew rescued.",
                    color=(60, 200, 80))

        # Deliver resources to home base if available
        if self.home_base:
            self.home_base.add_resource("metal", random.randint(5, 25))

        return {
            "type":          "wreck_recovered",
            "ship":          ship,
            "crew_rescued":  recovered_crew,
            "repair_cost":   repair_cost,
        }
