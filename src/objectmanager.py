from collections.abc import Callable

from pygame.surface import Surface
from tilemap_parser import CharacterHitboxes, HitboxState
from tilemap_parser.runtime.collision.hit import CollisionHit
from tilemap_parser.runtime.collision.manager import ObjectCollisionManager

from src.utils import WorldObject

THandler = Callable[[WorldObject, WorldObject, CollisionHit], None]


class ObjectManager:
    def __init__(self) -> None:
        self.collision_manager: ObjectCollisionManager = ObjectCollisionManager()
        self.object_container: list[WorldObject] = []
        self._handlers: dict[tuple[int, int], THandler] = {}

    def register_handler(self, a_id: int, b_id: int, handler: THandler):
        if (a_id, b_id) in self._handlers or (b_id, a_id) in self._handlers:
            raise ValueError("Handlers already exists")
        self._handlers[(a_id, b_id)] = handler

    def add_object(
        self, obj: WorldObject, hitboxes: CharacterHitboxes | None = None
    ) -> HitboxState | None:
        """Register a game object with the manager.

        Colliding objects must carry the ICollidable fields themselves
        (collision_shapes / collision_shape, collision_layer, collision_mask);
        the manager works with WorldObject. When `hitboxes` is given, a
        HitboxState is attached fixture-style to the object: broadphase
        enumerates it beside the body, removing the object drops it, and
        an idle window contributes nothing. Sync the returned state each
        frame (`state.sync(clip, frame, flip_h=...)`); hits it produces
        are event-only (hit.via_hitbox, hit.hitbox_a/hitbox_b carry the
        state; CollisionHit.resolve() refuses them).
        """
        state: HitboxState | None = None
        if hitboxes is not None:
            state = HitboxState(hitboxes, obj)
            self.collision_manager.attach_hitboxes(obj, state)
        self.object_container.append(obj)
        self.collision_manager.add_object(obj)
        return state

    def resolve_collision(self, collision_hit: CollisionHit):
        obj_a: WorldObject = collision_hit.object_a  # type: ignore
        obj_b: WorldObject = collision_hit.object_b  # type: ignore
        handler = self._handlers.get((obj_a.eid, obj_b.eid))

        if handler is not None:
            handler(obj_a, obj_b, collision_hit)
            return

        handler = self._handlers.get((obj_b.eid, obj_a.eid))
        if handler is not None:
            handler(obj_b, obj_a, collision_hit)

    def update(self, dt: float):
        for obj_index in range(len(self.object_container) - 1, -1, -1):
            obj = self.object_container[obj_index]
            obj.update(dt)
            if obj.can_kill():
                self.collision_manager.remove_object(obj)
                del self.object_container[obj_index]

        for collision_hit in self.collision_manager.check_all_collisions():
            self.resolve_collision(collision_hit)

    def render(self, surface: Surface, offset: tuple[float, float]):
        for obj in self.object_container:
            obj.render(surface, offset)
