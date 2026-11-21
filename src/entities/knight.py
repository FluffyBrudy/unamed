from random import random

import pygame
from pygame import Event
from pygame.rect import Rect
from tilemap_parser import get_shape_aabb

from src.base.character import Character
from src.entities.behaviors import KillableBehavior
from src.loader import SharedData
from src.settings import KNIGHT_EID

HEAD_TURN_NONE = 0
HEAD_TURN_LEFT = -1
HEAD_TURN_RIGHT = 1


class Knight(Character):
    def __init__(self, x: float, y: float):
        super().__init__(x, y, "dark_knight-192x192.anim", "dark_knight.collision", "idle", KNIGHT_EID)

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
        self.killable_behavior = KillableBehavior(self, 1.5, 5, "death")
        self.debug = SharedData().debug
        self._last_debug_state = self.current_state
        self._register_debug_watches()

    def _register_debug_watches(self):
        debug = self.debug
        debug.watch("player/state", lambda: self.current_state)
        debug.watch("player/cd", lambda: f"{self.killable_behavior.cd:.2f}s / {self.killable_behavior.hit_cd:.2f}s")
        debug.watch("player/hp", lambda: f"{self.killable_behavior.hit_count}/{self.killable_behavior.max_hit_count}")
        debug.watch("player/can_hurt", lambda: self.killable_behavior.can_hurt())
        debug.watch("player/ground", lambda: self.on_ground)
        debug.watch("player/pos", lambda: f"{self.x:.0f}, {self.y:.0f}")

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

    def on_collision(self, **kwargs):
        if self.can_hurt():
            self.killable_behavior.apply_cd()

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
        was_attacking = self.is_attacking
        if self.is_attacking:
            self.is_attacking = not self.animation_states[self.current_state].finished
        elif self.keys_pressed.get(pygame.K_RETURN):
            self.is_attacking = self.on_ground
        super().manage_state()
        if self.is_attacking and not was_attacking:
            self.debug.event(
                "player.attack",
                level="info",
                key="player.attack",
                state=self.current_state,
                on_ground=self.on_ground,
            )
        if self.current_state != self._last_debug_state:
            self.debug.event(
                "player.state",
                key="player.state",
                previous=self._last_debug_state,
                current=self.current_state,
            )
            self._last_debug_state = self.current_state

    def update(self, dt: float):
        self.killable_behavior.update(dt)
        self.update_animation(dt)
        self.handle_movement(dt)
        self.manage_state()

    def _render_debug(self):
        debug = self.debug
        if not debug.enabled or not debug.show_shapes:
            return

        left, top, right, bottom = get_shape_aabb(self.x, self.y, self.collision_shape)
        width = max(1.0, right - left)
        height = max(1.0, bottom - top)

        debug.rect((left, top, width, height), (90, 220, 255), width=1, space="world")
        debug.line(
            (self.x, self.y),
            (self.x + self.vx * 0.15, self.y + self.vy * 0.15),
            (120, 255, 150),
            width=2,
            space="world",
        )
        debug.point((self.x, self.y), (255, 230, 120), size=4, space="world")

        cd = self.killable_behavior.cd
        hit_cd = self.killable_behavior.hit_cd
        ratio = max(0.0, min(1.0, cd / hit_cd)) if hit_cd > 0 else 0.0
        bar_width = 48.0
        bar_y = top - 10
        debug.rect((left, bar_y, bar_width, 5), (25, 28, 36), width=0, space="world")
        if ratio > 0:
            debug.rect(
                (left, bar_y, bar_width * ratio, 5),
                (255, 110, 90),
                width=0,
                space="world",
            )
        else:
            debug.rect((left, bar_y, bar_width, 5), (90, 220, 140), width=0, space="world")
        debug.label(
            (left, top - 26),
            lambda: (
                f"{self.current_state}  cd {self.killable_behavior.cd:.2f}s  "
                f"{'ready' if self.killable_behavior.can_hurt() else 'cooldown'}"
            ),
            (255, 236, 150),
            space="world",
        )

    def render(self, surface: pygame.Surface, offset: tuple[float, float]):
        self._render_debug()
        frame = self.get_frame()
        if not frame:
            return
        if self.flipped:
            frame = pygame.transform.flip(frame, True, False)
        frame, blit_x, blit_y = self.get_blit_pos(frame, offset)
        surface.blit(frame, (blit_x, blit_y))
