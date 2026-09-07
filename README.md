# Space Pirates 🏴‍☠️

> **Brought to life by Deklin (DekSarex), with a little help from IBM Bob.**

A top-down 2D space pirate game built with Python and Pygame. Command your ship, raid enemies, board and capture vessels, build your home base, and push through a galaxy full of faction wars, escalating raider waves, and sector bosses.

---

## Features

### Combat
- **Real-time space combat** with full parallax starfield, nebula clouds, asteroid fields, and space debris
- **Board any ship** — when enemy shields are broken *or* hull drops below 25%, initiate room-by-room boarding combat
- **Drone system** — launch combat, repair, scout, and bomb drones mid-fight
- **Carrier class** — deploy escort fighters from your bay during battle
- **Status effects** — EMP slow, weapons offline, shield drain inside nebula zones
- **Loot floaters** — credits and weapon drops shown in real time above destroyed ships

### Ships & Crew
- **14 ship classes** — Fighter, Interceptor, Scout, Corvette, Gunship, Destroyer, Stealth, Freighter, Mining Barge, Assault Transport, Carrier, Pirate Carrier, Dreadnought, Battlecruiser
- **6-tier rarity system** — Common → Uncommon → Rare → Epic → Legendary → Secret
- **Deep crew system** — stats, XP levelling, role specializations, morale, injury recovery, per-role quirks
- **Crew gear** — equippable Head / Body / Tool slot items that boost stats and alter portraits
- **Boarding combat** — room-by-room, turn-based; capture crew, take hostages, strip for parts, or keep the ship

### Home Base
- **11 upgradeable buildings** — Armory, Defense Turrets, Cantina, Research Lab, Shipyard, Warehouse, Trading Post, Barracks, Comm Tower, Fuel Depot, Black Market
- **Raider waves** — 5-minute warning countdown in the HUD corner; fight off waves in full combat when they arrive
- **Crew & Quests tab** — hire mercenaries, send ships on side quests (10 quests across 5 difficulty tiers) once the Cantina is built
- **Research web** — unlock new weapons, ships, and upgrades through a node-based tech tree
- **Trading system** — buy and sell resources with 5 factions; build relations for discounts and exclusive items
- **Cargo ship routes** — automated trade runs earn passive income

### Galaxy & Progression
- **Sector map** with nation zones, nebula sectors, mining depots, and boss encounters
- **Full roguelite meta-progression** — permanent upgrades persist between runs; spend points on hull, speed, damage, drone slots, and more
- **Wanted level** — rises as you raid; affects raider frequency and faction hostility
- **Dynamic economy** — prices shift by sector type and faction relation
- **Pirate title system** tied to kill count and notoriety
- **Photo Mode** (F12) — freeze frame, cycle filters, screenshot

---

## Quick Start

```bash
pip install -r requirements.txt
python main.py
```

**Requires:** Python 3.9+ · Pygame 2.5+

---

## Controls

| Key / Input | Action |
|---|---|
| `WASD` / Arrow keys | Move ship |
| Mouse aim + Left click | Fire weapons |
| `B` | Board nearest weakened enemy |
| `SPACE` | Pause / resume combat |
| `Y` | Toggle autopilot (cockpit AUTO) |
| `R` | Raid nearest cargo ship |
| `G` | Open galaxy map (from base) |
| `U` | Upgrade tree |
| `F` | Fleet orders |
| `C` | Crew HQ |
| `ESC` | Pause / back |
| `F12` | Toggle Photo Mode |
| Right-click (combat) | Open drone deploy menu |

---

## Project Structure

```
spacePirates/
├── main.py               # Entry point
├── settings.py           # Global constants and colour palette
├── core/                 # Game loop, state machine, save/load, audio, particles
├── entities/             # Ship, Crew, Weapon, Drone, Projectile classes
├── combat/               # SpaceCombat engine, AI, boarding, drones, status effects
├── fleet/                # Fleet manager, orders, bay system, scrapper
├── base/                 # HomeBase, buildings, raiders, crew/quests UI
├── world/                # Galaxy map, sector definitions, events, economy
├── factions/             # Faction definitions, reputation manager
├── quests/               # Story quests, procedural job board, bounty board
├── progression/          # Meta-upgrades, rarity system, pirate titles
├── ui/                   # HUD, menus, split-screen layout, codex, photo mode
├── data/                 # JSON data — ships, crew, weapons, etc.
└── assets/               # Sprites, sounds, music (add your own — see below)
```

---

## Adding Audio Assets

The game runs silently if no audio files are present. Drop files into `assets/sounds/` and `assets/music/`:

**Music** (`assets/music/`): `menu.ogg` · `base.ogg` · `combat.ogg` · `exploration.ogg` · `graveyard.ogg` · `peaceful.ogg`

**SFX** (`assets/sounds/`): `laser.wav` · `missile.wav` · `explosion.wav` · `hull_hit.wav` · `shield_hit.wav` · `click.wav` · `loot.wav` · `levelup.wav` · `boarding.wav` · `quest.wav`

---

## Settings

Access via the **Settings** button at the bottom of the base screen. Available options:

- Combat speed (0.5× – 2.0×)
- Colorblind mode · Font size (S/M/L)
- Damage numbers · Screen shake · Particle effects · Show FPS
- Music & SFX volume
- Minimap · Enemy HP bars · Auto-pause on raid
- Difficulty (Easy / Normal / Hard)
- Auto-save interval (Off / 2 min / 5 min / 10 min)
- **Crosshair style** (cross / dot / circle / none)
- **HUD opacity** (50% – 100%)
- **Radar zoom** (×2 / ×1 / ½)
- **Auto-collect debris** · **Show hints** · **Boarding auto-attack**

---

## License

This project is shared for personal and educational use. All code was written collaboratively between the author and IBM Bob AI. No commercial use without permission from the author.

---

*Space Pirates — early access build. More content, ships, and story coming soon.*
