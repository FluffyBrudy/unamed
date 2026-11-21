from typing import Any

from tilemap_parser import CollisionHit

from src.base.character import Character
from src.settings import KNIGHT_EID


def default_player_enemy_collision(
    obj_a: Character,
    obj_b: Character,
    _: CollisionHit,
):
    if obj_a.eid == KNIGHT_EID:
        if obj_b.anim_activation_state() == "active":
            obj_a.on_collision()
    elif obj_b.eid == KNIGHT_EID:
        if obj_a.anim_activation_state() == "active":
            obj_b.on_collision()
