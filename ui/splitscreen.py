"""ui/splitscreen.py — Split-screen layout manager (combat left, management right)."""
from __future__ import annotations
import pygame
from settings import SCREEN_WIDTH, SCREEN_HEIGHT, PANEL_BG, BORDER, TEXT_MUTED

# Left panel = 65% of screen width for combat
COMBAT_PANEL_W = int(SCREEN_WIDTH * 0.65)
MGMT_PANEL_W   = SCREEN_WIDTH - COMBAT_PANEL_W
MGMT_PANEL_X   = COMBAT_PANEL_W


class SplitScreen:
    """Owns left (combat) and right (management) surfaces.

    Usage:
        ss = SplitScreen()
        ss.begin_frame(main_surface)     # fills backgrounds, draws divider
        # Draw combat content to ss.combat_surf
        # Draw management content to ss.mgmt_surf
        ss.end_frame(main_surface)       # blits both to main surface
    """

    def __init__(self):
        self.combat_surf = pygame.Surface((COMBAT_PANEL_W, SCREEN_HEIGHT))
        self.mgmt_surf   = pygame.Surface((MGMT_PANEL_W,   SCREEN_HEIGHT))
        pygame.font.init()
        self._font = pygame.font.SysFont("monospace", 11)

    def begin_frame(self, surface: pygame.Surface) -> None:
        from settings import DARK_BG
        self.combat_surf.fill(DARK_BG)
        self.mgmt_surf.fill(PANEL_BG)

    def end_frame(self, surface: pygame.Surface) -> None:
        surface.blit(self.combat_surf, (0, 0))
        surface.blit(self.mgmt_surf,   (MGMT_PANEL_X, 0))
        # Divider line
        pygame.draw.line(surface, BORDER,
                         (MGMT_PANEL_X, 0), (MGMT_PANEL_X, SCREEN_HEIGHT), 2)

    def combat_rect(self) -> pygame.Rect:
        return pygame.Rect(0, 0, COMBAT_PANEL_W, SCREEN_HEIGHT)

    def mgmt_rect(self) -> pygame.Rect:
        return pygame.Rect(MGMT_PANEL_X, 0, MGMT_PANEL_W, SCREEN_HEIGHT)
