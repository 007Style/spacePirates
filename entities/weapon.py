"""entities/weapon.py — Weapon class with XP-based upgrade paths."""
from __future__ import annotations
from progression.rarity import rarity_system


class Weapon:
    XP_PER_LEVEL = 100  # base; scaled by rarity

    def __init__(self, data: dict):
        self.id             = data["id"]
        self.name           = data["name"]
        self.type           = data["type"]          # laser / missile / railgun / emp / flak
        self.rarity         = data.get("rarity", "common")
        self.description    = data.get("description", "")
        self.lore           = data.get("lore", "")
        self.contraband     = data.get("contraband", False)
        self.price          = data.get("price", 0)
        self.status_effect  = data.get("status_effect")

        mult = rarity_system.stat_multiplier(self.rarity)
        self.base_damage    = round(data.get("base_damage", 20) * mult)
        self.fire_rate      = data.get("fire_rate", 1.0)     # shots/sec
        self.range          = data.get("range", 300)
        self.ammo_type      = data.get("ammo_type", "energy")

        self.upgrade_paths  = data.get("upgrade_paths", {})
        self.chosen_path    = None   # "A" or "B" after specialization
        self.xp             = 0
        self.xp_to_specialize = data.get("xp_to_specialize", 200)
        self.level          = 1
        # Abilities unlocked post-specialization
        self.abilities: list[str] = []

        # Current combat state
        self._cooldown = 0.0   # seconds until next shot

    # ── XP & leveling ────────────────────────────────────────────────────────
    def add_xp(self, amount: int) -> bool:
        """Add XP from a kill. Returns True if specialization just unlocked."""
        self.xp += amount
        if self.chosen_path is None and self.xp >= self.xp_to_specialize:
            return True   # signal caller to show specialization prompt
        return False

    def choose_path(self, path: str) -> None:
        """Lock in specialization path A or B."""
        if path not in self.upgrade_paths:
            return
        self.chosen_path = path
        # Apply path bonuses
        if path == "A":
            self.fire_rate = round(self.fire_rate * 1.4, 2)
            self.base_damage = round(self.base_damage * 0.85)
        elif path == "B":
            self.base_damage = round(self.base_damage * 1.6)
            self.fire_rate   = round(self.fire_rate * 0.7, 2)

    # ── Combat ───────────────────────────────────────────────────────────────
    def can_fire(self) -> bool:
        return self._cooldown <= 0

    def fire(self) -> float:
        """Mark weapon as fired; return damage dealt."""
        self._cooldown = 1.0 / max(self.fire_rate, 0.01)
        return float(self.base_damage)

    def update(self, dt: float) -> None:
        if self._cooldown > 0:
            self._cooldown -= dt

    # ── Serialization ────────────────────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "id":           self.id,
            "rarity":       self.rarity,
            "chosen_path":  self.chosen_path,
            "xp":           self.xp,
            "level":        self.level,
        }

    @classmethod
    def from_save(cls, save_data: dict, base_data: dict) -> "Weapon":
        obj = cls(base_data)
        obj.xp          = save_data.get("xp", 0)
        obj.level       = save_data.get("level", 1)
        path = save_data.get("chosen_path")
        if path:
            obj.choose_path(path)
        return obj

    def __repr__(self) -> str:
        path = f" [{self.chosen_path}]" if self.chosen_path else ""
        return f"<Weapon {self.name} ({self.rarity}){path}>"
