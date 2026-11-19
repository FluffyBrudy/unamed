from enum import Enum, auto
from typing import Literal

import pygame

from src.base.character import Character


class BehaviorState(Enum):
    IDLE = auto()
    FOLLOW = auto()
    WAIT = auto()
    ACT = auto()


class KillableBehavior:
    def __init__(self, entity: Character, hit_cd: float, hit_count: int, kill_state: str | None = None) -> None:
        self.entity = entity
        self.hit_cd = hit_cd
        self.cd = 0
        self.hit_count = hit_count
        self.kill_state = kill_state
        self.is_dead = False  # for explicit control

        entity.can_hurt = self.can_hurt
        entity.can_kill = self.can_kill

    def can_hurt(self):
        return not self.is_dead and self.cd == 0

    def can_kill(self):
        if self.is_dead:
            return True
        animation_ended = self.entity.animation_states[self.entity.current_state].finished
        if self.kill_state is not None:
            return self.entity.current_state == self.kill_state and animation_ended
        return animation_ended

    def update(self, dt: float):
        if self.cd:
            self.cd = max(0, self.cd - dt)


class ChaserBehavior:
    def __init__(self, owner: Character, target: Character, visible_dist: float, attack_dist: float) -> None:
        self.state: Literal["idle", "chase", "attack", "wait"] = "idle"
        self.owner = owner
        self.target = target
        self.visible_dist = visible_dist**2
        self.attack_dist = attack_dist**2
        self.vector = pygame.Vector2(0, 0)

    def update(self, dt: float):
        dx = self.target.x - self.owner.x
        dy = self.target.y - self.owner.y
        self.vector.update(dx, dy)
        dist = self.vector.length_squared()
        if dist > self.visible_dist:
            self.state = "idle"
        elif self.target.can_hurt():
            if dist <= self.attack_dist:
                self.state = "attack"
            else:
                self.state = "chase"
        else:
            self.state = "wait"
