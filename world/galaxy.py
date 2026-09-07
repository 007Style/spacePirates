"""world/galaxy.py — Galaxy sector map, travel logic."""
from __future__ import annotations
import pygame
import math
import random
from world.sector import Sector, SectorType
from settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, DARK_BG, PANEL_BG, ACCENT,
    TEXT_MAIN, TEXT_MUTED, BORDER, WARNING, DANGER, SUCCESS, WHITE,
    FUEL_COST_PER_SECTOR,
)


def _build_galaxy() -> dict[str, Sector]:
    """Build the static galaxy sector graph with expanded coordinate space."""
    sectors: dict[str, Sector] = {}

    def add(sid, name, x, y, diff=1, stype=SectorType.NORMAL,
            nation="", faction="", boss="", enemy_pool=None, connections=None):
        sectors[sid] = Sector(
            sid, name, x, y, diff, stype, nation, faction,
            boss, enemy_pool or [], connections or [],
        )

    # ── Home & Starting Area ─────────────────────────────────────────────────
    add("home_base",       "Your Base",            560, 500, 0,
        SectorType.HOME_BASE, connections=["derelict_field"])
    add("derelict_field",  "Derelict Field",       780, 390, 1,
        faction="scavengers", enemy_pool=["fighter_mk1"],
        connections=["home_base", "compact_border", "outer_rim", "trade_lanes",
                     "asteroid_belt_alpha"])

    # ── Terran Compact ───────────────────────────────────────────────────────
    add("compact_border",  "Compact Border",       980, 250, 2,
        faction="military", enemy_pool=["fighter_mk1", "fighter_mk2"],
        connections=["derelict_field", "compact_core"])
    add("compact_core",    "Compact Core",         1190, 165, 0,
        SectorType.NATION_SAFE, nation="terran_compact",
        connections=["compact_border", "compact_boss"])
    add("compact_boss",    "Admiral's Station",    1390, 140, 4,
        SectorType.BOSS, nation="terran_compact", boss="admiral_voss",
        connections=["compact_core", "deep_space"])

    # ── Merchant Syndicate ───────────────────────────────────────────────────
    add("trade_lanes",     "Trade Lanes",          870, 590, 2,
        faction="merchant_guild", enemy_pool=["freighter_mk1"],
        connections=["derelict_field", "syndicate_hub", "neutral_post_delta"])
    add("syndicate_hub",   "Syndicate Hub",        1050, 680, 0,
        SectorType.NATION_SAFE, nation="merchant_syndicate",
        connections=["trade_lanes", "black_market"])
    add("black_market",    "The Blind Eye",        1200, 810, 3,
        faction="space_pirates", enemy_pool=["fighter_mk2", "fighter_elite"],
        connections=["syndicate_hub", "void_nexus", "pirate_stronghold_gamma"])

    # ── Free Colonies ────────────────────────────────────────────────────────
    add("outer_rim",       "Outer Rim",            590, 690, 2,
        faction="scavengers", enemy_pool=["fighter_mk1", "freighter_mk1"],
        connections=["derelict_field", "colony_alpha"])
    add("colony_alpha",    "Colony Alpha",         420, 810, 0,
        SectorType.NATION_SAFE, nation="free_colonies",
        connections=["outer_rim", "ship_graveyard"])
    add("ship_graveyard",  "Ship Graveyard",       250, 910, 3,
        SectorType.GRAVEYARD,
        connections=["colony_alpha", "nebula_reach", "asteroid_belt_beta"])

    # ── Technocracy ──────────────────────────────────────────────────────────
    add("nebula_reach",    "Nebula Reach",         280, 670, 3,
        SectorType.NEBULA, faction="scavengers",
        enemy_pool=["fighter_mk2", "carrier_mk1"],
        connections=["ship_graveyard", "research_ring"])
    add("research_ring",   "Research Ring",        195, 500, 0,
        SectorType.NATION_SAFE, nation="technocracy",
        connections=["nebula_reach", "tech_citadel"])
    add("tech_citadel",    "Tech Citadel",         112, 360, 0,
        SectorType.NATION_SAFE, nation="technocracy",
        connections=["research_ring", "axiom_sector"])
    add("axiom_sector",    "AXIOM Sector",         112, 195, 5,
        SectorType.BOSS, boss="axiom_9",
        connections=["tech_citadel", "deep_space"])

    # ── Deep Space / Void ────────────────────────────────────────────────────
    add("deep_space",      "Deep Space",           700, 140, 5,
        faction="space_pirates", enemy_pool=["fighter_elite", "carrier_mk1"],
        connections=["compact_boss", "axiom_sector", "void_approaches"])
    add("void_approaches", "Void Approaches",      700, 56, 6,
        SectorType.NEBULA, enemy_pool=["carrier_mk1"],
        connections=["deep_space", "void_nexus"])
    add("void_nexus",      "Void Nexus",           840, 56, 0,
        SectorType.NATION_SAFE, nation="void_collective",
        connections=["void_approaches", "black_market", "final_sector"])
    add("final_sector",    "End of the Line",      980, 56, 8,
        SectorType.BOSS, boss="captain_dread_final",
        connections=["void_nexus"])

    # ── NEW SECTORS ──────────────────────────────────────────────────────────
    # Asteroid belt mining areas
    add("asteroid_belt_alpha", "Asteroid Belt Alpha", 900, 480, 2,
        SectorType.NORMAL, faction="scavengers",
        enemy_pool=["fighter_mk1", "fighter_mk2"],
        connections=["derelict_field", "asteroid_belt_beta", "mining_depot"])
    add("asteroid_belt_beta",  "Asteroid Belt Beta",  200, 780, 3,
        SectorType.NORMAL, faction="scavengers",
        enemy_pool=["fighter_mk2", "carrier_mk1"],
        connections=["ship_graveyard", "asteroid_belt_alpha"])
    add("mining_depot",        "Mining Depot",         1100, 450, 2,
        SectorType.NATION_SAFE, nation="merchant_syndicate",
        connections=["asteroid_belt_alpha", "neutral_post_delta"])

    # Black hole sector
    add("black_hole_sector",   "Event Horizon",       1100, 300, 6,
        SectorType.NEBULA, enemy_pool=["fighter_elite", "carrier_mk1"],
        connections=["deep_space", "pirate_stronghold_alpha", "void_rift"])

    # Pirate strongholds
    add("pirate_stronghold_alpha", "Skull Rock",       1300, 400, 5,
        SectorType.NORMAL, faction="space_pirates",
        enemy_pool=["fighter_elite", "carrier_mk1"],
        connections=["black_hole_sector", "pirate_stronghold_gamma", "compact_boss"])
    add("pirate_stronghold_gamma", "Iron Teeth Dock",  1350, 680, 4,
        SectorType.NORMAL, faction="space_pirates",
        enemy_pool=["fighter_mk2", "fighter_elite"],
        connections=["black_market", "pirate_stronghold_alpha"])

    # Neutral trading posts
    add("neutral_post_delta",  "Waypoint Delta",       1000, 560, 1,
        SectorType.NATION_SAFE, nation="merchant_syndicate",
        connections=["trade_lanes", "mining_depot", "neutral_post_epsilon"])
    add("neutral_post_epsilon","Waypoint Epsilon",     1200, 620, 2,
        SectorType.NORMAL, faction="merchant_guild",
        enemy_pool=["freighter_mk1"],
        connections=["neutral_post_delta", "pirate_stronghold_gamma"])

    # Void rift
    add("void_rift",           "Void Rift",            900, 140, 7,
        SectorType.NEBULA, enemy_pool=["fighter_elite", "carrier_mk1"],
        connections=["black_hole_sector", "void_approaches", "axiom_sector"])

    return sectors


class Galaxy:
    def __init__(self):
        self.sectors: dict[str, Sector] = _build_galaxy()
        self.current_sector_id: str     = "home_base"
        self._selected_id: str | None   = None
        self._back_btn:    "pygame.Rect | None" = None
        self._travel_btn:  "pygame.Rect | None" = None
        self._battle_btn:  "pygame.Rect | None" = None
        self._explore_btn: "pygame.Rect | None" = None

        # Seasonal sector timer (ticks)
        self._seasonal_timer = 0
        self._seasonal_active_sector = "ship_graveyard"  # rotates

        # Font
        pygame.font.init()
        self._font_sm  = pygame.font.SysFont("monospace", 11)
        self._font_med = pygame.font.SysFont("monospace", 14)

        # Scroll / pan state for the large map
        self._scroll_x: float = 0.0
        self._scroll_y: float = 0.0
        self._zoom: float     = 0.75   # default zoom-out to fit the wider map
        self._panning: bool   = False
        self._pan_start: tuple[int, int] = (0, 0)
        self._pan_scroll_start: tuple[float, float] = (0.0, 0.0)

        # ── Cargo ships on trade routes ───────────────────────────────────────
        # Each entry: {route: (sid_a, sid_b), t: 0..1, speed, direction: 1/-1}
        import random as _rng
        _TRADE_ROUTES = [
            ("home_base",       "derelict_field"),
            ("derelict_field",  "trade_lanes"),
            ("trade_lanes",     "syndicate_hub"),
            ("syndicate_hub",   "neutral_post_delta"),
            ("neutral_post_delta", "mining_depot"),
            ("compact_border",  "compact_core"),
            ("outer_rim",       "colony_alpha"),
        ]
        self._cargo_ships: list[dict] = []
        for route in _TRADE_ROUTES:
            for _ in range(_rng.randint(1, 2)):
                self._cargo_ships.append({
                    "route":  route,
                    "t":      _rng.random(),
                    "speed":  _rng.uniform(0.04, 0.10),
                    "dir":    _rng.choice([1, -1]),
                    "color":  (180, 220, 140),
                })
        self._cargo_anim_time = 0.0

        # ── NPC Pirates scattered on the map ─────────────────────────────────
        # Each can be recruited by visiting their sector and clicking RECRUIT
        _NPC_PIRATE_NAMES = [
            "Red Vance", "Sable Cross", "The Iron Wren", "Kira Voss",
            "Drax Nomad", "Zenna the Quick", "Brutus Kane", "Phantom Yael",
        ]
        _NPC_SECTORS = [
            "derelict_field", "outer_rim", "black_market", "nebula_reach",
            "ship_graveyard", "trade_lanes", "asteroid_belt_alpha",
            "pirate_stronghold_gamma", "neutral_post_epsilon",
        ]
        npc_rng = random.Random(77)
        self._npc_pirates: list[dict] = []
        used_sectors = set()
        for name in _NPC_PIRATE_NAMES[:5]:   # 5 NPC pirates on the map
            candidates = [s for s in _NPC_SECTORS if s not in used_sectors
                          and s in self.sectors]
            if not candidates:
                break
            sector_id2 = npc_rng.choice(candidates)
            used_sectors.add(sector_id2)
            self._npc_pirates.append({
                "name":      name,
                "sector_id": sector_id2,
                "recruited": False,
                "ship_class": npc_rng.choice(["fighter", "freighter", "fighter"]),
                "bonus":     npc_rng.choice([
                    "+10 combat", "+15% speed", "+20 hull",
                    "+8 gunnery", "+5 repair/sec",
                ]),
            })

    # ── Properties ───────────────────────────────────────────────────────────
    @property
    def current_sector(self) -> Sector:
        return self.sectors[self.current_sector_id]

    @property
    def selected_sector(self) -> Sector | None:
        return self.sectors.get(self._selected_id) if self._selected_id else None

    # ── Travel ───────────────────────────────────────────────────────────────
    def can_travel_to(self, sector_id: str, fuel: float) -> tuple[bool, str]:
        """Returns (ok, reason)."""
        if sector_id not in self.sectors:
            return False, "Unknown sector"
        if sector_id not in self.current_sector.connections:
            return False, "Not connected"
        cost = self.travel_cost(sector_id)
        if fuel < cost:
            return False, f"Need {cost} fuel (have {fuel:.0f})"
        target = self.sectors[sector_id]
        if target.is_boss_sector and not self._boss_unlocked(sector_id):
            return False, "Defeat previous boss first"
        return True, "OK"

    def travel_to(self, sector_id: str, ship) -> dict:
        ok, reason = self.can_travel_to(sector_id, ship.fuel)
        if not ok:
            return {"success": False, "reason": reason}
        cost = self.travel_cost(sector_id)
        ship.fuel -= cost
        self.current_sector_id = sector_id
        self.sectors[sector_id].visited = True
        from core.events import bus
        bus.publish("sector_entered", sector=self.sectors[sector_id])
        return {"success": True, "fuel_used": cost}

    def travel_cost(self, sector_id: str) -> int:
        return FUEL_COST_PER_SECTOR

    def _boss_unlocked(self, boss_sector_id: str) -> bool:
        # Check if all boss sectors below difficulty are defeated
        target = self.sectors.get(boss_sector_id)
        if not target:
            return False
        # Simple rule: previous difficulty-tier bosses must be done
        required_diff = target.difficulty - 3
        if required_diff <= 0:
            return True
        for s in self.sectors.values():
            if s.is_boss_sector and s.difficulty <= required_diff and not s.boss_defeated:
                return False
        return True

    # ── Seasonal events ───────────────────────────────────────────────────────
    def tick_seasonal(self, dt: float) -> None:
        self._seasonal_timer += dt
        # Rotate seasonal sector every 5 minutes
        if self._seasonal_timer > 300:
            self._seasonal_timer = 0
            self._rotate_seasonal()

    def _rotate_seasonal() -> None:
        pass   # Future: cycle through seasonal sector list

    # ── Coordinate helpers for zoom/pan ──────────────────────────────────────
    def _world_to_screen(self, wx: float, wy: float) -> tuple[int, int]:
        z = self._zoom
        sx = int((wx + self._scroll_x) * z)
        sy = int((wy + self._scroll_y) * z)
        return (sx, sy)

    def _screen_to_world(self, sx: int, sy: int) -> tuple[float, float]:
        z = self._zoom
        return (sx / z - self._scroll_x, sy / z - self._scroll_y)

    # ── Input (galaxy map screen) ─────────────────────────────────────────────
    def handle_event(self, event: pygame.event.Event) -> str | None:
        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            if event.button == 1:
                # Travel / Back / Battle / Explore buttons (screen-space, not zoomed)
                if hasattr(self, "_travel_btn") and self._travel_btn and self._travel_btn.collidepoint(mx, my):
                    return f"travel:{self._selected_id}"
                if hasattr(self, "_battle_btn") and self._battle_btn and self._battle_btn.collidepoint(mx, my):
                    return f"battle:{self._selected_id}"  # enter combat at this sector
                if hasattr(self, "_explore_btn") and self._explore_btn and self._explore_btn.collidepoint(mx, my):
                    return f"explore:{self._selected_id}"  # explore mining depot
                if hasattr(self, "_recruit_btn") and self._recruit_btn and self._recruit_btn.collidepoint(mx, my):
                    npc = getattr(self, "_recruit_npc", None)
                    if npc:
                        npc["recruited"] = True
                        return f"recruit:{npc['name']}:{npc['ship_class']}:{npc['bonus']}"
                if hasattr(self, "_back_btn") and self._back_btn and self._back_btn.collidepoint(mx, my):
                    return "back"
                # Sector node click — convert screen pos to world pos first
                wx, wy = self._screen_to_world(mx, my)
                for sid, sector in self.sectors.items():
                    sx2, sy2 = self._world_to_screen(sector.x, sector.y)
                    if math.hypot(sx2 - mx, sy2 - my) < 14:
                        self._selected_id = sid
                        return "select"
                # Start pan drag
                self._panning = True
                self._pan_start = (mx, my)
                self._pan_scroll_start = (self._scroll_x, self._scroll_y)
            elif event.button == 3:
                # Right-click → start pan too
                self._panning = True
                self._pan_start = (mx, my)
                self._pan_scroll_start = (self._scroll_x, self._scroll_y)
            elif event.button == 4:
                # Scroll wheel up → zoom in
                self._zoom = min(2.0, self._zoom + 0.1)
            elif event.button == 5:
                # Scroll wheel down → zoom out
                self._zoom = max(0.3, self._zoom - 0.1)
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button in (1, 3):
                self._panning = False
        elif event.type == pygame.MOUSEMOTION:
            if self._panning:
                mx, my = event.pos
                dx = (mx - self._pan_start[0]) / self._zoom
                dy = (my - self._pan_start[1]) / self._zoom
                self._scroll_x = self._pan_scroll_start[0] + dx
                self._scroll_y = self._pan_scroll_start[1] + dy
        return None

    # ── Draw ──────────────────────────────────────────────────────────────────
    SECTOR_COLORS = {
        SectorType.NORMAL:      (80,  80, 120),
        SectorType.NATION_SAFE: (40, 160,  80),
        SectorType.GRAVEYARD:   (120, 60,  40),
        SectorType.NEBULA:      (120, 40, 160),
        SectorType.BOSS:        (200, 40,  40),
        SectorType.SEASONAL:    (200, 160,  0),
        SectorType.HOME_BASE:   (60, 140, 220),
    }

    def update(self, dt: float, home_base=None) -> None:
        """Animate cargo ships along trade routes.
        When a ship reaches t=1 or t=0, check if it touches home_base
        and award +1000cr to the player."""
        self._cargo_anim_time += dt
        for cs in self._cargo_ships:
            old_t = cs["t"]
            cs["t"] += cs["speed"] * cs["dir"] * dt
            if cs["t"] > 1.0:
                cs["t"] = 1.0; cs["dir"] = -1
                # If home_base is one of the endpoints, award credits
                if home_base and "home_base" in cs["route"]:
                    home_base.add_resource("credits", 1000)
                    try:
                        from core.events import bus as _bus
                        _bus.publish("notification",
                                     msg="📦 Trade cargo arrived at base! +1000cr",
                                     color=(200, 230, 140))
                    except Exception:
                        pass
            elif cs["t"] < 0.0:
                cs["t"] = 0.0; cs["dir"] = 1
                if home_base and "home_base" in cs["route"]:
                    home_base.add_resource("credits", 1000)
                    try:
                        from core.events import bus as _bus
                        _bus.publish("notification",
                                     msg="📦 Trade cargo arrived at base! +1000cr",
                                     color=(200, 230, 140))
                    except Exception:
                        pass

    def draw(self, surface: pygame.Surface) -> None:
        import time as _t
        import math as _m
        sw, sh = surface.get_size()
        t_now = _t.time()

        # ── 1. Deep-space starfield background ───────────────────────────────
        surface.fill((4, 4, 12))
        # Draw parallax star layers based on scroll
        _rng2 = random.Random(7777)
        for layer, count, speed, min_r, max_r, col_base in [
            (0, 180, 0.10, 1, 1, (60,  60,  80)),
            (1, 100, 0.25, 1, 2, (120, 120, 150)),
            (2,  40, 0.50, 1, 2, (200, 200, 220)),
        ]:
            for _ in range(count):
                wx = _rng2.uniform(0, 1920)
                wy = _rng2.uniform(0, 1080)
                # Parallax: stars at different speeds relative to scroll
                px = int((wx + self._scroll_x * speed * self._zoom) % sw)
                py = int((wy + self._scroll_y * speed * self._zoom) % sh)
                twinkle = int(20 * _m.sin(t_now * _rng2.uniform(0.5, 2.5) + wx))
                sc = tuple(min(255, c + twinkle) for c in col_base)
                r_star = _rng2.randint(min_r, max_r)
                pygame.draw.circle(surface, sc, (px, py), r_star)

        # ── 2. Nebula clouds in background ───────────────────────────────────
        _nebula_rng = random.Random(9999)
        _nebula_defs = [
            (420, 300, (60, 0, 80),   55),
            (900, 180, (0, 40, 100),  45),
            (700, 600, (80, 30, 0),   40),
            (300, 650, (0, 60, 80),   50),
            (1100,450, (50, 0, 90),   38),
        ]
        for nx_, ny_, ncol, nalpha in _nebula_defs:
            sx_, sy_ = self._world_to_screen(nx_, ny_)
            nr = int(110 * self._zoom)
            if -nr < sx_ < sw + nr and -nr < sy_ < sh + nr:
                nsurf = pygame.Surface((nr * 2, nr * 2), pygame.SRCALPHA)
                pygame.draw.circle(nsurf, (*ncol, nalpha), (nr, nr), nr)
                pygame.draw.circle(nsurf, (*tuple(min(255,c+20) for c in ncol), nalpha // 2),
                                   (nr, nr), nr * 2 // 3)
                surface.blit(nsurf, (sx_ - nr, sy_ - nr))

        # Build set of active cargo routes for line highlight
        _active_routes: set[frozenset] = set()
        for cs in self._cargo_ships:
            _active_routes.add(frozenset(cs["route"]))

        # ── 3. Connection lines with animated trade route dashes ──────────────
        for sid, sector in self.sectors.items():
            for cid in sector.connections:
                if cid <= sid:  # draw each pair only once
                    continue
                if cid in self.sectors:
                    cs2 = self.sectors[cid]
                    p1 = self._world_to_screen(sector.x, sector.y)
                    p2 = self._world_to_screen(cs2.x, cs2.y)
                    is_cargo = frozenset((sid, cid)) in _active_routes
                    if is_cargo:
                        # Base gold lane
                        pygame.draw.line(surface, (55, 48, 18), p1, p2, 3)
                        pygame.draw.line(surface, (140, 120, 40), p1, p2, 1)
                        # Animated dashes moving along the route
                        dx = p2[0] - p1[0]; dy = p2[1] - p1[1]
                        length = max(1, _m.hypot(dx, dy))
                        steps = int(length // 14)
                        phase = (t_now * 0.6) % 1.0
                        for step in range(steps):
                            tt = ((step / max(steps, 1)) + phase) % 1.0
                            px_ = int(p1[0] + dx * tt)
                            py_ = int(p1[1] + dy * tt)
                            pygame.draw.circle(surface, (200, 175, 70), (px_, py_), 1)
                    else:
                        # Faint lane
                        pygame.draw.line(surface, (28, 30, 50), p1, p2, 2)
                        pygame.draw.line(surface, (45, 48, 70), p1, p2, 1)

        # ── 4. Cargo ship icons ───────────────────────────────────────────────
        for cs in self._cargo_ships:
            sid_a, sid_b = cs["route"]
            if sid_a not in self.sectors or sid_b not in self.sectors:
                continue
            sa = self.sectors[sid_a]; sb = self.sectors[sid_b]
            t  = cs["t"]
            wx = sa.x + (sb.x - sa.x) * t
            wy = sa.y + (sb.y - sa.y) * t
            sx, sy = self._world_to_screen(wx, wy)
            # Direction angle for the ship icon
            dx = sb.x - sa.x; dy = sb.y - sa.y
            if cs["dir"] < 0:
                dx, dy = -dx, -dy
            angle = _m.degrees(_m.atan2(dy, dx))
            # Engine glow
            glow_s = pygame.Surface((20, 20), pygame.SRCALPHA)
            pygame.draw.circle(glow_s, (100, 200, 80, 60), (10, 10), 9)
            surface.blit(glow_s, (sx - 10, sy - 10))
            # Ship body: rotated diamond/arrow
            cos_a = _m.cos(_m.radians(angle))
            sin_a = _m.sin(_m.radians(angle))
            def _rot(ox, oy):
                return (int(sx + ox * cos_a - oy * sin_a),
                        int(sy + ox * sin_a + oy * cos_a))
            hull_pts = [_rot(7, 0), _rot(-4, -3), _rot(-2, 0), _rot(-4, 3)]
            pygame.draw.polygon(surface, (50, 80, 45), hull_pts)
            pygame.draw.polygon(surface, (140, 220, 110), hull_pts, 1)
            # Cargo container stripes
            cargo_pts = [_rot(-1, -2), _rot(4, -2), _rot(4, 2), _rot(-1, 2)]
            pygame.draw.polygon(surface, (200, 180, 60), cargo_pts, 1)
            # Engine trail dot
            pygame.draw.circle(surface, (80, 200, 120), _rot(-5, 0), 2)
            # Home-base route: extra yellow glow when near home
            if "home_base" in cs["route"]:
                hb_sec = self.sectors.get("home_base")
                if hb_sec:
                    hbsx, hbsy = self._world_to_screen(hb_sec.x, hb_sec.y)
                    dist_px = _m.hypot(sx - hbsx, sy - hbsy)
                    if dist_px < 40:
                        prox = pygame.Surface((24, 24), pygame.SRCALPHA)
                        alpha = int(180 * (1 - dist_px / 40))
                        pygame.draw.circle(prox, (255, 220, 60, alpha), (12, 12), 11)
                        surface.blit(prox, (sx - 12, sy - 12))

        # ── 5. NPC pirate icons ───────────────────────────────────────────────
        for npc in self._npc_pirates:
            if npc["recruited"]:
                continue
            sec = self.sectors.get(npc["sector_id"])
            if not sec:
                continue
            nx, ny = self._world_to_screen(sec.x + 18, sec.y - 18)
            # Skull icon — concentric circles with X
            pygame.draw.circle(surface, (80, 40, 10), (nx, ny), 7)
            pygame.draw.circle(surface, (220, 130, 40), (nx, ny), 7, 1)
            # X mark on skull
            pygame.draw.line(surface, (220, 130, 40), (nx-3,ny-3), (nx+3,ny+3), 1)
            pygame.draw.line(surface, (220, 130, 40), (nx+3,ny-3), (nx-3,ny+3), 1)
            if self._zoom >= 0.55:
                try:
                    npc_lbl = self._font_sm.render(
                        f"☠ {npc['name'].split()[0]}", True, (220, 160, 60))
                    surface.blit(npc_lbl, (nx - npc_lbl.get_width() // 2, ny - 16))
                except Exception:
                    pass

        # ── 6. Sector nodes ───────────────────────────────────────────────────
        pulse_t = _m.sin(t_now * 2.5) * 0.5 + 0.5   # 0..1
        for sid, sector in self.sectors.items():
            base_col = self.SECTOR_COLORS.get(sector.sector_type, (80, 80, 120))
            sx, sy = self._world_to_screen(sector.x, sector.y)
            r = max(6, int(12 * self._zoom))
            visited = sector.visited

            # ── Glow halo ────────────────────────────────────────────────────
            if visited:
                glow_r = r + 8
                g_surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
                g_alpha = int(30 + 20 * pulse_t) if sid == self.current_sector_id else 18
                pygame.draw.circle(g_surf, (*base_col, g_alpha), (glow_r, glow_r), glow_r)
                surface.blit(g_surf, (sx - glow_r, sy - glow_r))

            # ── Current sector pulse ring ────────────────────────────────────
            if sid == self.current_sector_id:
                pulse_r = r + 4 + int(3 * pulse_t)
                pygame.draw.circle(surface, ACCENT, (sx, sy), pulse_r, 2)
                # Extra bright inner ring
                pygame.draw.circle(surface, tuple(min(255, c + 60) for c in base_col),
                                   (sx, sy), r + 1, 1)

            # ── Selected ring ────────────────────────────────────────────────
            if sid == self._selected_id:
                pygame.draw.circle(surface, WARNING, (sx, sy), r + 7, 2)

            # ── Node fill (layered circle for 3D look) ───────────────────────
            fill_col = base_col if visited else tuple(c // 4 for c in base_col)
            dark_col = tuple(max(0, c - 40) for c in fill_col)
            lit_col  = tuple(min(255, c + 50) for c in fill_col)
            # Shadow
            pygame.draw.circle(surface, dark_col, (sx + 1, sy + 1), r)
            # Fill
            pygame.draw.circle(surface, fill_col, (sx, sy), r)
            # Top-left specular highlight
            hl_surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(hl_surf, (*lit_col, 100 if visited else 30),
                               (r // 2, r // 2), r // 2)
            surface.blit(hl_surf, (sx - r, sy - r))
            # Outline
            pygame.draw.circle(surface, dark_col, (sx, sy), r, 1)

            # ── Boss/type markers ─────────────────────────────────────────────
            if sector.is_boss_sector:
                pygame.draw.circle(surface, DANGER, (sx, sy), r, 2)
                # Skull-ish X over boss node
                pygame.draw.line(surface, DANGER, (sx-r//2,sy-r//2), (sx+r//2,sy+r//2), 1)
                pygame.draw.line(surface, DANGER, (sx+r//2,sy-r//2), (sx-r//2,sy+r//2), 1)
            if sector.sector_type == SectorType.HOME_BASE:
                # House icon dot
                pygame.draw.circle(surface, (100, 200, 255), (sx, sy), max(3, r // 2))

            # ── Name label ────────────────────────────────────────────────────
            if self._zoom >= 0.45:
                lbl_col = TEXT_MAIN if visited else tuple(c // 2 for c in TEXT_MUTED)
                lbl = self._font_sm.render(sector.name, True, lbl_col)
                # Subtle backing for readability
                lbl_r = pygame.Rect(sx - lbl.get_width() // 2 - 2, sy + r + 1,
                                    lbl.get_width() + 4, lbl.get_height())
                back_s = pygame.Surface((lbl_r.w, lbl_r.h), pygame.SRCALPHA)
                back_s.fill((0, 0, 0, 100))
                surface.blit(back_s, lbl_r.topleft)
                surface.blit(lbl, (sx - lbl.get_width() // 2, sy + r + 2))

        # ── 7. Info panel ─────────────────────────────────────────────────────
        if self._selected_id and self._selected_id in self.sectors:
            self._draw_info_panel(surface, self.sectors[self._selected_id])

        # ── 8. Return to Base button ──────────────────────────────────────────
        self._back_btn = pygame.Rect(10, 10, 200, 40)
        p_btn = abs(_m.sin(t_now * 2))
        btn_col = (int(20 + 10 * p_btn), int(45 + 15 * p_btn), int(20 + 10 * p_btn))
        border_col = (int(60 + 40 * p_btn), int(200 + 55 * p_btn), int(60 + 40 * p_btn))
        pygame.draw.rect(surface, btn_col, self._back_btn, border_radius=6)
        pygame.draw.rect(surface, border_col, self._back_btn, 2, border_radius=6)
        bt = self._font_med.render("⌂  Return to Base", True, border_col)
        surface.blit(bt, (self._back_btn.x + 10,
                          self._back_btn.centery - bt.get_height() // 2))

        # ── 9. HUD hints strip ────────────────────────────────────────────────
        hint_y = sh - 20
        hint_surf = pygame.Surface((sw, 20), pygame.SRCALPHA)
        hint_surf.fill((0, 0, 0, 120))
        surface.blit(hint_surf, (0, hint_y))
        esc_hint = self._font_sm.render(
            "ESC / ⌂ = base   scroll-wheel = zoom   drag = pan   click node = info",
            True, TEXT_MUTED)
        surface.blit(esc_hint, (10, hint_y + 2))
        zoom_lbl = self._font_sm.render(f"Zoom {self._zoom:.1f}×", True, TEXT_MUTED)
        surface.blit(zoom_lbl, (sw - zoom_lbl.get_width() - 8, hint_y + 2))

    def _draw_info_panel(self, surface: pygame.Surface, sector: Sector) -> None:
        import math, time as _t
        is_connected  = sector.sector_id in self.current_sector.connections
        is_current    = sector.sector_id == self.current_sector_id
        is_hostile    = (sector.sector_type not in
                         (SectorType.HOME_BASE, SectorType.NATION_SAFE))
        is_mining     = sector.sector_id == "mining_depot"

        # NPC pirate at this sector?
        npc_here = next((n for n in self._npc_pirates
                         if n["sector_id"] == sector.sector_id and not n["recruited"]
                         and is_current), None)

        # BATTLE is shown:
        #   • when travelling to a connected hostile sector (before arrival)
        #   • OR when already at a hostile sector (always available)
        has_battle    = is_hostile and (is_connected or is_current)
        has_explore   = is_mining  # blue explore button at mining depot
        has_recruit   = npc_here is not None
        # Extra buttons expand panel
        extra_rows = sum([has_battle, has_explore, has_recruit])
        ph = 210 + extra_rows * 30
        pw = 270
        px = SCREEN_WIDTH - pw - 10
        py = 10
        pygame.draw.rect(surface, (20, 20, 40), (px, py, pw, ph))
        pygame.draw.rect(surface, BORDER,       (px, py, pw, ph), 1)

        # Sector name (large)
        name_s = self._font_med.render(sector.name, True, TEXT_MAIN)
        surface.blit(name_s, (px + 8, py + 6))

        # Info lines
        info_lines = [
            (f"Type: {sector.sector_type}",                        TEXT_MUTED),
            (f"Difficulty: {'★' * max(sector.difficulty, 1)}",     TEXT_MUTED),
            (f"Nation: {sector.nation_id or '—'}",                 TEXT_MUTED),
            (f"Faction: {sector.faction_id or '—'}",               TEXT_MUTED),
            (f"Visited: {'Yes' if sector.visited else 'No'}",       TEXT_MUTED),
            (f"Fuel cost: {FUEL_COST_PER_SECTOR}",                 TEXT_MUTED),
        ]
        if sector.is_boss_sector:
            info_lines.append((
                f"Boss: {'Defeated ✓' if sector.boss_defeated else '⚠ ACTIVE'}",
                DANGER if not sector.boss_defeated else SUCCESS,
            ))
        if is_mining:
            info_lines.append(("⛏  Mining resources available!", (80, 200, 255)))

        y_off = py + 24
        for line, col in info_lines:
            t = self._font_sm.render(line, True, col)
            surface.blit(t, (px + 8, y_off))
            y_off += 15

        # ── BATTLE button (always visible when at or connected to hostile sector) ─
        self._battle_btn = None
        if has_battle:
            bat_rect = pygame.Rect(px + 8, y_off + 2, pw - 16, 24)
            pulse = abs(math.sin(_t.time() * 3))
            b_col = (int(180 + 70 * pulse), 30, 30)
            pygame.draw.rect(surface, (40, 0, 0), bat_rect)
            pygame.draw.rect(surface, b_col, bat_rect, 2)
            # Label: "FIGHT HERE" when already at sector, "BATTLE" when connected
            btn_lbl = "⚔  FIGHT HERE  ⚔" if is_current else "⚔  BATTLE  ⚔"
            bat_lbl = self._font_med.render(btn_lbl, True, b_col)
            surface.blit(bat_lbl, (bat_rect.centerx - bat_lbl.get_width() // 2,
                                    bat_rect.centery - bat_lbl.get_height() // 2))
            self._battle_btn = bat_rect
            y_off += 30

        # ── EXPLORE button (mining depot) ─────────────────────────────────────
        self._explore_btn = None
        if has_explore:
            exp_rect = pygame.Rect(px + 8, y_off + 2, pw - 16, 24)
            pulse2 = abs(math.sin(_t.time() * 2 + 1.0))
            e_col  = (int(60 + 40 * pulse2), int(180 + 40 * pulse2), 255)
            pygame.draw.rect(surface, (0, 20, 50), exp_rect)
            pygame.draw.rect(surface, e_col, exp_rect, 2)
            exp_lbl = self._font_med.render("⛏  EXPLORE DEPOT", True, e_col)
            surface.blit(exp_lbl, (exp_rect.centerx - exp_lbl.get_width() // 2,
                                    exp_rect.centery - exp_lbl.get_height() // 2))
            self._explore_btn = exp_rect
            y_off += 30

        # ── RECRUIT NPC pirate button ─────────────────────────────────────────
        self._recruit_btn  = None
        self._recruit_npc  = None
        if has_recruit and npc_here:
            rec_rect = pygame.Rect(px + 8, y_off + 2, pw - 16, 24)
            r_pulse3 = abs(math.sin(_t.time() * 2.5))
            r_col3   = (int(200 + 55 * r_pulse3), int(140 + 60 * r_pulse3), 40)
            pygame.draw.rect(surface, (30, 20, 0), rec_rect)
            pygame.draw.rect(surface, r_col3, rec_rect, 2)
            rec_lbl = self._font_med.render(
                f"★ RECRUIT  {npc_here['name']}", True, r_col3)
            surface.blit(rec_lbl, (rec_rect.centerx - rec_lbl.get_width() // 2,
                                    rec_rect.centery - rec_lbl.get_height() // 2))
            self._recruit_btn = rec_rect
            self._recruit_npc = npc_here
            y_off += 30

        # ── Travel / status button ────────────────────────────────────────────
        self._travel_btn = None
        if is_connected and not is_current:
            btn = pygame.Rect(px + 8, py + ph - 38, pw - 16, 30)
            pygame.draw.rect(surface, (20, 60, 30), btn)
            pygame.draw.rect(surface, SUCCESS, btn, 1)
            label = self._font_med.render(
                f"▶  Travel  ({FUEL_COST_PER_SECTOR} fuel)", True, SUCCESS)
            surface.blit(label, (btn.centerx - label.get_width() // 2,
                                  btn.centery - label.get_height() // 2))
            self._travel_btn = btn
        elif is_current:
            here = self._font_med.render("★ You are here", True, ACCENT)
            surface.blit(here, (px + 8, py + ph - 32))
        else:
            not_conn = self._font_med.render("Not connected", True, TEXT_MUTED)
            surface.blit(not_conn, (px + 8, py + ph - 32))

    def to_dict(self) -> dict:
        return {
            "current_sector_id": self.current_sector_id,
            "sectors": {sid: s.to_dict() for sid, s in self.sectors.items()},
        }
