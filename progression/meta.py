"""progression/meta.py — Meta-upgrade tree, progression points, wanted level, NG+."""
from __future__ import annotations
from core.events     import bus
from progression.titles import TitleSystem
from settings import POINTS_PER_KILL, POINTS_BOSS_BONUS, POINTS_QUEST_BONUS, MAX_WANTED_LEVEL


# ── Meta-upgrade tree definition ─────────────────────────────────────────────
# Each node: (id, name, description, base_cost, max_level, effect_key, effect_per_level, category, icon)
# Cost for level N = base_cost * N   (so level 1 costs 1x, level 2 costs 2x, etc.)
# Categories: "combat" | "crew" | "ship" | "economy" | "special"
META_UPGRADES = [
    # ── COMBAT ───────────────────────────────────────────────────────────────
    ("kill_bonus_pts",   "Kill Bounty",      "Earn extra progression pts per kill",   2,  5, "kill_pts_bonus",   1,    "combat",  "★"),
    ("weapon_damage",    "Weapon Mastery",   "+8% weapon damage per level",           3,  5, "damage_pct",       0.08, "combat",  "⚔"),
    ("weapon_range",     "Long Reach",       "+10% weapon range per level",           3,  5, "range_pct",        0.10, "combat",  "🎯"),
    ("evasion_bonus",    "Ghost Maneuver",   "+3% evasion per level",                 3,  5, "evasion_bonus",    0.03, "combat",  "👁"),
    ("shield_start",     "Hardened Shields", "Start with extra shield HP",            3,  5, "shield_bonus",     30,   "combat",  "🛡"),
    # ── SHIP ─────────────────────────────────────────────────────────────────
    ("starting_hull",    "Armored Start",    "Start with extra hull HP",              3,  5, "hull_bonus",       50,   "ship",    "🔩"),
    ("speed_boost",      "Hot Engines",      "+10 base speed per level",              2,  5, "speed_bonus",      10,   "ship",    "🚀"),
    ("fuel_bonus",       "Full Tank",        "Start with extra fuel",                 2,  5, "fuel_bonus",       20,   "ship",    "⛽"),
    ("repair_rate",      "Field Repairs",    "Passive hull repair in combat",         4,  5, "repair_bonus",     1.5,  "ship",    "🔧"),
    # ── CREW ─────────────────────────────────────────────────────────────────
    ("crew_slots",       "Crew Expansion",   "All ships get +1 crew slot",            5,  5, "crew_slots",       1,    "crew",    "👥"),
    ("combat_start_xp",  "Veteran Crew",     "Crew start each run with bonus XP",     4,  5, "start_xp",        60,   "crew",    "🎖"),
    ("morale_floor",     "Unbreakable",      "Crew morale never drops below floor",   4,  5, "morale_floor",     10,   "crew",    "💪"),
    ("boarding_power",   "Boarding Elite",   "+20% boarding combat power per level",  4,  5, "boarding_bonus",   0.20, "crew",    "🗡"),
    # ── ECONOMY ──────────────────────────────────────────────────────────────
    ("starting_credits", "Loaded Pockets",   "Start each run with more credits",      4,  5, "credits_bonus",    250,  "economy", "💰"),
    ("luck_bonus",       "Fortune's Favor",  "Better drop rarities from all kills",   5,  5, "luck",             0.15, "economy", "🍀"),
    ("resource_mult",    "Salvage Expert",   "More metal/fuel from kills",            4,  5, "resource_mult",    0.20, "economy", "♻"),
    ("cargo_bonus",      "Cargo King",       "More credits seized from cargo raids",  3,  5, "cargo_pct",        0.15, "economy", "📦"),
    # ── FLEET ────────────────────────────────────────────────────────────────
    ("fleet_slots",      "Bigger Fleet",     "Unlock an extra fleet ship slot",       8,  5, "fleet_slots",      1,    "economy", "🚢"),
    ("research_discount","Efficient R&D",    "Base building upgrades cost less",      6,  5, "research_discount",0.08, "economy", "🔬"),
    ("drone_slots",      "Drone Bay Upgrade","All ships get +2 max drone slots",      5,  5, "drone_slots_bonus",2,    "ship",    "🤖"),
    # ── SPECIAL (NG+ gated) ───────────────────────────────────────────────────
    ("ng_plus_luck",     "Void Touched",     "LEGENDARY drops +50% (NG+ only)",      20, 1, "ng_luck",          0.5,  "special", "✦"),
    ("ng_secret_branch", "Secret Paths",     "Hidden upgrade branches (NG+ only)",   30, 1, "ng_secret",        1.0,  "special", "👁"),
]

# Display order within each category for the grid layout
CATEGORY_ORDER = ["combat", "ship", "crew", "economy", "special"]
CATEGORY_LABELS = {
    "combat":  "COMBAT",
    "ship":    "SHIP",
    "crew":    "CREW",
    "economy": "ECONOMY / FLEET",
    "special": "NG+ SPECIAL",
}
CATEGORY_COLORS = {
    "combat":  (220,  80,  80),
    "ship":    ( 80, 180, 255),
    "crew":    ( 80, 220, 120),
    "economy": (220, 180,  60),
    "special": (200,  80, 220),
}


class MetaProgression:
    def __init__(self):
        self.progression_points = 0
        self.spent_points       = 0
        self.total_kills        = 0
        self.total_runs         = 0
        self.ng_plus            = False
        self.ng_plus_count      = 0

        # upgrade_id → current_level
        self.upgrade_levels: dict[str, int] = {u[0]: 0 for u in META_UPGRADES}

        self.wanted_level     = 0
        self._wanted_timer    = 0.0
        self._wanted_decay    = 120.0   # seconds between wanted level decrements

        self.title_system     = TitleSystem()
        self.captain_log: list[str] = []

        # Subscribe to events
        bus.subscribe("enemy_killed",   self._on_kill)
        bus.subscribe("quest_completed",self._on_quest_complete)
        bus.subscribe("boss_defeated",  self._on_boss)

    # ── Progression points ────────────────────────────────────────────────────
    def _on_kill(self, **kwargs) -> None:
        self.total_kills += 1
        # Base 1 pt/kill + any kill_pts_bonus upgrades
        bonus = int(self.get_upgrade_value("kill_pts_bonus", 0))
        pts   = POINTS_PER_KILL + bonus
        self.progression_points += pts
        self.wanted_level = min(MAX_WANTED_LEVEL,
                                self.wanted_level + 1 if self.total_kills % 10 == 0 else self.wanted_level)
        self.title_system.update(self.total_kills, self.wanted_level)
        self.captain_log.append(f"Kill #{self.total_kills}")

    def _on_quest_complete(self, quest=None, **kwargs) -> None:
        self.progression_points += POINTS_QUEST_BONUS
        if quest:
            self.captain_log.append(f"Quest complete: {quest.title}")
        bus.publish("notification",
                    msg=f"+{POINTS_QUEST_BONUS} progression points (quest)",
                    color=(60, 200, 80))

    def _on_boss(self, boss_id="", **kwargs) -> None:
        self.progression_points += POINTS_BOSS_BONUS
        self.captain_log.append(f"Boss defeated: {boss_id}")
        bus.publish("notification",
                    msg=f"+{POINTS_BOSS_BONUS} progression points (boss)",
                    color=(255, 160, 40))

    # ── Wanted level ──────────────────────────────────────────────────────────
    def update(self, dt: float) -> None:
        if self.wanted_level > 0:
            self._wanted_timer += dt
            if self._wanted_timer >= self._wanted_decay:
                self._wanted_timer = 0.0
                self.wanted_level  = max(0, self.wanted_level - 1)

    def add_piracy(self, amount: int = 1) -> None:
        self.wanted_level = min(MAX_WANTED_LEVEL, self.wanted_level + amount)

    # ── Upgrade tree ──────────────────────────────────────────────────────────
    def get_upgrade(self, uid: str) -> tuple | None:
        for u in META_UPGRADES:
            if u[0] == uid:
                return u
        return None

    def level_cost(self, uid: str) -> int:
        """Cost to buy the *next* level: base_cost × (current_level + 1)."""
        upg = self.get_upgrade(uid)
        if not upg:
            return 9999
        base_cost   = upg[3]
        next_level  = self.upgrade_levels.get(uid, 0) + 1
        return base_cost * next_level

    def can_purchase(self, uid: str) -> tuple[bool, str]:
        upg = self.get_upgrade(uid)
        if not upg:
            return False, "Unknown upgrade"
        _id, name, desc, base_cost, max_lvl = upg[0], upg[1], upg[2], upg[3], upg[4]
        current = self.upgrade_levels.get(uid, 0)
        if current >= max_lvl:
            return False, "Max level"
        if uid.startswith("ng_") and not self.ng_plus:
            return False, "Requires New Game+"
        cost = self.level_cost(uid)
        if self.progression_points < cost:
            return False, f"Need {cost} pts"
        return True, "OK"

    def purchase(self, uid: str) -> dict:
        ok, reason = self.can_purchase(uid)
        if not ok:
            return {"ok": False, "reason": reason}
        cost = self.level_cost(uid)
        upg  = self.get_upgrade(uid)
        self.progression_points -= cost
        self.spent_points       += cost
        self.upgrade_levels[uid] = self.upgrade_levels.get(uid, 0) + 1
        bus.publish("meta_upgrade_purchased", uid=uid, level=self.upgrade_levels[uid])
        return {"ok": True, "upgrade": upg[1], "level": self.upgrade_levels[uid]}

    def get_upgrade_value(self, effect_key: str, default=0):
        """Sum of all values for a given effect_key across upgrades."""
        total = default
        for u in META_UPGRADES:
            _id, _n, _d, _c, _ml, key, val = u[0], u[1], u[2], u[3], u[4], u[5], u[6]
            if key == effect_key:
                lvl = self.upgrade_levels.get(_id, 0)
                total += val * lvl
        return total

    # ── Starting bonuses for new run ──────────────────────────────────────────
    def starting_bonuses(self) -> dict:
        return {
            "hull_bonus":     int(self.get_upgrade_value("hull_bonus",    0)),
            "credits_bonus":  int(self.get_upgrade_value("credits_bonus", 0)),
            "fuel_bonus":     int(self.get_upgrade_value("fuel_bonus",    0)),
            "luck":           self.get_upgrade_value("luck",              0.0),
            "crew_slots":     int(self.get_upgrade_value("crew_slots",    0)),
            "fleet_slots":    int(self.get_upgrade_value("fleet_slots",   0)),
            "start_xp":       int(self.get_upgrade_value("start_xp",     0)),
            "morale_floor":   int(self.get_upgrade_value("morale_floor",  0)),
            "shield_bonus":   int(self.get_upgrade_value("shield_bonus",  0)),
            "speed_bonus":    int(self.get_upgrade_value("speed_bonus",   0)),
            "damage_pct":     self.get_upgrade_value("damage_pct",       0.0),
            "evasion_bonus":  self.get_upgrade_value("evasion_bonus",    0.0),
            "repair_bonus":   self.get_upgrade_value("repair_bonus",     0.0),
        }

    # ── Death handling ────────────────────────────────────────────────────────
    def on_death(self, run_kills: int) -> dict:
        self.total_runs += 1
        self.captain_log.append(f"--- Run {self.total_runs} ended (kills: {run_kills}) ---")
        self.wanted_level = 0
        return {
            "runs":          self.total_runs,
            "total_kills":   self.total_kills,
            "banked_points": self.progression_points,
        }

    # ── New Game+ ─────────────────────────────────────────────────────────────
    def trigger_ng_plus(self) -> None:
        self.ng_plus       = True
        self.ng_plus_count += 1
        self.captain_log.append(f"=== NEW GAME+ (run {self.ng_plus_count}) ===")
        bus.publish("ng_plus_triggered", count=self.ng_plus_count)

    # ── Captain origin bonuses ────────────────────────────────────────────────
    @staticmethod
    def origin_bonuses(origin: str) -> dict:
        return {
            "ex_military":       {"hull_bonus": 30,    "combat_stat_bonus": 3,
                                  "gunnery_stat_bonus": 2},
            "born_pirate":       {"credits_bonus": 400, "luck_bonus": 0.1,
                                  "speed_bonus": 5},
            "escaped_prisoner":  {"speed_bonus": 15,   "gunnery_stat_bonus": 3,
                                  "evasion_bonus": 0.03},
            "merchant_defector": {"credits_bonus": 800, "trade_discount": 0.1,
                                  "cargo_pct": 0.2},
            "rogue_engineer":    {"shield_bonus": 40,   "repair_bonus": 2.0,
                                  "drone_slots_bonus": 1},
            "void_wanderer":     {"fuel_bonus": 60,     "evasion_bonus": 0.05,
                                  "luck_bonus": 0.05,  "credits_bonus": 200},
        }.get(origin, {})

    # ── Serialization ─────────────────────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "progression_points": self.progression_points,
            "spent_points":       self.spent_points,
            "total_kills":        self.total_kills,
            "total_runs":         self.total_runs,
            "ng_plus":            self.ng_plus,
            "ng_plus_count":      self.ng_plus_count,
            "upgrade_levels":     self.upgrade_levels,
            "wanted_level":       self.wanted_level,
            "title":              self.title_system.to_dict(),
            "captain_log":        self.captain_log[-200:],
        }

    def load_from_dict(self, data: dict) -> None:
        self.progression_points = data.get("progression_points", 0)
        self.spent_points       = data.get("spent_points",       0)
        self.total_kills        = data.get("total_kills",        0)
        self.total_runs         = data.get("total_runs",         0)
        self.ng_plus            = data.get("ng_plus",            False)
        self.ng_plus_count      = data.get("ng_plus_count",      0)
        self.upgrade_levels.update(data.get("upgrade_levels",   {}))
        self.wanted_level       = data.get("wanted_level",       0)
        self.title_system.load_from_dict(data.get("title",      {}))
        self.captain_log        = data.get("captain_log",       [])
