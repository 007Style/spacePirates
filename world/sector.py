"""world/sector.py — Individual sector definition."""
from __future__ import annotations
import random


class SectorType:
    NORMAL        = "normal"
    NATION_SAFE   = "nation_safe"
    GRAVEYARD     = "graveyard"
    NEBULA        = "nebula"
    BOSS          = "boss"
    SEASONAL      = "seasonal"
    HOME_BASE     = "home_base"


class Sector:
    def __init__(
        self,
        sector_id: str,
        name: str,
        x: int,
        y: int,
        difficulty: int       = 1,
        sector_type: str      = SectorType.NORMAL,
        nation_id: str        = "",
        faction_id: str       = "",
        boss_id: str          = "",
        enemy_pool: list      = None,
        connections: list     = None,
        seasonal_active: bool = False,
    ):
        self.sector_id       = sector_id
        self.name            = name
        self.x               = x
        self.y               = y
        self.difficulty      = difficulty
        self.sector_type     = sector_type
        self.nation_id       = nation_id
        self.faction_id      = faction_id
        self.boss_id         = boss_id
        self.enemy_pool      = enemy_pool or []
        self.connections: list[str] = connections or []
        self.seasonal_active = seasonal_active

        self.visited         = False
        self.boss_defeated   = False

    # ── Helpers ───────────────────────────────────────────────────────────────
    @property
    def is_safe(self) -> bool:
        return self.sector_type == SectorType.NATION_SAFE

    @property
    def has_nebula(self) -> bool:
        return self.sector_type == SectorType.NEBULA

    @property
    def is_boss_sector(self) -> bool:
        return self.sector_type == SectorType.BOSS

    def enemy_count(self) -> int:
        base = self.difficulty * 2
        return max(1, base + random.randint(-1, 1))

    # ── Serialization ─────────────────────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "sector_id":      self.sector_id,
            "visited":        self.visited,
            "boss_defeated":  self.boss_defeated,
        }

    def __repr__(self) -> str:
        return (f"<Sector '{self.name}' type={self.sector_type} "
                f"diff={self.difficulty}>")
