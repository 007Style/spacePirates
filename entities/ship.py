"""entities/ship.py — Ship class: modular grid, stations, crew, weapons, quirks."""
from __future__ import annotations
import pygame
import math
from progression.rarity import rarity_system
from entities.crew    import Crew, STATION_PRIMARY_STAT
from entities.weapon  import Weapon
from entities.drone   import Drone


# All station types
STATIONS = [
    "cockpit", "gun_turret", "engine_room",
    "repair_station", "drone_bay", "brig",
]


class ShipModule:
    """A module placed in a free slot on the ship grid."""
    def __init__(self, module_id: str, name: str, effect: dict):
        self.module_id = module_id
        self.name      = name
        self.effect    = effect  # e.g. {"hull_bonus": 50} or {"shield_bonus": 30}

    def to_dict(self) -> dict:
        return {"module_id": self.module_id, "name": self.name, "effect": self.effect}


class Ship(pygame.sprite.Sprite):
    # Hull type passive modifiers
    HULL_MODIFIERS = {
        "light":    {"speed_mult": 1.2, "hull_mult": 0.8,  "regen": 0},
        "medium":   {"speed_mult": 1.0, "hull_mult": 1.0,  "regen": 0},
        "heavy":    {"speed_mult": 0.8, "hull_mult": 1.3,  "regen": 0},
        "adaptive": {"speed_mult": 1.0, "hull_mult": 1.0,  "regen": 2},  # HP/sec regen
    }

    def __init__(self, data: dict):
        super().__init__()
        # Store raw data dict so AI systems can query carrier-specific fields
        self._data       = data
        self.id          = data["id"]
        self.name        = data.get("name", "Unknown Ship")
        self.ship_class  = data.get("class", "fighter")
        self.rarity      = data.get("rarity", "common")
        self.description = data.get("description", "")
        self.lore        = data.get("lore", "")
        self.price       = data.get("price", 0)
        self.contraband  = data.get("contraband", False)
        self.quirks: list[str] = list(data.get("quirks", []))

        mult = rarity_system.stat_multiplier(self.rarity)
        self.max_hull    = round(data.get("max_hull", 100) * mult)
        self.max_shield  = round(data.get("max_shield", 50) * mult)
        self.base_speed  = data.get("base_speed", 120)
        self.base_evasion= data.get("base_evasion", 0.05)
        self.fuel_capacity = data.get("fuel_capacity", 100)
        self.fuel        = self.fuel_capacity
        self.supplies    = 50

        # Apply hull type modifiers
        self.hull_type   = data.get("hull_type", "light")
        mods = self.HULL_MODIFIERS.get(self.hull_type, self.HULL_MODIFIERS["light"])
        self.max_hull    = round(self.max_hull  * mods["hull_mult"])
        self.speed       = round(self.base_speed * mods["speed_mult"])
        self._hp_regen   = mods["regen"]

        self.hull        = float(self.max_hull)
        self.shield      = float(self.max_shield)

        # Crew slots
        self.crew_slots:  int                   = data.get("crew_slots", 3)
        self.crew:        list[Crew]            = []
        self.station_assignments: dict[str, Crew | None] = {s: None for s in STATIONS}

        # Module slots
        self.free_module_slots: int             = data.get("free_module_slots", 2)
        self.modules:           list[ShipModule]= []

        # Weapons (by hardpoint size)
        self.hardpoint_slots: dict              = data.get("hardpoint_slots", {"small": 1, "medium": 0, "large": 0})
        self.weapons:         list[Weapon]      = []

        # Drones
        self.drones:          list[Drone]       = []
        self.drone_slots:     int               = data.get("drone_slots", 0)

        # Fighter bay (carrier ships only)
        self.bay_slots: int = data.get("bay_slots", 0)
        if self.bay_slots > 0:
            from fleet.bay import BaySystem
            self.bay = BaySystem(capacity=self.bay_slots)
        else:
            self.bay = None   # non-carrier ships have no bay

        # Bay membership flag (set True when docked inside another carrier)
        self._in_bay: bool = False

        # Specialization
        self.specialization_paths = data.get("specialization_paths", {})
        self.chosen_path: str | None            = None

        # Cosmetics
        self.custom_name:   str  = self.name
        self.color_scheme:  tuple= (100, 180, 255)
        self.insignia:      str  = ""

        # Fleet order
        self.fleet_order:   str  = "standby"

        # In-combat position
        self.x = 0.0
        self.y = 0.0
        self.angle = 0.0  # degrees, facing direction
        self.vx = 0.0
        self.vy = 0.0

        # Active status effects: {effect_name: ticks_remaining}
        self.status_effects: dict[str, float] = {}

        # Shield break recharge lock: counts down after shield hits 0
        # Shield cannot regen until this reaches 0
        self.shield_recharge_lock: float = 0.0

        self._build_sprite()

    # ── Sprite ───────────────────────────────────────────────────────────────
    def _build_sprite(self) -> None:
        color = self.color_scheme
        dim   = self._sprite_dims()
        w, h  = dim
        self.image = pygame.Surface((w, h), pygame.SRCALPHA)
        self._draw_ship_shape(self.image, color, w, h)
        self.rect  = self.image.get_rect()
        # Store rotated base for use during draw
        self._base_image = self.image.copy()

    def _sprite_dims(self) -> tuple[int, int]:
        return {
            "fighter":          (56, 36),
            "interceptor":      (52, 28),
            "scout":            (48, 28),
            "gunship":          (64, 44),
            "corvette":         (68, 42),
            "destroyer":        (76, 50),
            "stealth":          (62, 36),
            "freighter":        (64, 46),
            "mining_barge":     (72, 52),
            "assault_transport":(76, 54),
            "battlecruiser":    (96, 64),
            "carrier":          (90, 62),
            "pirate_carrier":   (96, 68),   # wider + taller for the marauder silhouette
            "dreadnought":      (72, 50),
        }.get(self.ship_class, (56, 36))

    def _draw_ship_shape(self, surf: "pygame.Surface", color: tuple,
                         w: int, h: int) -> None:
        import pygame as pg
        r, g, b = color[:3]
        dark    = (max(0, r - 70),  max(0, g - 70),  max(0, b - 70))
        mid     = (max(0, r - 30),  max(0, g - 30),  max(0, b - 30))
        light   = (min(255, r + 80), min(255, g + 80), min(255, b + 80))
        trim    = (min(255, r + 120), min(255, g + 120), min(255, b + 120))
        cx, cy  = w // 2, h // 2

        def _glow(surface, col, pos, radius):
            """Draw a soft multi-ring glow."""
            gx, gy = pos
            for ri, alpha in [(radius + 3, 30), (radius + 1, 70), (radius, 140)]:
                gsurf = pg.Surface((ri * 2, ri * 2), pg.SRCALPHA)
                pg.draw.circle(gsurf, (*col, alpha), (ri, ri), ri)
                surface.blit(gsurf, (gx - ri, gy - ri), special_flags=pg.BLEND_ALPHA_SDL2)

        sc = self.ship_class

        if sc == "fighter":
            # ── Sleek needle-nose interceptor ────────────────────────────────
            # Main fuselage (dark centre stripe)
            fuselage = [(w - 2, cy), (cx + 6, cy - 3), (cx - 10, cy - 4),
                        (4, cy - 2), (4, cy + 2), (cx - 10, cy + 4),
                        (cx + 6, cy + 3)]
            pg.draw.polygon(surf, dark, fuselage)
            pg.draw.polygon(surf, mid, fuselage, 1)
            # Swept delta wings
            wing_u = [(cx + 4, cy - 3), (cx - 8, 2), (2, cy - 1), (cx - 4, cy - 3)]
            wing_d = [(cx + 4, cy + 3), (cx - 8, h - 2), (2, cy + 1), (cx - 4, cy + 3)]
            pg.draw.polygon(surf, color, wing_u)
            pg.draw.polygon(surf, color, wing_d)
            # Wing edge highlight
            pg.draw.line(surf, light, (cx + 4, cy - 3), (cx - 8, 2), 1)
            pg.draw.line(surf, light, (cx + 4, cy + 3), (cx - 8, h - 2), 1)
            # Nose tip
            pg.draw.polygon(surf, light, [(w - 2, cy), (cx + 6, cy - 3), (cx + 6, cy + 3)])
            # Cockpit canopy (small tinted rect)
            canopy = pg.Rect(cx + 2, cy - 4, 12, 8)
            pg.draw.rect(surf, (40, 120, 220), canopy)
            pg.draw.rect(surf, trim, canopy, 1)
            # Canopy glare line
            pg.draw.line(surf, (160, 200, 255), (cx + 4, cy - 3), (cx + 12, cy - 3), 1)
            # Engine nozzle
            eng_r = pg.Rect(2, cy - 4, 6, 8)
            pg.draw.rect(surf, dark, eng_r)
            pg.draw.rect(surf, (60, 60, 80), eng_r, 1)
            # Engine glow
            _glow(surf, (60, 140, 255), (5, cy), 4)
            # Weapon hardpoints on wings
            pg.draw.rect(surf, dark, pg.Rect(cx - 2, cy - 9, 6, 3))
            pg.draw.rect(surf, dark, pg.Rect(cx - 2, cy + 6, 6, 3))
            # Panel lines (detail)
            pg.draw.line(surf, mid, (cx - 6, cy), (cx + 8, cy), 1)

        elif sc == "freighter":
            # ── Heavy bulk hauler with cargo pods ────────────────────────────
            # Main spine hull
            spine = pg.Rect(10, cy - 6, w - 20, 12)
            pg.draw.rect(surf, dark, spine)
            pg.draw.rect(surf, mid, spine, 1)
            # Cargo pods top + bottom
            pod_t = [(w - 10, cy - 5), (cx - 6, 2), (6, cy - 9), (w - 16, cy - 5)]
            pod_b = [(w - 10, cy + 5), (cx - 6, h - 2), (6, cy + 9), (w - 16, cy + 5)]
            pg.draw.polygon(surf, color, pod_t)
            pg.draw.polygon(surf, color, pod_b)
            # Pod trim lines
            pg.draw.line(surf, light, (w - 10, cy - 5), (cx - 6, 2), 1)
            pg.draw.line(surf, light, (w - 10, cy + 5), (cx - 6, h - 2), 1)
            # Panel detail stripes on pods
            for px in [cx - 2, cx + 8]:
                pg.draw.line(surf, mid, (px, 5), (px, cy - 6), 1)
                pg.draw.line(surf, mid, (px, cy + 6), (px, h - 5), 1)
            # Command bridge (raised section)
            bridge = pg.Rect(w - 18, cy - 9, 12, 18)
            pg.draw.rect(surf, mid, bridge)
            pg.draw.rect(surf, light, bridge, 1)
            # Bridge windows (3 dots)
            for wy in [cy - 4, cy, cy + 4]:
                pg.draw.circle(surf, (120, 200, 255), (w - 13, wy), 1)
            # Nose sensor array
            pg.draw.polygon(surf, light, [(w - 2, cy), (w - 10, cy - 5), (w - 10, cy + 5)])
            # Dual engine nozzles
            eng1 = pg.Rect(4, cy - 7, 8, 6)
            eng2 = pg.Rect(4, cy + 1, 8, 6)
            pg.draw.rect(surf, dark, eng1)
            pg.draw.rect(surf, dark, eng2)
            pg.draw.rect(surf, (60, 60, 80), eng1, 1)
            pg.draw.rect(surf, (60, 60, 80), eng2, 1)
            _glow(surf, (60, 140, 255), (7, cy - 4), 4)
            _glow(surf, (60, 140, 255), (7, cy + 4), 4)
            # Docking clamp detail
            pg.draw.rect(surf, dark, pg.Rect(cx - 4, cy - 3, 3, 6))

        elif sc == "pirate_carrier":
            # ── Marauder Carrier — heavy converted warship bristling with guns ──
            # Massive battle-worn hull
            hull = pg.Rect(4, cy - 18, w - 8, 36)
            pg.draw.rect(surf, dark, hull)
            pg.draw.rect(surf, mid, hull, 2)
            # Armour plating lines (battle damage pattern)
            for ay in [cy - 14, cy - 8, cy - 2, cy + 2, cy + 8, cy + 14]:
                pg.draw.line(surf, mid, (8, ay), (w - 8, ay), 1)
            # Battle-scarred prow (heavy angle)
            prow = [(w - 2, cy), (w - 18, cy - 14), (cx - 2, cy - 18),
                    (cx - 2, cy + 18), (w - 18, cy + 14)]
            pg.draw.polygon(surf, mid, prow)
            pg.draw.polygon(surf, (200, 80, 60), prow, 2)   # red trim = danger
            # Bay door slots (fighter launch bays)
            bay_col = (30, 50, 70)
            for bx_ in [cx + 2, cx + 12, cx + 22]:
                bay = pg.Rect(bx_, cy - 10, 7, 20)
                pg.draw.rect(surf, bay_col, bay)
                pg.draw.rect(surf, (60, 100, 140), bay, 1)
            # Gun turrets (6 heavy mounts along hull)
            for ty, tx_off in [(cy - 18, 0), (cy - 8, 6), (cy + 2, 6),
                               (cy + 14, 0), (cy - 18, cx - 4), (cy + 14, cx - 4)]:
                turret = pg.Rect(tx_off + 8, ty, 14, 5)
                pg.draw.rect(surf, mid, turret)
                pg.draw.rect(surf, (220, 80, 60), turret, 1)
                barrel_len = 10 if tx_off == 0 else 7
                pg.draw.line(surf, (200, 60, 60),
                             (turret.right, ty + 2),
                             (turret.right + barrel_len, ty + 2), 2)
            # Command bridge (top-centre, armoured bunker)
            bridge = pg.Rect(cx - 4, cy - 26, 20, 12)
            pg.draw.rect(surf, mid, bridge)
            pg.draw.rect(surf, (200, 80, 60), bridge, 1)
            for bx_ in [cx - 1, cx + 5, cx + 11]:
                pg.draw.circle(surf, (200, 80, 80), (bx_, cy - 20), 2)
            # Pirate skull emblem (stylised dots on centre hull)
            pg.draw.circle(surf, (180, 40, 40), (cx + 10, cy), 4)
            pg.draw.circle(surf, (220, 60, 60), (cx + 10, cy), 4, 1)
            # 6 heavy engines (asymmetric battle arrangement)
            for ey in [cy - 15, cy - 8, cy - 1, cy + 5, cy + 12, cy + 18]:
                er = pg.Rect(2, ey, 9, 5)
                pg.draw.rect(surf, dark, er)
                pg.draw.rect(surf, (40, 40, 60), er, 1)
                _glow(surf, (255, 120, 60), (6, ey + 2), 3)   # orange engines = pirate
            # Boarding spike on prow tip
            pg.draw.line(surf, (180, 60, 40), (w - 2, cy), (w + 4, cy), 2)

        elif sc in ("carrier", "carrier_mk1_large"):
            # ── Massive carrier supercarrier ──────────────────────────────────
            # Flat flight deck hull
            deck = pg.Rect(6, cy - 12, w - 12, 24)
            pg.draw.rect(surf, dark, deck)
            pg.draw.rect(surf, mid, deck, 1)
            # Armoured prow
            prow = [(w - 4, cy), (w - 16, cy - 8), (cx, cy - 12),
                    (cx, cy + 12), (w - 16, cy + 8)]
            pg.draw.polygon(surf, mid, prow)
            pg.draw.polygon(surf, light, prow, 1)
            # Island superstructure (bridge tower)
            island = pg.Rect(cx + 4, cy - 20, 14, 16)
            pg.draw.rect(surf, mid, island)
            pg.draw.rect(surf, light, island, 1)
            # Bridge windows row
            for bx in [cx + 7, cx + 11, cx + 15]:
                pg.draw.circle(surf, (120, 200, 255), (bx, cy - 14), 2)
            # Radar antenna
            pg.draw.line(surf, light, (cx + 11, cy - 20), (cx + 11, cy - 26), 1)
            pg.draw.circle(surf, light, (cx + 11, cy - 26), 2, 1)
            # Flight deck catapult lines
            pg.draw.line(surf, light, (w - 14, cy - 8), (cx + 4, cy - 8), 1)
            pg.draw.line(surf, light, (w - 14, cy + 8), (cx + 4, cy + 8), 1)
            pg.draw.line(surf, (100, 200, 100), (w - 14, cy - 1), (10, cy - 1), 1)
            # Wing sponsons
            pg.draw.polygon(surf, color,
                [(w - 8, cy - 12), (8, 4), (4, cy - 14), (cx - 4, cy - 12)])
            pg.draw.polygon(surf, color,
                [(w - 8, cy + 12), (8, h - 4), (4, cy + 14), (cx - 4, cy + 12)])
            # Sponson detail
            pg.draw.line(surf, light, (w - 8, cy - 12), (8, 4), 1)
            pg.draw.line(surf, light, (w - 8, cy + 12), (8, h - 4), 1)
            # Engine bank (4 nozzles)
            for ei, ey in enumerate([cy - 9, cy - 3, cy + 3, cy + 9]):
                er = pg.Rect(4 + ei % 2 * 2, ey - 2, 8, 5)
                pg.draw.rect(surf, dark, er)
                pg.draw.rect(surf, (50, 50, 70), er, 1)
                _glow(surf, (80, 150, 255), (7, ey), 3)

        elif sc == "dreadnought":
            # ── Void Dreadnought — hulking warship ────────────────────────────
            # Massive armoured hull
            hull = pg.Rect(4, cy - 14, w - 8, 28)
            pg.draw.rect(surf, dark, hull)
            pg.draw.rect(surf, mid, hull, 2)
            # Layered armour plates
            for ay in [cy - 11, cy - 5, cy + 5, cy + 11]:
                pg.draw.line(surf, mid, (8, ay), (w - 8, ay), 1)
            # Heavy prow ram
            prow = [(w - 2, cy), (w - 12, cy - 10), (cx + 4, cy - 14),
                    (cx + 4, cy + 14), (w - 12, cy + 10)]
            pg.draw.polygon(surf, mid, prow)
            pg.draw.polygon(surf, trim, prow, 1)
            # Command citadel
            citadel = pg.Rect(cx - 2, cy - 18, 18, 12)
            pg.draw.rect(surf, mid, citadel)
            pg.draw.rect(surf, trim, citadel, 1)
            pg.draw.circle(surf, (140, 200, 255), (cx + 6, cy - 12), 2)
            # Heavy gun turrets
            for ty in [cy - 8, cy + 6]:
                turret = pg.Rect(cx - 8, ty, 12, 6)
                pg.draw.rect(surf, mid, turret)
                pg.draw.rect(surf, light, turret, 1)
                pg.draw.line(surf, light, (cx + 4, ty + 3), (w - 4, ty + 3), 2)
            # Quad engines
            for ey in [cy - 10, cy - 4, cy + 4, cy + 10]:
                er = pg.Rect(2, ey - 2, 10, 5)
                pg.draw.rect(surf, dark, er)
                pg.draw.rect(surf, (50, 50, 80), er, 1)
                _glow(surf, (100, 100, 255), (7, ey), 4)
            # Hull panel lines
            for px in [cx - 4, cx + 4, cx + 10]:
                pg.draw.line(surf, dark, (px, cy - 14), (px, cy + 14), 1)

        elif sc == "corvette":
            # ── Mid-weight Corvette — sleek hull with swept wings & twin guns ──
            # Central hull spine
            spine = [(w - 4, cy), (cx + 2, cy - 5), (cx - 10, cy - 4),
                     (6, cy - 2), (6, cy + 2), (cx - 10, cy + 4), (cx + 2, cy + 5)]
            pg.draw.polygon(surf, dark, spine)
            pg.draw.polygon(surf, mid, spine, 1)
            # Swept mid wings
            wing_u = [(cx + 6, cy - 4), (cx - 12, 4), (4, cy - 2), (cx - 4, cy - 4)]
            wing_d = [(cx + 6, cy + 4), (cx - 12, h - 4), (4, cy + 2), (cx - 4, cy + 4)]
            pg.draw.polygon(surf, color, wing_u)
            pg.draw.polygon(surf, color, wing_d)
            # Wing highlight edges
            pg.draw.line(surf, light, (cx + 6, cy - 4), (cx - 12, 4), 1)
            pg.draw.line(surf, light, (cx + 6, cy + 4), (cx - 12, h - 4), 1)
            # Nose section (heavier prow than fighter)
            prow = [(w - 4, cy), (cx + 4, cy - 5), (cx + 4, cy + 5)]
            pg.draw.polygon(surf, light, prow)
            # Twin gun barrels on wings
            for gy in [cy - 8, cy + 6]:
                barrel = pg.Rect(cx - 4, gy, 14, 2)
                pg.draw.rect(surf, mid, barrel)
                pg.draw.rect(surf, trim, barrel, 1)
            # Cockpit canopy
            canopy = pg.Rect(cx + 2, cy - 5, 14, 10)
            pg.draw.rect(surf, (40, 120, 220), canopy)
            pg.draw.rect(surf, trim, canopy, 1)
            pg.draw.line(surf, (160, 200, 255), (cx + 4, cy - 4), (cx + 14, cy - 4), 1)
            # Dual engine nozzles
            for ey in [cy - 5, cy + 3]:
                er = pg.Rect(4, ey, 7, 5)
                pg.draw.rect(surf, dark, er)
                pg.draw.rect(surf, (60, 60, 80), er, 1)
                _glow(surf, (80, 160, 255), (7, ey + 2), 4)
            # Panel line
            pg.draw.line(surf, mid, (cx - 8, cy), (cx + 10, cy), 1)

        elif sc == "interceptor":
            # ── Stinger Interceptor — needle-thin arrow, pure speed ───────────
            # Ultra-slim fuselage
            fuse = [(w - 2, cy), (cx + 2, cy - 2), (6, cy - 1),
                    (6, cy + 1), (cx + 2, cy + 2)]
            pg.draw.polygon(surf, dark, fuse)
            pg.draw.polygon(surf, mid, fuse, 1)
            # Swept delta wings — razor thin
            wing_u = [(cx + 4, cy - 2), (cx - 12, 2), (2, cy), (cx - 4, cy - 2)]
            wing_d = [(cx + 4, cy + 2), (cx - 12, h - 2), (2, cy), (cx - 4, cy + 2)]
            pg.draw.polygon(surf, color, wing_u)
            pg.draw.polygon(surf, color, wing_d)
            pg.draw.line(surf, light, (cx + 4, cy - 2), (cx - 12, 2), 1)
            pg.draw.line(surf, light, (cx + 4, cy + 2), (cx - 12, h - 2), 1)
            # Needle nose — bright tip
            pg.draw.polygon(surf, trim, [(w - 2, cy), (cx + 2, cy - 2), (cx + 2, cy + 2)])
            # Mid-wing sensor bumps
            for bx_ in [cx - 2, cx - 8]:
                pg.draw.circle(surf, mid, (bx_, cy - 3), 1)
                pg.draw.circle(surf, mid, (bx_, cy + 3), 1)
            # Twin engine nozzles (stacked vertically)
            for ey in [cy - 3, cy + 1]:
                eng = pg.Rect(2, ey, 6, 3)
                pg.draw.rect(surf, dark, eng)
                pg.draw.rect(surf, (50, 60, 90), eng, 1)
            # Afterburner glows — dual afterburners
            _glow(surf, (120, 180, 255), (5, cy - 1), 4)
            _glow(surf, (120, 180, 255), (5, cy + 2), 4)
            _glow(surf, (200, 120, 255), (4, cy), 2)   # central purple highlight
            # Cockpit slit
            pg.draw.rect(surf, (40, 100, 200), pg.Rect(cx + 4, cy - 2, 10, 4))
            pg.draw.rect(surf, (120, 160, 255), pg.Rect(cx + 4, cy - 2, 10, 4), 1)
            # Panel detail line
            pg.draw.line(surf, mid, (cx - 4, cy), (cx + 8, cy), 1)

        elif sc == "scout":
            # ── Wraith Scout — flat disc with sensor boom + side fins ─────────
            import math as _m
            # Flat oval body (smooth polygon)
            body_pts = []
            for i in range(20):
                a  = _m.radians(i * 18)
                rx = int(w * 0.30 * _m.cos(a))
                ry = int(h * 0.36 * _m.sin(a))
                body_pts.append((cx + rx, cy + ry))
            pg.draw.polygon(surf, dark, body_pts)
            pg.draw.polygon(surf, mid, body_pts, 1)
            # Layered tinted body rings (depth effect)
            inner_pts = [(cx + int(w*0.20*_m.cos(_m.radians(i*22.5))),
                          cy + int(h*0.24*_m.sin(_m.radians(i*22.5)))) for i in range(16)]
            pg.draw.polygon(surf, mid, inner_pts, 1)
            # Sensor boom — forward spike with tip glow
            pg.draw.line(surf, light, (cx + 4, cy), (w - 3, cy), 2)
            pg.draw.line(surf, trim,  (cx + 4, cy), (cx + 14, cy), 1)
            pg.draw.circle(surf, (200, 240, 255), (w - 3, cy), 3)
            pg.draw.circle(surf, trim, (w - 3, cy), 3, 1)
            # Side antenna fins (stubby)
            pg.draw.line(surf, light, (cx, cy - 4), (cx - 8, cy - 8), 1)
            pg.draw.line(surf, light, (cx, cy + 4), (cx - 8, cy + 8), 1)
            # Rear engine pod (wider)
            eg = pg.Rect(2, cy - 4, 8, 8)
            pg.draw.rect(surf, dark, eg)
            pg.draw.rect(surf, (40, 60, 80), eg, 1)
            # Dual blue ion engines
            _glow(surf, (60, 220, 255), (6, cy - 2), 4)
            _glow(surf, (60, 220, 255), (6, cy + 2), 3)
            # Cockpit dome (hemispherical highlight)
            pg.draw.circle(surf, (40, 120, 220), (cx + 4, cy), 6)
            pg.draw.circle(surf, (160, 220, 255), (cx + 4, cy), 6, 1)
            # Glare spot on dome
            pg.draw.circle(surf, (220, 240, 255), (cx + 6, cy - 2), 2)
            # Panel detail: radial lines around dome
            for ai in range(6):
                ar = _m.radians(ai * 60)
                dx2 = int(8 * _m.cos(ar)); dy2 = int(8 * _m.sin(ar))
                pg.draw.line(surf, (40, 50, 70), (cx + 4, cy), (cx + 4 + dx2, cy + dy2), 1)

        elif sc == "gunship":
            # ── Ironjaw Gunship — wide weapons platform ───────────────────────
            # Flat slab hull
            hull = pg.Rect(8, cy - 10, w - 16, 20)
            pg.draw.rect(surf, dark, hull)
            pg.draw.rect(surf, mid, hull, 1)
            # Gun pod port side
            for gpy in [cy - 14, cy - 7, cy + 5, cy + 12]:
                gp = pg.Rect(cx - 2, gpy, 20, 4)
                pg.draw.rect(surf, mid, gp)
                pg.draw.rect(surf, light, gp, 1)
                # Barrel extension
                pg.draw.line(surf, trim, (cx + 18, gpy + 2), (w - 4, gpy + 2), 2)
            # Cockpit slab
            cb = pg.Rect(w - 16, cy - 7, 12, 14)
            pg.draw.rect(surf, mid, cb)
            pg.draw.rect(surf, trim, cb, 1)
            for wy in [cy - 3, cy + 3]:
                pg.draw.circle(surf, (120, 200, 255), (w - 10, wy), 2)
            # Dual engine bank
            for ey in [cy - 7, cy + 5]:
                er = pg.Rect(4, ey, 8, 5)
                pg.draw.rect(surf, dark, er)
                _glow(surf, (60, 140, 255), (7, ey + 2), 4)

        elif sc == "destroyer":
            # ── Hammerfall Destroyer — heavy forward-ramming warship ──────────
            # Thick armoured hull
            hull = pg.Rect(6, cy - 14, w - 12, 28)
            pg.draw.rect(surf, dark, hull)
            pg.draw.rect(surf, mid, hull, 2)
            # Armour plate lines
            for ay in [cy - 10, cy - 4, cy + 4, cy + 10]:
                pg.draw.line(surf, mid, (10, ay), (w - 10, ay), 1)
            # RAM PROW — thick wedge nose
            prow = [(w - 2, cy), (w - 16, cy - 10), (cx + 2, cy - 14),
                    (cx + 2, cy + 14), (w - 16, cy + 10)]
            pg.draw.polygon(surf, trim, prow)
            pg.draw.polygon(surf, (255, 180, 60), prow, 2)
            # Command tower
            ct = pg.Rect(cx - 2, cy - 20, 16, 12)
            pg.draw.rect(surf, mid, ct)
            pg.draw.rect(surf, trim, ct, 1)
            pg.draw.circle(surf, (140, 200, 255), (cx + 6, cy - 14), 2)
            # Heavy guns port+stbd
            for ty in [cy - 8, cy + 4]:
                tg = pg.Rect(cx - 6, ty, 16, 5)
                pg.draw.rect(surf, mid, tg)
                pg.draw.rect(surf, light, tg, 1)
                pg.draw.line(surf, trim, (cx + 10, ty + 2), (w - 6, ty + 2), 2)
            # Triple engine bank
            for ey in [cy - 9, cy - 1, cy + 7]:
                er = pg.Rect(2, ey, 9, 5)
                pg.draw.rect(surf, dark, er)
                _glow(surf, (80, 140, 255), (6, ey + 2), 4)

        elif sc == "stealth":
            # ── Shadowfang — low-profile with angular stealth facets ──────────
            # Faceted stealth body — flat diamond cross-section
            fuse = [(w - 4, cy), (cx + 8, cy - 5), (cx - 8, cy - 3),
                    (4, cy), (cx - 8, cy + 3), (cx + 8, cy + 5)]
            pg.draw.polygon(surf, dark, fuse)
            # Hard angular facets (no curves)
            facet_u = [(cx + 8, cy - 5), (cx - 8, cy - 3),
                       (cx - 4, 3), (cx + 6, cy - 5)]
            facet_d = [(cx + 8, cy + 5), (cx - 8, cy + 3),
                       (cx - 4, h - 3), (cx + 6, cy + 5)]
            pg.draw.polygon(surf, mid, facet_u)
            pg.draw.polygon(surf, mid, facet_d)
            # Stealth edge lines (sharp, no glow)
            pg.draw.line(surf, (40, 60, 80), (4, cy), (cx - 8, cy - 3), 1)
            pg.draw.line(surf, (40, 60, 80), (4, cy), (cx - 8, cy + 3), 1)
            # Nose sensor tip (barely visible)
            pg.draw.line(surf, (80, 100, 120), (w - 4, cy), (cx + 8, cy - 5), 1)
            pg.draw.line(surf, (80, 100, 120), (w - 4, cy), (cx + 8, cy + 5), 1)
            # Cockpit — just a dark slit
            pg.draw.rect(surf, (20, 40, 70), pg.Rect(cx + 4, cy - 3, 12, 6))
            pg.draw.rect(surf, (50, 80, 120), pg.Rect(cx + 4, cy - 3, 12, 6), 1)
            # Minimal exhaust (stealth-shielded)
            _glow(surf, (30, 80, 160), (5, cy), 3)

        elif sc == "mining_barge":
            # ── Orebreaker Mining Barge — industrial bulk with drill nose ─────
            # Wide boxy hull
            hull = pg.Rect(8, cy - 16, w - 16, 32)
            pg.draw.rect(surf, dark, hull)
            pg.draw.rect(surf, mid, hull, 2)
            # Cargo tanks (side bulges)
            for ty in [cy - 20, cy + 14]:
                tank = pg.Rect(cx - 12, ty, w - cx - 4, 8)
                pg.draw.rect(surf, (max(0, dark[0]-10), dark[1], dark[2]), tank)
                pg.draw.rect(surf, mid, tank, 1)
            # Industrial drill prow
            drill = [(w - 2, cy), (w - 12, cy - 6), (cx + 4, cy - 14),
                     (cx + 4, cy + 14), (w - 12, cy + 6)]
            pg.draw.polygon(surf, (100, 80, 60), drill)
            pg.draw.polygon(surf, (160, 140, 80), drill, 2)
            # Drill bit tip (yellow-orange)
            pg.draw.polygon(surf, (255, 200, 60),
                [(w - 2, cy), (w - 8, cy - 3), (w - 8, cy + 3)])
            # Operator cab
            cab = pg.Rect(w - 22, cy - 10, 14, 20)
            pg.draw.rect(surf, mid, cab)
            pg.draw.rect(surf, light, cab, 1)
            for wy in [cy - 4, cy + 2]:
                pg.draw.circle(surf, (100, 180, 255), (w - 15, wy), 2)
            # Exhaust stacks (heavy industry)
            for sx_ in [cx - 8, cx]:
                pg.draw.rect(surf, dark, pg.Rect(sx_, cy - 22, 4, 8))
                _glow(surf, (255, 160, 40), (sx_ + 2, cy - 22), 3)
            # Twin slow engines
            for ey in [cy - 10, cy + 8]:
                er = pg.Rect(4, ey, 8, 6)
                pg.draw.rect(surf, dark, er)
                _glow(surf, (60, 120, 255), (7, ey + 3), 4)

        elif sc == "assault_transport":
            # ── Ironclad Transport — wide troop carrier ───────────────────────
            # Chunky rectangular hull
            hull = pg.Rect(6, cy - 16, w - 12, 32)
            pg.draw.rect(surf, dark, hull)
            pg.draw.rect(surf, mid, hull, 2)
            # Boarding bay doors (side hatches)
            for bx_ in [cx - 14, cx - 2, cx + 10]:
                hatch = pg.Rect(bx_, cy - 12, 8, 24)
                pg.draw.rect(surf, (30, 30, 40), hatch)
                pg.draw.rect(surf, (80, 80, 100), hatch, 1)
            # Armoured prow (blunt wedge)
            prow = [(w - 4, cy), (w - 14, cy - 10), (cx + 2, cy - 14),
                    (cx + 2, cy + 14), (w - 14, cy + 10)]
            pg.draw.polygon(surf, mid, prow)
            pg.draw.polygon(surf, light, prow, 1)
            # Defensive gun mounts (top + bottom)
            for ty in [cy - 20, cy + 14]:
                gm = pg.Rect(cx + 4, ty, 14, 5)
                pg.draw.rect(surf, mid, gm)
                pg.draw.rect(surf, trim, gm, 1)
                pg.draw.line(surf, trim, (cx + 18, ty + 2), (w - 8, ty + 2), 1)
            # Command section
            cs = pg.Rect(w - 20, cy - 8, 14, 16)
            pg.draw.rect(surf, mid, cs)
            pg.draw.rect(surf, trim, cs, 1)
            for wy in [cy - 3, cy + 3]:
                pg.draw.circle(surf, (120, 200, 255), (w - 13, wy), 2)
            # Quad engines
            for ey in [cy - 11, cy - 4, cy + 3, cy + 10]:
                er = pg.Rect(3, ey, 8, 5)
                pg.draw.rect(surf, dark, er)
                _glow(surf, (60, 120, 255), (7, ey + 2), 3)

        elif sc == "battlecruiser":
            # ── Warbringer Battlecruiser — enormous capital warship ───────────
            # Massive slab hull
            hull = pg.Rect(4, cy - 20, w - 8, 40)
            pg.draw.rect(surf, dark, hull)
            pg.draw.rect(surf, mid, hull, 2)
            # Deck plating layers
            for ay in [cy - 16, cy - 10, cy - 2, cy + 2, cy + 10, cy + 16]:
                pg.draw.line(surf, mid, (8, ay), (w - 8, ay), 1)
            # Armoured bow — double angled ram
            bow_outer = [(w - 2, cy), (w - 18, cy - 16), (cx + 2, cy - 20),
                         (cx + 2, cy + 20), (w - 18, cy + 16)]
            pg.draw.polygon(surf, mid, bow_outer)
            pg.draw.polygon(surf, trim, bow_outer, 2)
            # Capital gun sponsons (4 turrets)
            for ty in [cy - 16, cy - 6, cy + 4, cy + 14]:
                turret = pg.Rect(cx - 10, ty, 18, 6)
                pg.draw.rect(surf, mid, turret)
                pg.draw.rect(surf, (255, 160, 40), turret, 1)
                pg.draw.line(surf, (255, 160, 40), (cx + 8, ty + 3), (w - 6, ty + 3), 2)
            # Command tower + sensors
            tower = pg.Rect(cx - 4, cy - 28, 20, 16)
            pg.draw.rect(surf, mid, tower)
            pg.draw.rect(surf, light, tower, 1)
            for bx_ in [cx - 1, cx + 5, cx + 11]:
                pg.draw.circle(surf, (120, 200, 255), (bx_, cy - 20), 2)
            pg.draw.line(surf, light, (cx + 8, cy - 28), (cx + 8, cy - 34), 1)
            pg.draw.circle(surf, light, (cx + 8, cy - 34), 2, 1)
            # 6-nozzle engine bank
            for ey in [cy - 16, cy - 9, cy - 2, cy + 2, cy + 9, cy + 16]:
                er = pg.Rect(2, ey, 10, 5)
                pg.draw.rect(surf, dark, er)
                _glow(surf, (80, 140, 255), (7, ey + 2), 4)
            # Hull vertical stripes (capital detail)
            for px_ in [cx - 8, cx, cx + 8]:
                pg.draw.line(surf, dark, (px_, cy - 20), (px_, cy + 20), 1)

        else:
            # Fallback: simple sleek arrow
            pts = [(w - 4, cy), (cx - 6, 4), (4, cy - 2), (4, cy + 2), (cx - 6, h - 4)]
            pg.draw.polygon(surf, color, pts)
            pg.draw.polygon(surf, light, pts, 1)
            _glow(surf, (80, 140, 255), (5, cy), 3)

    # ── Hull / Shield ─────────────────────────────────────────────────────────
    def take_damage(self, amount: float, ignore_shield: bool = False) -> float:
        """Apply damage; returns actual hull damage dealt."""
        was_shielded = self.shield > 0
        if not ignore_shield and self.shield > 0:
            absorbed = min(self.shield, amount)
            self.shield -= absorbed
            amount -= absorbed
            # Shield just broke — lock recharge.
            # enemy_shield_mode ships get a much longer lock (25 s vs 10 s)
            if was_shielded and self.shield <= 0:
                self.shield_recharge_lock = (
                    25.0 if getattr(self, "_enemy_shield_mode", False) else 10.0
                )
        self.hull = max(0.0, self.hull - amount)
        return amount

    def repair(self, amount: float) -> None:
        self.hull = min(float(self.max_hull), self.hull + amount)

    def recharge_shield(self, amount: float) -> None:
        self.shield = min(float(self.max_shield), self.shield + amount)

    @property
    def is_destroyed(self) -> bool:
        return self.hull <= 0

    def update(self, dt: float) -> None:
        # HP regen (adaptive hull)
        if self._hp_regen and not self.is_destroyed:
            self.repair(self._hp_regen * dt)
        # Shield break recharge lock countdown
        if self.shield_recharge_lock > 0:
            self.shield_recharge_lock = max(0.0, self.shield_recharge_lock - dt)
        # Shield passive regen — only when lock has expired
        # Enemy ships in shield-mode regen slower (2 HP/s vs 5 HP/s)
        if self.shield < self.max_shield and self.shield_recharge_lock <= 0:
            regen_rate = 2.0 if getattr(self, "_enemy_shield_mode", False) else 5.0
            self.recharge_shield(regen_rate * dt)
        # Status effect ticks
        for eff in list(self.status_effects):
            self.status_effects[eff] -= dt
            if self.status_effects[eff] <= 0:
                del self.status_effects[eff]
        # Weapon cooldowns
        for w in self.weapons:
            w.update(dt)
        # Position
        self.x  += self.vx * dt
        self.y  += self.vy * dt
        self.rect.center = (int(self.x), int(self.y))

    # ── Crew management ──────────────────────────────────────────────────────
    def add_crew(self, member: Crew) -> bool:
        if len(self.crew) >= self.crew_slots:
            return False
        self.crew.append(member)
        member.assigned_ship = self.id
        return True

    def remove_crew(self, member: Crew) -> None:
        if member in self.crew:
            self.crew.remove(member)
            if member.assigned_station:
                self.station_assignments[member.assigned_station] = None
                member.assigned_station = None
            member.assigned_ship = None

    def assign_station(self, member: Crew, station: str) -> bool:
        if station not in STATIONS or member not in self.crew:
            return False
        # Unassign from previous station
        if member.assigned_station:
            self.station_assignments[member.assigned_station] = None
        # Unassign whoever was there
        old = self.station_assignments.get(station)
        if old:
            old.assigned_station = None
        self.station_assignments[station] = member
        member.assigned_station = station
        return True

    def equip_best(self) -> None:
        """Auto-assign crew to stations by best matching stat."""
        # Clear all assignments first
        for s in STATIONS:
            self.station_assignments[s] = None
        for c in self.crew:
            c.assigned_station = None

        available = list(self.crew)
        for station in STATIONS:
            primary = STATION_PRIMARY_STAT.get(station, "combat")
            best = max(
                (c for c in available if not c.injured),
                key=lambda c: c.effective_stat(primary, self.id),
                default=None,
            )
            if best:
                self.assign_station(best, station)
                available.remove(best)

    # ── Station performance ──────────────────────────────────────────────────
    def station_stat(self, station: str) -> float:
        member = self.station_assignments.get(station)
        if not member:
            return 0.0
        primary = STATION_PRIMARY_STAT.get(station, "combat")
        return member.effective_stat(primary, self.id)

    # ── Weapons ──────────────────────────────────────────────────────────────
    def add_weapon(self, weapon: Weapon) -> bool:
        total = sum(self.hardpoint_slots.values())
        if len(self.weapons) >= total:
            return False
        self.weapons.append(weapon)
        return True

    # ── Modules ──────────────────────────────────────────────────────────────
    def add_module(self, module: ShipModule) -> bool:
        if len(self.modules) >= self.free_module_slots:
            return False
        self.modules.append(module)
        self._apply_module(module)
        return True

    def _apply_module(self, module: ShipModule) -> None:
        e = module.effect
        if "hull_bonus"   in e: self.max_hull   += e["hull_bonus"];   self.hull   += e["hull_bonus"]
        if "shield_bonus" in e: self.max_shield  += e["shield_bonus"]; self.shield += e["shield_bonus"]
        if "speed_bonus"  in e: self.speed       += e["speed_bonus"]

    # ── Effective speed (pilot stat bonus) ───────────────────────────────────
    @property
    def effective_speed(self) -> float:
        pilot_stat = self.station_stat("cockpit")
        bonus = pilot_stat * 0.3  # 0.3 speed per piloting point
        return self.speed + bonus

    # ── Status effects ───────────────────────────────────────────────────────
    def apply_status(self, effect: str, duration: float) -> None:
        self.status_effects[effect] = max(
            self.status_effects.get(effect, 0), duration
        )

    def has_status(self, effect: str) -> bool:
        return effect in self.status_effects

    # ── Serialization ────────────────────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "id":           self.id,
            "rarity":       self.rarity,
            "custom_name":  self.custom_name,
            "color_scheme": list(self.color_scheme),
            "insignia":     self.insignia,
            "hull":         self.hull,
            "shield":       self.shield,
            "fuel":         self.fuel,
            "supplies":     self.supplies,
            "hull_type":    self.hull_type,
            "chosen_path":  self.chosen_path,
            "fleet_order":  self.fleet_order,
            "crew":         [c.to_dict()        for c in self.crew],
            "weapons":      [w.to_dict()        for w in self.weapons],
            "drones":       [d.to_dict()        for d in self.drones],
            "modules":      [m.to_dict()        for m in self.modules],
            "station_assignments": {
                s: (c.id if c else None)
                for s, c in self.station_assignments.items()
            },
        }

    def __repr__(self) -> str:
        return (f"<Ship '{self.custom_name}' ({self.ship_class}/{self.rarity}) "
                f"hull={self.hull:.0f}/{self.max_hull}>")
