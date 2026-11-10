"""Tests for src.base.scene.SceneManager queue behavior.

The queue holds (factory, handoff_kwargs) transition requests built by
queue_scene(); update() pops the first request only when the current scene
allows a transition.
"""

from src.base.scene import Scene, SceneManager


class FakeScene(Scene):
    """Logs every lifecycle call into one shared list so order is assertable."""

    def __init__(self, name: str, can_transition: bool, log: list[str]) -> None:
        super().__init__()
        self.name = name
        self._can_transition = can_transition
        self.log = log
        self.load_kwargs: dict | None = None
        self.update_calls: list[float] = []

    def can_transition(self, **kwargs) -> bool:
        return self._can_transition

    def enter(self, **kwargs) -> None:
        self.log.append(f"{self.name}.enter")

    def exit(self, **kwargs) -> None:
        self.log.append(f"{self.name}.exit")

    def load(self, **kwargs) -> None:
        self.load_kwargs = kwargs
        self.log.append(f"{self.name}.load")

    def update(self, dt: float) -> None:
        self.log.append("update")
        self.update_calls.append(dt)


def test_update_without_current_scene_is_a_no_op():
    log: list[str] = []
    manager = SceneManager()
    manager.queue_scene(lambda: FakeScene("queued", True, log))

    manager.update(0.016)

    assert len(manager.scene_queue) == 1  # untouched; nothing current to transition from
    assert log == []


def test_transition_pops_first_queued_scene_in_fifo_order():
    log: list[str] = []
    manager = SceneManager()
    current = FakeScene("menu", True, log)
    manager.change_scene(current)
    log.clear()
    manager.queue_scene(lambda: FakeScene("level1", True, log))
    manager.queue_scene(lambda: FakeScene("level2", True, log))

    manager.update(0.016)

    assert manager.current_scene.name == "level1"
    assert len(manager.scene_queue) == 1  # level2 still queued, level1 popped
    assert log == [
        "menu.exit",
        "level1.enter",
        "level1.load",
        "update",
    ]
    assert manager.current_scene.load_kwargs == {}  # handoff channel exists even when empty


def test_queue_scene_forwards_handoff_kwargs_to_popped_scene():
    log: list[str] = []
    manager = SceneManager()
    manager.change_scene(FakeScene("menu", True, log))
    log.clear()
    manager.queue_scene(
        lambda: FakeScene("level1", True, log),
        level="1",
        carried_health=40,
    )

    manager.update(0.016)

    assert manager.current_scene.load_kwargs == {"level": "1", "carried_health": 40}


def test_scene_that_cannot_transition_keeps_queue_intact():
    log: list[str] = []
    manager = SceneManager()
    manager.change_scene(FakeScene("menu", False, log))
    log.clear()
    manager.queue_scene(lambda: FakeScene("level1", True, log))

    manager.update(0.016)

    assert manager.current_scene.name == "menu"
    assert len(manager.scene_queue) == 1
    assert log == ["update"]  # current scene updated, nothing else


def test_can_transition_without_queue_changes_nothing():
    log: list[str] = []
    manager = SceneManager()
    menu = FakeScene("menu", True, log)  # allows transition, but queue is empty
    manager.change_scene(menu)
    log.clear()

    manager.update(0.016)

    assert manager.current_scene is menu
    assert log == ["update"]
