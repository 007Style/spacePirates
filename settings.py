# ── Screen ──────────────────────────────────────────────────────────────────
SCREEN_WIDTH  = 1280
SCREEN_HEIGHT = 720
FPS           = 60
TITLE         = "Space Pirates"

# ── Colors ───────────────────────────────────────────────────────────────────
BLACK       = (0,   0,   0)
WHITE       = (255, 255, 255)
DARK_BG     = (10,  10,  20)
PANEL_BG    = (18,  18,  35)
BORDER      = (50,  50,  80)
TEXT_MAIN   = (220, 220, 240)
TEXT_MUTED  = (120, 120, 150)
ACCENT      = (80,  160, 255)
WARNING     = (255, 180,  40)
DANGER      = (220,  50,  50)
SUCCESS     = (60,  200,  80)

# ── Rarity tiers ─────────────────────────────────────────────────────────────
# Each entry: (name, color_rgb, stat_multiplier, drop_weight)
RARITY_TIERS = {
    "common":    ("Common",    (160, 160, 160), 1.0,  60),
    "uncommon":  ("Uncommon",  ( 80, 200,  80), 1.3,  25),
    "rare":      ("Rare",      ( 60, 120, 255), 1.7,  10),
    "epic":      ("Epic",      (160,  60, 220), 2.2,   4),
    "legendary": ("Legendary", (255, 160,  30), 3.0,   1),
    "secret":    ("Secret",    (220,  30,  30), 4.5,   0.1),
}

# Colorblind-mode shape codes per rarity
RARITY_SHAPES = {
    "common":    "circle",
    "uncommon":  "square",
    "rare":      "diamond",
    "epic":      "star",
    "legendary": "crown",
    "secret":    "skull",
}

# ── Rarity order (ascending) ──────────────────────────────────────────────────
RARITY_ORDER = ["common", "uncommon", "rare", "epic", "legendary", "secret"]

# ── Game States ───────────────────────────────────────────────────────────────
class State:
    MAIN_MENU      = "main_menu"
    PLAYING        = "playing"
    PAUSED         = "paused"
    GAME_OVER      = "game_over"
    BASE           = "base"
    GALAXY_MAP     = "galaxy_map"
    BOARDING       = "boarding"
    UPGRADE_TREE   = "upgrade_tree"
    LOAD_SCREEN    = "load_screen"
    ORIGIN_SELECT  = "origin_select"

# ── Combat ────────────────────────────────────────────────────────────────────
COMBAT_SPEED_DEFAULT = 1.0   # multiplier; slider range 0.5–2.0
PAUSE_KEY            = "space"

# ── Economy ──────────────────────────────────────────────────────────────────
STARTING_CREDITS = 500
FUEL_COST_PER_SECTOR = 10

# ── Fleet ────────────────────────────────────────────────────────────────────
MAX_FLEET_SLOTS_BASE = 3      # increased via meta-upgrades

# ── Progression ──────────────────────────────────────────────────────────────
POINTS_PER_KILL   = 1
POINTS_BOSS_BONUS = 20
POINTS_QUEST_BONUS = 5

# ── Wanted Level ─────────────────────────────────────────────────────────────
MAX_WANTED_LEVEL  = 5
WANTED_DECAY_TICKS = 3600     # ticks between wanted level decrements

# ── Save ─────────────────────────────────────────────────────────────────────
SAVE_SLOTS     = 3
SAVE_DIR       = "saves"
AUTO_SAVE_FILE = "autosave"

# ── Audio ─────────────────────────────────────────────────────────────────────
MUSIC_VOLUME = 0.4
SFX_VOLUME   = 0.7

# ── Paths ─────────────────────────────────────────────────────────────────────
ASSET_DIR  = "assets"
SPRITE_DIR = f"{ASSET_DIR}/sprites"
SOUND_DIR  = f"{ASSET_DIR}/sounds"
MUSIC_DIR  = f"{ASSET_DIR}/music"
FONT_DIR   = f"{ASSET_DIR}/fonts"
DATA_DIR   = "data"
