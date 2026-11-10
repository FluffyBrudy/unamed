from abc import ABC, abstractmethod
from collections.abc import Callable

import pygame


class Scene(ABC):
    def __init__(self, *args, **kwargs) -> None:
        pass

    @abstractmethod
    def can_transition(self, **kwargs) -> bool: ...
    def enter(self, **kwargs): ...
    def exit(self, **kwargs): ...
    def handle_event(self, event: pygame.Event): ...
    def load(self, **kwargs): ...
    def update(self, dt: float): ...
    def render(self, screen: pygame.Surface): ...


class SceneManager:
    def __init__(self):
        self.scene_queue: list[tuple[Callable[[], Scene], dict]] = []
        self.current_scene: Scene | None = None
        self.is_paused = False

    def pause_scene(self):
        if self.current_scene is not None:
            self.is_paused = True
        else:
            print("nothing to pause")

    def resume_scene(self):
        if self.current_scene is not None:
            self.is_paused = False
        else:
            print("nothing to resume")

    def queue_scene(self, scene: Callable[[], Scene], **kwargs):
        self.scene_queue.append((scene, kwargs))

    def change_scene(self, scene: Scene, **kwargs):
        if self.current_scene is not None:
            self.current_scene.exit()

        self.current_scene = scene
        self.current_scene.enter()
        scene.load(**kwargs)

    def update(self, dt: float):
        if self.current_scene is not None:
            if self.current_scene.can_transition() and len(self.scene_queue) > 0:
                scene, kwargs = self.scene_queue.pop(0)
                self.change_scene(scene(), **kwargs)
            if not self.is_paused:
                self.current_scene.update(dt)

    def render(self, surface: pygame.Surface):
        if self.current_scene is not None:
            self.current_scene.render(surface)
