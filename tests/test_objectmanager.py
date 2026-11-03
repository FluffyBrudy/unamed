from src.objectmanager import ObjectManager


class FakeWorldObject:
    def __init__(self) -> None:
        self.killed = True

    def can_kill(self):
        return self.killed

    def can_hurt(self):
        return False

    def update(self, dt):
        pass

    def render(self, surface, offset):
        pass


def test_update_cleans_up_objects():
    manager = ObjectManager()
    obj = FakeWorldObject()
    manager.add_object(obj)
    manager.update(0.016)
    assert len(ObjectManager().collision_manager.objects) == 0 and len(ObjectManager().object_container) == 0
