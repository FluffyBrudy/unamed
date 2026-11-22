import pygame
from pygkit.lighting import RGB_MIN, LightMap
from pygkit.lighting.blend import RGB_ADD, RGB_SUB
from tilemap_parser import Camera

from src.base.scene import Scene
from src.entities.demonbat import DemonBat
from src.entities.knight import Knight
from src.lib.collision_registry import default_player_enemy_collision
from src.lightening import GlowSprite
from src.loader import LevelData, SharedData
from src.objectmanager import ObjectManager
from src.settings import DEFAULT_ENEMY_EID, KNIGHT_EID


class LevelScene(Scene):
    def enter(self, **kwargs):
        return super().enter(**kwargs)

    def load(self, **kwargs):
        LevelData().preload(f"{kwargs.get('level', 'untitled')}.json")
        SharedData().preload(render_scale=LevelData().level_render_scale)

        self.tile_layer_renderer = LevelData().tile_layer_renderer
        self.parallax = LevelData().parallax

        self.player = Knight(*LevelData().entities["dark_knight"][0])
        self.camera = LevelData().camera
        self.camera.follow(self.player)
        SharedData().debug.set_camera(self.camera)

        self.object_manager = ObjectManager()
        self.object_manager.add_object(self.player, hitbox_state=self.player.hitbox_state)
        self.glows: list[GlowSprite] = []
        self.load_entity()

        LevelData().unload()

        self.lightmap = LightMap((self.camera.viewport_w, self.camera.viewport_h))
        self.lightmap.set_ambient((177, 217, 155), 0.3)

    def load_entity(self):
        self.object_manager.register_handler(
            KNIGHT_EID,
            DEFAULT_ENEMY_EID,
            default_player_enemy_collision,  # type: ignore
        )

        for entity, coors in LevelData().entities.items():
            for x, y in coors:
                print(entity)
                if entity == "demon_bat":
                    demon_bat = DemonBat(x, y, self.player)
                    self.object_manager.add_object(demon_bat)

        for rf, rb in LevelData().light_pole_positions:
            rb.midtop = rf.midtop
            radius = 80
            self.glows.append(GlowSprite(rb.x - 31 - radius // 2, rb.y + 18 - radius, radius))

    def can_transition(self, **kwargs):
        return False

    def update(self, dt: float):
        self.object_manager.update(dt)
        self.camera.update(dt)

    def handle_event(self, event: pygame.Event):
        self.player.handle_event(event)

    def render(self, screen: pygame.Surface):
        self.parallax.render(screen, *self.camera.offset)
        self.tile_layer_renderer.render(screen, self.camera.offset)
        self.lightmap.apply(screen, blend=RGB_SUB)
        self.object_manager.render(screen, self.camera.offset)
        for pole in self.glows:
            pole.render(screen, self.camera.offset)
