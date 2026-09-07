"""factions/reputation.py — Reputation manager for factions and nations."""
from __future__ import annotations
from factions.faction import Faction, Nation, load_factions
from core.events import bus


class ReputationManager:
    def __init__(self):
        self.factions, self.nations = load_factions()

        # rep scores: {faction_id: int}
        self.scores: dict[str, int] = {}
        for fid, f in self.factions.items():
            self.scores[fid] = f.starting_rep
        for nid, n in self.nations.items():
            self.scores[nid] = n.starting_rep

        # Track if player has joined the secret faction
        self.joined_secret = False

    # ── Adjusting rep ─────────────────────────────────────────────────────────
    def adjust(self, entity_id: str, delta: int) -> None:
        """Adjust reputation with faction/nation and propagate to allies/enemies."""
        if entity_id not in self.scores:
            return

        old = self.scores[entity_id]
        self.scores[entity_id] = max(-100, min(100, old + delta))

        faction = self._get_entity(entity_id)
        if faction:
            # Allied factions gain fraction of positive rep
            if delta > 0:
                for ally_id in faction.ally_of:
                    if ally_id in self.scores:
                        self.scores[ally_id] = max(-100, min(100,
                            self.scores[ally_id] + delta // 3))
            # Enemy factions lose rep when you gain with their enemy
            if delta > 0:
                for enemy_id in faction.enemy_of:
                    if enemy_id in self.scores:
                        self.scores[enemy_id] = max(-100, min(100,
                            self.scores[enemy_id] - delta // 2))

        bus.publish("reputation_changed", entity_id=entity_id,
                    old=old, new=self.scores[entity_id])

    def _get_entity(self, eid: str) -> Faction | Nation | None:
        return self.factions.get(eid) or self.nations.get(eid)

    # ── Access level ──────────────────────────────────────────────────────────
    def standing(self, entity_id: str) -> str:
        """Returns 'hostile' | 'neutral' | 'friendly' | 'allied'."""
        score = self.scores.get(entity_id, 0)
        entity = self._get_entity(entity_id)
        if not entity:
            return "neutral"
        thresholds = entity.rep_thresholds
        if score >= thresholds.get("allied", 80):
            return "allied"
        if score >= thresholds.get("friendly", 40):
            return "friendly"
        if score >= thresholds.get("neutral", 0):
            return "neutral"
        return "hostile"

    def is_hostile(self, entity_id: str) -> bool:
        return self.standing(entity_id) == "hostile"

    def is_at_least_friendly(self, entity_id: str) -> bool:
        return self.standing(entity_id) in ("friendly", "allied")

    # ── Price modifier ────────────────────────────────────────────────────────
    def price_modifier(self, nation_id: str) -> float:
        """Returns a multiplier for buy/sell prices (< 1 = discount)."""
        s = self.standing(nation_id)
        return {"hostile": 1.4, "neutral": 1.0,
                "friendly": 0.9, "allied": 0.8}.get(s, 1.0)

    # ── Item access ───────────────────────────────────────────────────────────
    def has_item_access(self, entity_id: str, item_id: str) -> bool:
        entity = self._get_entity(entity_id)
        if not entity:
            return True
        if item_id not in entity.exclusive_items:
            return True
        return self.is_at_least_friendly(entity_id)

    # ── Secret faction discovery ──────────────────────────────────────────────
    def check_secret_discovery(self, codex_count: int) -> bool:
        sf = self.factions.get("secret_faction")
        if sf and not sf.hidden and codex_count >= sf.discover_codex_count:
            return True
        # Check if codex threshold met to reveal
        if sf and sf.hidden and codex_count >= sf.discover_codex_count:
            sf.hidden = False
            bus.publish("secret_faction_revealed")
            return True
        return False

    def join_secret_faction(self) -> None:
        self.joined_secret = True
        # Make all other factions hostile
        for fid in self.factions:
            if fid != "secret_faction":
                self.scores[fid] = -100
        for nid in self.nations:
            self.scores[nid] = max(self.scores[nid], -50)
        bus.publish("joined_secret_faction")

    # ── Aggression check ──────────────────────────────────────────────────────
    def will_attack_on_sight(self, faction_id: str) -> bool:
        return self.is_hostile(faction_id)

    # ── Serialization ─────────────────────────────────────────────────────────
    def to_dict(self) -> dict:
        return {"scores": self.scores, "joined_secret": self.joined_secret}

    def load_from_dict(self, data: dict) -> None:
        self.scores.update(data.get("scores", {}))
        self.joined_secret = data.get("joined_secret", False)
