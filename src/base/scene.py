from abc import ABC

import pygame


class Scene(ABC):
    def __init__(self, *args, **kwargs) -> None:
        pass

    def enter(self, **kwargs): ...
    def exit(self, **kwargs): ...
    def handle_event(self, event: pygame.Event): ...
    def load(self, **kwargs): ...
    def update(self, dt: float): ...
    def render(self, screen: pygame.Surface): ...


class SceneManager:
    def __init__(self):
        self.current_scene: Scene | None = None

    def change_scene(self, scene: Scene, **kwargs):
        if self.current_scene is not None:
            self.current_scene.exit()

        self.current_scene = scene
        self.current_scene.enter()
        scene.load(**kwargs)

    def update(self, dt: float):
        if self.current_scene is not None:
            self.current_scene.update(dt)

    def render(self, surface: pygame.Surface):
        if self.current_scene is not None:
            self.current_scene.render(surface)
