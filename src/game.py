import sys

import pygame

from src.base.scene import SceneManager
from src.loader import SharedData
from src.scenes.level_scene import LevelScene


class Game:
    WIDTH = 1280
    HEIGHT = 720
    FPS = 60
    TITLE = "Pygame"
    BG_COLOR = (30, 30, 30)

    def __init__(self) -> None:
        self.running = True
        self._init()

    def _init(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT))
        pygame.display.set_caption(self.TITLE)
        self.clock = pygame.time.Clock()

        SharedData().preload()
        self.scene_manager = SceneManager()
        self.scene_manager.change_scene(LevelScene(), vw=self.WIDTH, vh=self.HEIGHT)

    def handle_event(self) -> None:
        if self.scene_manager.current_scene is None:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
            return
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            self.scene_manager.current_scene.handle_event(event)

    def update(self, dt: float) -> None:
        self.scene_manager.update(dt)

    def render(self) -> None:
        self.screen.fill(self.BG_COLOR)
        self.scene_manager.render(self.screen)
        pygame.display.flip()

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(self.FPS) / 1000.0

            self.handle_event()

            self.update(dt)
            self.render()

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    Game().run()
