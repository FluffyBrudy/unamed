from collections.abc import Callable

from pygame.surface import Surface
from tilemap_parser.runtime.collision.hit import CollisionHit
from tilemap_parser.runtime.collision.manager import ObjectCollisionManager
from tilemap_parser.runtime.protocols import ICollidable

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

    def add_object(self, obj: ICollidable):
        if isinstance(obj, WorldObject):
            self.object_container.append(obj)
            self.collision_manager.add_object(obj)
        else:
            print("object doesnt implements updaate and render methods")

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
