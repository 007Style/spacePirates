"""progression/titles.py — Pirate title system."""
from __future__ import annotations
from core.events import bus


# (unlock_kills, unlock_wanted, title, dialogue_flag)
TITLE_DEFINITIONS = [
    (0,    0, "Drifter",            "rookie"),
    (10,   0, "Petty Pirate",       "rookie"),
    (25,   1, "Raider",             "pirate"),
    (50,   2, "Corsair",            "pirate"),
    (100,  2, "Brigand",            "feared"),
    (200,  3, "Scourge",            "feared"),
    (400,  3, "Dread Captain",      "legend"),
    (750,  4, "Terror of the Void", "legend"),
    (1500, 5, "Scourge of the Void","apex"),
    (3000, 5, "The Undying Blade",  "apex"),
]


class TitleSystem:
    def __init__(self):
        self.kills       = 0
        self.wanted_level = 0
        self._title_idx  = 0

    @property
    def current_title(self) -> str:
        return TITLE_DEFINITIONS[self._title_idx][2]

    @property
    def dialogue_flag(self) -> str:
        return TITLE_DEFINITIONS[self._title_idx][3]

    def update(self, kills: int, wanted: int) -> bool:
        """Returns True if title just changed."""
        self.kills        = kills
        self.wanted_level = wanted
        new_idx = self._title_idx
        for i, (req_kills, req_wanted, title, _) in enumerate(TITLE_DEFINITIONS):
            if kills >= req_kills and wanted >= req_wanted:
                new_idx = i
        if new_idx != self._title_idx:
            self._title_idx = new_idx
            bus.publish("title_changed", title=self.current_title)
            bus.publish("notification",
                        msg=f"🏴‍☠️ New title: {self.current_title}",
                        color=(255, 200, 40))
            return True
        return False

    def npc_price_modifier(self) -> float:
        """Fear discount at high title tiers."""
        flag = self.dialogue_flag
        return {"rookie": 1.0, "pirate": 0.98, "feared": 0.93,
                "legend": 0.88, "apex": 0.82}.get(flag, 1.0)

    def to_dict(self) -> dict:
        return {"kills": self.kills, "wanted_level": self.wanted_level,
                "title_idx": self._title_idx}

    def load_from_dict(self, data: dict) -> None:
        self.kills        = data.get("kills", 0)
        self.wanted_level = data.get("wanted_level", 0)
        self._title_idx   = data.get("title_idx", 0)
