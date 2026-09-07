"""entities/drone.py — Drone class with AI behavior."""
from __future__ import annotations
import pygame
import math
from progression.rarity import rarity_system


class DroneAI:
    IDLE     = "idle"
    FOLLOW   = "follow"
    ATTACK   = "attack"
    DEFEND   = "defend"
    COLLECT  = "collect"


class Drone(pygame.sprite.Sprite):
    def __init__(self, data: dict, owner=None):
        super().__init__()
        self.id          = data["id"]
        self.name        = data["name"]
        self.drone_type  = data.get("drone_type", "combat")   # combat / utility / repair
        self.rarity      = data.get("rarity", "common")
        self.description = data.get("description", "")
        self.owner       = owner   # Ship reference

        mult = rarity_system.stat_multiplier(self.rarity)
        self.max_hp   = round(data.get("max_hp", 40) * mult)
        self.hp       = self.max_hp
        self.damage   = round(data.get("damage", 10) * mult)
        self.speed    = data.get("speed", 120)
        self.range    = data.get("range", 200)
        self.price    = data.get("price", 200)

        self.ai_state = DroneAI.FOLLOW
        self._fire_cd = 0.0
        self.fire_rate = data.get("fire_rate", 1.0)

        # Sprite
        size = 12
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        color = rarity_system.color(self.rarity)
        pygame.draw.polygon(self.image, color, [(size//2, 0), (size, size), (0, size)])
        self.rect  = self.image.get_rect()
        self.x     = 0.0
        self.y     = 0.0

    def update(self, dt: float, target=None) -> None:
        if self._fire_cd > 0:
            self._fire_cd -= dt

        if self.ai_state == DroneAI.FOLLOW and self.owner:
            self._move_toward(self.owner.x + 30, self.owner.y, dt)
        elif self.ai_state == DroneAI.ATTACK and target:
            self._move_toward(target.x, target.y, dt)
        self.rect.center = (int(self.x), int(self.y))

    def _move_toward(self, tx: float, ty: float, dt: float) -> None:
        dx, dy = tx - self.x, ty - self.y
        dist = math.hypot(dx, dy)
        if dist > 5:
            self.x += (dx / dist) * self.speed * dt
            self.y += (dy / dist) * self.speed * dt

    def can_fire(self) -> bool:
        return self._fire_cd <= 0 and self.ai_state == DroneAI.ATTACK

    def fire(self) -> float:
        self._fire_cd = 1.0 / max(self.fire_rate, 0.01)
        return float(self.damage)

    def take_damage(self, amount: float) -> bool:
        self.hp -= amount
        return self.hp <= 0

    def to_dict(self) -> dict:
        return {"id": self.id, "rarity": self.rarity, "hp": self.hp}

    def __repr__(self) -> str:
        return f"<Drone {self.name} ({self.rarity}) hp={self.hp}/{self.max_hp}>"
