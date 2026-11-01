import pygame
from pygame import Surface
from tilemap_parser import CharacterCollision, SpriteAnimationSet
from tilemap_parser.runtime.collision_cache import get_cached_character_collision

from src.settings import ROOT


def singleton(cls):
    instance = None

    def get_instance(*args, **kwargs):
        nonlocal instance
        if instance is None:
            instance = cls(*args, **kwargs)
        return instance

    return get_instance


@singleton
class SharedData:
    def __init__(self) -> None:
        self.render_scale = 1.0
        self.preloaded = False

    def preload(self, render_scale: float = 1.0):
        if self.preloaded and abs(self.render_scale - render_scale) < 0.1:
            return
        self.preloaded = True
        self.render_scale = render_scale
        self.state_animations = self.load_state_animations()
        self.character_collisions = self.load_character_collisions()

    def load_character_collisions(self):
        char_collision_path = ROOT / "character_collision"
        character_collisions: dict[str, CharacterCollision] = {}
        for collision_path in char_collision_path.iterdir():
            collision = get_cached_character_collision(
                collision_path,
                render_scale=self.render_scale,
            )
            assert collision is not None
            character_collisions[collision_path.stem] = collision
        return character_collisions

    def load_state_animations(self):
        state_anim_path = ROOT / "data/animations"
        state_animations: dict[str, SpriteAnimationSet] = {}
        for anim_path in state_anim_path.iterdir():
            if "tanim" in str(anim_path):
                continue
            state_animations[anim_path.stem] = SpriteAnimationSet.load(
                anim_path,
                render_scale=self.render_scale,
            )
        return state_animations

    def load_misc_images(self):
        misc_images_path = ROOT / "assets" / "misc"
        images: dict[str, Surface] = {}
        for image in misc_images_path.iterdir():
            images[image.stem] = pygame.transform.scale_by(
                pygame.image.load(image).convert_alpha(),
                self.render_scale,
            )
        return images
