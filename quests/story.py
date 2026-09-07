"""quests/story.py — Story quest chain manager."""
from __future__ import annotations
import json
import os
from quests.quest import Quest, QuestStatus
from core.events import bus
from settings import DATA_DIR


class StoryManager:
    def __init__(self, reputation_mgr=None):
        self.rep_mgr = reputation_mgr
        self._quests: dict[str, Quest] = {}
        self._load_quests()
        self._current_quest_id: str | None = "sq_01"
        self.ending_triggered = False
        self.ending_type      = ""

        # Subscribe to game events to update quest progress
        bus.subscribe("enemy_killed",    self._on_enemy_killed)
        bus.subscribe("sector_entered",  self._on_sector_entered)
        bus.subscribe("boss_defeated",   self._on_boss_defeated)

    # ── Loading ───────────────────────────────────────────────────────────────
    def _load_quests(self) -> None:
        path = os.path.join(DATA_DIR, "quests.json")
        with open(path) as f:
            data = json.load(f)
        for qd in data.get("story_quests", []):
            self._quests[qd["id"]] = Quest(qd)
        # Activate first quest
        first = self._quests.get("sq_01")
        if first:
            first.activate()

    # ── Current quest ─────────────────────────────────────────────────────────
    @property
    def current_quest(self) -> Quest | None:
        return self._quests.get(self._current_quest_id)

    @property
    def active_quests(self) -> list[Quest]:
        return [q for q in self._quests.values()
                if q.status == QuestStatus.ACTIVE]

    # ── Event handlers ────────────────────────────────────────────────────────
    def _on_enemy_killed(self, **kwargs) -> None:
        self._feed_all("kill_ships", amount=1)

    def _on_sector_entered(self, sector=None, **kwargs) -> None:
        if sector:
            self._feed_all("visit_sector",    amount=1,
                           sector_id=sector.sector_id)
            self._feed_all("visit_nation",    amount=1,
                           nation_id=sector.nation_id)

    def _on_boss_defeated(self, boss_id="", **kwargs) -> None:
        self._feed_all("defeat_boss", amount=1, boss_id=boss_id)

    def _feed_all(self, event_type: str, **kwargs) -> None:
        for quest in list(self.active_quests):
            completed = quest.on_event(event_type, **kwargs)
            if completed:
                self._on_quest_completed(quest)

    # ── Completion ────────────────────────────────────────────────────────────
    def _on_quest_completed(self, quest: Quest) -> None:
        # Apply reputation changes
        if self.rep_mgr:
            for fid, delta in quest.faction_rep_changes.items():
                self.rep_mgr.adjust(fid, delta)

        bus.publish("quest_completed", quest=quest)

        if quest.triggers_ending:
            self._trigger_ending(quest)
            return

        # Unlock next quest
        if quest.unlocks_next and quest.unlocks_next in self._quests:
            next_q = self._quests[quest.unlocks_next]
            next_q.activate()
            self._current_quest_id = quest.unlocks_next
            bus.publish("new_quest", quest=next_q)

    def _trigger_ending(self, quest: Quest) -> None:
        self.ending_triggered = True
        # Determine ending based on rep
        if self.rep_mgr:
            if self.rep_mgr.joined_secret:
                self.ending_type = "void_ending"
            elif self.rep_mgr.is_at_least_friendly("military"):
                self.ending_type = "hero_ending"
            elif self.rep_mgr.is_at_least_friendly("merchant_guild"):
                self.ending_type = "merchant_ending"
            else:
                self.ending_type = "pirate_ending"
        else:
            self.ending_type = "pirate_ending"
        bus.publish("ending_triggered", ending=self.ending_type)

    # ── Rival Captain ─────────────────────────────────────────────────────────
    def get_rival_level(self) -> int:
        """Rival scales with story progress (0–5)."""
        completed = sum(1 for q in self._quests.values()
                        if q.status == QuestStatus.COMPLETE)
        return min(5, completed)

    # ── Serialization ─────────────────────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "current_quest_id":  self._current_quest_id,
            "ending_triggered":  self.ending_triggered,
            "ending_type":       self.ending_type,
            "quests":            {qid: q.to_dict()
                                  for qid, q in self._quests.items()},
        }

    def load_from_dict(self, data: dict) -> None:
        self._current_quest_id = data.get("current_quest_id", "sq_01")
        self.ending_triggered  = data.get("ending_triggered", False)
        self.ending_type       = data.get("ending_type", "")
        for qid, qd in data.get("quests", {}).items():
            if qid in self._quests:
                self._quests[qid].status = qd.get("status", QuestStatus.AVAILABLE)
