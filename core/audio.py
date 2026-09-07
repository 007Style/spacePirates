"""core/audio.py — Audio manager: music and SFX."""
from __future__ import annotations
import pygame
import os
from settings import MUSIC_VOLUME, SFX_VOLUME, SOUND_DIR, MUSIC_DIR
from core.events import bus


class AudioManager:
    # Music tracks per game state/sector type
    MUSIC_TRACKS = {
        "main_menu":   "menu.ogg",
        "base":        "base.ogg",
        "playing":     "combat.ogg",
        "galaxy_map":  "exploration.ogg",
        "graveyard":   "graveyard.ogg",
        "nation_safe": "peaceful.ogg",
        "boarding":    "boarding_intense.ogg",  # high-intensity boarding track
    }

    # SFX event → filename
    SFX_MAP = {
        "laser_fire":      "laser.wav",
        "missile_fire":    "missile.wav",
        "explosion":       "explosion.wav",
        "hull_hit":        "hull_hit.wav",
        "shield_hit":      "shield_hit.wav",
        "ui_click":        "click.wav",
        "loot_pickup":     "loot.wav",
        "level_up":        "levelup.wav",
        "boarding_start":  "boarding.wav",
        "quest_complete":  "quest.wav",
        "purchase":        "kaching.wav",    # ka-ching on any purchase
        "raid_pickup":     "loot.wav",       # cargo raid pickup
    }

    def __init__(self):
        self._music_vol = MUSIC_VOLUME
        self._sfx_vol   = SFX_VOLUME
        self._sfx_cache: dict[str, pygame.mixer.Sound] = {}
        self._current_track: str = ""
        self._enabled = pygame.mixer.get_init() is not None

        # Subscribe to game events for auto-SFX
        bus.subscribe("state_changed",    self._on_state)
        bus.subscribe("quest_completed",  lambda **k: self.play_sfx("quest_complete"))
        bus.subscribe("purchase_made",    lambda **k: self.play_sfx("purchase"))
        bus.subscribe("boarding_started", lambda **k: self.play_sfx("boarding_start"))
        bus.subscribe("sfx_play",         self._on_sfx_play)
        bus.subscribe("enemy_killed",     lambda **k: self.play_sfx("explosion"))

    # ── Music ─────────────────────────────────────────────────────────────────
    def play_music(self, track_key: str) -> None:
        if not self._enabled:
            return
        filename = self.MUSIC_TRACKS.get(track_key, "")
        if not filename or track_key == self._current_track:
            return
        path = os.path.join(MUSIC_DIR, filename)
        if os.path.exists(path):
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(self._music_vol)
            pygame.mixer.music.play(-1)  # loop
            self._current_track = track_key
        # If file doesn't exist (no assets yet), silently skip

    def stop_music(self) -> None:
        if self._enabled:
            pygame.mixer.music.stop()

    def set_music_volume(self, vol: float) -> None:
        self._music_vol = max(0.0, min(1.0, vol))
        if self._enabled:
            pygame.mixer.music.set_volume(self._music_vol)

    # ── SFX ──────────────────────────────────────────────────────────────────
    def play_sfx(self, event_key: str) -> None:
        if not self._enabled:
            return
        filename = self.SFX_MAP.get(event_key, "")
        if not filename:
            return
        if event_key not in self._sfx_cache:
            path = os.path.join(SOUND_DIR, filename)
            if os.path.exists(path):
                try:
                    self._sfx_cache[event_key] = pygame.mixer.Sound(path)
                except Exception:
                    return
            else:
                return  # asset not present yet
        sound = self._sfx_cache.get(event_key)
        if sound:
            sound.set_volume(self._sfx_vol)
            sound.play()

    def set_sfx_volume(self, vol: float) -> None:
        self._sfx_vol = max(0.0, min(1.0, vol))

    # ── Auto music on state change ────────────────────────────────────────────
    def _on_state(self, new="", **kwargs) -> None:
        self.play_music(new)

    def _on_sfx_play(self, key="", **kwargs) -> None:
        if key:
            self.play_sfx(key)
