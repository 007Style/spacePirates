"""ui/hud.py — In-combat HUD overlay."""
from __future__ import annotations
import pygame
from settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, TEXT_MAIN, TEXT_MUTED,
    SUCCESS, DANGER, WARNING, ACCENT, WHITE, MAX_WANTED_LEVEL,
)


class HUD:
    def __init__(self):
        pygame.font.init()
        self._font    = pygame.font.SysFont("monospace", 13)
        self._font_sm = pygame.font.SysFont("monospace", 11)
        self._font_lg = pygame.font.SysFont("monospace", 16)

        # Notifications queue: [(text, color, lifetime)]
        self._notifications: list[list] = []

        # Galaxy map button rect (set each draw frame, read by game.py for clicks)
        self.galaxy_map_btn: pygame.Rect | None = None

    # ── Notifications ─────────────────────────────────────────────────────────
    def push_notification(self, msg: str, color: tuple = None,
                          duration: float = 3.5) -> None:
        color = color or TEXT_MAIN
        self._notifications.append([msg, color, duration])

    def update(self, dt: float) -> None:
        for n in self._notifications:
            n[2] -= dt
        self._notifications = [n for n in self._notifications if n[2] > 0]

    # ── Draw ──────────────────────────────────────────────────────────────────
    def draw(self, surface: pygame.Surface, player_ship, meta_prog=None,
             combat=None) -> None:
        self._draw_ship_bars(surface, player_ship)
        if meta_prog:
            self._draw_wanted(surface, meta_prog.wanted_level)
            self._draw_title(surface, meta_prog.title_system.current_title)
        if player_ship:
            self._draw_status_effects(surface, player_ship)
            self._draw_fuel(surface, player_ship)
            self._draw_crew_morale(surface, player_ship)
        if combat:
            self._draw_kill_count(surface, combat.kills)
        self._draw_notifications(surface)

    # ── Components ────────────────────────────────────────────────────────────
    def _draw_ship_bars(self, surface: pygame.Surface, ship) -> None:
        if not ship:
            return
        bw, bh = 200, 14
        bx, by = 12, 12

        # Hull
        pygame.draw.rect(surface, (50, 10, 10), (bx, by, bw, bh))
        fill = int(bw * (ship.hull / max(ship.max_hull, 1)))
        pygame.draw.rect(surface, SUCCESS, (bx, by, fill, bh))
        label = self._font_sm.render(
            f"Hull {ship.hull:.0f}/{ship.max_hull}", True, WHITE)
        surface.blit(label, (bx + 4, by + 1))

        # Shield
        by2 = by + bh + 3
        pygame.draw.rect(surface, (10, 10, 50), (bx, by2, bw, bh))
        sfill = int(bw * (ship.shield / max(ship.max_shield, 1)))
        pygame.draw.rect(surface, (60, 120, 255), (bx, by2, sfill, bh))
        slabel = self._font_sm.render(
            f"Shield {ship.shield:.0f}/{ship.max_shield}", True, WHITE)
        surface.blit(slabel, (bx + 4, by2 + 1))

        # Galaxy Map button — sits directly below the shield bar
        btn_y = by2 + bh + 5
        btn   = pygame.Rect(bx, btn_y, bw, 18)
        mx, my = pygame.mouse.get_pos()
        hover  = btn.collidepoint(mx, my)
        bg_col = (15, 50, 80) if hover else (10, 30, 50)
        pygame.draw.rect(surface, bg_col, btn)
        pygame.draw.rect(surface, ACCENT, btn, 1)
        lbl = self._font_sm.render("⬡  Galaxy Map", True, ACCENT)
        surface.blit(lbl, (btn.centerx - lbl.get_width() // 2,
                            btn.centery - lbl.get_height() // 2))
        self.galaxy_map_btn = btn

    def _draw_wanted(self, surface: pygame.Surface, wanted: int) -> None:
        stars = "★" * wanted + "☆" * (MAX_WANTED_LEVEL - wanted)
        color = [SUCCESS, WARNING, WARNING, DANGER, DANGER, (220, 0, 0)][min(wanted, 5)]
        txt = self._font.render(f"WANTED: {stars}", True, color)
        surface.blit(txt, (SCREEN_WIDTH // 2 - txt.get_width() // 2, 8))

    def _draw_title(self, surface: pygame.Surface, title: str) -> None:
        txt = self._font_sm.render(title, True, TEXT_MUTED)
        surface.blit(txt, (SCREEN_WIDTH // 2 - txt.get_width() // 2, 26))

    def _draw_status_effects(self, surface: pygame.Surface, ship) -> None:
        if not ship.status_effects:
            return
        x = 12
        y = SCREEN_HEIGHT - 30
        for eff in ship.status_effects:
            lbl = self._font_sm.render(f"[{eff}]", True, WARNING)
            surface.blit(lbl, (x, y))
            x += lbl.get_width() + 6

    def _draw_fuel(self, surface: pygame.Surface, ship) -> None:
        pct  = ship.fuel / max(ship.fuel_capacity, 1)
        color = SUCCESS if pct > 0.3 else (WARNING if pct > 0.1 else DANGER)
        txt  = self._font_sm.render(f"Fuel {ship.fuel:.0f}/{ship.fuel_capacity}",
                                    True, color)
        surface.blit(txt, (SCREEN_WIDTH - txt.get_width() - 12, 12))

    def _draw_crew_morale(self, surface: pygame.Surface, ship) -> None:
        if not ship.crew:
            return
        avg_morale = sum(c.morale for c in ship.crew) / len(ship.crew)
        color = SUCCESS if avg_morale >= 60 else (WARNING if avg_morale >= 30 else DANGER)
        txt = self._font_sm.render(f"Morale {avg_morale:.0f}%", True, color)
        surface.blit(txt, (SCREEN_WIDTH - txt.get_width() - 12, 28))

    def _draw_kill_count(self, surface: pygame.Surface, kills: int) -> None:
        txt = self._font_sm.render(f"Kills: {kills}", True, TEXT_MUTED)
        surface.blit(txt, (SCREEN_WIDTH - txt.get_width() - 12, 44))

    def _draw_notifications(self, surface: pygame.Surface) -> None:
        y = SCREEN_HEIGHT - 60
        for msg, color, lifetime in reversed(self._notifications[-5:]):
            alpha = min(255, int(lifetime * 120))
            txt   = self._font.render(msg, True, color)
            surf  = pygame.Surface(txt.get_size(), pygame.SRCALPHA)
            surf.fill((0, 0, 0, 0))
            surf.blit(txt, (0, 0))
            surf.set_alpha(alpha)
            surface.blit(surf, (SCREEN_WIDTH // 2 - txt.get_width() // 2, y))
            y -= 20
