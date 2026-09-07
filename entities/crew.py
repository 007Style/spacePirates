"""entities/crew.py — Crew member class with stats, XP, morale, relationships."""
from __future__ import annotations
from progression.rarity import rarity_system


# Stat that each station benefits from most
STATION_PRIMARY_STAT = {
    "cockpit":         "piloting",
    "gun_turret":      "gunnery",
    "engine_room":     "engineering",
    "repair_station":  "repair",
    "drone_bay":       "repair",     # roboticist path
    "brig":            "combat",
}


class Crew:
    XP_TO_SPECIALIZE = 500

    def __init__(self, data: dict):
        self.id          = data["id"]
        self.name        = data["name"]
        self.role        = data["role"]          # pilot / gunner / engineer / combat / mechanic
        self.rarity      = data.get("rarity", "common")
        self.description = data.get("description", "")
        self.lore        = data.get("lore", "")
        self.price       = data.get("price", 300)

        base_stats = data.get("stats", {})
        mult       = rarity_system.stat_multiplier(self.rarity)
        self.stats: dict[str, int] = {
            k: round(v * mult) for k, v in base_stats.items()
        }

        self.abilities: list[str]   = list(data.get("abilities", []))
        self.specialization_paths   = data.get("specialization_paths", {})
        self.chosen_path: str | None = None

        # Progression
        self.xp     = 0
        self.level  = 1

        # Morale  0–100
        self.morale = 75

        # Relationships: {crew_id: "bond" | "rivalry"}
        self.relationships: dict[str, str] = {}

        # Cabin upgrade level on each ship {ship_id: level}
        self.cabin_upgrades: dict[str, int] = {}

        # Equipment slots: {slot_name: gear_id | None}
        # Slots: "head", "body", "tool"
        self.equipment: dict[str, str | None] = {
            "head": None,
            "body": None,
            "tool": None,
        }

        # Current assignment
        self.assigned_ship:    str | None = None
        self.assigned_station: str | None = None
        self.injured:          bool = False
        self.recovery_ticks:   int  = 0

    # ── XP & leveling ────────────────────────────────────────────────────────
    def add_xp(self, amount: int) -> bool:
        """Returns True if specialization prompt should be shown."""
        self.xp += amount
        threshold = self.XP_TO_SPECIALIZE * (self.level ** 1.5)
        if self.xp >= threshold:
            self.level += 1
            if self.chosen_path is None and self.level >= 5:
                return True  # prompt specialization
        return False

    def choose_path(self, path: str) -> None:
        if path not in self.specialization_paths:
            return
        self.chosen_path = path
        # Boost primary stat for chosen path
        primary = STATION_PRIMARY_STAT.get(
            {"pilot": "cockpit", "gunner": "gun_turret",
             "engineer": "engine_room", "mechanic": "repair_station",
             "combat": "brig"}.get(self.role, ""), ""
        )
        if primary and primary in self.stats:
            if path == "A":
                self.stats[primary] = round(self.stats[primary] * 1.4)
            else:
                # Path B boosts a secondary stat
                self.stats[primary] = round(self.stats[primary] * 1.2)
                for k in self.stats:
                    if k != primary:
                        self.stats[k] = round(self.stats[k] * 1.15)
                        break

    # ── Morale ───────────────────────────────────────────────────────────────
    def change_morale(self, delta: int) -> None:
        self.morale = max(0, min(100, self.morale + delta))

    # ── Relationships ────────────────────────────────────────────────────────
    def add_relationship(self, other_id: str, rel_type: str) -> None:
        self.relationships[other_id] = rel_type

    def stat_bonus_from_relationships(self) -> dict[str, float]:
        """Returns additive stat bonuses from bonds/rivalries."""
        bonus: dict[str, float] = {}
        for rel in self.relationships.values():
            if rel == "bond":
                bonus["combat"]  = bonus.get("combat", 0)  + 2
                bonus["morale_gain"] = bonus.get("morale_gain", 0) + 1
            elif rel == "rivalry":
                bonus["gunnery"] = bonus.get("gunnery", 0) + 3
        return bonus

    # ── Cabin upgrade ────────────────────────────────────────────────────────
    def cabin_level(self, ship_id: str) -> int:
        return self.cabin_upgrades.get(ship_id, 0)

    def upgrade_cabin(self, ship_id: str) -> None:
        self.cabin_upgrades[ship_id] = self.cabin_level(ship_id) + 1

    def cabin_stat_bonus(self, ship_id: str, stat: str) -> int:
        return self.cabin_level(ship_id) * 2  # +2 per upgrade level per stat

    # ── Station performance ──────────────────────────────────────────────────
    def effective_stat(self, stat: str, ship_id: str = "") -> float:
        base  = self.stats.get(stat, 0)
        cabin = self.cabin_stat_bonus(ship_id, stat)
        rel   = self.stat_bonus_from_relationships().get(stat, 0)
        gear  = self._gear_stat_bonus(stat)
        morale_mod = (self.morale - 50) / 100.0  # -0.5 to +0.5
        return (base + cabin + rel + gear) * (1.0 + morale_mod * 0.2)

    def _gear_stat_bonus(self, stat: str) -> int:
        """Sum of stat bonuses from all equipped crew gear."""
        # Import here to avoid circular import; CREW_GEAR_ITEMS lives in home_base
        try:
            from base.home_base import CREW_GEAR_ITEMS
            total = 0
            for slot_gear_id in self.equipment.values():
                if slot_gear_id:
                    item = next((g for g in CREW_GEAR_ITEMS
                                 if g["id"] == slot_gear_id), None)
                    if item:
                        total += item.get("stats", {}).get(stat, 0)
            return total
        except Exception:
            return 0

    # ── Injury ───────────────────────────────────────────────────────────────
    def injure(self, ticks: int = 300) -> None:
        self.injured = True
        self.recovery_ticks = ticks

    def tick_recovery(self) -> None:
        if self.injured and self.recovery_ticks > 0:
            self.recovery_ticks -= 1
            if self.recovery_ticks <= 0:
                self.injured = False

    # ── Serialization ────────────────────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "id":              self.id,
            "rarity":          self.rarity,
            "xp":              self.xp,
            "level":           self.level,
            "morale":          self.morale,
            "chosen_path":     self.chosen_path,
            "relationships":   self.relationships,
            "cabin_upgrades":  self.cabin_upgrades,
            "injured":         self.injured,
            "recovery_ticks":  self.recovery_ticks,
            "assigned_ship":   self.assigned_ship,
            "assigned_station":self.assigned_station,
            "equipment":       self.equipment,
        }

    @classmethod
    def from_save(cls, save_data: dict, base_data: dict) -> "Crew":
        obj = cls(base_data)
        obj.xp              = save_data.get("xp", 0)
        obj.level           = save_data.get("level", 1)
        obj.morale          = save_data.get("morale", 75)
        obj.chosen_path     = save_data.get("chosen_path")
        obj.relationships   = save_data.get("relationships", {})
        obj.cabin_upgrades  = save_data.get("cabin_upgrades", {})
        obj.injured         = save_data.get("injured", False)
        obj.recovery_ticks  = save_data.get("recovery_ticks", 0)
        obj.assigned_ship   = save_data.get("assigned_ship")
        obj.assigned_station= save_data.get("assigned_station")
        obj.equipment       = save_data.get("equipment",
                                            {"head": None, "body": None, "tool": None})
        return obj

    def __repr__(self) -> str:
        return f"<Crew {self.name} ({self.role}/{self.rarity}) lv{self.level}>"
