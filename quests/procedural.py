"""quests/procedural.py — Procedural job board quest generator."""
from __future__ import annotations
import json
import os
import random
import string
from quests.quest import Quest, QuestStatus
from settings import DATA_DIR

# Named NPC pools for templates
_NAMES = ["Mira Voss", "Cutter", "Thane Ord", "Sable", "Rex Markov",
          "Juni Tal", "Brennan", "The Old Dog", "Kira Nacht", "Doc Wolfe"]
_FACTIONS_LIST = ["space_pirates", "merchant_guild", "military", "scavengers"]
_CARGO_LIST    = ["spice crates", "void crystals", "medical supplies",
                  "weapons cache", "encrypted data cores", "fuel cells"]
_SECTORS_LIST  = ["derelict_field", "trade_lanes", "outer_rim",
                  "nebula_reach", "black_market"]


def _random_id(prefix: str = "job") -> str:
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"{prefix}_{suffix}"


def _generate_kill_quest() -> dict:
    faction = random.choice(_FACTIONS_LIST)
    count   = random.randint(2, 6)
    credits = count * random.randint(200, 600)
    return {
        "id":          _random_id("kill"),
        "title":       f"Bounty: Clear {faction.replace('_',' ').title()} ships",
        "description": f"Destroy {count} {faction.replace('_',' ')} ships. "
                       f"Payment on completion.",
        "objectives":  [{"type": "kill_ships", "count": count, "target": faction}],
        "rewards":     {"credits": credits, "progression_points": count},
        "faction_rep_changes": {faction: -count * 3},
    }


def _generate_delivery_quest() -> dict:
    cargo  = random.choice(_CARGO_LIST)
    sector = random.choice(_SECTORS_LIST)
    credits = random.randint(500, 3000)
    return {
        "id":          _random_id("delivery"),
        "title":       f"Deliver {cargo.title()}",
        "description": f"Haul a shipment of {cargo} to {sector.replace('_',' ').title()}.",
        "objectives":  [{"type": "deliver_cargo", "count": 1,
                          "target": sector}],
        "rewards":     {"credits": credits, "progression_points": 2},
        "faction_rep_changes": {"merchant_guild": 5},
    }


def _generate_escort_quest() -> dict:
    ship_name = random.choice(_NAMES) + "'s Hauler"
    sector    = random.choice(_SECTORS_LIST)
    credits   = random.randint(800, 4000)
    return {
        "id":          _random_id("escort"),
        "title":       f"Escort: {ship_name}",
        "description": f"Protect '{ship_name}' through {sector.replace('_',' ').title()}.",
        "objectives":  [{"type": "escort_ship", "count": 1, "target": sector}],
        "rewards":     {"credits": credits, "progression_points": 3},
        "faction_rep_changes": {},
    }


def _generate_rescue_quest() -> dict:
    name    = random.choice(_NAMES)
    faction = random.choice(_FACTIONS_LIST)
    credits = random.randint(300, 1500)
    return {
        "id":          _random_id("rescue"),
        "title":       f"Rescue: {name}",
        "description": f"A crew member named {name} is being held by "
                       f"{faction.replace('_',' ')} forces. Rescue them.",
        "objectives":  [{"type": "kill_ships", "count": 3, "target": faction},
                        {"type": "collect_item", "count": 1, "target": "hostage_pod"}],
        "rewards":     {"credits": credits, "progression_points": 4,
                        "items": ["crew_random"]},
        "faction_rep_changes": {faction: -10},
    }


_GENERATORS = [
    _generate_kill_quest,
    _generate_delivery_quest,
    _generate_escort_quest,
    _generate_rescue_quest,
]


class JobBoard:
    BOARD_SIZE = 5

    def __init__(self):
        self.jobs: list[Quest] = []
        self.refresh()

    def refresh(self) -> None:
        self.jobs = []
        for _ in range(self.BOARD_SIZE):
            gen  = random.choice(_GENERATORS)
            data = gen()
            q    = Quest(data)
            self.jobs.append(q)

    def accept_job(self, index: int) -> Quest | None:
        if 0 <= index < len(self.jobs):
            job = self.jobs.pop(index)
            job.activate()
            return job
        return None

    def to_dict(self) -> dict:
        return {"jobs": [j.to_dict() for j in self.jobs]}
