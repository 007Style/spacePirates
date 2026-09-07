"""tests/test_auto_gun_gating.py
Auto-gun gating unit tests.

Run from the spacePirates directory:
    python3 -m pytest tests/test_auto_gun_gating.py -v
or headlessly:
    SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python3 tests/test_auto_gun_gating.py
"""
import os
import sys
import types

# ── Minimal pygame stub so tests run headless ─────────────────────────────────
class _FakeFont:
    def render(self, *a, **k):
        surf = _FakeSurface()
        return surf
    def get_height(self): return 12

class _FakeSurface:
    def get_size(self): return (800, 600)
    def get_width(self): return 800
    def get_height(self): return 600
    def blit(self, *a, **k): pass
    def fill(self, *a, **k): pass
    def copy(self): return _FakeSurface()
    def get_rect(self): return _FakeRect(0, 0, 56, 36)

class _FakeRect:
    def __init__(self, x=0, y=0, w=0, h=0):
        self.x = x; self.y = y
        self.width = w; self.height = h
        self.centerx = x + w // 2
        self.centery = y + h // 2
        self.right = x + w
        self.left = x
        self.top = y
        self.bottom = y + h
        self.center = (self.centerx, self.centery)
    def collidepoint(self, *a): return False
    def inflate(self, *a): return _FakeRect()

# Pygame stub
pg = types.ModuleType("pygame")
pg.init = lambda: None
pg.font = types.SimpleNamespace(
    init=lambda: None,
    SysFont=lambda *a, **k: _FakeFont(),
)
pg.Surface = lambda size, *a, **k: _FakeSurface()
pg.Rect = _FakeRect
pg.SRCALPHA = 0x10000
pg.BLEND_ALPHA_SDL2 = 0

pg.MOUSEBUTTONDOWN = 1
pg.KEYDOWN = 2

class _EventModule:
    MOUSEBUTTONDOWN = 1
    KEYDOWN = 2
    def __init__(self):
        self.type = None
        self.pos = (0, 0)
        self.button = 0

pg.event = _EventModule()

class _DrawModule:
    def rect(self, *a, **k): pass
    def circle(self, *a, **k): pass
    def line(self, *a, **k): pass
    def polygon(self, *a, **k): pass
    def arc(self, *a, **k): pass

pg.draw = _DrawModule()
pg.transform = types.SimpleNamespace(rotate=lambda s, a: _FakeSurface())
pg.sprite = types.SimpleNamespace(Sprite=object, Group=list)
pg.mixer = types.SimpleNamespace(init=lambda: None)

sys.modules["pygame"] = pg
sys.modules["pygame.font"] = pg.font

# Add spacePirates directory to path
_HERE = os.path.dirname(__file__)
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# ── Stub splitscreen so MGMT_PANEL_X=0 (no coordinate offset in tests) ───────
# Must register this BEFORE importing ui.menus so the `from ui.splitscreen import`
# inside handle_event picks up our stub instead of the real module.
_split = types.ModuleType("ui.splitscreen")
_split.MGMT_PANEL_X = 0
sys.modules["ui.splitscreen"] = _split

# ── Stub out heavy transitive deps ────────────────────────────────────────────
for mod_name in [
    "progression.rarity",
    "entities.weapon",
    "entities.drone",
    "entities.projectile",
]:
    m = types.ModuleType(mod_name)
    if mod_name == "progression.rarity":
        _rs = types.SimpleNamespace(stat_multiplier=lambda r: 1.0,
                                    is_rare=lambda r: r in ("rare","epic","legendary"),
                                    rarity_color=lambda r: (255,255,255))
        m.rarity_system = _rs
    if mod_name == "entities.weapon":
        # Minimal Weapon stub — only needs to exist
        class _Weapon:
            def __init__(self, *a, **k): self.cooldown = 0; self.max_cooldown = 1
            def update(self, dt): pass
        m.Weapon = _Weapon
    if mod_name == "entities.drone":
        class _Drone:
            pass
        m.Drone = _Drone
    sys.modules[mod_name] = m

# Minimal settings stub
_settings = types.ModuleType("settings")
_settings.SCREEN_WIDTH  = 1280
_settings.SCREEN_HEIGHT = 800
_settings.DARK_BG       = (8, 8, 20)
_settings.DANGER        = (220, 50, 50)
_settings.SUCCESS       = (50, 200, 80)
_settings.WARNING       = (230, 180, 40)
_settings.WHITE         = (255, 255, 255)
_settings.ACCENT        = (60, 160, 255)
_settings.TEXT_MAIN     = (230, 230, 230)
_settings.TEXT_MUTED    = (130, 130, 150)
_settings.BORDER        = (50, 55, 80)
_settings.PANEL_BG      = (14, 16, 32)
_settings.RARITY_ORDER  = ["common", "uncommon", "rare", "epic", "legendary", "secret"]
class _State:
    MAIN_MENU = "main_menu"
    HOME_BASE = "home_base"
    COMBAT    = "combat"
_settings.State = _State
sys.modules["settings"] = _settings

# ── Now import the real modules ───────────────────────────────────────────────
from entities.crew import Crew   # noqa: E402
from ui.menus import CrewManagementMenu  # noqa: E402


# ── Helper builders ───────────────────────────────────────────────────────────
def make_crew(cid: str, role: str = "gunner", level: int = 1) -> Crew:
    c = Crew({
        "id": cid, "name": f"Crew_{cid}", "role": role,
        "rarity": "common",
        "stats": {"piloting": 5, "gunnery": 14, "engineering": 3,
                  "combat": 7, "repair": 2},
        "specialization_paths": {},
        "abilities": [],
        "price": 300,
    })
    c.level = level
    return c


class _FakeShip:
    """Minimal Ship stand-in for testing CrewManagementMenu."""
    def __init__(self):
        from entities.ship import STATIONS
        self.id    = "test_ship"
        self.ship_class = "fighter"
        self.crew  = []
        self.station_assignments = {s: None for s in STATIONS}

    def add_crew(self, member):
        if member not in self.crew:
            self.crew.append(member)
            member.assigned_ship = self.id

    def assign_station(self, member, station):
        from entities.ship import STATIONS
        if station not in STATIONS or member not in self.crew:
            return False
        if member.assigned_station:
            self.station_assignments[member.assigned_station] = None
        old = self.station_assignments.get(station)
        if old:
            old.assigned_station = None
        self.station_assignments[station] = member
        member.assigned_station = station
        return True

    def equip_best(self):
        pass


# ── Click-event factory ───────────────────────────────────────────────────────
def _click(rect):
    ev = types.SimpleNamespace(
        type=pg.event.MOUSEBUTTONDOWN,
        button=1,
        pos=(rect.x + 1, rect.y + 1),
    )
    return ev


# ═══════════════════════════════════════════════════════════════════════════════
# Tests
# ═══════════════════════════════════════════════════════════════════════════════

def test_1_gun_auto_blocked_when_cockpit_off():
    """gun_turret AUTO cannot turn ON while cockpit AUTO is OFF."""
    menu = CrewManagementMenu()
    ship = _FakeShip()
    # Manually register a fake rect for gun_turret (simulating a draw call)
    gun_rect = _FakeRect(500, 100, 40, 18)
    gun_rect.collidepoint = lambda x, y: (500 <= x < 540 and 100 <= y < 118)
    menu._auto_rects["gun_turret"] = gun_rect
    menu._last_gun_turret_crew = None

    # cockpit is OFF (default) — click gun_turret auto
    ev = _click(gun_rect)
    result = menu.handle_event(ev, ship)

    assert result == "gun_auto_denied:no_cockpit", f"Expected denial, got {result!r}"
    assert not menu._auto["gun_turret"], "gun_turret AUTO should remain OFF"
    print("PASS test_1: gun_turret blocked when cockpit OFF")


def test_2_gun_auto_blocked_when_no_gunner():
    """gun_turret AUTO denied when cockpit is ON but no gunner assigned."""
    menu = CrewManagementMenu()
    menu._auto["cockpit"] = True        # cockpit is ON
    ship = _FakeShip()

    gun_rect = _FakeRect(500, 100, 40, 18)
    gun_rect.collidepoint = lambda x, y: (500 <= x < 540 and 100 <= y < 118)
    menu._auto_rects["gun_turret"] = gun_rect
    menu._last_gun_turret_crew = None   # no gunner

    ev = _click(gun_rect)
    result = menu.handle_event(ev, ship)

    assert result == "gun_auto_denied:low_level", f"Expected low_level denial, got {result!r}"
    assert not menu._auto["gun_turret"]
    print("PASS test_2: gun_turret blocked when no gunner assigned")


def test_3_gun_auto_blocked_when_gunner_too_low():
    """gun_turret AUTO denied when gunner is level 2 (needs 3+)."""
    menu = CrewManagementMenu()
    menu._auto["cockpit"] = True
    ship = _FakeShip()

    low_gunner = make_crew("g_low", level=2)
    ship.add_crew(low_gunner)
    ship.assign_station(low_gunner, "gun_turret")

    gun_rect = _FakeRect(500, 100, 40, 18)
    gun_rect.collidepoint = lambda x, y: (500 <= x < 540 and 100 <= y < 118)
    menu._auto_rects["gun_turret"] = gun_rect
    menu._last_gun_turret_crew = low_gunner   # set as if draw() ran

    ev = _click(gun_rect)
    result = menu.handle_event(ev, ship)

    assert result == "gun_auto_denied:low_level", f"Expected low_level denial, got {result!r}"
    assert not menu._auto["gun_turret"]
    print("PASS test_3: gun_turret blocked when gunner < level 3")


def test_4_gun_auto_allowed_with_lv3_gunner_and_cockpit_on():
    """gun_turret AUTO can turn ON: cockpit ON + Lv3 gunner assigned."""
    menu = CrewManagementMenu()
    menu._auto["cockpit"] = True
    ship = _FakeShip()

    gunner3 = make_crew("g3", level=3)
    ship.add_crew(gunner3)
    ship.assign_station(gunner3, "gun_turret")

    gun_rect = _FakeRect(500, 100, 40, 18)
    gun_rect.collidepoint = lambda x, y: (500 <= x < 540 and 100 <= y < 118)
    menu._auto_rects["gun_turret"] = gun_rect
    menu._last_gun_turret_crew = gunner3

    ev = _click(gun_rect)
    result = menu.handle_event(ev, ship)

    assert result == "auto_toggle:gun_turret", f"Expected toggle, got {result!r}"
    assert menu._auto["gun_turret"], "gun_turret AUTO should now be ON"
    print("PASS test_4: gun_turret AUTO enabled with Lv3 gunner + cockpit ON")


def test_5_cockpit_off_cascades_to_gun_auto():
    """Turning cockpit AUTO OFF forces gun_turret AUTO OFF too."""
    menu = CrewManagementMenu()
    menu._auto["cockpit"]    = True
    menu._auto["gun_turret"] = True

    cockpit_rect = _FakeRect(500, 60, 40, 18)
    cockpit_rect.collidepoint = lambda x, y: (500 <= x < 540 and 60 <= y < 78)
    menu._auto_rects["cockpit"] = cockpit_rect

    ev = _click(cockpit_rect)
    result = menu.handle_event(ev, None)

    assert result == "auto_toggle:cockpit", f"Expected cockpit toggle, got {result!r}"
    assert not menu._auto["cockpit"],    "cockpit AUTO should now be OFF"
    assert not menu._auto["gun_turret"], "gun_turret AUTO should cascade to OFF"
    print("PASS test_5: cockpit OFF cascades gun_turret OFF")


def test_6_gun_auto_allowed_with_lv4_gunner():
    """
    Test 6 (the previously failing test):
    gun_turret AUTO works with a Lv4 gunner when cockpit is ON.
    The fix is: add crew to ship BEFORE calling assign_station
    (assign_station rejects crew not in ship.crew).
    """
    menu = CrewManagementMenu()
    menu._auto["cockpit"] = True
    ship = _FakeShip()

    high_gunner2 = make_crew("hg2", level=4)
    # FIX: add to ship.crew first, THEN assign station
    ship.add_crew(high_gunner2)
    ok = ship.assign_station(high_gunner2, "gun_turret")
    assert ok, "assign_station should succeed after add_crew"
    assert ship.station_assignments["gun_turret"] is high_gunner2, \
        "gun_turret station should be set to high_gunner2"

    gun_rect = _FakeRect(500, 100, 40, 18)
    gun_rect.collidepoint = lambda x, y: (500 <= x < 540 and 100 <= y < 118)
    menu._auto_rects["gun_turret"] = gun_rect
    # Simulate the draw loop having set _last_gun_turret_crew
    menu._last_gun_turret_crew = high_gunner2

    ev = _click(gun_rect)
    result = menu.handle_event(ev, ship)

    assert result == "auto_toggle:gun_turret", \
        f"Expected 'auto_toggle:gun_turret', got {result!r}"
    assert menu._auto["gun_turret"], \
        "gun_turret AUTO should be ON with Lv4 gunner + cockpit ON"
    print("PASS test_6: gun_turret AUTO enabled with Lv4 gunner (previously failing)")


def test_7_assign_station_requires_crew_in_ship():
    """assign_station returns False if crew member not in ship.crew first."""
    ship = _FakeShip()
    orphan = make_crew("orphan", level=5)
    # Do NOT add to ship — assign_station should refuse
    ok = ship.assign_station(orphan, "gun_turret")
    assert not ok, "assign_station should reject crew not in ship.crew"
    assert ship.station_assignments["gun_turret"] is None
    print("PASS test_7: assign_station rejects orphan crew")


def test_8_gun_auto_turns_off_when_already_on():
    """Clicking gun_turret AUTO when it's already ON turns it OFF (no gates)."""
    menu = CrewManagementMenu()
    menu._auto["cockpit"]    = True
    menu._auto["gun_turret"] = True   # already ON

    gun_rect = _FakeRect(500, 100, 40, 18)
    gun_rect.collidepoint = lambda x, y: (500 <= x < 540 and 100 <= y < 118)
    menu._auto_rects["gun_turret"] = gun_rect

    ev = _click(gun_rect)
    result = menu.handle_event(ev, None)

    assert result == "auto_toggle:gun_turret", f"Expected toggle, got {result!r}"
    assert not menu._auto["gun_turret"], "gun_turret AUTO should now be OFF"
    print("PASS test_8: gun_turret AUTO can be turned back OFF freely")


# ── Runner ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    tests = [
        test_1_gun_auto_blocked_when_cockpit_off,
        test_2_gun_auto_blocked_when_no_gunner,
        test_3_gun_auto_blocked_when_gunner_too_low,
        test_4_gun_auto_allowed_with_lv3_gunner_and_cockpit_on,
        test_5_cockpit_off_cascades_to_gun_auto,
        test_6_gun_auto_allowed_with_lv4_gunner,
        test_7_assign_station_requires_crew_in_ship,
        test_8_gun_auto_turns_off_when_already_on,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as exc:
            import traceback
            print(f"FAIL {t.__name__}: {exc}")
            traceback.print_exc()
            failed += 1

    print(f"\n{'='*50}")
    print(f"Results: {passed}/{len(tests)} passed, {failed} failed")
    if failed:
        sys.exit(1)
    print("ALL TESTS PASSED ✓")
