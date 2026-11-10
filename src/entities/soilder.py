from random import random

import pygame
from pygame import Event

from src.base.character import Character
from src.settings import SOILDER_EID

HEAD_TURN_NONE = 0
HEAD_TURN_LEFT = -1
HEAD_TURN_RIGHT = 1


class Soilder(Character):
    def __init__(self, x: float, y: float):
        super().__init__(x, y, "player.anim", "player.collision", "idle", SOILDER_EID)
        self.keys_pressed = {pygame.K_LEFT: False, pygame.K_RIGHT: False, pygame.K_SPACE: False}
        self.head_turn = HEAD_TURN_NONE

    def get_state(self) -> str:
        if self.vy > 0:
            return "fall"
        elif self.vy < 0:
            return "jump"
        elif abs(self.vx) > 0:
            return "walk"
        elif self.head_turn == HEAD_TURN_LEFT:
            return "idle_turn_left"
        elif self.head_turn == HEAD_TURN_RIGHT:
            return "idle_turn_right"
        return "idle"

    def handle_event(self, event: Event):
        if event.type == pygame.KEYDOWN:
            if event.key in self.keys_pressed:
                self.keys_pressed[event.key] = True
        elif event.type == pygame.KEYUP:
            if event.key in self.keys_pressed:
                self.keys_pressed[event.key] = False

    def handle_movement(self, dt: float):
        input_x = self.keys_pressed[pygame.K_RIGHT] - self.keys_pressed[pygame.K_LEFT]
        jumped = self.on_ground and self.keys_pressed[pygame.K_SPACE]
        if input_x != 0:
            if self.direction.x != input_x:
                self.direction.x = input_x
                self.flip_character_shape(True)
        self.flipped = self.direction.x < 0
        self.collision_runner.move_platformer_with_slide(self, None, None, dt, input_x, jumped)

    def update_animation(self, dt: float):
        if self.current_state.startswith("idle"):
            if self.head_turn == HEAD_TURN_NONE:
                if random() < dt * 0.4:
                    self.head_turn = HEAD_TURN_LEFT
            elif self.head_turn == HEAD_TURN_LEFT and random() < dt * 0.4:
                if self.animation_states[self.current_state].finished:
                    self.head_turn = HEAD_TURN_RIGHT
            elif self.head_turn == HEAD_TURN_RIGHT:
                if self.animation_states[self.current_state].finished:
                    self.head_turn = HEAD_TURN_NONE
            super().update_animation(dt * abs(self.head_turn))
        else:
            self.head_turn = HEAD_TURN_NONE
            super().update_animation(dt)

    def update(self, dt: float):
        self.update_animation(dt)
        self.handle_movement(dt)
        self.manage_state()

    def render(self, surface: pygame.Surface, offset: tuple[float, float]):
        frame = self.get_frame()
        if frame:
            if self.flipped:
                frame = pygame.transform.flip(frame, True, False)
            surface.blit(frame, (self.x - offset[0], self.y - offset[1]))
