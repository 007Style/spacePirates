"""combat/space_combat.py — Real-time space combat engine."""
from __future__ import annotations
import pygame
import math
import random
from entities.ship       import Ship
from entities.projectile import Projectile
from combat.status_effects import make_effect
from combat.drones       import DroneSystem, DRONE_TYPES
from settings import SCREEN_WIDTH, SCREEN_HEIGHT, DANGER, SUCCESS, WARNING, WHITE, DARK_BG


# ── Starfield ─────────────────────────────────────────────────────────────────
class Starfield:
    """Rich parallax star background: many star layers, distant galaxy clusters,
    nebula wash, and animated twinkle on bright foreground stars."""

    # (count, speed, size_range, color_range_lo, color_range_hi, twinkle)
    LAYERS = [
        # Far background — faint blue-grey dust
        {"count": 200, "speed": 0.02, "size": 1, "color": (55, 55, 75),  "twinkle": False},
        # Mid-far — slightly brighter, slight blue tint
        {"count": 150, "speed": 0.05, "size": 1, "color": (90, 90, 120), "twinkle": False},
        # Mid — warm white-grey
        {"count": 100, "speed": 0.12, "size": 1, "color": (160, 160, 190), "twinkle": False},
        # Near — slightly larger, twinkle
        {"count": 60,  "speed": 0.22, "size": 2, "color": (210, 210, 240), "twinkle": True},
        # Foreground bright stars — occasional large glow
        {"count": 18,  "speed": 0.40, "size": 3, "color": (240, 240, 255), "twinkle": True},
    ]

    def __init__(self, seed: int = 42):
        rng = random.Random(seed)
        self._stars: list[dict] = []
        TILE = 4096
        for layer in self.LAYERS:
            for _ in range(layer["count"]):
                # Give each star a slight color variation
                base = layer["color"]
                var  = rng.randint(-18, 18)
                col  = tuple(max(0, min(255, c + var)) for c in base)
                self._stars.append({
                    "wx":     rng.uniform(0, TILE),
                    "wy":     rng.uniform(0, TILE),
                    "speed":  layer["speed"],
                    "size":   layer["size"],
                    "color":  col,
                    "tile":   TILE,
                    "twinkle": layer["twinkle"],
                    "phase":  rng.uniform(0, 6.28),  # twinkle phase offset
                })

        # ── Distant galaxy blobs (very slow, behind everything) ──────────────
        self._galaxies: list[dict] = []
        g_rng = random.Random(seed + 9999)
        GTILE = 8192
        GALAXY_COLORS = [
            (60, 40, 80),   # purple
            (30, 50, 90),   # blue
            (80, 40, 20),   # amber
            (20, 70, 70),   # teal
            (70, 30, 30),   # deep red
        ]
        for _ in range(7):
            col = g_rng.choice(GALAXY_COLORS)
            self._galaxies.append({
                "wx":     g_rng.uniform(0, GTILE),
                "wy":     g_rng.uniform(0, GTILE),
                "rx":     g_rng.randint(120, 260),   # ellipse x-radius
                "ry":     g_rng.randint(50, 120),    # ellipse y-radius
                "angle":  g_rng.uniform(0, 3.14),
                "alpha":  g_rng.randint(14, 30),
                "color":  col,
                "speed":  0.008,
                "tile":   GTILE,
            })

        # ── Nebula wash layer (very faint, large patches) ────────────────────
        self._nebula_wash: list[dict] = []
        n_rng = random.Random(seed + 5555)
        NTILE = 6000
        NEBULA_COLS = [
            (40, 0, 80),    # deep violet
            (0, 30, 80),    # indigo
            (0, 60, 60),    # teal
            (80, 20, 0),    # dark red
        ]
        for _ in range(5):
            col = n_rng.choice(NEBULA_COLS)
            self._nebula_wash.append({
                "wx":    n_rng.uniform(0, NTILE),
                "wy":    n_rng.uniform(0, NTILE),
                "r":     n_rng.randint(220, 480),
                "alpha": n_rng.randint(8, 22),
                "color": col,
                "speed": 0.015,
                "tile":  NTILE,
            })

        # Pre-build nebula surfaces (expensive; done once)
        self._nebula_surfs: list[tuple] = []
        for n in self._nebula_wash:
            r = n["r"]
            surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*n["color"], n["alpha"]), (r, r), r)
            self._nebula_surfs.append((surf, n))

        # Pre-build galaxy surfaces
        self._galaxy_surfs: list[tuple] = []
        for g in self._galaxies:
            rx, ry = g["rx"], g["ry"]
            gsurf = pygame.Surface((rx * 2 + 4, ry * 2 + 4), pygame.SRCALPHA)
            pygame.draw.ellipse(gsurf, (*g["color"], g["alpha"]),
                                (2, 2, rx * 2, ry * 2))
            # Inner brighter core
            core_a = min(255, g["alpha"] * 3)
            cx2, cy2 = rx + 2, ry + 2
            pygame.draw.ellipse(gsurf, (*g["color"], core_a),
                                (cx2 - rx // 4, cy2 - ry // 4,
                                 rx // 2, ry // 2))
            self._galaxy_surfs.append((gsurf, g))

        self._time = 0.0  # for twinkle animation

    def update(self, dt: float) -> None:
        self._time += dt

    def draw(self, surface: pygame.Surface, cam_x: float, cam_y: float) -> None:
        sw, sh = surface.get_size()

        # ── 1. Nebula wash (deepest layer) ───────────────────────────────────
        for surf, n in self._nebula_surfs:
            r = n["r"]
            sx = (n["wx"] - cam_x * n["speed"]) % n["tile"]
            sy = (n["wy"] - cam_y * n["speed"]) % n["tile"]
            for ddx in range(-1, 2):
                for ddy in range(-1, 2):
                    px = int(sx + ddx * n["tile"]) - r
                    py = int(sy + ddy * n["tile"]) - r
                    if -r * 2 < px < sw + r * 2 and -r * 2 < py < sh + r * 2:
                        surface.blit(surf, (px, py))

        # ── 2. Distant galaxy clusters ────────────────────────────────────────
        for surf, g in self._galaxy_surfs:
            rx, ry = g["rx"], g["ry"]
            sx = (g["wx"] - cam_x * g["speed"]) % g["tile"]
            sy = (g["wy"] - cam_y * g["speed"]) % g["tile"]
            for ddx in range(-1, 2):
                for ddy in range(-1, 2):
                    px = int(sx + ddx * g["tile"]) - rx - 2
                    py = int(sy + ddy * g["tile"]) - ry - 2
                    if (-rx * 2 < px < sw + rx * 2 and
                            -ry * 2 < py < sh + ry * 2):
                        surface.blit(surf, (px, py))

        # ── 3. Stars (all layers) ─────────────────────────────────────────────
        for s in self._stars:
            sx = (s["wx"] - cam_x * s["speed"]) % s["tile"]
            sy = (s["wy"] - cam_y * s["speed"]) % s["tile"]
            for ddx in range(-1, 2):
                for ddy in range(-1, 2):
                    px = int(sx + ddx * s["tile"])
                    py = int(sy + ddy * s["tile"])
                    if -4 <= px <= sw + 4 and -4 <= py <= sh + 4:
                        col = s["color"]
                        # Twinkle: pulse brightness on foreground stars
                        if s["twinkle"]:
                            t = (math.sin(self._time * 2.5 + s["phase"]) + 1) * 0.5
                            col = tuple(int(c * (0.55 + 0.45 * t)) for c in col)
                        sz = s["size"]
                        if sz == 1:
                            surface.set_at((px, py), col)
                        elif sz == 2:
                            pygame.draw.circle(surface, col, (px, py), 1)
                        else:
                            # Large foreground star: draw with a soft cross-glare
                            pygame.draw.circle(surface, col, (px, py), 2)
                            glare_col = tuple(min(255, c + 60) for c in col)
                            for gx2, gy2 in [(px - 3, py), (px + 3, py),
                                            (px, py - 3), (px, py + 3)]:
                                if 0 <= gx2 < sw and 0 <= gy2 < sh:
                                    surface.set_at((gx2, gy2), glare_col)

# Optional particle system reference (set by Game when combat is created)
_particle_system = None

def set_particle_system(ps) -> None:
    global _particle_system
    _particle_system = ps


# ── Sector Environment Objects ────────────────────────────────────────────────

class AsteroidField:
    """4–8 asteroid obstacles that provide cover and drop resources on contact."""

    # Mineral types: (name, base_color, loot_bonus, glow_color)
    MINERAL_TYPES = [
        ("iron",     (75,  78,  88),  "metal",   (140, 150, 170), 55),   # blue-grey iron
        ("iron",     (82,  72,  60),  "metal",   (150, 140, 110), 45),   # brown iron ore
        ("copper",   (110, 85,  40),  "credits", (220, 170,  60), 40),   # copper/gold
        ("crystal",  (50,  80, 130),  "metal",   ( 80, 160, 255), 30),   # ice-blue crystal
        ("void",     (75,  40, 110),  "credits", (180,  80, 255), 15),   # rare void rock
    ]
    # Rarity weights for mineral type
    _MINERAL_WEIGHTS = [55, 45, 40, 30, 15]

    def __init__(self, seed: int = 0):
        rng = random.Random(seed)
        count = rng.randint(5, 10)
        self.asteroids: list[dict] = []
        # Cumulative weights for mineral selection
        _pop  = self.MINERAL_TYPES
        _wsum = sum(self._MINERAL_WEIGHTS)
        for _ in range(count):
            # Pick mineral type by weight
            r_pick = rng.randint(0, _wsum - 1)
            acc = 0
            mtype_idx = 0
            for mi, w in enumerate(self._MINERAL_WEIGHTS):
                acc += w
                if r_pick < acc:
                    mtype_idx = mi
                    break
            mname, mbase, mloot, mglow, _ = _pop[mtype_idx]
            # Vary the base color slightly per asteroid
            var = rng.randint(-18, 18)
            base_col = tuple(max(0, min(255, c + var)) for c in mbase)
            self.asteroids.append({
                "x":         rng.uniform(-1800, 1800),
                "y":         rng.uniform(-1200, 1200),
                "radius":    rng.uniform(18, 65),
                "color":     base_col,
                "glow_col":  mglow,
                "mineral":   mname,
                "loot_type": mloot,
                "collected": False,
                "rot":       rng.uniform(0, 360),
                "rot_spd":   rng.uniform(-8.0, 8.0),
                # 20-point jagged shape for better detail
                "shape_pts": [rng.uniform(0.55, 1.0) for _ in range(20)],
                "vx":        rng.uniform(-12, 12),
                "vy":        rng.uniform(-12, 12),
                # secondary highlight angle offset (per-asteroid variety)
                "hl2_off":   rng.uniform(0, math.pi * 2),
                # small dust ring radius multiplier
                "dust_r":    rng.uniform(1.12, 1.28),
            })

    def update(self, dt: float) -> None:
        """Rotate and drift asteroids."""
        WRAP = 2200
        self._anim_t = getattr(self, "_anim_t", 0.0) + dt
        for ast in self.asteroids:
            ast["rot"] = (ast["rot"] + ast["rot_spd"] * dt) % 360
            ast["x"] += ast["vx"] * dt
            ast["y"] += ast["vy"] * dt
            if abs(ast["x"]) > WRAP: ast["vx"] *= -1
            if abs(ast["y"]) > WRAP: ast["vy"] *= -1

    def draw(self, surface: pygame.Surface, ox: float, oy: float) -> None:
        sw, sh = surface.get_size()
        for ast in self.asteroids:
            sx = int(ast["x"] + ox)
            sy = int(ast["y"] + oy)
            r  = int(ast["radius"])
            # Skip off-screen
            if not (-r - 30 < sx < sw + r + 30 and -r - 30 < sy < sh + r + 30):
                continue
            col     = ast["color"]
            darker  = tuple(max(0, c - 45) for c in col)
            shadow  = tuple(max(0, c - 65) for c in col)
            lighter = tuple(min(255, c + 55) for c in col)
            highlight = tuple(min(255, c + 90) for c in col)

            # ── Dust ring / atmosphere halo (drawn behind everything) ─────────
            dust_r_mult = ast.get("dust_r", 1.18)
            dust_r = int(r * dust_r_mult)
            _anim_t = getattr(self, "_anim_t", 0.0)
            dust_alpha = max(12, int(20 + 8 * math.sin(_anim_t * 0.6 + float(id(ast) & 0xFF))))
            dust_surf = pygame.Surface((dust_r * 2 + 4, dust_r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(dust_surf, (*shadow, dust_alpha),
                               (dust_r + 2, dust_r + 2), dust_r)
            surface.blit(dust_surf, (sx - dust_r - 2, sy - dust_r - 2),
                         special_flags=pygame.BLEND_ALPHA_SDL2)

            # ── Rotating jagged polygon body ─────────────────────────────────
            shape_pts = ast.get("shape_pts", [1.0] * 20)
            rot_rad   = math.radians(ast.get("rot", 0))
            n_pts     = len(shape_pts)
            # Drop shadow polygon (slightly offset)
            shadow_pts = []
            for i, frac in enumerate(shape_pts):
                a = rot_rad + (i / n_pts) * 2 * math.pi
                shadow_pts.append((sx + 6 + int(r * frac * math.cos(a)),
                                   sy + 6 + int(r * frac * math.sin(a))))
            if len(shadow_pts) >= 3:
                pygame.draw.polygon(surface, shadow, shadow_pts)
            # Main body polygon
            body_pts = []
            for i, frac in enumerate(shape_pts):
                a = rot_rad + (i / n_pts) * 2 * math.pi
                body_pts.append((sx + int(r * frac * math.cos(a)),
                                 sy + int(r * frac * math.sin(a))))
            if len(body_pts) >= 3:
                pygame.draw.polygon(surface, darker, body_pts)
                # Inner slightly lighter fill (smaller scale)
                inner_pts = [(sx + int(r * f * 0.75 * math.cos(rot_rad + (i / n_pts) * 2 * math.pi)),
                              sy + int(r * f * 0.75 * math.sin(rot_rad + (i / n_pts) * 2 * math.pi)))
                             for i, f in enumerate(shape_pts)]
                pygame.draw.polygon(surface, col, inner_pts)
                # Rim highlight edge
                pygame.draw.polygon(surface, lighter, body_pts, 2)

            # ── Craters (rotate with body) ────────────────────────────────────
            rng_c = random.Random(id(ast) & 0xFFFF)
            num_craters = max(2, r // 10)
            for _ in range(num_craters):
                angle_c = rng_c.uniform(0, 2 * math.pi) + rot_rad
                dist_c  = rng_c.uniform(0.1, 0.55) * r
                cr      = rng_c.randint(2, max(3, r // 7))
                cx_     = int(sx + dist_c * math.cos(angle_c))
                cy_     = int(sy + dist_c * math.sin(angle_c))
                pygame.draw.circle(surface, shadow, (cx_, cy_), cr)
                pygame.draw.circle(surface, darker, (cx_, cy_), max(1, cr - 1), 1)
                # Small specular dot inside crater
                pygame.draw.circle(surface, col, (cx_ - 1, cy_ - 1), max(1, cr // 3))

            # ── Primary specular highlight (upper-left) ────────────────────────
            hl_angle = rot_rad - math.pi * 0.75
            hl_dist  = r * 0.35
            hl_x = sx + int(hl_dist * math.cos(hl_angle))
            hl_y = sy + int(hl_dist * math.sin(hl_angle))
            pygame.draw.circle(surface, highlight, (hl_x, hl_y), max(2, r // 5))
            pygame.draw.circle(surface, (255, 255, 255), (hl_x, hl_y), max(1, r // 9))

            # ── Secondary highlight (opposite side, dimmer) ────────────────────
            hl2_angle = rot_rad + math.pi * 0.4 + ast.get("hl2_off", 1.2)
            hl2_x = sx + int(r * 0.45 * math.cos(hl2_angle))
            hl2_y = sy + int(r * 0.45 * math.sin(hl2_angle))
            pygame.draw.circle(surface, lighter, (hl2_x, hl2_y), max(1, r // 8))

            # ── Satellite pebbles for large asteroids ─────────────────────────
            if r > 32:
                pebble_rng = random.Random((id(ast) & 0xFFFF) + 1)
                for _ in range(6):
                    ang_p = pebble_rng.uniform(0, 2 * math.pi) + rot_rad * 0.3
                    d_p   = r + pebble_rng.uniform(5, 18)
                    pr    = pebble_rng.randint(2, 6)
                    px_   = sx + int(d_p * math.cos(ang_p))
                    py_   = sy + int(d_p * math.sin(ang_p))
                    pygame.draw.circle(surface, shadow, (px_ + 2, py_ + 2), pr)
                    pygame.draw.circle(surface, darker, (px_, py_), pr)
                    pygame.draw.circle(surface, col, (px_, py_), pr, 1)

            # ── Mineral glow + glint on uncollected asteroids ─────────────────
            if not ast["collected"]:
                glow_col = ast.get("glow_col", (220, 200, 120))
                mineral  = ast.get("mineral", "iron")
                _anim_t  = getattr(self, "_anim_t", 0.0)

                # Crystal/void: outer glow halo
                if mineral in ("crystal", "void"):
                    halo_r = r + 8
                    halo_s = pygame.Surface((halo_r * 2, halo_r * 2), pygame.SRCALPHA)
                    halo_alpha = max(10, int(25 + 12 * math.sin(_anim_t * 2.5 + float(id(ast) & 0xFF))))
                    pygame.draw.circle(halo_s, (*glow_col, halo_alpha),
                                       (halo_r, halo_r), halo_r)
                    surface.blit(halo_s, (sx - halo_r, sy - halo_r))

                # Mineral veins inside body
                vein_col_map = {"copper": (220, 170, 60), "crystal": (120, 200, 255),
                                "void": (200, 100, 255)}
                vein_col = vein_col_map.get(mineral, tuple(min(255, c + 50) for c in col))
                vein_rng = random.Random((id(ast) & 0xFFFF) + 99)
                for _ in range(max(1, r // 15)):
                    va  = vein_rng.uniform(0, 2 * math.pi)
                    vd  = vein_rng.uniform(0.1, 0.45) * r
                    vlen = vein_rng.uniform(0.08, 0.20) * r
                    vx1 = int(sx + vd * math.cos(va + rot_rad))
                    vy1 = int(sy + vd * math.sin(va + rot_rad))
                    vx2 = int(vx1 + vlen * math.cos(va + rot_rad + 0.5))
                    vy2 = int(vy1 + vlen * math.sin(va + rot_rad + 0.5))
                    pygame.draw.line(surface, vein_col, (vx1, vy1), (vx2, vy2), 1)

                # Glint dot (mineral-coloured)
                glint_a = rot_rad + 0.8
                gx2 = sx + int(r * 0.55 * math.cos(glint_a))
                gy2 = sy + int(r * 0.55 * math.sin(glint_a))
                pygame.draw.circle(surface, glow_col, (gx2, gy2), 3)
                pygame.draw.circle(surface, (255, 255, 240), (gx2, gy2), 1)

                # Mineral label for large asteroids
                if r > 38:
                    try:
                        gi_f = pygame.font.SysFont("monospace", 9)
                        mineral_icons = {"iron": "⛏Fe", "copper": "⛏Cu",
                                         "crystal": "✦Ice", "void": "★Void"}
                        gi_t = gi_f.render(mineral_icons.get(mineral, "⛏"), True, glow_col)
                        surface.blit(gi_t, (sx - gi_t.get_width() // 2, sy - r - 14))
                    except Exception:
                        pass

    def check_collect(self, ship, radius_extra: float = 0.0
                      ) -> list[tuple[str, int]]:
        """Returns list of (resource_type, amount) collected this frame."""
        results = []
        for ast in self.asteroids:
            if ast["collected"]:
                continue
            dist = math.hypot(ship.x - ast["x"], ship.y - ast["y"])
            if dist <= ast["radius"] + 40 + radius_extra:
                ast["collected"] = True
                loot_type = ast.get("loot_type", "metal")
                mineral   = ast.get("mineral", "iron")
                # Rarer minerals give more loot
                if mineral == "void":
                    amount = random.randint(30, 60)
                elif mineral == "crystal":
                    amount = random.randint(20, 45)
                elif mineral == "copper":
                    amount = random.randint(15, 35)
                else:
                    amount = random.randint(10, 30)
                results.append((loot_type, amount))
        return results

    def deflect_chance(self, ship, base_chance: float = 0.30) -> float:
        """Returns the deflection chance for a ship near any asteroid (cover bonus)."""
        for ast in self.asteroids:
            dist = math.hypot(ship.x - ast["x"], ship.y - ast["y"])
            if dist <= ast["radius"] * 1.2:
                return base_chance
        return 0.0


class CometTrail:
    """A comet that streaks slowly across the combat arena."""

    SPEED = 90.0   # pixels/sec

    def __init__(self, seed: int = 0):
        rng = random.Random(seed + 1000)
        self.x   = rng.uniform(-2000, 2000)
        self.y   = rng.uniform(-1500, 1500)
        self.vx  = rng.uniform(-1, 1) * self.SPEED
        self.vy  = rng.uniform(-1, 1) * self.SPEED
        norm = math.hypot(self.vx, self.vy) or 1
        self.vx  = (self.vx / norm) * self.SPEED
        self.vy  = (self.vy / norm) * self.SPEED
        self._trail: list[tuple[float, float]] = []
        self._color = (200, 220, 255)

    def update(self, dt: float) -> None:
        self._trail.append((self.x, self.y))
        if len(self._trail) > 30:
            self._trail.pop(0)
        self.x += self.vx * dt
        self.y += self.vy * dt
        # Wrap around a large arena
        WRAP = 2500
        if abs(self.x) > WRAP: self.x = -self.x * 0.9
        if abs(self.y) > WRAP: self.y = -self.y * 0.9

    def draw(self, surface: pygame.Surface, ox: float, oy: float) -> None:
        # Draw fading trail
        for i, (tx, ty) in enumerate(self._trail):
            alpha = int(180 * i / max(len(self._trail), 1))
            frac  = i / max(len(self._trail), 1)
            col   = tuple(int(c * frac) for c in self._color)
            r     = max(1, int(3 * frac))
            pygame.draw.circle(surface, col,
                               (int(tx + ox), int(ty + oy)), r)
        # Head glow
        sx, sy = int(self.x + ox), int(self.y + oy)
        pygame.draw.circle(surface, self._color, (sx, sy), 5)
        pygame.draw.circle(surface, (255, 255, 255), (sx, sy), 2)


class NebulaCloud:
    """A soft nebula patch painted on the background."""

    def __init__(self, seed: int = 0, count: int = 5):
        rng = random.Random(seed + 2000)
        self.patches: list[dict] = []
        for _ in range(count):
            hue_choice = rng.choice(["purple", "blue", "teal", "red"])
            if hue_choice == "purple":
                col = (rng.randint(60, 120), 0, rng.randint(100, 180))
            elif hue_choice == "blue":
                col = (0, rng.randint(40, 80), rng.randint(140, 220))
            elif hue_choice == "teal":
                col = (0, rng.randint(120, 180), rng.randint(160, 220))
            else:
                col = (rng.randint(160, 220), rng.randint(20, 60), 0)
            self.patches.append({
                "x":      rng.uniform(-2000, 2000),
                "y":      rng.uniform(-1500, 1500),
                "radius": rng.randint(80, 240),
                "color":  col,
                "alpha":  rng.randint(18, 45),
            })

    def is_inside(self, x: float, y: float) -> bool:
        """Return True if world position (x,y) is inside any nebula patch."""
        return any(
            math.hypot(x - p["x"], y - p["y"]) < p["radius"]
            for p in self.patches
        )

    def apply_slow(self, ships: list) -> None:
        """Apply 0.55× speed slow to any ship inside a nebula patch.
        Removes the slow when the ship exits."""
        for ship in ships:
            if self.is_inside(ship.x, ship.y):
                ship._nebula_slow = 0.55
            else:
                ship._nebula_slow = 1.0

    def draw(self, surface: pygame.Surface, ox: float, oy: float,
             active_ships: list | None = None) -> None:
        for p in self.patches:
            sx = int(p["x"] + ox)
            sy = int(p["y"] + oy)
            r  = p["radius"]
            sw, sh = surface.get_size()
            # Only draw if on screen
            if -r < sx < sw + r and -r < sy < sh + r:
                neb = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
                # Base cloud layer
                pygame.draw.circle(neb, (*p["color"], p["alpha"]), (r, r), r)
                # Inner brighter core (depth effect)
                if r > 40:
                    inner_col = tuple(min(255, c + 20) for c in p["color"])
                    pygame.draw.circle(neb, (*inner_col, p["alpha"] // 2),
                                       (r, r), r * 2 // 3)
                # Ship-present glow: brighten patch when any ship is inside
                if active_ships and any(
                        math.hypot(s.x - p["x"], s.y - p["y"]) < r
                        for s in active_ships):
                    glow_col = tuple(min(255, c + 40) for c in p["color"])
                    pygame.draw.circle(neb, (*glow_col, 30), (r, r), r)
                surface.blit(neb, (sx - r, sy - r))


class SpaceDebris:
    """Floating space junk: old hull plates, fuel canisters, cargo pods.
    Drifts slowly across the arena; player can fly through to collect resources."""

    DEBRIS_TYPES = [
        # (label, color_base, loot_type, loot_min, loot_max, shape)
        ("hull plate",   (80,  90, 100), "metal",    8,  20, "rect"),
        ("fuel drum",    (120, 160, 80), "fuel",     5,  15, "circle"),
        ("cargo pod",    (140, 110, 60), "credits", 20,  60, "hexagon"),
        ("scrap pile",   (90,  80,  75), "metal",   15,  35, "jagged"),
        ("supply crate", (60, 100, 140), "supplies", 5,  12, "rect"),
        # New debris types
        ("ammo box",     (160, 120,  50), "supplies", 8,  18, "rect"),
        ("engine pod",   (60,  80, 120), "metal",   20,  45, "circle"),
        ("data core",    (180, 60, 200), "credits", 40, 120, "hexagon"),
        ("torn hull",    (70,  60,  60), "metal",   10,  30, "jagged"),
        ("coolant tank", (40, 180, 160), "fuel",    10,  25, "circle"),
    ]

    def __init__(self, seed: int = 0, count: int = 6):
        rng = random.Random(seed + 5000)
        self.pieces: list[dict] = []
        for _ in range(count):
            dtype = rng.choice(self.DEBRIS_TYPES)
            r     = rng.uniform(-0.4, 0.4)        # slight spin speed rad/s
            self.pieces.append({
                "x":        rng.uniform(-1600, 1600),
                "y":        rng.uniform(-1100, 1100),
                "vx":       rng.uniform(-18, 18),
                "vy":       rng.uniform(-18, 18),
                "rot":      rng.uniform(0, 360),
                "rot_spd":  r,
                "size":     rng.randint(8, 18),
                "type":     dtype,
                "collected": False,
                "glow_t":   0.0,   # flicker timer for "nearby" hint
            })

    def update(self, dt: float) -> None:
        for p in self.pieces:
            if p["collected"]:
                continue
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["rot"] = (p["rot"] + math.degrees(p["rot_spd"]) * dt) % 360
            WRAP = 2200
            if abs(p["x"]) > WRAP: p["vx"] *= -1
            if abs(p["y"]) > WRAP: p["vy"] *= -1

    def check_collect(self, ship, collect_r: float = 30.0) -> list[tuple[str, int]]:
        results = []
        for p in self.pieces:
            if p["collected"]:
                continue
            dist = math.hypot(ship.x - p["x"], ship.y - p["y"])
            if dist < collect_r + p["size"]:
                p["collected"] = True
                lbl, col, rtype, rmin, rmax, shape = p["type"]
                amount = random.randint(rmin, rmax)
                results.append((rtype, amount))
        return results

    def draw(self, surface: pygame.Surface, ox: float, oy: float,
             player_x: float = 0.0, player_y: float = 0.0) -> None:
        sw, sh = surface.get_size()
        for p in self.pieces:
            if p["collected"]:
                continue
            sx = int(p["x"] + ox)
            sy = int(p["y"] + oy)
            if not (-60 < sx < sw + 60 and -60 < sy < sh + 60):
                continue
            lbl, col, rtype, rmin, rmax, shape = p["type"]
            sz  = p["size"]
            dark = tuple(max(0, c - 40) for c in col)
            bright = tuple(min(255, c + 60) for c in col)

            # ── proximity glow ────────────────────────────────────────────
            dist = math.hypot(player_x - p["x"], player_y - p["y"])
            near = dist < 120
            if near:
                # soft green halo
                halo = pygame.Surface((sz * 4, sz * 4), pygame.SRCALPHA)
                pygame.draw.circle(halo, (80, 255, 120, 35), (sz * 2, sz * 2), sz * 2)
                surface.blit(halo, (sx - sz * 2, sy - sz * 2))

            # ── shape ──────────────────────────────────────────────────────
            angle = p["rot"]
            if shape == "rect":
                # Rotated rectangle (hull plate / crate)
                pts = []
                for dx, dy in [(-sz, -sz // 2), (sz, -sz // 2),
                                (sz, sz // 2), (-sz, sz // 2)]:
                    ra = math.radians(angle)
                    rx = dx * math.cos(ra) - dy * math.sin(ra)
                    ry = dx * math.sin(ra) + dy * math.cos(ra)
                    pts.append((sx + rx, sy + ry))
                pygame.draw.polygon(surface, dark, pts)
                pygame.draw.polygon(surface, col, pts, 2)
                # Rivet dots
                for rv in pts[:2]:
                    pygame.draw.circle(surface, bright, (int(rv[0]), int(rv[1])), 1)

            elif shape == "circle":
                # Fuel drum — circle with band lines
                pygame.draw.circle(surface, dark, (sx, sy), sz)
                pygame.draw.circle(surface, col, (sx, sy), sz, 2)
                # Horizontal band
                bx = int(sz * 0.7)
                pygame.draw.line(surface, bright, (sx - bx, sy), (sx + bx, sy), 1)
                # Valve dot
                pygame.draw.circle(surface, bright, (sx, sy - sz // 2), 2)

            elif shape == "hexagon":
                # 6-sided cargo pod
                pts = []
                for i in range(6):
                    a = math.radians(angle + i * 60)
                    pts.append((sx + sz * math.cos(a), sy + sz * math.sin(a)))
                pygame.draw.polygon(surface, dark, pts)
                pygame.draw.polygon(surface, col, pts, 2)
                # Inner cross
                for a in [0, 60, 120]:
                    ra = math.radians(angle + a)
                    pygame.draw.line(surface, bright,
                                     (sx - int(sz * 0.5 * math.cos(ra)),
                                      sy - int(sz * 0.5 * math.sin(ra))),
                                     (sx + int(sz * 0.5 * math.cos(ra)),
                                      sy + int(sz * 0.5 * math.sin(ra))), 1)

            else:  # jagged scrap
                rng = random.Random(id(p) & 0xFFFF)
                pts = []
                for i in range(7):
                    a  = math.radians(angle + i * (360 / 7))
                    r2 = sz * rng.uniform(0.5, 1.0)
                    pts.append((sx + r2 * math.cos(a), sy + r2 * math.sin(a)))
                pygame.draw.polygon(surface, dark, pts)
                pygame.draw.polygon(surface, col, pts, 1)

            # ── special glow for valuable junk (data core) ───────────────
            if lbl == "data core":
                halo2 = pygame.Surface((sz * 6, sz * 6), pygame.SRCALPHA)
                pygame.draw.circle(halo2, (180, 60, 200, 30), (sz * 3, sz * 3), sz * 3)
                surface.blit(halo2, (sx - sz * 3, sy - sz * 3))

            # ── loot label + type when nearby ─────────────────────────────
            if near:
                try:
                    fnt = pygame.font.SysFont("monospace", 9)
                    loot_icons = {"metal": "M", "fuel": "F", "credits": "$", "supplies": "S"}
                    icon = loot_icons.get(rtype, "?")
                    loot_str = f"[{icon}] {lbl[:9]}"
                    lt = fnt.render(loot_str, True, (190, 255, 190))
                    # Dark backdrop for legibility
                    bk = pygame.Surface((lt.get_width() + 4, lt.get_height()), pygame.SRCALPHA)
                    bk.fill((0, 0, 0, 100))
                    surface.blit(bk, (sx - lt.get_width() // 2 - 2, sy - sz - 16))
                    surface.blit(lt, (sx - lt.get_width() // 2, sy - sz - 15))
                except Exception:
                    pass


# ── Space Wreckage ────────────────────────────────────────────────────────────
class SpaceWreckage:
    """Large destroyed ship hull sections drifting through combat space.
    They serve as obstacles (block bullets + ships) and yield metal when mined."""

    # Hull section colour pools by ship class
    _WRECK_COLS = [
        (55,  60,  75),   # dark steel
        (70,  50,  40),   # burnt orange-brown
        (45,  55,  70),   # gunmetal blue-grey
        (80,  70,  60),   # weathered ochre
        (35,  40,  55),   # void black-blue
    ]

    def __init__(self, seed: int = 0, count: int = 0):
        rng = random.Random(seed + 8888)
        self.pieces: list[dict] = []
        for _ in range(count):
            col = rng.choice(self._WRECK_COLS)
            # Randomised wreck polygon: 6–9 sides, large size
            n_pts = rng.randint(6, 9)
            shape = [rng.uniform(0.45, 0.95) for _ in range(n_pts)]
            self.pieces.append({
                "x":        rng.uniform(-2000, 2000),
                "y":        rng.uniform(-1400, 1400),
                "radius":   rng.randint(22, 52),
                "rot":      rng.uniform(0, 360),
                "rot_spd":  rng.uniform(-3.0, 3.0),
                "vx":       rng.uniform(-8, 8),
                "vy":       rng.uniform(-8, 8),
                "color":    col,
                "shape":    shape,
                "collected": False,
                # Wreck detail flavour
                "has_window": rng.random() < 0.4,
                "damage_mark": rng.randint(0, 3),
            })

    def update(self, dt: float) -> None:
        WRAP = 2400
        for p in self.pieces:
            if p["collected"]:
                continue
            p["x"]   += p["vx"] * dt
            p["y"]   += p["vy"] * dt
            p["rot"]  = (p["rot"] + p["rot_spd"] * dt) % 360
            if abs(p["x"]) > WRAP: p["vx"] *= -1
            if abs(p["y"]) > WRAP: p["vy"] *= -1

    def check_collect(self, ship, collect_r: float = 35.0) -> list[tuple[str, int]]:
        results = []
        for p in self.pieces:
            if p["collected"]:
                continue
            dist = math.hypot(ship.x - p["x"], ship.y - p["y"])
            if dist < collect_r + p["radius"]:
                p["collected"] = True
                amount = random.randint(25, 80)
                results.append(("metal", amount))
        return results

    def draw(self, surface: pygame.Surface, ox: float, oy: float,
             player_x: float = 0.0, player_y: float = 0.0) -> None:
        sw, sh = surface.get_size()
        for p in self.pieces:
            if p["collected"]:
                continue
            sx = int(p["x"] + ox)
            sy = int(p["y"] + oy)
            r  = p["radius"]
            if not (-r - 30 < sx < sw + r + 30 and -r - 30 < sy < sh + r + 30):
                continue

            col   = p["color"]
            dark  = tuple(max(0, c - 35) for c in col)
            light = tuple(min(255, c + 45) for c in col)
            rot_r = math.radians(p["rot"])
            shape = p["shape"]
            n_pts = len(shape)

            # ── Main wreck body ───────────────────────────────────────────────
            body = []
            for i, frac in enumerate(shape):
                a = rot_r + (i / n_pts) * 2 * math.pi
                body.append((sx + int(r * frac * math.cos(a)),
                              sy + int(r * frac * math.sin(a))))
            if len(body) >= 3:
                # Drop shadow
                shadow_pts = [(x + 5, y + 5) for x, y in body]
                pygame.draw.polygon(surface, (10, 10, 15), shadow_pts)
                # Main fill
                pygame.draw.polygon(surface, dark, body)
                # Lighter inner fill (75% scale)
                inner = [(sx + int(r * frac * 0.72 * math.cos(rot_r + (i / n_pts) * 2 * math.pi)),
                          sy + int(r * frac * 0.72 * math.sin(rot_r + (i / n_pts) * 2 * math.pi)))
                         for i, frac in enumerate(shape)]
                pygame.draw.polygon(surface, col, inner)
                # Outline
                pygame.draw.polygon(surface, light, body, 1)

            # ── Panel / armour lines ──────────────────────────────────────────
            panel_rng = random.Random(id(p) & 0xFFFF)
            for _ in range(3):
                pa = rot_r + panel_rng.uniform(0, 2 * math.pi)
                pd = panel_rng.uniform(0.1, 0.6) * r
                pl = panel_rng.uniform(0.15, 0.35) * r
                px1 = int(sx + pd * math.cos(pa))
                py1 = int(sy + pd * math.sin(pa))
                px2 = int(px1 + pl * math.cos(pa + 1.5))
                py2 = int(py1 + pl * math.sin(pa + 1.5))
                pygame.draw.line(surface, light, (px1, py1), (px2, py2), 1)

            # ── Blown-out window (dark square) ────────────────────────────────
            if p.get("has_window"):
                wa = rot_r + 0.4
                wd = r * 0.4
                wx = sx + int(wd * math.cos(wa))
                wy = sy + int(wd * math.sin(wa))
                ws = max(3, r // 6)
                window_r = pygame.Rect(wx - ws, wy - ws, ws * 2, ws * 2)
                pygame.draw.rect(surface, (15, 20, 35), window_r)
                pygame.draw.rect(surface, (40, 60, 80), window_r, 1)

            # ── Burn/scorch marks ─────────────────────────────────────────────
            dm = p.get("damage_mark", 0)
            for di in range(dm):
                da = rot_r + di * 1.8
                dd = r * 0.35
                scorch_x = int(sx + dd * math.cos(da))
                scorch_y = int(sy + dd * math.sin(da))
                scorch_r = max(2, r // 8)
                ssurf = pygame.Surface((scorch_r * 2, scorch_r * 2), pygame.SRCALPHA)
                pygame.draw.circle(ssurf, (40, 20, 10, 80), (scorch_r, scorch_r), scorch_r)
                surface.blit(ssurf, (scorch_x - scorch_r, scorch_y - scorch_r))

            # ── Nearby pickup hint ────────────────────────────────────────────
            dist = math.hypot(player_x - p["x"], player_y - p["y"])
            if dist < 150:
                try:
                    fnt = pygame.font.SysFont("monospace", 9)
                    lt  = fnt.render("[M] wreckage", True, (160, 200, 160))
                    bk  = pygame.Surface((lt.get_width() + 4, lt.get_height()), pygame.SRCALPHA)
                    bk.fill((0, 0, 0, 100))
                    surface.blit(bk, (sx - lt.get_width() // 2 - 2, sy - r - 16))
                    surface.blit(lt, (sx - lt.get_width() // 2, sy - r - 15))
                except Exception:
                    pass


# ── Space Mines ───────────────────────────────────────────────────────────────
class SpaceMineField:
    """Stationary proximity mines scattered around the combat arena.
    Any ship (player or enemy) that flies within trigger_r triggers an explosion
    dealing damage and knocking the ship back.  Mines pulse red while armed;
    blink fast when just triggered."""

    MINE_DMG      = 30.0   # hull damage on trigger
    TRIGGER_R     = 38     # pixels
    BLINK_TIME    = 0.35   # seconds blink/flash after trigger before disappearing

    def __init__(self, seed: int = 0, count: int = 0):
        rng   = random.Random(seed + 7777)
        self.mines: list[dict] = []
        for _ in range(count):
            self.mines.append({
                "x":        rng.uniform(-1600, 1600),
                "y":        rng.uniform(-1100, 1100),
                "armed":    True,
                "blink_t":  0.0,   # countdown after trigger before removal
                "pulse":    rng.uniform(0, 6.28),  # phase offset for glow pulse
                "size":     rng.randint(7, 11),
            })

    def update(self, dt: float) -> None:
        for mine in self.mines:
            if mine["armed"]:
                mine["pulse"] += dt * 2.4
            elif mine["blink_t"] > 0:
                mine["blink_t"] -= dt

    def check_trigger(self, ships: list) -> list[tuple]:
        """Returns list of (ship, damage) for every ship that triggered a mine."""
        results = []
        for mine in self.mines:
            if not mine["armed"]:
                continue
            for ship in ships:
                if ship.is_destroyed:
                    continue
                dist = math.hypot(getattr(ship, "x", 0) - mine["x"],
                                  getattr(ship, "y", 0) - mine["y"])
                if dist < self.TRIGGER_R + mine["size"]:
                    mine["armed"]  = False
                    mine["blink_t"] = self.BLINK_TIME
                    results.append((ship, self.MINE_DMG))
        return results

    def draw(self, surface: pygame.Surface, ox: float, oy: float) -> None:
        sw, sh = surface.get_size()
        for mine in self.mines:
            if not mine["armed"] and mine["blink_t"] <= 0:
                continue
            sx = int(mine["x"] + ox)
            sy = int(mine["y"] + oy)
            if not (-30 < sx < sw + 30 and -30 < sy < sh + 30):
                continue
            sz = mine["size"]

            if mine["armed"]:
                # Pulsing red glow
                pulse = (math.sin(mine["pulse"]) + 1) * 0.5
                r_col = (int(180 + 60 * pulse), 20, 20)
                glow_r = sz + int(4 * pulse)
                # Outer glow ring
                gsurf = pygame.Surface((glow_r * 4, glow_r * 4), pygame.SRCALPHA)
                pygame.draw.circle(gsurf, (220, 30, 30, int(40 * pulse)),
                                   (glow_r * 2, glow_r * 2), glow_r * 2)
                surface.blit(gsurf, (sx - glow_r * 2, sy - glow_r * 2),
                             special_flags=pygame.BLEND_ALPHA_SDL2)
                # Mine body — hexagonal shape
                pts = [(sx + sz * math.cos(math.radians(a)),
                        sy + sz * math.sin(math.radians(a)))
                       for a in range(0, 360, 60)]
                pygame.draw.polygon(surface, (50, 50, 55), pts)
                pygame.draw.polygon(surface, r_col, pts, 2)
                # Spikes at each vertex
                for a in range(0, 360, 60):
                    ex = sx + (sz + 4) * math.cos(math.radians(a))
                    ey = sy + (sz + 4) * math.sin(math.radians(a))
                    pygame.draw.line(surface, r_col, (int(sx), int(sy)),
                                     (int(ex), int(ey)), 1)
                # Centre red dot
                pygame.draw.circle(surface, r_col, (sx, sy), max(2, sz // 3))
                # Danger symbol (small !)
                try:
                    mf = pygame.font.SysFont("monospace", 8)
                    mt = mf.render("!", True, (255, 100, 100))
                    surface.blit(mt, (sx - mt.get_width() // 2, sy - sz - 12))
                except Exception:
                    pass
            else:
                # Blinking explosion flash
                bfrac = mine["blink_t"] / self.BLINK_TIME
                ecol  = (int(255 * bfrac), int(120 * bfrac), 20)
                er    = sz + int(18 * bfrac)
                pygame.draw.circle(surface, ecol, (sx, sy), er)
                pygame.draw.circle(surface, (255, 255, 200), (sx, sy), max(1, er // 3))


# ── Enemy AI states ──────────────────────────────────────────────────────────
class AIState:
    PATROL   = "patrol"
    CHASE    = "chase"
    ATTACK   = "attack"
    RETREAT  = "retreat"
    DEAD     = "dead"


class EnemyAI:
    CHASE_RANGE    = 500
    ATTACK_RANGE   = 320
    RETREAT_HP_PCT = 0.20
    PATROL_SPEED   = 55
    MAX_SPEED      = 100   # cap enemy movement speed so they feel manageable
    TURN_SPEED     = 120   # deg/s

    def __init__(self, ship: Ship):
        self.ship       = ship
        self.state      = AIState.PATROL
        self._patrol_target = (ship.x + random.randint(-200, 200),
                               ship.y + random.randint(-200, 200))
        self._fire_cd   = random.uniform(1.0, 2.5)

    def update(self, dt: float, player_ship: Ship) -> list[Projectile]:
        if self.ship.is_destroyed:
            self.state = AIState.DEAD
            return []

        dist = math.hypot(player_ship.x - self.ship.x,
                          player_ship.y - self.ship.y)
        hp_pct = self.ship.hull / max(self.ship.max_hull, 1)

        # State transitions
        if hp_pct <= self.RETREAT_HP_PCT:
            self.state = AIState.RETREAT
        elif dist <= self.ATTACK_RANGE:
            self.state = AIState.ATTACK
        elif dist <= self.CHASE_RANGE:
            self.state = AIState.CHASE
        else:
            self.state = AIState.PATROL

        projectiles = []
        if self.state == AIState.PATROL:
            self._move_toward(*self._patrol_target, dt, speed=self.PATROL_SPEED)
            if math.hypot(self._patrol_target[0] - self.ship.x,
                          self._patrol_target[1] - self.ship.y) < 20:
                self._patrol_target = (
                    self.ship.x + random.randint(-300, 300),
                    self.ship.y + random.randint(-300, 300),
                )

        elif self.state == AIState.CHASE:
            self._move_toward(player_ship.x, player_ship.y, dt)

        elif self.state == AIState.ATTACK:
            # Strafe: circle the player
            angle_to_player = math.atan2(
                player_ship.y - self.ship.y,
                player_ship.x - self.ship.x,
            )
            strafe_angle = angle_to_player + math.pi / 2
            tx = player_ship.x + math.cos(strafe_angle) * 200
            ty = player_ship.y + math.sin(strafe_angle) * 200
            self._move_toward(tx, ty, dt)
            # Fire
            self._fire_cd -= dt
            if self._fire_cd <= 0 and self.ship.weapons:
                self._fire_cd = random.uniform(1.0, 2.0)
                for w in self.ship.weapons:
                    if w.can_fire() and not self.ship.has_status("weapons_offline"):
                        ang = math.degrees(angle_to_player)
                        projectiles.append(
                            Projectile(self.ship.x, self.ship.y, ang,
                                       400, w.fire(),
                                       owner=self.ship,
                                       color=(220, 80, 80),
                                       status_effect=w.status_effect,
                                       max_range=w.range)
                        )

        elif self.state == AIState.RETREAT:
            # Move away from player
            angle_away = math.atan2(
                self.ship.y - player_ship.y,
                self.ship.x - player_ship.x,
            )
            retreat_spd = min(self.ship.speed, self.MAX_SPEED)
            self.ship.vx = math.cos(angle_away) * retreat_spd
            self.ship.vy = math.sin(angle_away) * retreat_spd
            self.ship.angle = math.degrees(angle_away)

        return projectiles

    def _move_toward(self, tx: float, ty: float, dt: float,
                     speed: float | None = None) -> None:
        # Cap speed at MAX_SPEED so enemies don't feel teleport-fast
        raw_speed = speed if speed is not None else self.ship.speed
        # EMP slow + nebula slow: combine multipliers
        emp_mult    = getattr(self.ship, "_emp_slow_mult", 1.0)
        nebula_mult = getattr(self.ship, "_nebula_slow",   1.0)
        s = min(raw_speed, self.MAX_SPEED) * emp_mult * nebula_mult
        dx = tx - self.ship.x
        dy = ty - self.ship.y
        dist = math.hypot(dx, dy)
        if dist > 5:
            self.ship.vx = (dx / dist) * s
            self.ship.vy = (dy / dist) * s
            # Rotate ship sprite to face direction of travel
            self.ship.angle = math.degrees(math.atan2(dy, dx))
        else:
            self.ship.vx = 0
            self.ship.vy = 0


# ── Carrier AI — handles turrets, drones, escort launches ────────────────────
class CarrierAI(EnemyAI):
    """Enhanced AI for carrier-class enemies.
    - Multiple independent turrets that fire simultaneously
    - Deploys combat drones (small fast ships) on engage
    - Launches escort fighters when hull drops below 70 %
    - Moves slowly, holds position and bombards
    """

    # Turret fire every 0.6 s at high damage; drones every 12 s
    TURRET_FIRE_CD  = 0.6
    DRONE_DEPLOY_CD = 12.0
    ESCORT_HULL_PCT = 0.70   # launch escorts when hull drops here

    def __init__(self, ship: Ship):
        super().__init__(ship)
        self._turret_cd    = random.uniform(0, self.TURRET_FIRE_CD)
        self._drone_cd     = random.uniform(4, self.DRONE_DEPLOY_CD)
        self._turret_count = int(ship._data.get("carrier_turret_count", 4))
        self._drone_count  = int(ship._data.get("carrier_drone_count", 3))
        self._escort_count = int(ship._data.get("carrier_escort_count", 2))
        self._escort_launched = False
        self._drones_deployed: list = []   # live drone ships
        # Carriers hold back and bombard — much larger attack range
        self.CHASE_RANGE  = 900
        self.ATTACK_RANGE = 700
        self.MAX_SPEED    = 40

    def update(self, dt: float, player_ship: Ship) -> list[Projectile]:
        if self.ship.is_destroyed:
            self.state = AIState.DEAD
            return []

        dist   = math.hypot(player_ship.x - self.ship.x,
                            player_ship.y - self.ship.y)
        hp_pct = self.ship.hull / max(self.ship.max_hull, 1)

        # Carriers never retreat — they hold ground until destroyed
        if dist <= self.ATTACK_RANGE:
            self.state = AIState.ATTACK
        elif dist <= self.CHASE_RANGE:
            self.state = AIState.CHASE
        else:
            self.state = AIState.PATROL

        projectiles: list[Projectile] = []

        if self.state in (AIState.CHASE, AIState.PATROL):
            # Move slowly toward player when chasing; wander when patrolling
            if self.state == AIState.CHASE:
                self._move_toward(player_ship.x, player_ship.y, dt)
            else:
                self._move_toward(*self._patrol_target, dt, speed=20)
                if math.hypot(self._patrol_target[0] - self.ship.x,
                              self._patrol_target[1] - self.ship.y) < 30:
                    self._patrol_target = (
                        self.ship.x + random.randint(-250, 250),
                        self.ship.y + random.randint(-250, 250),
                    )

        elif self.state == AIState.ATTACK:
            # Slowly circle at long range
            angle_to = math.atan2(player_ship.y - self.ship.y,
                                  player_ship.x - self.ship.x)
            strafe_r = 500
            sx = player_ship.x + math.cos(angle_to + math.pi / 2) * strafe_r
            sy = player_ship.y + math.sin(angle_to + math.pi / 2) * strafe_r
            self._move_toward(sx, sy, dt, speed=35)

            # ── Multi-turret volley ───────────────────────────────────────
            self._turret_cd -= dt
            if self._turret_cd <= 0:
                self._turret_cd = self.TURRET_FIRE_CD + random.uniform(-0.1, 0.2)
                angle_deg = math.degrees(angle_to)
                spread_angles = [angle_deg + (i - self._turret_count / 2) * 8
                                 for i in range(self._turret_count)]
                for ang in spread_angles:
                    # High-damage turret shot (28 dmg, orange-red)
                    projectiles.append(
                        Projectile(
                            self.ship.x, self.ship.y, ang,
                            480,          # speed
                            28,           # damage
                            owner=self.ship,
                            color=(255, 120, 40),
                            size=7,
                            max_range=750,
                        )
                    )

        # ── Drone deployment ──────────────────────────────────────────────
        self._drone_cd -= dt
        if self._drone_cd <= 0 and dist <= self.CHASE_RANGE:
            self._drone_cd = self.DRONE_DEPLOY_CD
            projectiles += self._spawn_drones(player_ship)

        # ── Escort launch at 70 % hull ────────────────────────────────────
        if not self._escort_launched and hp_pct < self.ESCORT_HULL_PCT:
            self._escort_launched = True
            projectiles += self._spawn_escorts(player_ship)

        return projectiles

    def _spawn_drones(self, player_ship: Ship) -> list[Projectile]:
        """Create small fast drone ships that chase the player.

        We return them as special Projectile objects with drone_ship set,
        SpaceCombat._update_enemies handles adding them to enemy list.
        Instead, we attach them to a special queue on self.
        """
        from entities.ship import Ship as _Ship
        import json as _json
        drones = []
        try:
            with open("data/ships.json") as f:
                sd = {s["id"]: s for s in _json.load(f)}
            proto = sd.get("fighter_mk1") or list(sd.values())[0]
            for i in range(self._drone_count):
                d = _Ship(proto)
                angle_off = random.uniform(0, 6.2832)
                d.x = self.ship.x + 60 * math.cos(angle_off)
                d.y = self.ship.y + 60 * math.sin(angle_off)
                d.color_scheme = (255, 140, 0)   # orange drones
                d.hull     = d.hull     * 0.4    # drones are fragile
                d.max_hull = d.max_hull * 0.4
                d.custom_name = f"Drone-{i+1}"
                d._is_drone = True
                self._drones_deployed.append(d)
        except Exception:
            pass
        return []  # drones added via queue in SpaceCombat

    def _spawn_escorts(self, player_ship: Ship) -> list[Projectile]:
        from entities.ship import Ship as _Ship
        import json as _json
        try:
            with open("data/ships.json") as f:
                sd = {s["id"]: s for s in _json.load(f)}
            proto = sd.get("fighter_mk2") or sd.get("fighter_mk1") or list(sd.values())[0]
            for i in range(self._escort_count):
                e = _Ship(proto)
                angle_off = random.uniform(0, 6.2832)
                e.x = self.ship.x + 80 * math.cos(angle_off)
                e.y = self.ship.y + 80 * math.sin(angle_off)
                e.color_scheme = (220, 60, 60)
                e.custom_name  = f"Escort-{i+1}"
                e._is_escort   = True
                self._drones_deployed.append(e)
        except Exception:
            pass
        return []


# ── Space Combat ─────────────────────────────────────────────────────────────
class SpaceCombat:
    SHIELD_REGEN_RATE = 5.0   # HP/sec when out of combat (3s grace)

    def __init__(self, player_ship: Ship, enemy_ships: list[Ship],
                 nebula: bool = False):
        self.player_ship   = player_ship
        self.enemy_ships   = list(enemy_ships)
        self.nebula        = nebula
        self.paused        = False
        self.over          = False
        self.victory       = False

        # ── Allied / escort ships (captured + follow) ──────────────────────────
        self.allied_ships:  list[Ship] = []

        # Sprite groups
        self.all_sprites     = pygame.sprite.Group()
        self.player_group    = pygame.sprite.GroupSingle(player_ship)
        self.enemy_group     = pygame.sprite.Group(*enemy_ships)
        self.player_bullets  = pygame.sprite.Group()
        self.enemy_bullets   = pygame.sprite.Group()
        self.all_sprites.add(player_ship, *enemy_ships)

        # Enemy AI controllers — use CarrierAI for carrier-class ships
        self.ai_controllers = [
            CarrierAI(s) if (s.ship_class == "carrier" or
                             getattr(s, "_data", {}).get("is_carrier", False))
            else EnemyAI(s)
            for s in enemy_ships
        ]

        # Active status effect objects per ship
        self._active_effects: dict[int, list] = {}

        # Combat results
        self.kills              = 0
        self.loot_drops: list[dict] = []
        self._kill_credits      = 0    # total credits earned from kills (kills × 100)
        self._base_ref          = None  # set by game.py so kills auto-credit base

        # Boarding flag
        self.boarding_target: Ship | None = None

        # Nebula modifiers
        self._nebula_weapon_fail_chance = 0.15 if nebula else 0.0
        self._nebula_shield_drain       = 3.0  if nebula else 0.0
        self._nebula_visibility         = 0.5  if nebula else 1.0

        # Font for damage numbers
        pygame.font.init()
        self._font = pygame.font.SysFont("monospace", 14)

        # Damage numbers: [(text_surf, x, y, lifetime)]
        self._dmg_numbers: list[list] = []

        # Screen shake
        self._shake = 0.0

        # Surface size (set on first draw call; used for camera)
        self._surf_size: tuple[int, int] = (832, 720)  # default combat panel size

        # Starfield
        self._starfield = Starfield(seed=random.randint(0, 9999))

        # Crew menu reference (set by Game after combat created) for AUTO mode
        self.crew_menu = None

        # Enemy leash radius — enemies won't wander beyond this from the player
        self.ENEMY_LEASH = 1100

        # Boarding pods in flight: [(x, y, tx, ty, progress 0-1, target_ship)]
        self._boarding_pods: list[list] = []
        # Suppress auto-fire at a ship that we have initiated boarding on
        self._boarding_suppress_target = None

        # ── Drone deploy menu state ────────────────────────────────────────────
        # True when the drone selection menu is open (combat is paused)
        self._drone_menu_open: bool = False
        # Queued types the player has selected (before confirming launch)
        self._drone_menu_selection: dict[str, int] = {k: 0 for k in DRONE_TYPES}
        # Click rects populated by _draw_drone_menu each frame
        self._drone_menu_icon_rects:  list[tuple[str, pygame.Rect]] = []  # (dtype, rect)
        self._drone_menu_launch_rect: pygame.Rect | None = None
        self._drone_menu_close_rect:  pygame.Rect | None = None
        self._drone_menu_hovered:     str | None = None   # dtype of hovered icon

        # ── Player Drone System ────────────────────────────────────────────────
        # Max slots from ship data (0 = no drone bay), + upgrade bonus applied
        # later by Game when it calls set_drone_slots()
        base_drone_slots = int(player_ship._data.get("drone_slots", 0))
        self.drone_system = DroneSystem(max_slots=max(base_drone_slots, 0))
        # drone_panel_btns: set during draw for click handling
        self._drone_panel_btns: list[tuple[str, pygame.Rect]] = []

        # Per-kill loot floaters: [(text, world_x, world_y, lifetime)]
        self._loot_floaters: list[list] = []

        # Sector-clear state (set when all enemies dead; player presses G to leave)
        self.sector_clear       = False
        self._sector_clear_time = 0.0   # seconds since clear

        # Generic pulse timer for visual effects
        self._pulse_time = 0.0

        # Reset carrier bay thresholds for fresh combat
        bay = getattr(player_ship, "bay", None)
        if bay is not None:
            bay.reset_thresholds()

        # ── Sector environment objects ─────────────────────────────────────────
        env_seed = random.randint(0, 99999)
        self._asteroid_field = AsteroidField(seed=env_seed)
        self._comet          = CometTrail(seed=env_seed)
        self._nebula_cloud   = NebulaCloud(seed=env_seed, count=4)
        self._space_debris   = SpaceDebris(seed=env_seed, count=random.randint(4, 8))
        # Space wreckage — 60% chance to spawn some hull wreckage (1–4 pieces)
        wreck_count = random.randint(1, 4) if random.random() < 0.60 else 0
        self._space_wreckage = SpaceWreckage(seed=env_seed, count=wreck_count)
        # Space mines — 30% chance to spawn a mine field (2–5 mines)
        mine_count = random.randint(2, 5) if random.random() < 0.30 else 0
        self._mine_field     = SpaceMineField(seed=env_seed, count=mine_count)
        # Collected loot queued for home_base via game reference
        self._asteroid_loot: list[tuple[str, int]] = []

        # ── Cargo ships (unarmed, escorted, raidable) ─────────────────────────
        # 40% chance a cargo ship spawns in the sector
        self._cargo_ships_combat: list[dict] = []
        if random.random() < 0.40:
            n_cargo = random.randint(1, 2)
            for i in range(n_cargo):
                angle = random.uniform(0, 6.2832)
                dist  = random.uniform(600, 1100)
                self._cargo_ships_combat.append({
                    "x":       player_ship.x + dist * math.cos(angle),
                    "y":       player_ship.y + dist * math.sin(angle),
                    "vx":      random.uniform(-18, 18),
                    "vy":      random.uniform(-18, 18),
                    "cargo_metal":   random.randint(30, 80),
                    "cargo_fuel":    random.randint(15, 40),
                    "cargo_credits": random.randint(50, 150),
                    "looted":  False,
                    "id":      f"cargo_{i}",
                })
        # Raid button state: set by draw loop when player is close
        self._raid_target: dict | None = None

    # ── Drone menu helpers ────────────────────────────────────────────────────
    def open_drone_menu(self) -> None:
        """Open the drone selection menu and pause combat."""
        if self.drone_system.max_slots <= 0:
            return
        self._drone_menu_open    = True
        self.paused              = True
        # Reset selection but keep any already-deployed counts visible
        self._drone_menu_selection = {k: 0 for k in DRONE_TYPES}

    def close_drone_menu(self) -> None:
        """Close the drone menu (without launching) and unpause."""
        self._drone_menu_open = False
        self.paused           = False
        self._drone_menu_selection = {k: 0 for k in DRONE_TYPES}

    def _drone_menu_selected_total(self) -> int:
        return sum(self._drone_menu_selection.values())

    # ── Input ─────────────────────────────────────────────────────────────────
    def handle_event(self, event: pygame.event.Event) -> str | None:
        """Returns action string or None. Actions: 'pause', 'unpause', 'board', 'raid',
        'drone_menu_open', 'drone_menu_close', 'drones_launched'."""

        # ── Drone menu is open — intercept all clicks ────────────────────────
        if self._drone_menu_open:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button in (1, 3):
                mx, my = event.pos
                # ── Click a drone icon ────────────────────────────────────────
                for dtype, rect in self._drone_menu_icon_rects:
                    if rect.collidepoint(mx, my):
                        if event.button == 1:
                            # Left-click: add one of this drone type if slots remain
                            remaining_slots = (self.drone_system.max_slots
                                               - self.drone_system.active_count
                                               - self._drone_menu_selected_total())
                            if remaining_slots > 0:
                                self._drone_menu_selection[dtype] += 1
                        else:
                            # Right-click: remove one from queue
                            if self._drone_menu_selection[dtype] > 0:
                                self._drone_menu_selection[dtype] -= 1
                        return None

                # ── Launch button: deploy queued drones, close menu ───────────
                if (self._drone_menu_launch_rect
                        and self._drone_menu_launch_rect.collidepoint(mx, my)
                        and self._drone_menu_selected_total() > 0):
                    px, py = self.player_ship.x, self.player_ship.y
                    launched = 0
                    for dtype, count in self._drone_menu_selection.items():
                        for _ in range(count):
                            if self.drone_system.launch(dtype, px, py):
                                launched += 1
                    self._drone_menu_open = False
                    self.paused           = False
                    self._drone_menu_selection = {k: 0 for k in DRONE_TYPES}
                    if launched:
                        self._loot_floaters.append(
                            [f"Deployed {launched} drone(s)!", px, py - 30, 2.0])
                    return "drones_launched"

                # ── Close / back to battle button ─────────────────────────────
                if (self._drone_menu_close_rect
                        and self._drone_menu_close_rect.collidepoint(mx, my)):
                    self.close_drone_menu()
                    return "drone_menu_close"

            # ESC also closes the menu
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.close_drone_menu()
                return "drone_menu_close"

            # Consume all events while menu is open
            return None

        # ── Normal combat events ──────────────────────────────────────────────
        # Right-click (button 3) → open drone deploy menu
        if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 3
                and self.drone_system.max_slots > 0):
            self.open_drone_menu()
            return "drone_menu_open"

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                self.paused = not self.paused
                return "pause" if self.paused else "unpause"
            if event.key == pygame.K_b:
                # Attempt boarding nearest weakened enemy
                target = self._nearest_boardable_enemy()
                if target:
                    self.boarding_target = target
                    # Stop firing at this ship — mark it
                    self._boarding_suppress_target = target
                    return "board"
            if event.key == pygame.K_r:
                # Raid nearest close cargo ship
                if self._raid_target and not self._raid_target["looted"]:
                    cs = self._raid_target
                    cs["looted"] = True
                    # Return loot data for game.py to process
                    self._last_cargo_loot = {
                        "metal":   cs["cargo_metal"],
                        "fuel":    cs["cargo_fuel"],
                        "credits": cs["cargo_credits"],
                    }
                    # Loot floater
                    self._loot_floaters.append([
                        f"+{cs['cargo_metal']}mt +{cs['cargo_fuel']}fu +{cs['cargo_credits']}cr",
                        cs["x"], cs["y"], 2.5])
                    return "raid"
        return None

    def raid_cargo_loot(self) -> dict | None:
        """Pop and return the loot from the last successful raid."""
        loot = getattr(self, "_last_cargo_loot", None)
        self._last_cargo_loot = None
        return loot

    # ── Camera (player always centred) ────────────────────────────────────────
    @property
    def _cam_offset(self) -> tuple[float, float]:
        """World → screen offset so player is always in the centre."""
        sw, sh = self._surf_size
        return (sw / 2 - self.player_ship.x,
                sh / 2 - self.player_ship.y)

    def _world_to_screen(self, wx: float, wy: float) -> tuple[int, int]:
        ox, oy = self._cam_offset
        return (int(wx + ox), int(wy + oy))

    # ── Allied ships ──────────────────────────────────────────────────────────
    def add_allied_ship(self, ship: Ship) -> None:
        """Add a captured/friendly ship that flies in formation near the player."""
        # Remove from enemy tracking groups first (ship was an enemy)
        if ship in self.enemy_ships:
            self.enemy_ships.remove(ship)
        self.enemy_group.remove(ship)
        for ai in list(self.ai_controllers):
            if ai.ship is ship:
                self.ai_controllers.remove(ai)
        # Remove from all_sprites so re-add is clean (pygame deduplicates anyway
        # but explicit removal avoids group state inconsistency)
        self.all_sprites.remove(ship)

        # Position alongside the player ship
        import random as _rand
        offset_angle = _rand.uniform(0, 6.2832)
        ship.x = self.player_ship.x + 120 * math.cos(offset_angle)
        ship.y = self.player_ship.y + 120 * math.sin(offset_angle)
        ship.angle  = self.player_ship.angle
        ship.hull   = max(ship.hull, ship.max_hull * 0.3)   # at least 30% hull
        ship.rect.center = (int(ship.x), int(ship.y))        # sync rect immediately
        # Reset enemy shield mode so ally can regen normally
        ship._enemy_shield_mode = False
        self.allied_ships.append(ship)
        self.all_sprites.add(ship)

    # ── Allied ship constants ──────────────────────────────────────────────────
    ALLY_ENGAGE_RANGE  = 420   # px — ally starts attacking enemies within this range
    ALLY_ATTACK_RANGE  = 340   # px — ally stops advancing and fires at this distance
    ALLY_FOLLOW_DIST   = 110   # px — formation offset behind player
    ALLY_FIRE_INTERVAL = 1.2   # seconds between ally shots
    ALLY_SPEED         = 165.0

    def _update_allied_ships(self, dt: float) -> None:
        """Escort AI: follow the player in formation; attack nearby enemies on sight."""
        living_enemies = [e for e in self.enemy_ships if not e.is_destroyed]

        for i, ship in enumerate(self.allied_ships):
            if ship.is_destroyed:
                continue

            # Find nearest enemy within engage range
            nearest_enemy = None
            nearest_dist  = self.ALLY_ENGAGE_RANGE
            for enemy in living_enemies:
                d = math.hypot(enemy.x - ship.x, enemy.y - ship.y)
                if d < nearest_dist:
                    nearest_dist  = d
                    nearest_enemy = enemy

            if nearest_enemy is not None:
                # ── ATTACK MODE ───────────────────────────────────────────────
                dx = nearest_enemy.x - ship.x
                dy = nearest_enemy.y - ship.y
                attack_angle = math.atan2(dy, dx)
                ship.angle = math.degrees(attack_angle)

                if nearest_dist > self.ALLY_ATTACK_RANGE:
                    # Close in on the enemy
                    ship.x += math.cos(attack_angle) * self.ALLY_SPEED * dt
                    ship.y += math.sin(attack_angle) * self.ALLY_SPEED * dt
                else:
                    # Strafe to avoid standing still
                    strafe_angle = attack_angle + math.pi / 2
                    ship.x += math.cos(strafe_angle) * (self.ALLY_SPEED * 0.4) * dt
                    ship.y += math.sin(strafe_angle) * (self.ALLY_SPEED * 0.4) * dt

                # Fire at the enemy
                ally_cd = getattr(ship, "_ally_fire_cd", 0.0)
                ally_cd -= dt
                if ally_cd <= 0 and ship.weapons and not ship.has_status("weapons_offline"):
                    ally_cd = self.ALLY_FIRE_INTERVAL + random.uniform(-0.2, 0.3)
                    for w in ship.weapons:
                        if w.can_fire():
                            spread = random.uniform(-6, 6)   # slight aim wobble
                            proj = Projectile(
                                ship.x, ship.y,
                                math.degrees(attack_angle) + spread,
                                440, w.fire(),
                                owner=ship,
                                color=(80, 220, 200),   # cyan = friendly fire
                                max_range=getattr(w, "range", 500),
                            )
                            self.player_bullets.add(proj)   # same group — won't hit player
                            self.all_sprites.add(proj)
                ship._ally_fire_cd = ally_cd

            else:
                # ── FOLLOW MODE — triangle formation behind player ─────────────
                angle_offset = math.pi + (i - len(self.allied_ships) / 2) * 0.6
                target_x = (self.player_ship.x +
                            self.ALLY_FOLLOW_DIST * math.cos(
                                self.player_ship.angle * math.pi / 180 + angle_offset))
                target_y = (self.player_ship.y +
                            self.ALLY_FOLLOW_DIST * math.sin(
                                self.player_ship.angle * math.pi / 180 + angle_offset))
                dx = target_x - ship.x
                dy = target_y - ship.y
                dist = math.hypot(dx, dy)
                if dist > 20:
                    ship.x += (dx / dist) * self.ALLY_SPEED * dt
                    ship.y += (dy / dist) * self.ALLY_SPEED * dt
                    ship.angle = math.degrees(math.atan2(dy, dx))

            ship.update(dt)

    # ── Update ────────────────────────────────────────────────────────────────
    def update(self, dt: float) -> None:
        if self.paused or self.over:
            return

        keys = pygame.key.get_pressed()
        self._update_player(dt, keys)
        self._update_enemies(dt)
        self._update_bullets(dt)
        self._check_collisions()
        self._update_ships(dt)
        self._update_allied_ships(dt)
        self._update_dmg_numbers(dt)
        self._update_boarding_pods(dt)
        self._update_loot_floaters(dt)
        self._pulse_time += dt

        # ── Environment updates ────────────────────────────────────────────────
        self._starfield.update(dt)
        self._comet.update(dt)
        self._asteroid_field.update(dt)
        self._space_debris.update(dt)
        self._space_wreckage.update(dt)
        self._mine_field.update(dt)
        # Asteroid resource collection check
        collected = self._asteroid_field.check_collect(self.player_ship)
        for rtype, amount in collected:
            self._asteroid_loot.append((rtype, amount))
            self._loot_floaters.append(
                [f"+{amount} {rtype}", self.player_ship.x, self.player_ship.y, 1.8])
        # Floating debris collection — gated by auto_collect_debris setting
        _auto_col = getattr(self, "_auto_collect_debris", True)
        if _auto_col:
            debris_loot = self._space_debris.check_collect(self.player_ship, collect_r=28.0)
            for rtype, amount in debris_loot:
                self._asteroid_loot.append((rtype, amount))
                self._loot_floaters.append(
                    [f"+{amount} {rtype}", self.player_ship.x, self.player_ship.y, 1.8])
        # Wreckage collection (always auto — large pieces, obvious)
        wreck_loot = self._space_wreckage.check_collect(self.player_ship, collect_r=10.0)
        for rtype, amount in wreck_loot:
            self._asteroid_loot.append((rtype, amount))
            self._loot_floaters.append(
                [f"+{amount} {rtype} (wreck)", self.player_ship.x, self.player_ship.y, 2.0])
        # Nebula slow — applies to all ships
        all_ships_for_slow = ([self.player_ship]
                              + [e for e in self.enemy_ships if not e.is_destroyed]
                              + [a for a in self.allied_ships if not a.is_destroyed])
        self._nebula_cloud.apply_slow(all_ships_for_slow)

        # Mine field — check all ships (player + enemies + allied)
        all_ships = [self.player_ship] + self.enemy_ships + self.allied_ships
        for hit_ship, mine_dmg in self._mine_field.check_trigger(all_ships):
            hit_ship.take_damage(mine_dmg, ignore_shield=False)
            self._shake = max(self._shake, 10.0)
            self._loot_floaters.append(
                [f"-{int(mine_dmg)} MINE!", hit_ship.x, hit_ship.y, 1.2])

        # ── Player drone system ───────────────────────────────────────────────
        if self.drone_system.max_slots > 0:
            live_enemies = [e for e in self.enemy_ships if not e.is_destroyed]
            self.drone_system.update(
                dt,
                self.player_ship.x, self.player_ship.y,
                live_enemies,
                self.player_ship,
            )
            # Apply EMP slow effect to any enemy that has it flagged
            for e in live_enemies:
                slow_t = getattr(e, "_emp_slow_timer", 0.0)
                if slow_t > 0:
                    e._emp_slow_timer = max(0.0, slow_t - dt)
                    # Slow effect: reduce AI movement (checked in EnemyAI via
                    # _emp_slow_mult flag)
                    if e._emp_slow_timer <= 0:
                        e._emp_slow_mult  = 1.0

        if self._shake > 0:
            self._shake -= dt * 60
            self._shake = max(0.0, self._shake)

        # ── Player carrier bay auto-launch ────────────────────────────────────
        bay = getattr(self.player_ship, "bay", None)
        if bay is not None:
            launch_pct = float(self.player_ship._data.get("bay_launch_hull_pct", 0.25))
            bay.update_anim(dt)
            launched = bay.check_auto_launch(self.player_ship, launch_pct)
            if launched:
                # Spawn as allied ship in the arena
                angle_off = random.uniform(0, 6.2832)
                launched.x = self.player_ship.x + 80 * math.cos(angle_off)
                launched.y = self.player_ship.y + 80 * math.sin(angle_off)
                launched.color_scheme = (80, 220, 200)   # cyan = friendly
                launched._build_sprite()
                launched.fleet_order = "follow"
                # Command Aura: +10% speed if carrier is pirate_carrier
                if self.player_ship._data.get("id") == "pirate_carrier":
                    launched.speed = int(launched.speed * 1.10)
                self.add_allied_ship(launched)
                # Trigger bay door animation
                bay.start_launch_anim(self.player_ship.x, self.player_ship.y,
                                      self.player_ship.angle)
                self._loot_floaters.append(
                    [f"BAY LAUNCH: {launched.custom_name}",
                     self.player_ship.x, self.player_ship.y - 20, 2.0])
                self._shake = max(self._shake, 6.0)

        # ── Cargo ship movement ───────────────────────────────────────────────
        self._raid_target = None
        for cs in self._cargo_ships_combat:
            if cs["looted"]:
                continue
            cs["x"] += cs["vx"] * dt
            cs["y"] += cs["vy"] * dt
            # Drift slowly — dampen velocity
            cs["vx"] *= 0.998
            cs["vy"] *= 0.998
            # Check if player is close (raid range = 200px)
            dist = math.hypot(cs["x"] - self.player_ship.x,
                              cs["y"] - self.player_ship.y)
            if dist < 220:
                self._raid_target = cs

        # Defeat — player dies
        if self.player_ship.is_destroyed:
            self.over    = True
            self.victory = False
        # Sector clear — all enemies dead; game.py detects sector_clear and shows victory screen
        elif self.enemy_ships and all(s.is_destroyed for s in self.enemy_ships):
            if not self.sector_clear:
                self.sector_clear = True
                self.victory = True
            self._sector_clear_time += dt

    def _nearest_living_enemy(self) -> "Ship | None":
        """Return the nearest non-destroyed enemy ship, regardless of range."""
        living = [s for s in self.enemy_ships if not s.is_destroyed]
        if not living:
            return None
        return min(living,
                   key=lambda s: math.hypot(s.x - self.player_ship.x,
                                            s.y - self.player_ship.y))

    def _is_auto(self, station: str) -> bool:
        """Check if a crew station has AUTO mode enabled."""
        cm = self.crew_menu
        return cm.is_auto(station) if cm else False

    def _update_player(self, dt: float, keys) -> None:
        ship  = self.player_ship
        if ship.has_status("movement_offline"):
            return
        # Combine EMP slow + nebula slow
        spd   = (ship.effective_speed
                 * getattr(ship, "_slow_factor", 1.0)
                 * getattr(ship, "_nebula_slow", 1.0))

        # ── AUTO PILOT (cockpit) ─────────────────────────────────────────────
        # If auto pilot is on, steer toward the nearest enemy.
        # Manual keys still override.
        manual_input = (keys[pygame.K_w] or keys[pygame.K_UP] or
                        keys[pygame.K_s] or keys[pygame.K_DOWN] or
                        keys[pygame.K_a] or keys[pygame.K_LEFT] or
                        keys[pygame.K_d] or keys[pygame.K_RIGHT])

        if not manual_input and self._is_auto("cockpit"):
            # ── Priority 1: kill all living enemies ───────────────────────────
            target = self._nearest_living_enemy()
            if target:
                dx = target.x - ship.x
                dy = target.y - ship.y
                dist = math.hypot(dx, dy)
                # Close enough? stop advancing (don't ram)
                if dist > 280:
                    ship.vx = (dx / dist) * spd
                    ship.vy = (dy / dist) * spd
                else:
                    # Strafe: circle at attack distance
                    perp = math.atan2(dy, dx) + math.pi / 2
                    ship.vx = math.cos(perp) * spd * 0.6
                    ship.vy = math.sin(perp) * spd * 0.6
            else:
                # ── Priority 2: collect nearest uncollected resource ──────────
                # Check asteroids and debris for the closest pickup
                nearest_res = None
                nearest_res_dist = 9999.0
                for ast in self._asteroid_field.asteroids:
                    if ast["collected"]:
                        continue
                    d = math.hypot(ast["x"] - ship.x, ast["y"] - ship.y)
                    if d < nearest_res_dist:
                        nearest_res_dist = d
                        nearest_res = (ast["x"], ast["y"])
                for piece in self._space_debris.pieces:
                    if piece["collected"]:
                        continue
                    d = math.hypot(piece["x"] - ship.x, piece["y"] - ship.y)
                    if d < nearest_res_dist:
                        nearest_res_dist = d
                        nearest_res = (piece["x"], piece["y"])
                if nearest_res:
                    dx = nearest_res[0] - ship.x
                    dy = nearest_res[1] - ship.y
                    dist = math.hypot(dx, dy) or 1
                    ship.vx = (dx / dist) * spd
                    ship.vy = (dy / dist) * spd
                else:
                    ship.vx, ship.vy = 0.0, 0.0
        else:
            mx_v, my_v = 0.0, 0.0
            if keys[pygame.K_w] or keys[pygame.K_UP]:    my_v -= spd
            if keys[pygame.K_s] or keys[pygame.K_DOWN]:  my_v += spd
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:  mx_v -= spd
            if keys[pygame.K_d] or keys[pygame.K_RIGHT]: mx_v += spd
            ship.vx, ship.vy = mx_v, my_v

        # ── AUTO ENGINE BOOST ────────────────────────────────────────────────
        if self._is_auto("engine_room"):
            target = self._nearest_living_enemy()
            if target and math.hypot(target.x - ship.x,
                                     target.y - ship.y) > 400:
                # Boost speed by 25% when engine auto is on and enemy is far
                ship.vx *= 1.25
                ship.vy *= 1.25

        # Aim toward mouse (screen coords → world angle via camera offset)
        mx_pos, my_pos = pygame.mouse.get_pos()
        ox, oy = self._cam_offset
        world_mx = mx_pos - ox
        world_my = my_pos - oy
        ship.angle = math.degrees(math.atan2(world_my - ship.y,
                                             world_mx - ship.x))

        # ── GUNNER / AUTO-FIRE ───────────────────────────────────────────────
        # Gun auto always on (existing). Additionally honour gun_turret AUTO toggle
        # which forces firing even outside weapon range.
        nearest = self._nearest_enemy_in_range(ship)
        manual  = pygame.mouse.get_pressed()[0]
        # If gun_turret AUTO is on, also chase the nearest enemy for aim
        if self._is_auto("gun_turret") and not nearest:
            nearest = self._nearest_living_enemy()

        # Suppress firing at any ship that's been tagged as a boarding target
        suppress = getattr(self, "_boarding_suppress_target", None)
        if suppress is not None and nearest is suppress:
            nearest = None
            manual  = False
        should_fire = (nearest is not None) or manual

        if should_fire and not ship.has_status("weapons_offline"):
            if manual:
                fire_angle = ship.angle
            elif nearest:
                fire_angle = math.degrees(
                    math.atan2(nearest.y - ship.y, nearest.x - ship.x))
                ship.angle = fire_angle
            else:
                fire_angle = ship.angle

            for w in ship.weapons:
                if w.can_fire():
                    if random.random() < self._nebula_weapon_fail_chance:
                        continue
                    dmg = w.fire()
                    gunner_bonus = ship.station_stat("gun_turret") * 0.02
                    meta_dmg     = getattr(ship, "_meta_damage_pct", 0.0)
                    dmg *= (1 + gunner_bonus + meta_dmg)
                    proj = Projectile(
                        ship.x, ship.y, fire_angle,
                        500, dmg,
                        owner=ship,
                        color=(80, 200, 255),
                        status_effect=w.status_effect,
                        max_range=w.range,
                    )
                    self.player_bullets.add(proj)
                    self.all_sprites.add(proj)
                    # Play shoot SFX via event bus
                    sfx_key = "missile_fire" if getattr(w, "weapon_type", "") == "missile" else "laser_fire"
                    try:
                        from core.events import bus as _bus
                        _bus.publish("sfx_play", key=sfx_key)
                    except Exception:
                        pass

        # ── AUTO REPAIR (repair_station) ─────────────────────────────────────
        if self._is_auto("repair_station"):
            hp_pct = ship.hull / max(ship.max_hull, 1)
            if hp_pct < 0.5:
                repair_rate = 4.0 + ship.station_stat("repair_station") * 0.5
                ship.hull = min(ship.max_hull, ship.hull + repair_rate * dt)

    def _nearest_enemy_in_range(self, ship: "Ship") -> "Ship | None":
        """Return the nearest living enemy within weapon range, or None."""
        max_range = max((w.range for w in ship.weapons), default=0)
        if not max_range:
            return None
        candidates = [
            s for s in self.enemy_ships
            if not s.is_destroyed
            and math.hypot(s.x - ship.x, s.y - ship.y) <= max_range
        ]
        if not candidates:
            return None
        return min(candidates,
                   key=lambda s: math.hypot(s.x - ship.x, s.y - ship.y))

    def _update_enemies(self, dt: float) -> None:
        px, py = self.player_ship.x, self.player_ship.y
        for ai in self.ai_controllers:
            if ai.state == AIState.DEAD:
                continue
            new_projs = ai.update(dt, self.player_ship)
            for p in new_projs:
                self.enemy_bullets.add(p)
                self.all_sprites.add(p)

            # ── Flush drone/escort deploy queue from CarrierAI ───────────────
            if isinstance(ai, CarrierAI) and ai._drones_deployed:
                for spawn in list(ai._drones_deployed):
                    # Only add ships not yet in enemy_ships
                    if spawn not in self.enemy_ships:
                        self.enemy_ships.append(spawn)
                        self.all_sprites.add(spawn)
                        # Give spawned ship its own EnemyAI
                        self.ai_controllers.append(EnemyAI(spawn))
                        # Notification
                        from core.events import bus
                        tag = "Drone" if getattr(spawn, "_is_drone", False) else "Escort"
                        bus.publish("notification",
                            msg=f"Carrier deploys {tag}!",
                            color=(255, 140, 40))
                ai._drones_deployed.clear()

            # ── Enemy leash: never let them drift too far ────────────────────
            dist = math.hypot(ai.ship.x - px, ai.ship.y - py)
            if dist > self.ENEMY_LEASH:
                # Teleport enemy back to leash edge instantly (hard clamp)
                angle_back = math.atan2(py - ai.ship.y, px - ai.ship.x)
                ai.ship.x = px - math.cos(angle_back) * self.ENEMY_LEASH
                ai.ship.y = py - math.sin(angle_back) * self.ENEMY_LEASH
                ai.ship.vx = 0.0
                ai.ship.vy = 0.0
                # Also force chase state
                ai.state = AIState.CHASE

            # Nebula shield drain
            if self.nebula:
                ai.ship.shield = max(0.0,
                    ai.ship.shield - self._nebula_shield_drain * dt)

        # Nebula shield drain on player
        if self.nebula:
            self.player_ship.shield = max(
                0.0, self.player_ship.shield - self._nebula_shield_drain * dt
            )

    def _update_bullets(self, dt: float) -> None:
        self.player_bullets.update(dt)
        self.enemy_bullets.update(dt)

    def _update_ships(self, dt: float) -> None:
        self.player_ship.update(dt)
        for ship in self.enemy_ships:
            ship.update(dt)

    def _check_collisions(self) -> None:
        from progression.rarity import rarity_system

        # Player bullets → enemy ships
        for proj in list(self.player_bullets):
            for ship in self.enemy_ships:
                if ship.is_destroyed:
                    continue
                if proj.rect.colliderect(ship.rect):
                    # Evasion check
                    if random.random() < ship.base_evasion:
                        proj.kill()
                        continue
                    hull_dmg = ship.take_damage(proj.damage)
                    self._spawn_dmg_number(proj.damage, ship.x, ship.y, (255, 200, 50))
                    if hull_dmg > 0:
                        self._shake = min(self._shake + 6, 20)
                        if _particle_system:
                            _particle_system.emit_hit_sparks(ship.x, ship.y, (255, 200, 50))
                    if proj.status_effect:
                        eff = make_effect(proj.status_effect)
                        if eff:
                            eff.on_apply(ship)
                            if _particle_system:
                                _particle_system.emit_status_effect(ship.x, ship.y, proj.status_effect)
                    proj.kill()
                    if ship.is_destroyed:
                        if _particle_system:
                            _particle_system.emit_explosion(ship.x, ship.y, count=40)
                        self._on_enemy_killed(ship)
                    break

        # Enemy bullets → player
        evasion_bonus = self.player_ship.base_evasion + (
            self.player_ship.station_stat("cockpit") * 0.001
        )
        # Asteroid cover bonus
        asteroid_deflect = self._asteroid_field.deflect_chance(self.player_ship)
        for proj in list(self.enemy_bullets):
            if proj.rect.colliderect(self.player_ship.rect):
                if random.random() < evasion_bonus + asteroid_deflect:
                    proj.kill()
                    continue
                self.player_ship.take_damage(proj.damage)
                self._spawn_dmg_number(proj.damage, self.player_ship.x,
                                       self.player_ship.y, (220, 60, 60))
                if _particle_system:
                    _particle_system.emit_hit_sparks(
                        self.player_ship.x, self.player_ship.y, (220, 100, 60))
                if proj.status_effect:
                    eff = make_effect(proj.status_effect)
                    if eff:
                        eff.on_apply(self.player_ship)
                self._shake = min(self._shake + 4, 20)
                proj.kill()

    def _on_enemy_killed(self, ship: Ship) -> None:
        self.kills += 1
        # ── Kill reward: 100cr per kill, tracked + awarded to base ───────────
        CREDIT_PER_KILL = 100
        self._kill_credits += CREDIT_PER_KILL
        if self._base_ref is not None:
            try:
                self._base_ref.add_resource("credits", CREDIT_PER_KILL)
            except Exception:
                pass
        # Clear boarding suppression if this ship was being boarded
        if getattr(self, "_boarding_suppress_target", None) is ship:
            self._boarding_suppress_target = None
            self.boarding_target = None
        from core.events import bus
        bus.publish("enemy_killed", ship=ship, kills=self.kills,
                    kill_credits=self._kill_credits)
        # Roll loot drop
        from progression.rarity import rarity_system
        import json, os
        drop_name = None
        try:
            with open(os.path.join("data", "weapons.json")) as f:
                weapon_pool = json.load(f)
            drops = rarity_system.roll_drop_table(weapon_pool, luck=0.0, count=1)
            self.loot_drops.extend(drops)
            if drops:
                drop_name = drops[0].get("name", "weapon")
        except Exception:
            pass
        # Floating loot text above destroyed ship (shows running total)
        label = f"+{CREDIT_PER_KILL}cr  [{self.kills}×100={self._kill_credits}cr]"
        if drop_name:
            label = f"+{CREDIT_PER_KILL}cr  [{drop_name}]"
        self._loot_floaters.append([label, ship.x, ship.y, 2.5])

    # ── Boarding helper ───────────────────────────────────────────────────────
    def _nearest_boardable_enemy(self) -> Ship | None:
        """Return nearest enemy that can be boarded.
        Primary:   shield depleted + recharge lock active (shield freshly broken).
        Fallback:  any ship within 900px with hull < 35 pct (badly damaged).
        """
        def _dist(s):
            return math.hypot(s.x - self.player_ship.x, s.y - self.player_ship.y)

        # Primary: shield broken (relaxed range to 900)
        primary = [
            s for s in self.enemy_ships
            if not s.is_destroyed
            and s.shield <= 0
            and s.shield_recharge_lock > 0
            and _dist(s) < 900
        ]
        if primary:
            return min(primary, key=_dist)

        # Fallback: low-hull enemy within boarding range (relaxed to 35% hull, 900px)
        candidates = [
            s for s in self.enemy_ships
            if not s.is_destroyed
            and (s.hull / max(s.max_hull, 1)) < 0.35
            and _dist(s) < 900
        ]
        if not candidates:
            return None
        return min(candidates,
                   key=lambda s: math.hypot(s.x - self.player_ship.x,
                                            s.y - self.player_ship.y))

    def launch_boarding_pod(self, target: Ship) -> None:
        """Spawn a boarding pod flying from player to target."""
        ps = self.player_ship
        self._boarding_pods.append([
            ps.x, ps.y,       # current position
            target.x, target.y,  # destination (snapshot)
            0.0,              # progress 0→1
            target,           # reference for live position update
        ])

    def _update_boarding_pods(self, dt: float) -> None:
        SPEED = 0.8   # fraction of distance per second
        for pod in list(self._boarding_pods):
            pod[4] = min(1.0, pod[4] + SPEED * dt)
            # Interpolate toward target's live position
            tgt = pod[5]
            pod[2], pod[3] = tgt.x, tgt.y
            t = pod[4]
            pod[0] = self.player_ship.x + (tgt.x - self.player_ship.x) * t
            pod[1] = self.player_ship.y + (tgt.y - self.player_ship.y) * t
            if pod[4] >= 1.0:
                self._boarding_pods.remove(pod)

    # ── Loot floaters ──────────────────────────────────────────────────────────
    def _update_loot_floaters(self, dt: float) -> None:
        for f in self._loot_floaters:
            f[2] -= 22 * dt   # float upward
            f[3] -= dt
        self._loot_floaters = [f for f in self._loot_floaters if f[3] > 0]

    # ── Damage numbers ────────────────────────────────────────────────────────
    def _spawn_dmg_number(self, dmg: float, x: float, y: float,
                          color: tuple) -> None:
        surf = self._font.render(f"-{dmg:.0f}", True, color)
        self._dmg_numbers.append([surf, x, y, 1.0])

    def _update_dmg_numbers(self, dt: float) -> None:
        for entry in self._dmg_numbers:
            entry[2] -= 30 * dt  # float upward
            entry[3] -= dt
        self._dmg_numbers = [e for e in self._dmg_numbers if e[3] > 0]

    # ── Draw ──────────────────────────────────────────────────────────────────
    def draw(self, surface: pygame.Surface) -> None:
        # Update stored surface size for camera calculation
        self._surf_size = surface.get_size()
        sw, sh = self._surf_size

        # Camera offset (keeps player centred)
        cam_ox, cam_oy = self._cam_offset

        # Screen shake extra nudge
        sh_x = random.randint(-int(self._shake), int(self._shake)) if self._shake > 1 else 0
        sh_y = random.randint(-int(self._shake), int(self._shake)) if self._shake > 1 else 0
        ox = cam_ox + sh_x
        oy = cam_oy + sh_y

        # ── Starfield (drawn first, below everything) ─────────────────────────
        surface.fill(DARK_BG)
        self._starfield.draw(surface, self.player_ship.x, self.player_ship.y)

        # ── Sector environment: nebula clouds, comet, asteroids, debris, mines ─
        _active_ships = ([self.player_ship]
                         + [e for e in self.enemy_ships if not e.is_destroyed]
                         + [a for a in self.allied_ships if not a.is_destroyed])
        self._nebula_cloud.draw(surface, ox, oy, active_ships=_active_ships)
        self._comet.draw(surface, ox, oy)
        self._asteroid_field.draw(surface, ox, oy)
        self._space_debris.draw(surface, ox, oy,
                                player_x=self.player_ship.x,
                                player_y=self.player_ship.y)
        self._space_wreckage.draw(surface, ox, oy,
                                  player_x=self.player_ship.x,
                                  player_y=self.player_ship.y)
        self._mine_field.draw(surface, ox, oy)

        # ── Player drones (drawn above environment, below ships) ──────────────
        if self.drone_system.max_slots > 0:
            self.drone_system.draw(surface, ox, oy)

        # ── Bay door launch animation ─────────────────────────────────────────
        bay = getattr(self.player_ship, "bay", None)
        if bay is not None:
            bay.draw_anim(surface, ox, oy)

        # Nebula tint overlay
        if self.nebula:
            overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            overlay.fill((60, 0, 80, 40))
            surface.blit(overlay, (0, 0))

        # Draw ships with rotation + camera offset
        # Allied ships drawn with a cyan/teal tint ring so player can tell them apart
        all_ships = [self.player_ship] + [s for s in self.enemy_ships if not s.is_destroyed]
        all_allied = [s for s in self.allied_ships if not s.is_destroyed]
        for ship in all_ships + all_allied:
            base = getattr(ship, "_base_image", ship.image)
            rotated = pygame.transform.rotate(base, -ship.angle)
            sx = int(ship.x + ox) - rotated.get_width()  // 2
            sy = int(ship.y + oy) - rotated.get_height() // 2

            # ── Engine exhaust glow (drawn behind sprite) ─────────────────
            moving = (ship.vx ** 2 + ship.vy ** 2) > 4
            if moving or True:   # always show a resting idle glow
                ang_rad = math.radians(ship.angle + 180)   # behind the ship
                sc_class = getattr(ship, "ship_class", "fighter")
                # Engine glow size by class
                eng_r = {"fighter": 7, "interceptor": 9, "corvette": 9,
                         "gunship": 11, "destroyer": 12, "battlecruiser": 16,
                         "carrier": 14, "pirate_carrier": 16, "dreadnought": 15,
                         "scout": 6, "stealth": 5, "freighter": 9,
                         "mining_barge": 8, "assault_transport": 10}.get(sc_class, 7)
                num_eng = {"battlecruiser": 6, "pirate_carrier": 6, "carrier": 4,
                           "dreadnought": 4, "destroyer": 3, "assault_transport": 4,
                           "freighter": 2, "corvette": 2}.get(sc_class, 1)
                # Engine colour: player=blue, ally=teal, enemy=orange/red
                if ship is self.player_ship:
                    ecol = (80, 160, 255)
                elif ship in all_allied:
                    ecol = (60, 220, 180)
                elif sc_class == "pirate_carrier":
                    ecol = (255, 100, 30)
                else:
                    ecol = (255, 140, 40)

                half_w = base.get_width() // 2
                eng_ox = half_w - 4  # engine offset from center
                spread = 6 if num_eng <= 2 else 10
                for ei in range(num_eng):
                    t = (ei / max(num_eng - 1, 1) - 0.5) * spread if num_eng > 1 else 0
                    perp_rad = ang_rad + math.pi / 2
                    ex = ship.x + ox + math.cos(ang_rad) * eng_ox + math.cos(perp_rad) * t
                    ey = ship.y + oy + math.sin(ang_rad) * eng_ox + math.sin(perp_rad) * t
                    sz_m = eng_r + (4 if moving else 1)
                    gsurf = pygame.Surface((sz_m * 4, sz_m * 4), pygame.SRCALPHA)
                    # Outer halo
                    pygame.draw.circle(gsurf, (*ecol, 18), (sz_m * 2, sz_m * 2), sz_m * 2)
                    # Inner bright core
                    pygame.draw.circle(gsurf, (*ecol, 90), (sz_m * 2, sz_m * 2), sz_m)
                    # Brightest centre dot
                    pygame.draw.circle(gsurf, (255, 255, 255, 120), (sz_m * 2, sz_m * 2), max(2, sz_m // 3))
                    surface.blit(gsurf, (int(ex) - sz_m * 2, int(ey) - sz_m * 2),
                                 special_flags=pygame.BLEND_ALPHA_SDL2)

            surface.blit(rotated, (sx, sy))

            # ── Shield bubble (drawn over sprite when shield is active) ───────
            if ship.shield > 0 and ship.max_shield > 0:
                shield_pct = ship.shield / ship.max_shield
                # Colour: player=blue, ally=cyan, enemy=amber
                if ship is self.player_ship:
                    shcol = (60, 120, 255)
                elif ship in all_allied:
                    shcol = (40, 200, 200)
                else:
                    shcol = (180, 140, 40)
                # Alpha proportional to shield %
                alpha = int(30 + 60 * shield_pct)
                ring_r2 = max(rotated.get_width(), rotated.get_height()) // 2 + 5
                sh_surf = pygame.Surface((ring_r2 * 2 + 4, ring_r2 * 2 + 4), pygame.SRCALPHA)
                # Draw hexagonal shield facets (6 segments, slowly rotating)
                import time as _st
                _t_now = _st.time()
                for seg in range(6):
                    a0 = math.radians(seg * 60 + _t_now * 15)
                    a1 = math.radians((seg + 1) * 60 + _t_now * 15)
                    p0 = (int(ring_r2 + 2 + ring_r2 * math.cos(a0)),
                          int(ring_r2 + 2 + ring_r2 * math.sin(a0)))
                    p1 = (int(ring_r2 + 2 + ring_r2 * math.cos(a1)),
                          int(ring_r2 + 2 + ring_r2 * math.sin(a1)))
                    pygame.draw.line(sh_surf, (*shcol, alpha), p0, p1, 1)
                    # Facet fill (subtle)
                    mid_pt = (ring_r2 + 2, ring_r2 + 2)
                    pygame.draw.polygon(sh_surf, (*shcol, alpha // 4),
                                        [mid_pt, p0, p1])
                surface.blit(sh_surf,
                             (int(ship.x + ox) - ring_r2 - 2,
                              int(ship.y + oy) - ring_r2 - 2),
                             special_flags=pygame.BLEND_ALPHA_SDL2)

            # Friendly ring for allied ships
            if ship in all_allied:
                ring_r = max(rotated.get_width(), rotated.get_height()) // 2 + 4
                pygame.draw.circle(surface, (60, 200, 200),
                                   (int(ship.x + ox), int(ship.y + oy)), ring_r, 1)
                # "ALLY" label above
                try:
                    ally_f = pygame.font.SysFont("monospace", 9)
                    ally_t = ally_f.render("ALLY", True, (60, 220, 220))
                    surface.blit(ally_t, (int(ship.x + ox) - ally_t.get_width() // 2,
                                          int(ship.y + oy) - ring_r - 12))
                except Exception:
                    pass
            # Lightly-guarded enemy: dashed yellow ring + label
            elif getattr(ship, "_lightly_guarded", False) and ship in [s for s in self.enemy_ships]:
                ring_r = max(rotated.get_width(), rotated.get_height()) // 2 + 6
                # Dashed circle approximated by arc segments
                for seg in range(8):
                    a0 = math.radians(seg * 45)
                    a1 = math.radians(seg * 45 + 22)
                    p1 = (int(ship.x + ox + ring_r * math.cos(a0)),
                          int(ship.y + oy + ring_r * math.sin(a0)))
                    p2 = (int(ship.x + ox + ring_r * math.cos(a1)),
                          int(ship.y + oy + ring_r * math.sin(a1)))
                    pygame.draw.line(surface, (220, 200, 60), p1, p2, 1)
                try:
                    lg_f = pygame.font.SysFont("monospace", 9)
                    lg_t = lg_f.render("LIGHTLY GUARDED", True, (220, 200, 60))
                    surface.blit(lg_t, (int(ship.x + ox) - lg_t.get_width() // 2,
                                        int(ship.y + oy) - ring_r - 12))
                except Exception:
                    pass
            # Engine trail particles
            if _particle_system and (ship.vx != 0 or ship.vy != 0):
                _particle_system.emit_engine_trail(
                    ship.x + ox, ship.y + oy, ship.angle,
                    color=(80, 160, 255) if ship is self.player_ship
                    else (60, 200, 200) if ship in all_allied
                    else (255, 100, 40))

        # Draw projectiles with camera offset
        for proj in list(self.player_bullets) + list(self.enemy_bullets):
            sx = int(proj.x + ox)
            sy = int(proj.y + oy)
            proj_surf = proj.image
            surface.blit(proj_surf, (sx - proj_surf.get_width()  // 2,
                                      sy - proj_surf.get_height() // 2))

        # Particles
        if _particle_system:
            _particle_system.draw(surface)

        # Health bars (player+enemies + allied escorts)
        for ship in all_ships + all_allied:
            self._draw_health_bar(surface, ship, ox, oy)

        # Damage numbers
        for entry in self._dmg_numbers:
            surface.blit(entry[0], (int(entry[1] + ox), int(entry[2] + oy)))

        # Loot floaters (gold text rising above destroyed ships)
        loot_font = pygame.font.SysFont("monospace", 13, bold=True)
        for lf in self._loot_floaters:
            alpha = min(255, int(lf[3] * 200))
            txt = loot_font.render(lf[0], True, (255, 220, 60))
            ts  = pygame.Surface(txt.get_size(), pygame.SRCALPHA)
            ts.blit(txt, (0, 0))
            ts.set_alpha(alpha)
            surface.blit(ts, (int(lf[1] + ox) - txt.get_width() // 2,
                               int(lf[2] + oy)))

        # Boarding pods (small cyan diamond flying toward target)
        for pod in self._boarding_pods:
            sx = int(pod[0] + ox)
            sy = int(pod[1] + oy)
            size = 5
            pts = [(sx, sy - size), (sx + size, sy),
                   (sx, sy + size), (sx - size, sy)]
            pygame.draw.polygon(surface, (80, 255, 220), pts)
            pygame.draw.polygon(surface, (200, 255, 240), pts, 1)
            # Trail line back toward player
            ps_sx = int(self.player_ship.x + ox)
            ps_sy = int(self.player_ship.y + oy)
            pygame.draw.line(surface, (40, 120, 100), (ps_sx, ps_sy), (sx, sy), 1)

        # ── Cargo ships in combat arena ───────────────────────────────────────
        for cs in self._cargo_ships_combat:
            if cs["looted"]:
                continue
            csx = int(cs["x"] + ox)
            csy = int(cs["y"] + oy)
            sw2, sh2 = surface.get_size()
            if -40 < csx < sw2 + 40 and -20 < csy < sh2 + 20:
                # Draw as a distinctive wide freighter shape
                pygame.draw.rect(surface, (60, 80, 40), (csx - 18, csy - 6, 36, 12))
                pygame.draw.rect(surface, (140, 200, 100), (csx - 18, csy - 6, 36, 12), 1)
                pygame.draw.rect(surface, (200, 180, 60), (csx - 6, csy - 9, 12, 18))
                pygame.draw.circle(surface, (60, 200, 60), (csx, csy), 4)
                # Label
                try:
                    cargo_f = pygame.font.SysFont("monospace", 9)
                    cargo_t = cargo_f.render("CARGO", True, (180, 220, 120))
                    surface.blit(cargo_t, (csx - cargo_t.get_width() // 2, csy - 20))
                except Exception:
                    pass
                # RAID indicator when player is close
                dist_cs = math.hypot(cs["x"] - self.player_ship.x,
                                     cs["y"] - self.player_ship.y)
                if dist_cs < 220:
                    try:
                        raid_f = pygame.font.SysFont("monospace", 11, bold=True)
                        r_pulse = abs(math.sin(self._pulse_time * 4))
                        r_col   = (int(200 + 55 * r_pulse), 30, 30)
                        raid_t  = raid_f.render("⚠ RAID  [R]", True, r_col)
                        surface.blit(raid_t, (csx - raid_t.get_width() // 2, csy - 32))
                    except Exception:
                        pass

        # Shield-break boardable indicator: pulsing cyan ring around boardable enemies
        pulse = abs(math.sin(self._pulse_time * 4))
        for ship in self.enemy_ships:
            if not ship.is_destroyed and ship.shield <= 0 and ship.shield_recharge_lock > 0:
                sx = int(ship.x + ox)
                sy = int(ship.y + oy)
                r_lock = ship.shield_recharge_lock
                # Ring pulses and fades as lock ticks down
                intensity = int(80 + 160 * pulse)
                ring_col = (0, intensity, intensity)
                pygame.draw.circle(surface, ring_col, (sx, sy),
                                   30 + int(4 * pulse), 2)
                # Countdown label
                lock_font = self._font
                lock_txt = lock_font.render(
                    f"BOARD ({r_lock:.0f}s)", True, (60, 220, 200))
                surface.blit(lock_txt, (sx - lock_txt.get_width() // 2, sy - 48))

        # ── Player status indicators (EMP / Nebula slow) ─────────────────────
        status_y = 8
        if getattr(self.player_ship, "_emp_slow_mult", 1.0) < 1.0:
            try:
                sf = pygame.font.SysFont("monospace", 12, bold=True)
                st = sf.render("⚡ EMP SLOWED", True, (255, 220, 40))
                surface.blit(st, (sw - st.get_width() - 8, status_y))
                status_y += 18
            except Exception:
                pass
        if getattr(self.player_ship, "_nebula_slow", 1.0) < 1.0:
            try:
                sf = pygame.font.SysFont("monospace", 12, bold=True)
                pulse_neb = abs(math.sin(self._pulse_time * 2))
                neb_alpha = int(160 + 95 * pulse_neb)
                nc = (60, int(120 + 60 * pulse_neb), int(180 + 75 * pulse_neb))
                st = sf.render("\u2601 IN NEBULA", True, nc)
                surface.blit(st, (sw - st.get_width() - 8, status_y))
            except Exception:
                pass

        # Pause overlay
        if self.paused:
            self._draw_pause_overlay(surface)

        # ── Drone deploy menu (drawn on top of everything, replaces pause text) ─
        if self._drone_menu_open:
            self._draw_drone_menu(surface)

        # ── Mini-radar (bottom-left of combat panel) ──────────────────────────
        self._draw_radar(surface, ox, oy)

    def _draw_sector_clear_overlay(self, surface: pygame.Surface) -> None:
        """Banner overlay shown when all enemies are destroyed."""
        sw, sh = surface.get_size()
        t = self._sector_clear_time
        # Fade in over 0.5s
        alpha = min(220, int(t / 0.5 * 220))
        ov = pygame.Surface((sw, 80), pygame.SRCALPHA)
        ov.fill((0, 30, 0, alpha))
        surface.blit(ov, (0, sh // 2 - 40))

        font_lg  = pygame.font.SysFont("monospace", 28, bold=True)
        font_med = pygame.font.SysFont("monospace", 16, bold=True)
        font_sm  = pygame.font.SysFont("monospace", 13)

        title = font_lg.render("✦ SECTOR CLEAR ✦", True, (80, 255, 100))

        # Kill multiplier line  e.g. "5 ships × 100cr = 500cr"
        if self.kills > 0:
            mult_str = f"{self.kills} ship{'s' if self.kills != 1 else ''} × 100cr  =  {self._kill_credits}cr earned"
            mult_col = (255, 220, 80)
        else:
            mult_str = "No ships destroyed"
            mult_col = (140, 140, 140)
        mult_t = font_med.render(mult_str, True, mult_col)

        hint  = font_sm.render("Press G to return to galaxy map", True, (120, 200, 120))

        # Expand overlay to fit all lines
        ov = pygame.Surface((sw, 100), pygame.SRCALPHA)
        ov.fill((0, 30, 0, alpha))
        surface.blit(ov, (0, sh // 2 - 50))

        surface.blit(title,  (sw // 2 - title.get_width()  // 2, sh // 2 - 44))
        surface.blit(mult_t, (sw // 2 - mult_t.get_width() // 2, sh // 2 - 10))
        surface.blit(hint,   (sw // 2 - hint.get_width()   // 2, sh // 2 + 18))

    def _draw_radar(self, surface: pygame.Surface, ox: float, oy: float) -> None:
        """Mini radar:
          player=green centre  enemies=red  allies=cyan
          asteroids/resources=yellow  planets=bright-red markers  debris=yellow diamond
        """
        sw, sh = surface.get_size()
        r       = 60          # slightly larger radar
        # Apply radar_zoom setting (1.0=default, 0.5=zoomed in/closer, 2.0=zoomed out/wider)
        _zoom   = getattr(self, "_radar_zoom", 1.0)
        scale   = 0.055 / max(0.1, _zoom)   # bigger zoom → smaller scale → more detail
        cx      = r + 8       # radar centre on screen (bottom-left)
        cy      = sh - r - 8

        # Background + scanline
        pygame.draw.circle(surface, (8, 14, 8), (cx, cy), r)
        # Subtle scanline sweep (purely decorative)
        import time as _t
        sweep_angle = (_t.time() * 120) % 360
        sa_rad = math.radians(sweep_angle)
        sweep_end = (int(cx + r * math.cos(sa_rad)), int(cy + r * math.sin(sa_rad)))
        sweep_surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.polygon(sweep_surf, (30, 80, 30, 30), [
            (r, r),
            (int(r + r * math.cos(sa_rad - 0.4)), int(r + r * math.sin(sa_rad - 0.4))),
            sweep_end,
        ])
        surface.blit(sweep_surf, (cx - r, cy - r))
        pygame.draw.circle(surface, (30, 70, 30), (cx, cy), r, 2)
        # Range rings
        for ring in (0.33, 0.66):
            pygame.draw.circle(surface, (20, 50, 20), (cx, cy), int(r * ring), 1)
        # Crosshair
        for d in ((-r, 0), (r, 0), (0, -r), (0, r)):
            pygame.draw.line(surface, (25, 60, 25),
                             (cx + d[0] - d[1] // 4, cy + d[1] - d[0] // 4),
                             (cx + d[0] + d[1] // 4, cy + d[1] + d[0] // 4), 1)

        def _plot(wx, wy, col, sz=2):
            """Project a world point onto the radar, clamped to the edge."""
            dx_ = (wx - self.player_ship.x) * scale
            dy_ = (wy - self.player_ship.y) * scale
            d_  = math.hypot(dx_, dy_)
            if d_ > r - sz - 1:
                dx_, dy_ = dx_ / d_ * (r - sz - 1), dy_ / d_ * (r - sz - 1)
            return int(cx + dx_), int(cy + dy_)

        # ── Asteroids / resource nodes (yellow diamond) ───────────────────────
        for ast in self._asteroid_field.asteroids:
            if ast["collected"]:
                continue
            px_, py_ = _plot(ast["x"], ast["y"], (220, 200, 40))
            # Diamond shape
            pygame.draw.polygon(surface, (220, 200, 40),
                [(px_, py_ - 3), (px_ + 3, py_), (px_, py_ + 3), (px_ - 3, py_)])

        # ── Space debris (yellow smaller dot) ─────────────────────────────────
        for piece in self._space_debris.pieces:
            if piece["collected"]:
                continue
            px_, py_ = _plot(piece["x"], piece["y"], (200, 180, 40))
            pygame.draw.circle(surface, (200, 180, 40), (px_, py_), 2)

        # ── Space wreckage (grey larger dot) ──────────────────────────────────
        for piece in self._space_wreckage.pieces:
            if piece["collected"]:
                continue
            px_, py_ = _plot(piece["x"], piece["y"], (120, 120, 140))
            pygame.draw.rect(surface, (120, 120, 140),
                             (px_ - 2, py_ - 2, 4, 4))   # small square = wreck

        # ── Allied ships (cyan) ───────────────────────────────────────────────
        for ship in self.allied_ships:
            if ship.is_destroyed:
                continue
            px_, py_ = _plot(ship.x, ship.y, (60, 200, 200))
            pygame.draw.circle(surface, (60, 200, 200), (px_, py_), 3)

        # ── Enemies (red) ─────────────────────────────────────────────────────
        for ship in self.enemy_ships:
            if ship.is_destroyed:
                continue
            px_, py_ = _plot(ship.x, ship.y, (220, 60, 60))
            pygame.draw.circle(surface, (220, 60, 60), (px_, py_), 3)

        # ── Player (bright green centre) ──────────────────────────────────────
        pygame.draw.circle(surface, (80, 255, 100), (cx, cy), 4)
        pygame.draw.circle(surface, (40, 140, 60), (cx, cy), 4, 1)

        # ── Legend labels (tiny) ──────────────────────────────────────────────
        try:
            leg_f = pygame.font.SysFont("monospace", 8)
            for i, (lbl, col) in enumerate([
                    ("◆ res", (220, 200, 40)),
                    ("● ally", (60, 200, 200)),
                    ("● enemy", (220, 60, 60)),
            ]):
                lt = leg_f.render(lbl, True, col)
                surface.blit(lt, (cx - r, cy + r + 2 + i * 10))
        except Exception:
            pass

    def _draw_health_bar(self, surface, ship, ox=0, oy=0) -> None:
        bw = 44
        bh = 5
        bx = int(ship.x + ox) - bw // 2
        by = int(ship.y + oy) - 34
        # Hull
        pygame.draw.rect(surface, (60, 0, 0),  (bx, by, bw, bh))
        fill = int(bw * (ship.hull / max(ship.max_hull, 1)))
        pygame.draw.rect(surface, SUCCESS,     (bx, by, fill, bh))
        # Shield
        if ship.max_shield > 0:
            pygame.draw.rect(surface, (0, 0, 60), (bx, by - bh - 1, bw, bh))
            sfill = int(bw * (ship.shield / max(ship.max_shield, 1)))
            pygame.draw.rect(surface, (60, 120, 255), (bx, by - bh - 1, sfill, bh))

    def _draw_pause_overlay(self, surface) -> None:
        # Only show generic PAUSED text when NOT in drone menu
        if self._drone_menu_open:
            return
        ov = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 120))
        surface.blit(ov, (0, 0))
        font = pygame.font.SysFont("monospace", 36)
        txt  = font.render("PAUSED — Giving Orders", True, WHITE)
        surface.blit(txt, (surface.get_width() // 2 - txt.get_width() // 2,
                            surface.get_height() // 2 - txt.get_height() // 2))

    def _draw_drone_menu(self, surface: pygame.Surface) -> None:
        """Full-screen drone deploy menu drawn on top of frozen combat."""
        sw, sh = surface.get_size()

        # ── Semi-transparent backdrop ─────────────────────────────────────────
        ov = pygame.Surface((sw, sh), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 170))
        surface.blit(ov, (0, 0))

        # ── Panel dimensions ──────────────────────────────────────────────────
        ICON_SIZE   = 90     # square icon cell size (px)
        ICON_PAD    = 18     # gap between icons
        N           = len(DRONE_TYPES)
        PANEL_W     = N * (ICON_SIZE + ICON_PAD) + ICON_PAD
        PANEL_H     = 320
        px          = (sw - PANEL_W) // 2
        py          = (sh - PANEL_H) // 2

        # Panel background
        pygame.draw.rect(surface, (12, 16, 30), (px, py, PANEL_W, PANEL_H),
                         border_radius=10)
        pygame.draw.rect(surface, (60, 100, 180), (px, py, PANEL_W, PANEL_H),
                         2, border_radius=10)

        # ── Title ─────────────────────────────────────────────────────────────
        font_title = pygame.font.SysFont("monospace", 17, bold=True)
        font_label = pygame.font.SysFont("monospace", 12, bold=True)
        font_sm    = pygame.font.SysFont("monospace", 11)

        title = font_title.render("DEPLOY DRONES", True, (140, 200, 255))
        surface.blit(title, (px + PANEL_W // 2 - title.get_width() // 2, py + 10))

        # Slot info
        active_now = self.drone_system.active_count
        selected   = self._drone_menu_selected_total()
        remaining  = self.drone_system.max_slots - active_now - selected
        slot_col   = (80, 255, 120) if remaining > 0 else (255, 80, 80)
        slot_t = font_sm.render(
            f"Slots used: {active_now + selected} / {self.drone_system.max_slots}"
            f"   Available: {remaining}",
            True, slot_col)
        surface.blit(slot_t, (px + PANEL_W // 2 - slot_t.get_width() // 2, py + 32))

        hint_t = font_sm.render(
            "Click a drone to queue it  ·  Right-click icon to remove one",
            True, (120, 140, 160))
        surface.blit(hint_t, (px + PANEL_W // 2 - hint_t.get_width() // 2, py + 48))

        # ── Drone icon grid ───────────────────────────────────────────────────
        mx_pos, my_pos = pygame.mouse.get_pos()
        self._drone_menu_icon_rects = []
        self._drone_menu_hovered    = None

        icon_y = py + 72
        for i, (dtype, spec) in enumerate(DRONE_TYPES.items()):
            ix = px + ICON_PAD + i * (ICON_SIZE + ICON_PAD)
            rect = pygame.Rect(ix, icon_y, ICON_SIZE, ICON_SIZE)
            self._drone_menu_icon_rects.append((dtype, rect))

            hovered = rect.collidepoint(mx_pos, my_pos)
            if hovered:
                self._drone_menu_hovered = dtype

            # Icon background: brightens on hover
            bg_col = (20, 40, 70) if not hovered else (30, 60, 110)
            sel_count = self._drone_menu_selection[dtype]
            # Green tint when this type is queued
            if sel_count > 0:
                bg_col = (10, 50, 20) if not hovered else (15, 70, 30)
            pygame.draw.rect(surface, bg_col, rect, border_radius=8)
            pygame.draw.rect(surface, spec["color"], rect, 2, border_radius=8)

            # Drone body icon — diamond with glow colour
            cx_ = rect.centerx
            cy_ = rect.centery - 8
            sz_ = 18
            drone_pts = [(cx_, cy_ - sz_), (cx_ + sz_, cy_),
                         (cx_, cy_ + sz_), (cx_ - sz_, cy_)]
            pygame.draw.polygon(surface, spec["glow_color"], drone_pts)
            pygame.draw.polygon(surface, (255, 255, 255), drone_pts, 1)
            pygame.draw.circle(surface, (255, 255, 255), (cx_, cy_), 4)

            # Label (drone name)
            lbl = font_label.render(spec["label"], True, spec["color"])
            surface.blit(lbl, (rect.centerx - lbl.get_width() // 2,
                                rect.bottom - 28))

            # Count badge (queued this session)
            count_col = (80, 255, 80) if sel_count > 0 else (80, 80, 100)
            cnt_t = font_label.render(str(sel_count), True, count_col)
            surface.blit(cnt_t, (rect.centerx - cnt_t.get_width() // 2,
                                  rect.bottom - 14))

            # Max-slot ring indicator
            if remaining <= 0 and sel_count == 0:
                # Dim out with "FULL" label if no room
                full_t = font_sm.render("FULL", True, (160, 80, 80))
                surface.blit(full_t, (rect.centerx - full_t.get_width() // 2,
                                       rect.top + 6))

        # ── Tooltip: hovered drone stats ─────────────────────────────────────
        hov = self._drone_menu_hovered
        if hov:
            spec = DRONE_TYPES[hov]
            tip_lines = [
                spec["label"].upper(),
                spec["desc"],
                f"Duration: {spec['duration']:.0f}s",
            ]
            if spec.get("damage"):
                tip_lines.append(f"Damage: {spec['damage']} / {spec.get('fire_cd', 0):.1f}s")
            if spec.get("heal_rate"):
                tip_lines.append(f"Heal: {spec['heal_rate']:.0f} HP/s")
            if spec.get("radar_bonus"):
                tip_lines.append(f"Radar bonus: +{spec['radar_bonus']} px")
            if spec.get("shield_bonus"):
                tip_lines.append(f"Shield bonus: +{spec['shield_bonus']}")
            if spec.get("emp_slow"):
                tip_lines.append(f"EMP slow: {int(spec['emp_slow']*100)}%  for {spec['emp_dur']:.0f}s")

            tip_font_b = pygame.font.SysFont("monospace", 12, bold=True)
            tip_font   = pygame.font.SysFont("monospace", 11)
            tip_max_w  = max((tip_font.size(l)[0] for l in tip_lines[1:]), default=180) + 20
            tip_w      = max(tip_max_w, tip_font_b.size(tip_lines[0])[0] + 20)
            tip_h      = 16 + len(tip_lines) * 15 + 6
            tip_x      = min(mx_pos + 14, sw - tip_w - 6)
            tip_y      = max(my_pos - tip_h - 4, 4)
            pygame.draw.rect(surface, (8, 12, 24), (tip_x, tip_y, tip_w, tip_h),
                             border_radius=5)
            pygame.draw.rect(surface, spec["color"], (tip_x, tip_y, tip_w, tip_h),
                             1, border_radius=5)
            ty = tip_y + 6
            # Title line
            t0 = tip_font_b.render(tip_lines[0], True, spec["color"])
            surface.blit(t0, (tip_x + 8, ty)); ty += 15
            for line in tip_lines[1:]:
                tl = tip_font.render(line, True, (200, 220, 240))
                surface.blit(tl, (tip_x + 8, ty)); ty += 14

        # ── Bottom button row ─────────────────────────────────────────────────
        btn_y     = py + PANEL_H - 44
        btn_h     = 32
        can_launch = selected > 0

        # LAUNCH button (green, shown when selection > 0)
        launch_w = 140
        launch_x = px + PANEL_W // 2 - launch_w - 6
        launch_rect = pygame.Rect(launch_x, btn_y, launch_w, btn_h)
        launch_bg = (15, 55, 15) if can_launch else (30, 30, 30)
        launch_bc = (60, 200, 80) if can_launch else (50, 50, 50)
        pygame.draw.rect(surface, launch_bg, launch_rect, border_radius=5)
        pygame.draw.rect(surface, launch_bc, launch_rect, 2, border_radius=5)
        launch_lbl = font_label.render(
            f"LAUNCH  ({selected})" if can_launch else "LAUNCH",
            True, launch_bc)
        surface.blit(launch_lbl, (launch_rect.centerx - launch_lbl.get_width() // 2,
                                   launch_rect.centery - launch_lbl.get_height() // 2))
        self._drone_menu_launch_rect = launch_rect

        # BACK TO BATTLE button (always shown)
        close_w  = 140
        close_x  = px + PANEL_W // 2 + 6
        close_rect = pygame.Rect(close_x, btn_y, close_w, btn_h)
        pygame.draw.rect(surface, (30, 20, 20), close_rect, border_radius=5)
        pygame.draw.rect(surface, (180, 80, 80), close_rect, 2, border_radius=5)
        close_lbl = font_label.render("BACK TO BATTLE", True, (220, 120, 120))
        surface.blit(close_lbl, (close_rect.centerx - close_lbl.get_width() // 2,
                                   close_rect.centery - close_lbl.get_height() // 2))
        self._drone_menu_close_rect = close_rect
