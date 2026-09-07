"""factions/faction.py — Faction and Nation data classes."""
from __future__ import annotations
import json
import os
from settings import DATA_DIR


class Faction:
    def __init__(self, data: dict):
        self.id              = data["id"]
        self.name            = data["name"]
        self.description     = data.get("description", "")
        self.color           = tuple(data.get("color", [128, 128, 128]))
        self.starting_rep    = data.get("starting_rep", 0)
        self.rep_thresholds  = data.get("rep_thresholds", {
            "hostile": -50, "neutral": 0, "friendly": 40, "allied": 80
        })
        self.exclusive_items: list[str] = data.get("exclusive_items", [])
        self.enemy_of:  list[str]       = data.get("enemy_of", [])
        self.ally_of:   list[str]       = data.get("ally_of", [])
        self.hidden:    bool            = data.get("hidden", False)
        self.join_locks_all: bool       = data.get("join_locks_all_factions", False)
        self.discover_codex_count: int  = data.get("discover_codex_count", 999)
        self.lore:      str             = data.get("lore", "")


class Nation(Faction):
    """Nation extends Faction with safe-sector and boss info."""
    def __init__(self, data: dict):
        super().__init__(data)
        self.specialty        = data.get("specialty", "")
        self.safe_sectors:  list[str] = data.get("safe_sectors", [])
        self.nation_upgrade = data.get("nation_upgrade", "")
        self.signature_boss = data.get("signature_boss", "")


def load_factions() -> tuple[dict[str, Faction], dict[str, Nation]]:
    """Load factions and nations from data file."""
    path = os.path.join(DATA_DIR, "factions.json")
    with open(path) as f:
        raw = json.load(f)

    factions: dict[str, Faction] = {}
    for fd in raw.get("factions", []):
        factions[fd["id"]] = Faction(fd)

    nations: dict[str, Nation] = {}
    for nd in raw.get("nations", []):
        nations[nd["id"]] = Nation(nd)

    return factions, nations
