"""ui/menus.py — All menu/screen classes registered with Game state machine."""
from __future__ import annotations
import pygame
import math
from settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, DARK_BG, PANEL_BG, BORDER,
    TEXT_MAIN, TEXT_MUTED, ACCENT, SUCCESS, WARNING, DANGER, WHITE,
    State, RARITY_ORDER,
)
from progression.rarity import rarity_system


# ── Helpers ───────────────────────────────────────────────────────────────────

def _draw_esc_button(surface: "pygame.Surface", font: "pygame.font.Font") -> "pygame.Rect":
    """Draw a small [ESC] button in the top-left corner. Returns its Rect."""
    btn = pygame.Rect(10, 10, 68, 26)
    pygame.draw.rect(surface, (25, 25, 40), btn)
    pygame.draw.rect(surface, (80, 80, 110), btn, 1)
    txt = font.render("ESC ←", True, (140, 140, 180))
    surface.blit(txt, (btn.x + 6, btn.y + (btn.h - txt.get_height()) // 2))
    return btn


def _draw_button(surface, rect, label, font, active=True, selected=False):
    bg  = (30, 60, 100) if selected else (20, 30, 50)
    fg  = TEXT_MAIN if active else TEXT_MUTED
    pygame.draw.rect(surface, bg, rect)
    pygame.draw.rect(surface, BORDER, rect, 1)
    txt = font.render(label, True, fg)
    surface.blit(txt, (rect.x + rect.w // 2 - txt.get_width() // 2,
                        rect.y + rect.h // 2 - txt.get_height() // 2))
    return rect


def _wrap(text, max_w, font):
    words = text.split()
    lines, cur = [], ""
    for word in words:
        test = (cur + " " + word).strip()
        if font.size(test)[0] <= max_w:
            cur = test
        else:
            if cur: lines.append(cur)
            cur = word
    if cur: lines.append(cur)
    return lines


# ── Main Menu ─────────────────────────────────────────────────────────────────

class MainMenuScreen:
    def __init__(self, game):
        self.game     = game
        pygame.font.init()
        self._font_lg = pygame.font.SysFont("monospace", 48, bold=True)
        self._font    = pygame.font.SysFont("monospace", 20)
        self._font_sm = pygame.font.SysFont("monospace", 13)
        self._buttons = [
            ("New Game",    State.ORIGIN_SELECT),
            ("Load Game",   State.LOAD_SCREEN),
            ("Compendium",  "compendium"),
            ("Lore Codex",  "codex"),
            ("Quit",        "quit"),
        ]
        self._selected = 0

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self._selected = (self._selected - 1) % len(self._buttons)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self._selected = (self._selected + 1) % len(self._buttons)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._activate(self._buttons[self._selected][1])
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, (_, rect) in enumerate(self._btn_rects):
                if rect.collidepoint(event.pos):
                    self._activate(self._buttons[i][1])

    def _activate(self, target):
        if target == "quit":
            self.game.running = False
        elif target == "codex":
            self.game.change_state("codex_screen")
        elif target == "compendium":
            self.game.change_state("compendium_screen")
        else:
            self.game.change_state(target)

    def update(self, dt): pass

    def draw(self, surface):
        surface.fill(DARK_BG)
        # Stars background
        import random; rng = random.Random(42)
        for _ in range(120):
            sx = rng.randint(0, SCREEN_WIDTH)
            sy = rng.randint(0, SCREEN_HEIGHT)
            pygame.draw.circle(surface, (200, 200, 220), (sx, sy), 1)

        title = self._font_lg.render("SPACE PIRATES", True, ACCENT)
        surface.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 120))

        sub = self._font_sm.render("Hunt. Raid. Upgrade. Survive.", True, TEXT_MUTED)
        surface.blit(sub, (SCREEN_WIDTH // 2 - sub.get_width() // 2, 182))

        self._btn_rects = []
        bw, bh = 260, 46
        by = 260
        for i, (label, _) in enumerate(self._buttons):
            rect = pygame.Rect(SCREEN_WIDTH // 2 - bw // 2, by, bw, bh)
            _draw_button(surface, rect, label, self._font,
                         selected=(i == self._selected))
            self._btn_rects.append((label, rect))
            by += bh + 10


# ── Origin Select ─────────────────────────────────────────────────────────────

# Rarity colours for ship-pick screen
_RARITY_COL = {
    "common":   (160, 160, 180),
    "uncommon": ( 80, 200, 120),
    "rare":     ( 80, 140, 255),
    "epic":     (180,  80, 255),
    "secret":   (255, 200,  60),
}


class OriginSelectScreen:
    """Two-step new-game flow:
    Step 1 — pick an origin (background / bonuses)
    Step 2 — pick your starting ship from the starter-flagged pool
    """

    ORIGINS = [
        ("ex_military",       "Ex-Military",
         "You served in a planetary navy before going rogue.",
         "Hull +30  Combat +3  Gunnery +2",
         (220, 80, 80)),
        ("born_pirate",       "Born Pirate",
         "Born on a pirate station — this life chose you.",
         "Credits +400  Luck +10%  Speed +5",
         (255, 160, 40)),
        ("escaped_prisoner",  "Escaped Prisoner",
         "You broke out of a corporate prison with nothing but rage.",
         "Speed +15  Gunnery +3  Evasion +3%",
         (160, 80, 255)),
        ("merchant_defector", "Merchant Defector",
         "You embezzled a freighter and never looked back.",
         "Credits +800  Trade discount  Cargo +20%",
         (60, 200, 140)),
        ("rogue_engineer",    "Rogue Engineer",
         "Ex-shipyard tech who knows every bolt of every hull.",
         "Shield +40  Repair +2/s  Drone slots +1",
         (80, 180, 255)),
        ("void_wanderer",     "Void Wanderer",
         "You drifted alone in deep space. Nobody knows how you survived.",
         "Fuel +60  Evasion +5%  Mystery origin bonus",
         (200, 200, 255)),
    ]

    def __init__(self, game):
        self.game           = game
        self._step          = 1          # 1=origin, 2=ship
        self._sel_origin    = 0
        self._sel_ship      = 0
        self._origin_id     = None
        self._ships_data    = []         # populated on step 2 entry
        self._ship_surf_cache: dict[str, pygame.Surface] = {}
        pygame.font.init()
        self._font    = pygame.font.SysFont("monospace", 18, bold=True)
        self._font_md = pygame.font.SysFont("monospace", 14)
        self._font_sm = pygame.font.SysFont("monospace", 11)
        self._origin_btns: list[pygame.Rect] = []
        self._ship_btns:   list[pygame.Rect] = []
        self._confirm_rect: pygame.Rect | None = None
        self._back_rect:    pygame.Rect | None = None
        self._esc_rect:     pygame.Rect | None = None

    # ── helpers ───────────────────────────────────────────────────────────────
    def _load_starters(self):
        import json as _j
        try:
            with open("data/ships.json") as f:
                all_ships = _j.load(f)
            self._ships_data = [s for s in all_ships if s.get("starter", False)]
        except Exception:
            self._ships_data = []

    def _ship_preview_surf(self, sdata: dict) -> pygame.Surface:
        sid = sdata["id"]
        if sid not in self._ship_surf_cache:
            from entities.ship import Ship as _Ship
            try:
                s     = _Ship(sdata)
                scale = 3
                w, h  = s._sprite_dims()
                big   = pygame.Surface((w * scale, h * scale), pygame.SRCALPHA)
                tmp   = pygame.Surface((w, h), pygame.SRCALPHA)
                s._draw_ship_shape(tmp, s.color_scheme, w, h)
                pygame.transform.scale(tmp, (w * scale, h * scale), big)
                self._ship_surf_cache[sid] = big
            except Exception:
                fallback = pygame.Surface((80, 40), pygame.SRCALPHA)
                pygame.draw.polygon(fallback, (120, 120, 180),
                                    [(76, 20), (10, 4), (4, 20), (10, 36)])
                self._ship_surf_cache[sid] = fallback
        return self._ship_surf_cache[sid]

    # ── event handling ────────────────────────────────────────────────────────
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self._step == 2:
                    self._step = 1
                else:
                    self.game.change_state(State.MAIN_MENU)
            elif event.key in (pygame.K_LEFT, pygame.K_a):
                if self._step == 1:
                    self._sel_origin = (self._sel_origin - 1) % len(self.ORIGINS)
                else:
                    self._sel_ship = (self._sel_ship - 1) % max(len(self._ships_data), 1)
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                if self._step == 1:
                    self._sel_origin = (self._sel_origin + 1) % len(self.ORIGINS)
                else:
                    self._sel_ship = (self._sel_ship + 1) % max(len(self._ships_data), 1)
            elif event.key == pygame.K_RETURN:
                self._advance()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            if self._esc_rect and self._esc_rect.collidepoint(mx, my):
                if self._step == 2:
                    self._step = 1
                else:
                    self.game.change_state(State.MAIN_MENU)
                return
            if self._back_rect and self._back_rect.collidepoint(mx, my):
                if self._step == 2:
                    self._step = 1
                else:
                    self.game.change_state(State.MAIN_MENU)
                return
            if self._step == 1:
                for i, r in enumerate(self._origin_btns):
                    if r.collidepoint(mx, my):
                        self._sel_origin = i
                if self._confirm_rect and self._confirm_rect.collidepoint(mx, my):
                    self._advance()
            else:
                # Nav arrows in detail panel
                if (hasattr(self, "_nav_left_rect") and self._nav_left_rect
                        and self._nav_left_rect.collidepoint(mx, my)):
                    self._sel_ship = (self._sel_ship - 1) % max(len(self._ships_data), 1)
                    return
                if (hasattr(self, "_nav_right_rect") and self._nav_right_rect
                        and self._nav_right_rect.collidepoint(mx, my)):
                    self._sel_ship = (self._sel_ship + 1) % max(len(self._ships_data), 1)
                    return
                # Sidebar list rows (skip None placeholders for off-screen rows)
                for i, r in enumerate(self._ship_btns):
                    if r is not None and r.collidepoint(mx, my):
                        self._sel_ship = i
                        return
                if self._confirm_rect and self._confirm_rect.collidepoint(mx, my):
                    self._advance()

    def _advance(self):
        if self._step == 1:
            self._origin_id = self.ORIGINS[self._sel_origin][0]
            self._load_starters()
            self._sel_ship  = 0
            self._step      = 2
        else:
            if not self._ships_data:
                return
            ship_id = self._ships_data[self._sel_ship]["id"]
            self.game.change_state(State.BASE,
                                   origin=self._origin_id,
                                   ship_id=ship_id)

    def update(self, dt): pass

    # ── drawing ───────────────────────────────────────────────────────────────
    def draw(self, surface: pygame.Surface):
        surface.fill(DARK_BG)
        self._esc_rect = _draw_esc_button(surface, self._font_sm)
        if self._step == 1:
            self._draw_origin_step(surface)
        else:
            self._draw_ship_step(surface)

    def _draw_origin_step(self, surface: pygame.Surface):
        sw, sh = surface.get_size()

        # Title
        t = self._font.render("CHOOSE YOUR ORIGIN", True, ACCENT)
        surface.blit(t, (sw // 2 - t.get_width() // 2, 22))
        sub = self._font_sm.render(
            "Your background shapes your starting bonuses  —  use ← → or click",
            True, TEXT_MUTED)
        surface.blit(sub, (sw // 2 - sub.get_width() // 2, 48))

        # Origin cards — 2 per row
        card_w, card_h = 380, 130
        cols    = 2
        gap     = 20
        total_w = cols * card_w + (cols - 1) * gap
        start_x = sw // 2 - total_w // 2
        start_y = 80

        self._origin_btns = []
        for i, (oid, name, flavour, bonuses, col) in enumerate(self.ORIGINS):
            col_i = i % cols
            row_i = i // cols
            rx    = start_x + col_i * (card_w + gap)
            ry    = start_y + row_i * (card_h + 14)
            sel   = (i == self._sel_origin)

            # Card background
            r_rect = pygame.Rect(rx, ry, card_w, card_h)
            bg     = (25, 35, 55) if sel else PANEL_BG
            pygame.draw.rect(surface, bg, r_rect, border_radius=6)
            pygame.draw.rect(surface, col if sel else BORDER, r_rect,
                             2 if sel else 1, border_radius=6)

            # Colour accent bar on left
            pygame.draw.rect(surface, col, pygame.Rect(rx, ry + 6, 4, card_h - 12),
                             border_radius=2)

            # Name
            n = self._font_md.render(name, True, col if sel else TEXT_MAIN)
            surface.blit(n, (rx + 14, ry + 10))

            # Flavour text (italic-style via wrapping)
            max_chars = 46
            words     = flavour.split()
            lines, line = [], ""
            for w_ in words:
                if len(line) + len(w_) + 1 <= max_chars:
                    line = (line + " " + w_).strip()
                else:
                    lines.append(line)
                    line = w_
            lines.append(line)
            for li, ln in enumerate(lines[:2]):
                ft = self._font_sm.render(ln, True, TEXT_MUTED)
                surface.blit(ft, (rx + 14, ry + 32 + li * 14))

            # Bonus line
            bt = self._font_sm.render(bonuses, True, col if sel else (120, 200, 120))
            surface.blit(bt, (rx + 14, ry + card_h - 22))

            self._origin_btns.append(r_rect)

        # NEXT button
        ny = start_y + ((len(self.ORIGINS) - 1) // cols + 1) * (card_h + 14) + 20
        cw, ch_ = 260, 44
        self._confirm_rect = pygame.Rect(sw // 2 - cw // 2, ny, cw, ch_)
        _draw_button(surface, self._confirm_rect, "Next: Pick Ship →", self._font_md)
        self._back_rect = None

    def _draw_ship_step(self, surface: pygame.Surface):
        sw, sh = surface.get_size()

        # Header
        orig_name = self.ORIGINS[self._sel_origin][1]
        t = self._font.render(f"PICK YOUR SHIP  —  {orig_name}", True, ACCENT)
        surface.blit(t, (sw // 2 - t.get_width() // 2, 14))
        sub = self._font_sm.render(
            "← → or click to browse  ·  ENTER to confirm",
            True, TEXT_MUTED)
        surface.blit(sub, (sw // 2 - sub.get_width() // 2, 36))

        if not self._ships_data:
            nt = self._font_md.render("No starter ships found.", True, DANGER)
            surface.blit(nt, (sw // 2 - nt.get_width() // 2, sh // 2))
            return

        n = len(self._ships_data)
        sel = max(0, min(self._sel_ship, n - 1))

        # ── Layout: LEFT panel = ship list sidebar, RIGHT panel = detail ─────
        LIST_W   = 220
        DETAIL_X = LIST_W + 16
        DETAIL_W = sw - DETAIL_X - 16
        LIST_Y   = 58
        LIST_H   = sh - LIST_Y - 56   # leave room for buttons

        # ── Left sidebar: scrollable ship list ───────────────────────────────
        pygame.draw.rect(surface, (10, 14, 24),
                         (0, LIST_Y, LIST_W, LIST_H))
        pygame.draw.line(surface, BORDER,
                         (LIST_W, LIST_Y), (LIST_W, LIST_Y + LIST_H))

        ROW_H   = 52
        max_vis = LIST_H // ROW_H
        # Keep selected row visible — scroll the list
        list_scroll = max(0, sel - max_vis + 2)
        list_scroll = min(list_scroll, max(0, n - max_vis))

        self._ship_btns = []
        for i, sdata in enumerate(self._ships_data):
            vis_i = i - list_scroll
            if vis_i < 0 or vis_i >= max_vis:
                self._ship_btns.append(None)   # placeholder for index alignment
                continue
            ry  = LIST_Y + vis_i * ROW_H
            rar = sdata.get("rarity", "common")
            rc  = _RARITY_COL.get(rar, (160, 160, 180))
            is_sel = (i == sel)

            row_r = pygame.Rect(0, ry, LIST_W - 1, ROW_H - 2)
            pygame.draw.rect(surface, (25, 38, 62) if is_sel else (14, 18, 30),
                             row_r)
            pygame.draw.rect(surface, rc if is_sel else (40, 44, 58), row_r, 1)
            # Colour stripe on left
            pygame.draw.rect(surface, rc, (0, ry, 3, ROW_H - 2))

            # Mini sprite preview
            prev = self._ship_preview_surf(sdata)
            prev_small = pygame.transform.scale(prev, (36, 22))
            surface.blit(prev_small, (6, ry + ROW_H // 2 - 11))

            nm_t = self._font_md.render(sdata["name"][:16], True,
                                        rc if is_sel else TEXT_MAIN)
            surface.blit(nm_t, (46, ry + 6))
            cl_t = self._font_sm.render(
                sdata["class"].replace("_", " ").title()[:18],
                True, (120, 130, 150))
            surface.blit(cl_t, (46, ry + 22))
            hull_t = self._font_sm.render(
                f"HP {sdata['max_hull']}", True, (80, 160, 80))
            surface.blit(hull_t, (46, ry + 36))

            self._ship_btns.append(row_r)

        # Scroll arrows on sidebar
        if list_scroll > 0:
            arr = self._font_sm.render("▲ more", True, TEXT_MUTED)
            surface.blit(arr, (LIST_W // 2 - arr.get_width() // 2, LIST_Y + 2))
        if list_scroll + max_vis < n:
            arr = self._font_sm.render("▼ more", True, TEXT_MUTED)
            surface.blit(arr, (LIST_W // 2 - arr.get_width() // 2,
                                LIST_Y + LIST_H - 14))

        # ── Right panel: full detail for the selected ship ────────────────────
        sdata = self._ships_data[sel]
        rar   = sdata.get("rarity", "common")
        rcol  = _RARITY_COL.get(rar, (160, 160, 180))

        pygame.draw.rect(surface, (12, 18, 32),
                         (DETAIL_X, LIST_Y, DETAIL_W, LIST_H),
                         border_radius=8)
        pygame.draw.rect(surface, rcol,
                         (DETAIL_X, LIST_Y, DETAIL_W, LIST_H),
                         2, border_radius=8)

        dy = LIST_Y + 14

        # Ship name + rarity banner
        big_name = self._font.render(sdata["name"], True, rcol)
        surface.blit(big_name, (DETAIL_X + 16, dy))
        rar_t = self._font_md.render(
            f"[{rar.upper()}]  {sdata['class'].replace('_',' ').title()}",
            True, rcol)
        surface.blit(rar_t, (DETAIL_X + 16, dy + big_name.get_height() + 2))
        dy += big_name.get_height() + rar_t.get_height() + 12

        # ── Large sprite preview ──────────────────────────────────────────────
        preview = self._ship_preview_surf(sdata)
        # Scale up 2× for the detail panel
        big_prev = pygame.transform.scale(
            preview, (preview.get_width() * 2, preview.get_height() * 2))
        bpw, bph = big_prev.get_size()
        px_ = DETAIL_X + DETAIL_W - bpw - 16
        py_ = LIST_Y + 12
        surface.blit(big_prev, (px_, py_))

        # ── Stats — each with a labelled bar ─────────────────────────────────
        font_lbl  = pygame.font.SysFont("monospace", 13, bold=True)
        font_val  = pygame.font.SysFont("monospace", 12)
        bar_total = DETAIL_W - 32 - bpw - 20   # bar fits left of sprite
        bar_x     = DETAIL_X + 16

        stats = [
            ("Hull",      sdata["max_hull"],             800,  (80,  200, 80)),
            ("Shield",    sdata["max_shield"],            600,  (80,  160, 255)),
            ("Speed",     sdata["base_speed"],            300,  (255, 200, 60)),
            ("Evasion",   int(sdata.get("base_evasion",0)*100), 30, (180, 120, 255)),
            ("Crew Slots",sdata.get("crew_slots", 3),      8,  (120, 210, 200)),
            ("Drones",    sdata.get("drone_slots", 0),     8,  (255, 140, 60)),
            ("Bay Slots", sdata.get("bay_slots", 0),       4,  (255, 200, 100)),
        ]
        for label, val, max_val, bar_col in stats:
            frac = min(1.0, val / max(max_val, 1))
            lbl_s = font_lbl.render(f"{label}", True, TEXT_MUTED)
            val_s = font_val.render(str(val), True, TEXT_MAIN)
            surface.blit(lbl_s, (bar_x, dy))
            surface.blit(val_s, (bar_x + 110, dy))
            # Background track
            pygame.draw.rect(surface, (30, 30, 45),
                             (bar_x, dy + 15, bar_total, 7), border_radius=3)
            # Filled portion
            if frac > 0:
                pygame.draw.rect(surface, bar_col,
                                 (bar_x, dy + 15, max(4, int(bar_total * frac)), 7),
                                 border_radius=3)
            dy += 28

        dy += 6
        pygame.draw.line(surface, (35, 42, 60),
                         (DETAIL_X + 14, dy), (DETAIL_X + DETAIL_W - 14, dy))
        dy += 10

        # ── Hardpoints ───────────────────────────────────────────────────────
        hp = sdata.get("hardpoint_slots", {})
        if any(hp.values()):
            hp_s = font_lbl.render(
                f"Weapons:  S×{hp.get('small',0)}  M×{hp.get('medium',0)}"
                f"  L×{hp.get('large',0)}",
                True, (200, 180, 80))
            surface.blit(hp_s, (bar_x, dy))
            dy += 18

        # ── Description ───────────────────────────────────────────────────────
        desc_raw = sdata.get("description", "")
        # Word-wrap at ~55 chars
        words  = desc_raw.split()
        lines, line = [], []
        for w in words:
            if len(" ".join(line + [w])) > 55:
                if line:
                    lines.append(" ".join(line))
                line = [w]
            else:
                line.append(w)
        if line:
            lines.append(" ".join(line))
        for ln in lines[:3]:
            lt = font_val.render(ln, True, TEXT_MUTED)
            surface.blit(lt, (bar_x, dy))
            dy += 15
        dy += 4

        # ── Lore ─────────────────────────────────────────────────────────────
        lore = sdata.get("lore", "")
        if lore and dy < LIST_Y + LIST_H - 30:
            lore_clip = f'"{lore[:70]}"'
            lr_t = font_val.render(lore_clip, True, (130, 130, 180))
            surface.blit(lr_t, (bar_x, dy))
            dy += 16

        # ── Quirks ───────────────────────────────────────────────────────────
        quirks = sdata.get("quirks", [])
        if quirks and dy < LIST_Y + LIST_H - 30:
            for q in quirks[:2]:
                qt = font_val.render(f"✦ {q[:54]}", True, (200, 200, 100))
                surface.blit(qt, (bar_x, dy))
                dy += 14

        # ── Nav arrows (←  N/total  →) ───────────────────────────────────────
        nav_y = LIST_Y + LIST_H + 6
        arr_font = pygame.font.SysFont("monospace", 20, bold=True)
        left_r  = pygame.Rect(DETAIL_X,              nav_y, 40, 36)
        right_r = pygame.Rect(DETAIL_X + DETAIL_W - 40, nav_y, 40, 36)
        for arr_r, lbl in [(left_r, "◀"), (right_r, "▶")]:
            pygame.draw.rect(surface, (20, 30, 50), arr_r, border_radius=4)
            pygame.draw.rect(surface, BORDER, arr_r, 1, border_radius=4)
            at = arr_font.render(lbl, True, ACCENT)
            surface.blit(at, (arr_r.centerx - at.get_width() // 2,
                               arr_r.centery - at.get_height() // 2))
        ctr_t = self._font_md.render(
            f"{sel + 1} / {n}", True, TEXT_MUTED)
        surface.blit(ctr_t, (DETAIL_X + DETAIL_W // 2 - ctr_t.get_width() // 2,
                              nav_y + 9))
        self._nav_left_rect  = left_r
        self._nav_right_rect = right_r

        # ── Bottom buttons ────────────────────────────────────────────────────
        btn_y = sh - 50
        cw, ch_ = 240, 40
        self._confirm_rect = pygame.Rect(sw // 2 + 10, btn_y, cw, ch_)
        _draw_button(surface, self._confirm_rect, "▶ Begin Run", self._font_md)

        bw2 = 160
        self._back_rect = pygame.Rect(sw // 2 - bw2 - 10, btn_y, bw2, ch_)
        pygame.draw.rect(surface, PANEL_BG, self._back_rect, border_radius=4)
        pygame.draw.rect(surface, TEXT_MUTED, self._back_rect, 1, border_radius=4)
        bk = self._font_sm.render("← Back", True, TEXT_MUTED)
        surface.blit(bk, (self._back_rect.centerx - bk.get_width() // 2,
                          self._back_rect.centery - bk.get_height() // 2))


# ── Load Screen ───────────────────────────────────────────────────────────────

class LoadScreen:
    def __init__(self, game):
        self.game   = game
        self._slots = []
        pygame.font.init()
        self._font    = pygame.font.SysFont("monospace", 15)
        self._font_sm = pygame.font.SysFont("monospace", 12)
        # Each slot row has a load rect and a delete rect
        self._load_rects:   list[pygame.Rect | None] = []
        self._delete_rects: list[pygame.Rect | None] = []
        self._back_rect:    pygame.Rect | None = None
        # Confirmation state: slot index waiting for delete confirm, or None
        self._confirm_delete: int | None = None

    def _refresh(self):
        from core.save import list_saves
        self._slots = list_saves()
        self._confirm_delete = None

    def handle_event(self, event):
        if not self._slots:
            self._refresh()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            # ESC button top-left
            if hasattr(self, "_esc_click_rect") and self._esc_click_rect.collidepoint(mx, my):
                self.game.change_state(State.MAIN_MENU)
                return
            # Back to menu (bottom button)
            if self._back_rect and self._back_rect.collidepoint(mx, my):
                self.game.change_state(State.MAIN_MENU)
                return
            # If confirming a delete, check for Yes / No rects
            if self._confirm_delete is not None:
                if hasattr(self, "_confirm_yes") and self._confirm_yes.collidepoint(mx, my):
                    from core.save import delete_save
                    delete_save(self._confirm_delete)
                    self._refresh()
                    return
                if hasattr(self, "_confirm_no") and self._confirm_no.collidepoint(mx, my):
                    self._confirm_delete = None
                    return
                return  # swallow other clicks while confirming
            for i, (lr, dr) in enumerate(zip(self._load_rects, self._delete_rects)):
                if dr and dr.collidepoint(mx, my) and self._slots[i]:
                    self._confirm_delete = i
                    return
                if lr and lr.collidepoint(mx, my) and self._slots[i]:
                    self.game.save_slot = i
                    self.game.change_state(State.BASE)
                    return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self._confirm_delete is not None:
                self._confirm_delete = None
            else:
                self.game.change_state(State.MAIN_MENU)

    def update(self, dt):
        if not self._slots:
            self._refresh()

    def draw(self, surface):
        surface.fill(DARK_BG)
        # ESC button top-left
        self._esc_click_rect = _draw_esc_button(surface, self._font_sm)
        font_lg = pygame.font.SysFont("monospace", 26, bold=True)
        title = font_lg.render("LOAD GAME", True, ACCENT)
        surface.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 28))

        self._load_rects   = []
        self._delete_rects = []

        bw, bh = 560, 80
        del_w   = 90
        gap     = 10
        row_w   = bw + gap + del_w
        left_x  = SCREEN_WIDTH // 2 - row_w // 2
        by = 90

        for i, slot in enumerate(self._slots):
            # ── Load / info rect ─────────────────────────────────────────────
            lr = pygame.Rect(left_x, by, bw, bh)
            pygame.draw.rect(surface, PANEL_BG, lr)
            pygame.draw.rect(surface, BORDER, lr, 1)
            if slot:
                lines = [
                    f"Slot {i + 1}  —  Captain: {slot['captain']}",
                    f"Sector: {slot['sector']}   Kills: {slot['kills']}",
                    f"Playtime: {slot['playtime'] // 60}m  {'[NG+]' if slot['ng_plus'] else ''}",
                ]
                for j, line in enumerate(lines):
                    t = self._font_sm.render(line, True, TEXT_MAIN if j == 0 else TEXT_MUTED)
                    surface.blit(t, (lr.x + 12, lr.y + 8 + j * 20))
                self._load_rects.append(lr)
            else:
                empty = self._font_sm.render(f"Slot {i + 1}  —  Empty", True, TEXT_MUTED)
                surface.blit(empty, (lr.x + 12, lr.y + 28))
                self._load_rects.append(None)  # not clickable

            # ── Delete button ────────────────────────────────────────────────
            dr = pygame.Rect(left_x + bw + gap, by, del_w, bh)
            if slot:
                pygame.draw.rect(surface, (50, 15, 15), dr)
                pygame.draw.rect(surface, DANGER, dr, 1)
                del_txt = self._font_sm.render("🗑 DELETE", True, DANGER)
                surface.blit(del_txt, (dr.centerx - del_txt.get_width() // 2,
                                       dr.centery - del_txt.get_height() // 2))
                self._delete_rects.append(dr)
            else:
                self._delete_rects.append(None)

            by += bh + 14

        # ── Back button ───────────────────────────────────────────────────────
        self._back_rect = pygame.Rect(SCREEN_WIDTH // 2 - 130, by + 14, 260, 38)
        pygame.draw.rect(surface, PANEL_BG,   self._back_rect)
        pygame.draw.rect(surface, TEXT_MUTED, self._back_rect, 1)
        back_txt = self._font.render("← Back to Main Menu", True, TEXT_MUTED)
        surface.blit(back_txt, (self._back_rect.centerx - back_txt.get_width() // 2,
                                 self._back_rect.centery - back_txt.get_height() // 2))

        # ── Delete confirmation overlay ───────────────────────────────────────
        if self._confirm_delete is not None:
            ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 180))
            surface.blit(ov, (0, 0))
            cw, ch = 400, 140
            cx = SCREEN_WIDTH // 2 - cw // 2
            cy = SCREEN_HEIGHT // 2 - ch // 2
            pygame.draw.rect(surface, PANEL_BG, (cx, cy, cw, ch), border_radius=8)
            pygame.draw.rect(surface, DANGER,   (cx, cy, cw, ch), 2, border_radius=8)
            msg1 = self._font.render("Delete this save?", True, TEXT_MAIN)
            msg2 = self._font_sm.render("This cannot be undone.", True, TEXT_MUTED)
            surface.blit(msg1, (cx + cw // 2 - msg1.get_width() // 2, cy + 18))
            surface.blit(msg2, (cx + cw // 2 - msg2.get_width() // 2, cy + 42))
            self._confirm_yes = pygame.Rect(cx + 30,        cy + 82, 150, 36)
            self._confirm_no  = pygame.Rect(cx + cw - 180,  cy + 82, 150, 36)
            pygame.draw.rect(surface, (60, 15, 15), self._confirm_yes)
            pygame.draw.rect(surface, DANGER,       self._confirm_yes, 1)
            pygame.draw.rect(surface, PANEL_BG,     self._confirm_no)
            pygame.draw.rect(surface, TEXT_MUTED,   self._confirm_no, 1)
            yes_t = self._font.render("Yes, Delete", True, DANGER)
            no_t  = self._font.render("Cancel",      True, TEXT_MUTED)
            surface.blit(yes_t, (self._confirm_yes.centerx - yes_t.get_width() // 2,
                                  self._confirm_yes.centery - yes_t.get_height() // 2))
            surface.blit(no_t,  (self._confirm_no.centerx  - no_t.get_width()  // 2,
                                  self._confirm_no.centery  - no_t.get_height()  // 2))


# ── Pause Menu ────────────────────────────────────────────────────────────────

class PauseMenu:
    def __init__(self, game):
        self.game    = game
        self._items  = ["Resume", "Crew Orders", "Galaxy Map", "Save & Quit"]
        self._sel    = 0
        pygame.font.init()
        self._font   = pygame.font.SysFont("monospace", 20)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.game.change_state(State.PLAYING)
            elif event.key in (pygame.K_UP, pygame.K_w):
                self._sel = (self._sel - 1) % len(self._items)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self._sel = (self._sel + 1) % len(self._items)
            elif event.key == pygame.K_RETURN:
                self._activate()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, rect in enumerate(self._rects):
                if rect.collidepoint(event.pos):
                    self._sel = i
                    self._activate()

    def _activate(self):
        item = self._items[self._sel]
        if item == "Resume":
            self.game.change_state(State.PLAYING)
        elif item == "Galaxy Map":
            self.game.change_state(State.GALAXY_MAP)
        elif item == "Save & Quit":
            self.game.running = False

    def update(self, dt): pass

    def draw(self, surface):
        ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 160))
        surface.blit(ov, (0, 0))

        bw, bh = 260, 46
        by = SCREEN_HEIGHT // 2 - (len(self._items) * (bh + 8)) // 2
        self._rects = []
        for i, item in enumerate(self._items):
            rect = pygame.Rect(SCREEN_WIDTH // 2 - bw // 2, by, bw, bh)
            _draw_button(surface, rect, item, self._font,
                         selected=(i == self._sel))
            self._rects.append(rect)
            by += bh + 8


# ── Crew Management Menu ──────────────────────────────────────────────────────

# AUTO behaviour descriptions shown as tooltip/hint
_AUTO_DESCS = {
    "cockpit":        "Pilot auto-steers toward nearest enemy",
    "gun_turret":     "Gunner fires at nearest enemy",
    "engine_room":    "Engineer boosts speed when chasing",
    "repair_station": "Medic auto-repairs hull below 50%",
    "drone_bay":      "Drone bay auto-launches repair drones",
    "brig":           "Brig crew watches prisoners",
}


class CrewManagementMenu:
    """Right-panel menu for assigning crew to stations + Equip Best + AUTO toggles."""

    def __init__(self):
        pygame.font.init()
        self._font    = pygame.font.SysFont("monospace", 13)
        self._font_sm = pygame.font.SysFont("monospace", 11)
        self._font_lg = pygame.font.SysFont("monospace", 16)
        self._equip_rect: pygame.Rect | None = None
        self._station_rects: dict[str, pygame.Rect] = {}
        self._auto_rects: dict[str, pygame.Rect] = {}
        self._board_rect: pygame.Rect | None = None
        # Per-station auto toggle state (True = on)
        self._auto: dict[str, bool] = {s: False for s in
            ["cockpit", "gun_turret", "engine_room",
             "repair_station", "drone_bay", "brig"]}
        # Drone launcher panel — buttons populated during draw
        self._drone_launch_btns: list[tuple[str, pygame.Rect]] = []

    def is_auto(self, station: str) -> bool:
        return self._auto.get(station, False)

    def handle_event(self, event, ship, combat=None):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            # The crew/mgmt panel is blit at MGMT_PANEL_X on screen;
            # all rects drawn on mgmt_surf use local (panel-relative) coords.
            # Translate screen coords → panel-local coords for hit-testing.
            try:
                from ui.splitscreen import MGMT_PANEL_X
                lx, ly = mx - MGMT_PANEL_X, my
            except ImportError:
                lx, ly = mx, my
            # AUTO toggles
            for station, btn in self._auto_rects.items():
                if btn.collidepoint(lx, ly):
                    self._auto[station] = not self._auto[station]
                    return f"auto_toggle:{station}"
            if self._equip_rect and self._equip_rect.collidepoint(lx, ly):
                ship.equip_best()
                return "equip_best"
            if self._board_rect and self._board_rect.collidepoint(lx, ly):
                return "board"
            # Drone launch buttons
            for dtype, drect in self._drone_launch_btns:
                if drect.collidepoint(lx, ly):
                    return f"launch_drone:{dtype}"
        # Keyboard shortcut: Y = toggle pilot auto
        if event.type == pygame.KEYDOWN and event.key == pygame.K_y:
            self._auto["cockpit"] = not self._auto["cockpit"]
            return "auto_toggle:cockpit"
        return None

    def draw(self, surface: pygame.Surface, ship, offset_x: int = 0,
             combat=None) -> None:
        if not ship:
            return
        from ui.splitscreen import MGMT_PANEL_W
        x0  = offset_x + 8
        y   = 10
        w   = MGMT_PANEL_W - 16
        sh  = surface.get_height()

        # Ship name header
        rarity_color = rarity_system.color(ship.rarity)
        name_surf = self._font_lg.render(
            f"{ship.custom_name}  [{rarity_system.name(ship.rarity)}]",
            True, rarity_color)
        surface.blit(name_surf, (x0, y)); y += 20

        # Hull/Shield bars (visual)
        for val, maxval, color, label in [
            (ship.hull,   ship.max_hull,   SUCCESS,        f"Hull  {ship.hull:.0f}/{ship.max_hull}"),
            (ship.shield, ship.max_shield, (60, 120, 255), f"Shld  {ship.shield:.0f}/{ship.max_shield}"),
        ]:
            pct = val / max(maxval, 1)
            pygame.draw.rect(surface, (30, 10, 10), (x0, y, w, 7))
            pygame.draw.rect(surface, color,        (x0, y, int(w * pct), 7))
            lbl = self._font_sm.render(label, True, TEXT_MUTED)
            surface.blit(lbl, (x0 + 2, y - 1)); y += 10
        y += 4

        pygame.draw.line(surface, BORDER, (x0, y), (x0 + w, y)); y += 6

        # ── STATIONS + AUTO buttons ────────────────────────────────────────────
        title = self._font.render("STATIONS", True, ACCENT)
        # "AUTO" column header
        auto_hdr = self._font_sm.render("AUTO", True, TEXT_MUTED)
        auto_btn_w = 36
        auto_x = x0 + w - auto_btn_w
        surface.blit(title, (x0, y))
        surface.blit(auto_hdr, (auto_x + auto_btn_w // 2 - auto_hdr.get_width() // 2, y))
        y += 16

        self._station_rects = {}
        self._auto_rects    = {}
        from entities.ship import STATIONS
        STATION_SHORT = {
            "cockpit":        "Cockpit",
            "gun_turret":     "Gun",
            "engine_room":    "Engine",
            "repair_station": "Repair",
            "drone_bay":      "Drones",
            "brig":           "Brig",
        }
        ROW_H = 20
        for station in STATIONS:
            crew = ship.station_assignments.get(station)
            lbl  = STATION_SHORT.get(station, station)
            crew_name  = crew.name[:10] if crew else "(empty)"
            crew_color = rarity_system.color(crew.rarity) if crew else TEXT_MUTED
            if station == "brig" and crew:
                crew_color = (255, 160, 40)

            # Row background
            row_rect = pygame.Rect(x0, y, w - auto_btn_w - 4, ROW_H)
            self._station_rects[station] = row_rect
            pygame.draw.rect(surface, (20, 20, 35), row_rect)
            stn_txt = self._font_sm.render(f"{lbl:<8} {crew_name}", True, crew_color)
            surface.blit(stn_txt, (x0 + 2, y + (ROW_H - stn_txt.get_height()) // 2))

            # AUTO toggle button
            on = self._auto.get(station, False)
            abtn = pygame.Rect(auto_x, y, auto_btn_w, ROW_H)
            self._auto_rects[station] = abtn
            abg  = (15, 55, 15) if on else (55, 15, 15)
            afg  = SUCCESS      if on else DANGER
            pygame.draw.rect(surface, abg, abtn)
            pygame.draw.rect(surface, afg, abtn, 1)
            at = self._font_sm.render("ON" if on else "OFF", True, afg)
            surface.blit(at, (abtn.centerx - at.get_width() // 2,
                               abtn.centery - at.get_height() // 2))
            y += ROW_H + 1

        y += 4
        pygame.draw.line(surface, BORDER, (x0, y), (x0 + w, y)); y += 6

        # ── CREW ROSTER ───────────────────────────────────────────────────────
        title2 = self._font.render("CREW ROSTER", True, ACCENT)
        surface.blit(title2, (x0, y)); y += 16

        max_crew_y = sh - 100
        for c in ship.crew:
            if y >= max_crew_y:
                more = self._font_sm.render(
                    f"+ {len(ship.crew) - ship.crew.index(c)} more...", True, TEXT_MUTED)
                surface.blit(more, (x0, y)); y += 14
                break
            rc      = rarity_system.color(c.rarity)
            inj     = " [INJ]" if c.injured else ""
            assigned= f" →{c.assigned_station[:5]}" if c.assigned_station else ""
            line    = f"{c.name[:10]:<10} Lv{c.level}{assigned}{inj}"
            cs      = self._font_sm.render(line, True, (180, 80, 80) if c.injured else rc)
            surface.blit(cs, (x0, y)); y += 14

        # ── BOTTOM BUTTONS ────────────────────────────────────────────────────
        btn_y    = sh - 92
        btn_h    = 30
        half_w   = (w - 4) // 2

        # EQUIP BEST (left)
        eb_rect = pygame.Rect(x0, btn_y, half_w, btn_h)
        pygame.draw.rect(surface, (20, 80, 40), eb_rect)
        pygame.draw.rect(surface, SUCCESS, eb_rect, 1)
        eb_txt = self._font_sm.render("⚡ EQUIP BEST", True, SUCCESS)
        surface.blit(eb_txt, (eb_rect.centerx - eb_txt.get_width() // 2,
                               eb_rect.centery - eb_txt.get_height() // 2))
        self._equip_rect = eb_rect

        # BOARD SHIP button (right) — active when nearest enemy is boardable
        self._board_rect = None
        board_target = combat._nearest_boardable_enemy() if combat is not None else None
        board_active = board_target is not None
        brd_rect = pygame.Rect(x0 + half_w + 4, btn_y, half_w, btn_h)

        if board_active:
            import time as _time
            pulse = abs(math.sin(_time.time() * 4))
            # Distinguish: shield-broken (cyan) vs low-hull fallback (orange)
            shield_broken = (board_target.shield <= 0
                             and getattr(board_target, "shield_recharge_lock", 0) > 0)
            if shield_broken:
                r_c     = int(60 + 160 * pulse)
                bg_col  = (0, int(30 * pulse), int(50 * pulse))
                brd_col = (0, r_c, int(r_c * 0.85))     # cyan
            else:
                r_c     = int(100 + 120 * pulse)
                bg_col  = (int(40 * pulse), int(20 * pulse), 0)
                brd_col = (r_c, int(r_c * 0.65), 0)     # orange
        else:
            bg_col  = (20, 20, 30)
            brd_col = (60, 60, 60)

        pygame.draw.rect(surface, bg_col,  brd_rect)
        pygame.draw.rect(surface, brd_col, brd_rect, 2 if board_active else 1)
        brd_txt = self._font_sm.render("⚔ BOARD", True, brd_col)
        surface.blit(brd_txt, (brd_rect.centerx - brd_txt.get_width() // 2,
                                brd_rect.centery - brd_txt.get_height() // 2))
        if board_active:
            self._board_rect = brd_rect

        # Hint line
        if board_active:
            shield_broken2 = (board_target.shield <= 0
                              and getattr(board_target, "shield_recharge_lock", 0) > 0)
            hint_txt = ("Shield down! Press B or BOARD" if shield_broken2
                        else "Hull critical! Press B or BOARD")
            hint = self._font_sm.render(hint_txt, True, (80, 220, 200))
        else:
            hint = self._font_sm.render(
                "Y=autopilot  Click AUTO to toggle station", True, TEXT_MUTED)
        surface.blit(hint, (x0, btn_y + btn_h + 4))

        # ── Drone Launcher Panel ──────────────────────────────────────────────
        self._drone_launch_btns = []
        drone_sys = getattr(combat, "drone_system", None) if combat else None
        if drone_sys is not None and drone_sys.max_slots > 0:
            from combat.drones import DRONE_TYPES
            dy_start = btn_y + btn_h + 20
            dhdr = self._font_sm.render(
                f"DRONES  {drone_sys.active_count}/{drone_sys.max_slots}  "
                f"{'(FULL)' if not drone_sys.can_launch() else ''}",
                True, (255, 200, 60))
            surface.blit(dhdr, (x0, dy_start))
            dy_start += 14

            # Status lines for active drones
            for line in drone_sys.status_lines():
                sl = self._font_sm.render(line, True, (180, 220, 160))
                surface.blit(sl, (x0 + 4, dy_start))
                dy_start += 12

            # Launch buttons — 2 per row
            dy = dy_start + 2
            dx = x0
            btn_w_d = (w - 4) // 2
            btn_h_d = 18
            for i, (dtype, spec) in enumerate(DRONE_TYPES.items()):
                col = spec["color"]
                can = drone_sys.can_launch()
                bg  = (25, 20, 40) if can else (20, 20, 20)
                bc  = col if can else (50, 50, 50)
                db  = pygame.Rect(dx, dy, btn_w_d - 2, btn_h_d)
                pygame.draw.rect(surface, bg, db)
                pygame.draw.rect(surface, bc, db, 1)
                lbl = self._font_sm.render(spec["label"], True, col if can else (60, 60, 60))
                surface.blit(lbl, (db.x + 4, db.centery - lbl.get_height() // 2))
                if can:
                    self._drone_launch_btns.append((dtype, db))
                dx += btn_w_d
                if i % 2 == 1:
                    dx = x0
                    dy += btn_h_d + 2
            dy += btn_h_d + 4

            # Scout radar bonus indicator
            if drone_sys.radar_bonus > 0:
                rb = self._font_sm.render(
                    f"▲ Radar +{drone_sys.radar_bonus}px (Scout active)",
                    True, (100, 200, 255))
                surface.blit(rb, (x0, dy))

        # Weapons summary
        wpn_y = sh - 28
        weapons_str = "  ".join(
            f"{ww.type[:3].upper()}{'*' if ww.chosen_path else ''}"
            for ww in ship.weapons
        ) or "no weapons"
        wt = self._font_sm.render(f"Weapons: {weapons_str}", True, TEXT_MUTED)
        surface.blit(wt, (x0, wpn_y))


# ── Upgrade Tree Menu ─────────────────────────────────────────────────────────

# Ship class upgrade paths
SHIP_CLASS_UPGRADES = {
    "fighter":   [("elite_fighter",  "Elite Fighter",  3000, "fighter"),
                  ("heavy_gunship",  "Heavy Gunship",  5000, "freighter")],
    "freighter": [("heavy_freighter","Heavy Freighter",4000, "freighter"),
                  ("assault_hauler", "Assault Hauler", 6000, "fighter")],
    "carrier":   [("super_carrier",  "Super Carrier",  8000, "carrier"),
                  ("command_ship",   "Command Ship",   12000,"carrier")],
}


class UpgradeTreeMenu:
    def __init__(self, game):
        self.game     = game
        self._scroll  = 0
        self._sel     = 0
        pygame.font.init()
        self._font    = pygame.font.SysFont("monospace", 14)
        self._font_sm = pygame.font.SysFont("monospace", 11)
        self._btn_rects: list[tuple[str, pygame.Rect]] = []
        self._ship_upgrade_btns: list[tuple] = []   # (ship, new_class, new_name, cost, rect)
        self._selected_ship_for_upgrade = None

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.game.change_state(State.BASE)
            elif event.key in (pygame.K_UP, pygame.K_w):
                self._sel = max(0, self._sel - 1)
                self._scroll = max(0, self._scroll - 56)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self._sel = min(len(self._btn_rects) - 1, self._sel + 1)
                self._scroll += 56
            elif event.key == pygame.K_RETURN:
                if self._btn_rects:
                    uid, _ = self._btn_rects[self._sel]
                    self._purchase(uid)
        # Mouse wheel scrolls the right-side upgrade list
        if event.type == pygame.MOUSEWHEEL:
            self._scroll = max(0, self._scroll - event.y * 40)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            # Back to Base button (not scrolled — always at bottom)
            if (hasattr(self, "_back_to_base_rect") and
                    self._back_to_base_rect and
                    self._back_to_base_rect.collidepoint(mx, my)):
                self.game.change_state(State.BASE)
                return
            # Ship class upgrade buttons (left panel, unscrolled)
            for ship, new_class, new_name, cost, rect in self._ship_upgrade_btns:
                if rect.collidepoint(mx, my):
                    self._do_ship_class_upgrade(ship, new_class, new_name, cost)
                    return
            # Upgrade tree buttons (right panel, scrolled)
            for uid, rect in self._btn_rects:
                if rect.collidepoint(mx, my):
                    self._purchase(uid)

    def _do_ship_class_upgrade(self, ship, new_class: str, new_name: str, cost: int):
        """Upgrade a ship's class if player can afford it, or select for upgrade sub-panel."""
        if new_class == "select":
            # Toggle ship selection
            if self._selected_ship_for_upgrade is ship:
                self._selected_ship_for_upgrade = None
            else:
                self._selected_ship_for_upgrade = ship
            return
        from core.events import bus
        hb = self.game.home_base
        if not hb or not hb.spend_resource("credits", cost):
            bus.publish("notification",
                        msg=f"Need {cost} credits to upgrade!",
                        color=(220, 60, 60))
            return
        old_class  = ship.ship_class
        ship.ship_class  = new_class
        ship.custom_name = new_name
        ship._build_sprite()   # rebuild sprite with new class shape
        bus.publish("notification",
                    msg=f"Ship upgraded: {old_class} → {new_class} ({new_name})",
                    color=(60, 200, 80))
        self._selected_ship_for_upgrade = None

    def _purchase(self, uid: str):
        meta = self.game.meta_progression
        if not meta:
            return
        if meta:
            result = meta.purchase(uid)
            from core.events import bus
            if result["ok"]:
                bus.publish("notification",
                            msg=f"Upgraded: {result['upgrade']} Lv{result['level']}",
                            color=(60, 200, 80))
            else:
                bus.publish("notification",
                            msg=f"Cannot upgrade: {result['reason']}",
                            color=(220, 60, 60))

    def update(self, dt): pass

    def draw(self, surface):
        from progression.meta import META_UPGRADES
        surface.fill(DARK_BG)
        meta  = self.game.meta_progression
        fleet = self.game.player_fleet

        # Guard: if no game has been started yet, show a placeholder
        if meta is None:
            font = pygame.font.SysFont("monospace", 18)
            msg = font.render("Start a game first to access Upgrades.", True, TEXT_MUTED)
            surface.blit(msg, (SCREEN_WIDTH // 2 - msg.get_width() // 2,
                               SCREEN_HEIGHT // 2 - 30))
            back_rect = pygame.Rect(SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 + 10, 200, 36)
            pygame.draw.rect(surface, (15, 50, 25), back_rect, border_radius=4)
            pygame.draw.rect(surface, SUCCESS, back_rect, 2, border_radius=4)
            lbl = self._font.render("⌂  Back to Base", True, SUCCESS)
            surface.blit(lbl, (back_rect.centerx - lbl.get_width() // 2,
                                back_rect.centery - lbl.get_height() // 2))
            self._back_to_base_rect = back_rect
            return

        # ── Left third: ships list + class upgrade ────────────────────────────
        LEFT_W  = SCREEN_WIDTH // 3
        RIGHT_X = LEFT_W + 10

        pygame.draw.line(surface, BORDER, (LEFT_W, 0), (LEFT_W, SCREEN_HEIGHT))

        # Header
        header = self._font.render("SHIPS", True, ACCENT)
        surface.blit(header, (14, 14))

        self._ship_upgrade_btns = []
        ship_y = 40
        ships = list(fleet.ships) if fleet else []
        if not ships:
            surface.blit(self._font_sm.render("No ships in fleet.", True, TEXT_MUTED),
                         (14, ship_y))

        for ship in ships:
            row = pygame.Rect(8, ship_y, LEFT_W - 16, 56)
            is_sel = (ship is self._selected_ship_for_upgrade)
            pygame.draw.rect(surface, (25, 35, 55) if is_sel else PANEL_BG, row)
            pygame.draw.rect(surface, ACCENT if is_sel else BORDER, row, 1)

            name_s = self._font.render(
                f"{ship.custom_name[:16]}", True, TEXT_MAIN)
            surface.blit(name_s, (14, ship_y + 4))
            cls_s = self._font_sm.render(
                f"Class: {ship.ship_class}", True, TEXT_MUTED)
            surface.blit(cls_s, (14, ship_y + 20))

            # UPGRADE CLASS button
            up_btn = pygame.Rect(LEFT_W - 100, ship_y + 12, 90, 26)
            pygame.draw.rect(surface, (20, 40, 60), up_btn)
            pygame.draw.rect(surface, ACCENT, up_btn, 1)
            ub_lbl = self._font_sm.render("UPGRADE", True, ACCENT)
            surface.blit(ub_lbl, (up_btn.centerx - ub_lbl.get_width() // 2,
                                   up_btn.centery - ub_lbl.get_height() // 2))
            # Click on the row itself to select
            if is_sel:
                # Draw class upgrade options below
                opts = SHIP_CLASS_UPGRADES.get(ship.ship_class, [])
                oy = ship_y + 60
                for uid2, uname, ucost, uclass in opts:
                    hb2 = self.game.home_base
                    can = bool(hb2) and hb2.get_resource("credits") >= ucost
                    opt_rect = pygame.Rect(14, oy, LEFT_W - 24, 28)
                    pygame.draw.rect(surface, (20, 50, 20) if can else (40, 20, 20), opt_rect)
                    pygame.draw.rect(surface, SUCCESS if can else DANGER, opt_rect, 1)
                    opt_lbl = self._font_sm.render(
                        f"{uname}  ({uclass})  {ucost}cr",
                        True, SUCCESS if can else DANGER)
                    surface.blit(opt_lbl, (opt_rect.x + 6,
                                           opt_rect.centery - opt_lbl.get_height() // 2))
                    self._ship_upgrade_btns.append(
                        (ship, uclass, uname, ucost, opt_rect))
                    oy += 32
                ship_y = oy + 8
            else:
                # Up button selects the ship for upgrade
                self._ship_upgrade_btns.append(
                    (ship, "select", "", 0, up_btn))
                ship_y += 64

        # ── Right two-thirds: existing upgrade tree ───────────────────────────
        pts_surf = self._font.render(
            f"UPGRADE TREE   Points: {meta.progression_points if meta else 0}",
            True, ACCENT)
        surface.blit(pts_surf, (RIGHT_X, 14))

        from progression.meta import CATEGORY_COLORS
        self._btn_rects = []
        bw   = SCREEN_WIDTH - RIGHT_X - 20
        bh   = 52
        # Clamp scroll so we never scroll past the last item
        total_h   = len(META_UPGRADES) * (bh + 4)
        list_area_h = SCREEN_HEIGHT - 60 - 50   # header area + button area
        max_scroll  = max(0, total_h - list_area_h)
        self._scroll = min(self._scroll, max_scroll)

        # Clip drawing to the list area so scrolled items don't show outside
        clip_rect = pygame.Rect(RIGHT_X, 46, bw + 20, list_area_h)
        old_clip  = surface.get_clip()
        surface.set_clip(clip_rect)

        by = 46 - self._scroll
        for i, (uid, name, desc, cost, max_lvl, key, val, category, icon) in enumerate(META_UPGRADES):
            current = meta.upgrade_levels.get(uid, 0) if meta else 0
            ok, reason = meta.can_purchase(uid) if meta else (False, "No meta")

            # Skip rows fully above or below the visible area
            if by + bh < 46 or by > SCREEN_HEIGHT - 50:
                by += bh + 4
                continue

            rect = pygame.Rect(RIGHT_X, by, bw, bh)
            bg   = (20, 40, 20) if ok else PANEL_BG
            sel  = (i == self._sel)
            if sel:
                bg = (30, 60, 90)
            pygame.draw.rect(surface, bg, rect)
            cat_col = CATEGORY_COLORS.get(category, BORDER)
            pygame.draw.rect(surface, cat_col if sel else BORDER, rect, 1)

            # Category colour bar on left edge
            pygame.draw.rect(surface, cat_col, (rect.x, rect.y, 3, bh))

            # Level pips
            for lvl in range(max_lvl):
                pip_col = SUCCESS if lvl < current else (40, 40, 40)
                pygame.draw.rect(surface, pip_col,
                                 (rect.x + 10 + lvl * 14, rect.y + 6, 10, 6))

            # Icon + name
            try:
                icon_s = self._font.render(icon, True, cat_col)
                surface.blit(icon_s, (rect.x + 8, rect.y + 16))
                n_surf = self._font.render(name, True, TEXT_MAIN)
                surface.blit(n_surf, (rect.x + 28, rect.y + 18))
            except Exception:
                n_surf = self._font.render(name, True, TEXT_MAIN)
                surface.blit(n_surf, (rect.x + 10, rect.y + 18))

            d_surf = self._font_sm.render(desc, True, TEXT_MUTED)
            surface.blit(d_surf, (rect.x + 10, rect.y + 34))

            cost_str = f"Cost: {cost}pt" if ok else f"{reason}"
            c_col = SUCCESS if ok else DANGER
            cs = self._font_sm.render(cost_str, True, c_col)
            surface.blit(cs, (rect.right - cs.get_width() - 10, rect.y + 18))

            # Store rect at its ACTUAL screen position (for click detection)
            self._btn_rects.append((uid, rect))
            by += bh + 4

        surface.set_clip(old_clip)

        # Scroll indicator bar (right edge of list area)
        if max_scroll > 0:
            bar_h     = int(list_area_h * list_area_h / total_h)
            bar_y     = 46 + int(self._scroll / max_scroll * (list_area_h - bar_h))
            pygame.draw.rect(surface, (40, 40, 60),
                             (RIGHT_X + bw + 4, 46, 6, list_area_h))
            pygame.draw.rect(surface, ACCENT,
                             (RIGHT_X + bw + 4, bar_y, 6, bar_h))
            # Scroll hint
            hint_s = self._font_sm.render("↕ scroll", True, TEXT_MUTED)
            surface.blit(hint_s, (RIGHT_X + bw + 2, 30))

        # ── Back to Base button ───────────────────────────────────────────────
        back_rect = pygame.Rect(SCREEN_WIDTH - 180, SCREEN_HEIGHT - 46, 170, 36)
        mx_m, my_m = pygame.mouse.get_pos()
        hover_back = back_rect.collidepoint(mx_m, my_m)
        pygame.draw.rect(surface, (15, 50, 25) if hover_back else PANEL_BG, back_rect,
                         border_radius=4)
        pygame.draw.rect(surface, SUCCESS, back_rect, 2, border_radius=4)
        bb_lbl = self._font.render("⌂  Back to Base", True, SUCCESS)
        surface.blit(bb_lbl, (back_rect.centerx - bb_lbl.get_width() // 2,
                               back_rect.centery - bb_lbl.get_height() // 2))
        self._back_to_base_rect = back_rect

        # ESC hint
        esc_s = self._font_sm.render("ESC or click button above = back to base",
                                      True, TEXT_MUTED)
        surface.blit(esc_s, (RIGHT_X, SCREEN_HEIGHT - 20))


# ── Accessibility Settings ────────────────────────────────────────────────────

class SettingsMenu:
    def __init__(self, game):
        self.game = game
        pygame.font.init()
        self._font = pygame.font.SysFont("monospace", 16)
        self._font_sm = pygame.font.SysFont("monospace", 13)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.game.change_state(State.MAIN_MENU)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if hasattr(self, "_cb_rect") and self._cb_rect.collidepoint(event.pos):
                self.game.colorblind = not self.game.colorblind
            if hasattr(self, "_spd_left") and self._spd_left.collidepoint(event.pos):
                self.game.combat_speed = max(0.5, round(self.game.combat_speed - 0.1, 1))
            if hasattr(self, "_spd_right") and self._spd_right.collidepoint(event.pos):
                self.game.combat_speed = min(2.0, round(self.game.combat_speed + 0.1, 1))
            if hasattr(self, "_font_s") and self._font_s.collidepoint(event.pos):
                self.game.font_size = "S"
            if hasattr(self, "_font_m") and self._font_m.collidepoint(event.pos):
                self.game.font_size = "M"
            if hasattr(self, "_font_l") and self._font_l.collidepoint(event.pos):
                self.game.font_size = "L"

    def update(self, dt): pass

    def draw(self, surface):
        surface.fill(DARK_BG)
        title = self._font.render("ACCESSIBILITY SETTINGS", True, ACCENT)
        surface.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 30))
        y = 90

        # Combat speed
        surface.blit(self._font.render("Combat Speed:", True, TEXT_MAIN), (200, y))
        lrect = pygame.Rect(450, y - 2, 30, 26)
        rrect = pygame.Rect(530, y - 2, 30, 26)
        _draw_button(surface, lrect, "<", self._font_sm)
        _draw_button(surface, rrect, ">", self._font_sm)
        sp_txt = self._font.render(f"{self.game.combat_speed:.1f}x", True, ACCENT)
        surface.blit(sp_txt, (486, y))
        self._spd_left, self._spd_right = lrect, rrect
        y += 50

        # Colorblind mode
        surface.blit(self._font.render("Colorblind Mode:", True, TEXT_MAIN), (200, y))
        cb_rect = pygame.Rect(450, y - 2, 80, 26)
        pygame.draw.rect(surface, PANEL_BG, cb_rect)
        pygame.draw.rect(surface, BORDER, cb_rect, 1)
        cb_lbl = "ON" if self.game.colorblind else "OFF"
        cb_col = SUCCESS if self.game.colorblind else TEXT_MUTED
        ct = self._font_sm.render(cb_lbl, True, cb_col)
        surface.blit(ct, (cb_rect.centerx - ct.get_width() // 2,
                           cb_rect.centery - ct.get_height() // 2))
        self._cb_rect = cb_rect
        y += 50

        # Font size
        surface.blit(self._font.render("Font Size:", True, TEXT_MAIN), (200, y))
        for i, sz in enumerate(["S", "M", "L"]):
            r = pygame.Rect(450 + i * 50, y - 2, 40, 26)
            sel = (self.game.font_size == sz)
            pygame.draw.rect(surface, (30, 60, 90) if sel else PANEL_BG, r)
            pygame.draw.rect(surface, ACCENT if sel else BORDER, r, 1)
            st = self._font_sm.render(sz, True, TEXT_MAIN)
            surface.blit(st, (r.centerx - st.get_width() // 2,
                               r.centery - st.get_height() // 2))
            if sz == "S": self._font_s = r
            elif sz == "M": self._font_m = r
            else: self._font_l = r


# ── Photo Mode ────────────────────────────────────────────────────────────────

class PhotoMode:
    FILTERS = ["none", "vintage", "noir", "neon"]

    def __init__(self):
        self._filter_idx = 0
        pygame.font.init()
        self._font = pygame.font.SysFont("monospace", 14)
        self.active = False

    def toggle(self):
        self.active = not self.active

    def handle_event(self, event):
        if not self.active:
            return None
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_f:
                self._filter_idx = (self._filter_idx + 1) % len(self.FILTERS)
            if event.key == pygame.K_p:
                self._take_screenshot()
            if event.key == pygame.K_ESCAPE:
                self.active = False
        return None

    def apply_filter(self, surface: pygame.Surface) -> pygame.Surface:
        filt = self.FILTERS[self._filter_idx]
        if filt == "none":
            return surface
        result = surface.copy()
        if filt == "vintage":
            ov = pygame.Surface(result.get_size(), pygame.SRCALPHA)
            ov.fill((60, 40, 0, 60))
            result.blit(ov, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        elif filt == "noir":
            # desaturate via overlay
            ov = pygame.Surface(result.get_size(), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 80))
            result.blit(ov, (0, 0))
        elif filt == "neon":
            ov = pygame.Surface(result.get_size(), pygame.SRCALPHA)
            ov.fill((0, 40, 80, 40))
            result.blit(ov, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        return result

    def draw_overlay(self, surface: pygame.Surface) -> None:
        if not self.active:
            return
        lbl = self._font.render(
            f"PHOTO MODE  [F] Filter: {self.FILTERS[self._filter_idx].upper()}"
            f"  [P] Capture  [ESC] Exit",
            True, (255, 255, 100))
        surface.blit(lbl, (10, SCREEN_HEIGHT - 28))

    def _take_screenshot(self) -> None:
        import os
        import time
        os.makedirs("screenshots", exist_ok=True)
        fname = f"screenshots/space_pirates_{int(time.time())}.png"
        pygame.image.save(pygame.display.get_surface(), fname)
        from core.events import bus
        bus.publish("notification",
                    msg=f"Screenshot saved: {fname}", color=(200, 200, 60))


# ── Compendium ────────────────────────────────────────────────────────────────

class CompendiumScreen:
    """Full reference browser: Ships / Weapons / Crew / Drones / Tips.

    Accessible from the main menu.  Read-only — no game state is modified.
    Tabs across the top; left side-list; right detail panel.
    """

    TABS = ["Ships", "Weapons", "Crew", "Drones", "Tips"]

    TIPS = [
        ("Board, don't just shoot",
         "Boarding a weakened enemy gives you their ship, crew, cargo, AND +2 upgrade "
         "points.  Always try to board before you finish them off."),
        ("Scout drones extend your radar",
         "A Scout drone orbits at 160 px and adds +400 px to your minimap radar range.  "
         "Launch one every fight — it also deals 4 dmg to any enemy it passes through."),
        ("Carrier bay = free allies",
         "Load fighters into your carrier's bay before entering combat.  Each time the "
         "carrier loses 25% hull, a docked ship launches automatically as an allied escort."),
        ("EMP drones win fights",
         "Fire an EMP drone at a shielded enemy — it rushes in, disables their shield, "
         "and slows them to 50% speed for 3 seconds.  Then board them."),
        ("Raider countdown = prep time",
         "When the 5-minute raider warning appears in the base corner, use the time to "
         "repair your ship, load the carrier bay, and launch scout drones."),
        ("Kill multiplier stacks fast",
         "Every enemy destroyed in a sector is worth 100 credits at the victory screen.  "
         "A full wave of 5 enemies = 500cr on top of normal loot."),
        ("Repair drones save runs",
         "A Repair drone heals you 4 HP/s for 25 seconds = 100 HP total.  Launch one "
         "at the start of every sector before shots are fired."),
        ("Asteroids give free metal",
         "Fly through asteroid fields to collect metal — no cost, no fight.  Large "
         "asteroids show a pickaxe icon when uncollected."),
        ("Space mines hit enemies too",
         "You won't trigger mines because you know where they are.  Your enemy AI does "
         "not.  Lure enemies over mine clusters for free 30 HP bursts."),
        ("Upgrade points from captures",
         "Every ship you capture (any choice — keep, return, strip, crew) gives +2 "
         "upgrade points.  Boarding is the fastest way to unlock the tech tree."),
        ("Drone Bay Upgrade in the meta tree",
         "The 'Drone Bay Upgrade' meta node adds +2 drone slots to all ships per level "
         "(5 levels = +10 slots).  Prioritise it once you have a corvette or carrier."),
        ("Origin: Rogue Engineer = +1 drone slot",
         "Choosing Rogue Engineer at new-game adds +1 drone slot at the start of every "
         "combat, even on ships that normally have 0 slots."),
        ("Shield drone stacks above your cap",
         "Shield drones top up your shield beyond max_shield while active.  Combined "
         "with meta shield upgrades this can make early sectors trivial."),
        ("Check the Trading Post relations",
         "Gift credits to nations in the Trading tab to raise relations.  At +50 "
         "relation you get a 20% discount on everything they sell."),
        ("Side quests send ships automatically",
         "In the Crew & Quests tab, assign a fleet ship to a side quest.  It returns "
         "with credits, metal, and XP — no input required while you're elsewhere."),
    ]

    def __init__(self, game):
        self.game         = game
        self._tab         = 0           # active tab index
        self._sel         = 0           # selected row in side list
        self._scroll      = 0           # pixel scroll offset in detail panel
        self._list_scroll = 0           # row scroll offset in side list
        self._ships_data: list[dict]   = []
        self._weapons_data: list[dict] = []
        self._crew_data: list[dict]    = []
        self._sprite_cache: dict[str, pygame.Surface] = {}
        pygame.font.init()
        self._font_lg = pygame.font.SysFont("monospace", 20, bold=True)
        self._font    = pygame.font.SysFont("monospace", 14)
        self._font_sm = pygame.font.SysFont("monospace", 11)
        self._font_xs = pygame.font.SysFont("monospace", 10)
        self._tab_rects: list[pygame.Rect] = []
        self._list_rects: list[pygame.Rect] = []
        self._esc_rect: pygame.Rect | None = None

    # ── Data loading (lazy) ───────────────────────────────────────────────────
    def _ensure_data(self) -> None:
        if not self._ships_data:
            import json, os
            try:
                with open("data/ships.json")   as f: self._ships_data   = json.load(f)
                with open("data/weapons.json") as f: self._weapons_data = json.load(f)
                with open("data/crew.json")    as f: self._crew_data    = json.load(f)
            except Exception:
                pass

    def _ship_sprite(self, sdata: dict) -> pygame.Surface:
        sid = sdata["id"]
        if sid not in self._sprite_cache:
            from entities.ship import Ship as _Ship
            try:
                s    = _Ship(sdata)
                w, h = s._sprite_dims()
                sc   = 4
                big  = pygame.Surface((w * sc, h * sc), pygame.SRCALPHA)
                tmp  = pygame.Surface((w, h), pygame.SRCALPHA)
                s._draw_ship_shape(tmp, s.color_scheme, w, h)
                pygame.transform.scale(tmp, (w * sc, h * sc), big)
                self._sprite_cache[sid] = big
            except Exception:
                fb = pygame.Surface((80, 40), pygame.SRCALPHA)
                pygame.draw.polygon(fb, (100, 120, 180),
                                    [(76, 20), (8, 4), (4, 20), (8, 36)])
                self._sprite_cache[sid] = fb
        return self._sprite_cache[sid]

    # ── Active list ───────────────────────────────────────────────────────────
    def _active_list(self) -> list:
        self._ensure_data()
        tab = self.TABS[self._tab]
        if tab == "Ships":   return self._ships_data
        if tab == "Weapons": return self._weapons_data
        if tab == "Crew":    return self._crew_data
        if tab == "Drones":
            from combat.drones import DRONE_TYPES
            return list(DRONE_TYPES.items())  # [(dtype, spec_dict), ...]
        if tab == "Tips":    return self.TIPS
        return []

    def _item_label(self, item, tab: str) -> str:
        if tab == "Drones": return item[1]["label"]
        if tab == "Tips":   return item[0][:40]
        return item.get("name", "?")

    def _item_rarity(self, item, tab: str) -> str:
        if tab in ("Drones", "Tips"): return "common"
        return item.get("rarity", "common")

    # ── Events ────────────────────────────────────────────────────────────────
    def handle_event(self, event) -> str | None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.game.change_state(State.MAIN_MENU)
                return "close"
            if event.key in (pygame.K_UP, pygame.K_w):
                self._sel = max(0, self._sel - 1)
                self._scroll = 0
            if event.key in (pygame.K_DOWN, pygame.K_s):
                items = self._active_list()
                self._sel = min(len(items) - 1, self._sel + 1)
                self._scroll = 0
            if event.key in (pygame.K_LEFT, pygame.K_a):
                self._tab = (self._tab - 1) % len(self.TABS)
                self._sel = 0; self._scroll = 0; self._list_scroll = 0
            if event.key in (pygame.K_RIGHT, pygame.K_d):
                self._tab = (self._tab + 1) % len(self.TABS)
                self._sel = 0; self._scroll = 0; self._list_scroll = 0
            if event.key == pygame.K_PAGEDOWN:
                self._scroll += 120
            if event.key == pygame.K_PAGEUP:
                self._scroll = max(0, self._scroll - 120)

        if event.type == pygame.MOUSEWHEEL:
            self._scroll = max(0, self._scroll - event.y * 30)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            if self._esc_rect and self._esc_rect.collidepoint(mx, my):
                self.game.change_state(State.MAIN_MENU)
                return "close"
            for ti, tr in enumerate(self._tab_rects):
                if tr.collidepoint(mx, my):
                    self._tab = ti
                    self._sel = 0; self._scroll = 0; self._list_scroll = 0
            for ri, lr in enumerate(self._list_rects):
                if lr.collidepoint(mx, my):
                    self._sel = self._list_scroll + ri
                    self._scroll = 0
        return None

    def update(self, dt): pass

    # ── Draw ──────────────────────────────────────────────────────────────────
    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(DARK_BG)
        sw, sh = surface.get_size()

        # ESC
        self._esc_rect = _draw_esc_button(surface, self._font_sm)

        # Title
        tit = self._font_lg.render("COMPENDIUM", True, ACCENT)
        surface.blit(tit, (sw // 2 - tit.get_width() // 2, 10))

        # ── Tab bar ───────────────────────────────────────────────────────────
        tab_y   = 42
        tab_h   = 28
        tab_gap = 6
        tab_total_w = sum(self._font.size(t)[0] + 28 for t in self.TABS) + \
                      tab_gap * (len(self.TABS) - 1)
        tx = sw // 2 - tab_total_w // 2
        self._tab_rects = []
        TAB_COLORS = [(220,80,80),(255,160,40),(80,200,120),(255,140,60),(80,180,255)]
        for i, tab in enumerate(self.TABS):
            tw  = self._font.size(tab)[0] + 28
            tr  = pygame.Rect(tx, tab_y, tw, tab_h)
            sel = (i == self._tab)
            col = TAB_COLORS[i % len(TAB_COLORS)]
            pygame.draw.rect(surface, (25, 32, 52) if sel else PANEL_BG, tr, border_radius=4)
            pygame.draw.rect(surface, col if sel else BORDER, tr,
                             2 if sel else 1, border_radius=4)
            label_s = self._font.render(tab, True, col if sel else TEXT_MUTED)
            surface.blit(label_s, (tr.centerx - label_s.get_width() // 2,
                                   tr.centery - label_s.get_height() // 2))
            self._tab_rects.append(tr)
            tx += tw + tab_gap

        CONTENT_Y = tab_y + tab_h + 8
        LIST_W    = 220
        DETAIL_X  = LIST_W + 12
        DETAIL_W  = sw - DETAIL_X - 8

        # Divider
        pygame.draw.line(surface, BORDER, (LIST_W, CONTENT_Y), (LIST_W, sh - 10))

        # ── Side list ─────────────────────────────────────────────────────────
        items    = self._active_list()
        tab_name = self.TABS[self._tab]
        vis_rows = (sh - CONTENT_Y - 10) // 26
        self._list_scroll = max(0, min(self._list_scroll,
                                       max(0, len(items) - vis_rows)))
        # Scroll selection into view
        if self._sel < self._list_scroll:
            self._list_scroll = self._sel
        elif self._sel >= self._list_scroll + vis_rows:
            self._list_scroll = self._sel - vis_rows + 1

        self._list_rects = []
        for ri in range(vis_rows):
            idx = self._list_scroll + ri
            if idx >= len(items):
                break
            item   = items[idx]
            ly     = CONTENT_Y + ri * 26
            lrect  = pygame.Rect(4, ly, LIST_W - 6, 24)
            sel    = (idx == self._sel)
            rar    = self._item_rarity(item, tab_name)
            rcol   = _RARITY_COL.get(rar, (160, 160, 180))
            bg     = (22, 34, 54) if sel else PANEL_BG
            pygame.draw.rect(surface, bg, lrect, border_radius=3)
            pygame.draw.rect(surface, rcol if sel else BORDER, lrect,
                             1, border_radius=3)
            lbl    = self._item_label(item, tab_name)
            lt     = self._font_sm.render(lbl[:26], True, rcol if sel else TEXT_MAIN)
            surface.blit(lt, (lrect.x + 6,
                               lrect.centery - lt.get_height() // 2))
            self._list_rects.append(lrect)

        # Scroll indicator
        if len(items) > vis_rows:
            total_h = sh - CONTENT_Y - 10
            frac_s  = self._list_scroll / max(len(items), 1)
            frac_e  = min(1.0, (self._list_scroll + vis_rows) / max(len(items), 1))
            bar_y   = CONTENT_Y + int(total_h * frac_s)
            bar_h   = max(8, int(total_h * (frac_e - frac_s)))
            pygame.draw.rect(surface, (60, 60, 80),
                             (LIST_W - 4, CONTENT_Y, 3, total_h))
            pygame.draw.rect(surface, (120, 140, 200),
                             (LIST_W - 4, bar_y, 3, bar_h))

        # ── Detail panel ──────────────────────────────────────────────────────
        if not items or self._sel >= len(items):
            return
        item = items[self._sel]

        # Clip detail area
        clip = pygame.Rect(DETAIL_X, CONTENT_Y, DETAIL_W, sh - CONTENT_Y - 4)
        surface.set_clip(clip)

        dy = CONTENT_Y - self._scroll   # running y, scrolled

        if tab_name == "Ships":
            dy = self._draw_ship_detail(surface, item, DETAIL_X, dy, DETAIL_W, sh)
        elif tab_name == "Weapons":
            dy = self._draw_weapon_detail(surface, item, DETAIL_X, dy, DETAIL_W)
        elif tab_name == "Crew":
            dy = self._draw_crew_detail(surface, item, DETAIL_X, dy, DETAIL_W)
        elif tab_name == "Drones":
            dy = self._draw_drone_detail(surface, item, DETAIL_X, dy, DETAIL_W)
        elif tab_name == "Tips":
            dy = self._draw_tip_detail(surface, item, DETAIL_X, dy, DETAIL_W)

        surface.set_clip(None)

        # Scroll hint
        if dy - (CONTENT_Y - self._scroll) > (sh - CONTENT_Y):
            sc_hint = self._font_xs.render(
                "↓ scroll  (mouse wheel / Page Down)", True, (80, 80, 110))
            surface.blit(sc_hint, (DETAIL_X + 4, sh - 16))

    # ── Detail renderers ──────────────────────────────────────────────────────

    def _stat_bar(self, surface, x, y, label, val, max_val, col, w=220):
        frac = min(1.0, val / max(max_val, 1))
        lt   = self._font_xs.render(f"{label:<9}{val}", True, TEXT_MUTED)
        surface.blit(lt, (x, y))
        pygame.draw.rect(surface, (30, 30, 40), (x, y + 13, w, 5))
        pygame.draw.rect(surface, col, (x, y + 13, int(w * frac), 5))
        return y + 22

    def _section(self, surface, x, y, heading):
        hs = self._font.render(heading, True, ACCENT)
        surface.blit(hs, (x, y))
        pygame.draw.line(surface, (40, 50, 80),
                         (x, y + hs.get_height() + 2),
                         (x + 400, y + hs.get_height() + 2))
        return y + hs.get_height() + 8

    def _wrap_text(self, surface, text, x, y, max_w, col=None, font=None):
        font = font or self._font_sm
        col  = col  or TEXT_MUTED
        words = text.split()
        line, lines = "", []
        for word in words:
            test = (line + " " + word).strip()
            if font.size(test)[0] <= max_w:
                line = test
            else:
                lines.append(line); line = word
        lines.append(line)
        for ln in lines:
            ls = font.render(ln, True, col)
            surface.blit(ls, (x, y))
            y += font.get_height() + 2
        return y + 4

    # ── Ship detail ───────────────────────────────────────────────────────────
    def _draw_ship_detail(self, surface, sdata, x, y, w, sh) -> int:
        rar  = sdata.get("rarity", "common")
        rcol = _RARITY_COL.get(rar, (160, 160, 180))

        # Name + class badge
        ns = self._font_lg.render(sdata["name"], True, rcol)
        surface.blit(ns, (x, y)); y += ns.get_height() + 2
        cls_s = self._font_sm.render(
            f"{sdata['class'].replace('_',' ').title()}  •  {rar.upper()}  •  "
            f"{sdata.get('hull_type','').upper()} hull  •  "
            f"{'STARTER' if sdata.get('starter') else ''}  "
            f"Price: {sdata.get('price',0):,}cr",
            True, rcol)
        surface.blit(cls_s, (x, y)); y += cls_s.get_height() + 6

        # Sprite preview
        sprite = self._ship_sprite(sdata)
        sw_, sh_ = sprite.get_size()
        surface.blit(sprite, (x, y)); y += sh_ + 8

        # Stat bars
        y = self._stat_bar(surface, x, y, "Hull",    sdata["max_hull"],         2500, (100,200,100))
        y = self._stat_bar(surface, x, y, "Shield",  sdata["max_shield"],       1200, (80,160,255))
        y = self._stat_bar(surface, x, y, "Speed",   sdata["base_speed"],        260, (255,200,60))
        y = self._stat_bar(surface, x, y, "Evasion", int(sdata.get("base_evasion",0)*100), 40, (200,120,255))
        y = self._stat_bar(surface, x, y, "Crew",    sdata.get("crew_slots",0),   35, (200,160,80))
        y = self._stat_bar(surface, x, y, "Fuel",    sdata.get("fuel_capacity",0),400,(80,200,200))
        y = self._stat_bar(surface, x, y, "Drones",  sdata.get("drone_slots",0),  10, (255,140,60))
        y = self._stat_bar(surface, x, y, "Bay",     sdata.get("bay_slots",0),     5, (255,220,80))
        y += 4

        # Hardpoints summary
        hp = sdata.get("hardpoint_slots", {})
        hp_s = self._font_sm.render(
            f"Hardpoints  Small:{hp.get('small',0)}  "
            f"Medium:{hp.get('medium',0)}  Large:{hp.get('large',0)}",
            True, TEXT_MUTED)
        surface.blit(hp_s, (x, y)); y += hp_s.get_height() + 8

        # Description
        y = self._section(surface, x, y, "Description")
        y = self._wrap_text(surface, sdata.get("description",""), x, y, w - 10)

        # Lore
        lore = sdata.get("lore","")
        if lore:
            y = self._section(surface, x, y, "Lore")
            y = self._wrap_text(surface, f'"{lore}"', x, y, w - 10,
                                col=(140,140,180))

        # Quirks
        quirks = sdata.get("quirks", [])
        if quirks:
            y = self._section(surface, x, y, "Quirks")
            for q in quirks:
                qs = self._font_sm.render(f"• {q}", True, (200,200,100))
                surface.blit(qs, (x, y)); y += qs.get_height() + 3

        # Specialization paths
        paths = sdata.get("specialization_paths", {})
        if paths:
            y = self._section(surface, x, y, "Specialization Paths")
            for key, val in paths.items():
                ps = self._font_sm.render(
                    f"  Path {key}: {val.replace('_',' ').title()}", True, (100,180,255))
                surface.blit(ps, (x, y)); y += ps.get_height() + 3

        return y + 10

    # ── Weapon detail ─────────────────────────────────────────────────────────
    def _draw_weapon_detail(self, surface, wdata, x, y, w) -> int:
        rar  = wdata.get("rarity","common")
        rcol = _RARITY_COL.get(rar,(160,160,180))

        ns = self._font_lg.render(wdata["name"], True, rcol)
        surface.blit(ns, (x, y)); y += ns.get_height() + 2

        meta = self._font_sm.render(
            f"{wdata.get('type','').upper()}  •  {rar.upper()}  •  "
            f"Ammo: {wdata.get('ammo_type','?')}  •  "
            f"Price: {wdata.get('price',0):,}cr",
            True, rcol)
        surface.blit(meta, (x, y)); y += meta.get_height() + 10

        # Visual: simple weapon icon
        wtype = wdata.get("type","laser")
        icon_col = {
            "laser":   (80, 200, 255),
            "missile": (255, 140, 60),
            "railgun": (180, 120, 255),
            "emp":     (120, 80, 255),
            "flak":    (200, 200, 80),
        }.get(wtype, (160,160,180))
        # Draw a simple weapon silhouette
        gun_pts = [(x+60,y+12),(x,y+8),(x,y+16),(x+50,y+16),(x+50,y+18),(x+60,y+14)]
        pygame.draw.polygon(surface, icon_col, gun_pts)
        # Muzzle flash
        pygame.draw.circle(surface, (255,240,180), (x+62, y+13), 4)
        y += 30

        # Stat bars
        y = self._stat_bar(surface, x, y, "Damage",   wdata.get("base_damage",0),   500, (220,80,80))
        y = self._stat_bar(surface, x, y, "Fire rate", int(wdata.get("fire_rate",1)*10), 40, (255,160,40))
        y = self._stat_bar(surface, x, y, "Range",    wdata.get("range",0),          800, (80,200,200))
        y += 4

        # Description
        y = self._section(surface, x, y, "Description")
        y = self._wrap_text(surface, wdata.get("description",""), x, y, w - 10)

        # Status effect
        fx = wdata.get("status_effect")
        if fx:
            y = self._section(surface, x, y, "Status Effect")
            fxs = self._font_sm.render(f"• {fx}", True, (255,180,80))
            surface.blit(fxs, (x, y)); y += fxs.get_height() + 6

        # Upgrade paths
        paths = wdata.get("upgrade_paths", {})
        if paths:
            y = self._section(surface, x, y, "Upgrade Paths")
            for key, pdata in paths.items():
                ps = self._font_sm.render(
                    f"  Path {key}: {pdata['name'].replace('_',' ').title()}",
                    True, (100,180,255))
                surface.blit(ps, (x, y)); y += ps.get_height() + 2
                pd = self._font_xs.render(f"     {pdata['description']}", True, TEXT_MUTED)
                surface.blit(pd, (x, y)); y += pd.get_height() + 4

        xp = wdata.get("xp_to_specialize", 0)
        if xp:
            xs = self._font_xs.render(f"XP to specialize: {xp}", True, TEXT_MUTED)
            surface.blit(xs, (x, y)); y += xs.get_height() + 6

        return y + 10

    # ── Crew detail ───────────────────────────────────────────────────────────
    def _draw_crew_detail(self, surface, cdata, x, y, w) -> int:
        rar  = cdata.get("rarity","common")
        rcol = _RARITY_COL.get(rar,(160,160,180))

        ns = self._font_lg.render(cdata["name"], True, rcol)
        surface.blit(ns, (x, y)); y += ns.get_height() + 2

        meta = self._font_sm.render(
            f"Role: {cdata.get('role','?').title()}  •  {rar.upper()}  •  "
            f"Price: {cdata.get('price',0):,}cr",
            True, rcol)
        surface.blit(meta, (x, y)); y += meta.get_height() + 10

        # Crew portrait — a stylised silhouette
        portrait_x, portrait_y = x, y
        role_col = {
            "pilot":    (80, 160, 255),
            "gunner":   (220, 80, 80),
            "engineer": (255, 160, 40),
            "combat":   (200, 60, 60),
            "mechanic": (80, 200, 120),
        }.get(cdata.get("role",""), (160,160,180))
        # Head + torso silhouette
        pygame.draw.circle(surface, role_col, (portrait_x+20, portrait_y+12), 10)
        pygame.draw.rect(surface, role_col,
                         pygame.Rect(portrait_x+10, portrait_y+24, 20, 18))
        y += 50

        # Stat bars
        stats = cdata.get("stats", {})
        stat_defs = [
            ("Piloting",    "piloting",    38, (80,160,255)),
            ("Gunnery",     "gunnery",     38, (220,80,80)),
            ("Engineering", "engineering", 38, (255,160,40)),
            ("Combat",      "combat",      38, (200,60,60)),
            ("Repair",      "repair",      38, (80,200,120)),
        ]
        for label, key, max_v, col in stat_defs:
            y = self._stat_bar(surface, x, y, label, stats.get(key,0), max_v, col)
        y += 4

        # Description
        y = self._section(surface, x, y, "Description")
        y = self._wrap_text(surface, cdata.get("description",""), x, y, w - 10)

        # Abilities
        abilities = cdata.get("abilities", [])
        if abilities:
            y = self._section(surface, x, y, "Abilities")
            for ab in abilities:
                if isinstance(ab, dict):
                    abs_ = self._font_sm.render(
                        f"• {ab.get('name','?')}: {ab.get('description','')[:60]}",
                        True, (200,200,100))
                else:
                    abs_ = self._font_sm.render(f"• {ab}", True, (200,200,100))
                surface.blit(abs_, (x, y)); y += abs_.get_height() + 3

        # Specialization paths
        paths = cdata.get("specialization_paths", {})
        if paths:
            y = self._section(surface, x, y, "Specialization Paths")
            for key, val in paths.items():
                ps = self._font_sm.render(
                    f"  Path {key}: {val.replace('_',' ').title()}" if isinstance(val, str)
                    else f"  Path {key}: {val}",
                    True, (100,180,255))
                surface.blit(ps, (x, y)); y += ps.get_height() + 3

        return y + 10

    # ── Drone detail ──────────────────────────────────────────────────────────
    def _draw_drone_detail(self, surface, item, x, y, w) -> int:
        dtype, spec = item
        col = spec["color"]

        ns = self._font_lg.render(f"{spec['label']} Drone", True, col)
        surface.blit(ns, (x, y)); y += ns.get_height() + 2

        cost_s = self._font_sm.render(
            f"Cost: {spec.get('cost',0)}cr  •  Duration: {spec.get('duration',0):.0f}s  "
            f"•  Speed: {spec.get('speed',0)} px/s",
            True, col)
        surface.blit(cost_s, (x, y)); y += cost_s.get_height() + 10

        # Draw drone diamond icon (large)
        import math as _m
        sz = 18
        dx_, dy_ = x + 30, y + 20
        pts = [(dx_, dy_-sz),(dx_+sz,dy_),(dx_,dy_+sz),(dx_-sz,dy_)]
        pygame.draw.polygon(surface, col, pts)
        pygame.draw.circle(surface, (255,255,255), (dx_,dy_), max(1,sz//3))
        y += sz*2 + 12

        # Stat bars where applicable
        damage  = spec.get("damage", 0)
        heal    = spec.get("heal_rate", 0)
        shield  = spec.get("shield_bonus", 0)
        radar   = spec.get("radar_bonus", 0)
        if damage:
            y = self._stat_bar(surface, x, y, "Damage",    damage,    50, (220,80,80))
        if heal:
            y = self._stat_bar(surface, x, y, "Heal/s",    int(heal*10), 80, (80,200,120))
        if shield:
            y = self._stat_bar(surface, x, y, "Shield+",   shield,    50, (80,160,255))
        if radar:
            y = self._stat_bar(surface, x, y, "Radar+px",  radar,    800, (100,200,255))
        y += 4

        # Description
        y = self._section(surface, x, y, "What it does")
        y = self._wrap_text(surface, spec.get("desc",""), x, y, w - 10,
                            col=(200,200,200))

        # Fire CD / special fields
        fire_cd = spec.get("fire_cd")
        if fire_cd:
            fcd_s = self._font_sm.render(f"Fires every {fire_cd:.1f}s", True, TEXT_MUTED)
            surface.blit(fcd_s, (x, y)); y += fcd_s.get_height() + 4
        orbit = spec.get("orbit_r")
        if orbit:
            os_s = self._font_sm.render(f"Orbit radius: {orbit}px", True, TEXT_MUTED)
            surface.blit(os_s, (x, y)); y += os_s.get_height() + 4
        emp_slow = spec.get("emp_slow")
        if emp_slow:
            es = self._font_sm.render(
                f"EMP slow: {int(emp_slow*100)}% speed  "
                f"for {spec.get('emp_dur',0):.0f}s",
                True, (180,120,255))
            surface.blit(es, (x, y)); y += es.get_height() + 4

        # Which ships can use this drone
        y += 4
        y = self._section(surface, x, y, "Available on ships with drone_slots > 0")
        self._ensure_data()
        drone_ships = [s["name"] for s in self._ships_data if s.get("drone_slots",0) > 0]
        y = self._wrap_text(surface,
                            "  ".join(drone_ships) or "None",
                            x, y, w - 10, col=(160,200,160))
        return y + 10

    # ── Tip detail ────────────────────────────────────────────────────────────
    def _draw_tip_detail(self, surface, item, x, y, w) -> int:
        title, body = item
        ts = self._font_lg.render(title, True, (255,220,80))
        # Wrap title if long
        if self._font_lg.size(title)[0] > w - 10:
            ts = self._font.render(title, True, (255,220,80))
        surface.blit(ts, (x, y)); y += ts.get_height() + 8

        # Tip icon — lightbulb-ish
        pygame.draw.circle(surface, (255,220,80), (x+14, y+14), 12)
        pygame.draw.circle(surface, DARK_BG, (x+14, y+14), 8)
        pygame.draw.line(surface, (255,220,80), (x+10, y+26), (x+18, y+26), 2)
        pygame.draw.line(surface, (255,220,80), (x+14, y+26), (x+14, y+30), 2)
        y += 36

        y = self._wrap_text(surface, body, x, y, w - 10,
                            col=(220,220,220), font=self._font_sm)

        # Divider + tip number
        num_s = self._font_xs.render(
            f"Tip {self.TIPS.index(item)+1} of {len(self.TIPS)}", True, (60,60,90))
        surface.blit(num_s, (x, y)); y += num_s.get_height() + 6
        return y + 10


def register_all_menus(game) -> None:
    """Register all menu screens with the game state machine."""
    game.register_screen(State.MAIN_MENU,     MainMenuScreen(game))
    game.register_screen(State.ORIGIN_SELECT, OriginSelectScreen(game))
    game.register_screen(State.LOAD_SCREEN,   LoadScreen(game))
    game.register_screen(State.PAUSED,        PauseMenu(game))
    game.register_screen(State.UPGRADE_TREE,  UpgradeTreeMenu(game))
    game.register_screen("compendium_screen", CompendiumScreen(game))
