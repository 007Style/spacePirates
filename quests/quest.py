"""quests/quest.py — Quest base class and objective tracking."""
from __future__ import annotations


class QuestStatus:
    AVAILABLE = "available"
    ACTIVE    = "active"
    COMPLETE  = "complete"
    FAILED    = "failed"


class Objective:
    def __init__(self, data: dict):
        self.obj_type  = data["type"]          # kill_ships, visit_sector, collect_item etc.
        self.count     = data.get("count", 1)
        self.target    = data.get("target", "any")
        self.progress  = 0
        self.completed = False

    def update(self, event_type: str, **kwargs) -> bool:
        """Feed an event; returns True if objective just completed."""
        if self.completed:
            return False
        if event_type == self.obj_type:
            self.progress += kwargs.get("amount", 1)
            if self.progress >= self.count:
                self.progress  = self.count
                self.completed = True
                return True
        return False

    def to_dict(self) -> dict:
        return {
            "obj_type":  self.obj_type,
            "count":     self.count,
            "target":    self.target,
            "progress":  self.progress,
            "completed": self.completed,
        }


class Quest:
    def __init__(self, data: dict):
        self.quest_id    = data["id"]
        self.title       = data["title"]
        self.description = data["description"]
        self.status      = QuestStatus.AVAILABLE
        self.objectives: list[Objective] = [
            Objective(o) for o in data.get("objectives", [])
        ]
        self.rewards: dict = data.get("rewards", {})
        self.faction_rep_changes: dict = data.get("faction_rep_changes", {})
        self.unlocks_next: str | None  = data.get("unlocks_next")
        self.triggers_ending: bool     = data.get("triggers_ending", False)

    # ── Lifecycle ─────────────────────────────────────────────────────────────
    def activate(self) -> None:
        self.status = QuestStatus.ACTIVE

    def fail(self) -> None:
        self.status = QuestStatus.FAILED

    # ── Progress ──────────────────────────────────────────────────────────────
    def on_event(self, event_type: str, **kwargs) -> bool:
        """Feed a game event; returns True if quest just completed."""
        if self.status != QuestStatus.ACTIVE:
            return False
        for obj in self.objectives:
            obj.update(event_type, **kwargs)
        if all(o.completed for o in self.objectives):
            self.status = QuestStatus.COMPLETE
            return True
        return False

    @property
    def progress_summary(self) -> str:
        parts = []
        for obj in self.objectives:
            parts.append(f"{obj.obj_type}: {obj.progress}/{obj.count}")
        return " | ".join(parts)

    # ── Serialization ─────────────────────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "quest_id":   self.quest_id,
            "status":     self.status,
            "objectives": [o.to_dict() for o in self.objectives],
        }

    def __repr__(self) -> str:
        return f"<Quest '{self.title}' [{self.status}]>"
