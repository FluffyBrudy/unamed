from pygame import Vector2

from src.base.character import Character
from src.entities.behaviors import KillableBehavior
from src.loader import LevelData
from src.settings import DEFAULT_ENEMY_EID
from src.utils import sign


class Undead(Character):
    CHASE_RANGE = 300**2
    SPEED = 50

    def __init__(self, x: float, y: float, target: Character):
        super().__init__(x, y, "undead.anim", "undead.collision", "idle", DEFAULT_ENEMY_EID)
        self.killable_behavior = KillableBehavior(self, 0.2, 5)
        self.target = target
        self.target_vector = Vector2((target.x - self.x, target.y - self.y))

        self.collision_runner = LevelData().collision_runner

    def update(self, dt: float):
        self.update_animation(dt)
        self.target_vector.update((self.target.x - self.x, self.target.y - self.y))
        if self.target_vector.length_squared() <= self.CHASE_RANGE:
            self.vx = sign(self.target_vector.x) * self.SPEED
        movement_res = self.collision_runner.move_grounded(self, None, None, dt)
        self.manage_state()
