from enum import Enum, auto

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
