from typing import Protocol

from pygame import Surface
from tilemap_parser import ICollidable, ICollidableSprite
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
