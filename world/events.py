"""world/events.py — Random space events triggered on sector entry."""
from __future__ import annotations
import random


class SpaceEvent:
    def __init__(self, event_id: str, title: str, description: str,
                 choices: list[dict]):
        self.event_id    = event_id
        self.title       = title
        self.description = description
        self.choices     = choices   # list of {label, outcome_fn}

    def resolve(self, choice_idx: int, player_ship, fleet) -> dict:
        if choice_idx < len(self.choices):
            outcome_fn = self.choices[choice_idx].get("outcome_fn")
            if callable(outcome_fn):
                return outcome_fn(player_ship, fleet)
        return {"message": "Nothing happened."}


# ── Event definitions ─────────────────────────────────────────────────────────

def _distress_signal(player_ship, fleet) -> dict:
    # Reward: random crew member rescued
    return {"message": "You rescue a survivor. They join your crew.", "reward": "crew_random"}

def _distress_ignore(player_ship, fleet) -> dict:
    return {"message": "You fly on. The signal fades.", "morale_delta": -3}

def _derelict_loot(player_ship, fleet) -> dict:
    return {"message": "You find useful salvage aboard.", "reward": "resource_random"}

def _derelict_trap(player_ship, fleet) -> dict:
    dmg = random.randint(15, 40)
    player_ship.take_damage(dmg)
    return {"message": f"It was a trap! You take {dmg} hull damage.", "damage": dmg}

def _ambush_fight(player_ship, fleet) -> dict:
    return {"message": "Enemies drop out of warp!", "trigger": "combat"}

def _ambush_bribe(player_ship, fleet) -> dict:
    cost = random.randint(100, 400)
    return {"message": f"You pay {cost} credits to be left alone.",
            "credits_delta": -cost}

def _meteor_evade(player_ship, fleet) -> dict:
    return {"message": "Skilled piloting — you thread the field unscathed."}

def _meteor_hit(player_ship, fleet) -> dict:
    dmg = random.randint(10, 25)
    player_ship.take_damage(dmg, ignore_shield=True)
    return {"message": f"A meteor clips your hull for {dmg} damage.", "damage": dmg}


RANDOM_EVENTS: list[SpaceEvent] = [
    SpaceEvent(
        "distress_signal",
        "Distress Signal",
        "A faint distress signal is coming from a nearby drifting pod.",
        [
            {"label": "Investigate",  "outcome_fn": _distress_signal},
            {"label": "Ignore",        "outcome_fn": _distress_ignore},
        ],
    ),
    SpaceEvent(
        "derelict_ship",
        "Derelict Vessel",
        "A drifting hulk with no life signs. Could be loot — or a trap.",
        [
            {"label": "Board and loot", "outcome_fn": _derelict_loot},
            {"label": "Leave it",       "outcome_fn": lambda s, f: {"message": "You fly past."}},
            {"label": "Scan first",     "outcome_fn": _derelict_trap},
        ],
    ),
    SpaceEvent(
        "pirate_ambush",
        "Pirate Ambush",
        "Ships drop out of warp on an intercept course!",
        [
            {"label": "Fight!",        "outcome_fn": _ambush_fight},
            {"label": "Pay them off",  "outcome_fn": _ambush_bribe},
            {"label": "Run!",          "outcome_fn": lambda s, f: {"message": "You boost engines and escape.", "fuel_delta": -5}},
        ],
    ),
    SpaceEvent(
        "meteor_shower",
        "Meteor Shower",
        "A dense field of rocks crosses your path.",
        [
            {"label": "Navigate through", "outcome_fn": _meteor_evade},
            {"label": "Punch through",    "outcome_fn": _meteor_hit},
            {"label": "Wait it out",      "outcome_fn": lambda s, f: {"message": "You wait. It passes. Supplies -5.", "supplies_delta": -5}},
        ],
    ),
]


class EventManager:
    def __init__(self):
        self._event_chance = 0.3  # 30% chance on sector entry

    def roll_event(self) -> SpaceEvent | None:
        if random.random() < self._event_chance:
            return random.choice(RANDOM_EVENTS)
        return None
