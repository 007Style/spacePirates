"""entities/projectile.py — Projectile fired by a weapon."""
from __future__ import annotations
import pygame
import math


class Projectile(pygame.sprite.Sprite):
    def __init__(
        self,
        x: float,
        y: float,
        angle_deg: float,
        speed: float,
        damage: float,
        owner,               # Ship reference
        color: tuple = (255, 220, 60),
        status_effect: str | None = None,
        size: int = 5,
        max_range: float = 400,
    ):
        super().__init__()
        self.x         = float(x)
        self.y         = float(y)
        self.speed     = speed
        self.damage    = damage
        self.owner     = owner
        self.status_effect = status_effect
        self.max_range = max_range
        self._dist     = 0.0

        rad = math.radians(angle_deg)
        self.vx = math.cos(rad) * speed
        self.vy = math.sin(rad) * speed

        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(self.image, color, (size // 2, size // 2), size // 2)
        self.rect  = self.image.get_rect(center=(int(x), int(y)))

    def update(self, dt: float) -> None:
        move = self.speed * dt
        self.x      += self.vx * dt
        self.y      += self.vy * dt
        self._dist  += move
        self.rect.center = (int(self.x), int(self.y))
        if self._dist >= self.max_range:
            self.kill()

    def to_dict(self) -> dict:
        return {
            "x": self.x, "y": self.y,
            "vx": self.vx, "vy": self.vy,
            "damage": self.damage,
            "status_effect": self.status_effect,
        }
