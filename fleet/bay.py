"""fleet/bay.py — Ship Bay System.

The BaySystem manages ships docked inside a carrier's fighter bay.
Docked ships are held in reserve; they do not participate in combat
until launched.  The carrier ship object owns a BaySystem instance.

Bay Control (home base tab) lets the player:
  • Load  — move a fleet ship into the carrier bay
  • Unload — pull a ship back out of the bay into the fleet
  • Repair All — repair all docked ships (costs metal)
  • Set Launch Order — drag/reorder which ship launches first

In combat the carrier auto-launches one ship per threshold crossed
(configurable via bay_launch_hull_pct on the ship data).
"""
from __future__ import annotations
import math
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from entities.ship import Ship


# ── Bay berth ────────────────────────────────────────────────────────────────
class BayBerth:
    """One slot in the carrier bay.  Holds a ship or is empty."""

    def __init__(self, index: int):
        self.index:   int           = index
        self.ship:    "Ship | None" = None
        self.damaged: bool          = False  # berth itself can be damaged

    @property
    def empty(self) -> bool:
        return self.ship is None

    def load(self, ship: "Ship") -> bool:
        if not self.empty:
            return False
        self.ship = ship
        ship._in_bay = True
        return True

    def unload(self) -> "Ship | None":
        s = self.ship
        if s:
            s._in_bay = False
            self.ship = None
        return s

    def to_dict(self) -> dict:
        return {
            "index":   self.index,
            "ship_id": self.ship.id if self.ship else None,
            "damaged": self.damaged,
        }


# ── Bay system ────────────────────────────────────────────────────────────────
class BaySystem:
    """Manages the fighter/ship bay of a carrier.

    Attributes
    ──────────
    capacity        : max ships the bay can hold
    berths          : list[BayBerth]
    _launch_queue   : order in which ships are auto-launched
    _hull_thresholds: set of hull-pct thresholds already triggered
    """

    REPAIR_COST_PER_HULL = 0.5  # metal per HP repaired

    def __init__(self, capacity: int = 4):
        self.capacity           = max(1, capacity)
        self.berths: list[BayBerth] = [BayBerth(i) for i in range(self.capacity)]
        self._hull_thresholds: set[int] = set()   # 75, 50, 25, 0 pct marks
        self._launch_anim: list[dict] = []         # active launch animations
        # Bay alert: set when a launch is triggered this frame
        self.last_launched: "Ship | None" = None

    # ── Query ─────────────────────────────────────────────────────────────────
    @property
    def docked_ships(self) -> list["Ship"]:
        return [b.ship for b in self.berths if b.ship is not None]

    @property
    def docked_count(self) -> int:
        return sum(1 for b in self.berths if not b.empty)

    @property
    def free_berths(self) -> int:
        return sum(1 for b in self.berths if b.empty)

    @property
    def is_full(self) -> bool:
        return self.free_berths == 0

    def launch_order(self) -> list["Ship"]:
        """Ships in launch order (first empty berth first, then by index)."""
        return [b.ship for b in self.berths if b.ship is not None]

    # ── Load / Unload ─────────────────────────────────────────────────────────
    def load(self, ship: "Ship") -> dict:
        """Dock a ship in the bay.  Returns {ok, reason}."""
        if self.is_full:
            return {"ok": False, "reason": f"Bay full ({self.capacity} slots)"}
        for berth in self.berths:
            if berth.empty:
                berth.load(ship)
                return {"ok": True, "berth": berth.index}
        return {"ok": False, "reason": "No free berth"}

    def unload(self, ship: "Ship") -> dict:
        """Remove a ship from the bay.  Returns {ok, ship}."""
        for berth in self.berths:
            if berth.ship is ship:
                berth.unload()
                return {"ok": True, "ship": ship}
        return {"ok": False, "reason": "Ship not in bay"}

    def unload_by_index(self, berth_idx: int) -> "Ship | None":
        if 0 <= berth_idx < len(self.berths):
            return self.berths[berth_idx].unload()
        return None

    # ── Combat auto-launch ────────────────────────────────────────────────────
    def check_auto_launch(self, carrier_ship: "Ship",
                          launch_pct: float = 0.25) -> "Ship | None":
        """Call each frame with current carrier hull %.
        Returns a ship to launch (and removes it from bay) if a threshold
        has been crossed, otherwise returns None.

        launch_pct: fraction of max_hull lost per launch (default 25 %).
        """
        if not self.docked_ships:
            return None

        hp_pct = carrier_ship.hull / max(carrier_ship.max_hull, 1)
        # thresholds at 75%, 50%, 25%, 0% hull remaining
        steps = [int((1.0 - launch_pct * (i + 1)) * 100)
                 for i in range(int(1 / launch_pct))]

        for step in steps:
            if hp_pct * 100 <= step and step not in self._hull_thresholds:
                self._hull_thresholds.add(step)
                # Launch the first ship in the queue
                for berth in self.berths:
                    if berth.ship is not None:
                        ship = berth.unload()
                        self.last_launched = ship
                        return ship
        return None

    def reset_thresholds(self) -> None:
        """Call at the start of a new combat so thresholds reset."""
        self._hull_thresholds.clear()
        self.last_launched = None

    # ── Repair ────────────────────────────────────────────────────────────────
    def repair_all(self, metal_available: int) -> dict:
        """Repair all docked ships.  Costs REPAIR_COST_PER_HULL metal/HP.
        Returns {repaired_hp, metal_spent}."""
        total_damage = sum(
            max(0, s.max_hull - s.hull)
            for s in self.docked_ships
        )
        affordable = min(total_damage,
                         metal_available / max(self.REPAIR_COST_PER_HULL, 0.01))
        if affordable <= 0:
            return {"repaired_hp": 0, "metal_spent": 0}

        # Distribute repairs proportionally
        repaired = 0.0
        metal_left = affordable * self.REPAIR_COST_PER_HULL
        for s in self.docked_ships:
            need = max(0, s.max_hull - s.hull)
            if need > 0 and metal_left >= self.REPAIR_COST_PER_HULL:
                fix  = min(need, metal_left / self.REPAIR_COST_PER_HULL)
                s.repair(fix)
                repaired   += fix
                metal_left -= fix * self.REPAIR_COST_PER_HULL

        spent = int(repaired * self.REPAIR_COST_PER_HULL)
        return {"repaired_hp": int(repaired), "metal_spent": spent}

    # ── Stats for Bay Control UI ──────────────────────────────────────────────
    def stats(self) -> dict:
        ships = self.docked_ships
        total_crew = sum(len(s.crew) for s in ships)
        total_hull = sum(s.hull for s in ships)
        max_hull   = sum(s.max_hull for s in ships)
        repair_need = sum(max(0, s.max_hull - s.hull) for s in ships)
        return {
            "docked":       len(ships),
            "capacity":     self.capacity,
            "total_crew":   total_crew,
            "total_hull":   int(total_hull),
            "max_hull":     int(max_hull),
            "repair_need":  int(repair_need),
            "repair_cost":  int(repair_need * self.REPAIR_COST_PER_HULL),
        }

    # ── Launch animation helpers (visual only) ────────────────────────────────
    def start_launch_anim(self, carrier_x: float, carrier_y: float,
                          angle: float) -> None:
        """Record a launch animation entry for SpaceCombat to draw."""
        self._launch_anim.append({
            "x": carrier_x, "y": carrier_y,
            "angle": angle,
            "t": 0.0, "max_t": 0.6,
        })

    def update_anim(self, dt: float) -> None:
        for a in self._launch_anim:
            a["t"] += dt
        self._launch_anim = [a for a in self._launch_anim if a["t"] < a["max_t"]]

    def draw_anim(self, surface, ox: float, oy: float) -> None:
        import pygame
        for a in self._launch_anim:
            frac = a["t"] / max(a["max_t"], 0.01)
            # Expanding door-glow rectangle
            sx = int(a["x"] + ox)
            sy = int(a["y"] + oy)
            glow_w = int(40 + 60 * frac)
            glow_h = int(10 + 30 * frac)
            alpha  = int(200 * (1 - frac))
            gsurf  = pygame.Surface((glow_w, glow_h), pygame.SRCALPHA)
            pygame.draw.ellipse(gsurf, (255, 200, 80, alpha), (0, 0, glow_w, glow_h))
            surface.blit(gsurf, (sx - glow_w // 2, sy - glow_h // 2))
            # "LAUNCH" text flash
            if frac < 0.4:
                try:
                    fnt = pygame.font.SysFont("monospace", 11, bold=True)
                    lt  = fnt.render("LAUNCH!", True,
                                     (255, int(220 * (1 - frac)), 40))
                    surface.blit(lt, (sx - lt.get_width() // 2, sy - 26))
                except Exception:
                    pass

    # ── Serialization ─────────────────────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "capacity": self.capacity,
            "berths":   [b.to_dict() for b in self.berths],
        }
