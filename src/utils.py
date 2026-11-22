from typing import Protocol

import pygame
from pygame import Surface
from tilemap_parser import ICollidable, ICollidableSprite
from tilemap_parser.runtime.movement.queries import math
from tilemap_parser.runtime.protocols import runtime_checkable


@runtime_checkable
class WorldObject(ICollidable, Protocol):
    eid: int

    def can_kill(self) -> bool: ...
    def can_hurt(self) -> bool: ...
    def update(self, dt: float): ...
    def render(self, surface: Surface, offset: tuple[float, float]): ...


@runtime_checkable
class WorldSprite(ICollidableSprite, Protocol):
    eid: int

    def can_kill(self) -> bool: ...
    def can_hurt(self) -> bool: ...
    def update(self, dt: float): ...
    def render(self, surface: Surface, offset: tuple[float, float]): ...


def sign(x: float):
    if x == 0:
        return 0
    return -1 if x < 0 else 1


def flicker(surface: Surface, speed=1.0):
    max_a, min_a = 255, 100
    amplitude = max_a - min_a
    center_offset = (max_a + min_a) / 2
    ticks = pygame.time.get_ticks() / 1000
    alpha = int(center_offset + amplitude * math.sin(ticks * speed))
    surf = surface.copy()
    surf.set_alpha(alpha)
    return surf


def silhouette_effect(
    surface: Surface, color: tuple[int, int, int] = (255, 255, 255), dest_surf: Surface | None = None
):
    mask = pygame.mask.from_surface(surface)
    return mask.to_surface(surface=dest_surf, setcolor=(*color[:3], 255), unsetcolor=(0, 0, 0, 0))


def move_towards(src: float, dest: float, dx: float):
    if src > dest:
        return max(src - dx, dest)
    return min(src + dx, dest)
