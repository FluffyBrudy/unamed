from pygame import Vector2
from pygame.rect import Rect
from tilemap_parser import AnimationPlayer, flip_character_shape

from src.loader import LevelData, SharedData


class Character:
    """Satisfies tilemap_parser's ICollidableSprite structurally; the
    protocol is not inherited explicitly (inherited read-only protocol
    members would shadow the plain attributes assigned below)."""

    def __init__(
        self,
        x: float,
        y: float,
        animation_stem: str,
        collision_stem: str,
        default_state: str,
        eid: int,
    ) -> None:
        self.x = x
        self.y = y
        self.vx = 0
        self.vy = 0
        self.on_ground = False

        self.direction = Vector2(0, 0)

        self.fps = {}
        self.animation_states: dict[str, AnimationPlayer] = {}
        self.shape_bounds: dict[str, Rect] = {}
        base_animation_set = SharedData().state_animations[animation_stem]
        self.base_tile_size = base_animation_set.library.tile_size
        self.add_animation(animation_stem)

        collision_data = SharedData().character_collisions[collision_stem]
        self.collision_mask = collision_data.collision_mask
        self.collision_layer = collision_data.collision_layer
        self.original_collision_shape = collision_data.shape
        self.collision_shape = collision_data.shape

        self.current_state = default_state
        self.eid = eid

        self.collision_runner = LevelData().collision_runner
        self.flipped = False

        self.direction = Vector2(1, 0)

    def add_animation(self, animation_stem: str):
        animation_set = SharedData().state_animations[animation_stem]
        animations = animation_set.library.animations
        self.fps |= {k: animations[k].fps for k in animations}
        self.animation_states |= {k: AnimationPlayer(animation_set, k) for k in animations}
        self.shape_bounds |= {
            k: bounds
            for k in animations
            if (bounds := animation_set.get_content_bounds(k)) is not None
        }

    def get_state(self) -> str:
        raise NotImplementedError()

    def can_kill(self) -> bool:
        raise NotImplementedError()

    def can_hurt(self) -> bool:
        raise NotImplementedError()

    def manage_state(self):
        next_state = self.get_state()
        if self.current_state != next_state:
            self.animation_states[self.current_state].reset()
            self.current_state = next_state

    def flip_character_shape(self, flip_h: bool):
        if flip_h:
            self.collision_shape = flip_character_shape(
                self.original_collision_shape,
                self.base_tile_size,
                flip_h=flip_h,
            )
        else:
            self.collision_shape = self.original_collision_shape

    def update_animation(self, dt: float):
        anim_state = self.animation_states[self.current_state]
        fps = self.fps[self.current_state]
        anim_state.update(dt * (fps / 60) * 1000)

    def get_frame(self):
        current_frame = self.animation_states[self.current_state].get_current_image()
        if current_frame is None:
            return
        return current_frame
