"""progression/rarity.py — Rarity system and drop tables."""
from __future__ import annotations
import random
from settings import RARITY_TIERS, RARITY_ORDER


class RaritySystem:
    """Handles rarity rolling, stat multipliers, and drop table selection."""

    def __init__(self):
        # Build cumulative weight table once
        self._weights = {
            key: data[3] for key, data in RARITY_TIERS.items()
        }

    # ── Rolling ──────────────────────────────────────────────────────────────
    def roll_rarity(self, luck: float = 0.0) -> str:
        """Roll a rarity key. luck is a multiplier bonus (0.0 = no bonus).
        Higher luck shifts weight toward rarer tiers.
        """
        weights = dict(self._weights)
        if luck > 0:
            # Reduce common/uncommon weight, boost rare+
            for i, key in enumerate(RARITY_ORDER):
                shift = luck * i * 0.5
                weights[key] = max(0.01, weights[key] + shift if i >= 2 else weights[key] - shift)

        keys   = list(weights.keys())
        values = list(weights.values())
        return random.choices(keys, weights=values, k=1)[0]

    # ── Stat multiplier ──────────────────────────────────────────────────────
    @staticmethod
    def stat_multiplier(rarity: str) -> float:
        return RARITY_TIERS.get(rarity, RARITY_TIERS["common"])[2]

    # ── Color ────────────────────────────────────────────────────────────────
    @staticmethod
    def color(rarity: str) -> tuple:
        return RARITY_TIERS.get(rarity, RARITY_TIERS["common"])[1]

    @staticmethod
    def name(rarity: str) -> str:
        return RARITY_TIERS.get(rarity, RARITY_TIERS["common"])[0]

    # ── Comparison ───────────────────────────────────────────────────────────
    @staticmethod
    def rank(rarity: str) -> int:
        """Return 0-based index; higher = rarer."""
        try:
            return RARITY_ORDER.index(rarity)
        except ValueError:
            return 0

    @staticmethod
    def is_rarer(a: str, b: str) -> bool:
        return RaritySystem.rank(a) > RaritySystem.rank(b)

    # ── Drop table ───────────────────────────────────────────────────────────
    def roll_drop_table(
        self,
        pool: list[dict],
        luck: float = 0.0,
        count: int = 1,
    ) -> list[dict]:
        """Given a pool of item dicts (each must have a 'rarity' field),
        return `count` items selected by weighted rarity roll.
        """
        if not pool:
            return []

        result = []
        for _ in range(count):
            target_rarity = self.roll_rarity(luck)
            # Find items at or below target rarity
            candidates = [
                item for item in pool
                if self.rank(item.get("rarity", "common")) <= self.rank(target_rarity)
            ]
            if not candidates:
                candidates = pool  # fallback
            result.append(random.choice(candidates))
        return result

    # ── Apply rarity scaling to a stat dict ─────────────────────────────────
    @staticmethod
    def apply_to_stats(stats: dict, rarity: str) -> dict:
        mult = RaritySystem.stat_multiplier(rarity)
        return {k: round(v * mult) for k, v in stats.items()}


# Global singleton
rarity_system = RaritySystem()
