"""core/save.py — Full JSON-based save/load system with auto-save triggers."""
from __future__ import annotations
import json
import os
import time
from settings import SAVE_DIR, SAVE_SLOTS
from core.events import bus


def _slot_path(slot: int) -> str:
    os.makedirs(SAVE_DIR, exist_ok=True)
    return os.path.join(SAVE_DIR, f"slot_{slot}.json")


# ── Low-level file I/O ────────────────────────────────────────────────────────

def save_game(slot: int, data: dict) -> None:
    with open(_slot_path(slot), "w") as f:
        json.dump(data, f, indent=2)


def load_game(slot: int) -> dict | None:
    path = _slot_path(slot)
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def delete_save(slot: int) -> None:
    path = _slot_path(slot)
    if os.path.exists(path):
        os.remove(path)


def list_saves() -> list[dict | None]:
    result = []
    for slot in range(SAVE_SLOTS):
        data = load_game(slot)
        if data is None:
            result.append(None)
        else:
            result.append({
                "slot":      slot,
                "captain":   data.get("captain_name", "Unknown"),
                "sector":    data.get("current_sector", "???"),
                "kills":     data.get("total_kills", 0),
                "playtime":  data.get("playtime_seconds", 0),
                "ng_plus":   data.get("ng_plus", False),
                "saved_at":  data.get("saved_at", 0),
            })
    return result


# ── High-level SaveSystem ─────────────────────────────────────────────────────

class SaveSystem:
    """Serializes the full game state to/from a save slot."""

    def __init__(self, game):
        self.game = game
        # Subscribe to auto-save triggers
        bus.subscribe("sector_entered",  self._auto_save)
        bus.subscribe("quest_completed", self._auto_save)
        bus.subscribe("state_changed",   self._on_state_changed)

    # ── Auto-save hooks ───────────────────────────────────────────────────────
    def _auto_save(self, **kwargs) -> None:
        self.save(self.game.save_slot)

    def _on_state_changed(self, new="", **kwargs) -> None:
        if new in ("base", "game_over"):
            self.save(self.game.save_slot)

    # ── Save ──────────────────────────────────────────────────────────────────
    def save(self, slot: int) -> bool:
        try:
            data = self._collect()
            save_game(slot, data)
            bus.publish("notification", msg="Game saved.", color=(60, 200, 80))
            return True
        except Exception as e:
            bus.publish("notification",
                        msg=f"Save failed: {e}", color=(220, 60, 60))
            return False

    def _collect(self) -> dict:
        g = self.game
        data: dict = {
            "version":        1,
            "saved_at":       int(time.time()),
            "playtime_seconds": int(g.playtime),
        }

        # Captain
        ship = g.player_fleet.active_ship if g.player_fleet else None
        data["captain_name"]    = ship.custom_name if ship else "Unknown"
        data["current_sector"]  = g.galaxy.current_sector_id if g.galaxy else "???"

        # Meta progression (always persisted)
        if g.meta_progression:
            meta_dict = g.meta_progression.to_dict()
            data["total_kills"]    = meta_dict.get("total_kills", 0)
            data["ng_plus"]        = meta_dict.get("ng_plus", False)
            data["meta"]           = meta_dict

        # Fleet
        if g.player_fleet:
            data["fleet"] = g.player_fleet.to_dict()

        # Home base
        if g.home_base:
            data["home_base"] = g.home_base.to_dict()

        # Galaxy
        if g.galaxy:
            data["galaxy"] = g.galaxy.to_dict()

        # Reputation
        if g.reputation_mgr:
            data["reputation"] = g.reputation_mgr.to_dict()

        # Story quests
        if g.quest_manager:
            data["story"] = g.quest_manager.to_dict()

        # Codex
        if g.codex:
            data["codex"] = g.codex.to_dict()

        return data

    # ── Load ──────────────────────────────────────────────────────────────────
    def load(self, slot: int) -> bool:
        data = load_game(slot)
        if data is None:
            return False
        try:
            self._apply(data)
            self.game.save_slot = slot
            return True
        except Exception as e:
            bus.publish("notification",
                        msg=f"Load failed: {e}", color=(220, 60, 60))
            return False

    def _apply(self, data: dict) -> None:
        import json as _json
        g = self.game

        # Bootstrap subsystems if not already initialized
        if g.meta_progression is None:
            from progression.meta import MetaProgression
            g.meta_progression = MetaProgression()
        if data.get("meta"):
            g.meta_progression.load_from_dict(data["meta"])

        # Galaxy
        from world.galaxy import Galaxy
        g.galaxy = Galaxy()
        if data.get("galaxy"):
            gd = data["galaxy"]
            g.galaxy.current_sector_id = gd.get("current_sector_id", "home_base")
            for sid, sd in gd.get("sectors", {}).items():
                if sid in g.galaxy.sectors:
                    g.galaxy.sectors[sid].visited       = sd.get("visited", False)
                    g.galaxy.sectors[sid].boss_defeated = sd.get("boss_defeated", False)

        # Reputation
        from factions.reputation import ReputationManager
        g.reputation_mgr = ReputationManager()
        if data.get("reputation"):
            g.reputation_mgr.load_from_dict(data["reputation"])

        # Home base
        from base.home_base import HomeBase
        meta = g.meta_progression
        g.home_base = HomeBase(wanted_level_ref=lambda: meta.wanted_level)
        if data.get("home_base"):
            g.home_base.load_from_dict(data["home_base"])

        # Economy
        from world.economy import Economy
        g.economy = Economy(g.galaxy, g.reputation_mgr)

        # Fleet — rebuild ships from save data + base JSON definitions
        from fleet.fleet  import Fleet
        from entities.ship import Ship
        from entities.crew import Crew
        from entities.weapon import Weapon

        g.player_fleet = Fleet(g.home_base, g.meta_progression)
        fleet_data = data.get("fleet", {})

        ship_defs:   dict = {}
        crew_defs:   dict = {}
        weapon_defs: dict = {}
        try:
            with open("data/ships.json")   as f: ship_defs   = {s["id"]: s for s in _json.load(f)}
            with open("data/crew.json")    as f: crew_defs   = {c["id"]: c for c in _json.load(f)}
            with open("data/weapons.json") as f: weapon_defs = {w["id"]: w for w in _json.load(f)}
        except Exception:
            pass

        active_id = fleet_data.get("active_ship_id")
        for ship_save in fleet_data.get("ships", []):
            sid = ship_save.get("id")
            base = ship_defs.get(sid)
            if not base:
                continue
            ship = Ship(base)
            ship.hull          = ship_save.get("hull", ship.max_hull)
            ship.shield        = ship_save.get("shield", ship.max_shield)
            ship.fuel          = ship_save.get("fuel", ship.fuel_capacity)
            ship.custom_name   = ship_save.get("custom_name", ship.name)
            ship.fleet_order   = ship_save.get("fleet_order", "standby")
            # Crew
            for crew_save in ship_save.get("crew", []):
                cid = crew_save.get("id")
                cbase = crew_defs.get(cid)
                if cbase:
                    crew = Crew.from_save(crew_save, cbase)
                    ship.add_crew(crew)
            # Weapons
            for w_save in ship_save.get("weapons", []):
                wid = w_save.get("id")
                wbase = weapon_defs.get(wid)
                if wbase:
                    weapon = Weapon.from_save(w_save, wbase)
                    ship.add_weapon(weapon)
            g.player_fleet.add_ship(ship)
            if sid == active_id:
                g.player_fleet.active_ship = ship

        # Story quests
        from quests.story import StoryManager
        g.quest_manager = StoryManager(g.reputation_mgr)
        if data.get("story"):
            g.quest_manager.load_from_dict(data["story"])

        # Codex
        if g.codex and data.get("codex"):
            g.codex.load_from_dict(data["codex"])

        g.playtime = data.get("playtime_seconds", 0)
        g.change_state("base")
