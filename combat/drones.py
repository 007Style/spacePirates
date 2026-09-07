"""combat/drones.py — Player-launched drone system.

Drones are launched from the player's ship in combat (up to max_slots at a
time, default 5).  Each drone has a type, a live position, a behaviour, and
a duration.  They are rendered in SpaceCombat and their effects are applied
during the update loop.

Drone types
───────────
  attack  – Flies toward the nearest enemy; fires a weak shot every 1.5 s;
             deals 8 dmg per hit; lasts 30 s.
  repair  – Orbits the player ship; heals the player 4 HP/s; lasts 25 s.
  scout   – Orbits at a wider radius; extends the combat radar range by 400 px
             and deals 4 dmg to enemies it passes through; lasts 40 s.
  emp     – Rushes the nearest enemy; on contact applies a 3-second slow
             (50% speed) and disables their shield briefly; single-use.
  shield  – Orbits between player and nearest enemy; adds +20 temporary shield
             to the player (decays when the drone dies); lasts 20 s.
"""
from __future__ import annotations
import math
import random
import pygame


# ── Drone type definitions ────────────────────────────────────────────────────
DRONE_TYPES: dict[str, dict] = {
    "attack": {
        "label":       "Attack",
        "color":       (255, 100, 60),
        "glow_color":  (255, 60, 20),
        "duration":    30.0,
        "fire_cd":     1.5,
        "damage":      8,
        "speed":       140,
        "orbit_r":     None,   # None = flies to target
        "size":        5,
        "desc":        "Attacks nearest enemy  8 dmg / 1.5 s  30 s duration",
        "cost":        350,
    },
    "repair": {
        "label":       "Repair",
        "color":       (60, 220, 120),
        "glow_color":  (40, 180, 90),
        "duration":    25.0,
        "fire_cd":     None,
        "heal_rate":   4.0,    # HP/s to player
        "speed":       90,
        "orbit_r":     70,
        "size":        5,
        "desc":        "Heals player 4 HP/s while orbiting  25 s duration",
        "cost":        450,
    },
    "scout": {
        "label":       "Scout",
        "color":       (100, 200, 255),
        "glow_color":  (60, 160, 255),
        "duration":    40.0,
        "fire_cd":     3.0,
        "damage":      4,
        "speed":       180,
        "orbit_r":     160,   # wide orbit
        "radar_bonus": 400,   # extra radar range (px)
        "size":        4,
        "desc":        "Extends radar +400 px, deals 4 dmg on pass-through  40 s",
        "cost":        250,
    },
    "emp": {
        "label":       "EMP",
        "color":       (180, 120, 255),
        "glow_color":  (140, 80, 255),
        "duration":    15.0,
        "fire_cd":     None,
        "speed":       200,
        "orbit_r":     None,  # flies to target then detonates
        "emp_slow":    0.5,   # speed multiplier on target
        "emp_dur":     3.0,   # seconds of slow
        "size":        5,
        "desc":        "Rushes enemy, applies 50% slow + shield disable for 3 s",
        "cost":        600,
    },
    "shield": {
        "label":       "Shield",
        "color":       (60, 160, 255),
        "glow_color":  (40, 120, 220),
        "duration":    20.0,
        "fire_cd":     None,
        "shield_bonus":20,    # temporary shield added to player
        "speed":       110,
        "orbit_r":     90,
        "size":        6,
        "desc":        "Adds +20 temp shield to player while active  20 s",
        "cost":        500,
    },
}


class Drone:
    """A single live drone unit."""

    def __init__(self, dtype: str, owner_x: float, owner_y: float,
                 idx: int = 0):
        self.dtype      = dtype
        spec            = DRONE_TYPES[dtype]
        self.color      = spec["color"]
        self.glow_color = spec["glow_color"]
        self.speed      = spec["speed"]
        self.orbit_r    = spec.get("orbit_r")
        self.size       = spec["size"]
        self.duration   = spec["duration"]
        self.age        = 0.0
        self.fire_cd    = spec.get("fire_cd") or 9999.0
        self._fire_t    = random.uniform(0, self.fire_cd)  # stagger shots
        self.damage     = spec.get("damage", 0)
        self.heal_rate  = spec.get("heal_rate", 0.0)
        self.radar_bonus= spec.get("radar_bonus", 0)
        self.shield_bonus = spec.get("shield_bonus", 0)
        self.emp_slow   = spec.get("emp_slow", 1.0)
        self.emp_dur    = spec.get("emp_dur", 0.0)
        self.alive      = True
        self.detonated  = False   # EMP/one-shot drones

        # Position + velocity
        angle_off = (idx / 5) * 2 * math.pi
        self.x = owner_x + 40 * math.cos(angle_off)
        self.y = owner_y + 40 * math.sin(angle_off)
        self.vx = 0.0
        self.vy = 0.0

        # Orbit angle (for orbiting drones)
        self._orbit_angle = angle_off

        # Visual pulse
        self._pulse = random.uniform(0, 6.28)

    @property
    def remaining(self) -> float:
        return max(0.0, self.duration - self.age)

    def update(self, dt: float,
               owner_x: float, owner_y: float,
               enemies: list,
               player_ship) -> list[tuple]:
        """Returns list of (action, data) tuples for effects this frame.
        action: 'heal', 'fire', 'emp_hit', 'shield_on'
        """
        if not self.alive:
            return []

        self.age    += dt
        self._pulse += dt * 3.0

        if self.age >= self.duration:
            self.alive = False
            return []

        effects = []
        self._fire_t += dt

        if self.orbit_r is not None:
            # ── Orbiting drones ────────────────────────────────────────────
            self._orbit_angle += dt * (self.speed / max(self.orbit_r, 1))
            self.x = owner_x + self.orbit_r * math.cos(self._orbit_angle)
            self.y = owner_y + self.orbit_r * math.sin(self._orbit_angle)

            if self.dtype == "repair" and self.heal_rate:
                effects.append(("heal", self.heal_rate * dt))

            if self.dtype == "shield":
                effects.append(("shield_on", self.shield_bonus))

            # Scout: fire at enemies within pass-through range
            if self.dtype == "scout" and self._fire_t >= self.fire_cd:
                for e in enemies:
                    if getattr(e, "is_destroyed", True):
                        continue
                    dist = math.hypot(e.x - self.x, e.y - self.y)
                    if dist < 120:
                        self._fire_t = 0.0
                        effects.append(("fire", (e, self.damage)))
                        break

        else:
            # ── Non-orbiting drones (attack / emp) ────────────────────────────
            # Find nearest enemy measured FROM THE DRONE (not from origin)
            target = self._nearest_enemy_from(enemies, self.x, self.y)
            has_target = target and not getattr(target, "is_destroyed", True)

            if has_target:
                tx, ty = target.x, target.y
                dx, dy = tx - self.x, ty - self.y
                dist   = math.hypot(dx, dy) or 1

                if self.dtype == "attack":
                    # ── Attack: stay close to player, engage when enemy is
                    #    within a reasonable escort radius (400 px).
                    #    Outside that range follow the owner instead.
                    owner_dx = owner_x - self.x
                    owner_dy = owner_y - self.y
                    owner_dist = math.hypot(owner_dx, owner_dy) or 1

                    if dist < 400:
                        # Enemy close enough — charge it
                        self.vx = (dx / dist) * self.speed
                        self.vy = (dy / dist) * self.speed
                    else:
                        # Enemy too far — shadow the player instead
                        self.vx = (owner_dx / owner_dist) * self.speed
                        self.vy = (owner_dy / owner_dist) * self.speed

                    self.x += self.vx * dt
                    self.y += self.vy * dt

                    if self._fire_t >= self.fire_cd and dist < 220:
                        self._fire_t = 0.0
                        effects.append(("fire", (target, self.damage)))

                elif self.dtype == "emp":
                    # ── EMP: rush the target; detonate on contact
                    self.vx = (dx / dist) * self.speed
                    self.vy = (dy / dist) * self.speed
                    self.x += self.vx * dt
                    self.y += self.vy * dt

                    if dist < 40 and not self.detonated:
                        self.detonated = True
                        self.alive = False
                        effects.append(("emp_hit", (target, self.emp_slow,
                                                    self.emp_dur)))

            else:
                # No live enemy — orbit the owner loosely
                orbit_radius = 90 if self.dtype == "attack" else 70
                self._orbit_angle += dt * 1.2
                self.x = owner_x + orbit_radius * math.cos(self._orbit_angle)
                self.y = owner_y + orbit_radius * math.sin(self._orbit_angle)

        return effects

    @staticmethod
    def _nearest_enemy_from(enemies: list, from_x: float, from_y: float):
        """Return nearest living enemy measured from (from_x, from_y)."""
        best, best_dist = None, 9999.0
        for e in enemies:
            if getattr(e, "is_destroyed", True):
                continue
            dist = math.hypot(getattr(e, "x", 0) - from_x,
                              getattr(e, "y", 0) - from_y)
            if dist < best_dist:
                best_dist = dist
                best = e
        return best

    # Keep old name as an alias so nothing else breaks
    @staticmethod
    def _nearest_enemy(enemies: list):
        return Drone._nearest_enemy_from(enemies, 0.0, 0.0)

    def draw(self, surface: pygame.Surface, ox: float, oy: float) -> None:
        if not self.alive:
            return
        sx = int(self.x + ox)
        sy = int(self.y + oy)
        sw, sh = surface.get_size()
        if not (-20 < sx < sw + 20 and -20 < sy < sh + 20):
            return

        pulse = (math.sin(self._pulse) + 1) * 0.5
        sz    = self.size
        glow_r = sz + int(3 * pulse)

        # Glow halo
        gsurf = pygame.Surface((glow_r * 4, glow_r * 4), pygame.SRCALPHA)
        pygame.draw.circle(gsurf, (*self.glow_color, int(50 * pulse)),
                           (glow_r * 2, glow_r * 2), glow_r * 2)
        surface.blit(gsurf, (sx - glow_r * 2, sy - glow_r * 2),
                     special_flags=pygame.BLEND_ALPHA_SDL2)

        # ── Per-type distinct shapes ──────────────────────────────────────────
        col  = self.color
        if self.dtype == "attack":
            # Fighter silhouette: forward-pointing arrowhead
            pts = [(sx,      sy - sz - 2),   # nose
                   (sx + sz, sy + sz - 1),   # right wing tip
                   (sx,      sy + sz // 2),  # tail notch centre
                   (sx - sz, sy + sz - 1)]   # left wing tip
            pygame.draw.polygon(surface, col, pts)
            pygame.draw.polygon(surface, (255, 255, 255), pts, 1)
            # Engine glow dot at tail
            pygame.draw.circle(surface, (255, 140, 40), (sx, sy + sz - 1), 2)

        elif self.dtype == "repair":
            # Green cross (medical)
            arm = max(3, sz)
            pygame.draw.rect(surface, col, (sx - 1, sy - arm, 3, arm * 2 + 1))
            pygame.draw.rect(surface, col, (sx - arm, sy - 1, arm * 2 + 1, 3))
            pygame.draw.rect(surface, (255, 255, 255),
                             (sx - arm, sy - arm, arm * 2 + 1, arm * 2 + 1), 1)

        elif self.dtype == "scout":
            # Saucer: wide flat ellipse + dome
            rx, ry = sz + 3, max(2, sz // 2)
            pygame.draw.ellipse(surface, col, (sx - rx, sy - ry, rx * 2, ry * 2))
            pygame.draw.ellipse(surface, (255, 255, 255),
                                (sx - rx, sy - ry, rx * 2, ry * 2), 1)
            # Dome on top
            dome_r = max(2, sz - 1)
            pygame.draw.circle(surface, (200, 220, 255), (sx, sy - 1), dome_r)
            # Glare
            pygame.draw.circle(surface, (255, 255, 255), (sx - 1, sy - 2), 1)

        elif self.dtype == "emp":
            # Hexagon with lightning bolt inside
            n = 6
            hex_pts = [(sx + int(sz * math.cos(math.pi / 6 + i * math.pi / 3)),
                        sy + int(sz * math.sin(math.pi / 6 + i * math.pi / 3)))
                       for i in range(n)]
            pygame.draw.polygon(surface, col, hex_pts, 2)
            # Lightning bolt (zigzag)
            bolt = [(sx,       sy - sz + 3),
                    (sx - 2,   sy - 1),
                    (sx + 1,   sy - 1),
                    (sx - 2,   sy + sz - 3)]
            pygame.draw.lines(surface, (255, 255, 120), False, bolt, 2)
            # Yellow inner glow
            pygame.draw.circle(surface, (255, 240, 60), (sx, sy), 2)

        elif self.dtype == "shield":
            # Two concentric rings (energy shield look)
            pygame.draw.circle(surface, col, (sx, sy), sz, 2)
            pygame.draw.circle(surface, col, (sx, sy), max(1, sz - 3), 1)
            # Cross of 4 dots on ring
            for angle_deg in (0, 90, 180, 270):
                a = math.radians(angle_deg)
                dx = int((sz - 1) * math.cos(a))
                dy = int((sz - 1) * math.sin(a))
                pygame.draw.circle(surface, (200, 230, 255), (sx + dx, sy + dy), 2)

        else:
            # Fallback: diamond
            pts = [(sx, sy - sz), (sx + sz, sy), (sx, sy + sz), (sx - sz, sy)]
            pygame.draw.polygon(surface, col, pts)

        # Bright centre dot (all types)
        pygame.draw.circle(surface, (255, 255, 255), (sx, sy), max(1, sz // 3))

        # Remaining-life bar (tiny, above drone)
        bar_w = 14
        frac  = self.remaining / self.duration
        pygame.draw.rect(surface, (40, 40, 40),
                         (sx - bar_w // 2, sy - sz - 5, bar_w, 2))
        pygame.draw.rect(surface, self.color,
                         (sx - bar_w // 2, sy - sz - 5,
                          int(bar_w * frac), 2))


class DroneSystem:
    """Manages the player's drone bay for a single combat session.

    Attributes
    ──────────
    max_slots   : int  – max simultaneous drones (from ship + upgrades)
    drones      : list[Drone] – currently live drones
    """

    def __init__(self, max_slots: int = 5):
        self.max_slots: int      = max_slots
        self.drones: list[Drone] = []
        self._launch_cooldown    = 0.0    # brief CD between launches

    # ── Querying ──────────────────────────────────────────────────────────────
    @property
    def active_count(self) -> int:
        return sum(1 for d in self.drones if d.alive)

    @property
    def radar_bonus(self) -> int:
        """Sum of all live scout drone radar bonuses."""
        return sum(d.radar_bonus for d in self.drones
                   if d.alive and d.dtype == "scout")

    @property
    def has_shield_drone(self) -> bool:
        return any(d.alive and d.dtype == "shield" for d in self.drones)

    def can_launch(self) -> bool:
        return self.active_count < self.max_slots and self._launch_cooldown <= 0

    # ── Launching ─────────────────────────────────────────────────────────────
    def launch(self, dtype: str, owner_x: float, owner_y: float) -> bool:
        """Launch one drone. Returns True if successful."""
        if dtype not in DRONE_TYPES:
            return False
        if not self.can_launch():
            return False
        idx = self.active_count
        d   = Drone(dtype, owner_x, owner_y, idx=idx)
        self.drones.append(d)
        self._launch_cooldown = 0.4   # brief CD so you can't spam
        return True

    def launch_batch(self, dtypes: list[str],
                     owner_x: float, owner_y: float) -> int:
        """Launch up to 5 drones of specified types. Returns count launched."""
        launched = 0
        for dt in dtypes[:5]:
            if self.launch(dt, owner_x, owner_y):
                launched += 1
        return launched

    # ── Update ────────────────────────────────────────────────────────────────
    def update(self, dt: float,
               owner_x: float, owner_y: float,
               enemies: list,
               player_ship) -> None:
        """Process all live drones, apply effects to player_ship / enemies."""
        self._launch_cooldown = max(0.0, self._launch_cooldown - dt)

        # Remove expired/dead drones (keep list clean)
        self.drones = [d for d in self.drones if d.alive or d.age < d.duration]

        shield_applied_this_frame = False

        for drone in self.drones:
            if not drone.alive:
                continue
            effects = drone.update(dt, owner_x, owner_y, enemies, player_ship)
            for action, data in effects:
                if action == "heal":
                    player_ship.repair(data)

                elif action == "fire":
                    target, dmg = data
                    if not getattr(target, "is_destroyed", True):
                        target.take_damage(dmg)

                elif action == "emp_hit":
                    target, slow_mult, slow_dur = data
                    if not getattr(target, "is_destroyed", True):
                        # Apply slow flag (SpaceCombat's EnemyAI checks this)
                        target._emp_slow_mult = slow_mult
                        target._emp_slow_timer = slow_dur
                        target.shield = 0.0
                        target.shield_recharge_lock = max(
                            target.shield_recharge_lock, slow_dur)

                elif action == "shield_on" and not shield_applied_this_frame:
                    # Top up player shield up to the drone's bonus cap
                    cap = player_ship.max_shield + data
                    player_ship.shield = min(cap, player_ship.shield + 1.0 * dt)
                    shield_applied_this_frame = True

        # Purge fully dead drones
        self.drones = [d for d in self.drones if d.alive]

    # ── Draw ──────────────────────────────────────────────────────────────────
    def draw(self, surface: pygame.Surface, ox: float, oy: float) -> None:
        for d in self.drones:
            if d.alive:
                d.draw(surface, ox, oy)

    # ── HUD info ──────────────────────────────────────────────────────────────
    def status_lines(self) -> list[str]:
        lines = []
        by_type: dict[str, list] = {}
        for d in self.drones:
            if d.alive:
                by_type.setdefault(d.dtype, []).append(d)
        for dtype, group in by_type.items():
            label = DRONE_TYPES[dtype]["label"]
            remaining = min(d.remaining for d in group)
            lines.append(f"{label}×{len(group)}  {remaining:.0f}s")
        return lines
