import pygame
from tilemap_parser import Camera

from src.base.scene import Scene
from src.entities.soilder import Soilder
from src.loader import LevelData, SharedData


class LevelScene(Scene):
    def enter(self, **kwargs):
        return super().enter(**kwargs)

    def load(self, **kwargs):
        LevelData().preload(f"{kwargs.get('level', 'untitled')}.json")
        SharedData().preload(render_scale=LevelData().level_render_scale)

        self.tile_layer_renderer = LevelData().tile_layer_renderer

        self.player = Soilder(*LevelData().entities["dark_knight"][0])
        self.camera = LevelData().camera
        self.camera.follow(self.player)

    def can_transition(self, **kwargs):
        return False

    def update(self, dt: float):
        self.player.update(dt)
        self.camera.update(dt)

    def handle_event(self, event: pygame.Event):
        self.player.handle_event(event)

    def render(self, screen: pygame.Surface):
        self.tile_layer_renderer.render(screen, self.camera.offset)
        self.player.render(screen, self.camera.offset)
