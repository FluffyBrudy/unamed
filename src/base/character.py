from tilemap_parser import AnimationPlayer, ICollidableSprite, flip_character_shape

from src.loader import SharedData


class Character(ICollidableSprite):
    def __init__(
        self,
        x: float,
        y: float,
        animation_stem: str,
        collision_stem: str,
        default_state: str,
    ) -> None:
        self.x = x
        self.y = y
        self.vx = 0
        self.vy = 0
        self.on_ground = False

        animation_set = SharedData().state_animations[animation_stem]
        animations = animation_set.library.animations
        self.fps = {k: animations[k].fps for k in animations}
        self.animation_states = {k: AnimationPlayer(animation_set, k) for k in animations}

        collision_data = SharedData().character_collisions[collision_stem]
        self.collision_mask = collision_data.collision_mask
        self.collision_layer = collision_data.collision_layer
        self.original_collision_shape = collision_data.shape
        self.collision_shape = collision_data.shape

        self.current_state = default_state

    def get_state(self) -> str:
        raise NotImplementedError()

    def manage_state(self):
        next_state = self.get_state()
        if self.current_state != next_state:
            self.animation_states[self.current_state].reset()
            self.current_state = next_state

    def flip_character_shape(self, flip_h: bool):
        frame = self.get_frame()
        if frame is None:
            return
        if flip_h:
            self.collision_shape = flip_character_shape(
                self.original_collision_shape,
                frame.size,
                flip_h=flip_h,
            )
        else:
            self.collision_shape = self.original_collision_shape

    def update(self, dt: float):
        anim_state = self.animation_states[self.current_state]
        fps = self.fps[self.current_state]
        anim_state.update(dt * (fps / 60) * 1000)

    def get_frame(self):
        current_frame = self.animation_states[self.current_state].get_current_image()
        if current_frame is None:
            return
        return current_frame
