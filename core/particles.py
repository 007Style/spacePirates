"""core/particles.py — Lightweight particle system."""
from __future__ import annotations
import pygame
import random
import math


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life",
                 "color", "size", "gravity")

    def __init__(self, x, y, vx, vy, life, color, size=3, gravity=0.0):
        self.x        = float(x)
        self.y        = float(y)
        self.vx       = float(vx)
        self.vy       = float(vy)
        self.life     = float(life)
        self.max_life = float(life)
        self.color    = color
        self.size     = size
        self.gravity  = gravity

    @property
    def alive(self) -> bool:
        return self.life > 0

    def update(self, dt: float) -> None:
        self.x    += self.vx * dt
        self.y    += self.vy * dt
        self.vy   += self.gravity * dt
        self.life -= dt

    def draw(self, surface: pygame.Surface) -> None:
        alpha_ratio = max(0.0, self.life / self.max_life)
        r, g, b = self.color[:3]
        fade_color = (int(r * alpha_ratio), int(g * alpha_ratio), int(b * alpha_ratio))
        size = max(1, int(self.size * alpha_ratio))
        pygame.draw.circle(surface, fade_color, (int(self.x), int(self.y)), size)


class ParticleSystem:
    def __init__(self):
        self._particles: list[Particle] = []

    def emit_explosion(self, x: float, y: float, count: int = 24,
                       color: tuple = (255, 140, 40)) -> None:
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(40, 180)
            life  = random.uniform(0.4, 1.2)
            size  = random.randint(2, 6)
            self._particles.append(Particle(
                x, y,
                math.cos(angle) * speed,
                math.sin(angle) * speed,
                life, color, size, gravity=60,
            ))

    def emit_engine_trail(self, x: float, y: float,
                          angle_deg: float, color: tuple = (80, 160, 255)) -> None:
        for _ in range(3):
            spread = random.uniform(-20, 20)
            trail_angle = math.radians(angle_deg + 180 + spread)
            speed = random.uniform(20, 60)
            life  = random.uniform(0.15, 0.4)
            self._particles.append(Particle(
                x, y,
                math.cos(trail_angle) * speed,
                math.sin(trail_angle) * speed,
                life, color, size=2,
            ))

    def emit_hit_sparks(self, x: float, y: float,
                        color: tuple = (255, 255, 100), count: int = 8) -> None:
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(30, 100)
            life  = random.uniform(0.2, 0.5)
            self._particles.append(Particle(
                x, y,
                math.cos(angle) * speed,
                math.sin(angle) * speed,
                life, color, size=2,
            ))

    def emit_status_effect(self, x: float, y: float, effect: str) -> None:
        colors = {
            "burning":    (255, 100, 20),
            "emp":        (100, 200, 255),
            "hull_breach":(200, 200, 200),
            "slow":       (150, 60, 255),
        }
        color = colors.get(effect, (200, 200, 200))
        for _ in range(5):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(10, 40)
            life  = random.uniform(0.3, 0.8)
            self._particles.append(Particle(
                x + random.uniform(-10, 10),
                y + random.uniform(-10, 10),
                math.cos(angle) * speed,
                math.sin(angle) * speed,
                life, color, size=3,
            ))

    def update(self, dt: float) -> None:
        for p in self._particles:
            p.update(dt)
        self._particles = [p for p in self._particles if p.alive]

    def draw(self, surface: pygame.Surface) -> None:
        for p in self._particles:
            p.draw(surface)

    def clear(self) -> None:
        self._particles.clear()
