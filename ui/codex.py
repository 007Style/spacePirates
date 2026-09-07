"""ui/codex.py — Lore Codex UI."""
from __future__ import annotations
import json
import os
import pygame
from settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, DARK_BG, PANEL_BG, BORDER,
    TEXT_MAIN, TEXT_MUTED, ACCENT, DATA_DIR, WHITE,
)


class Codex:
    def __init__(self):
        pygame.font.init()
        self._font     = pygame.font.SysFont("monospace", 14)
        self._font_sm  = pygame.font.SysFont("monospace", 11)
        self._font_lg  = pygame.font.SysFont("monospace", 18)
        self._entries  = self._load_entries()
        self._unlocked: set[str]   = set()
        self._selected: str | None = None
        self._scroll                = 0

    def _load_entries(self) -> list[dict]:
        try:
            with open(os.path.join(DATA_DIR, "lore.json")) as f:
                return json.load(f)
        except Exception:
            return []

    def unlock(self, entry_id: str) -> bool:
        if entry_id not in self._unlocked:
            self._unlocked.add(entry_id)
            from core.events import bus
            bus.publish("notification",
                        msg=f"📖 New Lore: {self._entry_title(entry_id)}",
                        color=(160, 100, 255))
            return True
        return False

    def unlock_count(self) -> int:
        return len(self._unlocked)

    def _entry_title(self, entry_id: str) -> str:
        for e in self._entries:
            if e["id"] == entry_id:
                return e.get("title", entry_id)
        return entry_id

    def handle_event(self, event: pygame.event.Event) -> str | None:
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                mx, my = event.pos
                # ESC / back button
                if hasattr(self, "_esc_rect") and self._esc_rect.collidepoint(mx, my):
                    return "close"
                for eid, rect in self._entry_rects.items():
                    if rect.collidepoint(mx, my):
                        self._selected = eid
            elif event.button == 4:
                self._scroll = max(0, self._scroll - 1)
            elif event.button == 5:
                self._scroll += 1
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return "close"
        return None

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(DARK_BG)
        self._entry_rects: dict[str, pygame.Rect] = {}

        # ESC button top-left
        self._esc_rect = pygame.Rect(10, 10, 68, 26)
        pygame.draw.rect(surface, (25, 25, 40), self._esc_rect)
        pygame.draw.rect(surface, (80, 80, 110), self._esc_rect, 1)
        esc_fnt = pygame.font.SysFont("monospace", 11)
        esc_txt = esc_fnt.render("ESC ←", True, (140, 140, 180))
        surface.blit(esc_txt, (self._esc_rect.x + 6,
                                self._esc_rect.y + (self._esc_rect.h - esc_txt.get_height()) // 2))

        # Title
        title = self._font_lg.render("LORE CODEX", True, ACCENT)
        surface.blit(title, (90, 14))

        count_txt = self._font_sm.render(
            f"{len(self._unlocked)}/{len(self._entries)} entries  — unlock entries by playing",
            True, TEXT_MUTED)
        surface.blit(count_txt, (90, 34))

        # Entry list panel
        list_w = 280
        pygame.draw.rect(surface, PANEL_BG,  (0, 60, list_w, SCREEN_HEIGHT - 60))
        pygame.draw.rect(surface, BORDER, (0, 60, list_w, SCREEN_HEIGHT - 60), 1)

        y = 70
        visible_entries = self._entries[self._scroll:]
        for entry in visible_entries:
            eid    = entry["id"]
            locked = eid not in self._unlocked
            label  = entry.get("title", eid) if not locked else "???"
            color  = TEXT_MUTED if locked else TEXT_MAIN
            if self._selected == eid:
                pygame.draw.rect(surface, (30, 30, 60),
                                 (2, y - 2, list_w - 4, 18))
            txt = self._font_sm.render(label, True, color)
            surface.blit(txt, (10, y))
            self._entry_rects[eid] = pygame.Rect(2, y - 2, list_w - 4, 18)
            y += 20
            if y > SCREEN_HEIGHT - 20:
                break

        # Detail panel
        if self._selected and self._selected in self._unlocked:
            self._draw_detail(surface, self._selected, list_w + 10)

    def _draw_detail(self, surface: pygame.Surface, eid: str, x: int) -> None:
        for entry in self._entries:
            if entry["id"] != eid:
                continue
            y = 70
            title_surf = self._font.render(entry.get("title", ""), True, ACCENT)
            surface.blit(title_surf, (x, y)); y += 24

            cat = self._font_sm.render(
                f"Category: {entry.get('category','')}", True, TEXT_MUTED)
            surface.blit(cat, (x, y)); y += 18

            pygame.draw.line(surface, BORDER, (x, y), (SCREEN_WIDTH - 20, y)); y += 10

            # Wrap text
            text = entry.get("text", "")
            max_w = SCREEN_WIDTH - x - 20
            lines = self._wrap(text, max_w, self._font_sm)
            for line in lines:
                surf = self._font_sm.render(line, True, TEXT_MAIN)
                surface.blit(surf, (x, y))
                y += 16
                if y > SCREEN_HEIGHT - 20:
                    break

    @staticmethod
    def _wrap(text: str, max_w: int, font: pygame.font.Font) -> list[str]:
        words = text.split()
        lines, cur = [], ""
        for word in words:
            test = (cur + " " + word).strip()
            if font.size(test)[0] <= max_w:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
        return lines

    def to_dict(self) -> dict:
        return {"unlocked": list(self._unlocked)}

    def load_from_dict(self, data: dict) -> None:
        self._unlocked = set(data.get("unlocked", []))
