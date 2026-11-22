"""Hitbox wiring: attach, frame sync, origin alignment, and hit dispatch."""

from dataclasses import dataclass, field

import pygame
import pytest
from pygame import Surface
from tilemap_parser import (
    CapsuleShape,
    CircleShape,
    CollisionHit,
    CollisionPolygon,
    RectangleShape,
    flip_character_shape,
    get_shape_aabb,
)

from src.entities.demonbat import DemonBat
from src.entities.knight import Knight
from src.lib.collision_registry import default_player_enemy_collision
from src.loader import LevelData, SharedData
from src.objectmanager import ObjectManager
from src.settings import DEFAULT_ENEMY_EID


@dataclass
class DummyTarget:
    """Small collidable target for deterministic hitbox tests."""

    x: float
    y: float
    eid: int = DEFAULT_ENEMY_EID
    collision_shape: (
        RectangleShape | CircleShape | CapsuleShape | CollisionPolygon
    ) = field(default_factory=lambda: RectangleShape(16.0, 16.0))
    collision_layer: int = 1
    collision_mask: int = 0xFFFFFFFF

    def can_kill(self) -> bool:
        return False

    def can_hurt(self) -> bool:
        return True

    def update(self, dt: float) -> None:
        pass

    def render(self, surface: Surface, offset: tuple[float, float]) -> None:
        pass


@pytest.fixture(scope="module")
def initialized_game():
    pygame.init()
    surface = pygame.display.set_mode((800, 600))
    SharedData().preload()
    LevelData().preload("untitled.json")
    yield surface
    pygame.quit()


def _advance_to_frame(player: Knight, frame: int) -> None:
    player.current_state = "heavy_attack1"
    anim = player.animation_states["heavy_attack1"]
    anim.reset()
    clip = anim.clip
    assert clip is not None
    for _ in range(frame):
        anim.update(clip.frames[anim.frame_index].duration_ms)
    assert anim.frame_index == frame
    player.sync_hitboxes()


def _frame_origin(player: Knight) -> tuple[float, float]:
    bounds = player.anim_props["shape_bounds"][player.current_state]
    left, _, right, bottom = get_shape_aabb(
        player.x, player.y, player.collision_shape
    )
    return (
        (left + right) / 2 - bounds.width / 2 - bounds.x,
        bottom - bounds.height - bounds.y,
    )


def test_loader_binds_hitboxes_to_their_animation_library(initialized_game):
    hitboxes = SharedData().character_hitboxes["dark-knight-336x105.hitbox"]
    tile_size = SharedData().state_animations[
        "dark-knight-336x105.anim"
    ].library.tile_size
    assert hitboxes.frame_size == (float(tile_size[0]), float(tile_size[1]))


def test_synced_hitbox_matches_the_drawn_frame(initialized_game):
    player = Knight(1092.0, 300.0)
    _advance_to_frame(player, 3)

    state = player.hitbox_state
    assert state is not None and state.active
    assert state.window_id == "hit_1"

    parsed = state.hitboxes.windows_at("heavy_attack1", 3)[0].shapes[0]
    frame_left, frame_top = _frame_origin(player)
    expected = get_shape_aabb(frame_left, frame_top, parsed)
    actual = get_shape_aabb(player.x, player.y, state.collision_shapes[0])
    assert actual == pytest.approx(expected)


def test_flipped_hitbox_matches_the_drawn_frame(initialized_game):
    player = Knight(1092.0, 300.0)
    player.flipped = True
    player.flip_character_shape(True)
    _advance_to_frame(player, 3)

    state = player.hitbox_state
    assert state is not None and state.active
    parsed = state.hitboxes.windows_at("heavy_attack1", 3)[0].shapes[0]
    frame_size = state.hitboxes.frame_size
    assert frame_size is not None
    mirrored = flip_character_shape(parsed, frame_size, flip_h=True)
    frame_left, frame_top = _frame_origin(player)
    expected = get_shape_aabb(frame_left, frame_top, mirrored)
    actual = get_shape_aabb(player.x, player.y, state.collision_shapes[0])
    assert actual == pytest.approx(expected)


def test_attack_hitbox_reaches_a_target_in_front(initialized_game):
    player = Knight(1092.0, 300.0)
    _advance_to_frame(player, 3)

    state = player.hitbox_state
    assert state is not None
    hitbox = get_shape_aabb(player.x, player.y, state.collision_shapes[0])
    target = DummyTarget(
        x=(hitbox[0] + hitbox[2]) / 2 - 8.0,
        y=(hitbox[1] + hitbox[3]) / 2 - 8.0,
    )

    manager = ObjectManager()
    manager.add_object(player, hitbox_state=state)
    manager.add_object(target)

    hits = [
        hit
        for hit in manager.collision_manager.check_all_collisions()
        if hit.via_hitbox
    ]
    assert len(hits) == 1
    assert hits[0].other(player) is target


def test_hitbox_hit_is_deduped_per_window(initialized_game):
    player = Knight(1092.0, 300.0)
    _advance_to_frame(player, 3)
    state = player.hitbox_state
    assert state is not None
    hitbox = get_shape_aabb(player.x, player.y, state.collision_shapes[0])
    target = DummyTarget(
        x=(hitbox[0] + hitbox[2]) / 2 - 8.0,
        y=(hitbox[1] + hitbox[3]) / 2 - 8.0,
    )

    calls: list[CollisionHit] = []

    def on_hit(_a, _b, hit: CollisionHit) -> None:
        if hit.via_hitbox:
            calls.append(hit)

    manager = ObjectManager()
    manager.add_object(player, hitbox_state=state)
    manager.add_object(target)
    manager.register_handler(player.eid, target.eid, on_hit)

    def dispatch() -> None:
        for hit in manager.collision_manager.check_all_collisions(hit_once=True):
            manager.resolve_collision(hit)

    dispatch()
    dispatch()
    assert len(calls) == 1

    # Leaving the window and re-entering it starts a fresh hit-once set.
    state.sync("heavy_attack1", 0)
    assert not state.active
    dispatch()
    player.sync_hitboxes()
    dispatch()
    assert len(calls) == 2


def test_knight_hitbox_damages_the_target_not_the_owner(initialized_game):
    player = Knight(1092.0, 300.0)
    _advance_to_frame(player, 3)
    state = player.hitbox_state
    assert state is not None
    bat = DemonBat(1100.0, 300.0, player)
    assert bat.can_hurt()

    hit = CollisionHit(
        object_a=player,
        object_b=bat,
        normal=(1.0, 0.0),
        depth=1.0,
        hitbox_a=state,
    )
    default_player_enemy_collision(player, bat, hit)

    assert not bat.can_hurt()
    assert player.can_hurt()
