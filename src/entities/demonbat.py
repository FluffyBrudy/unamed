import pygame
from pygame import Surface
from tilemap_parser import check_collision

from src.base.character import Character
from src.entities.behaviors import ChaserBehavior, KillableBehavior
from src.entities.knight import get_shape_aabb
from src.loader import SharedData
from src.settings import DEFAULT_ENEMY_EID


class DemonBat(Character):
    def __init__(self, x: float, y: float, target: Character) -> None:
        super().__init__(x, y, "demon_bat-192x192.anim", "demon_bat.collision", "fly", DEFAULT_ENEMY_EID)
        self.killable_behavior = KillableBehavior(self, 0.25, 5, "death")
        l, t, r, b = get_shape_aabb(self.x, self.y, self.collision_shape)
        w, h = (r - l), (b - t)
        self.chase_behavior = ChaserBehavior(self, target, (w + h), 50)
        SharedData().debug.watch("bat/attack", lambda: self.chase_behavior.vector)
        SharedData().debug.watch("bat/behave_state", lambda: self.chase_behavior.state)
        SharedData().debug.watch("bat/state", lambda: self.current_state)
        self.direction.x = 1

    def get_state(self) -> str:
        if self.chase_behavior.state == "attack" and self.chase_behavior.target.can_hurt():
            return "bite"
        return "fly"

    def can_hurt(self) -> bool:
        return self.killable_behavior.can_hurt()

    def can_kill(self) -> bool:
        return self.killable_behavior.can_kill()

    def handle_movement(self, dt: float):
        state = self.chase_behavior.state
        if state == "idle":
            self.vx = 0
            self.vy = 0
        elif state == "wait" or state == "attack":
            self.vx = 0  # 1
            self.vy = 0
        elif state == "chase":
            norm_x, norm_y = self.chase_behavior.vector.normalize()
            self.vx, self.vy = norm_x * 150, norm_y * 150
        if self.vx != 0:
            self.direction.x = -1 if self.vx < 0 else 1
        self.flipped = self.direction.x < 0
        self.collision_runner.move_grounded(self, None, None, dt, (self.vx, self.vy))

    def update(self, dt: float):
        self.chase_behavior.update(dt)
        self.killable_behavior.update(dt)
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
