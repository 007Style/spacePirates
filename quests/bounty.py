"""quests/bounty.py — Bounty board: named enemy captains."""
from __future__ import annotations
import random
import json
import os
from entities.ship import Ship
from entities.weapon import Weapon
from settings import DATA_DIR


_CAPTAIN_TITLES = [
    "Dread", "Iron", "Cursed", "Void", "Black", "Red",
    "Silver", "Scar", "Ghost", "Ruin",
]
_CAPTAIN_NAMES = [
    "Mara", "Vex", "Dorian", "Sable", "Kira",
    "Rex", "Thorn", "Lirien", "Bolt", "Havoc",
]


class BountyTarget:
    def __init__(self, name: str, ship: Ship, reward_credits: int,
                 reward_items: list[dict]):
        self.name            = name
        self.ship            = ship
        self.reward_credits  = reward_credits
        self.reward_items    = reward_items
        self.claimed         = False

    def to_dict(self) -> dict:
        return {
            "name":           self.name,
            "ship_id":        self.ship.id,
            "reward_credits": self.reward_credits,
            "claimed":        self.claimed,
        }


class BountyBoard:
    BOARD_SIZE = 4

    def __init__(self):
        self.targets: list[BountyTarget] = []
        self._ships_data:   list[dict] = []
        self._weapons_data: list[dict] = []
        self._load_data()
        self.refresh()

    def _load_data(self) -> None:
        try:
            with open(os.path.join(DATA_DIR, "ships.json")) as f:
                self._ships_data = json.load(f)
            with open(os.path.join(DATA_DIR, "weapons.json")) as f:
                self._weapons_data = json.load(f)
        except Exception:
            pass

    def _make_bounty_ship(self, difficulty: int) -> Ship:
        """Create a named pirate captain's ship."""
        # Pick a ship scaled to difficulty (higher diff = rarer ship)
        rarity_filter = ["common", "uncommon", "rare", "epic", "legendary"]
        tier  = min(difficulty - 1, len(rarity_filter) - 1)
        pool  = [s for s in self._ships_data
                 if s.get("rarity") == rarity_filter[tier]]
        if not pool:
            pool = self._ships_data
        ship_data = random.choice(pool)
        ship = Ship(ship_data)
        ship.x = random.randint(300, 900)
        ship.y = random.randint(100, 600)

        # Equip 1–2 weapons
        weapon_pool = [w for w in self._weapons_data
                       if w.get("rarity") in rarity_filter[:tier + 2]]
        if weapon_pool:
            for _ in range(min(2, len(weapon_pool))):
                wd = random.choice(weapon_pool)
                ship.add_weapon(Weapon(wd))
        return ship

    def refresh(self, difficulty: int = 2) -> None:
        self.targets = []
        for _ in range(self.BOARD_SIZE):
            title   = random.choice(_CAPTAIN_TITLES)
            name    = random.choice(_CAPTAIN_NAMES)
            captain = f"Captain {title} {name}"
            diff    = max(1, difficulty + random.randint(-1, 2))
            ship    = self._make_bounty_ship(diff)
            reward  = diff * random.randint(800, 2000)
            # Reward item from the ship's weapon pool
            items = [w.to_dict() for w in ship.weapons[:1]]
            self.targets.append(BountyTarget(captain, ship, reward, items))

    def claim(self, target_name: str) -> dict | None:
        for t in self.targets:
            if t.name == target_name and not t.claimed:
                t.claimed = True
                return {
                    "credits": t.reward_credits,
                    "items":   t.reward_items,
                }
        return None

    def to_dict(self) -> dict:
        return {"targets": [t.to_dict() for t in self.targets]}
