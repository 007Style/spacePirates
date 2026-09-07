"""base/buildings.py — Building definitions and upgrade tiers."""
from __future__ import annotations


class Building:
    def __init__(self, building_id: str, name: str, description: str,
                 max_level: int = 3, base_cost: dict = None):
        self.building_id = building_id
        self.name        = name
        self.description = description
        self.level       = 0          # 0 = not built
        self.max_level   = max_level
        self.base_cost   = base_cost or {"credits": 500, "metal": 100}

    def upgrade_cost(self) -> dict:
        mult = self.level + 1
        return {k: v * mult for k, v in self.base_cost.items()}

    def can_upgrade(self) -> bool:
        return self.level < self.max_level

    def upgrade(self) -> bool:
        if not self.can_upgrade():
            return False
        self.level += 1
        return True

    def is_built(self) -> bool:
        return self.level > 0

    def effect_description(self) -> str:
        """Human-readable description of current level effect."""
        return f"{self.name} Lv{self.level}"

    def to_dict(self) -> dict:
        return {"building_id": self.building_id, "level": self.level}


# ── Building definitions ──────────────────────────────────────────────────────

BUILDING_DEFINITIONS = [
    {
        "id":          "shipyard",
        "name":        "Shipyard",
        "description": "Repair and switch between your ships. Higher levels unlock faster repairs.",
        "max_level":   3,
        "cost":        {"credits": 800,  "metal": 200},
        "effects":     {1: "Repair ships | Switch active ship",
                        2: "Repair 50% faster | Mod slot +1 per ship",
                        3: "Instant repair | Unlock ship class upgrades"},
    },
    {
        "id":          "barracks",
        "name":        "Barracks",
        "description": "Manage your crew roster and run crew training programs.",
        "max_level":   3,
        "cost":        {"credits": 600,  "metal": 100},
        "effects":     {1: "Manage crew | Crew roster +5 slots",
                        2: "Crew training -20% cost | Fleet Admiral slot",
                        3: "Crew XP rate +50% | Roster +10 more slots"},
    },
    {
        "id":          "armory",
        "name":        "Armory",
        "description": "Store and manage all weapons, gear, and drones.",
        "max_level":   3,
        "cost":        {"credits": 700,  "metal": 150},
        "effects":     {1: "Weapon storage 20 slots | Drone storage 5 slots",
                        2: "Weapon upgrade bench | Drone upgrade bench",
                        3: "Weapon XP boost when stored | Secret weapon slot"},
    },
    {
        "id":          "warehouse",
        "name":        "Warehouse",
        "description": "Store resources, fuel, supplies, and contraband.",
        "max_level":   3,
        "cost":        {"credits": 400,  "metal": 80},
        "effects":     {1: "Resource cap ×2 | Fuel reserve +50",
                        2: "Resource cap ×4 | Contraband hidden storage",
                        3: "Resource cap ×8 | Auto-resupply ships from stock"},
    },
    {
        "id":          "research_lab",
        "name":        "Research Lab",
        "description": "Spend progression points on the permanent meta-upgrade tree.",
        "max_level":   3,
        "cost":        {"credits": 1200, "metal": 300, "void_crystals": 5},
        "effects":     {1: "Basic upgrades unlocked | Meta-upgrade tree access",
                        2: "Advanced upgrades | Upgrade cost -10%",
                        3: "Legendary upgrades | Secret upgrade branch"},
    },
    {
        "id":          "cantina",
        "name":        "Cantina",
        "description": "Recruit crew members, pick up side quests, and hire mercenaries.",
        "max_level":   3,
        "cost":        {"credits": 500,  "metal": 50},
        "effects":     {1: "Crew recruitment | Job board (3 jobs)",
                        2: "Rare crew pool | Mercenary hiring | Job board (5 jobs)",
                        3: "Legendary crew pool | Morale events | Job board (7 jobs)"},
    },
    {
        "id":          "trading_post",
        "name":        "Trading Post",
        "description": "Buy and sell ships, weapons, crew, and resources.",
        "max_level":   3,
        "cost":        {"credits": 600,  "metal": 100},
        "effects":     {1: "Basic market | Buy/sell resources",
                        2: "Ship market | Sell price +10%",
                        3: "Auction access | Black market contact | Sell price +20%"},
    },
    {
        "id":          "defense_turrets",
        "name":        "Defense Turrets",
        "description": "Automated defenses that protect your base from raiders.",
        "max_level":   4,
        "cost":        {"credits": 500,  "metal": 200},
        "effects":     {1: "1 light turret | Base HP +200",
                        2: "2 turrets | Base HP +400 | Turret damage +50%",
                        3: "3 turrets | EMP turret added | Alert radius +30%",
                        4: "4 turrets | Shield dome | Raider warning +60s"},
    },
]


def make_buildings() -> dict[str, Building]:
    result: dict[str, Building] = {}
    for bd in BUILDING_DEFINITIONS:
        result[bd["id"]] = Building(
            bd["id"], bd["name"], bd["description"],
            bd["max_level"], bd["cost"],
        )
    return result
