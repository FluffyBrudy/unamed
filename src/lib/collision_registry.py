from typing import TYPE_CHECKING

from tilemap_parser import CollisionHit

from src.base.character import Character
from src.settings import DEFAULT_ENEMY_EID, KNIGHT_EID

if TYPE_CHECKING:
    from src.entities.knight import Knight


def default_player_enemy_collision(obj_a: Character, obj_b: Character, collision_hit: CollisionHit):
    if obj_a.eid == KNIGHT_EID:
        if obj_b.has_anim_finished() and obj_b.anim_activation_state() == "active":
            obj_a.on_collision()
    elif obj_b.eid == DEFAULT_ENEMY_EID:
        if obj_a.has_anim_finished():
            obj_b.on_collision()
