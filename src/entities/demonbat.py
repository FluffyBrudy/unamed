import pygame
from pygame import Surface

from src.base.character import Character
from src.entities.behaviors import ChaserBehavior, KillableBehavior
from src.entities.knight import get_shape_aabb
from tests.test_objectmanager import EID_ENEMY


class DemonBat(Character):
    def __init__(self, x: float, y: float, target: Character) -> None:
        super().__init__(x, y, "demon_bat-192x192.anim", "demon_bat.collision", "fly", EID_ENEMY)
        self.killable_behavior = KillableBehavior(self, 0.25, 5)
        l, t, r, b = get_shape_aabb(self.x, self.y, self.collision_shape)
        w, h = (r - l), (b - t)
        self.chase_behavior = ChaserBehavior(self, target, (w + h), (w + h) // 2)

    def can_hurt(self) -> bool:
        return False

    def can_kill(self) -> bool:
        return False

    def handle_movement(self, dt: float):
        state = self.chase_behavior.state
        if state == "idle":
            self.vx = 0
            self.vy = 0
        elif state == "wait":
            self.vx = 0  # 1
            self.vy = 0
        elif state == "chase":
            norm_x, norm_y = self.chase_behavior.vector.normalize()
            self.vx, self.vy = norm_x * 150, norm_y * 150
        self.flipped = self.vx < 0
        self.collision_runner.move_grounded(self, None, None, dt, (self.vx, self.vy))

    def update(self, dt: float):
        self.chase_behavior.update(dt)
        self.killable_behavior.update(dt)
        self.update_animation(dt)
        self.handle_movement(dt)

    def render(self, surface: pygame.Surface, offset: tuple[float, float]):
        frame = self.get_frame()
        if not frame:
            return

        if self.flipped:
            frame = pygame.transform.flip(frame, True, False)

        shape_bound = self.shape_bounds.get(self.current_state)
        if shape_bound is not None:
            frame = frame.subsurface(shape_bound)

        l, t, r, b = get_shape_aabb(self.x, self.y, self.collision_shape)
        feet_x = (l + r) / 2
        feet_y = b

        w, h = frame.get_size()
        blit_x = round(feet_x - w / 2 - offset[0])
        blit_y = round(feet_y - h - offset[1])
        surface.blit(frame, (blit_x, blit_y))
