import pygame
from tilemap_parser import Camera

from src.base.scene import Scene
from src.entities.demonbat import DemonBat
from src.entities.knight import Knight
from src.loader import LevelData, SharedData
from src.objectmanager import ObjectManager


class LevelScene(Scene):
    def enter(self, **kwargs):
        return super().enter(**kwargs)

    def load(self, **kwargs):
        LevelData().preload(f"{kwargs.get('level', 'untitled')}.json")
        SharedData().preload(render_scale=LevelData().level_render_scale)

        self.tile_layer_renderer = LevelData().tile_layer_renderer

        self.player = Knight(*LevelData().entities["dark_knight"][0])
        self.camera = LevelData().camera
        self.camera.follow(self.player)
        SharedData().debug.set_camera(self.camera)

        self.object_manager = ObjectManager()
        self.object_manager.add_object(self.player)
        self.load_entity()

    def load_entity(self):
        for entity, coors in LevelData().entities.items():
            for x, y in coors:
                print(entity)
                if entity == "demon_bat":
                    demon_bat = DemonBat(x, y, self.player)
                    self.object_manager.add_object(demon_bat)

    def can_transition(self, **kwargs):
        return False

    def update(self, dt: float):
        self.object_manager.update(dt)
        self.camera.update(dt)

    def handle_event(self, event: pygame.Event):
        self.player.handle_event(event)

    def render(self, screen: pygame.Surface):
        self.tile_layer_renderer.render(screen, self.camera.offset)
        self.object_manager.render(screen, self.camera.offset)
