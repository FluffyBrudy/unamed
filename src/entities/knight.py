from random import random

import pygame
from pygame import Event
from pygame.rect import Rect
from tilemap_parser import get_shape_aabb

from src.base.character import Character
from src.entities.behaviors import KillableBehavior
from src.settings import SOILDER_EID

HEAD_TURN_NONE = 0
HEAD_TURN_LEFT = -1
HEAD_TURN_RIGHT = 1


class Knight(Character):
    def __init__(self, x: float, y: float):
        super().__init__(x, y, "dark_knight-192x192.anim", "dark_knight.collision", "idle", SOILDER_EID)

        # fmt: off
        registered_keys = (
            pygame.K_LEFT, pygame.K_RIGHT,
            pygame.K_SPACE, pygame.K_RETURN
        )
        # fmt: on
        self.keys_pressed = dict.fromkeys(registered_keys, False)
        self.add_animation("dark-knight-336x105.anim")
        self.add_animation("dark-knight-168x207.anim")
        self.is_attacking = False
        self.killable_behavior = KillableBehavior(self, 0.25, 5, "death")

    def get_state(self) -> str:
        if self.killable_behavior.reach_hit_count():
            return "death"
        if self.vy > 0:
            return "fall"
        elif self.vy < 0:
            return "jump"
        elif self.is_attacking:
            return "heavy_attack1"
        elif abs(self.vx) > 0:
            return "run"
        return "idle"

    def can_hurt(self) -> bool:
        return self.killable_behavior.can_hurt()

    def can_kill(self) -> bool:
        return self.killable_behavior.can_kill()

    def handle_event(self, event: Event):
        if event.type == pygame.KEYDOWN:
            if event.key in self.keys_pressed:
                self.keys_pressed[event.key] = True
        elif event.type == pygame.KEYUP:
            if event.key in self.keys_pressed:
                self.keys_pressed[event.key] = False

    def handle_movement(self, dt: float):
        input_x = self.keys_pressed[pygame.K_RIGHT] - self.keys_pressed[pygame.K_LEFT]
        if self.is_attacking:
            input_x = 0
        jumped = self.on_ground and self.keys_pressed[pygame.K_SPACE] and not self.is_attacking
        if input_x != 0 and self.direction.x != input_x:
            self.direction.x = input_x
            self.flipped = self.direction.x < 0
            self.flip_character_shape(self.flipped)
        self.collision_runner.move_platformer_with_slide(self, None, None, dt, input_x, jumped)

    def manage_state(self):
        if self.is_attacking:
            self.is_attacking = not self.animation_states[self.current_state].finished
        elif self.keys_pressed.get(pygame.K_RETURN):
            self.is_attacking = self.on_ground
        super().manage_state()

    def update(self, dt: float):
        self.update_animation(dt)
        self.handle_movement(dt)
        self.manage_state()

    def render(self, surface: pygame.Surface, offset: tuple[float, float]):
        frame = self.get_frame()
        if not frame:
            return
        if self.flipped:
            frame = pygame.transform.flip(frame, True, False)
        frame, blit_x, blit_y = self.get_blit_pos(frame, offset)
        surface.blit(frame, (blit_x, blit_y))
