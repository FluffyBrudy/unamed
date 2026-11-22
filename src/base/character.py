from typing import Any, Literal, TypedDict

import pygame
from pygame import Surface, Vector2
from pygame.rect import Rect
from tilemap_parser import (
    AnimationPlayer,
    CharacterHitboxes,
    HitboxState,
    ICollidableSprite,
    flip_character_shape,
    get_shape_aabb,
)

from src.loader import LevelData, SharedData


class AnimProps(TypedDict):
    shape_bounds: dict[str, Rect]
    metadata: dict[str, Any]


class Character(ICollidableSprite):
    def __init__(
        self,
        x: float,
        y: float,
        animation_stem: str,
        collision_stem: str,
        default_state: str,
        eid: int,
        *,
        hitboxes: CharacterHitboxes | None = None,
    ) -> None:
        self.x = x
        self.y = y
        self.vx = 0
        self.vy = 0
        self.on_ground = False

        self.fps = {}
        self.animation_states: dict[str, AnimationPlayer] = {}
        self.anim_props: AnimProps = {"shape_bounds": {}, "metadata": {}}
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
        self.hitbox_state: HitboxState | None = HitboxState(hitboxes, self) if hitboxes is not None else None

    def add_animation(self, animation_stem: str):
        animation_set = SharedData().state_animations[animation_stem]
        animations = animation_set.library.animations
        self.fps |= {k: animations[k].fps for k in animations}
        self.animation_states |= {k: AnimationPlayer(animation_set, k) for k in animations}
        for k in animations:
            bounds = animation_set.get_content_bounds(k)
            metadata = animations[k].metadata
            if bounds:
                self.anim_props["shape_bounds"][k] = bounds
            if metadata:
                for mk, v in metadata.items():
                    self.anim_props["metadata"][f"{k}.{mk}"] = v

    def anim_activation_state(self) -> Literal["active", "inactive"]:
        activation_frame = self.anim_props["metadata"].get(f"{self.current_state}.activation", 0)
        deactivation_frame = self.anim_props["metadata"].get(f"{self.current_state}.deactivation", 0)
        current_frame = self.animation_states[self.current_state].frame_index
        if current_frame >= activation_frame and current_frame < deactivation_frame:
            return "active"
        return "inactive"

    def get_state(self) -> str:
        raise NotImplementedError()

    def can_kill(self) -> bool:
        raise NotImplementedError()

    def can_hurt(self) -> bool:
        raise NotImplementedError()

    def has_anim_finished(self):
        return self.animation_states[self.current_state].finished

    def on_collision(self, **kwargs):
        pass

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

    def sync_hitboxes(self) -> None:
        state = self.hitbox_state
        if state is None:
            return

        clip = self.current_state
        frame_index = self.animation_states[clip].frame_index
        bounds = self.anim_props["shape_bounds"].get(clip)
        if bounds is not None:
            frame_x = float(bounds.x)
            frame_y = float(bounds.y)
            frame_w = float(bounds.width)
            frame_h = float(bounds.height)
        else:
            frame = self.get_frame()
            if frame is None:
                state.sync(clip, frame_index, flip_h=self.flipped)
                return
            frame_x = frame_y = 0.0
            frame_w, frame_h = frame.get_size()

        left, _, right, bottom = get_shape_aabb(self.x, self.y, self.collision_shape)
        frame_left = (left + right) / 2 - frame_w / 2 - frame_x
        frame_top = bottom - frame_h - frame_y
        state.sync(
            clip,
            frame_index,
            flip_h=self.flipped,
            origin=(frame_left - self.x, frame_top - self.y),
        )

    def get_frame(self):
        current_frame = self.animation_states[self.current_state].get_current_image()
        if current_frame is None:
            return
        return current_frame

    def get_blit_pos(self, frame: Surface, offset: tuple[float, float]):
        shape_bound = self.anim_props["shape_bounds"].get(self.current_state)
        if shape_bound is not None:
            frame = frame.subsurface(shape_bound)
        l, _, r, b = get_shape_aabb(self.x, self.y, self.collision_shape)
        feet_x = (l + r) / 2
        feet_y = b
        w, h = frame.get_size()
        blit_x = round(feet_x - w / 2 - offset[0])
        blit_y = round(feet_y - h - offset[1])
        return frame, blit_x, blit_y
