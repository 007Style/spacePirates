"""core/game.py — Main Game class with full integrated state machine."""
from __future__ import annotations
import math
import pygame
from settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS, TITLE,
    DARK_BG, State, COMBAT_SPEED_DEFAULT,
)
from core.events import bus


class Game:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        self.screen  = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(TITLE)
        self.clock   = pygame.time.Clock()
        self.running = True

        # Accessibility / settings
        self.combat_speed        = COMBAT_SPEED_DEFAULT
        self.colorblind          = False
        self.font_size           = "M"
        self.show_damage_numbers = True
        self.show_minimap        = True
        self.screen_shake        = True
        self.music_volume        = 0.4
        self.sfx_volume          = 0.7
        self.enemy_health_bars   = True
        self.autopause_on_raid   = True   # auto-pause combat when raid starts
        self.particle_effects    = True   # enable/disable explosion particles
        self.show_fps            = False  # overlay FPS counter in-game
        self.difficulty          = "normal"   # "easy" | "normal" | "hard"
        self.autosave_interval   = 300    # seconds between auto-saves (0=off)
        self._autosave_timer     = 0.0

        # Extended settings
        self.crosshair_style     = "cross"   # "cross" | "dot" | "circle" | "none"
        self.hud_opacity         = 1.0       # 0.5 to 1.0
        self.auto_collect_debris = True      # fly over debris to auto-collect
        self.show_hints          = True      # in-combat hint overlays
        self.boarding_auto_attack= True      # ENTER = auto-attack in boarding
        self.radar_zoom          = 1.0       # radar scale: 0.5=zoomed in, 2.0=zoomed out

        # Active state
        self.state = State.MAIN_MENU

        # Subsystems (lazy-loaded when game starts)
        self.player_fleet     = None
        self.home_base        = None
        self.galaxy           = None
        self.meta_progression = None
        self.reputation_mgr   = None
        self.quest_manager    = None
        self.economy          = None
        self.save_slot        = 0
        self.playtime         = 0.0

        # UI systems
        self.hud              = None
        self.split_screen     = None
        self.photo_mode       = None
        self.codex            = None
        self.crew_menu        = None
        self.job_board        = None
        self.bounty_board     = None

        # Active combat (set when entering a sector with enemies)
        self.active_combat    = None

        # Screen registry
        self._screens: dict = {}
        self._init_ui()

        # Audio & particles
        from core.audio     import AudioManager
        from core.particles import ParticleSystem
        self.audio     = AudioManager()
        self.particles = ParticleSystem()

        # Subscribe to events
        bus.subscribe("notification",        self._on_notification)
        bus.subscribe("state_changed",       self._on_state_changed)
        bus.subscribe("base_raid_started",   self._on_base_raid)
        bus.subscribe("raid_warning_started",self._on_raid_warning)

    # ── UI init ───────────────────────────────────────────────────────────────
    def _init_ui(self):
        from ui.menus       import register_all_menus
        from ui.hud         import HUD
        from ui.splitscreen import SplitScreen
        from ui.codex       import Codex
        from ui.menus       import PhotoMode, CrewManagementMenu

        self.hud          = HUD()
        self.split_screen = SplitScreen()
        self.photo_mode   = PhotoMode()
        self.codex        = Codex()
        self.crew_menu    = CrewManagementMenu()
        register_all_menus(self)
        # Register codex as a navigable screen state
        self.register_screen("codex_screen", self.codex)

    # ── Game start (called from origin select) ────────────────────────────────
    def start_new_game(self, origin: str = "born_pirate",
                       ship_id: str | None = None) -> None:
        import json
        from entities.ship       import Ship
        from entities.weapon     import Weapon
        from entities.crew       import Crew
        from fleet.fleet         import Fleet
        from base.home_base      import HomeBase
        from world.galaxy        import Galaxy
        from world.economy       import Economy
        from progression.meta    import MetaProgression
        from factions.reputation import ReputationManager
        from quests.story        import StoryManager
        from quests.procedural   import JobBoard
        from quests.bounty       import BountyBoard

        # Meta progression (persists)
        if self.meta_progression is None:
            self.meta_progression = MetaProgression()

        meta = self.meta_progression
        bonuses = meta.starting_bonuses()
        origin_bonuses = MetaProgression.origin_bonuses(origin)

        # Galaxy
        self.galaxy = Galaxy()

        # Reputation
        self.reputation_mgr = ReputationManager()

        # Home base
        self.home_base = HomeBase(wanted_level_ref=lambda: meta.wanted_level)
        self.home_base.add_resource("credits", bonuses.get("credits_bonus", 0)
                                    + origin_bonuses.get("credits_bonus", 0))
        self.home_base.add_resource("fuel",    bonuses.get("fuel_bonus", 0))

        # Economy
        self.economy = Economy(self.galaxy, self.reputation_mgr)

        # Fleet & player ship
        with open("data/ships.json")   as f: ships_data   = json.load(f)
        with open("data/crew.json")    as f: crew_data     = json.load(f)
        with open("data/weapons.json") as f: weapons_data  = json.load(f)

        # Pick ship by chosen ship_id, fall back to first ship
        _ship_map = {s["id"]: s for s in ships_data}
        _chosen   = (_ship_map.get(ship_id) if ship_id else None) or ships_data[0]
        player_ship = Ship(_chosen)
        # Ensure reasonable starting crew/hardpoint minimums
        player_ship.crew_slots = max(player_ship.crew_slots, 8)
        if not player_ship.hardpoint_slots.get("small"):
            player_ship.hardpoint_slots = {"small": 3, "medium": 1, "large": 0}

        # ── Apply meta-progression bonuses ────────────────────────────────────
        hull_b   = bonuses.get("hull_bonus",   0) + origin_bonuses.get("hull_bonus",   0)
        shield_b = bonuses.get("shield_bonus", 0)
        speed_b  = bonuses.get("speed_bonus",  0) + origin_bonuses.get("speed_bonus",  0)
        evasion_b= bonuses.get("evasion_bonus",0.0)

        player_ship.hull      += hull_b
        player_ship.max_hull  += hull_b
        player_ship.shield    += shield_b
        player_ship.max_shield+= shield_b
        player_ship.speed     += speed_b
        player_ship.base_evasion = min(0.60, player_ship.base_evasion + evasion_b)
        player_ship.fuel      += bonuses.get("fuel_bonus", 0)

        # Passive repair rate from meta upgrade
        if bonuses.get("repair_bonus", 0.0):
            player_ship._hp_regen = player_ship._hp_regen + bonuses["repair_bonus"]

        # Damage multiplier stored on ship for SpaceCombat to pick up
        player_ship._meta_damage_pct = bonuses.get("damage_pct", 0.0)

        player_ship.x = SCREEN_WIDTH * 0.3
        player_ship.y = SCREEN_HEIGHT // 2

        # 8 starter crew — diverse roles, guaranteed regardless of crew.json size
        start_xp   = bonuses.get("start_xp", 0)
        import random as _r
        _STARTER_CREW = [
            {"id":"sc_0","name":"Hawk (Pilot)",    "role":"pilot",      "rarity":"common",  "stats":{"combat":4,"piloting":8,"gunnery":4,"engineering":3,"repair":3}},
            {"id":"sc_1","name":"Bolt (Gunner)",   "role":"gunner",     "rarity":"common",  "stats":{"combat":5,"piloting":4,"gunnery":8,"engineering":2,"repair":2}},
            {"id":"sc_2","name":"Wrench (Eng)",    "role":"engineer",   "rarity":"common",  "stats":{"combat":3,"piloting":2,"gunnery":3,"engineering":8,"repair":6}},
            {"id":"sc_3","name":"Grit (Brawler)",  "role":"combat",     "rarity":"common",  "stats":{"combat":9,"piloting":2,"gunnery":4,"engineering":2,"repair":2}},
            {"id":"sc_4","name":"Doc (Medic)",     "role":"mechanic",   "rarity":"common",  "stats":{"combat":3,"piloting":3,"gunnery":2,"engineering":5,"repair":9}},
            {"id":"sc_5","name":"Nav (Navigator)", "role":"pilot",      "rarity":"common",  "stats":{"combat":3,"piloting":6,"gunnery":3,"engineering":4,"repair":3}},
            {"id":"sc_6","name":"Sparks (Tech)",   "role":"engineer",   "rarity":"uncommon","stats":{"combat":4,"piloting":3,"gunnery":4,"engineering":9,"repair":7}},
            {"id":"sc_7","name":"Fang (Combat)",   "role":"combat",     "rarity":"uncommon","stats":{"combat":10,"piloting":3,"gunnery":5,"engineering":2,"repair":2}},
        ]
        for cdata_sc in _STARTER_CREW:
            c = Crew(cdata_sc)
            c.add_xp(start_xp)
            player_ship.add_crew(c)

        # 3 starter weapons (3 pulse lasers)
        for _ in range(3):
            player_ship.add_weapon(Weapon(weapons_data[0]))

        player_ship.equip_best()

        self.player_fleet = Fleet(self.home_base, self.meta_progression)
        self.player_fleet.add_ship(player_ship)

        # Quests
        self.quest_manager = StoryManager(self.reputation_mgr)
        self.job_board     = JobBoard()
        self.bounty_board  = BountyBoard()

        # Unlock starter lore entries so the codex isn't empty
        if self.codex:
            for entry_id in ("lore_pirates", "lore_ship_classes"):
                self.codex._unlocked.add(entry_id)

        # Mirror starting crew into home_base._hired_crew so the Crew tab shows them
        for cdata_sc in _STARTER_CREW:
            self.home_base._hired_crew.append({
                "name":   cdata_sc["name"],
                "role":   cdata_sc["role"],
                "rarity": cdata_sc["rarity"],
                "combat": cdata_sc["stats"]["combat"],
            })

        self.playtime    = 0.0
        self._run_origin = origin   # stored so start_combat can apply per-origin bonuses
        self.change_state(State.BASE)

    # ── Screen registry ───────────────────────────────────────────────────────
    def register_screen(self, state: str, screen_obj) -> None:
        self._screens[state] = screen_obj

    # ── State machine ─────────────────────────────────────────────────────────
    def change_state(self, new_state: str, **kwargs) -> None:
        old = self.state
        self.state = new_state

        # Entering BASE with an origin kwarg means we're starting a new game
        if new_state == State.BASE and kwargs.get("origin"):
            self.start_new_game(kwargs["origin"],
                                ship_id=kwargs.get("ship_id"))
            return  # start_new_game calls change_state(BASE) again without origin

        bus.publish("state_changed", old=old, new=new_state, **kwargs)

    # ── Main loop ─────────────────────────────────────────────────────────────
    def run(self) -> None:
        while self.running:
            raw_dt = self.clock.tick(FPS) / 1000.0
            dt     = raw_dt * (self.combat_speed if self.state == State.PLAYING else 1.0)
            self.playtime += raw_dt

            self.handle_events()
            self.update(dt)
            self.draw()
            pygame.display.flip()
        pygame.quit()

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return

            # ── Game Over screen inputs ──────────────────────────────────────
            if self.state == State.GAME_OVER:
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        self.start_new_game()
                        return
                    if event.key == pygame.K_ESCAPE:
                        self.change_state(State.MAIN_MENU)
                        return
                    # Scroll tree with arrow keys
                    if event.key == pygame.K_DOWN:
                        self._game_over_scroll = getattr(self, "_game_over_scroll", 0) + 40
                    if event.key == pygame.K_UP:
                        self._game_over_scroll = max(0, getattr(self, "_game_over_scroll", 0) - 40)
                # Mouse-wheel scrolls the tree
                if event.type == pygame.MOUSEWHEEL:
                    self._game_over_scroll = max(
                        0, getattr(self, "_game_over_scroll", 0) - event.y * 30)
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mx, my = event.pos
                    if getattr(self, "_game_over_retry_btn", None) and \
                            self._game_over_retry_btn.collidepoint(mx, my):
                        self.start_new_game()
                        return
                    if getattr(self, "_game_over_save_btn", None) and \
                            self._game_over_save_btn.collidepoint(mx, my):
                        self._do_save_game()
                        import time as _t
                        self._game_over_save_msg = f"Saved  {_t.strftime('%H:%M:%S')}"
                        self._game_over_save_ttl = 3.0
                        # do NOT return — stay on game over screen
                    if getattr(self, "_game_over_menu_btn", None) and \
                            self._game_over_menu_btn.collidepoint(mx, my):
                        self.change_state(State.MAIN_MENU)
                        return
                    # Tech tree node clicks
                    for uid, btn_rect in getattr(self, "_tree_node_rects", {}).items():
                        if btn_rect.collidepoint(mx, my):
                            if self.meta_progression:
                                result = self.meta_progression.purchase(uid)
                                if not result["ok"]:
                                    # Store brief flash message
                                    self._tree_msg = result["reason"]
                                    self._tree_msg_uid = uid
                                    self._tree_msg_ttl = 1.8
                            break
                continue  # swallow all other events on game over screen

            # ── Victory screen inputs ────────────────────────────────────────
            if (self.state == State.PLAYING and
                    getattr(self, "_victory_shown", False) and
                    self.active_combat and self.active_combat.sector_clear):
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    # "Return to Map" button dismisses — SPACE/ENTER no longer
                    # auto-dismisses so player can keep exploring
                    btn = getattr(self, "_victory_continue_btn", None)
                    if btn and btn.collidepoint(event.pos):
                        self._dismiss_victory()
                        return
                # Do NOT swallow other events — let player keep flying/collecting
                # The victory banner is a non-blocking overlay

            # Photo mode captures input first
            if self.photo_mode:
                self.photo_mode.handle_event(event)

            # Global hotkeys
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F12:
                    if self.photo_mode:
                        self.photo_mode.toggle()
                # ESC only pauses during combat; other states handle their own ESC
                if event.key == pygame.K_ESCAPE and self.state == State.PLAYING:
                    self.change_state(State.PAUSED)
                    return
                # ESC from upgrade tree / fleet / settings → back to base
                if event.key == pygame.K_ESCAPE and self.state in (
                        State.UPGRADE_TREE, "fleet_screen", "settings_screen"):
                    self.change_state(State.BASE)
                    return
                # ESC from codex → main menu (handled by the screen itself via "close")
                if event.key == pygame.K_ESCAPE and self.state == "codex_screen":
                    self.change_state(State.MAIN_MENU)
                    return
                # ESC from compendium → main menu
                if event.key == pygame.K_ESCAPE and self.state == "compendium_screen":
                    self.change_state(State.MAIN_MENU)
                    return
                # ESC from origin select → main menu
                if event.key == pygame.K_ESCAPE and self.state == State.ORIGIN_SELECT:
                    self.change_state(State.MAIN_MENU)
                    return
                # ESC during boarding = retreat and return to combat
                if event.key == pygame.K_ESCAPE and self.state == State.BOARDING:
                    from combat.boarding import BoardingAction
                    bc = getattr(self, "_active_boarding", None)
                    if bc:
                        bc.take_action(BoardingAction.RETREAT)
                    # retreat sets result; _draw_boarding will show outcome then
                    # return so global ESC handlers don't steal this event
                    return

            # Boarding screen click handling
            if self.state == State.BOARDING:
                bc = getattr(self, "_active_boarding", None)
                if bc:
                    from combat.boarding import BoardingResult, BoardingAction
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        mx, my = event.pos
                        # Action buttons
                        for action, btn in getattr(self, "_boarding_action_btns", []):
                            if btn.collidepoint(mx, my):
                                bc.take_action(action)
                        # Capture choice buttons
                        for cid, btn in getattr(self, "_capture_choice_btns", []):
                            if btn.collidepoint(mx, my):
                                self._resolve_capture_choice(cid)
                    if event.type == pygame.KEYDOWN:
                        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                            if bc.result == BoardingResult.ONGOING:
                                bc.take_action(BoardingAction.ATTACK)
                            else:
                                # Non-capture outcomes: return to combat
                                self._active_boarding = None
                                self.change_state(State.PLAYING)

            # Delegate to active combat
            if self.state == State.PLAYING and self.active_combat:
                action = self.active_combat.handle_event(event)
                if action == "board" and self.active_combat.boarding_target:
                    self._start_boarding(self.active_combat.boarding_target)
                    return
                if action == "raid":
                    loot = self.active_combat.raid_cargo_loot()
                    if loot and self.home_base:
                        for rtype, amount in loot.items():
                            self.home_base.add_resource(rtype, amount)
                        self.hud.push_notification(
                            f"Cargo raided! +{loot.get('metal',0)} metal  "
                            f"+{loot.get('fuel',0)} fuel  +{loot.get('credits',0)}cr",
                            (220, 180, 60))
                        bus.publish("sfx_play", key="raid_pickup")
                    return
                # Drone menu opened / closed / launched — no extra work needed here
                if action in ("drone_menu_open", "drone_menu_close", "drones_launched"):
                    return

            # Delegate to registered screen (upgrade tree, menus etc.)
            screen = self._screens.get(self.state)
            if screen and hasattr(screen, "handle_event"):
                result = screen.handle_event(event)
                # Codex / Compendium "close" → back to main menu
                if result == "close" and self.state in ("codex_screen", "compendium_screen"):
                    self.change_state(State.MAIN_MENU)

            # Crew menu events in combat
            if self.state == State.PLAYING and self.player_fleet and self.crew_menu:
                ship = self.player_fleet.active_ship
                if ship:
                    result = self.crew_menu.handle_event(
                        event, ship, combat=self.active_combat)
                    if result == "board":
                        target = (self.active_combat._nearest_boardable_enemy()
                                  if self.active_combat else None)
                        if target:
                            # Suppress fire on this ship before boarding
                            if self.active_combat:
                                self.active_combat._boarding_suppress_target = target
                                self.active_combat.boarding_target = target
                            self._start_boarding(target)
                        else:
                            # No valid target — inform the player
                            self.hud.push_notification(
                                "No boardable target!  Destroy shields first (or hull < 25%)",
                                (220, 140, 40))
                    elif result and result.startswith("launch_drone:"):
                        dtype = result.split(":", 1)[1]
                        if self.active_combat and self.active_combat.drone_system.max_slots > 0:
                            ok = self.active_combat.drone_system.launch(
                                dtype, ship.x, ship.y)
                            if ok:
                                self.hud.push_notification(
                                    f"▶ {dtype.capitalize()} drone launched!", (200, 200, 60))
                            else:
                                self.hud.push_notification(
                                    "Drone bay full or cooldown!", (180, 80, 40))

            # HUD Galaxy Map button (drawn on the main screen, checked before
            # splitting to panels — uses raw screen coords)
            if (self.state == State.PLAYING and
                    event.type == pygame.MOUSEBUTTONDOWN and event.button == 1):
                btn = getattr(self.hud, "galaxy_map_btn", None)
                if btn and btn.collidepoint(event.pos):
                    self.change_state(State.GALAXY_MAP)

            # Galaxy map
            if self.state == State.GALAXY_MAP and self.galaxy:
                result = self.galaxy.handle_event(event)
                self._handle_galaxy_nav(result, event)

            # Home base — handle nav bar returns and keyboard shortcuts
            if self.state == State.BASE and self.home_base:
                nav_result = self.home_base.handle_event(event)
                self._handle_base_nav(nav_result, event)

            # Fleet screen clicks
            if self.state == "fleet_screen" and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                # Back button
                if hasattr(self, "_fleet_back_btn") and self._fleet_back_btn.collidepoint(mx, my):
                    self.change_state(State.BASE)
                # Order buttons (fleet + captured ships)
                for ship_id, order, btn in getattr(self, "_fleet_order_buttons", []):
                    if btn.collidepoint(mx, my):
                        # Search both fleet ships and captured ships
                        all_ships = list(self.player_fleet.ships) + \
                                    list(getattr(self.player_fleet, "captured_ships", []))
                        ship = next((s for s in all_ships if s.id == ship_id), None)
                        if ship:
                            ship.fleet_order = order
                            self.hud.push_notification(
                                f"{ship.custom_name} → {order}", (80, 200, 80))
                # Hire crew buttons (post-mission hire pool)
                from entities.crew import Crew
                for idx, btn in getattr(self, "_fleet_hire_btns", []):
                    if btn.collidepoint(mx, my):
                        pool = getattr(self.player_fleet, "hire_pool", [])
                        if idx < len(pool) and self.home_base:
                            if self.home_base.spend_resource("credits", 200):
                                bus.publish("purchase_made")
                                crew_data = pool.pop(idx)
                                new_crew = Crew(crew_data)
                                if self.player_fleet.active_ship:
                                    added = self.player_fleet.active_ship.add_crew(new_crew)
                                    msg = (f"Hired {new_crew.name}!" if added
                                           else f"Hired {new_crew.name} (ship full).")
                                    self.hud.push_notification(msg, (60, 220, 80))
                            else:
                                self.hud.push_notification("Not enough credits!", (220, 60, 60))

            # Settings screen clicks
            if self.state == "settings_screen" and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                if hasattr(self, "_settings_back_btn") and self._settings_back_btn.collidepoint(mx, my):
                    self.change_state(State.BASE)
                for val, btn in getattr(self, "_settings_speed_btns", []):
                    if btn.collidepoint(mx, my):
                        self.combat_speed = val
                if hasattr(self, "_settings_cb_btn") and self._settings_cb_btn.collidepoint(mx, my):
                    self.colorblind = not self.colorblind
                for sz, btn in getattr(self, "_settings_font_btns", []):
                    if btn.collidepoint(mx, my):
                        self.font_size = sz
                # New settings toggles
                if hasattr(self, "_settings_dmg_btn") and self._settings_dmg_btn.collidepoint(mx, my):
                    self.show_damage_numbers = not self.show_damage_numbers
                if hasattr(self, "_settings_minimap_btn") and self._settings_minimap_btn.collidepoint(mx, my):
                    self.show_minimap = not self.show_minimap
                if hasattr(self, "_settings_shake_btn") and self._settings_shake_btn.collidepoint(mx, my):
                    self.screen_shake = not self.screen_shake
                if hasattr(self, "_settings_ehb_btn") and self._settings_ehb_btn.collidepoint(mx, my):
                    self.enemy_health_bars = not self.enemy_health_bars
                if hasattr(self, "_settings_autopause_btn") and self._settings_autopause_btn.collidepoint(mx, my):
                    self.autopause_on_raid = not self.autopause_on_raid
                if hasattr(self, "_settings_music_left") and self._settings_music_left.collidepoint(mx, my):
                    self.music_volume = max(0.0, round(self.music_volume - 0.1, 1))
                if hasattr(self, "_settings_music_right") and self._settings_music_right.collidepoint(mx, my):
                    self.music_volume = min(1.0, round(self.music_volume + 0.1, 1))
                if hasattr(self, "_settings_sfx_left") and self._settings_sfx_left.collidepoint(mx, my):
                    self.sfx_volume = max(0.0, round(self.sfx_volume - 0.1, 1))
                if hasattr(self, "_settings_sfx_right") and self._settings_sfx_right.collidepoint(mx, my):
                    self.sfx_volume = min(1.0, round(self.sfx_volume + 0.1, 1))
                # New settings toggles
                if hasattr(self, "_settings_particles_btn") and self._settings_particles_btn.collidepoint(mx, my):
                    self.particle_effects = not self.particle_effects
                if hasattr(self, "_settings_fps_btn") and self._settings_fps_btn.collidepoint(mx, my):
                    self.show_fps = not self.show_fps
                # Difficulty buttons
                for diff_val, btn in getattr(self, "_settings_diff_btns", []):
                    if btn.collidepoint(mx, my):
                        self.difficulty = diff_val
                # Auto-save interval buttons
                for iv_val, btn in getattr(self, "_settings_autosave_btns", []):
                    if btn.collidepoint(mx, my):
                        self.autosave_interval = iv_val
                        self._autosave_timer = 0.0
                # Save Game button
                if hasattr(self, "_settings_save_btn") and self._settings_save_btn.collidepoint(mx, my):
                    self._do_save_game()
                # New extended settings
                if hasattr(self, "_settings_hints_btn") and self._settings_hints_btn.collidepoint(mx, my):
                    self.show_hints = not self.show_hints
                if hasattr(self, "_settings_autocollect_btn") and self._settings_autocollect_btn.collidepoint(mx, my):
                    self.auto_collect_debris = not self.auto_collect_debris
                if hasattr(self, "_settings_boarding_auto_btn") and self._settings_boarding_auto_btn.collidepoint(mx, my):
                    self.boarding_auto_attack = not self.boarding_auto_attack
                for style, btn in getattr(self, "_settings_crosshair_btns", []):
                    if btn.collidepoint(mx, my):
                        self.crosshair_style = style
                for val, btn in getattr(self, "_settings_hud_opacity_btns", []):
                    if btn.collidepoint(mx, my):
                        self.hud_opacity = val
                for val, btn in getattr(self, "_settings_radar_zoom_btns", []):
                    if btn.collidepoint(mx, my):
                        self.radar_zoom = val

    def update(self, dt: float) -> None:
        # Auto-save timer
        if self.autosave_interval > 0 and self.state not in (
                State.MAIN_MENU, State.LOAD_SCREEN, State.GAME_OVER):
            self._autosave_timer += dt
            if self._autosave_timer >= self.autosave_interval:
                self._autosave_timer = 0.0
                self._do_save_game()

        # Tick game-over overlay messages
        if self.state == State.GAME_OVER:
            ttl = getattr(self, "_tree_msg_ttl", 0.0)
            if ttl > 0:
                self._tree_msg_ttl = max(0.0, ttl - dt)
            save_ttl = getattr(self, "_game_over_save_ttl", 0.0)
            if save_ttl > 0:
                self._game_over_save_ttl = max(0.0, save_ttl - dt)
                if self._game_over_save_ttl <= 0:
                    self._game_over_save_msg = ""

        # Update HUD notifications
        if self.hud:
            self.hud.update(dt)

        # Meta progression (wanted level decay)
        if self.meta_progression:
            self.meta_progression.update(dt)

        # Home base (raider timer)
        if self.home_base:
            self.home_base.update(dt)

        # Galaxy cargo ship animation
        if self.galaxy:
            self.galaxy.update(dt, home_base=self.home_base)

        # Fleet autonomy
        if self.player_fleet:
            self.player_fleet.update(dt)

        # Economy
        if self.economy:
            self.economy.update(dt)

        # Particles update
        if self.particles:
            self.particles.update(dt)

        # Active combat
        if self.state == State.PLAYING and self.active_combat:
            self.active_combat.update(dt)
            # Flush asteroid loot into home base
            for rtype, amount in self.active_combat._asteroid_loot:
                if self.home_base:
                    self.home_base.add_resource(rtype, amount)
            self.active_combat._asteroid_loot.clear()
            # When sector clears, snapshot the victory data once
            if self.active_combat.sector_clear and not getattr(self, "_victory_shown", False):
                self._victory_shown = True
                kills    = self.active_combat.kills
                credits  = kills * 100   # 100 credits per kill multiplier
                is_base_defense = getattr(self.active_combat, "_is_base_defense", False)
                sector_name = "Base Defense" if is_base_defense else (
                    self.galaxy.current_sector.name
                    if self.galaxy and self.galaxy.current_sector else "Unknown")
                self._victory_data  = {
                    "kills":           kills,
                    "credits":         credits,
                    "credits_per_kill":100,
                    "loot":            list(self.active_combat.loot_drops),
                    "sector":          sector_name,
                    "is_base_defense": is_base_defense,
                }
                # Add credits to base immediately so it persists
                if self.home_base:
                    self.home_base.add_resource("credits", credits)
                    if self._victory_data["loot"]:
                        self.home_base.add_resource("metal",
                                                    len(self._victory_data["loot"]) * 10)
                # Resolve the base defense wave
                if is_base_defense and self.home_base:
                    wave = getattr(self, "_base_defense_wave", None)
                    if wave:
                        self.home_base.raiders.resolve_wave([])
                        self._base_defense_wave = None
            # Defeat check (over but not sector_clear)
            if self.active_combat.over and not self.active_combat.sector_clear:
                self._on_combat_defeat()

        # Boarding state — auto-resolve each turn on update tick
        # (turn resolution is triggered by player input; see _draw_boarding)

        # Registered screen
        screen = self._screens.get(self.state)
        if screen and hasattr(screen, "update"):
            screen.update(dt)

    def draw(self) -> None:
        if self.state == State.PLAYING:
            self._draw_playing()
        elif self.state == State.BOARDING:
            self._draw_boarding()
        elif self.state == State.GAME_OVER:
            self._draw_game_over()
            return  # skip HUD on game over
        elif self.state == State.GALAXY_MAP and self.galaxy:
            self.galaxy.draw(self.screen)
        elif self.state == State.BASE and self.home_base:
            self.home_base.draw(self.screen, fleet=self.player_fleet)
        elif self.state == State.UPGRADE_TREE:
            screen = self._screens.get(State.UPGRADE_TREE)
            if screen:
                screen.draw(self.screen)
        elif self.state == "fleet_screen":
            self._draw_fleet_screen()
        elif self.state == "settings_screen":
            self._draw_settings_screen()
        else:
            screen = self._screens.get(self.state)
            if screen and hasattr(screen, "draw"):
                screen.draw(self.screen)
            else:
                self._draw_placeholder()

        # HUD notifications always on top
        if self.hud and self.state not in (State.MAIN_MENU, State.LOAD_SCREEN):
            self.hud._draw_notifications(self.screen)

        # FPS counter overlay (top-left, toggled via settings)
        if self.show_fps:
            fps_val = self.clock.get_fps()
            fps_font = pygame.font.SysFont("monospace", 11)
            fps_surf = fps_font.render(f"FPS: {fps_val:.0f}", True, (100, 200, 100))
            self.screen.blit(fps_surf, (4, 4))

        # Photo mode overlay
        if self.photo_mode and self.photo_mode.active:
            self.photo_mode.draw_overlay(self.screen)

    def _draw_raid_warning_overlay(self, warn_secs: float) -> None:
        """Small top-right corner countdown shown during combat when a raid is incoming."""
        import math as _math
        s     = self.screen
        sw, _ = s.get_size()
        mins  = int(warn_secs) // 60
        secs  = int(warn_secs) % 60
        t     = pygame.time.get_ticks() / 1000.0
        pulse = abs(_math.sin(t * 3))
        rc    = int(180 + 75 * pulse)
        font  = pygame.font.SysFont("monospace", 15, bold=True)
        text  = f"\u26a0 RAIDERS IN {mins}:{secs:02d}"
        surf  = font.render(text, True, (rc, 40, 40))
        wx    = sw - surf.get_width() - 14
        wy    = 52
        backing = pygame.Rect(wx - 6, wy - 4, surf.get_width() + 12, surf.get_height() + 8)
        pygame.draw.rect(s, (20, 5, 5), backing, border_radius=4)
        pygame.draw.rect(s, (rc, 40, 40), backing, 1, border_radius=4)
        s.blit(surf, (wx, wy))

    def _draw_victory_screen(self) -> None:
        """Full victory overlay shown over the combat view after sector clear."""
        from settings import (PANEL_BG, BORDER, TEXT_MAIN, TEXT_MUTED,
                               SUCCESS, WARNING, DANGER)
        s      = self.screen
        sw, sh = s.get_size()
        vd     = getattr(self, "_victory_data", {})

        font_lg = pygame.font.SysFont("monospace", 20, bold=True)
        font    = pygame.font.SysFont("monospace", 15)
        font_sm = pygame.font.SysFont("monospace", 12)

        # ── Non-blocking top banner (not a full overlay) ──────────────────────
        is_base_defense = vd.get("is_base_defense", False)
        kills     = vd.get("kills", 0)
        cred_per  = vd.get("credits_per_kill", 100)
        credits   = vd.get("credits", 0)
        title_text  = "BASE DEFENDED!" if is_base_defense else "SECTOR CLEAR!"
        title_color = (255, 200, 60) if is_base_defense else (80, 255, 100)

        banner_h = 110
        banner = pygame.Surface((sw, banner_h), pygame.SRCALPHA)
        banner.fill((0, 0, 0, 190))
        s.blit(banner, (0, 0))

        # Title
        title_s = font_lg.render(title_text, True, title_color)
        s.blit(title_s, (20, 6))

        # Kill multiplier
        mult_text = (f"{kills} kills × {cred_per}cr = +{credits}cr  |  "
                     f"You can still fly and collect resources!")
        mult_s = font.render(mult_text, True, (255, 220, 60))
        s.blit(mult_s, (20, 30))

        # Gather stats
        player_ship = (self.player_fleet.active_ship if self.player_fleet else None)
        hull_pct   = 0
        crew_alive = 0
        crew_total = 0
        if player_ship:
            hull_pct   = int(player_ship.hull / max(player_ship.max_hull, 1) * 100)
            crew_alive = sum(1 for c in player_ship.crew if not c.injured)
            crew_total = len(player_ship.crew)
        loot_names = [d.get("name", "?") for d in vd.get("loot", [])]
        metal_earned = len(vd.get("loot", [])) * 10

        stats_line = (f"Hull: {hull_pct}%  |  Crew: {crew_alive}/{crew_total}  |  "
                      f"+{metal_earned} metal  |  "
                      f"Drops: {', '.join(loot_names) if loot_names else 'none'}")
        stats_s = font_sm.render(stats_line, True, TEXT_MUTED)
        s.blit(stats_s, (20, 52))

        hint_s = font_sm.render(
            "Fly around to collect resources  —  click 'Return to Map' when done",
            True, (120, 200, 120))
        s.blit(hint_s, (20, 70))

        # ── "Return to Map" button — top-right corner, always visible ─────────
        btn_w, btn_h = 200, 36
        mx_m, my_m = pygame.mouse.get_pos()
        self._victory_continue_btn = pygame.Rect(sw - btn_w - 10, 8, btn_w, btn_h)
        hover = self._victory_continue_btn.collidepoint(mx_m, my_m)
        bg_c  = (30, 80, 50) if hover else (15, 50, 25)
        pygame.draw.rect(s, bg_c, self._victory_continue_btn, border_radius=5)
        pygame.draw.rect(s, SUCCESS, self._victory_continue_btn, 2, border_radius=5)
        cont = font_lg.render("↩ Return to Map", True, SUCCESS)
        s.blit(cont, (self._victory_continue_btn.centerx - cont.get_width() // 2,
                      self._victory_continue_btn.centery - cont.get_height() // 2))

    def _draw_playing(self) -> None:
        if not self.player_fleet or not self.player_fleet.active_ship:
            self._draw_placeholder()
            return

        ss   = self.split_screen
        ship = self.player_fleet.active_ship
        ss.begin_frame(self.screen)

        # Left: combat view
        if self.active_combat:
            self.active_combat.draw(ss.combat_surf)
        else:
            font = pygame.font.SysFont("monospace", 18)
            msg  = font.render("No active combat — press SPACE to pause / open map", True, (80, 80, 100))
            ss.combat_surf.blit(msg, (20, ss.combat_surf.get_height() // 2))

        # Right: crew management
        self.crew_menu.draw(ss.mgmt_surf, ship, combat=self.active_combat)

        ss.end_frame(self.screen)

        # HUD on top
        if self.hud:
            self.hud.draw(self.screen, ship, self.meta_progression,
                          self.active_combat,
                          crosshair_style=getattr(self, "crosshair_style", "cross"),
                          hud_opacity=getattr(self, "hud_opacity", 1.0))

        # Victory screen overlay (drawn over everything when sector is clear)
        if self.active_combat and self.active_combat.sector_clear and \
                getattr(self, "_victory_shown", False):
            self._draw_victory_screen()

        # Raid warning countdown overlay — visible even in combat so player
        # knows another wave is incoming while they're fighting
        if self.home_base:
            warn_secs = self.home_base.raiders.warning_seconds_left()
            if warn_secs > 0:
                self._draw_raid_warning_overlay(warn_secs)

    # ── Combat lifecycle ──────────────────────────────────────────────────────
    def start_combat(self, enemy_ships, nebula: bool = False) -> None:
        from combat.space_combat import SpaceCombat, set_particle_system
        ship = self.player_fleet.active_ship if self.player_fleet else None
        if not ship:
            return
        set_particle_system(self.particles)
        self.active_combat = SpaceCombat(ship, enemy_ships, nebula=nebula)
        # Give the combat engine a reference to the crew menu so AUTO works
        self.active_combat.crew_menu = self.crew_menu
        # Give combat a base reference so kill credits auto-flow to base wallet
        if getattr(self, "home_base", None):
            self.active_combat._base_ref = self.home_base
        # Pass settings flags to combat engine
        self.active_combat._auto_collect_debris = self.auto_collect_debris
        # Apply meta + origin drone_slots_bonus to drone system
        if self.meta_progression:
            bonus = int(self.meta_progression.get_upgrade_value("drone_slots_bonus", 0))
            self.active_combat.drone_system.max_slots += bonus
        # Apply origin-specific drone slots bonus (e.g. rogue_engineer +1)
        if getattr(self, "_run_origin", None) and self.meta_progression:
            from progression.meta import MetaProgression as _MP
            ob = _MP.origin_bonuses(self._run_origin)
            origin_drone = int(ob.get("drone_slots_bonus", 0))
            self.active_combat.drone_system.max_slots += origin_drone
        # Reset victory tracking for this new combat
        self._victory_shown = False
        self._victory_data  = {}
        self.change_state(State.PLAYING)

    def _start_boarding(self, target_ship) -> None:
        from combat.boarding import BoardingCombat
        ship   = self.player_fleet.active_ship
        # Use combat crew (non-injured) as troops — up to 4
        troops = [c for c in ship.crew
                  if not c.injured and c.stats.get("combat", 0) >= 5][:4]
        if not troops:
            troops = [c for c in ship.crew if not c.injured][:4]
        self._active_boarding = BoardingCombat(ship, target_ship)
        self._active_boarding.start_boarding(troops)
        self._boarding_choice_made = False
        # Launch visual boarding pod
        if self.active_combat:
            self.active_combat.launch_boarding_pod(target_ship)
        # Play boarding SFX + switch to high-intensity music
        bus.publish("boarding_started")
        self.change_state(State.BOARDING)

    def _draw_boarding(self) -> None:
        from combat.boarding import BoardingResult, BoardingAction
        from settings import DARK_BG, PANEL_BG, BORDER, ACCENT, TEXT_MAIN, TEXT_MUTED, SUCCESS, DANGER, WARNING, WHITE

        s  = self.screen
        bc = getattr(self, "_active_boarding", None)
        if not bc:
            self.change_state(State.PLAYING)
            return

        s.fill(DARK_BG)
        font_lg = pygame.font.SysFont("monospace", 22)
        font    = pygame.font.SysFont("monospace", 15)
        font_sm = pygame.font.SysFont("monospace", 12)

        # Header
        room = bc.current_room
        room_name = room.name if room else "—"
        hdr = font_lg.render(
            f"BOARDING: {bc.defender_ship.custom_name}  —  Room: {room_name}",
            True, (220, 80, 80))
        s.blit(hdr, (20, 14))

        prog_txt = font_sm.render(
            f"Room {bc.current_room_idx + 1}/{len(bc.rooms)}  "
            f"Turn {bc.turn}  "
            f"Troops: {sum(1 for c in bc.attackers if bc.attacker_hp.get(c.id, 0) > 0)}/{len(bc.attackers)}",
            True, TEXT_MUTED)
        s.blit(prog_txt, (20, 40))

        # ── Enemy ship rendered view (top-right panel) ────────────────────────
        ship_panel_w, ship_panel_h = 340, 110
        ship_panel_x = SCREEN_WIDTH - ship_panel_w - 10
        ship_panel_y = 8
        pygame.draw.rect(s, (8, 12, 24), (ship_panel_x, ship_panel_y,
                                           ship_panel_w, ship_panel_h))
        pygame.draw.rect(s, (100, 40, 40), (ship_panel_x, ship_panel_y,
                                             ship_panel_w, ship_panel_h), 1)
        # Draw title
        sp_title = font_sm.render(
            f"TARGET: {bc.defender_ship.custom_name}  [{bc.defender_ship.ship_class.upper()}]",
            True, (220, 80, 80))
        s.blit(sp_title, (ship_panel_x + 6, ship_panel_y + 4))
        # Render the ship sprite scaled up
        try:
            ship_img = bc.defender_ship._base_image
            # Scale to fit in panel with some padding (keep aspect ratio)
            max_w, max_h = ship_panel_w - 12, ship_panel_h - 30
            iw, ih = ship_img.get_size()
            scale = min(max_w / max(iw, 1), max_h / max(ih, 1), 3.5)
            new_w = max(1, int(iw * scale))
            new_h = max(1, int(ih * scale))
            scaled_ship = pygame.transform.scale(ship_img, (new_w, new_h))
            # Center horizontally in panel, vertically below title
            bx_ = ship_panel_x + (ship_panel_w - new_w) // 2
            by_ = ship_panel_y + 22 + (ship_panel_h - 26 - new_h) // 2
            s.blit(scaled_ship, (bx_, by_))
        except Exception:
            pass
        # Hull / shield bars on ship panel
        def_ship = bc.defender_ship
        hull_pct  = def_ship.hull / max(def_ship.max_hull, 1)
        shld_pct  = def_ship.shield / max(def_ship.max_shield, 1) if def_ship.max_shield else 0
        bar_x = ship_panel_x + 6
        bar_y = ship_panel_y + ship_panel_h - 22
        bar_w = ship_panel_w - 12
        # Hull bar
        pygame.draw.rect(s, (40, 10, 10), (bar_x, bar_y, bar_w, 7))
        pygame.draw.rect(s, DANGER, (bar_x, bar_y, int(bar_w * hull_pct), 7))
        hull_lbl = font_sm.render(
            f"Hull {def_ship.hull:.0f}/{def_ship.max_hull}", True, DANGER)
        s.blit(hull_lbl, (bar_x + 2, bar_y - 13))
        # Shield bar
        if def_ship.max_shield > 0:
            pygame.draw.rect(s, (10, 20, 50), (bar_x, bar_y + 9, bar_w, 5))
            pygame.draw.rect(s, (60, 140, 220),
                             (bar_x, bar_y + 9, int(bar_w * shld_pct), 5))

        # ── Combat log (left half, taller) ───────────────────────────────────
        log_rect = pygame.Rect(20, 60, SCREEN_WIDTH // 2 - 30, 300)
        pygame.draw.rect(s, PANEL_BG, log_rect)
        pygame.draw.rect(s, BORDER, log_rect, 1)
        log_title = font_sm.render("COMBAT LOG", True, ACCENT)
        s.blit(log_title, (log_rect.x + 6, log_rect.y + 4))
        log_lines = bc.log[-16:]
        for i, line in enumerate(log_lines):
            # Colour coding: crits=orange, down=red, cleared=green, def=red, warn=yellow
            lw = line.lower()
            if "[crit" in lw:
                col = (255, 160, 40)
            elif "✓" in line or "cleared" in lw or "captured" in lw:
                col = SUCCESS
            elif "✗" in line or "goes down" in lw or "repelled" in lw:
                col = DANGER
            elif "[def]" in lw:
                col = (220, 80, 80)
            elif "⚠" in line or "morale" in lw or "shaken" in lw:
                col = WARNING
            elif "breaches" in lw or "boarding party" in lw:
                col = (100, 180, 255)
            else:
                col = TEXT_MUTED
            lt = font_sm.render(line[:72], True, col)
            s.blit(lt, (log_rect.x + 4, log_rect.y + 20 + i * 17))

        # ── Right side: troop HP + boarding diagram ───────────────────────────
        atk_x   = SCREEN_WIDTH // 2 + 20
        diag_x  = SCREEN_WIDTH // 2 + 240   # diagram starts 220px right of HP bars

        # ── YOUR TROOPS HP bars ────────────────────────────────────────────────
        atk_y = 60
        s.blit(font.render("YOUR TROOPS", True, ACCENT), (atk_x, atk_y)); atk_y += 20
        for c in bc.attackers:
            hp    = bc.attacker_hp.get(c.id, 0)
            maxhp = c.stats.get("combat", 10) * 5
            pct   = max(0.0, hp / max(maxhp, 1))
            alive = hp > 0
            col   = SUCCESS if pct > 0.5 else (WARNING if pct > 0.2 else DANGER)
            pygame.draw.rect(s, (40, 10, 10), (atk_x, atk_y, 180, 10))
            if alive:
                pygame.draw.rect(s, col, (atk_x, atk_y, int(180 * pct), 10))
            nm = font_sm.render(
                f"{'●' if alive else '✗'} {c.name[:12]}  {hp:.0f}/{maxhp}  mor:{c.morale}",
                True, col if alive else (80, 80, 80))
            s.blit(nm, (atk_x, atk_y + 12)); atk_y += 30

        # ── ENEMY DEFENDERS HP bars ────────────────────────────────────────────
        def_y = atk_y + 14
        s.blit(font.render("ENEMY DEFENDERS", True, (220, 80, 80)), (atk_x, def_y))
        def_y += 20
        if room:
            for d in room.defenders:
                hp    = room.hp.get(d.id, 0)
                maxhp = d.stats.get("combat", 10) * 5
                pct   = max(0.0, hp / max(maxhp, 1))
                alive = hp > 0
                pygame.draw.rect(s, (40, 10, 10), (atk_x, def_y, 180, 10))
                if alive:
                    pygame.draw.rect(s, DANGER, (atk_x, def_y, int(180 * pct), 10))
                nm = font_sm.render(
                    f"{'◆' if alive else '✗'} {d.name[:12]}  {hp:.0f}/{maxhp}",
                    True, DANGER if alive else (80, 80, 80))
                s.blit(nm, (atk_x, def_y + 12)); def_y += 30

        # ── Boarding room diagram ──────────────────────────────────────────────
        # Shows a top-down grid of rooms with attackers (green ●) vs defenders (red ◆)
        if room:
            diag_top = 60
            dw, dh   = 340, 260   # diagram canvas
            # Panel
            diag_rect = pygame.Rect(diag_x, diag_top, dw, dh)
            pygame.draw.rect(s, (12, 18, 30), diag_rect)
            pygame.draw.rect(s, BORDER, diag_rect, 1)
            dtitle = font_sm.render(
                f"ROOM: {room.name}  ({bc.current_room_idx+1}/{len(bc.rooms)})",
                True, ACCENT)
            s.blit(dtitle, (diag_x + 4, diag_top + 4))

            # Draw all rooms as tiles
            room_tile_w = max(40, dw // max(len(bc.rooms), 1))
            room_tile_h = 40
            for ri, rm in enumerate(bc.rooms):
                rx = diag_x + 4 + ri * (room_tile_w + 2)
                ry = diag_top + 22
                if rx + room_tile_w > diag_x + dw - 4:
                    break
                is_current = (ri == bc.current_room_idx)
                is_cleared = rm.is_cleared
                bg_c  = (20, 60, 20) if is_cleared else ((30, 50, 80) if is_current else (20, 20, 35))
                bdr_c = SUCCESS if is_cleared else (ACCENT if is_current else BORDER)
                pygame.draw.rect(s, bg_c, (rx, ry, room_tile_w - 2, room_tile_h))
                pygame.draw.rect(s, bdr_c, (rx, ry, room_tile_w - 2, room_tile_h), 2 if is_current else 1)
                short_name = rm.name[:4]
                rl = font_sm.render(short_name, True, SUCCESS if is_cleared else (TEXT_MAIN if is_current else TEXT_MUTED))
                s.blit(rl, (rx + 2, ry + 2))
                # Door connector
                if ri < len(bc.rooms) - 1:
                    pygame.draw.line(s, BORDER,
                                     (rx + room_tile_w - 2, ry + room_tile_h // 2),
                                     (rx + room_tile_w + 2, ry + room_tile_h // 2), 2)

            # Current room combat figure
            fig_y = diag_top + 72
            # Left side: your troops (green circles)
            s.blit(font_sm.render("YOUR SQUAD", True, SUCCESS), (diag_x + 8, fig_y))
            fig_y += 16
            alive_atk = [c for c in bc.attackers if bc.attacker_hp.get(c.id, 0) > 0]
            dead_atk  = [c for c in bc.attackers if bc.attacker_hp.get(c.id, 0) <= 0]
            col_count = 4
            for idx, c in enumerate(alive_atk):
                fx = diag_x + 10 + (idx % col_count) * 34
                fy = fig_y  + (idx // col_count) * 38
                # Troop circle
                pygame.draw.circle(s, SUCCESS, (fx + 12, fy + 10), 11)
                pygame.draw.circle(s, (20, 100, 20), (fx + 12, fy + 10), 11, 2)
                # Role initial
                role_i = font_sm.render(c.role[0].upper(), True, (10, 10, 10))
                s.blit(role_i, (fx + 12 - role_i.get_width() // 2,
                                fy + 10 - role_i.get_height() // 2))
                # HP pip row
                hp_pct = bc.attacker_hp.get(c.id, 0) / max(c.stats.get("combat", 10) * 5, 1)
                for pip in range(5):
                    pc = SUCCESS if pip < hp_pct * 5 else (40, 40, 40)
                    pygame.draw.rect(s, pc, (fx + 4 + pip * 5, fy + 24, 4, 4))
            for idx, c in enumerate(dead_atk):
                fx = diag_x + 10 + ((len(alive_atk) + idx) % col_count) * 34
                fy = fig_y  + ((len(alive_atk) + idx) // col_count) * 38
                pygame.draw.circle(s, (80, 40, 40), (fx + 12, fy + 10), 11)
                pygame.draw.line(s, DANGER, (fx + 5, fy + 3), (fx + 19, fy + 17), 2)
                pygame.draw.line(s, DANGER, (fx + 19, fy + 3), (fx + 5, fy + 17), 2)

            # Right side: defenders (red diamonds)
            def_fig_y = fig_y + 80
            s.blit(font_sm.render("ENEMY DEFENDERS", True, DANGER),
                   (diag_x + 8, def_fig_y))
            def_fig_y += 16
            alive_defs = [d for d in room.defenders if room.hp.get(d.id, 0) > 0]
            dead_defs  = [d for d in room.defenders if room.hp.get(d.id, 0) <= 0]
            for idx, d in enumerate(alive_defs):
                fx = diag_x + 10 + (idx % col_count) * 34
                fy = def_fig_y + (idx // col_count) * 38
                # Enemy diamond shape
                pygame.draw.polygon(s, (180, 40, 40),
                    [(fx+12, fy+1), (fx+22, fy+11), (fx+12, fy+21), (fx+2, fy+11)])
                pygame.draw.polygon(s, DANGER,
                    [(fx+12, fy+1), (fx+22, fy+11), (fx+12, fy+21), (fx+2, fy+11)], 2)
                role_i = font_sm.render(d.role[0].upper(), True, (255, 200, 200))
                s.blit(role_i, (fx + 12 - role_i.get_width() // 2,
                                fy + 11 - role_i.get_height() // 2))
                hp_pct = room.hp.get(d.id, 0) / max(d.stats.get("combat", 10) * 5, 1)
                for pip in range(5):
                    pc = DANGER if pip < hp_pct * 5 else (40, 40, 40)
                    pygame.draw.rect(s, pc, (fx + 4 + pip * 5, fy + 24, 4, 4))
            for idx, d in enumerate(dead_defs):
                fx = diag_x + 10 + ((len(alive_defs) + idx) % col_count) * 34
                fy = def_fig_y + ((len(alive_defs) + idx) // col_count) * 38
                pygame.draw.polygon(s, (60, 20, 20),
                    [(fx+12, fy+1), (fx+22, fy+11), (fx+12, fy+21), (fx+2, fy+11)])
                pygame.draw.line(s, (120, 60, 60), (fx+5, fy+3), (fx+19, fy+17), 2)

        # Action buttons
        if bc.result == BoardingResult.ONGOING:
            actions = bc.get_available_actions()
            btn_colors = {
                BoardingAction.ATTACK:   ((20, 60, 20), SUCCESS),
                BoardingAction.HOSTAGE:  ((60, 40, 10), WARNING),
                BoardingAction.RETREAT:  ((60, 10, 10), DANGER),
            }
            self._boarding_action_btns = []
            bx = 20
            for action in actions:
                bg, fg = btn_colors.get(action, (PANEL_BG, TEXT_MAIN))
                lbl_map = {
                    BoardingAction.ATTACK:  "⚔ ATTACK",
                    BoardingAction.HOSTAGE: "✋ TAKE HOSTAGE",
                    BoardingAction.RETREAT: "← RETREAT",
                }
                lbl = lbl_map.get(action, action)
                bw  = max(130, font.size(lbl)[0] + 20)
                btn = pygame.Rect(bx, 380, bw, 40)
                pygame.draw.rect(s, bg, btn)
                pygame.draw.rect(s, fg, btn, 1)
                bt  = font.render(lbl, True, fg)
                s.blit(bt, (btn.centerx - bt.get_width() // 2,
                             btn.centery - bt.get_height() // 2))
                self._boarding_action_btns.append((action, btn))
                bx += bw + 12

        # Outcome screen
        elif bc.result in (BoardingResult.CAPTURED, BoardingResult.RETREATED,
                           BoardingResult.REPELLED):
            self._draw_boarding_outcome(s, bc, font_lg, font, font_sm)

        # ESC / B hint
        esc_txt = font_sm.render(
            "B or click action to take turn  |  ESC = Retreat", True, TEXT_MUTED)
        s.blit(esc_txt, (20, SCREEN_HEIGHT - 22))

        # Handle boarding keyboard input this frame
        keys = pygame.key.get_pressed()
        if keys[pygame.K_RETURN] or keys[pygame.K_KP_ENTER]:
            if bc.result == BoardingResult.ONGOING:
                bc.take_action(BoardingAction.ATTACK)

    def _draw_boarding_outcome(self, s, bc, font_lg, font, font_sm) -> None:
        from combat.boarding import BoardingResult
        from settings import SUCCESS, DANGER, WARNING, ACCENT, TEXT_MAIN, TEXT_MUTED, PANEL_BG, BORDER

        summary = bc.summary()
        result  = summary["result"]

        result_color = SUCCESS if result == BoardingResult.CAPTURED else DANGER
        result_text  = {
            BoardingResult.CAPTURED:  "SHIP CAPTURED!",
            BoardingResult.RETREATED: "BOARDED RETREATED",
            BoardingResult.REPELLED:  "BOARDING REPELLED",
        }.get(result, result)

        rt = font_lg.render(result_text, True, result_color)
        s.blit(rt, (SCREEN_WIDTH // 2 - rt.get_width() // 2, 300))

        if result == BoardingResult.CAPTURED:
            self._capture_choice_btns = []

            # ── Prominent CAPTURE CREW button ─────────────────────────────────
            capturable = summary.get("capturable_crew", [])
            cc_label = f"⚔  CAPTURE CREW  ({len(capturable)} available)"
            cc_btn = pygame.Rect(SCREEN_WIDTH // 2 - 180, 330, 360, 48)
            pygame.draw.rect(s, (30, 10, 50), cc_btn)
            pygame.draw.rect(s, (200, 80, 220), cc_btn, 2)
            cc_t = font_lg.render(cc_label, True, (220, 100, 255))
            s.blit(cc_t, (cc_btn.centerx - cc_t.get_width() // 2,
                           cc_btn.centery - cc_t.get_height() // 2))
            self._capture_choice_btns.append(("capture_crew", cc_btn))

            # ── Regular capture options ───────────────────────────────────────
            choices = [("keep",   "Keep Ship",       SUCCESS),
                       ("return", "Send to Base",    (80, 160, 255)),
                       ("strip",  "Strip for Parts", WARNING)]
            bx = SCREEN_WIDTH // 2 - (len(choices) * 175) // 2
            by = 396
            for cid, clabel, col in choices:
                btn = pygame.Rect(bx, by, 160, 36)
                pygame.draw.rect(s, (15, 15, 30), btn)
                pygame.draw.rect(s, col, btn, 1)
                ct = font.render(clabel, True, col)
                s.blit(ct, (btn.centerx - ct.get_width() // 2,
                             btn.centery - ct.get_height() // 2))
                self._capture_choice_btns.append((cid, btn))
                bx += 170

            hs = font_sm.render(
                f"Hostages: {', '.join(summary['hostages']) or 'none'}  |  "
                f"Survivors: {', '.join(summary['survivors']) or 'none'}",
                True, TEXT_MUTED)
            s.blit(hs, (SCREEN_WIDTH // 2 - hs.get_width() // 2, 444))
        else:
            cont = font.render("Press ESC or ENTER to return to combat", True, TEXT_MUTED)
            s.blit(cont, (SCREEN_WIDTH // 2 - cont.get_width() // 2, 380))

    def _resolve_capture_choice(self, choice: str) -> None:
        """Called when player picks keep / return to base / strip / capture_crew."""
        from settings import SUCCESS, DANGER, WARNING  # needed locally — not in module-level imports
        bc = getattr(self, "_active_boarding", None)
        if not bc:
            self.change_state(State.PLAYING)
            return

        captured_ship = bc.defender_ship

        if choice == "capture_crew":
            # Capture all crew from defender ship + add ship to captured_ships list
            crew_captured = list(captured_ship.crew)
            if self.player_fleet and self.player_fleet.active_ship:
                added_count = 0
                for crew_member in crew_captured:
                    if self.player_fleet.active_ship.add_crew(crew_member):
                        added_count += 1
                self.hud.push_notification(
                    f"Captured {added_count} crew from '{captured_ship.custom_name}'!",
                    (200, 100, 255))
            if self.player_fleet:
                captured_ship.fleet_order = "guard_base"
                captured_ship.color_scheme = (80, 160, 255)
                captured_ship._build_sprite()
                self.player_fleet.captured_ships.append(captured_ship)

        elif choice == "return":
            # Auto-assign the captured ship to return to home base
            captured_ship.fleet_order = "guard_base"
            captured_ship.color_scheme = (80, 160, 255)   # blue = friendly
            captured_ship._build_sprite()                  # rebuild sprite with new colour
            if self.player_fleet:
                added = self.player_fleet.add_ship(captured_ship)
                if added:
                    self.hud.push_notification(
                        f"'{captured_ship.custom_name}' captured! Heading to base.",
                        (80, 160, 255))
                else:
                    self.hud.push_notification(
                        "Fleet full! Ship abandoned.", (220, 120, 40))

        elif choice == "keep":
            # Recolour to cyan-friendly and rebuild sprite before adding as ally
            captured_ship.fleet_order  = "follow"
            captured_ship.color_scheme = (80, 220, 200)   # cyan = escort
            captured_ship._build_sprite()
            if self.player_fleet:
                self.player_fleet.add_ship(captured_ship)
                self.hud.push_notification(
                    f"'{captured_ship.custom_name}' follows you!", SUCCESS)
            # add_allied_ship removes it from enemy groups — do NOT remove again below
            if self.active_combat:
                self.active_combat.add_allied_ship(captured_ship)

        elif choice == "strip":
            # Add parts to armory / resources
            if self.home_base:
                self.home_base.add_resource("metal", int(captured_ship.price * 0.15))
            self.hud.push_notification("Ship stripped for parts.", (200, 160, 40))

        # ── Every captured ship yields +2 upgrade points + cargo ─────────────
        if self.meta_progression:
            self.meta_progression.progression_points += 2
            self.hud.push_notification(
                "Ship captured → +2 upgrade points!", (180, 120, 255))

        import random as _r
        cargo_metal   = _r.randint(15, 40)
        cargo_fuel    = _r.randint(8,  20)
        cargo_credits = _r.randint(30, 80)
        if self.home_base:
            self.home_base.add_resource("metal",   cargo_metal)
            self.home_base.add_resource("fuel",    cargo_fuel)
            self.home_base.add_resource("credits", cargo_credits)
        self.hud.push_notification(
            f"Cargo seized: +{cargo_metal} metal  +{cargo_fuel} fuel  +{cargo_credits}cr",
            (200, 180, 80))

        # Rescue captured hostages into crew roster
        for hostage in bc.hostages:
            if self.player_fleet and self.player_fleet.active_ship:
                self.player_fleet.active_ship.add_crew(hostage)

        # Remove captured ship from active combat enemy list.
        # For "keep", add_allied_ship already removed it — the guard below is safe
        # because it checks membership first before removing.
        if self.active_combat and captured_ship in self.active_combat.enemy_ships:
            self.active_combat.enemy_ships.remove(captured_ship)
            for ai in list(self.active_combat.ai_controllers):
                if ai.ship is captured_ship:
                    self.active_combat.ai_controllers.remove(ai)

        self._active_boarding = None
        if self.active_combat:
            self.active_combat._boarding_suppress_target = None
            self.active_combat.boarding_target = None
        self.change_state(State.PLAYING)

    def _dismiss_victory(self) -> None:
        """Called when player clicks Continue on the victory screen."""
        vd    = getattr(self, "_victory_data", {})
        loot  = vd.get("loot", [])
        is_base_defense = vd.get("is_base_defense", False)
        # Give weapon drop to player ship
        ship = self.player_fleet.active_ship if self.player_fleet else None
        if ship and loot:
            from entities.weapon import Weapon
            for drop in loot[:1]:
                try:
                    ship.add_weapon(Weapon(drop))
                    self.hud.push_notification(
                        f"Equipped: {drop.get('name','weapon')}!", (200, 200, 60))
                except Exception:
                    pass
        self._victory_shown = False
        self._victory_data  = {}
        self.active_combat  = None
        # Base defense returns to base; regular combat returns to galaxy map
        if is_base_defense:
            self.change_state(State.BASE)
        else:
            self.change_state(State.GALAXY_MAP)

    def _on_combat_victory(self) -> None:
        """Legacy — now unused; victory is handled via _dismiss_victory."""
        self.active_combat = None
        self.change_state(State.GALAXY_MAP)

    def _on_combat_defeat(self) -> None:
        # Snapshot death summary before clearing state
        self._death_summary = {
            "kills":    getattr(self.active_combat, "kills",     0),
            "playtime": int(getattr(self, "playtime", 0) / 60),
            "sector":   (self.galaxy.current_sector.name
                         if self.galaxy and self.galaxy.current_sector else "Unknown Sector"),
            "credits":  (self.home_base.get_resource("credits")
                         if self.home_base else 0),
        }
        self.active_combat = None
        # Award meta progression for the run
        if self.meta_progression:
            run_result = self.meta_progression.on_death(self._death_summary["kills"])
            self._death_summary["banked_points"] = run_result.get("banked_points", 0)
            self._death_summary["total_runs"]    = run_result.get("runs", 0)
        self.change_state(State.GAME_OVER)

    def _draw_game_over(self) -> None:
        """Full Game Over screen: death summary top bar, full upgrade tech tree, buttons."""
        from settings import (DARK_BG, PANEL_BG, BORDER, ACCENT,
                               TEXT_MAIN, TEXT_MUTED, DANGER, SUCCESS, WARNING)
        from progression.meta import META_UPGRADES, CATEGORY_ORDER, CATEGORY_LABELS, CATEGORY_COLORS

        s       = self.screen
        sw, sh  = s.get_size()
        s.fill(DARK_BG)
        mx_m, my_m = pygame.mouse.get_pos()

        font_xl  = pygame.font.SysFont("monospace", 38, bold=True)
        font_lg  = pygame.font.SysFont("monospace", 18, bold=True)
        font     = pygame.font.SysFont("monospace", 14)
        font_sm  = pygame.font.SysFont("monospace", 11)
        font_xs  = pygame.font.SysFont("monospace", 10)

        meta = self.meta_progression
        ds   = getattr(self, "_death_summary", {})
        pts  = meta.progression_points if meta else 0

        # ── TOP STRIP (fixed, not scrollable) ─────────────────────────────────
        STRIP_H = 80
        pygame.draw.rect(s, (14, 8, 22), (0, 0, sw, STRIP_H))
        pygame.draw.line(s, BORDER, (0, STRIP_H), (sw, STRIP_H))

        title = font_xl.render("SHIP DESTROYED", True, DANGER)
        s.blit(title, (20, 10))

        # Summary stats in a single row
        stat_x = 20
        for label, val, col in [
            ("Sector",    ds.get("sector",   "—"),              TEXT_MUTED),
            ("Kills",     str(ds.get("kills", 0)),              (255, 140, 40)),
            ("Playtime",  f"{ds.get('playtime', 0)}min",        TEXT_MUTED),
            ("Credits",   str(ds.get("credits", 0)),            (220, 200, 60)),
        ]:
            lbl_s = font_sm.render(f"{label}:", True, TEXT_MUTED)
            val_s = font.render(val, True, col)
            s.blit(lbl_s, (stat_x, 52))
            s.blit(val_s,  (stat_x, 62))
            stat_x += max(lbl_s.get_width(), val_s.get_width()) + 28

        # Points display (top-right)
        pts_s = font_lg.render(f"★ {pts} pts available", True, (255, 220, 60))
        s.blit(pts_s, (sw - pts_s.get_width() - 14, 12))
        run_s = font_sm.render(
            f"Run #{ds.get('total_runs', 1)}  |  Total kills: {meta.total_kills if meta else 0}  |  "
            f"Pts spent all-time: {meta.spent_points if meta else 0}",
            True, TEXT_MUTED)
        s.blit(run_s, (sw - run_s.get_width() - 14, 36))
        hint_s = font_xs.render("Scroll ↑↓ or mousewheel to browse tree", True, (60, 60, 80))
        s.blit(hint_s, (sw - hint_s.get_width() - 14, 54))

        # ── BOTTOM BUTTONS (fixed) ─────────────────────────────────────────────
        BTN_STRIP_H = 50
        BTN_Y = sh - BTN_STRIP_H
        pygame.draw.rect(s, (10, 6, 18), (0, BTN_Y, sw, BTN_STRIP_H))
        pygame.draw.line(s, BORDER, (0, BTN_Y), (sw, BTN_Y))

        btn_w, btn_h = 200, 36
        GAP = 10
        # Three buttons centred together: NEW RUN | SAVE GAME | MAIN MENU
        total_btns_w = btn_w * 3 + GAP * 2
        b_start = sw // 2 - total_btns_w // 2
        self._game_over_retry_btn = pygame.Rect(b_start,                     BTN_Y + 7, btn_w, btn_h)
        self._game_over_save_btn  = pygame.Rect(b_start + btn_w + GAP,       BTN_Y + 7, btn_w, btn_h)
        self._game_over_menu_btn  = pygame.Rect(b_start + (btn_w + GAP) * 2, BTN_Y + 7, btn_w, btn_h)

        save_col = (60, 160, 255)   # blue for save
        for btn, label, col in [
            (self._game_over_retry_btn, "▶  NEW RUN",    SUCCESS),
            (self._game_over_save_btn,  "💾  SAVE GAME", save_col),
            (self._game_over_menu_btn,  "⌂  MAIN MENU", TEXT_MUTED),
        ]:
            hover = btn.collidepoint(mx_m, my_m)
            bg    = tuple(min(255, c + 30) for c in col) if hover else PANEL_BG
            pygame.draw.rect(s, bg, btn, border_radius=5)
            pygame.draw.rect(s, col, btn, 2, border_radius=5)
            lbl = font_lg.render(label, True, col)
            s.blit(lbl, (btn.centerx - lbl.get_width() // 2,
                         btn.centery - lbl.get_height() // 2))

        # Show last-save confirmation if present
        save_msg = getattr(self, "_game_over_save_msg", "")
        if save_msg:
            sm = font_xs.render(save_msg, True, save_col)
            s.blit(sm, (self._game_over_save_btn.x,
                        BTN_Y + btn_h + 10))

        hint2 = font_xs.render("ENTER = New run    ESC = Main menu", True, TEXT_MUTED)
        s.blit(hint2, (14, BTN_Y + 17))

        # ── SCROLLABLE TECH TREE AREA ──────────────────────────────────────────
        TREE_Y0   = STRIP_H + 2
        TREE_MAXH = BTN_Y - TREE_Y0 - 2
        scroll    = getattr(self, "_game_over_scroll", 0)

        # Build clip region so nodes don't bleed into header/footer
        clip_rect = pygame.Rect(0, TREE_Y0, sw, TREE_MAXH)
        s.set_clip(clip_rect)

        # Node card dimensions
        CARD_W, CARD_H = 210, 108
        COL_GAP, ROW_GAP = 12, 10
        MARGIN_X = 16
        COLS = max(1, (sw - MARGIN_X * 2 + COL_GAP) // (CARD_W + COL_GAP))

        # Group upgrades by category
        cat_nodes: dict[str, list] = {c: [] for c in CATEGORY_ORDER}
        for u in META_UPGRADES:
            cat_nodes[u[7]].append(u)

        self._tree_node_rects: dict[str, pygame.Rect] = {}
        y_cursor = TREE_Y0 + 4 - scroll

        for cat in CATEGORY_ORDER:
            nodes = cat_nodes.get(cat, [])
            if not nodes:
                continue
            cat_col = CATEGORY_COLORS[cat]
            cat_lbl = CATEGORY_LABELS[cat]

            # Category header
            hdr_y = y_cursor
            if TREE_Y0 <= hdr_y < TREE_Y0 + TREE_MAXH:
                pygame.draw.rect(s, (14 + cat_col[0]//10, 8 + cat_col[1]//10, 20 + cat_col[2]//10),
                                 (MARGIN_X, hdr_y, sw - MARGIN_X * 2, 20), border_radius=3)
                hdr_t = font.render(f"── {cat_lbl} ──", True, cat_col)
                s.blit(hdr_t, (MARGIN_X + 6, hdr_y + 3))
            y_cursor += 24

            # Draw nodes in a grid
            col = 0
            row_start_y = y_cursor
            for u in nodes:
                uid, uname, udesc, ubase_cost, umax, ukey, uval, ucat, uicon = (
                    u[0], u[1], u[2], u[3], u[4], u[5], u[6], u[7], u[8])

                cur_lvl  = meta.upgrade_levels.get(uid, 0) if meta else 0
                maxed    = (cur_lvl >= umax)
                next_cost= meta.level_cost(uid) if meta else ubase_cost
                can_buy, reason = (meta.can_purchase(uid) if meta else (False, "no meta"))

                cx_card = MARGIN_X + col * (CARD_W + COL_GAP)
                cy_card = row_start_y

                rect = pygame.Rect(cx_card, cy_card, CARD_W, CARD_H)
                # Only register click rect if on screen
                if clip_rect.colliderect(rect):
                    self._tree_node_rects[uid] = rect

                # Only draw if visible in clip area
                if cy_card + CARD_H >= TREE_Y0 and cy_card <= TREE_Y0 + TREE_MAXH:
                    hov = rect.collidepoint(mx_m, my_m)

                    # Card background
                    if maxed:
                        bg_col   = (8, 28, 8)
                        brd_col  = (40, 140, 40)
                    elif can_buy:
                        bg_col  = (20, 30, 50) if not hov else (30, 45, 75)
                        brd_col = cat_col
                    else:
                        bg_col  = (18, 14, 22)
                        brd_col = (40, 40, 60)

                    pygame.draw.rect(s, bg_col, rect, border_radius=5)
                    pygame.draw.rect(s, brd_col, rect, 2 if can_buy or maxed else 1, border_radius=5)

                    # ── Icon + Name ───────────────────────────────────────────
                    tx = cx_card + 6
                    ty = cy_card + 5
                    try:
                        icon_s = font_lg.render(uicon, True, cat_col if not maxed else (80, 200, 80))
                        s.blit(icon_s, (tx, ty))
                        tx += icon_s.get_width() + 4
                    except Exception:
                        pass
                    name_s = font.render(uname, True,
                                         (80, 220, 80) if maxed else (TEXT_MAIN if can_buy else TEXT_MUTED))
                    s.blit(name_s, (tx, ty + 1))

                    # ── Description (wrapped to 2 lines) ─────────────────────
                    desc_y = cy_card + 23
                    words  = udesc.split()
                    line, lines = "", []
                    for w in words:
                        test = (line + " " + w).strip()
                        if font_xs.size(test)[0] <= CARD_W - 10:
                            line = test
                        else:
                            if line: lines.append(line)
                            line = w
                    if line: lines.append(line)
                    for dl in lines[:2]:
                        ds_s = font_xs.render(dl, True, TEXT_MUTED)
                        s.blit(ds_s, (cx_card + 6, desc_y))
                        desc_y += 12

                    # ── Level pips (5 filled circles) ─────────────────────────
                    pip_y = cy_card + CARD_H - 32
                    for pip in range(umax):
                        px_ = cx_card + 6 + pip * 14
                        filled = pip < cur_lvl
                        pc = (80, 220, 80) if maxed else (cat_col if filled else (30, 30, 50))
                        pygame.draw.circle(s, pc, (px_ + 5, pip_y + 5), 5)
                        pygame.draw.circle(s, (60, 60, 80), (px_ + 5, pip_y + 5), 5, 1)

                    # ── Cost / status row ─────────────────────────────────────
                    cost_y = cy_card + CARD_H - 18
                    if maxed:
                        cs = font_xs.render("✓ MAXED", True, (60, 200, 60))
                        s.blit(cs, (cx_card + 6, cost_y))
                    else:
                        cost_col = (255, 220, 60) if can_buy else (100, 80, 80)
                        cs = font_xs.render(f"Cost: {next_cost} pts  (Lv{cur_lvl+1}/{umax})",
                                            True, cost_col)
                        s.blit(cs, (cx_card + 6, cost_y))

                    # Per-level value preview (right-aligned)
                    val_str = (f"+{uval*100:.0f}%" if isinstance(uval, float) and uval < 2
                               else f"+{uval:.0f}")
                    vp = font_xs.render(val_str + "/lv", True, cat_col)
                    s.blit(vp, (cx_card + CARD_W - vp.get_width() - 4, cost_y))

                    # ── Flash error message on this node ──────────────────────
                    if (getattr(self, "_tree_msg_uid", None) == uid and
                            getattr(self, "_tree_msg_ttl", 0) > 0):
                        alpha = min(255, int(getattr(self, "_tree_msg_ttl", 0) / 1.8 * 255))
                        err_s = font_xs.render(getattr(self, "_tree_msg", ""), True, DANGER)
                        err_surf = pygame.Surface(err_s.get_size(), pygame.SRCALPHA)
                        err_surf.blit(err_s, (0, 0))
                        err_surf.set_alpha(alpha)
                        s.blit(err_surf, (cx_card + 4, cy_card + CARD_H - 30))

                # Advance grid position
                col += 1
                if col >= COLS:
                    col = 0
                    row_start_y += CARD_H + ROW_GAP

            # If last row didn't finish a full row, still advance
            if col > 0:
                row_start_y += CARD_H + ROW_GAP
            y_cursor = row_start_y + 8

        # Clamp scroll to content height
        content_h = max(0, y_cursor + scroll - TREE_Y0)
        self._game_over_scroll = min(scroll, max(0, content_h - TREE_MAXH + 40))

        s.set_clip(None)   # restore full drawing area

        # Scrollbar indicator (thin right edge)
        if content_h > TREE_MAXH:
            sb_h   = max(20, int(TREE_MAXH * TREE_MAXH / content_h))
            sb_y   = TREE_Y0 + int(scroll / content_h * TREE_MAXH)
            pygame.draw.rect(s, (60, 60, 100),
                             (sw - 6, sb_y, 4, sb_h), border_radius=2)

    # ── Galaxy map navigation handler ────────────────────────────────────────
    def _handle_galaxy_nav(self, result: str | None, event) -> None:
        import pygame as _pg
        # ESC always returns to base from galaxy map
        if event.type == _pg.KEYDOWN and event.key == _pg.K_ESCAPE:
            self.change_state(State.BASE)
            return
        # Back button click
        if result == "back":
            self.change_state(State.BASE)
            return

        if result and result.startswith("travel:"):
            sector_id = result.split(":", 1)[1]
            ship = self.player_fleet.active_ship if self.player_fleet else None
            if not ship:
                return
            travel_result = self.galaxy.travel_to(sector_id, ship)
            if not travel_result["success"]:
                self.hud.push_notification(
                    f"Cannot travel: {travel_result['reason']}", (220, 60, 60))
                return

            sector = self.galaxy.sectors[sector_id]
            self.hud.push_notification(
                f"Arrived at {sector.name}  (Fuel: {ship.fuel:.0f})",
                (60, 200, 80))

            # Home base → just switch state, no combat
            if sector.sector_id == "home_base":
                self.change_state(State.BASE)
                return

            # Safe nation sector → show map with info, no combat auto-start
            if sector.is_safe:
                self.hud.push_notification(
                    f"{sector.name} — safe zone, explore freely.", (60, 180, 255))
                # Stay on galaxy map — no auto combat
                return

            # Non-safe sector: stay on galaxy map, show BATTLE button
            # Player must click the BATTLE button to enter combat
            self.hud.push_notification(
                f"Arrived at {sector.name} — click BATTLE to fight!", (255, 200, 60))
            # Stay on GALAXY_MAP state — do not spawn combat yet

        elif result and result.startswith("battle:"):
            # Player clicked the BATTLE button — either at this sector or connected to it
            sector_id = result.split(":", 1)[1]
            ship = self.player_fleet.active_ship if self.player_fleet else None
            if not ship:
                return
            sector = self.galaxy.sectors.get(sector_id)
            if not sector:
                return

            # If player is not at the sector yet, travel there first automatically
            if sector_id != self.galaxy.current_sector_id:
                travel_result = self.galaxy.travel_to(sector_id, ship)
                if not travel_result["success"]:
                    self.hud.push_notification(
                        f"Cannot travel: {travel_result['reason']}", (220, 60, 60))
                    return
                self.hud.push_notification(
                    f"Jumping to {sector.name}…", (255, 200, 60))

            # Roll for random space event
            from world.events import EventManager
            em = EventManager()
            ev = em.roll_event()
            if ev:
                self.hud.push_notification(f"Event: {ev.title}", (255, 200, 80))
                outcome = ev.resolve(0, ship, self.player_fleet)
                if outcome.get("trigger") == "combat":
                    self._spawn_sector_combat(sector)
                elif outcome.get("damage"):
                    self.hud.push_notification(
                        f"Hull damage: -{outcome['damage']}", (220, 60, 60))
                elif outcome.get("reward"):
                    self.hud.push_notification(
                        f"Reward: {outcome['reward']}", (60, 200, 80))
                return

            # Normal sector — spawn combat
            self._spawn_sector_combat(sector)

        elif result and result.startswith("explore:"):
            # Player clicked EXPLORE DEPOT at mining depot
            sector_id = result.split(":", 1)[1]
            ship = self.player_fleet.active_ship if self.player_fleet else None
            if not ship:
                return
            # If not already there, travel first
            if sector_id != self.galaxy.current_sector_id:
                travel_result = self.galaxy.travel_to(sector_id, ship)
                if not travel_result["success"]:
                    self.hud.push_notification(
                        f"Cannot reach depot: {travel_result['reason']}", (220, 60, 60))
                    return
            # Give resources from the mining depot
            import random as _r
            yields = [
                ("metal",    _r.randint(25, 60)),
                ("fuel",     _r.randint(10, 30)),
                ("credits",  _r.randint(40, 120)),
            ]
            if self.home_base:
                for rtype, amount in yields:
                    self.home_base.add_resource(rtype, amount)
            msg = "  ".join(f"+{a} {r}" for r, a in yields)
            self.hud.push_notification(f"Mining Depot explored: {msg}", (80, 200, 255))
            # 30% chance of a random combat ambush
            sector = self.galaxy.sectors.get(sector_id)
            if sector and _r.random() < 0.30:
                self.hud.push_notification("Ambush! Pirates spotted the depot!", (220, 60, 60))
                self._spawn_sector_combat(sector)

        elif result and result.startswith("recruit:"):
            # Player clicked RECRUIT on an NPC pirate
            parts = result.split(":", 3)
            npc_name   = parts[1] if len(parts) > 1 else "Unknown"
            ship_class = parts[2] if len(parts) > 2 else "fighter"
            bonus      = parts[3] if len(parts) > 3 else ""
            # Add a new ship to the fleet
            import json as _j
            try:
                with open("data/ships.json") as f:
                    _sdata = _j.load(f)
                _smap = {s["id"]: s for s in _sdata}
                _cls_to_id = {"fighter": "fighter_mk2", "freighter": "freighter_mk1",
                              "carrier": "carrier_mk1"}
                _ship_id = _cls_to_id.get(ship_class, "fighter_mk1")
                from entities.ship import Ship
                new_ship = Ship(_smap.get(_ship_id, _sdata[0]))
                new_ship.custom_name  = f"{npc_name}'s Ship"
                new_ship.color_scheme = (220, 150, 60)
                new_ship._build_sprite()
                new_ship.fleet_order  = "follow"
                if self.player_fleet:
                    added = self.player_fleet.add_ship(new_ship)
                    if added:
                        self.hud.push_notification(
                            f"★ {npc_name} joined your fleet!  [{ship_class}]  Bonus: {bonus}",
                            (220, 160, 60))
                    else:
                        self.hud.push_notification("Fleet full! Cannot recruit.", (220, 120, 40))
            except Exception as e:
                self.hud.push_notification(f"Recruit failed: {e}", (220, 60, 60))

    def _spawn_sector_combat(self, sector) -> None:
        """Spawn enemy ships for a sector and launch combat."""
        import json, random
        from entities.ship   import Ship
        from entities.weapon import Weapon
        from entities.crew   import Crew

        try:
            with open("data/ships.json")   as f: ships_data   = json.load(f)
            with open("data/weapons.json") as f: weapons_data  = json.load(f)
            with open("data/crew.json")    as f: crew_data     = json.load(f)
        except Exception:
            self.hud.push_notification("Could not load enemy data!", (220, 60, 60))
            return

        ship_dict = {s["id"]: s for s in ships_data}
        enemy_ships = []
        count = sector.enemy_count()
        pool  = sector.enemy_pool or [ships_data[0]["id"]]

        player_ship = self.player_fleet.active_ship if self.player_fleet else None
        px = getattr(player_ship, "x", 0)
        py = getattr(player_ship, "y", 0)

        # Names for generic enemy crew
        _ENEMY_NAMES = [
            "Krix", "Vasha", "Dolan", "Mera", "Skol", "Thane", "Rill",
            "Vex", "Orun", "Czar", "Fyke", "Bela", "Naxx", "Zev",
        ]
        _ROLES = ["gunner", "pilot", "engineer", "combat", "mechanic"]

        for ship_idx in range(count):
            eid   = random.choice(pool)
            edata = ship_dict.get(eid, ships_data[0])
            e     = Ship(edata)

            # ── 20% chance: lightly-guarded / skeleton crew ship ──────────────
            lightly_guarded = (random.random() < 0.20)
            if lightly_guarded:
                # Weaker hull/shield — easy target, easy to board
                e.hull      = e.hull      * 1.0
                e.max_hull  = e.max_hull  * 1.0
                e.shield    = 0.0           # no shields — shield already down
                e.max_shield= e.max_shield  # keep capacity but start empty
                e.shield_recharge_lock = 30.0  # long recharge delay (easily boardable)
                e._enemy_shield_mode = False
                e.color_scheme = (160, 90, 90)  # slightly desaturated red
            else:
                # Multiply hull and shield for beefier sector enemies
                e.hull       = e.hull       * 2.5
                e.max_hull   = e.max_hull   * 2.5
                e.shield     = e.shield     * 2.0
                e.max_shield = e.max_shield * 2.0
                # Enable extended shield mode (25 s lock, slow regen)
                e._enemy_shield_mode = True
                e.color_scheme = (200, 60, 60)

            # Spawn enemies in a ring 500-900 px away from the player
            angle = random.uniform(0, 6.2832)
            dist  = random.randint(500, 900)
            e.x   = px + dist * math.cos(angle)
            e.y   = py + dist * math.sin(angle)
            # Arm the enemy
            if weapons_data:
                w_data = random.choice(weapons_data[:4])
                e.add_weapon(Weapon(w_data))

            # ── Crew setup ─────────────────────────────────────────────────────
            if lightly_guarded:
                # Only 1–2 startled crew with halved combat stats
                crew_count = random.randint(1, 2)
                for ci in range(crew_count):
                    name = random.choice(_ENEMY_NAMES) + f" {random.randint(1,99)}"
                    role = random.choice(_ROLES)
                    cdata = {
                        "id":    f"enemy_crew_{id(e)}_{ci}",
                        "name":  f"(Startled) {name}",
                        "role":  role,
                        "rarity": "common",
                        "stats": {
                            "combat":      random.randint(1, 3),   # halved — panicked
                            "piloting":    random.randint(1, 3),
                            "gunnery":     random.randint(1, 3),
                            "engineering": random.randint(1, 3),
                            "repair":      random.randint(1, 2),
                        },
                    }
                    try:
                        e.add_crew(Crew(cdata))
                    except Exception:
                        pass
                # Flag for notification
                e._lightly_guarded = True
            else:
                # Guarantee min 10 crew, max 10 capturable
                crew_count = max(10, len(e.crew))
                for ci in range(crew_count - len(e.crew)):
                    name  = random.choice(_ENEMY_NAMES) + f" {random.randint(1,99)}"
                    role  = random.choice(_ROLES)
                    cdata = {
                        "id":    f"enemy_crew_{id(e)}_{ci}",
                        "name":  name,
                        "role":  role,
                        "rarity": "common",
                        "stats": {
                            "combat":      random.randint(4, 8),
                            "piloting":    random.randint(2, 6),
                            "gunnery":     random.randint(3, 7),
                            "engineering": random.randint(2, 6),
                            "repair":      random.randint(2, 5),
                        },
                    }
                    try:
                        e.add_crew(Crew(cdata))
                    except Exception:
                        pass

            enemy_ships.append(e)

        self.start_combat(enemy_ships, nebula=sector.has_nebula)
        # Notify player about any lightly-guarded ships spotted on sensors
        light_count = sum(1 for e in enemy_ships if getattr(e, "_lightly_guarded", False))
        if light_count:
            self.hud.push_notification(
                f"Sensors: {light_count} lightly-guarded ship(s) detected — easy to board!",
                (255, 220, 80))

    # ── Base navigation handler ───────────────────────────────────────────────
    def _handle_base_nav(self, nav_result: str | None, event) -> None:
        """Route nav bar clicks and keyboard shortcuts from the base screen."""
        import pygame as _pg

        # Keyboard shortcuts on base screen
        if event.type == _pg.KEYDOWN:
            if event.key == _pg.K_g:
                nav_result = "galaxy_map"
            elif event.key == _pg.K_u:
                nav_result = "upgrade_tree"
            elif event.key == _pg.K_f:
                nav_result = "fleet_orders"
            elif event.key == _pg.K_c:
                nav_result = "crew_roster"

        if nav_result is None:
            return

        if nav_result == "quit_to_menu":
            self.change_state(State.MAIN_MENU)

        elif nav_result == "galaxy_map":
            self.change_state(State.GALAXY_MAP)

        elif nav_result == "upgrade_tree":
            self.change_state(State.UPGRADE_TREE)

        elif nav_result == "fleet_orders":
            self.change_state("fleet_screen")

        elif nav_result == "crew_roster":
            # Open the crew roster tab directly in the base screen
            if self.home_base:
                self.home_base._active_tab = self.home_base.TAB_ROSTER

        elif nav_result == "settings":
            self.change_state("settings_screen")

        elif nav_result and nav_result.startswith("build_result:"):
            parts = nav_result.split(":", 2)
            ok     = parts[1] == "True"
            reason = parts[2] if len(parts) > 2 else ""
            if ok:
                self.hud.push_notification("Building constructed!", (60, 200, 80))
            else:
                self.hud.push_notification(f"Cannot build: {reason}", (220, 60, 60))

        elif nav_result and nav_result.startswith("upgrade_result:"):
            parts = nav_result.split(":", 2)
            ok     = parts[1] == "True"
            reason = parts[2] if len(parts) > 2 else ""
            if ok:
                self.hud.push_notification("Building upgraded!", (60, 200, 80))
            else:
                self.hud.push_notification(f"Cannot upgrade: {reason}", (220, 60, 60))

    # ── Event handlers ─────────────────────────────────────────────────────────
    def _on_notification(self, msg="", color=None, **kwargs) -> None:
        if self.hud:
            self.hud.push_notification(msg, color)

    def _on_state_changed(self, old="", new="", **kwargs) -> None:
        pass  # hook for future transitions

    def _on_raid_warning(self, seconds=300, ship_count=1, **kwargs) -> None:
        """5-minute warning before raiders arrive."""
        mins = int(seconds) // 60
        if self.hud:
            self.hud.push_notification(
                f"⚠ RAIDERS INCOMING — {ship_count} ship(s) in {mins} minutes!",
                color=(220, 100, 30), duration=8.0)

    def _on_base_raid(self, wave=None, **kwargs) -> None:
        """Called when raiders actually arrive — start a base defense combat."""
        if self.hud:
            self.hud.push_notification(
                "⚠ BASE UNDER ATTACK! Defend the base!", color=(220, 50, 50), duration=8.0)
        # Auto-start base defense combat
        if wave and self.player_fleet and self.player_fleet.active_ship:
            self._start_base_defense(wave)

    def _start_base_defense(self, wave) -> None:
        """Launch normal combat against the raider wave, positioned near base."""
        import math as _math
        from combat.space_combat import SpaceCombat, set_particle_system
        ship = self.player_fleet.active_ship
        set_particle_system(self.particles)

        # Position enemy ships around the player
        import random as _rnd
        for i, raider in enumerate(wave.ships):
            angle = (_rnd.uniform(0, 6.2832))
            dist  = _rnd.randint(450, 800)
            raider.x = ship.x + _math.cos(angle) * dist
            raider.y = ship.y + _math.sin(angle) * dist

        self._base_defense_wave = wave
        self.active_combat = SpaceCombat(ship, wave.ships, nebula=False)
        self.active_combat.crew_menu = self.crew_menu
        self.active_combat._is_base_defense = True   # flag checked in victory
        # Kill credits flow to base wallet
        if getattr(self, "home_base", None):
            self.active_combat._base_ref = self.home_base
        self._victory_shown = False
        self._victory_data  = {}
        self.change_state(State.PLAYING)

    # ── Fleet screen ──────────────────────────────────────────────────────────
    def _draw_fleet_screen(self) -> None:
        from settings import DARK_BG, PANEL_BG, BORDER, ACCENT, TEXT_MAIN, TEXT_MUTED, SUCCESS, WARNING, DANGER
        s = self.screen
        s.fill(DARK_BG)
        font_lg = pygame.font.SysFont("monospace", 20)
        font    = pygame.font.SysFont("monospace", 14)
        font_sm = pygame.font.SysFont("monospace", 11)

        title = font_lg.render("FLEET ORDERS  [ESC] Back to Base", True, ACCENT)
        s.blit(title, (20, 14))

        if not self.player_fleet:
            s.blit(font.render("No fleet loaded.", True, TEXT_MUTED), (20, 60))
            return

        from fleet.orders import Order

        # WANDER=yellow FOLLOW=green GUARD=blue (the 3 big toggles shown per non-active ship)
        BIG_ORDERS = [
            (Order.WANDER,     "WANDER",  (200, 180, 40)),
            (Order.FOLLOW,     "FOLLOW",  (60,  200, 80)),
            (Order.GUARD_BASE, "GUARD",   (60,  120, 255)),
        ]
        ORDER_COLORS = {
            Order.FOLLOW:         (60,  200, 80),
            Order.GUARD_BASE:     (60,  120, 255),
            Order.PATROL_COLLECT: (200, 160, 40),
            Order.WANDER:         (200, 180, 40),
            Order.MISSION:        (200, 80,  200),
            Order.STANDBY:        (120, 120, 120),
        }

        y = 55
        order_buttons: list[tuple[str, str, pygame.Rect]] = []  # (ship_id, order, rect)

        # ── Fleet ships ────────────────────────────────────────────────────────
        for ship in self.player_fleet.ships:
            is_active = (ship is self.player_fleet.active_ship)
            row = pygame.Rect(20, y, SCREEN_WIDTH - 40, 52)
            pygame.draw.rect(s, PANEL_BG, row)
            pygame.draw.rect(s, ACCENT if is_active else BORDER, row, 1)

            tag = " [ACTIVE]" if is_active else ""
            name_s = font.render(
                f"{ship.custom_name}  ({ship.ship_class}){tag}", True, TEXT_MAIN)
            s.blit(name_s, (30, y + 6))

            hp_pct = ship.hull / max(ship.max_hull, 1)
            pygame.draw.rect(s, (60, 0, 0),  (30, y + 26, 160, 6))
            pygame.draw.rect(s, SUCCESS,     (30, y + 26, int(160 * hp_pct), 6))
            hull_s = font_sm.render(f"Hull {ship.hull:.0f}/{ship.max_hull}", True, TEXT_MUTED)
            s.blit(hull_s, (30, y + 34))

            # Big 3-toggle order buttons for non-active ships
            if not is_active:
                bx = 220
                for order, label, col in BIG_ORDERS:
                    active_order = (ship.fleet_order == order or
                                    (order == Order.WANDER and ship.fleet_order == Order.PATROL_COLLECT))
                    btn = pygame.Rect(bx, y + 8, 110, 34)
                    bg  = col if active_order else (20, 20, 40)
                    pygame.draw.rect(s, bg, btn)
                    pygame.draw.rect(s, col, btn, 1)
                    lbl = font_sm.render(label, True,
                                         (10, 10, 10) if active_order else TEXT_MUTED)
                    s.blit(lbl, (btn.x + btn.w // 2 - lbl.get_width() // 2,
                                  btn.y + btn.h // 2 - lbl.get_height() // 2))
                    order_buttons.append((ship.id, order, btn))
                    bx += 114
                # Current order label
                cur_col = ORDER_COLORS.get(ship.fleet_order, (120, 120, 120))
                cur_lbl = font_sm.render(f"({ship.fleet_order})", True, cur_col)
                s.blit(cur_lbl, (bx + 4, y + 20))

            y += 60

        # ── Captured ships ─────────────────────────────────────────────────────
        captured = getattr(self.player_fleet, "captured_ships", [])
        if captured:
            y += 4
            pygame.draw.line(s, BORDER, (20, y), (SCREEN_WIDTH - 20, y)); y += 6
            cap_title = font.render(f"CAPTURED SHIPS  ({len(captured)})", True, (200, 80, 220))
            s.blit(cap_title, (20, y)); y += 18
            for ship in captured:
                row = pygame.Rect(20, y, SCREEN_WIDTH - 40, 50)
                pygame.draw.rect(s, (20, 10, 30), row)
                pygame.draw.rect(s, (120, 40, 160), row, 1)
                name_s = font.render(
                    f"  {ship.custom_name}  ({ship.ship_class})", True, (200, 140, 220))
                s.blit(name_s, (30, y + 6))
                hp_pct = ship.hull / max(ship.max_hull, 1)
                pygame.draw.rect(s, (60, 0, 0),  (30, y + 24, 140, 5))
                pygame.draw.rect(s, SUCCESS,     (30, y + 24, int(140 * hp_pct), 5))
                hull_s2 = font_sm.render(f"Hull {ship.hull:.0f}/{ship.max_hull}", True, TEXT_MUTED)
                s.blit(hull_s2, (30, y + 32))
                # Order buttons for captured ships
                bx = 220
                for order, label, col in BIG_ORDERS:
                    active_order = (ship.fleet_order == order or
                                    (order == Order.WANDER and ship.fleet_order == Order.PATROL_COLLECT))
                    btn = pygame.Rect(bx, y + 8, 110, 32)
                    bg  = col if active_order else (20, 20, 40)
                    pygame.draw.rect(s, bg, btn)
                    pygame.draw.rect(s, col, btn, 1)
                    lbl = font_sm.render(label, True,
                                         (10, 10, 10) if active_order else TEXT_MUTED)
                    s.blit(lbl, (btn.x + btn.w // 2 - lbl.get_width() // 2,
                                  btn.y + btn.h // 2 - lbl.get_height() // 2))
                    order_buttons.append((ship.id, order, btn))
                    bx += 114
                y += 54

        # Handle clicks on order buttons
        self._fleet_order_buttons = order_buttons

        # ── Active missions ────────────────────────────────────────────────────
        y += 8
        pygame.draw.line(s, BORDER, (20, y), (SCREEN_WIDTH - 20, y)); y += 8
        mis_title = font.render("ACTIVE MISSIONS", True, ACCENT)
        s.blit(mis_title, (20, y)); y += 20
        if self.player_fleet.active_missions:
            for m in self.player_fleet.active_missions:
                pct  = m.progress_pct
                line = (f"{m.title}  —  Ship: "
                        f"{m.assigned_ship.custom_name if m.assigned_ship else '?'}"
                        f"  {int(pct*100)}%")
                ls = font_sm.render(line, True, TEXT_MUTED)
                s.blit(ls, (20, y))
                pygame.draw.rect(s, (20, 20, 40),  (20, y + 14, 300, 6))
                pygame.draw.rect(s, SUCCESS, (20, y + 14, int(300 * pct), 6))
                y += 26
        else:
            s.blit(font_sm.render("No active missions.", True, TEXT_MUTED), (20, y))
            y += 18

        # ── Available crew (post-mission hire pool) ────────────────────────────
        hire_pool = getattr(self.player_fleet, "hire_pool", [])
        if hire_pool:
            y += 6
            pygame.draw.line(s, BORDER, (20, y), (SCREEN_WIDTH - 20, y)); y += 6
            avail_title = font.render(
                f"AVAILABLE CREW  (hired after missions — 200cr each)", True, SUCCESS)
            s.blit(avail_title, (20, y)); y += 18
            self._fleet_hire_btns: list[tuple[int, pygame.Rect]] = []
            for idx, crew_entry in enumerate(hire_pool):
                if y > SCREEN_HEIGHT - 80:
                    break
                name  = crew_entry.get("name", "?")
                role  = crew_entry.get("role", "?")
                rar   = crew_entry.get("rarity", "common")
                rar_col = {"common": TEXT_MUTED, "uncommon": SUCCESS,
                           "rare": (80, 140, 255), "epic": (180, 60, 220),
                           "legendary": (255, 200, 40)}.get(rar, TEXT_MUTED)
                crew_lbl = font_sm.render(
                    f"  {name[:18]:<18}  [{role}]  [{rar}]", True, rar_col)
                s.blit(crew_lbl, (20, y))
                hire_btn = pygame.Rect(SCREEN_WIDTH - 200, y - 2, 100, 20)
                can = (self.home_base and
                       self.home_base.get_resource("credits") >= 200)
                pygame.draw.rect(s, (20, 60, 20) if can else (40, 20, 20), hire_btn)
                pygame.draw.rect(s, SUCCESS if can else DANGER, hire_btn, 1)
                hl = font_sm.render("200cr HIRE", True, SUCCESS if can else DANGER)
                s.blit(hl, (hire_btn.centerx - hl.get_width() // 2,
                             hire_btn.centery - hl.get_height() // 2))
                self._fleet_hire_btns.append((idx, hire_btn))
                y += 20

        # ESC hint & Back button
        esc_s = font_sm.render("Press ESC or click Back to return to Base", True, TEXT_MUTED)
        s.blit(esc_s, (20, SCREEN_HEIGHT - 24))
        back_btn = pygame.Rect(SCREEN_WIDTH - 160, SCREEN_HEIGHT - 40, 150, 30)
        pygame.draw.rect(s, PANEL_BG, back_btn)
        pygame.draw.rect(s, BORDER, back_btn, 1)
        bt = font_sm.render("← Back to Base", True, TEXT_MUTED)
        s.blit(bt, (back_btn.x + 8, back_btn.y + 8))
        self._fleet_back_btn = back_btn

    # ── Settings screen ────────────────────────────────────────────────────────
    def _draw_settings_screen(self) -> None:
        from settings import DARK_BG, PANEL_BG, BORDER, ACCENT, TEXT_MAIN, TEXT_MUTED, SUCCESS, DANGER, WARNING
        s = self.screen
        s.fill(DARK_BG)
        font_lg = pygame.font.SysFont("monospace", 20, bold=True)
        font    = pygame.font.SysFont("monospace", 15)
        font_sm = pygame.font.SysFont("monospace", 12)

        title = font_lg.render("SETTINGS  [ESC] Back to Base", True, ACCENT)
        s.blit(title, (20, 14))

        # Two-column layout
        LEFT_X  = 20
        COL2_X  = SCREEN_WIDTH // 2 + 20
        LABEL_W = 220
        VAL_X   = LEFT_X + LABEL_W + 10
        VAL2_X  = COL2_X + LABEL_W + 10
        ROW_H   = 48
        y = 58

        def _toggle(surface, rect, state):
            bg  = (20, 80, 40) if state else (60, 20, 20)
            col = SUCCESS     if state else DANGER
            pygame.draw.rect(surface, bg, rect)
            pygame.draw.rect(surface, col, rect, 1)
            lbl = font_sm.render("ON" if state else "OFF", True, col)
            surface.blit(lbl, (rect.centerx - lbl.get_width()//2,
                                rect.centery - lbl.get_height()//2))
            return rect

        def _row(lx, vx, label):
            nonlocal y
            lb = font.render(label, True, TEXT_MAIN)
            s.blit(lb, (lx, y + 5))
            return vx, y

        # ── LEFT COLUMN ───────────────────────────────────────────────────────
        # Combat speed
        lb = font.render("Combat Speed:", True, TEXT_MAIN)
        s.blit(lb, (LEFT_X, y + 5))
        self._settings_speed_btns = []
        for i, val in enumerate([0.5, 0.75, 1.0, 1.25, 1.5, 2.0]):
            btn = pygame.Rect(VAL_X + i * 68, y, 62, 28)
            sel = abs(self.combat_speed - val) < 0.01
            pygame.draw.rect(s, (30, 60, 90) if sel else PANEL_BG, btn)
            pygame.draw.rect(s, ACCENT if sel else BORDER, btn, 1)
            lt = font_sm.render(f"{val}x", True, TEXT_MAIN)
            s.blit(lt, (btn.centerx - lt.get_width()//2, btn.centery - lt.get_height()//2))
            self._settings_speed_btns.append((val, btn))
        y += ROW_H

        # Colorblind mode
        lb = font.render("Colorblind Mode:", True, TEXT_MAIN)
        s.blit(lb, (LEFT_X, y + 5))
        cb_btn = pygame.Rect(VAL_X, y, 80, 28)
        _toggle(s, cb_btn, self.colorblind)
        self._settings_cb_btn = cb_btn
        y += ROW_H

        # Font size
        lb = font.render("Font Size:", True, TEXT_MAIN)
        s.blit(lb, (LEFT_X, y + 5))
        self._settings_font_btns = []
        for i, sz in enumerate(["S", "M", "L"]):
            btn = pygame.Rect(VAL_X + i * 60, y, 54, 28)
            sel = (self.font_size == sz)
            pygame.draw.rect(s, (30, 60, 90) if sel else PANEL_BG, btn)
            pygame.draw.rect(s, ACCENT if sel else BORDER, btn, 1)
            ft = font_sm.render(sz, True, TEXT_MAIN)
            s.blit(ft, (btn.centerx - ft.get_width()//2, btn.centery - ft.get_height()//2))
            self._settings_font_btns.append((sz, btn))
        y += ROW_H

        # Damage numbers toggle
        lb = font.render("Damage Numbers:", True, TEXT_MAIN)
        s.blit(lb, (LEFT_X, y + 5))
        dmg_btn = pygame.Rect(VAL_X, y, 80, 28)
        _toggle(s, dmg_btn, self.show_damage_numbers)
        self._settings_dmg_btn = dmg_btn
        y += ROW_H

        # Screen shake toggle
        lb = font.render("Screen Shake:", True, TEXT_MAIN)
        s.blit(lb, (LEFT_X, y + 5))
        shake_btn = pygame.Rect(VAL_X, y, 80, 28)
        _toggle(s, shake_btn, self.screen_shake)
        self._settings_shake_btn = shake_btn
        y += ROW_H

        # Particle effects toggle
        lb = font.render("Particle Effects:", True, TEXT_MAIN)
        s.blit(lb, (LEFT_X, y + 5))
        par_btn = pygame.Rect(VAL_X, y, 80, 28)
        _toggle(s, par_btn, self.particle_effects)
        self._settings_particles_btn = par_btn
        y += ROW_H

        # Show FPS toggle
        lb = font.render("Show FPS:", True, TEXT_MAIN)
        s.blit(lb, (LEFT_X, y + 5))
        fps_btn = pygame.Rect(VAL_X, y, 80, 28)
        _toggle(s, fps_btn, self.show_fps)
        self._settings_fps_btn = fps_btn
        y += ROW_H

        # ── RIGHT COLUMN ──────────────────────────────────────────────────────
        y2 = 58

        # Music volume
        lb = font.render("Music Volume:", True, TEXT_MAIN)
        s.blit(lb, (COL2_X, y2 + 5))
        ml = pygame.Rect(VAL2_X, y2, 30, 28)
        mr = pygame.Rect(VAL2_X + 80, y2, 30, 28)
        pygame.draw.rect(s, PANEL_BG, ml); pygame.draw.rect(s, BORDER, ml, 1)
        pygame.draw.rect(s, PANEL_BG, mr); pygame.draw.rect(s, BORDER, mr, 1)
        s.blit(font_sm.render("<", True, TEXT_MAIN), (ml.centerx-4, ml.centery-7))
        s.blit(font_sm.render(">", True, TEXT_MAIN), (mr.centerx-4, mr.centery-7))
        mv_t = font.render(f"{self.music_volume:.1f}", True, ACCENT)
        s.blit(mv_t, (VAL2_X + 38, y2 + 4))
        self._settings_music_left  = ml
        self._settings_music_right = mr
        y2 += ROW_H

        # SFX volume
        lb = font.render("SFX Volume:", True, TEXT_MAIN)
        s.blit(lb, (COL2_X, y2 + 5))
        sl = pygame.Rect(VAL2_X, y2, 30, 28)
        sr = pygame.Rect(VAL2_X + 80, y2, 30, 28)
        pygame.draw.rect(s, PANEL_BG, sl); pygame.draw.rect(s, BORDER, sl, 1)
        pygame.draw.rect(s, PANEL_BG, sr); pygame.draw.rect(s, BORDER, sr, 1)
        s.blit(font_sm.render("<", True, TEXT_MAIN), (sl.centerx-4, sl.centery-7))
        s.blit(font_sm.render(">", True, TEXT_MAIN), (sr.centerx-4, sr.centery-7))
        sv_t = font.render(f"{self.sfx_volume:.1f}", True, ACCENT)
        s.blit(sv_t, (VAL2_X + 38, y2 + 4))
        self._settings_sfx_left  = sl
        self._settings_sfx_right = sr
        y2 += ROW_H

        # Minimap toggle
        lb = font.render("Show Minimap:", True, TEXT_MAIN)
        s.blit(lb, (COL2_X, y2 + 5))
        mm_btn = pygame.Rect(VAL2_X, y2, 80, 28)
        _toggle(s, mm_btn, self.show_minimap)
        self._settings_minimap_btn = mm_btn
        y2 += ROW_H

        # Enemy health bars toggle
        lb = font.render("Enemy HP Bars:", True, TEXT_MAIN)
        s.blit(lb, (COL2_X, y2 + 5))
        ehb_btn = pygame.Rect(VAL2_X, y2, 80, 28)
        _toggle(s, ehb_btn, self.enemy_health_bars)
        self._settings_ehb_btn = ehb_btn
        y2 += ROW_H

        # Auto-pause on raid
        lb = font.render("Auto-Pause on Raid:", True, TEXT_MAIN)
        s.blit(lb, (COL2_X, y2 + 5))
        ap_btn = pygame.Rect(VAL2_X, y2, 80, 28)
        _toggle(s, ap_btn, self.autopause_on_raid)
        self._settings_autopause_btn = ap_btn
        y2 += ROW_H

        # Difficulty
        lb = font.render("Difficulty:", True, TEXT_MAIN)
        s.blit(lb, (COL2_X, y2 + 5))
        self._settings_diff_btns = []
        for i, diff in enumerate(["easy", "normal", "hard"]):
            btn = pygame.Rect(VAL2_X + i * 80, y2, 74, 28)
            sel = (self.difficulty == diff)
            diff_col = {
                "easy":   (60, 200, 80),
                "normal": (255, 180, 40),
                "hard":   (220, 50, 50),
            }[diff]
            pygame.draw.rect(s, (20, 60, 20) if sel and diff == "easy" else
                                (60, 50, 10) if sel and diff == "normal" else
                                (60, 15, 15) if sel and diff == "hard" else PANEL_BG, btn)
            pygame.draw.rect(s, diff_col if sel else BORDER, btn, 2 if sel else 1)
            dt = font_sm.render(diff.capitalize(), True, diff_col if sel else TEXT_MUTED)
            s.blit(dt, (btn.centerx - dt.get_width() // 2, btn.centery - dt.get_height() // 2))
            self._settings_diff_btns.append((diff, btn))
        y2 += ROW_H

        # Auto-save interval
        lb = font.render("Auto-Save:", True, TEXT_MAIN)
        s.blit(lb, (COL2_X, y2 + 5))
        self._settings_autosave_btns = []
        for i, (iv, lbl) in enumerate([(0, "Off"), (120, "2 min"),
                                        (300, "5 min"), (600, "10 min")]):
            btn = pygame.Rect(VAL2_X + i * 74, y2, 68, 28)
            sel = (self.autosave_interval == iv)
            pygame.draw.rect(s, (20, 50, 80) if sel else PANEL_BG, btn)
            pygame.draw.rect(s, ACCENT if sel else BORDER, btn, 2 if sel else 1)
            at = font_sm.render(lbl, True, TEXT_MAIN if sel else TEXT_MUTED)
            s.blit(at, (btn.centerx - at.get_width() // 2, btn.centery - at.get_height() // 2))
            self._settings_autosave_btns.append((iv, btn))
        y2 += ROW_H

        # ── EXTENDED SETTINGS row ─────────────────────────────────────────────
        sep_y = max(y, y2) + 6
        pygame.draw.line(s, BORDER, (LEFT_X, sep_y), (SCREEN_WIDTH - LEFT_X, sep_y))
        ext_title = font.render("⚙ MORE SETTINGS", True, (140, 100, 220))
        s.blit(ext_title, (LEFT_X, sep_y + 4))
        sep_y += 24

        # Row 1: crosshair style | HUD opacity | Radar zoom
        EXT_ROW_H = 40
        ext_y = sep_y
        ext_x = LEFT_X

        # Crosshair style
        lb = font_sm.render("Crosshair:", True, TEXT_MAIN)
        s.blit(lb, (ext_x, ext_y + 4))
        self._settings_crosshair_btns = []
        for i, (style, label) in enumerate([("cross","✚"), ("dot","●"), ("circle","○"), ("none","–")]):
            btn = pygame.Rect(ext_x + 80 + i * 50, ext_y, 44, 28)
            sel = (self.crosshair_style == style)
            pygame.draw.rect(s, (30,60,90) if sel else PANEL_BG, btn)
            pygame.draw.rect(s, ACCENT if sel else BORDER, btn, 1)
            lt = font_sm.render(label, True, TEXT_MAIN if sel else TEXT_MUTED)
            s.blit(lt, (btn.centerx-lt.get_width()//2, btn.centery-lt.get_height()//2))
            self._settings_crosshair_btns.append((style, btn))

        # HUD opacity
        hud_x = ext_x + 310
        lb2 = font_sm.render("HUD Opacity:", True, TEXT_MAIN)
        s.blit(lb2, (hud_x, ext_y + 4))
        self._settings_hud_opacity_btns = []
        for i, val in enumerate([0.5, 0.7, 0.85, 1.0]):
            btn = pygame.Rect(hud_x + 100 + i * 50, ext_y, 44, 28)
            sel = abs(self.hud_opacity - val) < 0.01
            pygame.draw.rect(s, (30,60,90) if sel else PANEL_BG, btn)
            pygame.draw.rect(s, ACCENT if sel else BORDER, btn, 1)
            lt = font_sm.render(f"{int(val*100)}%", True, TEXT_MAIN if sel else TEXT_MUTED)
            s.blit(lt, (btn.centerx-lt.get_width()//2, btn.centery-lt.get_height()//2))
            self._settings_hud_opacity_btns.append((val, btn))

        # Radar zoom
        radar_x = hud_x + 310
        lb3 = font_sm.render("Radar Zoom:", True, TEXT_MAIN)
        s.blit(lb3, (radar_x, ext_y + 4))
        self._settings_radar_zoom_btns = []
        for i, (val, lbl) in enumerate([(0.5,"×2"), (1.0,"×1"), (2.0,"½")]):
            btn = pygame.Rect(radar_x + 96 + i * 50, ext_y, 44, 28)
            sel = abs(self.radar_zoom - val) < 0.01
            pygame.draw.rect(s, (30,60,90) if sel else PANEL_BG, btn)
            pygame.draw.rect(s, ACCENT if sel else BORDER, btn, 1)
            lt = font_sm.render(lbl, True, TEXT_MAIN if sel else TEXT_MUTED)
            s.blit(lt, (btn.centerx-lt.get_width()//2, btn.centery-lt.get_height()//2))
            self._settings_radar_zoom_btns.append((val, btn))

        sep_y += EXT_ROW_H

        # Row 2: Show Hints | Auto-Collect Debris | Boarding Auto-Attack
        lb4 = font_sm.render("Show Hints:", True, TEXT_MAIN)
        s.blit(lb4, (LEFT_X, sep_y + 4))
        hints_btn = pygame.Rect(LEFT_X + 100, sep_y, 80, 28)
        _toggle(s, hints_btn, self.show_hints)
        self._settings_hints_btn = hints_btn

        lb5 = font_sm.render("Auto-Collect Debris:", True, TEXT_MAIN)
        s.blit(lb5, (LEFT_X + 220, sep_y + 4))
        ac_btn = pygame.Rect(LEFT_X + 390, sep_y, 80, 28)
        _toggle(s, ac_btn, self.auto_collect_debris)
        self._settings_autocollect_btn = ac_btn

        lb6 = font_sm.render("Boarding Auto-Attack:", True, TEXT_MAIN)
        s.blit(lb6, (LEFT_X + 510, sep_y + 4))
        ba_btn = pygame.Rect(LEFT_X + 690, sep_y, 80, 28)
        _toggle(s, ba_btn, self.boarding_auto_attack)
        self._settings_boarding_auto_btn = ba_btn

        sep_y += EXT_ROW_H + 4

        # ── Photo mode hint ───────────────────────────────────────────────────
        pygame.draw.line(s, BORDER, (LEFT_X, sep_y), (SCREEN_WIDTH - LEFT_X, sep_y))
        ph = font_sm.render("Photo Mode: F12 in-game  |  Kill multiplier: 100 cr/ship  |  Board: destroy shields OR hull < 25%", True, TEXT_MUTED)
        s.blit(ph, (LEFT_X, sep_y + 4))
        sep_y += 18

        # ── SAVE GAME button ──────────────────────────────────────────────────
        save_btn = pygame.Rect(LEFT_X, sep_y + 8, 200, 34)
        hover_save = save_btn.collidepoint(pygame.mouse.get_pos())
        save_bg = (20, 60, 40) if hover_save else (12, 38, 24)
        pygame.draw.rect(s, save_bg, save_btn, border_radius=4)
        pygame.draw.rect(s, SUCCESS, save_btn, 2, border_radius=4)
        save_lbl = font.render("💾  Save Game", True, SUCCESS)
        s.blit(save_lbl, (save_btn.centerx - save_lbl.get_width() // 2,
                           save_btn.centery - save_lbl.get_height() // 2))
        self._settings_save_btn = save_btn

        # Save status text (shown after save)
        save_msg = getattr(self, "_settings_save_msg", "")
        if save_msg:
            sm = font_sm.render(save_msg, True, SUCCESS)
            s.blit(sm, (LEFT_X + 210, sep_y + 36))

        # ESC hint + back button
        esc_s = font_sm.render("Press ESC to return to Base", True, TEXT_MUTED)
        s.blit(esc_s, (20, SCREEN_HEIGHT - 24))
        back_btn = pygame.Rect(SCREEN_WIDTH - 160, SCREEN_HEIGHT - 40, 150, 30)
        pygame.draw.rect(s, PANEL_BG, back_btn)
        pygame.draw.rect(s, BORDER, back_btn, 1)
        bt = font_sm.render("← Back to Base", True, TEXT_MUTED)
        s.blit(bt, (back_btn.x + 8, back_btn.y + 8))
        self._settings_back_btn = back_btn

    # ── Save / Load ───────────────────────────────────────────────────────────
    def _do_save_game(self) -> None:
        """Quick-save the current game state to saves/slot0.json."""
        import json, os, time as _time
        os.makedirs("saves", exist_ok=True)
        data: dict = {
            "version":  1,
            "saved_at": _time.strftime("%Y-%m-%d %H:%M"),
            "playtime": round(self.playtime, 1),
        }
        # Home base resources
        if self.home_base:
            data["resources"] = dict(self.home_base.resources)
            data["buildings"] = list(self.home_base.buildings)
            data["research_unlocked"] = list(self.home_base.research_unlocked)
        # Galaxy visited sectors
        if self.galaxy:
            data["galaxy"] = {
                "current_sector_id": self.galaxy.current_sector_id,
                "sectors": {sid: {"visited": s.visited, "boss_defeated": s.boss_defeated}
                            for sid, s in self.galaxy.sectors.items()},
            }
        # Player ship basics
        if self.player_fleet and self.player_fleet.active_ship:
            ship = self.player_fleet.active_ship
            data["player_ship"] = {
                "hull":      round(ship.hull, 1),
                "max_hull":  ship.max_hull,
                "shield":    round(ship.shield, 1),
                "max_shield":ship.max_shield,
                "fuel":      round(ship.fuel, 1),
                "crew_count":len(ship.crew),
            }
        path = os.path.join("saves", "slot0.json")
        try:
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
            self._settings_save_msg = f"Saved  {data['saved_at']}"
            if self.hud:
                self.hud.push_notification("Game saved!", (60, 220, 80))
        except Exception as e:
            self._settings_save_msg = f"Save failed: {e}"

    # ── Placeholder ───────────────────────────────────────────────────────────
    def _draw_placeholder(self) -> None:
        self.screen.fill(DARK_BG)
        font = pygame.font.SysFont("monospace", 28)
        msg  = font.render(f"Space Pirates  [{self.state}]", True, (180, 180, 200))
        self.screen.blit(msg, (SCREEN_WIDTH // 2 - msg.get_width() // 2,
                                SCREEN_HEIGHT // 2 - msg.get_height() // 2))
