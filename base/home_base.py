"""base/home_base.py — Home base manager."""
from __future__ import annotations
import math
import random
import pygame
from base.buildings  import Building, make_buildings
from base.raiders    import RaiderManager
from settings        import (
    SCREEN_WIDTH, SCREEN_HEIGHT, DARK_BG, PANEL_BG, BORDER,
    TEXT_MAIN, TEXT_MUTED, ACCENT, SUCCESS, WARNING, DANGER, WHITE,
)


# ── Armory / Gear Store catalogue ─────────────────────────────────────────────
GEAR_CATALOGUE = [
    # Weapons
    {"id": "pulse_laser",    "name": "Pulse Laser",       "type": "weapon",  "cost": 300,  "rarity": "common",   "desc": "Fast-firing energy weapon. +8 dmg/shot."},
    {"id": "cannon_heavy",   "name": "Heavy Cannon",      "type": "weapon",  "cost": 600,  "rarity": "uncommon", "desc": "Slow but devastating. +22 dmg/shot."},
    {"id": "plasma_burst",   "name": "Plasma Burst",      "type": "weapon",  "cost": 900,  "rarity": "rare",     "desc": "Area pulse that slows enemies. +18 dmg."},
    {"id": "void_lance",     "name": "Void Lance",        "type": "weapon",  "cost": 2200, "rarity": "epic",     "desc": "Penetrates shields entirely. +35 dmg."},
    {"id": "railgun_sniper", "name": "Railgun Sniper",    "type": "weapon",  "cost": 1500, "rarity": "rare",     "desc": "Extreme range, one-shot power. +40 dmg."},
    # Ship modules / gear
    {"id": "shield_booster", "name": "Shield Booster",   "type": "module",  "cost": 400,  "rarity": "common",   "desc": "Installs extra shield cell. +40 shield."},
    {"id": "hull_plate",     "name": "Reinforced Hull",   "type": "module",  "cost": 500,  "rarity": "common",   "desc": "Armour plating. +60 hull points."},
    {"id": "engine_boost",   "name": "Engine Overcharge", "type": "module",  "cost": 700,  "rarity": "uncommon", "desc": "Speed chip. +20 speed permanently."},
    {"id": "stealth_coat",   "name": "Stealth Coating",   "type": "module",  "cost": 1200, "rarity": "rare",     "desc": "Evasion +8% vs enemy targeting."},
    {"id": "repair_drone_kit","name": "Repair Drone Kit", "type": "module",  "cost": 800,  "rarity": "uncommon", "desc": "Auto-repair 3 HP/sec in combat."},
    # Drones for sale
    {"id": "combat_drone",   "name": "Combat Drone",      "type": "drone",   "cost": 350,  "rarity": "common",   "desc": "Attacks enemies. Low HP but fast."},
    {"id": "scout_drone",    "name": "Scout Drone",       "type": "drone",   "cost": 250,  "rarity": "common",   "desc": "Reveals enemy positions on radar."},
    {"id": "repair_drone",   "name": "Repair Drone",      "type": "drone",   "cost": 450,  "rarity": "uncommon", "desc": "Hovers near ally, heals 5 HP/sec."},
    {"id": "bomb_drone",     "name": "Bomb Drone",        "type": "drone",   "cost": 600,  "rarity": "rare",     "desc": "Kamikazes into enemies. Huge burst dmg."},
    # Ships for sale
    {"id": "fighter_mk1",    "name": "Corsair Mk I",      "type": "ship",    "cost": 800,  "rarity": "common",   "desc": "Nimble fighter. Good starter vessel."},
    {"id": "fighter_mk2",    "name": "Viper Mk II",       "type": "ship",    "cost": 2200, "rarity": "uncommon", "desc": "Upgraded fighter with twin turrets."},
    {"id": "freighter_mk1",  "name": "Bulkhead Hauler",   "type": "ship",    "cost": 1200, "rarity": "common",   "desc": "Slow heavy freighter. Great hull."},
    {"id": "carrier_mk1",    "name": "Ironwing Carrier",  "type": "ship",    "cost": 15000,"rarity": "uncommon", "desc": "Carrier with drone bays and troops."},
]

# ── Crew gear items (equippable by individual crew members) ───────────────────
CREW_GEAR_ITEMS = [
    # HEAD slot
    {"id": "cg_targeting_visor",  "name": "Targeting Visor",   "slot": "head", "role": "gunner",
     "rarity": "common",   "cost": 300,
     "stats": {"gunnery": 4},
     "desc": "HUD overlay; +4 gunnery.",
     "avatar_tint": (255, 200, 60)},
    {"id": "cg_nav_helm",         "name": "Nav Helm",           "slot": "head", "role": "pilot",
     "rarity": "common",   "cost": 280,
     "stats": {"piloting": 4},
     "desc": "Holographic nav display; +4 piloting.",
     "avatar_tint": (80, 180, 255)},
    {"id": "cg_combat_helmet",    "name": "Combat Helmet",      "slot": "head", "role": "any",
     "rarity": "common",   "cost": 250,
     "stats": {"combat": 3},
     "desc": "Ballistic-rated; +3 combat.",
     "avatar_tint": (160, 160, 160)},
    {"id": "cg_drone_uplink",     "name": "Drone Uplink Crown", "slot": "head", "role": "engineer",
     "rarity": "uncommon", "cost": 600,
     "stats": {"repair": 3, "gunnery": 2},
     "desc": "Neural uplink to drones; +3 repair +2 gunnery.",
     "avatar_tint": (255, 140, 60)},
    {"id": "cg_psi_headset",      "name": "Psi Headset",        "slot": "head", "role": "any",
     "rarity": "rare",     "cost": 1200,
     "stats": {"piloting": 4, "gunnery": 4},
     "desc": "Empathic targeting; +4 piloting +4 gunnery.",
     "avatar_tint": (180, 80, 255)},
    # BODY slot
    {"id": "cg_pilot_suit",       "name": "G-Force Suit",       "slot": "body", "role": "pilot",
     "rarity": "common",   "cost": 350,
     "stats": {"piloting": 5, "combat": -1},
     "desc": "Flight suit; +5 piloting, -1 combat.",
     "avatar_tint": (80, 160, 255)},
    {"id": "cg_gunner_vest",      "name": "Ballistic Vest",     "slot": "body", "role": "gunner",
     "rarity": "common",   "cost": 350,
     "stats": {"combat": 4, "gunnery": 2},
     "desc": "Armored vest; +4 combat +2 gunnery.",
     "avatar_tint": (180, 100, 40)},
    {"id": "cg_engineer_coat",    "name": "Engineer's Coat",    "slot": "body", "role": "engineer",
     "rarity": "uncommon", "cost": 500,
     "stats": {"repair": 6, "engineering": 4},
     "desc": "Tool-lined coat; +6 repair +4 engineering.",
     "avatar_tint": (100, 200, 120)},
    {"id": "cg_stealth_cloak",    "name": "Stealth Cloak",      "slot": "body", "role": "any",
     "rarity": "rare",     "cost": 1100,
     "stats": {"combat": 6, "piloting": 3},
     "desc": "Light-bending cloak; +6 combat +3 piloting.",
     "avatar_tint": (40, 40, 80)},
    {"id": "cg_powered_armour",   "name": "Powered Armour",     "slot": "body", "role": "any",
     "rarity": "epic",     "cost": 2500,
     "stats": {"combat": 10, "repair": -2},
     "desc": "Exo-suit; +10 combat, -2 repair.",
     "avatar_tint": (220, 60, 60)},
    # TOOL slot
    {"id": "cg_repair_wrench",    "name": "Nano-Wrench",        "slot": "tool", "role": "engineer",
     "rarity": "common",   "cost": 200,
     "stats": {"repair": 5},
     "desc": "Nano-tip repair tool; +5 repair.",
     "avatar_tint": (120, 220, 120)},
    {"id": "cg_sidearm",          "name": "Sidearm Pistol",     "slot": "tool", "role": "any",
     "rarity": "common",   "cost": 180,
     "stats": {"combat": 4},
     "desc": "Compact sidearm; +4 combat.",
     "avatar_tint": (200, 160, 80)},
    {"id": "cg_scanner",          "name": "Tactical Scanner",   "slot": "tool", "role": "any",
     "rarity": "uncommon", "cost": 450,
     "stats": {"piloting": 2, "gunnery": 3},
     "desc": "Combat scanner; +2 piloting +3 gunnery.",
     "avatar_tint": (60, 220, 255)},
    {"id": "cg_drone_toolkit",    "name": "Drone Toolkit",      "slot": "tool", "role": "engineer",
     "rarity": "uncommon", "cost": 550,
     "stats": {"repair": 4, "engineering": 5},
     "desc": "Field drone kit; +4 repair +5 engineering.",
     "avatar_tint": (255, 160, 40)},
    {"id": "cg_void_blade",       "name": "Void Blade",         "slot": "tool", "role": "any",
     "rarity": "epic",     "cost": 2200,
     "stats": {"combat": 12, "gunnery": 4},
     "desc": "Phase-edge blade; +12 combat +4 gunnery.",
     "avatar_tint": (160, 60, 255)},
]

# ── Per-role crew quirks ───────────────────────────────────────────────────────
CREW_QUIRKS_BY_ROLE = {
    "pilot": [
        ("Smooth Hands",      "Reduces weapon spread by 5% when piloting.",    True),
        ("Speed Demon",       "+10% speed when below 30% hull.",               True),
        ("Nervous Flier",     "-2 piloting in nebula sectors.",                 False),
        ("Ace Instinct",      "10% chance to auto-evade on critical hit.",     True),
        ("Star Reader",       "Fuel consumption -8%.",                          True),
        ("Reckless",          "+5 piloting, -3 repair.",                        True),
    ],
    "gunner": [
        ("Eagle Eye",         "+3 gunnery vs shields.",                        True),
        ("Hair Trigger",      "-0.2 s fire cooldown.",                          True),
        ("Reload Drills",     "Weapons reload 12% faster.",                     True),
        ("Ammo Hoarder",      "+10% damage with kinetic weapons.",              True),
        ("Skittish",          "-2 gunnery when hull < 50%.",                    False),
        ("Double Tap",        "5% chance to fire twice per shot.",              True),
    ],
    "engineer": [
        ("Jury Rigger",       "Repairs 2 extra HP per second in combat.",      True),
        ("Overclocker",       "+15% drone speed, +10% drone damage.",          True),
        ("Grease Monkey",     "Ship repairs cost 15% less metal.",             True),
        ("Shield Tuner",      "Shield recharge starts 2 s sooner.",            True),
        ("Burnout",           "-3 repair after two combat missions.",          False),
        ("Scavenger",         "+20% metal collected from destroyed ships.",    True),
    ],
    "mechanic": [
        ("Field Surgeon",     "Reduces crew injury recovery by 20 ticks.",    True),
        ("Hull Patcher",      "+40 hull repaired per repair action.",           True),
        ("Improvised Parts",  "Can repair with metal when credits low.",        True),
        ("Cautious",          "-1 repair speed but never makes errors.",        True),
        ("Tinkerer",          "Modules cost 10% less to install.",             True),
    ],
    "combat": [
        ("Berserker",         "+5 combat when below 25% hull.",                True),
        ("Boarding Expert",   "+3 combat during boarding actions.",            True),
        ("Battle Scarred",    "Immune to first morale break per combat.",      True),
        ("Volatile",          "-2 morale if combat is lost.",                   False),
        ("Intimidator",       "Enemy crew -10% combat on boarding.",           True),
        ("Iron Will",         "Injury recovery 30% faster.",                   True),
    ],
}

# ── Crew management species definitions ──────────────────────────────────────
CREW_SPECIES = [
    {"id": "human",    "name": "Human",    "bonus": "+5% all stats",        "icon": "H", "color": (200, 200, 200)},
    {"id": "robot",    "name": "Robot",    "bonus": "+15% repair, no morale","icon": "R", "color": (100, 200, 255)},
    {"id": "alien",    "name": "Alien",    "bonus": "+20% combat, low pay",  "icon": "A", "color": (80, 255, 120)},
    {"id": "android",  "name": "Android",  "bonus": "+10% gunnery & pilot",  "icon": "D", "color": (255, 180, 60)},
    {"id": "mutant",   "name": "Mutant",   "bonus": "High combat, unstable", "icon": "M", "color": (220, 80, 255)},
]

CREW_ROLES = ["Pilot", "Gunner", "Engineer", "Medic", "Brawler", "Navigator", "Hacker"]

# ── Research web node definitions ─────────────────────────────────────────────
# Each node: (id, name, category, cost_research, requires[], description, unlocks_desc)
RESEARCH_NODES = [
    # Tier 0 — always available
    ("res_basic_weapons",   "Basic Weapons",    "weapons", 50,  [],                        "Foundation of all weapons R&D.",           "Unlocks Pulse Laser Mk2 in shop"),
    ("res_basic_shields",   "Basic Shields",    "defense", 50,  [],                        "Hull & shield fundamentals.",              "Unlocks Shield Booster Mk2"),
    ("res_basic_engines",   "Basic Engines",    "engines", 50,  [],                        "Drive system baseline research.",          "Unlocks Engine Overcharge Mk2"),
    ("res_basic_drones",    "Basic Drones",     "drones",  50,  [],                        "Drone fabrication basics.",                "Unlocks Combat & Scout Drones"),
    # Tier 1 — requires one Tier 0
    ("res_energy_weapons",  "Energy Weapons",   "weapons", 120, ["res_basic_weapons"],     "Advanced laser & plasma tech.",            "Unlocks Plasma Burst, Void Lance"),
    ("res_ballistics",      "Ballistics",       "weapons", 120, ["res_basic_weapons"],     "Kinetic projectile mastery.",              "Unlocks Heavy Cannon, Railgun"),
    ("res_heavy_armor",     "Heavy Armor",      "defense", 120, ["res_basic_shields"],     "Reinforced composite plating.",            "Unlocks Reinforced Hull Mk2"),
    ("res_phase_shields",   "Phase Shields",    "defense", 150, ["res_basic_shields"],     "Phase-state shield matrix.",               "Shields recharge 50% faster"),
    ("res_warp_drives",     "Warp Drives",      "engines", 150, ["res_basic_engines"],     "Short-burst warp capability.",             "Unlocks Warp Jump in sectors"),
    ("res_stealth",         "Stealth Systems",  "engines", 180, ["res_basic_engines"],     "EM dampening and cloaking.",               "Unlocks Stealth Coating"),
    ("res_attack_drones",   "Attack Drones",    "drones",  130, ["res_basic_drones"],      "Weaponized autonomous drones.",            "Unlocks Bomb Drone, Swarm Drone"),
    ("res_repair_drones",   "Repair Drones",    "drones",  130, ["res_basic_drones"],      "Field repair drone systems.",              "Unlocks Repair Drone Mk2"),
    # Tier 2 — requires Tier 1
    ("res_void_weapons",    "Void Weapons",     "weapons", 300, ["res_energy_weapons"],    "Void-rift based weaponry.",                "Unlocks Void Lance Mk2"),
    ("res_ship_fighter",    "Fighter Class",    "ships",   200, ["res_basic_weapons","res_basic_shields"], "Fighter ship upgrades.",    "Unlocks Elite Fighter, Phantom Blade"),
    ("res_ship_carrier",    "Carrier Class",    "ships",   350, ["res_heavy_armor","res_repair_drones"],   "Carrier ship research.",    "Unlocks Vanguard Carrier"),
    ("res_ship_freighter",  "Freighter Class",  "ships",   250, ["res_heavy_armor"],       "Heavy freighter upgrades.",                "Unlocks Heavy Freighter, Dreadnought"),
    ("res_autonomous",      "Autonomous AI",    "drones",  400, ["res_attack_drones","res_repair_drones"], "Full autonomous drone AI.", "Drones last 3x longer"),
    ("res_wormhole",        "Wormhole Tech",    "engines", 500, ["res_warp_drives","res_stealth"],         "Wormhole creation device.", "Unlocks fast-travel routes"),
]

# ── Trading / nations data ─────────────────────────────────────────────────────
TRADE_NATIONS = [
    {
        "id": "terran_compact",
        "name": "Terran Compact",
        "color": (80, 160, 255),
        "desc": "Military republic. Strict but fair. Sells weapons and armor.",
        "base_relation": 0,
        "sells": [
            {"id": "mil_cannon",   "name": "Mil-Grade Cannon",  "cost_credits": 0, "cost_metal": 0, "cost_resource": "credits", "price": 800,  "desc": "+28 dmg cannon"},
            {"id": "armor_plate",  "name": "Compact Armor",     "cost_resource": "credits", "price": 600,   "desc": "+80 hull points"},
            {"id": "fuel_x2",      "name": "Military Fuel Pack", "cost_resource": "credits", "price": 200,   "desc": "+80 fuel"},
        ],
        "buys": [
            {"id": "contraband",   "name": "Contraband",        "price_per": 50,   "resource_key": "contraband"},
            {"id": "void_crystals","name": "Void Crystals",     "price_per": 400,  "resource_key": "void_crystals"},
        ],
        "relation_bonuses": {20: "10% discount", 50: "Rare weapons access", 80: "Alliance — no wanted level from Compact"},
    },
    {
        "id": "merchant_syndicate",
        "name": "Merchant Syndicate",
        "color": (60, 220, 120),
        "desc": "Trade guild. Money is religion. Best prices, exotic goods.",
        "base_relation": 10,
        "sells": [
            {"id": "exotic_fuel",  "name": "Exotic Fuel",       "cost_resource": "credits", "price": 150,   "desc": "+100 fuel"},
            {"id": "trade_credit", "name": "Trade Credit Chip",  "cost_resource": "credits", "price": 500,   "desc": "+1000cr next trade"},
            {"id": "supply_pack",  "name": "Supply Pack",       "cost_resource": "credits", "price": 120,   "desc": "+80 supplies"},
        ],
        "buys": [
            {"id": "metal",        "name": "Raw Metal",         "price_per": 8,    "resource_key": "metal"},
            {"id": "supplies",     "name": "Supplies",          "price_per": 12,   "resource_key": "supplies"},
            {"id": "contraband",   "name": "Contraband",        "price_per": 80,   "resource_key": "contraband"},
        ],
        "relation_bonuses": {20: "+10% sell price", 50: "Black market access", 80: "Smuggler's Route — hidden sector unlocked"},
    },
    {
        "id": "free_colonies",
        "name": "Free Colonies",
        "color": (220, 160, 60),
        "desc": "Independent settlers. Rough but loyal. Great for crew and salvage.",
        "base_relation": 20,
        "sells": [
            {"id": "salvage_drones","name": "Salvage Drones",   "cost_resource": "credits", "price": 300,   "desc": "Auto-collects metal in sectors"},
            {"id": "colony_brew",   "name": "Colony Brew",      "cost_resource": "credits", "price": 80,    "desc": "+30 crew morale"},
            {"id": "scrap_metal",   "name": "Scrap Metal",      "cost_resource": "credits", "price": 60,    "desc": "+120 metal"},
        ],
        "buys": [
            {"id": "fuel",         "name": "Fuel",              "price_per": 15,   "resource_key": "fuel"},
            {"id": "void_crystals","name": "Void Crystals",     "price_per": 500,  "resource_key": "void_crystals"},
        ],
        "relation_bonuses": {20: "Crew hire at -20% cost", 50: "Colony Militia joins raids", 80: "Permanent +2 crew slots"},
    },
    {
        "id": "technocracy",
        "name": "Technocracy",
        "color": (180, 80, 255),
        "desc": "Science collective. Sells research boosts and advanced modules.",
        "base_relation": -10,
        "sells": [
            {"id": "research_boost","name": "Research Accelerator","cost_resource": "void_crystals", "price": 2, "desc": "+100 research points"},
            {"id": "nano_repair",   "name": "Nano Repair Kit",   "cost_resource": "credits", "price": 1200,  "desc": "Instantly repair 200 hull"},
            {"id": "ai_pilot",      "name": "AI Pilot Module",   "cost_resource": "credits", "price": 2000,  "desc": "Autopilot improves 25%"},
        ],
        "buys": [
            {"id": "metal",        "name": "Raw Metal",         "price_per": 10,   "resource_key": "metal"},
            {"id": "contraband",   "name": "Contraband",        "price_per": 30,   "resource_key": "contraband"},
        ],
        "relation_bonuses": {20: "+25% research speed", 50: "Tech weapon schematics", 80: "Technocracy ships join your fleet"},
    },
    {
        "id": "void_collective",
        "name": "Void Collective",
        "color": (255, 60, 60),
        "desc": "Ancient alien faction. Hostile unless you earn trust. Rare void tech.",
        "base_relation": -30,
        "sells": [
            {"id": "void_crystal_stash","name": "Void Crystal Stash","cost_resource": "credits","price": 3000,"desc": "+10 void crystals"},
            {"id": "void_weapon",  "name": "Void Resonance Weapon","cost_resource": "void_crystals","price": 5,"desc": "+50 dmg, void damage type"},
            {"id": "void_drive",   "name": "Void Drive Core",  "cost_resource": "void_crystals","price": 8, "desc": "Infinite fuel for 1 sector"},
        ],
        "buys": [
            {"id": "supplies",     "name": "Supplies",          "price_per": 5,    "resource_key": "supplies"},
            {"id": "credits_bulk", "name": "Credits (bulk)",    "price_per": 0.001,"resource_key": "credits"},
        ],
        "relation_bonuses": {10: "Void tech shop unlocked", 30: "Void escort protection", 60: "Ancient weapon schematic"},
    },
]


# ── Mercenary roster definitions ──────────────────────────────────────────────
MERCENARY_ROSTER = [
    {"name": "Sid the Gun",    "role": "Gunner",    "cost": 400, "combat": 12, "stat": "gunnery",     "rarity": "uncommon",
     "desc": "Former Navy sharpshooter. Never misses twice."},
    {"name": "Raka",           "role": "Pilot",     "cost": 350, "combat": 7,  "stat": "piloting",    "rarity": "common",
     "desc": "Asteroid-belt racer turned gun-for-hire."},
    {"name": "Iron Yasha",     "role": "Brawler",   "cost": 600, "combat": 18, "stat": "combat",      "rarity": "rare",
     "desc": "Six-foot cyborg with a grudge and a plasma fist."},
    {"name": "Dr. Vex",        "role": "Medic",     "cost": 300, "combat": 4,  "stat": "repair",      "rarity": "common",
     "desc": "Licensed in three systems. Unlicensed in four others."},
    {"name": "Nyx",            "role": "Smuggler",  "cost": 500, "combat": 9,  "stat": "evasion",     "rarity": "uncommon",
     "desc": "Knows every back-door in the sector. Slippery."},
    {"name": "Mira Blackstar", "role": "Engineer",  "cost": 450, "combat": 6,  "stat": "engineering", "rarity": "uncommon",
     "desc": "Fixes engines with whatever's around. Somehow it holds."},
    {"name": "The Judge",      "role": "Bounty Hunter", "cost": 800, "combat": 20, "stat": "combat",  "rarity": "rare",
     "desc": "Wants dead. Accepts live. Prefers neither."},
    {"name": "Wren Calo",      "role": "Hacker",    "cost": 650, "combat": 5,  "stat": "engineering", "rarity": "rare",
     "desc": "Cracks enemy shields and ship systems in seconds."},
    {"name": "Oryx",           "role": "Navigator", "cost": 420, "combat": 6,  "stat": "piloting",    "rarity": "uncommon",
     "desc": "Charts hyperspace routes no one else dares to use."},
]

# ── Regular hireable crew (non-mercenary, cheaper, lower stats) ───────────────
REGULAR_CREW_ROSTER = [
    {"name": "Tam",    "role": "Gunner",    "cost": 180, "combat": 7,  "stat": "gunnery",     "rarity": "common",
     "desc": "Decent shot. Reliable under pressure."},
    {"name": "Kai",    "role": "Pilot",     "cost": 160, "combat": 5,  "stat": "piloting",    "rarity": "common",
     "desc": "Can fly most ships. Prefers the fast ones."},
    {"name": "Bren",   "role": "Engineer",  "cost": 170, "combat": 4,  "stat": "engineering", "rarity": "common",
     "desc": "Keeps the engines running. Usually."},
    {"name": "Sloane", "role": "Medic",     "cost": 150, "combat": 3,  "stat": "repair",      "rarity": "common",
     "desc": "Patch jobs, stims, and a steady hand."},
    {"name": "Ruck",   "role": "Brawler",   "cost": 200, "combat": 10, "stat": "combat",      "rarity": "common",
     "desc": "Big. Not too bright. Very effective."},
    {"name": "Dex",    "role": "Navigator", "cost": 175, "combat": 4,  "stat": "piloting",    "rarity": "common",
     "desc": "Good with charts and a quiet shift."},
]

# ── Side-quest definitions ────────────────────────────────────────────────────
# Each quest has a "level" 1-5. Higher level = longer, harder, better rewards.
# Players unlock higher levels by completing lower-level quests.
# level_req: how many total quests completed before this unlocks (0 = always available).
SIDE_QUESTS = [
    # Level 1 — always available
    {"id": "salvage_run",    "level": 1, "name": "Salvage Run",
     "desc": "Collect wreckage from a nearby battle site.",
     "reward_credits": 300,  "reward_metal": 80,  "reward_fuel": 0,   "duration_min": 2,   "level_req": 0},
    {"id": "recon_mission",  "level": 1, "name": "Recon Mission",
     "desc": "Scout an uncharted sector and report back.",
     "reward_credits": 400,  "reward_metal": 30,  "reward_fuel": 20,  "duration_min": 2,   "level_req": 0},
    # Level 2 — unlock after 2 quests done
    {"id": "escort_convoy",  "level": 2, "name": "Escort Convoy",
     "desc": "Protect a freighter through pirate space.",
     "reward_credits": 700,  "reward_metal": 0,   "reward_fuel": 30,  "duration_min": 4,   "level_req": 2},
    {"id": "prisoner_xfer",  "level": 2, "name": "Prisoner Transfer",
     "desc": "Deliver a high-value prisoner to a contact.",
     "reward_credits": 800,  "reward_metal": 0,   "reward_fuel": 0,   "duration_min": 4,   "level_req": 2},
    # Level 3 — unlock after 5 quests done
    {"id": "supply_raid",    "level": 3, "name": "Supply Raid",
     "desc": "Raid a corporate supply depot for metal and credits.",
     "reward_credits": 900,  "reward_metal": 200, "reward_fuel": 40,  "duration_min": 6,   "level_req": 5},
    {"id": "bounty_hunt",    "level": 3, "name": "Bounty Hunt",
     "desc": "Track down and eliminate a wanted pirate captain.",
     "reward_credits": 1100, "reward_metal": 0,   "reward_fuel": 0,   "duration_min": 7,   "level_req": 5},
    # Level 4 — unlock after 10 quests done
    {"id": "deep_strike",    "level": 4, "name": "Deep Strike",
     "desc": "Assault a military outpost in hostile territory.",
     "reward_credits": 1800, "reward_metal": 250, "reward_fuel": 60,  "duration_min": 10,  "level_req": 10},
    {"id": "artifact_heist", "level": 4, "name": "Artifact Heist",
     "desc": "Steal a void-crystal cache from Technocracy vaults.",
     "reward_credits": 1500, "reward_metal": 100, "reward_fuel": 0,   "duration_min": 9,   "level_req": 10},
    # Level 5 — unlock after 18 quests done (rare, big payout)
    {"id": "void_expedition","level": 5, "name": "Void Expedition",
     "desc": "Venture deep into void space and return with ancient tech.",
     "reward_credits": 3500, "reward_metal": 500, "reward_fuel": 120, "duration_min": 20,  "level_req": 18},
    {"id": "faction_war",    "level": 5, "name": "Faction War Contract",
     "desc": "Lead a strike team in a decisive faction battle.",
     "reward_credits": 4000, "reward_metal": 300, "reward_fuel": 80,  "duration_min": 18,  "level_req": 18},
]


class HomeBase:
    # Resource keys
    RESOURCE_KEYS = ["credits", "metal", "fuel", "supplies",
                     "void_crystals", "contraband"]

    # Base nav tabs
    TAB_BUILDINGS = "buildings"
    TAB_CREW      = "crew"
    TAB_ARMORY    = "armory"
    TAB_CREW_MGMT = "crew_mgmt"
    TAB_REPAIR    = "repair"
    TAB_RESEARCH  = "research"
    TAB_TRADING   = "trading"
    TAB_BAY       = "bay"

    # Tab display order and labels
    TAB_ROSTER  = "crew_roster"   # new: full crew roster screen

    ALL_TABS = [
        ("buildings",   "Buildings"),
        ("crew",        "Crew & Quests"),
        ("armory",      "Armory/Shop"),
        ("crew_mgmt",   "Crew Mgmt"),
        ("crew_roster", "Crew Roster"),
        ("repair",      "Repair"),
        ("research",    "Research"),
        ("trading",     "Trading"),
        ("bay",         "Bay Control"),
    ]

    # Building sub-categories
    BCAT_ALL      = "all"
    BCAT_COMBAT   = "combat"
    BCAT_ECONOMY  = "economy"
    BCAT_RESEARCH = "research"
    BCAT_FLEET    = "fleet"

    BUILDING_CATS = {
        "armory":          "combat",
        "defense_turrets": "combat",
        "warehouse":       "economy",
        "trading_post":    "economy",
        "cantina":         "economy",
        "research_lab":    "research",
        "shipyard":        "fleet",
        "barracks":        "fleet",
        "black_market":    "economy",
        "fuel_depot":      "economy",
        "comm_tower":      "fleet",
    }

    def __init__(self, wanted_level_ref=None):
        self.buildings: dict[str, Building] = make_buildings()
        self.resources: dict[str, int] = {
            "credits":       500,
            "metal":         100,
            "fuel":          80,
            "supplies":      50,
            "void_crystals": 0,
            "contraband":    0,
        }
        self.base_hp     = 500
        self.max_base_hp = 500
        self.expansion_level = 0   # 0=asteroid 1=small_station 2=full_station

        # Asteroid expansion system
        self.asteroid_count      = 1
        self.max_crew_per_asteroid = 50

        self.raiders = RaiderManager(wanted_level_ref)

        pygame.font.init()
        self._font     = pygame.font.SysFont("monospace", 14)
        self._font_sm  = pygame.font.SysFont("monospace", 11)
        self._font_big = pygame.font.SysFont("monospace", 20)

        self._selected_building: str | None = None
        self._anim_time: float = 0.0   # drives patrol ship orbits + pulse effects
        # Deterministic asteroid shape seed (fixed per base instance)
        self._asteroid_rng = random.Random(1337)

        # Active tab
        self._active_tab = self.TAB_BUILDINGS

        # Crew Roster tab state
        self._roster_selected: int = 0          # index into combined crew list
        self._roster_station_rects: dict = {}   # {station_id: Rect}
        self._roster_gear_rects: dict    = {}   # {(crew_idx, slot): Rect}
        self._roster_unequip_rects: dict = {}   # {(crew_idx, slot): Rect}

        # Crew tab state
        self._hired_crew: list[dict] = []       # crew hired from cantina
        self._active_quests: list[dict] = []    # ongoing side quests
        self._ships_on_mission: list[str] = []  # ship names on side quests
        self._quests_completed: int = 0         # total quests completed (unlocks higher levels)
        self._crew_scroll = 0
        self._quest_scroll = 0
        self._merc_scroll  = 0

        # Ship-selection popup for side quests
        self._quest_ship_select_popup: dict | None = None  # {quest_id, ship_list, selected_idx}
        self._quest_popup_btns: list[tuple] = []           # [(label, action, rect)]

        # Player-owned cargo ships (trade routes)
        self._player_cargo_ships: list[dict] = []
        # Each: {id, name, route_from, route_to, t(0-1), speed, dir, credits_per_trip, active}
        self._cargo_ship_popup: bool = False  # UI popup to create cargo ship

        # Shipyard build queue: list of {ship_type, cost, time_left, name}
        self._shipyard_queue: list[dict] = []

        # Building sub-tab (category filter)
        self._building_cat: str = self.BCAT_ALL

        # Notification queue for base-level messages
        self._notifications: list[list] = []    # [(msg, color, ttl)]

        # Armory / shop state
        self._armory_filter: str = "all"   # "all" / "weapon" / "module" / "drone" / "ship"
        self._armory_buy_rects: dict[int, pygame.Rect] = {}
        self._gear_inventory: list[str] = []   # crew gear items purchased, not yet equipped

        # Crew management state
        self._crew_selected: int | None = None    # index into _hired_crew
        self._crew_fire_rects: dict[int, pygame.Rect] = {}
        self._crew_train_rects: dict[int, pygame.Rect] = {}
        self._crew_buy_rects:  dict[int, pygame.Rect] = {}   # regular crew hire buttons

        # Repair shop state
        self._repair_ship_idx: int | None = None

        # Research state
        self.research_points: int = 0               # accumulated research resource
        self.research_unlocked: set[str] = set()    # set of unlocked node IDs
        self._research_invest_rects: dict[str, pygame.Rect] = {}
        self._research_invest_amounts: dict[str, int] = {}  # node_id → accumulated investment

        # Trading state
        self._trade_nation_idx: int = 0             # selected nation index
        self._trade_nation_relations: dict[str, int] = {
            n["id"]: n["base_relation"] for n in TRADE_NATIONS
        }
        self._trade_buy_rects:  dict[str, pygame.Rect] = {}
        self._trade_sell_rects: dict[str, pygame.Rect] = {}
        self._trade_sell_amounts: dict[str, int] = {}   # resource_key → qty to sell (10 default)
        self._trade_gift_rects: dict[str, pygame.Rect] = {}  # gift credits/supplies to build relation

    # ── Asteroid capacity ─────────────────────────────────────────────────────
    @property
    def total_crew_cap(self) -> int:
        return self.asteroid_count * self.max_crew_per_asteroid

    def buy_asteroid(self) -> dict:
        """Buy an additional asteroid: costs 2000 credits + 500 metal."""
        cost = {"credits": 2000, "metal": 500}
        if not self.can_afford(cost):
            return {"ok": False, "reason": f"Need 2000cr + 500metal"}
        self.spend_all(cost)
        self.asteroid_count += 1
        # Increase max HP slightly with new asteroid
        self.max_base_hp += 100
        self.base_hp = min(self.base_hp + 100, self.max_base_hp)
        return {"ok": True, "asteroid_count": self.asteroid_count}

    # ── Resources ─────────────────────────────────────────────────────────────
    def get_resource(self, key: str) -> int:
        return self.resources.get(key, 0)

    def add_resource(self, key: str, amount: int) -> None:
        cap = self._resource_cap(key)
        self.resources[key] = min(cap, self.resources.get(key, 0) + amount)

    def spend_resource(self, key: str, amount: int) -> bool:
        if self.resources.get(key, 0) >= amount:
            self.resources[key] -= amount
            return True
        return False

    def can_afford(self, cost: dict) -> bool:
        return all(self.resources.get(k, 0) >= v for k, v in cost.items())

    def spend_all(self, cost: dict) -> bool:
        if not self.can_afford(cost):
            return False
        for k, v in cost.items():
            self.resources[k] -= v
        return True

    def _resource_cap(self, key: str) -> int:
        wh = self.buildings.get("warehouse")
        base_caps = {
            "credits":       999999,
            "metal":         1000,
            "fuel":          200,
            "supplies":      200,
            "void_crystals": 50,
            "contraband":    20,
        }
        cap = base_caps.get(key, 500)
        if wh and wh.level >= 1: cap = int(cap * (2 ** wh.level))
        return cap

    # ── Building management ───────────────────────────────────────────────────
    def build(self, building_id: str) -> dict:
        b = self.buildings.get(building_id)
        if not b:
            return {"ok": False, "reason": "Unknown building"}
        if b.is_built():
            return {"ok": False, "reason": "Already built — use upgrade"}
        cost = b.upgrade_cost()
        if not self.can_afford(cost):
            return {"ok": False, "reason": f"Need: {cost}"}
        self.spend_all(cost)
        b.upgrade()
        self._check_expansion()
        return {"ok": True, "building": b.name}

    def upgrade_building(self, building_id: str) -> dict:
        b = self.buildings.get(building_id)
        if not b:
            return {"ok": False, "reason": "Unknown building"}
        if not b.is_built():
            return {"ok": False, "reason": "Build it first"}
        if not b.can_upgrade():
            return {"ok": False, "reason": "Already max level"}
        cost = b.upgrade_cost()
        if not self.can_afford(cost):
            return {"ok": False, "reason": f"Need: {cost}"}
        self.spend_all(cost)
        b.upgrade()
        self._check_expansion()
        return {"ok": True, "building": b.name, "level": b.level}

    def _check_expansion(self) -> None:
        built = sum(1 for b in self.buildings.values() if b.is_built())
        if built >= 4 and self.expansion_level < 1:
            self.expansion_level = 1
            self.max_base_hp += 300
            self.base_hp     += 300
        if built >= 7 and self.expansion_level < 2:
            self.expansion_level = 2
            self.max_base_hp += 500
            self.base_hp     += 500

    def _cantina_built(self) -> bool:
        c = self.buildings.get("cantina")
        return c is not None and c.is_built()

    # ── Crew hiring ───────────────────────────────────────────────────────────
    def hire_mercenary(self, merc_index: int, fleet=None) -> dict:
        if not self._cantina_built():
            return {"ok": False, "reason": "Build the Cantina first"}
        if merc_index < 0 or merc_index >= len(MERCENARY_ROSTER):
            return {"ok": False, "reason": "Invalid mercenary"}
        merc = MERCENARY_ROSTER[merc_index]
        # Check cantina level allows this rarity
        cantina = self.buildings.get("cantina")
        lvl = cantina.level if cantina else 1
        rarity_unlock = {1: {"common"}, 2: {"common", "uncommon"}, 3: {"common", "uncommon", "rare"}}
        allowed = rarity_unlock.get(lvl, {"common"})
        if merc["rarity"] not in allowed:
            return {"ok": False, "reason": f"Upgrade Cantina to hire {merc['rarity']} crew"}
        cost = {"credits": merc["cost"]}
        if not self.can_afford(cost):
            return {"ok": False, "reason": f"Need {merc['cost']} credits"}
        self.spend_all(cost)
        self._hired_crew.append(dict(merc))
        return {"ok": True, "name": merc["name"]}

    def hire_crew(self, crew_index: int) -> dict:
        """Hire a regular (non-mercenary) crew member from REGULAR_CREW_ROSTER."""
        if not self._cantina_built():
            return {"ok": False, "reason": "Build the Cantina first"}
        if crew_index < 0 or crew_index >= len(REGULAR_CREW_ROSTER):
            return {"ok": False, "reason": "Invalid crew index"}
        member = REGULAR_CREW_ROSTER[crew_index]
        cost = {"credits": member["cost"]}
        if not self.can_afford(cost):
            return {"ok": False, "reason": f"Need {member['cost']} credits"}
        self.spend_all(cost)
        self._hired_crew.append(dict(member))
        return {"ok": True, "name": member["name"]}

    @property
    def quest_level(self) -> int:
        """Current side-quest level unlocked (1-5), based on quests completed."""
        if self._quests_completed >= 18: return 5
        if self._quests_completed >= 10: return 4
        if self._quests_completed >= 5:  return 3
        if self._quests_completed >= 2:  return 2
        return 1

    def start_side_quest(self, quest_id: str, ship_name: str = "") -> dict:
        if not self._cantina_built():
            return {"ok": False, "reason": "Build the Cantina first"}
        quest_def = next((q for q in SIDE_QUESTS if q["id"] == quest_id), None)
        if not quest_def:
            return {"ok": False, "reason": "Unknown quest"}
        # Don't start same quest twice
        if any(aq["id"] == quest_id for aq in self._active_quests):
            return {"ok": False, "reason": "Quest already active"}
        # Check quest level requirement
        if quest_def.get("level_req", 0) > self._quests_completed:
            needed = quest_def["level_req"]
            return {"ok": False, "reason": f"Need {needed} quests completed (have {self._quests_completed})"}
        # Require a ship to be assigned
        if not ship_name:
            return {"ok": False, "reason": "No ship assigned"}
        mission = dict(quest_def)
        mission["time_left"] = quest_def["duration_min"] * 60.0  # convert to seconds
        mission["ship"]      = ship_name
        self._active_quests.append(mission)
        self._ships_on_mission.append(ship_name)
        return {"ok": True, "quest": quest_def["name"]}

    def open_quest_ship_popup(self, quest_id: str, fleet) -> None:
        """Open the ship-selection popup for a given quest."""
        # Build list of available ships (not already on a mission)
        ships = []
        if fleet:
            for s in list(fleet.ships) + list(getattr(fleet, "captured_ships", [])):
                available = s.custom_name not in self._ships_on_mission
                ships.append({"name": s.custom_name, "class": s.ship_class,
                               "available": available, "ship": s})
        self._quest_ship_select_popup = {
            "quest_id":    quest_id,
            "ships":       ships,
            "selected":    0,
        }

    # ── Armory / shop logic ───────────────────────────────────────────────────
    def buy_gear(self, item_idx: int, fleet=None) -> dict:
        """Buy a gear item from the armory catalogue (including crew gear)."""
        if self._armory_filter == "crew_gear":
            items = list(CREW_GEAR_ITEMS)
        elif self._armory_filter == "all":
            items = list(GEAR_CATALOGUE) + list(CREW_GEAR_ITEMS)
        else:
            items = [i for i in GEAR_CATALOGUE if i["type"] == self._armory_filter]
        if item_idx < 0 or item_idx >= len(items):
            return {"ok": False, "reason": "Invalid item"}
        item = items[item_idx]
        cost = {"credits": item["cost"]}
        if not self.can_afford(cost):
            return {"ok": False, "reason": f"Need {item['cost']} credits"}
        self.spend_all(cost)
        # Apply item effect immediately (simplified — items go to resource pool or fleet)
        # Detect crew gear by "slot" key (head/body/tool) when "type" not explicitly set
        itype = item.get("type", "crew_gear" if "slot" in item else "")
        if itype == "module":
            if "shield" in item["id"]:
                if fleet and fleet.active_ship:
                    fleet.active_ship.max_shield += 40
                    fleet.active_ship.shield = min(fleet.active_ship.shield + 40,
                                                   fleet.active_ship.max_shield)
            elif "hull" in item["id"]:
                if fleet and fleet.active_ship:
                    fleet.active_ship.max_hull += 60
                    fleet.active_ship.hull = min(fleet.active_ship.hull + 60,
                                                 fleet.active_ship.max_hull)
            elif "engine" in item["id"]:
                if fleet and fleet.active_ship:
                    fleet.active_ship.speed = int(fleet.active_ship.speed * 1.15)
        elif itype == "crew_gear":
            # Add to gear inventory — crew can equip from the roster screen
            self._gear_inventory.append(item["id"])
        # Track purchase in inventory
        self._push_note(f"Purchased: {item['name']}", SUCCESS)
        # Fire purchase SFX event
        try:
            from core.events import bus as _ebus
            _ebus.publish("purchase_made")
        except Exception:
            pass
        return {"ok": True, "item": item["name"], "type": itype}

    # ── Research logic ────────────────────────────────────────────────────────
    def invest_research(self, node_id: str, amount: int = 50) -> dict:
        """Invest research points into a node. Unlocks when threshold reached."""
        node = next((n for n in RESEARCH_NODES if n[0] == node_id), None)
        if not node:
            return {"ok": False, "reason": "Unknown node"}
        if node_id in self.research_unlocked:
            return {"ok": False, "reason": "Already researched"}
        # Check prerequisites
        for req in node[4]:
            if req not in self.research_unlocked:
                return {"ok": False, "reason": f"Requires: {req}"}
        # Check research points
        if self.research_points < amount:
            return {"ok": False, "reason": f"Need {amount} research points"}
        self.research_points -= amount
        # Accumulate toward threshold
        self._research_invest_amounts[node_id] = \
            self._research_invest_amounts.get(node_id, 0) + amount
        cost = node[3]
        if self._research_invest_amounts[node_id] >= cost:
            self.research_unlocked.add(node_id)
            self._push_note(f"Research complete: {node[1]}!", (160, 80, 255))
            return {"ok": True, "completed": True, "name": node[1]}
        progress = self._research_invest_amounts[node_id]
        self._push_note(f"Research: {node[1]} {progress}/{cost}", (140, 100, 220))
        return {"ok": True, "completed": False, "progress": progress, "cost": cost}

    def add_research_points(self, amount: int) -> None:
        self.research_points += amount

    # ── Trading logic ─────────────────────────────────────────────────────────
    def trade_buy(self, nation_id: str, item_id: str) -> dict:
        nation = next((n for n in TRADE_NATIONS if n["id"] == nation_id), None)
        if not nation:
            return {"ok": False, "reason": "Unknown nation"}
        rel = self._trade_nation_relations.get(nation_id, 0)
        if rel < -20:
            return {"ok": False, "reason": "Relation too low to trade"}
        item = next((s for s in nation["sells"] if s["id"] == item_id), None)
        if not item:
            return {"ok": False, "reason": "Item not sold by this nation"}
        res_key  = item.get("cost_resource", "credits")
        price    = item.get("price", 999)
        # Relation discount: 10% off at rel 20+, 20% at rel 50+
        if rel >= 50:
            price = int(price * 0.8)
        elif rel >= 20:
            price = int(price * 0.9)
        if self.resources.get(res_key, 0) < price:
            return {"ok": False, "reason": f"Need {price} {res_key}"}
        self.resources[res_key] = self.resources.get(res_key, 0) - price
        # Apply effect
        desc = item.get("desc", "")
        if "fuel" in desc.lower():
            amt = int("".join(c for c in desc if c.isdigit()) or "50")
            self.add_resource("fuel", amt)
        elif "metal" in desc.lower():
            amt = int("".join(c for c in desc if c.isdigit()) or "60")
            self.add_resource("metal", amt)
        elif "supply" in desc.lower() or "supplies" in desc.lower():
            amt = int("".join(c for c in desc if c.isdigit()) or "40")
            self.add_resource("supplies", amt)
        elif "void crystal" in desc.lower():
            self.add_resource("void_crystals", 10)
        elif "research" in desc.lower():
            self.add_research_points(100)
        # Build relation slightly
        self._trade_nation_relations[nation_id] = min(100, rel + 2)
        self._push_note(f"Bought {item['name']} from {nation['name']}", SUCCESS)
        return {"ok": True, "item": item["name"]}

    def trade_sell(self, nation_id: str, resource_key: str, amount: int) -> dict:
        nation = next((n for n in TRADE_NATIONS if n["id"] == nation_id), None)
        if not nation:
            return {"ok": False, "reason": "Unknown nation"}
        rel = self._trade_nation_relations.get(nation_id, 0)
        if rel < -20:
            return {"ok": False, "reason": "Relation too low to trade"}
        buy_entry = next((b for b in nation["buys"] if b["resource_key"] == resource_key), None)
        if not buy_entry:
            return {"ok": False, "reason": "This nation doesn't buy that"}
        have = self.resources.get(resource_key, 0)
        if have < amount:
            amount = have
        if amount <= 0:
            return {"ok": False, "reason": f"No {resource_key} to sell"}
        price_per = buy_entry.get("price_per", 0)
        # Relation bonus: +10% sell price at rel 20+
        if rel >= 20:
            price_per = price_per * 1.1
        earned = int(amount * price_per)
        self.resources[resource_key] = have - amount
        self.add_resource("credits", earned)
        self._trade_nation_relations[nation_id] = min(100, rel + 1)
        self._push_note(f"Sold {amount} {resource_key} for {earned}cr", (60, 220, 160))
        return {"ok": True, "earned": earned}

    def trade_gift(self, nation_id: str, gift_credits: int = 500) -> dict:
        """Send a gift of credits to build relations with a nation."""
        if not self.can_afford({"credits": gift_credits}):
            return {"ok": False, "reason": f"Need {gift_credits} credits"}
        self.resources["credits"] -= gift_credits
        rel_gain = max(1, gift_credits // 200)
        self._trade_nation_relations[nation_id] = min(
            100, self._trade_nation_relations.get(nation_id, 0) + rel_gain)
        self._push_note(f"Gift sent! +{rel_gain} relation", (80, 200, 255))
        return {"ok": True, "rel_gained": rel_gain}

    # ── Repair logic ──────────────────────────────────────────────────────────
    def repair_ship(self, ship, amount: int, cost_per_hp: float = 2.0) -> dict:
        """Repair `amount` HP on `ship`. Costs credits proportionally."""
        if not ship:
            return {"ok": False, "reason": "No ship selected"}
        damage = ship.max_hull - ship.hull
        if damage <= 0:
            return {"ok": False, "reason": "Ship is already at full health"}
        repair_amt = min(amount, damage)
        cost = int(repair_amt * cost_per_hp)
        if not self.can_afford({"credits": cost}):
            return {"ok": False, "reason": f"Need {cost} credits"}
        self.resources["credits"] -= cost
        ship.hull = min(ship.max_hull, ship.hull + repair_amt)
        return {"ok": True, "repaired": repair_amt, "cost": cost}

    def full_repair_ship(self, ship, cost_per_hp: float = 2.0) -> dict:
        if not ship:
            return {"ok": False, "reason": "No ship selected"}
        damage = ship.max_hull - ship.hull
        return self.repair_ship(ship, int(damage), cost_per_hp)

    # ── Update ────────────────────────────────────────────────────────────────
    def update(self, dt: float) -> None:
        self._anim_time += dt
        raid_started = self.raiders.update(dt)
        if raid_started:
            from core.events import bus
            secs = int(self.raiders.warning_seconds_left())
            mins = secs // 60
            rem  = secs % 60
            count = len(self.raiders._pending_wave_data or [])
            bus.publish("notification",
                        msg=f"⚠ RAIDERS INCOMING! {count} ship(s) — ETA {mins}:{rem:02d}",
                        color=(220, 60, 60))

        # Tick side quests
        for quest in list(self._active_quests):
            quest["time_left"] -= dt
            if quest["time_left"] <= 0:
                self._complete_quest(quest)
                self._active_quests.remove(quest)

        # Tick player cargo ships
        for cs in self._player_cargo_ships:
            if not cs.get("active", False):
                continue
            cs["t"] += cs["speed"] * cs["dir"] * dt
            if cs["t"] >= 1.0:
                cs["t"] = 1.0
                cs["dir"] = -1
                # Arrived at destination → award credits bonus
                self.add_resource("credits", 1000)
                from core.events import bus as _bus
                _bus.publish("notification",
                             msg=f"🚢 Cargo ship '{cs['name']}' completed a trade run!  +1000cr",
                             color=(180, 220, 140))
                _bus.publish("purchase_made")  # ka-ching
            elif cs["t"] <= 0.0:
                cs["t"] = 0.0
                cs["dir"] = 1
                self.add_resource("credits", 1000)
                from core.events import bus as _bus
                _bus.publish("notification",
                             msg=f"🚢 Cargo ship '{cs['name']}' returned to base!  +1000cr",
                             color=(180, 220, 140))
                _bus.publish("purchase_made")

        # Tick shipyard build queue
        for build in list(self._shipyard_queue):
            build["time_left"] -= dt
            if build["time_left"] <= 0:
                self._shipyard_queue.remove(build)
                from core.events import bus as _bus
                _bus.publish("notification",
                             msg=f"⚒  Shipyard: {build['name']} is ready!",
                             color=(80, 200, 255))

        # Tick notifications
        for n in self._notifications:
            n[2] -= dt
        self._notifications = [n for n in self._notifications if n[2] > 0]

    def _complete_quest(self, quest: dict) -> None:
        cr = quest.get("reward_credits", 0)
        mt = quest.get("reward_metal", 0)
        fu = quest.get("reward_fuel", 0)
        if cr: self.add_resource("credits", cr)
        if mt: self.add_resource("metal",   mt)
        if fu: self.add_resource("fuel",    fu)
        self._quests_completed += 1
        ship_name = quest.get("ship", "")
        if ship_name and ship_name in self._ships_on_mission:
            self._ships_on_mission.remove(ship_name)
        from core.events import bus
        qlvl  = quest.get("level", 1)
        bonus = f"  +{fu}fuel" if fu else ""
        bus.publish("notification",
                    msg=f"✓ [Lv{qlvl}] Quest complete: {quest['name']}  +{cr}cr +{mt}metal{bonus}",
                    color=(60, 200, 80))
        # Check for quest level unlock
        new_lvl = self.quest_level
        bus.publish("notification",
                    msg=f"⭐ Quest Level {new_lvl} unlocked!  New missions available.",
                    color=(255, 200, 60)) if self._quests_completed in (2, 5, 10, 18) else None

    def _push_note(self, msg: str, color=(220, 220, 240), ttl=3.5) -> None:
        self._notifications.append([msg, color, ttl])

    # ── Input ─────────────────────────────────────────────────────────────────
    def handle_event(self, event: pygame.event.Event) -> str | None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos

            # QUIT TO MENU button
            if hasattr(self, "_quit_rect") and self._quit_rect.collidepoint(mx, my):
                return "quit_to_menu"

            # LAUNCH button (top-right)
            if hasattr(self, "_launch_rect") and self._launch_rect.collidepoint(mx, my):
                return "galaxy_map"

            # Tab buttons
            for tab_id, tab_rect in getattr(self, "_tab_rects", {}).items():
                if tab_rect.collidepoint(mx, my):
                    self._active_tab = tab_id
                    return f"tab:{tab_id}"

            # BUY ASTEROID button (right panel, always visible)
            if hasattr(self, "_buy_asteroid_btn") and self._buy_asteroid_btn.collidepoint(mx, my):
                res = self.buy_asteroid()
                if res["ok"]:
                    self._push_note(
                        f"🪨 New asteroid acquired! Crew Cap: {self.total_crew_cap}",
                        (100, 220, 100))
                else:
                    self._push_note(f"Cannot buy: {res['reason']}", (220, 60, 60))
                return "buy_asteroid"

            # Nav bar buttons
            for action, rect in getattr(self, "_nav_rects", {}).items():
                if rect.collidepoint(mx, my):
                    return action

            # ── Buildings tab ───────────────────────────────────────────────
            if self._active_tab == self.TAB_BUILDINGS:
                for cat_id, cat_rect in getattr(self, "_bcat_tab_rects", {}).items():
                    if cat_rect.collidepoint(mx, my):
                        self._building_cat = cat_id
                        return f"bcat:{cat_id}"
                for bid, rect in getattr(self, "_building_rects", {}).items():
                    if rect.collidepoint(mx, my):
                        if self._selected_building == bid:
                            b = self.buildings.get(bid)
                            if b and not b.is_built():
                                result = self.build(bid)
                                return f"build_result:{result['ok']}:{result.get('reason','')}"
                            elif b and b.can_upgrade():
                                result = self.upgrade_building(bid)
                                return f"upgrade_result:{result['ok']}:{result.get('reason','')}"
                        else:
                            self._selected_building = bid
                        return f"select_{bid}"

            # ── Crew & Quests tab ────────────────────────────────────────────
            elif self._active_tab == self.TAB_CREW:
                # Handle ship-select popup first (it overlays everything)
                if self._quest_ship_select_popup is not None:
                    for action, idx, btn_rect in getattr(self, "_quest_popup_btns", []):
                        if btn_rect.collidepoint(mx, my):
                            if action == "select":
                                self._quest_ship_select_popup["selected"] = idx
                            elif action == "cancel":
                                self._quest_ship_select_popup = None
                            elif action == "confirm":
                                popup = self._quest_ship_select_popup
                                ships = popup.get("ships", [])
                                sel   = popup.get("selected", 0)
                                if ships and 0 <= sel < len(ships) and ships[sel]["available"]:
                                    ship_name = ships[sel]["name"]
                                    qid2 = popup["quest_id"]
                                    res = self.start_side_quest(qid2, ship_name)
                                    msg = (f"Quest started: {res['quest']}  → {ship_name}!"
                                           if res["ok"] else f"Cannot start: {res['reason']}")
                                    self._push_note(msg, SUCCESS if res["ok"] else DANGER)
                                    self._quest_ship_select_popup = None
                                    return f"start_quest:{qid2}"
                                else:
                                    self._push_note("Select an available ship first!", DANGER)
                    return  # absorb all clicks while popup open

                for idx, btn_rect in getattr(self, "_crew_buy_rects", {}).items():
                    if btn_rect.collidepoint(mx, my):
                        res = self.hire_crew(idx)
                        msg = f"Hired {res['name']}!" if res["ok"] else f"Cannot hire: {res['reason']}"
                        self._push_note(msg, SUCCESS if res["ok"] else DANGER)
                        return f"hire_crew:{idx}"
                for idx, btn_rect in getattr(self, "_merc_hire_rects", {}).items():
                    if btn_rect.collidepoint(mx, my):
                        res = self.hire_mercenary(idx)
                        msg = f"Hired {res['name']}!" if res["ok"] else f"Cannot hire: {res['reason']}"
                        self._push_note(msg, SUCCESS if res["ok"] else DANGER)
                        return f"hire_merc:{idx}"
                for qid, btn_rect in getattr(self, "_quest_start_rects", {}).items():
                    if btn_rect.collidepoint(mx, my):
                        # Open ship-selection popup instead of starting immediately
                        fleet_ref = getattr(self, "_last_fleet_ref", None)
                        self.open_quest_ship_popup(qid, fleet_ref)
                        return f"quest_popup:{qid}"

            # ── Armory / Shop tab ───────────────────────────────────────────
            elif self._active_tab == self.TAB_ARMORY:
                # Filter buttons
                for fid, frt in getattr(self, "_armory_filter_rects", {}).items():
                    if frt.collidepoint(mx, my):
                        self._armory_filter = fid
                        return f"armory_filter:{fid}"
                # Buy buttons — pass fleet reference stored in draw context
                fleet_ref = getattr(self, "_last_fleet_ref", None)
                for idx, brect in getattr(self, "_armory_buy_rects", {}).items():
                    if brect.collidepoint(mx, my):
                        res = self.buy_gear(idx, fleet_ref)
                        msg = f"Bought: {res['item']}!" if res["ok"] else f"Cannot buy: {res['reason']}"
                        self._push_note(msg, SUCCESS if res["ok"] else DANGER)
                        return f"buy_gear:{idx}"

            # ── Crew Management tab ─────────────────────────────────────────
            elif self._active_tab == self.TAB_CREW_MGMT:
                for idx, frect in getattr(self, "_crew_fire_rects", {}).items():
                    if frect.collidepoint(mx, my):
                        if 0 <= idx < len(self._hired_crew):
                            fired = self._hired_crew.pop(idx)
                            self._push_note(f"Dismissed {fired['name']}", WARNING)
                        return f"fire_crew:{idx}"
                for idx, trect in getattr(self, "_crew_train_rects", {}).items():
                    if trect.collidepoint(mx, my):
                        cost = 200
                        if self.can_afford({"credits": cost}) and 0 <= idx < len(self._hired_crew):
                            self.resources["credits"] -= cost
                            c = self._hired_crew[idx]
                            # Boost every stat by +1 (all-round training)
                            for stat in ("combat", "piloting", "gunnery",
                                         "engineering", "repair", "morale"):
                                c[stat] = c.get(stat, 5) + 1
                            self._push_note(
                                f"Trained {c['name']}! +1 to all stats", SUCCESS)
                        else:
                            self._push_note("Need 200cr to train", DANGER)
                        return f"train_crew:{idx}"
                # Select crew row
                for idx, srect in getattr(self, "_crew_select_rects", {}).items():
                    if srect.collidepoint(mx, my):
                        self._crew_selected = idx if self._crew_selected != idx else None
                        return f"select_crew:{idx}"

            # ── Crew Roster tab ─────────────────────────────────────────────
            elif self._active_tab == self.TAB_ROSTER:
                # Select a crew member from the list
                for idx, lrect in getattr(self, "_roster_list_rects", {}).items():
                    if lrect.collidepoint(mx, my):
                        self._roster_selected = idx
                        return f"roster_select:{idx}"
                # Assign station button
                for (cidx, station), arect in getattr(self, "_roster_station_rects", {}).items():
                    if arect.collidepoint(mx, my):
                        self._roster_assign_station(cidx, station, fleet)
                        return f"roster_station:{station}"
                # Unequip gear button
                for (cidx, slot), urect in getattr(self, "_roster_unequip_rects", {}).items():
                    if urect.collidepoint(mx, my):
                        self._roster_unequip_gear(cidx, slot, fleet)
                        return f"roster_unequip:{slot}"
                # Equip gear from inventory
                for gear_id, erect in getattr(self, "_roster_equip_btns", {}).items():
                    if erect.collidepoint(mx, my):
                        self._roster_equip_gear(self._roster_selected, gear_id, fleet)
                        return f"roster_equip:{gear_id}"

            # ── Repair tab ──────────────────────────────────────────────────
            elif self._active_tab == self.TAB_REPAIR:
                fleet_ref = getattr(self, "_last_fleet_ref", None)
                for sid, rrect in getattr(self, "_repair_25_rects", {}).items():
                    if rrect.collidepoint(mx, my) and fleet_ref:
                        ship = next((s for s in (fleet_ref.ships or [])
                                     if s.id == sid), None)
                        if ship:
                            hull_25 = int(ship.max_hull * 0.25)
                            res = self.repair_ship(ship, hull_25)
                            msg = f"Repaired {res.get('repaired',0):.0f} HP for {res.get('cost',0)}cr" \
                                  if res["ok"] else res["reason"]
                            self._push_note(msg, SUCCESS if res["ok"] else DANGER)
                        return f"repair_25:{sid}"
                for sid, frect in getattr(self, "_repair_full_rects", {}).items():
                    if frect.collidepoint(mx, my) and fleet_ref:
                        ship = next((s for s in (fleet_ref.ships or [])
                                     if s.id == sid), None)
                        if ship:
                            res = self.full_repair_ship(ship)
                            msg = f"Full repair: {res.get('repaired',0):.0f} HP for {res.get('cost',0)}cr" \
                                  if res["ok"] else res["reason"]
                            self._push_note(msg, SUCCESS if res["ok"] else DANGER)
                        return f"repair_full:{sid}"
                for sid, hrect in getattr(self, "_repair_hull_rects", {}).items():
                    if hrect.collidepoint(mx, my) and fleet_ref:
                        ship = next((s for s in (fleet_ref.ships or [])
                                     if s.id == sid), None)
                        if ship:
                            cost = 300
                            if self.can_afford({"credits": cost}):
                                self.resources["credits"] -= cost
                                ship.max_hull = int(ship.max_hull * 1.1)
                                self._push_note(f"Hull upgraded! +10% max hull ({cost}cr)", SUCCESS)
                            else:
                                self._push_note("Need 300cr for hull upgrade", DANGER)
                        return f"upgrade_hull:{sid}"

            # ── Research tab ────────────────────────────────────────────────
            elif self._active_tab == self.TAB_RESEARCH:
                for nid, irct in getattr(self, "_research_invest_rects", {}).items():
                    if irct.collidepoint(mx, my):
                        invest_amt = 50
                        # If no research points, convert 100cr → 10 rp
                        if self.research_points < invest_amt:
                            if self.can_afford({"credits": 100}):
                                self.resources["credits"] -= 100
                                self.research_points += 10
                                self._push_note("Converted 100cr → 10 research pts", (160, 80, 255))
                            else:
                                self._push_note("Need 100cr or research points!", DANGER)
                        res = self.invest_research(nid, min(invest_amt, self.research_points))
                        if res.get("ok"):
                            pass  # push_note called inside invest_research
                        else:
                            self._push_note(f"Research blocked: {res['reason']}", DANGER)
                        return f"research:{nid}"

            # ── Trading tab ─────────────────────────────────────────────────
            elif self._active_tab == self.TAB_TRADING:
                # Gift nation picker buttons (inline row above gift amounts)
                for nid, grect in getattr(self, "_gift_nation_btns", []):
                    if grect.collidepoint(mx, my):
                        self._gift_target_nation_id = nid
                        return f"gift_target:{nid}"
                # Nation selector tabs
                for ni, nrect in getattr(self, "_trade_nation_rects", {}).items():
                    if nrect.collidepoint(mx, my):
                        self._trade_nation_idx = ni
                        return f"trade_nation:{ni}"
                # Buy from nation
                nation = TRADE_NATIONS[self._trade_nation_idx] if self._trade_nation_idx < len(TRADE_NATIONS) else None
                if nation:
                    for item_id, brect in getattr(self, "_trade_buy_rects", {}).items():
                        if brect.collidepoint(mx, my):
                            res = self.trade_buy(nation["id"], item_id)
                            msg = f"Bought from {nation['name']}!" if res["ok"] else res["reason"]
                            self._push_note(msg, SUCCESS if res["ok"] else DANGER)
                            return f"trade_buy:{item_id}"
                    # Sell to nation
                    for res_key, srect in getattr(self, "_trade_sell_rects", {}).items():
                        if srect.collidepoint(mx, my):
                            amount = self._trade_sell_amounts.get(res_key, 10)
                            res = self.trade_sell(nation["id"], res_key, amount)
                            msg = f"Sold {amount} {res_key} for {res.get('earned',0)}cr" \
                                  if res["ok"] else res["reason"]
                            self._push_note(msg, SUCCESS if res["ok"] else DANGER)
                            return f"trade_sell:{res_key}"
                    # Gift button — key is (nation_id, gift_amt)
                    for (nid, gamt), grect in getattr(self, "_trade_gift_rects", {}).items():
                        if grect.collidepoint(mx, my):
                            res = self.trade_gift(nid, gamt)
                            msg = f"+{res.get('rel_gained',0)} relation!" if res["ok"] else res["reason"]
                            self._push_note(msg, (80, 200, 255) if res["ok"] else DANGER)
                            return f"trade_gift:{nid}"

            # ── Bay Control tab ───────────────────────────────────────────────
            elif self._active_tab == self.TAB_BAY:
                # Load button: (_bay_load_btns is list of (ship, rect))
                for ship_ref, brect in getattr(self, "_bay_load_btns", []):
                    if brect.collidepoint(mx, my):
                        carrier = self._get_player_carrier(fleet)
                        if carrier and carrier.bay:
                            res = carrier.bay.load(ship_ref)
                            msg = (f"{ship_ref.custom_name} loaded into bay"
                                   if res["ok"] else res["reason"])
                            self._push_note(msg, SUCCESS if res["ok"] else DANGER)
                            return f"bay_load:{ship_ref.id}"
                # Unload button: (_bay_unload_btns list of (ship, rect))
                for ship_ref, brect in getattr(self, "_bay_unload_btns", []):
                    if brect.collidepoint(mx, my):
                        carrier = self._get_player_carrier(fleet)
                        if carrier and carrier.bay:
                            res = carrier.bay.unload(ship_ref)
                            msg = (f"{ship_ref.custom_name} unloaded from bay"
                                   if res["ok"] else res["reason"])
                            self._push_note(msg, SUCCESS if res["ok"] else DANGER)
                            return f"bay_unload:{ship_ref.id}"
                # Repair All button
                if getattr(self, "_bay_repair_btn", None) and \
                        self._bay_repair_btn.collidepoint(mx, my):
                    carrier = self._get_player_carrier(fleet)
                    if carrier and carrier.bay:
                        metal = self.resources.get("metal", 0)
                        res = carrier.bay.repair_all(metal)
                        if res["metal_spent"] > 0:
                            self.resources["metal"] = metal - res["metal_spent"]
                            self._push_note(
                                f"Bay repaired +{res['repaired_hp']} HP  "
                                f"(-{res['metal_spent']} metal)", SUCCESS)
                        else:
                            self._push_note("No repairs needed or no metal.", WARNING)
                    return "bay_repair_all"

        return None

    # ── Draw ──────────────────────────────────────────────────────────────────
    def draw(self, surface: pygame.Surface, fleet=None) -> None:
        """Main base screen draw.  fleet is optional Fleet reference for patrol ships."""
        surface.fill(DARK_BG)
        self._building_rects: dict[str, pygame.Rect] = {}

        sw, sh = surface.get_size()
        PANEL_W = 540
        ASTRO_X = PANEL_W

        # ── Top bar (full width) ─────────────────────────────────────────────
        title = self._font_big.render(
            f"HOME BASE  [Expansion Lv{self.expansion_level}]", True, TEXT_MAIN)
        surface.blit(title, (20, 10))

        # LAUNCH button (top-right)
        launch_rect = pygame.Rect(sw - 226, 6, 216, 40)
        pygame.draw.rect(surface, (20, 80, 40), launch_rect)
        pygame.draw.rect(surface, SUCCESS, launch_rect, 2)
        lt = self._font_big.render("▶  LAUNCH", True, SUCCESS)
        surface.blit(lt, (launch_rect.centerx - lt.get_width() // 2,
                          launch_rect.centery - lt.get_height() // 2))
        self._launch_rect = launch_rect

        # QUIT TO MENU button
        quit_rect = pygame.Rect(sw - 226 - 160 - 8, 6, 158, 40)
        pygame.draw.rect(surface, (40, 15, 15), quit_rect)
        pygame.draw.rect(surface, DANGER, quit_rect, 1)
        qt = self._font.render("← Menu", True, DANGER)
        surface.blit(qt, (quit_rect.centerx - qt.get_width() // 2,
                          quit_rect.centery - qt.get_height() // 2))
        self._quit_rect = quit_rect

        # Resource bar (two rows)
        RES_LABELS = {"credits": "Cr", "metal": "Metal", "fuel": "Fuel",
                      "supplies": "Sup", "void_crystals": "Void", "contraband": "Ctb"}
        res_items = [(RES_LABELS.get(k, k), v) for k, v in self.resources.items()]
        bar_y, bar_x = 54, 20
        for row_items in [res_items[:3], res_items[3:]]:
            x = bar_x
            for label, val in row_items:
                txt = self._font_sm.render(f"{label}: {val}", True, TEXT_MUTED)
                surface.blit(txt, (x, bar_y))
                x += txt.get_width() + 22
            bar_y += 16
        hp_pct = self.base_hp / max(self.max_base_hp, 1)
        pygame.draw.rect(surface, (60, 0, 0), (500, 57, 180, 8))
        pygame.draw.rect(surface, SUCCESS, (500, 57, int(180 * hp_pct), 8))
        hp_lbl = self._font_sm.render(f"Base HP {self.base_hp}/{self.max_base_hp}",
                                      True, TEXT_MUTED)
        surface.blit(hp_lbl, (500, 46))

        # ── Raider warning countdown (top-right corner) ──────────────────────
        warn_secs = self.raiders.warning_seconds_left()
        if warn_secs > 0:
            mins = int(warn_secs) // 60
            secs = int(warn_secs) % 60
            pulse = abs(math.sin(self._anim_time * 3))
            rc    = int(180 + 75 * pulse)
            warn_font = pygame.font.SysFont("monospace", 18, bold=True)
            warn_surf = warn_font.render(
                f"⚠ RAIDERS  {mins}:{secs:02d}", True, (rc, 30, 30))
            wx = sw - warn_surf.get_width() - 14
            wy = 50
            # dark backing rect
            backing = pygame.Rect(wx - 6, wy - 4,
                                  warn_surf.get_width() + 12,
                                  warn_surf.get_height() + 8)
            pygame.draw.rect(surface, (20, 5, 5), backing, border_radius=4)
            pygame.draw.rect(surface, (rc, 30, 30), backing, 1, border_radius=4)
            surface.blit(warn_surf, (wx, wy))
        elif self.raiders.active_wave and self.raiders.active_wave.active:
            # Active raid — show DEFEND NOW banner
            warn_font = pygame.font.SysFont("monospace", 18, bold=True)
            pulse = abs(math.sin(self._anim_time * 6))
            rc    = int(200 + 55 * pulse)
            defend_surf = warn_font.render("⚠ DEFEND BASE!", True, (rc, 40, 40))
            wx = sw - defend_surf.get_width() - 14
            wy = 50
            backing = pygame.Rect(wx - 6, wy - 4,
                                  defend_surf.get_width() + 12,
                                  defend_surf.get_height() + 8)
            pygame.draw.rect(surface, (40, 5, 5), backing, border_radius=4)
            pygame.draw.rect(surface, (rc, 40, 40), backing, 1, border_radius=4)
            surface.blit(defend_surf, (wx, wy))

        # Separator
        pygame.draw.line(surface, BORDER, (0, 88), (sw, 88))

        # Store fleet reference for use in click handlers
        self._last_fleet_ref = fleet

        # ── Tab bar — two rows of tabs to fit all 7 ──────────────────────────
        self._tab_rects: dict[str, pygame.Rect] = {}
        tab_font = pygame.font.SysFont("monospace", 10)
        tab_h = 22
        tab_y = 90
        ROW1 = self.ALL_TABS[:4]
        ROW2 = self.ALL_TABS[4:]
        for row_idx, row_tabs in enumerate([ROW1, ROW2]):
            tab_w = (PANEL_W - 14) // max(len(row_tabs), 1)
            tab_x = 14
            ry    = tab_y + row_idx * (tab_h + 1)
            for tid, tlabel in row_tabs:
                tr = pygame.Rect(tab_x, ry, tab_w - 2, tab_h)
                is_active = (self._active_tab == tid)
                bg = (30, 50, 90) if is_active else PANEL_BG
                bc = ACCENT if is_active else BORDER
                pygame.draw.rect(surface, bg, tr)
                pygame.draw.rect(surface, bc, tr, 1)
                tt = tab_font.render(tlabel, True, TEXT_MAIN if is_active else TEXT_MUTED)
                surface.blit(tt, (tr.centerx - tt.get_width() // 2,
                                   tr.centery - tt.get_height() // 2))
                self._tab_rects[tid] = tr
                tab_x += tab_w

        tab_bar_bottom = tab_y + 2 * (tab_h + 1)
        pygame.draw.line(surface, BORDER, (0, tab_bar_bottom), (PANEL_W, tab_bar_bottom))

        # ── Left panel content ────────────────────────────────────────────────
        content_y = tab_bar_bottom + 4
        if self._active_tab == self.TAB_BUILDINGS:
            self._draw_buildings_tab(surface, content_y, PANEL_W, sh)
        elif self._active_tab == self.TAB_CREW:
            self._draw_crew_tab(surface, content_y, PANEL_W, sh)
        elif self._active_tab == self.TAB_ARMORY:
            self._draw_armory_tab(surface, content_y, PANEL_W, sh)
        elif self._active_tab == self.TAB_CREW_MGMT:
            self._draw_crew_mgmt_tab(surface, content_y, PANEL_W, sh, fleet=fleet)
        elif self._active_tab == self.TAB_REPAIR:
            self._draw_repair_tab(surface, content_y, PANEL_W, sh, fleet=fleet)
        elif self._active_tab == self.TAB_RESEARCH:
            self._draw_research_tab(surface, content_y, PANEL_W, sh)
        elif self._active_tab == self.TAB_TRADING:
            self._draw_trading_tab(surface, content_y, PANEL_W, sh)
        elif self._active_tab == self.TAB_BAY:
            self._draw_bay_tab(surface, content_y, PANEL_W, sh, fleet=fleet)
        elif self._active_tab == self.TAB_ROSTER:
            self._draw_crew_roster_tab(surface, content_y, PANEL_W, sh, fleet=fleet)

        # ── RIGHT: asteroid base view ─────────────────────────────────────────
        pygame.draw.line(surface, BORDER, (PANEL_W, 88), (PANEL_W, sh - 50))
        self._draw_asteroid_view(surface, ASTRO_X, 88, sw - ASTRO_X, sh - 88 - 50,
                                 fleet=fleet)

        # ── Selected building detail panel ─────────────────────────────────────
        if self._active_tab == self.TAB_BUILDINGS and self._selected_building:
            b = self.buildings.get(self._selected_building)
            if b:
                self._draw_building_detail(surface, b)

        # ── Bottom navigation bar ──────────────────────────────────────────────
        self._draw_nav_bar(surface)

        # ── In-base notifications ─────────────────────────────────────────────
        ny = sh - 50 - 20
        for msg, color, _ in reversed(self._notifications[-4:]):
            nt = self._font_sm.render(msg, True, color)
            surface.blit(nt, (PANEL_W + 10, ny))
            ny -= 16

    # ── Buildings tab ─────────────────────────────────────────────────────────
    def _draw_buildings_tab(self, surface, start_y, panel_w, sh):
        # ── Building category tab strip ───────────────────────────────────────
        BCAT_TABS = [
            (self.BCAT_ALL,      "All",      TEXT_MUTED),
            (self.BCAT_COMBAT,   "Combat",   DANGER),
            (self.BCAT_ECONOMY,  "Economy",  SUCCESS),
            (self.BCAT_RESEARCH, "Research", (160, 80, 220)),
            (self.BCAT_FLEET,    "Fleet",    ACCENT),
        ]
        cat_tab_h  = 22
        cat_tab_w  = (panel_w - 14) // len(BCAT_TABS)
        cat_tab_x  = 14
        self._bcat_tab_rects: dict[str, pygame.Rect] = {}
        for cat_id, cat_lbl, cat_col in BCAT_TABS:
            tr = pygame.Rect(cat_tab_x, start_y, cat_tab_w - 2, cat_tab_h)
            is_sel = (self._building_cat == cat_id)
            pygame.draw.rect(surface, (30, 30, 60) if is_sel else PANEL_BG, tr)
            pygame.draw.rect(surface, cat_col if is_sel else BORDER, tr, 1)
            lt = self._font_sm.render(cat_lbl, True, cat_col if is_sel else TEXT_MUTED)
            surface.blit(lt, (tr.centerx - lt.get_width() // 2,
                               tr.centery - lt.get_height() // 2))
            self._bcat_tab_rects[cat_id] = tr
            cat_tab_x += cat_tab_w

        pygame.draw.line(surface, BORDER, (14, start_y + cat_tab_h),
                         (panel_w - 4, start_y + cat_tab_h))
        start_y += cat_tab_h + 4

        # ── Filter building list by category ─────────────────────────────────
        bw, bh = 160, 110
        pad    = 10
        start_x = 14
        cols_b  = 3
        all_buildings = list(self.buildings.values())
        if self._building_cat == self.BCAT_ALL:
            building_list = all_buildings
        else:
            building_list = [b for b in all_buildings
                             if self.BUILDING_CATS.get(b.building_id) == self._building_cat]

        for i, building in enumerate(building_list):
            col = i % cols_b
            row = i // cols_b
            bx  = start_x + col * (bw + pad)
            by  = start_y + row * (bh + pad)
            rect = pygame.Rect(bx, by, bw, bh)
            self._building_rects[building.building_id] = rect

            bg_color = (30, 30, 60) if self._selected_building == building.building_id \
                       else PANEL_BG
            pygame.draw.rect(surface, bg_color, rect)
            border_col = ACCENT if building.is_built() else BORDER
            pygame.draw.rect(surface, border_col, rect, 1)

            name_surf = self._font_sm.render(
                building.name, True, TEXT_MAIN if building.is_built() else TEXT_MUTED)
            surface.blit(name_surf, (bx + 6, by + 6))
            for lvl in range(building.max_level):
                pc = SUCCESS if lvl < building.level else (40, 40, 40)
                pygame.draw.rect(surface, pc, (bx + 6 + lvl * 13, by + 22, 9, 5))

            desc_lines = self._wrap_text(building.description, bw - 12, self._font_sm)
            for j, line in enumerate(desc_lines[:3]):
                lt = self._font_sm.render(line, True, TEXT_MUTED)
                surface.blit(lt, (bx + 6, by + 32 + j * 13))

            if not building.is_built():
                cost = building.upgrade_cost()
                cs = " ".join(f"{v}{k[:2]}" for k, v in cost.items())
                can = self.can_afford(cost)
                ct = self._font_sm.render(f"BUILD {cs}", True, SUCCESS if can else DANGER)
                surface.blit(ct, (bx + 6, by + bh - 16))
            elif building.can_upgrade():
                cost = building.upgrade_cost()
                cs = " ".join(f"{v}{k[:2]}" for k, v in cost.items())
                can = self.can_afford(cost)
                ct = self._font_sm.render(f"UP {cs}", True, WARNING if can else DANGER)
                surface.blit(ct, (bx + 6, by + bh - 16))
            else:
                mt = self._font_sm.render("MAX", True, SUCCESS)
                surface.blit(mt, (bx + 6, by + bh - 16))

    # ── Crew tab ──────────────────────────────────────────────────────────────
    def _draw_crew_tab(self, surface, start_y, panel_w, sh):
        """Draw the crew/mercenary/side-quest management tab."""
        x0 = 14
        y  = start_y
        w  = panel_w - x0 - 10

        cantina = self.buildings.get("cantina")
        if not cantina or not cantina.is_built():
            lock_font = pygame.font.SysFont("monospace", 14)
            lock1 = lock_font.render("Build the Cantina to unlock Crew management.", True, TEXT_MUTED)
            lock2 = lock_font.render("Hire mercenaries, start side quests, and send", True, TEXT_MUTED)
            lock3 = lock_font.render("ships on missions from here.", True, TEXT_MUTED)
            surface.blit(lock1, (x0, y + 20))
            surface.blit(lock2, (x0, y + 42))
            surface.blit(lock3, (x0, y + 64))
            return

        self._merc_hire_rects:  dict[int, pygame.Rect] = {}
        self._quest_start_rects: dict[str, pygame.Rect] = {}
        self._crew_buy_rects:   dict[int, pygame.Rect] = {}

        # ── Section: Hired crew ───────────────────────────────────────────────
        sec_font = pygame.font.SysFont("monospace", 13, bold=True)
        sm_font  = pygame.font.SysFont("monospace", 11)

        hired_hdr = sec_font.render(
            f"YOUR CREW  ({len(self._hired_crew)} hired)", True, ACCENT)
        surface.blit(hired_hdr, (x0, y)); y += 18

        if self._hired_crew:
            for crew_member in self._hired_crew[:6]:
                rc = {"common": TEXT_MUTED, "uncommon": SUCCESS,
                      "rare": (60, 120, 255), "epic": (160, 60, 220)}.get(
                    crew_member.get("rarity", "common"), TEXT_MUTED)
                role_icon = {
                    "Pilot": "✈", "Gunner": "🎯", "Engineer": "⚙",
                    "Medic": "+", "Brawler": "⚔", "Navigator": "⬡",
                    "Hacker": "⌨", "Smuggler": "◈",
                }.get(crew_member.get("role", "?"), "·")
                stat_key = crew_member.get("stat", "combat")
                stat_val = crew_member.get(stat_key, crew_member.get("combat", 0))
                line = sm_font.render(
                    f"  {role_icon} {crew_member['name'][:14]:<14}  [{crew_member['role'][:9]}]"
                    f"  {stat_key[:3].upper()}:{stat_val}",
                    True, rc)
                surface.blit(line, (x0, y)); y += 14
        else:
            none_t = sm_font.render("  No crew hired yet. Buy crew or hire a mercenary below.", True, TEXT_MUTED)
            surface.blit(none_t, (x0, y)); y += 14

        y += 6
        pygame.draw.line(surface, BORDER, (x0, y), (x0 + w, y)); y += 8

        # ── Section: BUY CREW (regular crew, always available at Cantina) ─────
        crew_hdr = sec_font.render("BUY CREW  (regular, Cantina Lv1+)", True, (180, 220, 255))
        surface.blit(crew_hdr, (x0, y)); y += 18

        btn_h = 22
        for reg_idx, member in enumerate(REGULAR_CREW_ROSTER):
            if y > sh - 180:
                break
            can = self.resources.get("credits", 0) >= member["cost"]
            row_r = pygame.Rect(x0, y, w - 80, btn_h)
            pygame.draw.rect(surface, PANEL_BG, row_r)
            pygame.draw.rect(surface, BORDER, row_r, 1)
            info = sm_font.render(
                f"{member['name']:<10}  {member['role']:<12}  {member['desc'][:28]}",
                True, TEXT_MAIN if can else TEXT_MUTED)
            surface.blit(info, (x0 + 4, y + (btn_h - info.get_height()) // 2))
            hire_r2 = pygame.Rect(x0 + w - 76, y, 74, btn_h)
            pygame.draw.rect(surface, (10, 40, 10) if can else (30, 15, 15), hire_r2)
            pygame.draw.rect(surface, SUCCESS if can else DANGER, hire_r2, 1)
            hire_lbl2 = sm_font.render(f"${member['cost']}", True, SUCCESS if can else DANGER)
            surface.blit(hire_lbl2, (hire_r2.centerx - hire_lbl2.get_width() // 2,
                                     hire_r2.centery - hire_lbl2.get_height() // 2))
            self._crew_buy_rects[reg_idx] = hire_r2
            y += btn_h + 2

        y += 6
        pygame.draw.line(surface, BORDER, (x0, y), (x0 + w, y)); y += 8

        # ── Section: Available Mercenaries ───────────────────────────────────
        lvl_cap = cantina.level
        merc_hdr = sec_font.render(
            f"HIRE MERCENARIES  (Cantina Lv{lvl_cap} — elite crew)", True, (255, 200, 80))
        surface.blit(merc_hdr, (x0, y)); y += 18

        # Filter mercs by cantina level: lv1→common only, lv2→+uncommon, lv3→+rare
        rarity_unlock = {1: {"common"}, 2: {"common", "uncommon"}, 3: {"common", "uncommon", "rare"}}
        allowed = rarity_unlock.get(lvl_cap, {"common"})
        available_mercs = [m for m in MERCENARY_ROSTER if m["rarity"] in allowed]

        btn_h = 26
        for idx, merc in enumerate(available_mercs[:9]):
            if y > sh - 120:
                break
            rc = {"common": TEXT_MUTED, "uncommon": SUCCESS,
                  "rare": (60, 120, 255), "epic": (180, 80, 240)}.get(merc["rarity"], TEXT_MUTED)
            can = self.resources.get("credits", 0) >= merc["cost"]
            row_r = pygame.Rect(x0, y, w - 80, btn_h)
            # Two-tone row bg
            pygame.draw.rect(surface, (12, 20, 30) if idx % 2 == 0 else PANEL_BG, row_r)
            pygame.draw.rect(surface, BORDER, row_r, 1)
            # Rarity stripe on left
            pygame.draw.rect(surface, rc, pygame.Rect(x0, y, 3, btn_h))
            name_t = sm_font.render(
                f" {merc['name'][:13]:<13}  [{merc['role'][:9]}]  Cmbt:{merc['combat']}",
                True, rc)
            desc_t = sm_font.render(
                f"   {merc.get('desc', '')[:34]}",
                True, TEXT_MUTED)
            # Stack name + desc in the row (2 lines, smaller)
            surface.blit(name_t, (x0 + 6, y + 2))
            if btn_h >= 24:
                surface.blit(desc_t, (x0 + 6, y + 14))
            else:
                surface.blit(name_t, (x0 + 4, y + (btn_h - name_t.get_height()) // 2))

            # Hire button
            hire_r = pygame.Rect(x0 + w - 76, y, 74, btn_h)
            pygame.draw.rect(surface, (20, 60, 20) if can else (40, 20, 20), hire_r)
            pygame.draw.rect(surface, SUCCESS if can else DANGER, hire_r, 1)
            hire_lbl = sm_font.render(f"${merc['cost']}", True, SUCCESS if can else DANGER)
            surface.blit(hire_lbl, (hire_r.centerx - hire_lbl.get_width() // 2,
                                    hire_r.centery - hire_lbl.get_height() // 2))
            # Map back to the full MERCENARY_ROSTER index
            roster_idx = MERCENARY_ROSTER.index(merc)
            self._merc_hire_rects[roster_idx] = hire_r
            y += btn_h + 2

        y += 6
        pygame.draw.line(surface, BORDER, (x0, y), (x0 + w, y)); y += 8

        # ── Section: Side Quests ─────────────────────────────────────────────
        ql_txt = sec_font.render(
            f"SIDE QUESTS  — Level {self.quest_level}  [{self._quests_completed} done]",
            True, ACCENT)
        surface.blit(ql_txt, (x0, y)); y += 14
        unlock_hint = sm_font.render(
            "Complete quests to unlock higher levels with better rewards",
            True, TEXT_MUTED)
        surface.blit(unlock_hint, (x0, y)); y += 16

        for q in SIDE_QUESTS:
            if y > sh - 60:
                break
            # Grey-out locked quests
            locked = q.get("level_req", 0) > self._quests_completed
            active_q = next((aq for aq in self._active_quests if aq["id"] == q["id"]), None)

            qlvl = q.get("level", 1)
            lvl_cols = {1:(160,160,160),2:(80,200,80),3:(60,120,255),4:(160,60,220),5:(255,160,30)}
            lvl_col = lvl_cols.get(qlvl, TEXT_MUTED)

            row_r = pygame.Rect(x0, y, w - 78, 36)
            row_bg = (15,15,20) if locked else PANEL_BG
            row_border = (40,40,50) if locked else BORDER
            pygame.draw.rect(surface, row_bg, row_r)
            pygame.draw.rect(surface, row_border, row_r, 1)

            # Level badge
            badge_r = pygame.Rect(x0+2, y+2, 26, 14)
            pygame.draw.rect(surface, lvl_col, badge_r, border_radius=2)
            badge_t = sm_font.render(f"L{qlvl}", True, DARK_BG)
            surface.blit(badge_t, (badge_r.centerx - badge_t.get_width()//2,
                                   badge_r.centery - badge_t.get_height()//2))

            name_col = TEXT_MUTED if locked else TEXT_MAIN
            name_s = sm_font.render(q["name"], True, name_col)
            surface.blit(name_s, (x0 + 32, y + 2))

            fu = q.get("reward_fuel", 0)
            rew_parts = [f"+{q['reward_credits']}cr"]
            if q["reward_metal"]: rew_parts.append(f"+{q['reward_metal']}mt")
            if fu: rew_parts.append(f"+{fu}fu")
            rew_parts.append(f"{q['duration_min']}min")
            rew_s = sm_font.render("  ".join(rew_parts), True, TEXT_MUTED if locked else (160,200,160))
            surface.blit(rew_s, (x0 + 32, y + 18))

            # Status / start / locked indicator
            if locked:
                need_s = sm_font.render(
                    f"Unlock at {q['level_req']} quests done", True, (80,60,40))
                surface.blit(need_s, (x0 + w - 132, y + 10))
            elif active_q:
                tl = active_q["time_left"]
                mm = int(tl) // 60; ss = int(tl) % 60
                ship_on = active_q.get("ship", "?")
                status_t = sm_font.render(f"{ship_on}  {mm}:{ss:02d}", True, WARNING)
                surface.blit(status_t, (x0 + w - 132, y + 10))
            else:
                qbtn = pygame.Rect(x0 + w - 76, y + 6, 74, 24)
                pygame.draw.rect(surface, (20, 50, 20), qbtn)
                pygame.draw.rect(surface, SUCCESS, qbtn, 1)
                ql2 = sm_font.render("SEND ▶", True, SUCCESS)
                surface.blit(ql2, (qbtn.centerx - ql2.get_width() // 2,
                                   qbtn.centery - ql2.get_height() // 2))
                self._quest_start_rects[q["id"]] = qbtn
            y += 40

        # ── Ship-selection popup for side quests ──────────────────────────────
        popup = self._quest_ship_select_popup
        if popup is not None:
            self._draw_quest_ship_popup(surface, popup, sm_font, sec_font)

    # ── RIGHT: asteroid base view ─────────────────────────────────────────────

    def _draw_quest_ship_popup(self, surface, popup: dict, sm_font, sec_font) -> None:
        """Draw the ship-selection popup that appears when SEND is clicked."""
        sw, sh2 = surface.get_size()
        pw, ph = 420, 320
        px = (sw - pw) // 2
        py = (sh2 - ph) // 2

        # Semi-transparent backdrop
        overlay = pygame.Surface((sw, sh2), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surface.blit(overlay, (0, 0))

        # Panel
        pygame.draw.rect(surface, (16, 20, 40), (px, py, pw, ph))
        pygame.draw.rect(surface, ACCENT, (px, py, pw, ph), 2)

        qid = popup["quest_id"]
        quest_def = next((q for q in SIDE_QUESTS if q["id"] == qid), None)
        qname = quest_def["name"] if quest_def else qid

        hdr = sec_font.render(f"SELECT SHIP — {qname}", True, ACCENT)
        surface.blit(hdr, (px + 10, py + 8))

        self._quest_popup_btns = []
        ships = popup.get("ships", [])
        sel   = popup.get("selected", 0)

        y2 = py + 30
        if not ships:
            none_t = sm_font.render("No ships available in your fleet.", True, WARNING)
            surface.blit(none_t, (px + 10, y2))
        else:
            for i, sinfo in enumerate(ships):
                is_sel = (i == sel)
                avail  = sinfo["available"]
                row = pygame.Rect(px + 8, y2, pw - 16, 28)
                bg  = (20, 50, 80) if is_sel else ((10, 10, 20) if not avail else (12, 25, 12))
                pygame.draw.rect(surface, bg, row)
                pygame.draw.rect(surface, ACCENT if is_sel else (BORDER if avail else DANGER), row, 1)
                status = "" if avail else "  [ON MISSION]"
                label_txt = f"  {sinfo['name'][:20]:<20}  [{sinfo['class']}]{status}"
                col = TEXT_MAIN if avail else DANGER
                lbl = sm_font.render(label_txt, True, col)
                surface.blit(lbl, (row.x + 4, row.centery - lbl.get_height() // 2))
                self._quest_popup_btns.append(("select", i, row))
                y2 += 30

        # Confirm / Cancel buttons
        y2 = py + ph - 46
        conf_btn = pygame.Rect(px + 10, y2, 140, 34)
        canc_btn = pygame.Rect(px + pw - 150, y2, 140, 34)
        sel_avail = (ships and 0 <= sel < len(ships) and ships[sel]["available"])
        pygame.draw.rect(surface, (20, 60, 20) if sel_avail else (30, 30, 30), conf_btn)
        pygame.draw.rect(surface, SUCCESS if sel_avail else BORDER, conf_btn, 1)
        conf_t = sm_font.render("✓ Assign Ship", True, SUCCESS if sel_avail else TEXT_MUTED)
        surface.blit(conf_t, (conf_btn.centerx - conf_t.get_width()//2,
                               conf_btn.centery - conf_t.get_height()//2))
        pygame.draw.rect(surface, (50, 20, 20), canc_btn)
        pygame.draw.rect(surface, DANGER, canc_btn, 1)
        canc_t = sm_font.render("✗ Cancel", True, DANGER)
        surface.blit(canc_t, (canc_btn.centerx - canc_t.get_width()//2,
                               canc_btn.centery - canc_t.get_height()//2))
        self._quest_popup_btns.append(("confirm", -1, conf_btn))
        self._quest_popup_btns.append(("cancel",  -1, canc_btn))

    # ── Armory / Shop tab ─────────────────────────────────────────────────────
    def _draw_armory_tab(self, surface, start_y, panel_w, sh):
        x0 = 14
        y  = start_y
        w  = panel_w - x0 - 10
        sf = pygame.font.SysFont("monospace", 13, bold=True)
        sm = pygame.font.SysFont("monospace", 11)

        # Header
        hdr = sf.render("ARMORY & GEAR SHOP", True, (200, 80, 80))
        surface.blit(hdr, (x0, y)); y += 18

        # Filter buttons
        FILTERS = [("all","All"), ("weapon","Weapons"), ("module","Modules"),
                   ("drone","Drones"), ("ship","Ships"), ("crew_gear","Crew Gear")]
        self._armory_filter_rects: dict[str, pygame.Rect] = {}
        fx = x0
        for fid, flbl in FILTERS:
            fw = (w) // len(FILTERS)
            fr = pygame.Rect(fx, y, fw - 2, 18)
            sel = (self._armory_filter == fid)
            pygame.draw.rect(surface, (30,30,60) if sel else PANEL_BG, fr)
            pygame.draw.rect(surface, ACCENT if sel else BORDER, fr, 1)
            ft = sm.render(flbl, True, TEXT_MAIN if sel else TEXT_MUTED)
            surface.blit(ft, (fr.centerx - ft.get_width()//2, fr.y + 3))
            self._armory_filter_rects[fid] = fr
            fx += fw
        y += 22

        armory_built = self.buildings.get("armory")
        if not armory_built or not armory_built.is_built():
            lock = sm.render("Build the Armory to unlock the gear shop.", True, TEXT_MUTED)
            surface.blit(lock, (x0, y + 10))
            return

        # Item list — combine GEAR_CATALOGUE + CREW_GEAR_ITEMS depending on filter
        if self._armory_filter == "crew_gear":
            items = list(CREW_GEAR_ITEMS)
        elif self._armory_filter == "all":
            items = list(GEAR_CATALOGUE) + list(CREW_GEAR_ITEMS)
        else:
            items = [i for i in GEAR_CATALOGUE if i["type"] == self._armory_filter]

        self._armory_buy_rects: dict[int, pygame.Rect] = {}
        RARITY_COLORS = {"common": TEXT_MUTED, "uncommon": SUCCESS,
                         "rare": (60,120,255), "epic": (160,60,220), "legendary": (255,160,30)}
        TYPE_ICONS = {"weapon": "⚔", "module": "⚙", "drone": "🤖", "ship": "🚀",
                      "crew_gear": "👤"}

        for i, item in enumerate(items):
            if y > sh - 90:
                more = sm.render(f"... {len(items)-i} more items", True, TEXT_MUTED)
                surface.blit(more, (x0, y)); break
            rc = RARITY_COLORS.get(item["rarity"], TEXT_MUTED)
            can = self.resources.get("credits", 0) >= item["cost"]
            row = pygame.Rect(x0, y, w - 76, 28)
            pygame.draw.rect(surface, PANEL_BG, row)
            icon = TYPE_ICONS.get(item["type"], "•")
            nm = sm.render(f"{icon} {item['name'][:18]:<18}  {item['rarity'][:3].upper()}",
                           True, rc)
            surface.blit(nm, (x0 + 4, y + 3))
            desc = sm.render(item["desc"][:36], True, TEXT_MUTED)
            surface.blit(desc, (x0 + 4, y + 16))
            # Buy button
            brect = pygame.Rect(x0 + w - 72, y + 4, 70, 20)
            pygame.draw.rect(surface, (20,60,20) if can else (40,20,20), brect)
            pygame.draw.rect(surface, SUCCESS if can else DANGER, brect, 1)
            bt = sm.render(f"{item['cost']}cr", True, SUCCESS if can else DANGER)
            surface.blit(bt, (brect.centerx - bt.get_width()//2,
                               brect.centery - bt.get_height()//2))
            self._armory_buy_rects[i] = brect
            y += 30

    # ── Crew Management tab ───────────────────────────────────────────────────

    # ── Crew Roster tab ───────────────────────────────────────────────────────
    def _all_roster_crew(self, fleet=None) -> list:
        """Return all Crew objects from fleet ships + _hired_crew dicts."""
        crew = []
        if fleet:
            for ship in (fleet.ships or []):
                for c in (ship.crew or []):
                    crew.append(c)
        # Also include hired_crew dicts (wrap lightly for display)
        for hc in self._hired_crew:
            # Avoid duplicates if already in fleet
            if not any(getattr(c, "name", None) == hc.get("name") for c in crew):
                crew.append(hc)
        return crew

    def _draw_crew_avatar(self, surface: pygame.Surface, crew_obj,
                          cx: int, cy: int, size: int = 80) -> None:
        """Render a proper bust-portrait card for a crew member.

        The portrait is painted into a 120×160 off-screen surface then scaled
        to `size` and blitted centred on (cx, cy).  All detail is proportional
        to the canvas so it looks good at any size from 60 to 120 px.
        """
        import pygame as _pg
        import math as _m

        # ── Data ─────────────────────────────────────────────────────────────
        import random as _rnd
        role   = getattr(crew_obj, "role",
                         crew_obj.get("role", "combat") if isinstance(crew_obj, dict) else "combat")
        rarity = getattr(crew_obj, "rarity",
                         crew_obj.get("rarity", "common") if isinstance(crew_obj, dict) else "common")
        name   = getattr(crew_obj, "name",
                         crew_obj.get("name", "?") if isinstance(crew_obj, dict) else "?")
        crew_id = getattr(crew_obj, "id",
                          crew_obj.get("id", name) if isinstance(crew_obj, dict) else name)
        equipment = (getattr(crew_obj, "equipment", {})
                     if not isinstance(crew_obj, dict) else {})

        # Deterministic RNG seeded from crew id — same person always looks the same
        _prng = _rnd.Random(hash(crew_id) & 0xFFFFFFFF)

        # ── Palette ───────────────────────────────────────────────────────────
        RARITY_GLOW = {
            "common":    (140, 140, 150),
            "uncommon":  (60,  200, 80),
            "rare":      (50,  130, 255),
            "epic":      (160, 50,  230),
            "legendary": (255, 175, 20),
        }
        # All possible skin tones — picked randomly per crew member
        SKIN_POOL = [
            (235, 200, 165),   # fair/light
            (215, 175, 135),   # light
            (195, 155, 115),   # light-medium
            (175, 135, 100),   # medium
            (155, 115,  80),   # medium-tan
            (130,  90,  55),   # tan/brown
            (100,  65,  35),   # dark brown
            ( 75,  45,  25),   # deep brown
            ( 50,  32,  18),   # very dark
            (225, 195, 155),   # warm ivory
            (205, 175, 140),   # warm beige
            (185, 148, 110),   # golden tan
            (215, 190, 160),   # cool fair
            (160, 120,  85),   # warm medium
            (210, 170, 130),   # neutral medium
        ]
        # Hair colours — independent random pick
        HAIR_POOL = [
            ( 20,  15,  10),   # jet black
            ( 45,  30,  18),   # dark brown
            ( 90,  55,  28),   # medium brown
            (140,  90,  40),   # warm brown
            (175, 130,  55),   # auburn
            (195, 155,  65),   # dirty blonde
            (220, 190,  90),   # blonde
            (235, 215, 140),   # light blonde
            ( 80,  80,  85),   # dark grey
            (140, 140, 145),   # silver-grey
            (180,  45,  30),   # auburn-red
            (210,  80,  40),   # bright red
            ( 30,  60, 120),   # blue-black (dyed)
            ( 55, 155,  80),   # green (dyed)
            (130,  40, 170),   # purple (dyed)
        ]
        UNIFORMS = {
            "pilot":    {"main": (28, 60, 140),  "trim": (90, 165, 255),  "hat": "visor"},
            "gunner":   {"main": (110, 22, 22),  "trim": (240, 90,  50),  "hat": "beret"},
            "engineer": {"main": (22, 80,  42),  "trim": (70,  215, 90),  "hat": "goggles"},
            "mechanic": {"main": (80, 65,  15),  "trim": (205, 185, 50),  "hat": "cap"},
            "combat":   {"main": (70, 15,  15),  "trim": (215, 70,  70),  "hat": "helmet"},
        }
        glow_col  = RARITY_GLOW.get(rarity, (140, 140, 150))
        skin_col  = _prng.choice(SKIN_POOL)
        hair_col  = _prng.choice(HAIR_POOL)
        skin_dark = tuple(max(0, c - 28) for c in skin_col)
        skin_lit  = tuple(min(255, c + 22) for c in skin_col)
        uni       = UNIFORMS.get(role, UNIFORMS["combat"])
        u_main    = uni["main"]
        u_trim    = uni["trim"]
        u_dark    = tuple(max(0, c - 25) for c in u_main)
        u_light   = tuple(min(255, c + 35) for c in u_main)
        hat_type  = uni["hat"]

        # ── Canvas (fixed 120 × 160 px, painted at 2× then scaled down) ──────
        CW, CH = 120, 160
        canvas = _pg.Surface((CW, CH), _pg.SRCALPHA)

        def _blend_rect(surf, col, rect, alpha=180, radius=0):
            s2 = _pg.Surface((rect.w, rect.h), _pg.SRCALPHA)
            _pg.draw.rect(s2, (*col, alpha), s2.get_rect(), border_radius=radius)
            surf.blit(s2, rect.topleft)

        # ── 1. Background gradient card ──────────────────────────────────────
        # Dark card with rarity-tinted corners
        for y_bg in range(CH):
            frac  = y_bg / CH
            r_bg  = int(12 + frac * 10)
            g_bg  = int(12 + frac * 8)
            b_bg  = int(20 + frac * 12)
            _pg.draw.line(canvas, (r_bg, g_bg, b_bg), (0, y_bg), (CW, y_bg))
        # Rarity colour vignette (top-left and bottom-right corners)
        for corner, pos in [((0, 0), True), ((CW, CH), False)]:
            gv = _pg.Surface((CW, CH), _pg.SRCALPHA)
            gcx, gcy = corner
            for ri, al in [(40, 30), (28, 20), (18, 12)]:
                _pg.draw.circle(gv, (*glow_col, al), (gcx, gcy), ri * 4)
            canvas.blit(gv, (0, 0))
        # Card border in rarity colour
        _pg.draw.rect(canvas, u_dark, canvas.get_rect(), border_radius=6)
        _pg.draw.rect(canvas, glow_col, canvas.get_rect(), 2, border_radius=6)

        # ── 2. Shoulder / chest area (occupies lower 55% of canvas) ──────────
        # Shoulders sweep out from centre
        sh_cx = CW // 2
        sh_top = CH * 52 // 100
        # Shoulder silhouette polygon
        shoulder_pts = [
            (sh_cx - 52, CH), (sh_cx - 52, sh_top + 14),
            (sh_cx - 32, sh_top),
            (sh_cx + 32, sh_top),
            (sh_cx + 52, sh_top + 14), (sh_cx + 52, CH),
        ]
        _pg.draw.polygon(canvas, u_dark, shoulder_pts)
        _pg.draw.polygon(canvas, u_main, shoulder_pts, 2)

        # Chest centre panel
        chest_rect = _pg.Rect(sh_cx - 20, sh_top + 4, 40, CH - sh_top - 4)
        _pg.draw.rect(canvas, u_main, chest_rect)
        # Centre stripe / zipper
        _pg.draw.line(canvas, u_trim, (sh_cx, sh_top + 6), (sh_cx, CH - 2), 1)

        # Role chest details
        if role == "pilot":
            # Wing badge on left chest
            bx, by = sh_cx - 16, sh_top + 22
            for i, (dx, dy) in enumerate([(-14,0),(-10,-4),(-4,-7),(0,-8),(4,-7),(10,-4),(14,0)]):
                _pg.draw.circle(canvas, u_trim, (bx + dx, by + dy), 1)
            _pg.draw.aaline(canvas, u_trim, (bx - 14, by), (bx + 14, by))
            # Flight suit collar V
            _pg.draw.aaline(canvas, u_trim, (sh_cx - 10, sh_top + 2), (sh_cx, sh_top + 10))
            _pg.draw.aaline(canvas, u_trim, (sh_cx + 10, sh_top + 2), (sh_cx, sh_top + 10))
        elif role == "gunner":
            # Diagonal bandolier strap
            _pg.draw.line(canvas, u_trim, (sh_cx - 32, sh_top + 4), (sh_cx + 16, CH - 4), 2)
            # Ammo pouches along strap
            for ty in range(sh_top + 16, CH - 6, 20):
                px_ = sh_cx - 32 + int((ty - sh_top - 4) * (48 / (CH - sh_top - 8)))
                _pg.draw.rect(canvas, u_trim, _pg.Rect(px_ - 4, ty - 4, 8, 7))
            # Shoulder pad lines
            _pg.draw.line(canvas, u_light, (sh_cx - 52, sh_top + 14),
                           (sh_cx - 38, sh_top + 4), 3)
            _pg.draw.line(canvas, u_light, (sh_cx + 52, sh_top + 14),
                           (sh_cx + 38, sh_top + 4), 3)
        elif role == "engineer":
            # Tool belt at bottom of torso
            belt_y = CH - 28
            _pg.draw.rect(canvas, u_trim, _pg.Rect(sh_cx - 38, belt_y, 76, 6))
            for px_ in [sh_cx - 26, sh_cx - 8, sh_cx + 8, sh_cx + 22]:
                _pg.draw.rect(canvas, u_dark,  _pg.Rect(px_ - 4, belt_y - 5, 8, 8))
                _pg.draw.rect(canvas, u_trim,  _pg.Rect(px_ - 4, belt_y - 5, 8, 8), 1)
            # Chest pocket
            _pg.draw.rect(canvas, u_trim, _pg.Rect(sh_cx + 4, sh_top + 8, 16, 14), 1,
                          border_radius=2)
        elif role == "mechanic":
            # Dungaree bib
            bib_r = _pg.Rect(sh_cx - 14, sh_top + 2, 28, CH - sh_top - 8)
            _pg.draw.rect(canvas, u_trim, bib_r, 1, border_radius=4)
            # Bib pockets
            for py_ in [sh_top + 12, sh_top + 28]:
                _pg.draw.rect(canvas, u_dark, _pg.Rect(sh_cx - 10, py_, 20, 10))
                _pg.draw.rect(canvas, u_trim, _pg.Rect(sh_cx - 10, py_, 20, 10), 1)
        elif role == "combat":
            # Horizontal armour plate lines
            for py_ in [sh_top + 6, sh_top + 18, sh_top + 30]:
                _pg.draw.line(canvas, u_trim,
                              (sh_cx - 44, py_), (sh_cx + 44, py_), 1)
            # Centre chest armour block
            _pg.draw.rect(canvas, u_trim, _pg.Rect(sh_cx - 14, sh_top + 6, 28, 26), 1,
                          border_radius=3)

        # ── 3. Neck ───────────────────────────────────────────────────────────
        neck_top = CH * 42 // 100
        neck_w   = 18
        _pg.draw.rect(canvas, skin_col,
                      _pg.Rect(sh_cx - neck_w // 2, neck_top, neck_w, 14))

        # ── 4. Head ───────────────────────────────────────────────────────────
        # Head is an oval, centred near top of canvas
        hcx, hcy = sh_cx, CH * 28 // 100
        hr_x, hr_y = 28, 32           # horizontal / vertical radii

        # Head base — painted with gradient
        for hy_ in range(hcy - hr_y, hcy + hr_y + 1):
            frac  = (hy_ - (hcy - hr_y)) / (hr_y * 2)
            # Ellipse half-width at this scanline
            dy_   = abs(hy_ - hcy)
            if dy_ >= hr_y: continue
            half_w = int(hr_x * _m.sqrt(max(0, 1 - (dy_ / hr_y) ** 2)))
            shading = int(frac * 30)   # slight bottom darkening
            hcol   = tuple(max(0, c - shading) for c in skin_col)
            _pg.draw.line(canvas, hcol,
                          (hcx - half_w, hy_), (hcx + half_w, hy_))
        # Head outline
        _pg.draw.ellipse(canvas, skin_dark,
                         _pg.Rect(hcx - hr_x, hcy - hr_y, hr_x * 2, hr_y * 2), 1)

        # Jaw / chin shadow
        jaw_surf = _pg.Surface((hr_x * 2, hr_y), _pg.SRCALPHA)
        _pg.draw.ellipse(jaw_surf, (*skin_dark, 60),
                         _pg.Rect(0, 0, hr_x * 2, hr_y))
        canvas.blit(jaw_surf, (hcx - hr_x, hcy))

        # ── 5. Hair ───────────────────────────────────────────────────────────
        hair_dark = tuple(max(0, c - 30) for c in hair_col)
        hair_lit  = tuple(min(255, c + 40) for c in hair_col)
        # Hair cap (filled arc above head)
        _pg.draw.ellipse(canvas, hair_col,
                         _pg.Rect(hcx - hr_x - 1, hcy - hr_y - 8,
                                   hr_x * 2 + 2, hr_y))
        # Side burns / hair taper
        for side, sx_ in [(-1, hcx - hr_x), (1, hcx + hr_x)]:
            for i in range(4):
                hy2 = hcy - hr_y // 2 + i * 5
                hw2 = 3 - i // 2
                _pg.draw.circle(canvas, hair_col, (sx_ + side * i, hy2), hw2)
        # Hair highlight streak
        _pg.draw.arc(canvas, hair_lit,
                     _pg.Rect(hcx - hr_x + 6, hcy - hr_y - 6, hr_x - 4, hr_y // 2),
                     _m.radians(25), _m.radians(155), 2)

        # ── 6. Eyes ───────────────────────────────────────────────────────────
        eye_y  = hcy - 4
        eye_ex = hr_x // 2 - 1     # horizontal offset from centre
        eye_rw, eye_rh = 7, 5       # eye half-width/height
        iris_col = glow_col
        for ex in [-eye_ex, eye_ex]:
            # White sclera
            _pg.draw.ellipse(canvas, (235, 232, 228),
                             _pg.Rect(hcx + ex - eye_rw, eye_y - eye_rh,
                                       eye_rw * 2, eye_rh * 2))
            # Upper eyelid shadow
            _pg.draw.arc(canvas, skin_dark,
                         _pg.Rect(hcx + ex - eye_rw, eye_y - eye_rh,
                                   eye_rw * 2, eye_rh * 2),
                         _m.radians(20), _m.radians(160), 2)
            # Iris
            iris_r = eye_rh - 1
            _pg.draw.circle(canvas, iris_col, (hcx + ex, eye_y), iris_r)
            # Pupil
            _pg.draw.circle(canvas, (8, 8, 12), (hcx + ex, eye_y), max(1, iris_r - 2))
            # Shine dot
            _pg.draw.circle(canvas, (240, 240, 255),
                            (hcx + ex + 2, eye_y - 2), 2)
        # Eyebrows
        brow_col = hair_dark
        for ex in [-eye_ex, eye_ex]:
            brow_y = eye_y - eye_rh - 3
            _pg.draw.arc(canvas, brow_col,
                         _pg.Rect(hcx + ex - eye_rw - 1, brow_y - 3,
                                   eye_rw * 2 + 2, 8),
                         _m.radians(15), _m.radians(165), 2)

        # ── 7. Nose ───────────────────────────────────────────────────────────
        nose_tip_y = hcy + hr_y // 4
        _pg.draw.ellipse(canvas, skin_dark,
                         _pg.Rect(hcx - 4, nose_tip_y - 4, 8, 6))
        _pg.draw.circle(canvas, skin_dark, (hcx - 5, nose_tip_y - 1), 2)
        _pg.draw.circle(canvas, skin_dark, (hcx + 5, nose_tip_y - 1), 2)

        # ── 8. Mouth ─────────────────────────────────────────────────────────
        mouth_y = hcy + hr_y * 55 // 100
        lip_col = tuple(max(0, c - 20) for c in skin_dark)
        # Upper lip line
        _pg.draw.arc(canvas, lip_col,
                     _pg.Rect(hcx - 10, mouth_y - 5, 20, 10),
                     _m.radians(200), _m.radians(340), 2)
        # Lower lip
        _pg.draw.arc(canvas, lip_col,
                     _pg.Rect(hcx - 9, mouth_y - 2, 18, 8),
                     _m.radians(15), _m.radians(165), 2)

        # ── 9. Headgear ───────────────────────────────────────────────────────
        if hat_type == "visor":
            # Flight helmet shell over hair
            helm_col  = tuple(max(0, c - 10) for c in u_main)
            helm_rect = _pg.Rect(hcx - hr_x - 2, hcy - hr_y - 6, hr_x * 2 + 4, hr_y + 4)
            # Helmet outer shell
            _pg.draw.ellipse(canvas, helm_col, helm_rect)
            _pg.draw.ellipse(canvas, u_light, helm_rect, 1)
            # Visor slit
            visor_r = _pg.Rect(hcx - hr_x + 4, eye_y - eye_rh - 6,
                                hr_x * 2 - 8, eye_rh * 2 + 10)
            visor_s = _pg.Surface((visor_r.w, visor_r.h), _pg.SRCALPHA)
            _pg.draw.rect(visor_s, (60, 120, 220, 150), visor_s.get_rect(),
                          border_radius=4)
            canvas.blit(visor_s, visor_r.topleft)
            _pg.draw.rect(canvas, u_trim, visor_r, 1, border_radius=4)
            # Helmet highlight
            _pg.draw.arc(canvas, u_light,
                         _pg.Rect(hcx - 16, hcy - hr_y - 4, 20, 14),
                         _m.radians(30), _m.radians(150), 2)

        elif hat_type == "beret":
            # Dark beret draped over left
            beret_pts = [
                (hcx - hr_x - 4, hcy - hr_y + 6),
                (hcx - hr_x + 8, hcy - hr_y - 8),
                (hcx + hr_x - 2, hcy - hr_y - 4),
                (hcx + hr_x + 2, hcy - hr_y + 4),
            ]
            _pg.draw.polygon(canvas, (52, 24, 14), beret_pts)
            _pg.draw.polygon(canvas, (90, 50, 28), beret_pts, 1)
            # Beret badge
            _pg.draw.circle(canvas, u_trim, (hcx - 8, hcy - hr_y - 2), 4)
            _pg.draw.circle(canvas, u_main, (hcx - 8, hcy - hr_y - 2), 4, 1)

        elif hat_type == "goggles":
            # Goggles pushed up on forehead
            gog_y = hcy - hr_y + 4
            for gx_ in [hcx - 11, hcx + 5]:
                _pg.draw.circle(canvas, (30, 55, 40), (gx_, gog_y), 7)
                _pg.draw.circle(canvas, (55, 185, 90), (gx_, gog_y), 7, 2)
                # Lens tint
                gog_s = _pg.Surface((14, 14), _pg.SRCALPHA)
                _pg.draw.circle(gog_s, (60, 200, 100, 70), (7, 7), 6)
                canvas.blit(gog_s, (gx_ - 7, gog_y - 7))
            # Strap
            _pg.draw.line(canvas, (70, 70, 80),
                          (hcx - 4, gog_y), (hcx + 4, gog_y), 2)

        elif hat_type == "cap":
            # Work cap (flat-top)
            cap_col = (70, 56, 12)
            cap_top = _pg.Rect(hcx - hr_x - 2, hcy - hr_y - 4, hr_x * 2 + 4, hr_y // 2 + 2)
            _pg.draw.rect(canvas, cap_col, cap_top, border_radius=4)
            _pg.draw.rect(canvas, (105, 82, 28), cap_top, 1, border_radius=4)
            # Cap brim extending to the right
            brim_pts = [
                (hcx - hr_x - 2, hcy - hr_y + hr_y // 4),
                (hcx + hr_x + 14, hcy - hr_y + hr_y // 4 - 4),
                (hcx + hr_x + 14, hcy - hr_y + hr_y // 4 + 3),
                (hcx - hr_x - 2, hcy - hr_y + hr_y // 4 + 4),
            ]
            _pg.draw.polygon(canvas, (90, 72, 20), brim_pts)

        elif hat_type == "helmet":
            # Full combat helmet
            helm_col2 = (42, 42, 52)
            _pg.draw.ellipse(canvas, helm_col2,
                             _pg.Rect(hcx - hr_x - 4, hcy - hr_y - 8,
                                       hr_x * 2 + 8, hr_y + 12))
            _pg.draw.ellipse(canvas, (72, 72, 90),
                             _pg.Rect(hcx - hr_x - 4, hcy - hr_y - 8,
                                       hr_x * 2 + 8, hr_y + 12), 1)
            # Helmet visor bar
            _pg.draw.rect(canvas, (20, 20, 26),
                          _pg.Rect(hcx - hr_x + 2, eye_y - eye_rh - 5,
                                    hr_x * 2 - 4, eye_rh * 2 + 4))
            _pg.draw.rect(canvas, (60, 60, 80),
                          _pg.Rect(hcx - hr_x + 2, eye_y - eye_rh - 5,
                                    hr_x * 2 - 4, eye_rh * 2 + 4), 1)
            # Ear guards
            for ex_ in [hcx - hr_x - 6, hcx + hr_x + 2]:
                _pg.draw.rect(canvas, helm_col2, _pg.Rect(ex_, eye_y - 6, 8, 14),
                              border_radius=2)
            # Helmet highlight
            _pg.draw.arc(canvas, (90, 90, 110),
                         _pg.Rect(hcx - 14, hcy - hr_y - 6, 18, 14),
                         _m.radians(30), _m.radians(150), 2)

        # ── 10. Ear detail ────────────────────────────────────────────────────
        if hat_type not in ("helmet",):
            for ex_ in [hcx - hr_x, hcx + hr_x - 1]:
                _pg.draw.ellipse(canvas, skin_col,
                                 _pg.Rect(ex_ - 4, eye_y - 5, 8, 11))
                _pg.draw.ellipse(canvas, skin_dark,
                                 _pg.Rect(ex_ - 4, eye_y - 5, 8, 11), 1)
                _pg.draw.arc(canvas, skin_dark,
                             _pg.Rect(ex_ - 2, eye_y - 2, 4, 6),
                             _m.radians(210), _m.radians(330), 1)

        # ── 11. Name strip at bottom ──────────────────────────────────────────
        strip_h = 18
        strip_surf = _pg.Surface((CW, strip_h), _pg.SRCALPHA)
        _pg.draw.rect(strip_surf, (*u_dark, 200),
                      _pg.Rect(0, 0, CW, strip_h), border_radius=0)
        _pg.draw.line(strip_surf, glow_col, (0, 0), (CW, 0), 1)
        try:
            name_f  = _pg.font.SysFont("monospace", 9, bold=True)
            role_f  = _pg.font.SysFont("monospace", 8)
            nm_surf = name_f.render(name[:14], True, (230, 230, 240))
            rl_surf = role_f.render(f"[{role[:8]}] {rarity[:3].upper()}", True, glow_col)
            strip_surf.blit(nm_surf, (4, 1))
            strip_surf.blit(rl_surf, (CW - rl_surf.get_width() - 4, strip_h - rl_surf.get_height() - 1))
        except Exception:
            pass
        canvas.blit(strip_surf, (0, CH - strip_h))

        # ── 12. Gear badges (small icons in top-right corner) ─────────────────
        gear_x = CW - 14
        gear_y = 6
        for slot in ("head", "body", "tool"):
            gear_id = equipment.get(slot)
            if not gear_id:
                gear_y += 17
                continue
            gdef = next((g for g in CREW_GEAR_ITEMS if g["id"] == gear_id), None)
            if not gdef:
                gear_y += 17
                continue
            tint  = gdef.get("avatar_tint", (200, 200, 200))
            tdark = tuple(max(0, c - 50) for c in tint)
            _pg.draw.circle(canvas, tdark,  (gear_x, gear_y), 7)
            _pg.draw.circle(canvas, tint,   (gear_x, gear_y), 7, 2)
            try:
                bf = _pg.font.SysFont("monospace", 7, bold=True)
                bl = bf.render(slot[0].upper(), True, (240, 240, 240))
                canvas.blit(bl, (gear_x - bl.get_width() // 2,
                                  gear_y - bl.get_height() // 2))
            except Exception:
                pass
            gear_y += 17

        # ── 13. Scale & blit onto target surface ─────────────────────────────
        # Portrait is square-ish: scale so height = size, width = size * 0.75
        dest_h = size
        dest_w = int(size * 0.75)
        scaled = _pg.transform.smoothscale(canvas, (dest_w, dest_h))
        surface.blit(scaled, (cx - dest_w // 2, cy - dest_h // 2))

    def _roster_assign_station(self, crew_idx: int, station: str, fleet=None) -> None:
        """Assign a fleet crew member to a station on their ship."""
        crew_list = self._all_roster_crew(fleet)
        if crew_idx < 0 or crew_idx >= len(crew_list):
            return
        c = crew_list[crew_idx]
        if not hasattr(c, "assigned_station"):
            return  # dict-based merc — no station assignment
        # Find which ship this crew member is on
        if fleet:
            for ship in (fleet.ships or []):
                if c in (ship.crew or []):
                    ship.assign_station(c, station)
                    self._push_note(f"{c.name} → {station}", SUCCESS)
                    return

    def _roster_unequip_gear(self, crew_idx: int, slot: str, fleet=None) -> None:
        """Remove gear from a crew member slot and return it to inventory."""
        crew_list = self._all_roster_crew(fleet)
        if crew_idx < 0 or crew_idx >= len(crew_list):
            return
        c = crew_list[crew_idx]
        equipment = getattr(c, "equipment", None)
        if equipment is None:
            return
        gear_id = equipment.get(slot)
        if gear_id:
            equipment[slot] = None
            self._gear_inventory.append(gear_id)
            gear_def = next((g for g in CREW_GEAR_ITEMS if g["id"] == gear_id), None)
            name = gear_def["name"] if gear_def else gear_id
            self._push_note(f"Unequipped: {name}", WARNING)

    def _roster_equip_gear(self, crew_idx: int, gear_id: str, fleet=None) -> bool:
        """Equip a gear item from inventory onto the selected crew member."""
        inv = self._gear_inventory
        if gear_id not in inv:
            return False
        crew_list = self._all_roster_crew(fleet)
        if crew_idx < 0 or crew_idx >= len(crew_list):
            return False
        c = crew_list[crew_idx]
        if not hasattr(c, "equipment"):
            return False
        gear_def = next((g for g in CREW_GEAR_ITEMS if g["id"] == gear_id), None)
        if not gear_def:
            return False
        slot = gear_def["slot"]
        # Unequip whatever was there
        if c.equipment.get(slot):
            inv.append(c.equipment[slot])
        c.equipment[slot] = gear_id
        inv.remove(gear_id)
        self._gear_inventory = inv
        self._push_note(f"Equipped {gear_def['name']} → {c.name}", SUCCESS)
        return True

    def _draw_crew_roster_tab(self, surface, start_y, panel_w, sh, fleet=None):
        """Full crew roster: left list, right detail panel with avatar + stats."""
        import math as _math
        x0   = 10
        y    = start_y
        w    = panel_w - x0 - 8

        sf   = pygame.font.SysFont("monospace", 12, bold=True)
        sm   = pygame.font.SysFont("monospace", 10)
        sb   = pygame.font.SysFont("monospace", 11)

        crew_all = self._all_roster_crew(fleet)
        n        = len(crew_all)

        self._roster_list_rects: dict[int, pygame.Rect] = {}

        if not n:
            none_t = sf.render("No crew hired yet.  Hire from the Cantina or Crew tab.", True, TEXT_MUTED)
            surface.blit(none_t, (x0, y + 20))
            return

        # ── Left: crew list ───────────────────────────────────────────────────
        LIST_W = 150
        ROW_H  = 42
        max_vis = (sh - start_y - 10) // ROW_H
        sel     = max(0, min(self._roster_selected, n - 1))
        scroll  = max(0, sel - max_vis + 2)
        scroll  = min(scroll, max(0, n - max_vis))

        pygame.draw.rect(surface, (10, 14, 24), (x0 - 2, y, LIST_W + 2, sh - y - 4))
        pygame.draw.line(surface, BORDER, (x0 + LIST_W, y), (x0 + LIST_W, sh - 4))

        RARITY_COL = {"common": (160,160,170), "uncommon": (80,200,80),
                      "rare": (60,120,255), "epic": (160,60,220), "legendary": (255,160,30)}
        ROLE_COL   = {"pilot": (80,180,255), "gunner": (255,100,60),
                      "engineer": (100,220,120), "mechanic": (200,200,80), "combat": (220,80,80)}

        for i, c in enumerate(crew_all):
            vis = i - scroll
            if vis < 0 or vis >= max_vis:
                continue
            ry   = y + vis * ROW_H
            role = getattr(c, "role", c.get("role", "?") if isinstance(c, dict) else "?")
            rar  = getattr(c, "rarity", c.get("rarity", "common") if isinstance(c, dict) else "common")
            nm   = getattr(c, "name",   c.get("name", "?") if isinstance(c, dict) else "?")
            rc   = RARITY_COL.get(rar, TEXT_MUTED)
            is_sel = (i == sel)
            row_r = pygame.Rect(x0, ry, LIST_W, ROW_H - 2)
            pygame.draw.rect(surface, (25, 38, 62) if is_sel else (14, 18, 30), row_r)
            pygame.draw.rect(surface, rc if is_sel else (40, 44, 58), row_r, 1)
            pygame.draw.rect(surface, ROLE_COL.get(role, TEXT_MUTED), (x0, ry, 3, ROW_H - 2))
            nm_t  = sm.render(nm[:14], True, rc if is_sel else TEXT_MAIN)
            rl_t  = sm.render(role[:10].title(), True, ROLE_COL.get(role, TEXT_MUTED))
            rar_t = sm.render(rar[:3].upper(), True, rc)
            surface.blit(nm_t,  (x0 + 6, ry + 4))
            surface.blit(rl_t,  (x0 + 6, ry + 16))
            surface.blit(rar_t, (x0 + 6, ry + 28))
            self._roster_list_rects[i] = row_r

        # ── Right: detail panel ───────────────────────────────────────────────
        DX = x0 + LIST_W + 6
        DW = panel_w - DX - 6

        c   = crew_all[sel]
        role = getattr(c, "role",    c.get("role", "?") if isinstance(c, dict) else "?")
        rar  = getattr(c, "rarity",  c.get("rarity", "common") if isinstance(c, dict) else "common")
        nm   = getattr(c, "name",    c.get("name", "?") if isinstance(c, dict) else "?")
        desc = getattr(c, "description", c.get("description", "") if isinstance(c, dict) else "")
        lv   = getattr(c, "level",   1)
        morale = getattr(c, "morale", 75)
        inj  = getattr(c, "injured", False)
        rc   = RARITY_COL.get(rar, TEXT_MUTED)

        dy = y + 4

        # Name + rarity banner
        nm_s = sf.render(nm, True, rc)
        surface.blit(nm_s, (DX, dy))
        rar_s = sm.render(f"[{rar.upper()}]  Lv{lv}  {role.title()}", True, rc)
        surface.blit(rar_s, (DX, dy + 14)); dy += 30

        # ── Avatar (left of detail) ───────────────────────────────────────────
        AVW = 80
        self._draw_crew_avatar(surface, c, DX + AVW // 2, dy + 50, size=AVW)

        # ── Stats bars (right of avatar) ──────────────────────────────────────
        stats_x   = DX + AVW + 8
        stats_bw  = DW - AVW - 12
        stat_keys = [
            ("piloting",    "Pilot",   (80,  180, 255)),
            ("gunnery",     "Guns",    (255, 100,  60)),
            ("engineering", "Eng",     (100, 220, 120)),
            ("repair",      "Repair",  (200, 200,  80)),
            ("combat",      "Combat",  (220,  80,  80)),
        ]
        raw_stats = getattr(c, "stats", c if isinstance(c, dict) else {}) if isinstance(c, dict) else getattr(c, "stats", {})
        # For dict-based hired crew, stats are direct keys
        if isinstance(c, dict):
            raw_stats = c
        sy = dy
        for key, label, bar_col in stat_keys:
            if isinstance(c, dict):
                val = c.get(key, c.get("combat", 0))
            else:
                val = getattr(c, "stats", {}).get(key, 0)
                # Add gear bonus
                gear_bonus = c._gear_stat_bonus(key) if hasattr(c, "_gear_stat_bonus") else 0
                if gear_bonus:
                    # show base+bonus
                    val_disp = f"{val}+{gear_bonus}"
                    val_draw = val + gear_bonus
                else:
                    val_disp = str(val)
                    val_draw = val
                val = val_draw
            lbl_s = sm.render(f"{label:<6}", True, TEXT_MUTED)
            surface.blit(lbl_s, (stats_x, sy))
            frac = min(1.0, val / 40.0)
            pygame.draw.rect(surface, (30, 30, 45),
                             (stats_x + 42, sy + 1, stats_bw - 44, 7), border_radius=2)
            if frac > 0:
                pygame.draw.rect(surface, bar_col,
                                 (stats_x + 42, sy + 1, max(4, int((stats_bw - 44) * frac)), 7),
                                 border_radius=2)
            val_t = sm.render(str(val), True, TEXT_MAIN)
            surface.blit(val_t, (stats_x + stats_bw - val_t.get_width() - 2, sy))
            sy += 14

        # Morale + injury indicator
        morale_col = SUCCESS if morale > 60 else (WARNING if morale > 30 else DANGER)
        mo_t = sm.render(f"Morale: {morale}%{'  [INJURED]' if inj else ''}", True,
                         morale_col if not inj else DANGER)
        surface.blit(mo_t, (stats_x, sy)); sy += 14

        dy = max(dy + AVW + 14, sy + 4)
        pygame.draw.line(surface, (35, 42, 60), (DX, dy), (DX + DW, dy)); dy += 6

        # ── Quirks ────────────────────────────────────────────────────────────
        q_hdr = sf.render("QUIRKS", True, (200, 200, 80))
        surface.blit(q_hdr, (DX, dy)); dy += 13
        role_quirks = CREW_QUIRKS_BY_ROLE.get(role, [])
        # Assign two deterministic quirks per crew member from their name hash
        name_hash   = sum(ord(ch) for ch in nm)
        chosen_idxs = [(name_hash % len(role_quirks))] if role_quirks else []
        if len(role_quirks) > 1:
            chosen_idxs.append((name_hash * 7 + 3) % len(role_quirks))
        shown = set()
        for qi in chosen_idxs:
            if qi in shown or qi >= len(role_quirks):
                continue
            shown.add(qi)
            qname, qdesc, qpos = role_quirks[qi]
            qcol = SUCCESS if qpos else DANGER
            qn_t = sm.render(f"✦ {qname}", True, qcol)
            surface.blit(qn_t, (DX + 2, dy)); dy += 12
            qd_t = sm.render(f"  {qdesc[:52]}", True, TEXT_MUTED)
            surface.blit(qd_t, (DX + 2, dy)); dy += 12
        if not chosen_idxs:
            no_q = sm.render("No quirks known.", True, TEXT_MUTED)
            surface.blit(no_q, (DX + 2, dy)); dy += 14

        pygame.draw.line(surface, (35, 42, 60), (DX, dy), (DX + DW, dy)); dy += 6

        # ── Equipment slots ───────────────────────────────────────────────────
        eq_hdr = sf.render("EQUIPMENT", True, ACCENT)
        surface.blit(eq_hdr, (DX, dy)); dy += 13

        equipment = getattr(c, "equipment", {}) if not isinstance(c, dict) else {}
        self._roster_gear_rects   = {}
        self._roster_unequip_rects = {}

        inv = getattr(self, "_gear_inventory", [])

        SLOT_LABELS = {"head": "HEAD", "body": "BODY", "tool": "TOOL"}
        for slot, slot_lbl in SLOT_LABELS.items():
            if dy > sh - 40:
                break
            gear_id  = equipment.get(slot)
            gear_def = next((g for g in CREW_GEAR_ITEMS if g["id"] == gear_id), None) if gear_id else None

            row_r = pygame.Rect(DX, dy, DW, 22)
            pygame.draw.rect(surface, (16, 22, 36), row_r)
            pygame.draw.rect(surface, BORDER, row_r, 1)

            # Slot label
            slbl_t = sm.render(f"{slot_lbl}:", True, TEXT_MUTED)
            surface.blit(slbl_t, (DX + 3, dy + 4))

            if gear_def:
                tint = gear_def.get("avatar_tint", (200, 200, 200))
                gn_t = sm.render(gear_def["name"][:20], True, tint)
                surface.blit(gn_t, (DX + 36, dy + 4))
                # stat summary
                stat_str = "  ".join(f"{'+' if v>0 else ''}{v} {k[:3]}"
                                     for k, v in gear_def.get("stats", {}).items())
                st_t = sm.render(stat_str[:28], True, TEXT_MUTED)
                surface.blit(st_t, (DX + 36, dy + 14 - 3))
                # Unequip button
                ur = pygame.Rect(DX + DW - 50, dy + 3, 46, 16)
                pygame.draw.rect(surface, (40, 20, 20), ur)
                pygame.draw.rect(surface, DANGER, ur, 1)
                ut = sm.render("REMOVE", True, DANGER)
                surface.blit(ut, (ur.centerx - ut.get_width() // 2,
                                  ur.centery - ut.get_height() // 2))
                self._roster_unequip_rects[(sel, slot)] = ur
            else:
                emp_t = sm.render("— empty —", True, (60, 60, 80))
                surface.blit(emp_t, (DX + 36, dy + 4))

            dy += 24

        # ── Gear inventory equip buttons ─────────────────────────────────────
        if inv:
            dy += 4
            inv_hdr = sf.render(f"INVENTORY  ({len(inv)} items)", True, ACCENT)
            surface.blit(inv_hdr, (DX, dy)); dy += 13
            self._roster_equip_btns: dict[str, pygame.Rect] = {}
            for gear_id in inv[:6]:
                if dy > sh - 24:
                    break
                gd = next((g for g in CREW_GEAR_ITEMS if g["id"] == gear_id), None)
                if not gd:
                    continue
                # Can this crew equip it?
                can_role = (gd.get("role", "any") in ("any", role))
                can_slot = gd["slot"] not in equipment or equipment.get(gd["slot"]) is None
                tint = gd.get("avatar_tint", (200, 200, 200))
                col2 = tint if can_role else (80, 80, 80)
                gr = pygame.Rect(DX, dy, DW - 54, 18)
                pygame.draw.rect(surface, (14, 18, 30), gr)
                gt = sm.render(f"[{gd['slot'][0].upper()}] {gd['name'][:18]}", True, col2)
                surface.blit(gt, (DX + 2, dy + 2))
                if can_role:
                    equip_r = pygame.Rect(DX + DW - 50, dy, 46, 18)
                    ebg = (15, 50, 15) if can_slot else (30, 30, 30)
                    ebc = SUCCESS if can_slot else (50, 50, 50)
                    pygame.draw.rect(surface, ebg, equip_r)
                    pygame.draw.rect(surface, ebc, equip_r, 1)
                    et = sm.render("EQUIP", True, ebc)
                    surface.blit(et, (equip_r.centerx - et.get_width() // 2,
                                      equip_r.centery - et.get_height() // 2))
                    self._roster_equip_btns[gear_id] = equip_r
                dy += 20

        # ── Station assignment ─────────────────────────────────────────────────
        if hasattr(c, "assigned_station") and dy < sh - 80:
            dy += 4
            pygame.draw.line(surface, (35, 42, 60), (DX, dy), (DX + DW, dy)); dy += 6
            sta_hdr = sf.render("ASSIGN STATION", True, (120, 200, 255))
            surface.blit(sta_hdr, (DX, dy)); dy += 13

            STATION_LABELS = {
                "cockpit":        ("Cockpit",        (80,  180, 255)),
                "gun_turret":     ("Gun Turret",     (255, 100,  60)),
                "engine_room":    ("Engine Room",    (100, 220, 120)),
                "repair_station": ("Repair Station", (200, 200,  80)),
                "drone_bay":      ("Drone Bay",      (255, 160,  40)),
                "brig":           ("Brig",           (220,  80,  80)),
            }
            cur_station = getattr(c, "assigned_station", None)
            self._roster_station_rects = {}
            col_i = 0
            for sid, (slabel, scol) in STATION_LABELS.items():
                if dy > sh - 24:
                    break
                is_cur = (cur_station == sid)
                sr = pygame.Rect(DX + col_i * (DW // 2 + 2), dy, DW // 2, 18)
                bg  = (20, 50, 20) if is_cur else (16, 22, 36)
                bc  = scol if is_cur else (40, 44, 58)
                pygame.draw.rect(surface, bg, sr)
                pygame.draw.rect(surface, bc, sr, 1)
                sl_t = sm.render(("✓ " if is_cur else "") + slabel[:14], True, scol if is_cur else TEXT_MUTED)
                surface.blit(sl_t, (sr.x + 3, sr.y + 3))
                self._roster_station_rects[(sel, sid)] = sr
                col_i = (col_i + 1) % 2
                if col_i == 0:
                    dy += 20


    def _draw_crew_mgmt_tab(self, surface, start_y, panel_w, sh, fleet=None):
        x0 = 14
        y  = start_y
        w  = panel_w - x0 - 10
        sf = pygame.font.SysFont("monospace", 13, bold=True)
        sm = pygame.font.SysFont("monospace", 11)

        # Header
        cr_total = len(self._hired_crew)
        hdr = sf.render(f"CREW MANAGEMENT  ({cr_total} hired  /  cap {self.total_crew_cap})",
                        True, ACCENT)
        surface.blit(hdr, (x0, y)); y += 20

        # Species reference panel
        sp_hdr = sf.render("SPECIES BONUSES", True, TEXT_MUTED)
        surface.blit(sp_hdr, (x0, y)); y += 14
        for sp in CREW_SPECIES:
            icon_s = sm.render(f" [{sp['icon']}] {sp['name']:<8} {sp['bonus']}", True, sp["color"])
            surface.blit(icon_s, (x0, y)); y += 13
        y += 4
        pygame.draw.line(surface, BORDER, (x0, y), (x0 + w, y)); y += 8

        # Crew roster with manage options
        roster_hdr = sf.render("YOUR CREW  (click row to select)", True, ACCENT)
        surface.blit(roster_hdr, (x0, y)); y += 16

        self._crew_fire_rects:   dict[int, pygame.Rect] = {}
        self._crew_train_rects:  dict[int, pygame.Rect] = {}
        self._crew_select_rects: dict[int, pygame.Rect] = {}

        if not self._hired_crew:
            none_t = sm.render("No crew hired. Go to Crew & Quests tab to hire.", True, TEXT_MUTED)
            surface.blit(none_t, (x0, y)); y += 14
        else:
            RARITY_COLORS = {"common": TEXT_MUTED, "uncommon": SUCCESS,
                             "rare": (60,120,255), "epic": (160,60,220)}
            for idx, crew in enumerate(self._hired_crew):
                if y > sh - 100: break
                rc    = RARITY_COLORS.get(crew.get("rarity","common"), TEXT_MUTED)
                sel   = (self._crew_selected == idx)
                row_r = pygame.Rect(x0, y, w - 140, 24)
                pygame.draw.rect(surface, (30,50,30) if sel else PANEL_BG, row_r)
                pygame.draw.rect(surface, SUCCESS if sel else BORDER, row_r, 1)
                species = crew.get("species", "Human")
                sp_entry = next((s for s in CREW_SPECIES if s["name"] == species), CREW_SPECIES[0])
                info = sm.render(
                    f"[{sp_entry['icon']}] {crew['name'][:14]:<14} [{crew['role']}]"
                    f"  Cmbt:{crew.get('combat',5)}",
                    True, sp_entry["color"])
                surface.blit(info, (x0 + 4, y + (24-info.get_height())//2))
                self._crew_select_rects[idx] = row_r

                # Train button
                tr_r = pygame.Rect(x0 + w - 136, y + 2, 60, 20)
                pygame.draw.rect(surface, (20,40,20), tr_r)
                pygame.draw.rect(surface, SUCCESS, tr_r, 1)
                trl = sm.render("Train 200cr", True, SUCCESS)
                surface.blit(trl, (tr_r.centerx - trl.get_width()//2,
                                   tr_r.centery - trl.get_height()//2))
                self._crew_train_rects[idx] = tr_r

                # Fire button
                fr_r = pygame.Rect(x0 + w - 72, y + 2, 60, 20)
                pygame.draw.rect(surface, (40,15,15), fr_r)
                pygame.draw.rect(surface, DANGER, fr_r, 1)
                frl = sm.render("Dismiss", True, DANGER)
                surface.blit(frl, (fr_r.centerx - frl.get_width()//2,
                                   fr_r.centery - frl.get_height()//2))
                self._crew_fire_rects[idx] = fr_r
                y += 26

        # Detail panel if selected
        if self._crew_selected is not None and self._crew_selected < len(self._hired_crew):
            sel_crew = self._hired_crew[self._crew_selected]
            y += 6
            pygame.draw.line(surface, BORDER, (x0, y), (x0+w, y)); y += 6
            det_hdr = sf.render(f"SELECTED: {sel_crew['name']}", True, ACCENT)
            surface.blit(det_hdr, (x0, y)); y += 14
            for k, v in [("Role", sel_crew.get("role","—")),
                         ("Combat", sel_crew.get("combat",5)),
                         ("Stat", sel_crew.get("stat","—")),
                         ("Rarity", sel_crew.get("rarity","common"))]:
                dl = sm.render(f"  {k:<10} {v}", True, TEXT_MUTED)
                surface.blit(dl, (x0, y)); y += 13

    # ── Repair Shop tab ───────────────────────────────────────────────────────
    def _draw_repair_tab(self, surface, start_y, panel_w, sh, fleet=None):
        x0 = 14
        y  = start_y
        w  = panel_w - x0 - 10
        sf = pygame.font.SysFont("monospace", 13, bold=True)
        sm = pygame.font.SysFont("monospace", 11)

        hdr = sf.render("REPAIR SHOP  (2 cr / HP)", True, (60, 220, 220))
        surface.blit(hdr, (x0, y)); y += 20

        shipyard = self.buildings.get("shipyard")
        if not shipyard or not shipyard.is_built():
            lock = sm.render("Build the Shipyard to unlock ship repairs.", True, TEXT_MUTED)
            surface.blit(lock, (x0, y + 10))
            return

        ships = getattr(fleet, "ships", []) if fleet else []
        if not ships:
            no_s = sm.render("No ships in fleet.", True, TEXT_MUTED)
            surface.blit(no_s, (x0, y + 10))
            return

        self._repair_25_rects:   dict[str, pygame.Rect] = {}
        self._repair_full_rects: dict[str, pygame.Rect] = {}
        self._repair_hull_rects: dict[str, pygame.Rect] = {}

        for ship in ships:
            if y > sh - 100: break
            hull_pct = ship.hull / max(ship.max_hull, 1)
            damage   = ship.max_hull - ship.hull
            cost_25  = int(ship.max_hull * 0.25 * 2)
            cost_full = int(damage * 2)
            color    = SUCCESS if hull_pct > 0.5 else (WARNING if hull_pct > 0.25 else DANGER)

            # Ship name + hull bar
            nm = sf.render(f"{ship.custom_name[:20]}  [{ship.ship_class}]", True, TEXT_MAIN)
            surface.blit(nm, (x0, y)); y += 16
            pygame.draw.rect(surface, (60,0,0), (x0, y, w, 8))
            pygame.draw.rect(surface, color, (x0, y, int(w * hull_pct), 8))
            hp_txt = sm.render(f"Hull: {ship.hull:.0f}/{ship.max_hull}  Damage: {damage:.0f}  Cost to fully repair: {cost_full}cr",
                               True, TEXT_MUTED)
            surface.blit(hp_txt, (x0, y + 10)); y += 24

            # Repair buttons row
            r25_r = pygame.Rect(x0, y, 100, 22)
            pygame.draw.rect(surface, (20,60,20), r25_r)
            pygame.draw.rect(surface, SUCCESS, r25_r, 1)
            r25_t = sm.render(f"Repair 25%  {cost_25}cr", True, SUCCESS)
            surface.blit(r25_t, (r25_r.x+4, r25_r.y+4))
            self._repair_25_rects[ship.id] = r25_r

            rfull_r = pygame.Rect(x0 + 106, y, 110, 22)
            can_full = self.can_afford({"credits": cost_full})
            pygame.draw.rect(surface, (20,80,20) if can_full else (40,20,20), rfull_r)
            pygame.draw.rect(surface, SUCCESS if can_full else DANGER, rfull_r, 1)
            rf_t = sm.render(f"Full repair  {cost_full}cr", True, SUCCESS if can_full else DANGER)
            surface.blit(rf_t, (rfull_r.x+4, rfull_r.y+4))
            self._repair_full_rects[ship.id] = rfull_r

            hull_up_r = pygame.Rect(x0 + 222, y, 110, 22)
            can_hull = self.can_afford({"credits": 300})
            pygame.draw.rect(surface, (20,40,60) if can_hull else (40,20,20), hull_up_r)
            pygame.draw.rect(surface, ACCENT if can_hull else DANGER, hull_up_r, 1)
            hu_t = sm.render("+10% Max Hull  300cr", True, ACCENT if can_hull else DANGER)
            surface.blit(hu_t, (hull_up_r.x+4, hull_up_r.y+4))
            self._repair_hull_rects[ship.id] = hull_up_r
            y += 30

    # ── Research Web tab ─────────────────────────────────────────────────────
    def _draw_research_tab(self, surface, start_y, panel_w, sh):
        x0 = 14
        y  = start_y
        w  = panel_w - x0 - 10
        sf = pygame.font.SysFont("monospace", 13, bold=True)
        sm = pygame.font.SysFont("monospace", 10)

        # Points header
        pts = sf.render(
            f"RESEARCH WEB   Points: {self.research_points}   "
            f"Unlocked: {len(self.research_unlocked)}/{len(RESEARCH_NODES)}",
            True, (160, 80, 255))
        surface.blit(pts, (x0, y)); y += 16
        hint = sm.render("Click INVEST to spend 50 pts. No pts? Click to convert 100cr→10pts.",
                         True, TEXT_MUTED)
        surface.blit(hint, (x0, y)); y += 14
        pygame.draw.line(surface, BORDER, (x0, y), (x0+w, y)); y += 6

        lab_built = self.buildings.get("research_lab")
        if not lab_built or not lab_built.is_built():
            lock = sm.render("Build the Research Lab to unlock research.", True, TEXT_MUTED)
            surface.blit(lock, (x0, y+8))
            return

        CAT_COLORS = {
            "weapons": (220, 80, 80),
            "defense": (60, 120, 255),
            "engines": (60, 220, 120),
            "drones":  (255, 180, 40),
            "ships":   (220, 160, 60),
        }
        self._research_invest_rects: dict[str, pygame.Rect] = {}

        current_cat = None
        for node in RESEARCH_NODES:
            nid, name, cat, cost, reqs, desc, unlocks = node
            if y > sh - 60: break

            # Category separator
            if cat != current_cat:
                current_cat = cat
                cat_col = CAT_COLORS.get(cat, ACCENT)
                cat_hdr = sf.render(cat.upper(), True, cat_col)
                surface.blit(cat_hdr, (x0, y)); y += 14

            done     = nid in self.research_unlocked
            invested = self._research_invest_amounts.get(nid, 0)
            # Check prereqs met
            prereqs_met = all(r in self.research_unlocked for r in reqs)
            # Color coding
            if done:
                row_col = (20, 40, 20)
                border_col = SUCCESS
                name_col   = (100, 200, 100)
            elif prereqs_met:
                row_col  = PANEL_BG
                border_col = CAT_COLORS.get(cat, BORDER)
                name_col = TEXT_MAIN
            else:
                row_col  = (20, 15, 20)
                border_col = BORDER
                name_col = TEXT_MUTED

            row_r = pygame.Rect(x0, y, w - 80, 34)
            pygame.draw.rect(surface, row_col, row_r)
            pygame.draw.rect(surface, border_col, row_r, 1)

            nm_s = sm.render(name, True, name_col)
            surface.blit(nm_s, (x0 + 4, y + 3))

            if done:
                status = sm.render("✓ COMPLETE", True, SUCCESS)
                surface.blit(status, (x0 + 4, y + 16))
            else:
                prog_w = int((row_r.width - 8) * min(1.0, invested / max(cost, 1)))
                pygame.draw.rect(surface, (40, 20, 60), (x0+4, y+16, row_r.width-8, 8))
                pygame.draw.rect(surface, (160, 80, 255), (x0+4, y+16, prog_w, 8))
                req_str = f"  req: {', '.join(r[:8] for r in reqs)}" if reqs else ""
                prog_t = sm.render(f"{invested}/{cost} pts{req_str}", True, TEXT_MUTED)
                surface.blit(prog_t, (x0 + 4, y + 26))

            # Invest button
            if not done and prereqs_met:
                inv_r = pygame.Rect(x0 + w - 76, y + 7, 74, 20)
                can_inv = self.research_points >= 50 or self.resources.get("credits", 0) >= 100
                pygame.draw.rect(surface, (20,10,40) if can_inv else (30,20,30), inv_r)
                pygame.draw.rect(surface, (160,80,255) if can_inv else BORDER, inv_r, 1)
                inv_t = sm.render("INVEST", True, (200,120,255) if can_inv else TEXT_MUTED)
                surface.blit(inv_t, (inv_r.centerx - inv_t.get_width()//2,
                                     inv_r.centery - inv_t.get_height()//2))
                self._research_invest_rects[nid] = inv_r
            elif not done:
                # Show prereqs needed
                lock_t = sm.render("🔒 locked", True, DANGER)
                surface.blit(lock_t, (x0 + w - 76, y + 10))

            y += 38

    # ── Trading tab ───────────────────────────────────────────────────────────
    def _draw_trading_tab(self, surface, start_y, panel_w, sh):
        x0 = 14
        y  = start_y
        w  = panel_w - x0 - 10
        sf = pygame.font.SysFont("monospace", 13, bold=True)
        sm = pygame.font.SysFont("monospace", 10)

        # Header
        hdr = sf.render("TRADING  — Build relations, buy & sell resources", True, (60, 220, 160))
        surface.blit(hdr, (x0, y)); y += 18

        trading_post = self.buildings.get("trading_post")
        if not trading_post or not trading_post.is_built():
            lock = sm.render("Build the Trading Post to enable trading with nations.", True, TEXT_MUTED)
            surface.blit(lock, (x0, y + 10))
            return

        # ── Nation selector tabs ──────────────────────────────────────────────
        self._trade_nation_rects: dict[int, pygame.Rect] = {}
        nt_w = w // len(TRADE_NATIONS)
        nx   = x0
        for ni, nation in enumerate(TRADE_NATIONS):
            nr = pygame.Rect(nx, y, nt_w - 2, 18)
            sel = (self._trade_nation_idx == ni)
            pygame.draw.rect(surface, (25,25,45) if sel else PANEL_BG, nr)
            pygame.draw.rect(surface, nation["color"] if sel else BORDER, nr, 1)
            nt = sm.render(nation["name"][:12], True, nation["color"] if sel else TEXT_MUTED)
            surface.blit(nt, (nr.centerx - nt.get_width()//2, nr.y+3))
            self._trade_nation_rects[ni] = nr
            nx += nt_w
        y += 22

        nation = TRADE_NATIONS[self._trade_nation_idx]
        rel    = self._trade_nation_relations.get(nation["id"], 0)
        rel_col = SUCCESS if rel >= 40 else (WARNING if rel >= 0 else DANGER)
        ncol   = nation["color"]

        # Nation info
        info_r = pygame.Rect(x0, y, w, 38)
        pygame.draw.rect(surface, (18,18,35), info_r)
        pygame.draw.rect(surface, ncol, info_r, 1)
        nm_s = sf.render(nation["name"], True, ncol)
        surface.blit(nm_s, (x0 + 6, y + 4))
        desc_s = sm.render(nation["desc"][:60], True, TEXT_MUTED)
        surface.blit(desc_s, (x0 + 6, y + 20))
        # Relation bar
        rel_lbl = sm.render(f"Relation: {rel:+d}", True, rel_col)
        surface.blit(rel_lbl, (x0 + w - 130, y + 6))
        rel_pct = (rel + 100) / 200.0
        pygame.draw.rect(surface, (40,20,20), (x0 + w - 130, y + 20, 120, 8))
        pygame.draw.rect(surface, rel_col, (x0 + w - 130, y + 20, int(120 * rel_pct), 8))
        y += 44

        # ── SELL section ─────────────────────────────────────────────────────
        self._trade_sell_rects: dict[str, pygame.Rect] = {}
        sell_hdr = sf.render("SELL TO NATION", True, (220,160,60))
        surface.blit(sell_hdr, (x0, y)); y += 14
        for buy_item in nation["buys"]:
            res_key = buy_item["resource_key"]
            have    = self.resources.get(res_key, 0)
            price   = buy_item["price_per"]
            amt     = self._trade_sell_amounts.get(res_key, 10)
            earn    = int(amt * price * (1.1 if rel >= 20 else 1.0))
            can_sell = have >= amt
            row_r = pygame.Rect(x0, y, w - 80, 22)
            pygame.draw.rect(surface, PANEL_BG, row_r)
            ri = sm.render(f"{buy_item['name']:<18} have:{have}  sell:{amt}  earn:{earn}cr",
                           True, TEXT_MAIN if can_sell else TEXT_MUTED)
            surface.blit(ri, (x0+4, y+4))
            sell_btn = pygame.Rect(x0 + w - 76, y+2, 74, 18)
            pygame.draw.rect(surface, (20,50,20) if can_sell else (30,20,20), sell_btn)
            pygame.draw.rect(surface, SUCCESS if can_sell else DANGER, sell_btn, 1)
            sb_t = sm.render("SELL x10", True, SUCCESS if can_sell else DANGER)
            surface.blit(sb_t, (sell_btn.centerx - sb_t.get_width()//2,
                                sell_btn.centery - sb_t.get_height()//2))
            self._trade_sell_rects[res_key] = sell_btn
            y += 24

        y += 4
        pygame.draw.line(surface, BORDER, (x0, y), (x0+w, y)); y += 6

        # ── BUY section ──────────────────────────────────────────────────────
        self._trade_buy_rects: dict[str, pygame.Rect] = {}
        buy_hdr = sf.render("BUY FROM NATION", True, (60,200,220))
        surface.blit(buy_hdr, (x0, y)); y += 14
        can_trade = rel >= -20
        for sell_item in nation["sells"]:
            if y > sh - 80: break
            res_key = sell_item.get("cost_resource", "credits")
            price   = sell_item.get("price", 0)
            if rel >= 50:   price = int(price * 0.8)
            elif rel >= 20: price = int(price * 0.9)
            can_buy = can_trade and self.resources.get(res_key, 0) >= price
            row_r = pygame.Rect(x0, y, w - 80, 22)
            pygame.draw.rect(surface, PANEL_BG, row_r)
            ri = sm.render(f"{sell_item['name']:<18}  {sell_item['desc'][:30]}",
                           True, TEXT_MAIN if can_buy else TEXT_MUTED)
            surface.blit(ri, (x0+4, y+4))
            buy_btn = pygame.Rect(x0+w-76, y+2, 74, 18)
            pygame.draw.rect(surface, (20,40,60) if can_buy else (30,20,20), buy_btn)
            pygame.draw.rect(surface, (60,200,220) if can_buy else DANGER, buy_btn, 1)
            bb_t = sm.render(f"{price}{res_key[:2]}", True, (60,200,220) if can_buy else DANGER)
            surface.blit(bb_t, (buy_btn.centerx - bb_t.get_width()//2,
                                buy_btn.centery - bb_t.get_height()//2))
            self._trade_buy_rects[sell_item["id"]] = buy_btn
            y += 24

        y += 4
        pygame.draw.line(surface, BORDER, (x0, y), (x0+w, y)); y += 6

        # ── GIFT section (build relations) ───────────────────────────────────
        self._trade_gift_rects: dict[tuple, pygame.Rect] = {}
        self._gift_nation_btns: list[tuple] = []  # [(nation_id, rect), ...]

        gift_hdr = sf.render("SEND GIFT  (build relations)", True, (80, 200, 255))
        surface.blit(gift_hdr, (x0, y)); y += 16

        # ── Recipient nation picker ───────────────────────────────────────────
        recip_lbl = sm.render("SEND TO:", True, TEXT_MUTED)
        surface.blit(recip_lbl, (x0, y + 3))
        btn_x = x0 + recip_lbl.get_width() + 8
        gift_target_id = getattr(self, "_gift_target_nation_id",
                                 TRADE_NATIONS[self._trade_nation_idx]["id"])
        for gn in TRADE_NATIONS:
            gn_rel = self._trade_nation_relations.get(gn["id"], 0)
            is_sel = (gn["id"] == gift_target_id)
            gb = pygame.Rect(btn_x, y, 80, 20)
            bg_c  = (25, 30, 50) if is_sel else PANEL_BG
            brd_c = gn["color"] if is_sel else BORDER
            pygame.draw.rect(surface, bg_c, gb)
            pygame.draw.rect(surface, brd_c, gb, 2 if is_sel else 1)
            gn_t = sm.render(gn["name"][:10], True, gn["color"] if is_sel else TEXT_MUTED)
            surface.blit(gn_t, (gb.x + 4, gb.centery - gn_t.get_height() // 2))
            self._gift_nation_btns.append((gn["id"], gb))
            btn_x += 84
            if btn_x + 80 > x0 + w:    # wrap to next row if out of space
                btn_x = x0 + recip_lbl.get_width() + 8
                y += 22
        y += 26

        # Recipient info line
        target_nation = next((n for n in TRADE_NATIONS if n["id"] == gift_target_id),
                             TRADE_NATIONS[0])
        tgt_rel = self._trade_nation_relations.get(gift_target_id, 0)
        tgt_rel_col = SUCCESS if tgt_rel >= 40 else (WARNING if tgt_rel >= 0 else DANGER)
        to_s = sm.render(
            f"→ {target_nation['name']}   current relation: {tgt_rel:+d}",
            True, target_nation["color"])
        surface.blit(to_s, (x0, y)); y += 16

        # Gift amount buttons
        for gift_amt, label in [(200, "Small Gift   200cr  +1 rel"),
                                 (500, "Gift         500cr  +2 rel"),
                                 (2000, "Tribute    2000cr  +10 rel")]:
            if y > sh - 60:
                break
            can_gift = self.resources.get("credits", 0) >= gift_amt
            gift_r = pygame.Rect(x0, y, 270, 22)
            pygame.draw.rect(surface, (20, 30, 50) if can_gift else (30, 20, 20), gift_r)
            pygame.draw.rect(surface, (80, 200, 255) if can_gift else DANGER, gift_r, 1)
            gt = sm.render(label, True, (80, 200, 255) if can_gift else DANGER)
            surface.blit(gt, (gift_r.x + 6, gift_r.centery - gt.get_height() // 2))
            self._trade_gift_rects[(gift_target_id, gift_amt)] = gift_r
            y += 26

        # Relation bonuses preview
        y += 4
        bonus_hdr = sf.render("RELATION BONUSES", True, TEXT_MUTED)
        surface.blit(bonus_hdr, (x0, y)); y += 13
        for threshold, bonus in sorted(nation["relation_bonuses"].items()):
            unlocked = rel >= threshold
            col = SUCCESS if unlocked else TEXT_MUTED
            bt = sm.render(f"  {'✓' if unlocked else '○'} At {threshold:+d}: {bonus}", True, col)
            surface.blit(bt, (x0, y)); y += 13


    def _draw_asteroid_view(self, surface: pygame.Surface,
                            ax: int, ay: int, aw: int, ah: int,
                            fleet=None) -> None:
        """Draw the big asteroid base visual on the right panel."""
        t  = self._anim_time
        cx = ax + aw // 2
        cy = ay + ah // 2

        # ── Starfield backdrop ────────────────────────────────────────────────
        rng = self._asteroid_rng
        rng.seed(42)
        for _ in range(120):
            sx = ax + rng.randint(0, aw)
            sy = ay + rng.randint(0, ah)
            sc = rng.randint(50, 200)
            # Slight colour variation for depth
            col = (sc, sc, min(255, sc + 40 + rng.randint(0, 30)))
            surface.set_at((sx, sy), col)
        # A few bright "star" clusters
        rng.seed(77)
        for _ in range(8):
            sx = ax + rng.randint(0, aw)
            sy = ay + rng.randint(0, ah)
            pygame.draw.circle(surface, (240, 240, 255), (sx, sy), 2)

        # ── Asteroid body — improved multi-layer rocky look ──────────────────
        built_count = sum(1 for b in self.buildings.values() if b.is_built())
        base_r = 90 + self.expansion_level * 20

        # Layer 1: shadow/depth blob (slightly larger, darker)
        rng.seed(888)
        shadow_pts = []
        for i in range(16):
            angle = (2 * math.pi * i) / 16
            r = base_r + rng.randint(-10, 14) + 12
            shadow_pts.append((cx + int(r * math.cos(angle + 0.15)),
                                cy + int(r * math.sin(angle + 0.15))))
        pygame.draw.polygon(surface, (28, 22, 18), shadow_pts)

        # Layer 2: main rock body
        rng.seed(999)
        pts_count = 18
        asteroid_pts = []
        for i in range(pts_count):
            angle = (2 * math.pi * i) / pts_count
            r = base_r + rng.randint(-20, 20)
            asteroid_pts.append((cx + int(r * math.cos(angle)),
                                  cy + int(r * math.sin(angle))))
        pygame.draw.polygon(surface, (62, 50, 40), asteroid_pts)

        # Layer 3: lighter face (slightly smaller, offset up-left to fake lighting)
        rng.seed(777)
        inner_pts = []
        for i in range(pts_count):
            angle = (2 * math.pi * i) / pts_count
            r = (base_r - 8) + rng.randint(-12, 12)
            inner_pts.append((cx - 6 + int(r * math.cos(angle)),
                               cy - 5 + int(r * math.sin(angle))))
        pygame.draw.polygon(surface, (78, 63, 50), inner_pts)

        # Outline / ridge
        pygame.draw.polygon(surface, (95, 78, 62), asteroid_pts, 3)

        # Crater pits — circles with shading
        CRATERS = [
            (cx - 22, cy + 14, 11, (40, 32, 26)),
            (cx + 28, cy - 18, 8,  (44, 35, 28)),
            (cx - 6,  cy - 28, 6,  (38, 30, 24)),
            (cx + 12, cy + 30, 10, (42, 34, 27)),
            (cx - 30, cy - 10, 7,  (45, 37, 30)),
        ]
        for crx, cry, crad, ccol in CRATERS:
            if math.hypot(crx - cx, cry - cy) < base_r * 0.85:
                pygame.draw.circle(surface, ccol, (crx, cry), crad)
                pygame.draw.circle(surface, (55, 44, 36), (crx, cry), crad, 1)
                # Highlight rim top-left
                pygame.draw.arc(surface, (90, 74, 60),
                                (crx - crad, cry - crad, crad * 2, crad * 2),
                                math.pi * 0.75, math.pi * 1.5, 1)

        # Rock texture / surface detail (random small pebble bumps)
        rng.seed(7)
        for _ in range(18):
            hx = cx + rng.randint(-int(base_r * 0.7), int(base_r * 0.7))
            hy = cy + rng.randint(-int(base_r * 0.7), int(base_r * 0.7))
            if math.hypot(hx - cx, hy - cy) < base_r * 0.75:
                hl = rng.randint(2, 5)
                pygame.draw.circle(surface, (98, 80, 65), (hx, hy), hl)
                # tiny dark shadow dot
                pygame.draw.circle(surface, (40, 32, 26), (hx + 1, hy + 1), hl - 1)

        # ── Buildings as surface modules ──────────────────────────────────────
        MODULE_COLORS = {
            "shipyard":       (60, 180, 220),
            "barracks":       (200, 140, 60),
            "armory":         (200, 80, 80),
            "warehouse":      (140, 200, 80),
            "fuel_depot":     (220, 180, 60),
            "research_lab":   (180, 80, 220),
            "comm_tower":     (80, 220, 220),
            "black_market":   (180, 60, 140),
            "cantina":        (220, 160, 60),
            "trading_post":   (60, 200, 160),
            "defense_turrets":(200, 60, 60),
        }
        building_list = list(self.buildings.values())
        for i, building in enumerate(building_list):
            if not building.is_built():
                continue
            mod_angle = (2 * math.pi * i / len(building_list)) - math.pi / 2
            mod_r = base_r + 8
            mx2 = cx + int(mod_r * math.cos(mod_angle))
            my2 = cy + int(mod_r * math.sin(mod_angle))
            col = MODULE_COLORS.get(building.building_id, ACCENT)
            mod_w = 16 + building.level * 4
            mod_h = 10 + building.level * 3
            mod_rect = pygame.Rect(mx2 - mod_w // 2, my2 - mod_h // 2, mod_w, mod_h)
            pygame.draw.rect(surface, col, mod_rect)
            pygame.draw.rect(surface, WHITE, mod_rect, 1)
            for lv in range(building.level):
                pygame.draw.circle(surface, WHITE,
                                   (mod_rect.x + 3 + lv * 5, mod_rect.bottom - 3), 2)
            nm = self._font_sm.render(building.name[:4], True, WHITE)
            surface.blit(nm, (mx2 - nm.get_width() // 2, my2 - mod_h // 2 - 12))

        # ── Docking arms ──────────────────────────────────────────────────────
        dock_count = min(built_count + 1, 4)
        for d in range(dock_count):
            arm_angle = (2 * math.pi * d / dock_count) + math.pi / 6
            ax0 = cx + int((base_r - 10) * math.cos(arm_angle))
            ay0 = cy + int((base_r - 10) * math.sin(arm_angle))
            ax1 = cx + int((base_r + 35) * math.cos(arm_angle))
            ay1 = cy + int((base_r + 35) * math.sin(arm_angle))
            pygame.draw.line(surface, (100, 140, 180), (ax0, ay0), (ax1, ay1), 3)
            pygame.draw.circle(surface, (60, 100, 160), (ax1, ay1), 6)
            pygame.draw.circle(surface, (100, 160, 220), (ax1, ay1), 6, 1)

        # ── Patrol fleet orbiting ─────────────────────────────────────────────
        if fleet:
            patrol_ships = [s for s in getattr(fleet, "ships", [])
                            if s is not getattr(fleet, "active_ship", None)]
            for pi, ps in enumerate(patrol_ships[:5]):
                orbit_r   = base_r + 55 + pi * 22
                orbit_spd = 0.3 + pi * 0.08
                pa = t * orbit_spd + pi * (2 * math.pi / max(len(patrol_ships), 1))
                px2 = cx + int(orbit_r * math.cos(pa))
                py2 = cy + int(orbit_r * math.sin(pa))
                col = getattr(ps, "color_scheme", (80, 160, 255))
                fw, fh = 14, 9
                forward = pa + math.pi / 2
                pts = [
                    (px2 + int(fw // 2 * math.cos(forward)),
                     py2 + int(fw // 2 * math.sin(forward))),
                    (px2 + int(fh // 2 * math.cos(forward + 2.3)),
                     py2 + int(fh // 2 * math.sin(forward + 2.3))),
                    (px2 + int(fh // 2 * math.cos(forward - 2.3)),
                     py2 + int(fh // 2 * math.sin(forward - 2.3))),
                ]
                pygame.draw.polygon(surface, col, pts)
                trail_a = pa - math.pi / 2
                tx2 = px2 + int(8 * math.cos(trail_a))
                ty2 = py2 + int(8 * math.sin(trail_a))
                pygame.draw.line(surface, (80, 120, 200), (px2, py2), (tx2, ty2), 1)
                nm = self._font_sm.render(
                    getattr(ps, "custom_name", ps.name)[:10], True, (120, 160, 220))
                surface.blit(nm, (px2 - nm.get_width() // 2, py2 + 8))

        # ── Base name + level label ───────────────────────────────────────────
        lvl_names = ["Asteroid Outpost", "Hidden Station", "Pirate Fortress"]
        lvl_name  = lvl_names[min(self.expansion_level, 2)]
        n_surf = self._font.render(lvl_name, True, TEXT_MAIN)
        surface.blit(n_surf, (cx - n_surf.get_width() // 2, cy + base_r + 48))

        # Pulsing danger ring when raiders incoming / active
        if self.raiders._raid_warning or (self.raiders.active_wave and
                                          self.raiders.active_wave.active):
            pulse = abs(math.sin(t * 6)) * 0.7 + 0.3
            rc2   = int(220 * pulse)
            pygame.draw.circle(surface, (rc2, 20, 20), (cx, cy), base_r + 28, 2)
            pygame.draw.circle(surface, (rc2 // 2, 10, 10), (cx, cy), base_r + 18, 1)

        # ── Crew capacity label ───────────────────────────────────────────────
        cap_lbl = self._font_sm.render(
            f"Crew Cap: {self.total_crew_cap}  (x{self.asteroid_count} asteroids)",
            True, TEXT_MUTED)
        surface.blit(cap_lbl, (cx - cap_lbl.get_width() // 2, cy + base_r + 65))

        # ── BUY ASTEROID button ───────────────────────────────────────────────
        btn_w, btn_h = 280, 34
        btn_x = cx - btn_w // 2
        btn_y = cy + base_r + 80
        can_buy = self.can_afford({"credits": 2000, "metal": 500})
        btn_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
        pygame.draw.rect(surface, (20, 35, 20) if can_buy else (35, 20, 20), btn_rect,
                         border_radius=4)
        pygame.draw.rect(surface, SUCCESS if can_buy else DANGER, btn_rect, 1,
                         border_radius=4)
        btn_txt = self._font_sm.render(
            "🪨 BUY ASTEROID  +50 crew cap  (2000cr+500mt)",
            True, SUCCESS if can_buy else DANGER)
        surface.blit(btn_txt, (btn_rect.centerx - btn_txt.get_width() // 2,
                                btn_rect.centery - btn_txt.get_height() // 2))
        self._buy_asteroid_btn = btn_rect

    def _draw_building_detail(self, surface: pygame.Surface, b) -> None:
        """Small info panel at bottom-left showing selected building details."""
        from base.buildings import BUILDING_DEFINITIONS
        effects = {}
        for bd in BUILDING_DEFINITIONS:
            if bd["id"] == b.building_id:
                effects = bd.get("effects", {})
                break

        pw, ph = 560, 80
        px, py = 20, SCREEN_HEIGHT - 130
        pygame.draw.rect(surface, (15, 15, 30), (px, py, pw, ph))
        pygame.draw.rect(surface, ACCENT if b.is_built() else BORDER, (px, py, pw, ph), 1)

        name_s = self._font.render(
            f"{b.name}  (Lv {b.level}/{b.max_level})", True, TEXT_MAIN)
        surface.blit(name_s, (px + 8, py + 6))

        action_hint = ""
        if not b.is_built():
            cost = b.upgrade_cost()
            cost_str = "  |  ".join(f"{v} {k}" for k, v in cost.items())
            can = self.can_afford(cost)
            color = SUCCESS if can else DANGER
            action_hint = f"Click again to BUILD  —  Cost: {cost_str}"
        elif b.can_upgrade():
            cost = b.upgrade_cost()
            cost_str = "  |  ".join(f"{v} {k}" for k, v in cost.items())
            can = self.can_afford(cost)
            color = WARNING if can else DANGER
            action_hint = f"Click again to UPGRADE  —  Cost: {cost_str}"
        else:
            color = SUCCESS
            action_hint = "MAX LEVEL"

        hint_s = self._font_sm.render(action_hint, True, color)
        surface.blit(hint_s, (px + 8, py + 26))

        eff_text = effects.get(b.level, effects.get(1, ""))
        if eff_text:
            eff_s = self._font_sm.render(f"Effect: {eff_text}", True, TEXT_MUTED)
            surface.blit(eff_s, (px + 8, py + 44))

    def _draw_nav_bar(self, surface: pygame.Surface) -> None:
        """Bottom navigation bar with action buttons."""
        self._nav_rects: dict[str, pygame.Rect] = {}
        bar_h  = 44
        bar_y  = SCREEN_HEIGHT - bar_h
        pygame.draw.rect(surface, (10, 10, 25),
                         (0, bar_y - 2, SCREEN_WIDTH, bar_h + 2))
        pygame.draw.line(surface, BORDER,
                         (0, bar_y - 2), (SCREEN_WIDTH, bar_y - 2))

        cantina_built = self._cantina_built()
        # Crew button is highlighted (gold) when cantina is available
        buttons = [
            ("galaxy_map",   "🗺  Galaxy Map  [G]",  ACCENT,             False),
            ("upgrade_tree", "⬆  Upgrades    [U]",   (160,  80, 220),    False),
            ("fleet_orders", "🚀  Fleet       [F]",   (60,  200,  80),    False),
            ("crew_roster",  "👥  CREW HQ    [C]",    (255, 200,  40) if cantina_built else TEXT_MUTED,
                                                        cantina_built),
            ("settings",     "⚙  Settings    [S]",   TEXT_MUTED,         False),
        ]
        bw  = SCREEN_WIDTH // len(buttons)
        for i, (action, label, col, highlight) in enumerate(buttons):
            bx   = i * bw
            rect = pygame.Rect(bx, bar_y, bw - 2, bar_h)
            bg   = (35, 28, 8) if highlight else PANEL_BG
            bdr  = col if highlight else BORDER
            pygame.draw.rect(surface, bg, rect)
            pygame.draw.rect(surface, bdr, rect, 2 if highlight else 1)
            txt = self._font.render(label, True, col)
            surface.blit(txt, (bx + bw // 2 - txt.get_width() // 2,
                                bar_y + bar_h // 2 - txt.get_height() // 2))
            self._nav_rects[action] = rect

    @staticmethod
    def _wrap_text(text: str, max_width: int, font: pygame.font.Font) -> list[str]:
        words = text.split()
        lines = []
        current = ""
        for word in words:
            test = current + (" " if current else "") + word
            if font.size(test)[0] <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines

    # ── Serialization ─────────────────────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "resources":       self.resources,
            "base_hp":         self.base_hp,
            "max_base_hp":     self.max_base_hp,
            "expansion_level": self.expansion_level,
            "buildings":       {bid: b.to_dict()
                                for bid, b in self.buildings.items()},
            "raiders":         self.raiders.to_dict(),
            "hired_crew":      self._hired_crew,
        }

    def load_from_dict(self, data: dict) -> None:
        self.resources.update(data.get("resources", {}))
        self.base_hp         = data.get("base_hp", 500)
        self.max_base_hp     = data.get("max_base_hp", 500)
        self.expansion_level = data.get("expansion_level", 0)
        for bid, bd in data.get("buildings", {}).items():
            if bid in self.buildings:
                self.buildings[bid].level = bd.get("level", 0)
        self.raiders.load_from_dict(data.get("raiders", {}))
        self._hired_crew = data.get("hired_crew", [])

    # ── Bay Control helpers ───────────────────────────────────────────────────
    def _get_player_carrier(self, fleet) -> "Ship | None":
        """Return the first fleet ship with a bay (carrier), or None."""
        if not fleet:
            return None
        for ship in fleet.ships:
            if getattr(ship, "bay", None) is not None:
                return ship
        return None

    def _draw_bay_tab(self, surface: pygame.Surface, start_y: int,
                      panel_w: int, sh: int, fleet=None) -> None:
        """Bay Control: load/unload ships, repair, view bay status."""
        from settings import (PANEL_BG, BORDER, TEXT_MAIN, TEXT_MUTED,
                               SUCCESS, WARNING, DANGER)
        x0 = 14
        y  = start_y
        w  = panel_w - x0 - 10
        sf = pygame.font.SysFont("monospace", 13, bold=True)
        sm = pygame.font.SysFont("monospace", 10)

        # ── Header ───────────────────────────────────────────────────────────
        hdr = sf.render("BAY CONTROL", True, (255, 200, 60))
        surface.blit(hdr, (x0, y)); y += 18

        carrier = self._get_player_carrier(fleet)
        if carrier is None:
            no_c = sm.render(
                "No carrier in fleet.  Buy a carrier-class ship to unlock Bay Control.",
                True, TEXT_MUTED)
            surface.blit(no_c, (x0, y + 8))
            return

        bay = carrier.bay
        stats = bay.stats()

        # ── Carrier info row ─────────────────────────────────────────────────
        ci = sf.render(
            f"{carrier.custom_name}   Bay: {stats['docked']}/{stats['capacity']}  "
            f"crew in bay: {stats['total_crew']}",
            True, (80, 220, 200))
        surface.blit(ci, (x0, y)); y += 16

        # Hull bar for carrier
        hull_pct = carrier.hull / max(carrier.max_hull, 1)
        bar_w = w - 80
        pygame.draw.rect(surface, (30, 30, 40), (x0, y, bar_w, 6))
        bar_col = (80, 200, 80) if hull_pct > 0.5 else (220, 160, 40) if hull_pct > 0.25 else (220, 60, 60)
        pygame.draw.rect(surface, bar_col, (x0, y, int(bar_w * hull_pct), 6))
        hl_t = sm.render(f"Hull {int(carrier.hull)}/{carrier.max_hull}", True, TEXT_MUTED)
        surface.blit(hl_t, (x0 + bar_w + 6, y - 2)); y += 12

        # Launch thresholds hint
        launch_pct = float(carrier._data.get("bay_launch_hull_pct", 0.25))
        thresholds = [int((1 - launch_pct * (i + 1)) * 100)
                      for i in range(int(1 / launch_pct))]
        th_str = "  ".join(f"{t}%" for t in thresholds)
        th_t = sm.render(f"Auto-launch at hull: {th_str}", True, (200, 160, 60))
        surface.blit(th_t, (x0, y)); y += 14

        pygame.draw.line(surface, BORDER, (x0, y), (x0 + w, y)); y += 6

        # ── Docked ships ─────────────────────────────────────────────────────
        docked_hdr = sf.render("DOCKED SHIPS", True, (80, 220, 200))
        surface.blit(docked_hdr, (x0, y)); y += 14

        self._bay_unload_btns = []
        if not bay.docked_ships:
            no_s = sm.render("Bay empty — load ships from fleet below.", True, TEXT_MUTED)
            surface.blit(no_s, (x0 + 4, y)); y += 16
        else:
            for berth_idx, berth in enumerate(bay.berths):
                if y > sh - 80:
                    break
                ship = berth.ship
                if ship is None:
                    # Empty berth indicator
                    eb_r = pygame.Rect(x0, y, w - 4, 22)
                    pygame.draw.rect(surface, (18, 18, 28), eb_r)
                    pygame.draw.rect(surface, BORDER, eb_r, 1, border_radius=2)
                    et = sm.render(f"Berth {berth_idx + 1}  [EMPTY]", True, (50, 50, 70))
                    surface.blit(et, (eb_r.x + 6, eb_r.centery - et.get_height() // 2))
                    y += 26
                    continue
                # Filled berth
                h_pct = ship.hull / max(ship.max_hull, 1)
                row_col = (60, 200, 80) if h_pct > 0.5 else (200, 140, 40) if h_pct > 0.25 else DANGER
                row_r = pygame.Rect(x0, y, w - 80, 22)
                pygame.draw.rect(surface, (20, 30, 20), row_r)
                pygame.draw.rect(surface, row_col, row_r, 1)
                # Ship name + class
                st = sm.render(
                    f"Berth {berth_idx + 1}  {ship.custom_name}  "
                    f"[{ship.ship_class}]  Hull {int(h_pct * 100)}%  "
                    f"Crew {len(ship.crew)}/{ship.crew_slots}",
                    True, TEXT_MAIN)
                surface.blit(st, (row_r.x + 4, row_r.centery - st.get_height() // 2))
                # Hull mini-bar inside row
                bar_inner_w = row_r.width - 10
                pygame.draw.rect(surface, (30, 30, 30),
                                 (row_r.x + 4, row_r.bottom - 4, bar_inner_w, 3))
                pygame.draw.rect(surface, row_col,
                                 (row_r.x + 4, row_r.bottom - 4,
                                  int(bar_inner_w * h_pct), 3))
                # UNLOAD button
                ub_r = pygame.Rect(x0 + w - 76, y + 2, 74, 18)
                pygame.draw.rect(surface, (30, 40, 60), ub_r)
                pygame.draw.rect(surface, (80, 160, 255), ub_r, 1)
                ub_t = sm.render("UNLOAD", True, (80, 160, 255))
                surface.blit(ub_t, (ub_r.centerx - ub_t.get_width() // 2,
                                    ub_r.centery - ub_t.get_height() // 2))
                self._bay_unload_btns.append((ship, ub_r))
                y += 26

        pygame.draw.line(surface, BORDER, (x0, y), (x0 + w, y)); y += 6

        # ── Repair All button ────────────────────────────────────────────────
        repair_need = stats["repair_need"]
        repair_cost = stats["repair_cost"]
        metal_have  = self.resources.get("metal", 0)
        can_repair  = repair_need > 0 and metal_have >= repair_cost
        rep_r = pygame.Rect(x0, y, 200, 22)
        pygame.draw.rect(surface, (20, 40, 20) if can_repair else (25, 20, 20), rep_r)
        pygame.draw.rect(surface, SUCCESS if can_repair else DANGER, rep_r, 1)
        rep_lbl = sm.render(
            f"Repair All  ({repair_need} HP  {repair_cost} metal)",
            True, SUCCESS if can_repair else DANGER)
        surface.blit(rep_lbl, (rep_r.x + 4, rep_r.centery - rep_lbl.get_height() // 2))
        self._bay_repair_btn = rep_r if can_repair else None
        y += 28

        pygame.draw.line(surface, BORDER, (x0, y), (x0 + w, y)); y += 6

        # ── Fleet ships available to load ────────────────────────────────────
        avail_hdr = sf.render("FLEET SHIPS  (click LOAD to dock)", True, (255, 200, 60))
        surface.blit(avail_hdr, (x0, y)); y += 14

        self._bay_load_btns = []
        if not fleet:
            surface.blit(sm.render("No fleet available.", True, TEXT_MUTED), (x0, y))
            return

        loadable = [s for s in fleet.ships
                    if s is not carrier
                    and not getattr(s, "_in_bay", False)]
        if not loadable:
            surface.blit(sm.render("No other fleet ships to load.", True, TEXT_MUTED),
                         (x0, y)); y += 14
        else:
            for ship in loadable:
                if y > sh - 40:
                    break
                h_pct = ship.hull / max(ship.max_hull, 1)
                can_load = not bay.is_full
                row_r2 = pygame.Rect(x0, y, w - 80, 22)
                pygame.draw.rect(surface, PANEL_BG, row_r2)
                pygame.draw.rect(surface, BORDER if can_load else (40, 40, 40), row_r2, 1)
                st2 = sm.render(
                    f"{ship.custom_name}  [{ship.ship_class}]  "
                    f"Hull {int(h_pct * 100)}%  Crew {len(ship.crew)}",
                    True, TEXT_MAIN if can_load else TEXT_MUTED)
                surface.blit(st2, (row_r2.x + 4, row_r2.centery - st2.get_height() // 2))
                lb_r = pygame.Rect(x0 + w - 76, y + 2, 74, 18)
                pygame.draw.rect(surface, (20, 40, 20) if can_load else (25, 20, 20), lb_r)
                pygame.draw.rect(surface, SUCCESS if can_load else (50, 50, 50), lb_r, 1)
                lb_t = sm.render("LOAD", True, SUCCESS if can_load else (50, 50, 50))
                surface.blit(lb_t, (lb_r.centerx - lb_t.get_width() // 2,
                                    lb_r.centery - lb_t.get_height() // 2))
                if can_load:
                    self._bay_load_btns.append((ship, lb_r))
                y += 26

        # ── Bay status footer ────────────────────────────────────────────────
        foot = sm.render(
            f"Total bay crew: {stats['total_crew']}  |  "
            f"Bay hull: {stats['total_hull']}/{stats['max_hull']}  |  "
            f"Metal on hand: {metal_have}",
            True, TEXT_MUTED)
        surface.blit(foot, (x0, max(y, sh - 44)))
