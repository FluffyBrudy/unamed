"""Tests for src.objects.ObjectManager.

Layer/mask matrix (bitwise, so no manual math is ever needed):

    bit 0 -> bullet   bit 1 -> player   bit 2 -> enemy

For a pair to collide "should_collide" requires MUTUAL agreement (AND):
    (a.mask & b.layer) != 0 and (b.mask & a.layer) != 0
So each entry below lists the layers that object kind *responds to*.
"""

from dataclasses import dataclass, field
from unittest.mock import ANY

import pytest
from pygame import Surface
from tilemap_parser import RectangleShape

from src.objectmanager import ObjectManager

# -- dispatch ids (manager dispatches on eid pairs) ----------------------------
EID_PLAYER, EID_ENEMY, EID_BULLET = 1, 2, 3

# -- collision layers ---------------------------------------------------------
LAYER_BULLET = 1 << 0
LAYER_PLAYER = 1 << 1
LAYER_ENEMY = 1 << 2
MASK_ALL = LAYER_PLAYER | LAYER_ENEMY | LAYER_BULLET

# kind -> (layer it occupies, mask it responds to)
#   player_enemies: yes; bullet_enemies: yes; player_bullet: nobody asks -> no hit
KINDS: dict[int, tuple[int, int]] = {
    EID_PLAYER: (LAYER_PLAYER, MASK_ALL),
    EID_ENEMY: (LAYER_ENEMY, LAYER_PLAYER | LAYER_BULLET),
    EID_BULLET: (LAYER_BULLET, LAYER_ENEMY),
}


@dataclass
class FakeWorldObject:
    """Stands in for a real entity; satisfies the WorldObject protocol."""

    eid: int
    x: float = 0.0
    y: float = 0.0
    collision_layer: int = MASK_ALL
    collision_mask: int = MASK_ALL
    collision_shape: RectangleShape = field(default_factory=lambda: RectangleShape(16.0, 16.0))
    killed: bool = False
    update_calls: list[float] = field(default_factory=list)
    render_calls: list[tuple[float, float]] = field(default_factory=list)

    def can_kill(self) -> bool:
        return self.killed

    def can_hurt(self) -> bool:
        return False

    def update(self, dt: float) -> None:
        self.update_calls.append(dt)

    def render(self, surface: Surface, offset: tuple[float, float]) -> None:
        self.render_calls.append(offset)


def make_world_object(eid: int, *, x: float = 0.0, y: float = 0.0, **overrides) -> FakeWorldObject:
    """Builds a fake with kind-appropriate layer/mask; override anything at call time."""
    layer, mask = KINDS[eid]
    return FakeWorldObject(
        eid=eid,
        x=x,
        y=y,
        collision_layer=layer,
        collision_mask=mask,
        **overrides,
    )


@dataclass
class RecordingHandler:
    """Collision callback that records the (a.eid, b.eid, hit) of every dispatch."""

    calls: list[tuple[int, int, object]] = field(default_factory=list)

    def __call__(self, obj_a, obj_b, hit) -> None:
        self.calls.append((obj_a.eid, obj_b.eid, hit))


# -- add_object ---------------------------------------------------------------


def test_add_object_stores_object_in_container_and_collision_manager():
    manager = ObjectManager()
    enemy = make_world_object(EID_ENEMY, x=100.0)

    manager.add_object(enemy)

    assert manager.object_container == [enemy]
    assert enemy in manager.collision_manager.objects


def test_add_object_rejects_object_missing_protocol_members():
    manager = ObjectManager()
    imposter = make_world_object(EID_PLAYER, x=100.0)
    del imposter.eid  # now the isinstance check must fail

    manager.add_object(imposter)

    assert manager.object_container == []
    assert manager.collision_manager.objects == []


# -- update: lifecycle --------------------------------------------------------


def test_update_removes_killed_object_from_both_containers():
    manager = ObjectManager()
    dead = make_world_object(EID_ENEMY, killed=True, x=100.0)
    manager.add_object(dead)

    manager.update(0.016)

    assert dead.update_calls == [0.016]  # updated once before removal
    assert manager.object_container == []
    assert manager.collision_manager.objects == []


def test_update_keeps_alive_objects_and_records_dt():
    manager = ObjectManager()
    alive = make_world_object(EID_ENEMY, x=100.0)
    manager.add_object(alive)

    manager.update(0.016)

    assert manager.object_container == [alive]
    assert manager.collision_manager.objects == [alive]
    assert alive.update_calls == [0.016]


# -- update: collision dispatch ----------------------------------------------


def test_registered_pair_dispatches_to_handler():
    manager = ObjectManager()
    handler = RecordingHandler()
    manager.register_handler(EID_PLAYER, EID_ENEMY, handler)

    player = make_world_object(EID_PLAYER, x=0.0)
    enemy = make_world_object(EID_ENEMY, x=8.0, y=8.0)  # overlaps the player's 16x16 shape
    manager.add_object(player)
    manager.add_object(enemy)

    manager.update(0.016)

    assert handler.calls == [(EID_PLAYER, EID_ENEMY, ANY)]
    # both survive; nothing in the fake sinks either of them
    assert len(manager.object_container) == 2


def test_pair_with_incompatible_masks_never_dispatches():
    manager = ObjectManager()
    handler = RecordingHandler()
    manager.register_handler(EID_PLAYER, EID_BULLET, handler)  # registered, but masks forbid

    player = make_world_object(EID_PLAYER, x=0.0)
    bullet = make_world_object(EID_BULLET, x=4.0, y=4.0)  # physically overlapping
    manager.add_object(player)
    manager.add_object(bullet)

    manager.update(0.016)

    assert handler.calls == []


def test_collision_of_kind_without_registered_handler_is_ignored():
    manager = ObjectManager()
    handler = RecordingHandler()
    manager.register_handler(EID_PLAYER, EID_ENEMY, handler)  # only player-enemy exists

    player_a = make_world_object(EID_PLAYER, x=0.0)
    player_b = make_world_object(EID_PLAYER, x=8.0, y=8.0)  # overlaps, eid-pair (1,1) unhandled
    manager.add_object(player_a)
    manager.add_object(player_b)

    manager.update(0.016)

    assert handler.calls == []
    assert len(manager.object_container) == 2


# -- register_handler ----------------------------------------------------------


def test_register_handler_rejects_duplicate_pair_in_either_order():
    manager = ObjectManager()
    manager.register_handler(EID_PLAYER, EID_ENEMY, RecordingHandler())

    with pytest.raises(ValueError):
        manager.register_handler(EID_ENEMY, EID_PLAYER, RecordingHandler())

    with pytest.raises(ValueError):
        manager.register_handler(EID_PLAYER, EID_ENEMY, RecordingHandler())


# -- render ---------------------------------------------------------------------


def test_render_dispatches_offset_to_every_object():
    manager = ObjectManager()
    player = make_world_object(EID_PLAYER, x=0.0)
    enemy = make_world_object(EID_ENEMY, x=64.0)
    manager.add_object(player)
    manager.add_object(enemy)

    manager.render(Surface((8, 8)), (10.0, 20.0))

    assert player.render_calls == [(10.0, 20.0)]
    assert enemy.render_calls == [(10.0, 20.0)]
