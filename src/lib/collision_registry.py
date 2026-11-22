from tilemap_parser import CollisionHit

from src.base.character import Character
from src.settings import KNIGHT_EID


def default_player_enemy_collision(
    obj_a: Character,
    obj_b: Character,
    hit: CollisionHit,
):
    if hit.via_hitbox:
        state = hit.hitbox_a or hit.hitbox_b
        if state is None:
            return
        if obj_a is state.owner:
            target = obj_b
        elif obj_b is state.owner:
            target = obj_a
        else:
            return
        target.on_collision()
        return

    if obj_a.eid == KNIGHT_EID:
        if obj_b.anim_activation_state() == "active":
            obj_a.on_collision()
    elif obj_b.eid == KNIGHT_EID:
        if obj_a.anim_activation_state() == "active":
            obj_b.on_collision()
