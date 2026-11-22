import typing
from collections import defaultdict
from math import ceil

import pygame
from pygame import Surface
from pygame.typing import Point
from pygkit.debug import Debug
from pygkit.parallax import ParallaxBackground, ParallaxLayer
from tilemap_parser import (
    Camera,
    CharacterCollision,
    CharacterHitboxes,
    CollisionRunner,
    PhysicsWorld,
    SpriteAnimationSet,
    TileLayerRenderer,
    TilemapData,
    get_cached_character_hitboxes,
    load_map,
)
from tilemap_parser.parser import load_tileset_collision
from tilemap_parser.runtime import clear_collision_cache
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
        self.loaded_once = False
        self.debug = Debug()

    def preload(self, render_scale: float = 1.0):
        if self.loaded_once:
            if abs(self.render_scale - render_scale) < 0.1:
                return
        else:
            # room for sounds
            self.loaded_once = True
            clear_collision_cache()
        self.render_scale = render_scale
        self.state_animations = self.load_state_animations()

        collisions = self.load_character_collisions()
        self.character_collisions: dict[str, CharacterCollision] = collisions["character_collisions"]
        self.character_hitboxes = collisions["hitbox_collisions"]

    def load_character_collisions(self):
        char_collision_path = ROOT / "data/character_collision"
        character_collisions: dict[str, CharacterCollision] = {}
        hitbox_collisions: dict[str, CharacterHitboxes] = {}
        for collision_path in char_collision_path.iterdir():
            if collision_path.suffixes[0] == ".collision":
                collision = get_cached_character_collision(
                    collision_path,
                    render_scale=self.render_scale,
                )
                assert collision is not None
                character_collisions[collision_path.stem] = collision
            elif collision_path.suffixes[0] == ".hitbox":
                anim_stem = collision_path.stem.removesuffix(".hitbox") + ".anim"
                collision = get_cached_character_hitboxes(
                    collision_path,
                    anim_library=self.state_animations[anim_stem].library,
                    render_scale=self.render_scale,
                )
                assert collision is not None
                hitbox_collisions[collision_path.stem] = collision
        return {"character_collisions": character_collisions, "hitbox_collisions": hitbox_collisions}

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


@singleton
class LevelData:
    def __init__(self) -> None:
        pass

    def preload(self, map_suffix: str):
        primary_surface = pygame.display.get_surface()
        if primary_surface is None:
            raise ValueError("Surface Uninitialized")

        data_path = ROOT / "data"
        mapdata = load_map(data_path / "maps" / f"{map_suffix}", offset_y=3)
        collision_tileset = load_tileset_collision(data_path / "collision/tileset.collision.json")

        if collision_tileset is None:
            raise ValueError("meow")

        self.physics_world = PhysicsWorld.from_map(mapdata, collision_tileset)
        self.collision_runner = CollisionRunner.from_world(self.physics_world)
        self.tile_layer_renderer = TileLayerRenderer(mapdata)
        self.camera = Camera(*primary_surface.size, mode="deadzone")
        self.level_render_scale = mapdata.render_scale

        self.camera.set_bounds_from_map(mapdata)

        self.entities: dict[str, list[Point]] = defaultdict(list)
        self._load_object_data(mapdata)
        self._load_parallax_data(mapdata)

        self.tilesize = mapdata.tile_size
        self.mapsize = mapdata.map_size
        self.tileset = mapdata.surfaces[0]

    def _load_object_data(self, mapdata: TilemapData):
        for layer in mapdata.get_layers(layer_type="object"):
            objects = mapdata.get_object_surfaces(layer.id, scaled=True)
            for surf, x, y, oid in objects:
                ttype = layer.objects[oid].ttype
                props = mapdata.parsed.tilesets[ttype].properties
                if layer.name == "entities":
                    if props.get("name") is not None:
                        self.entities[props["name"]].append((x, y))

    def _load_parallax_data(self, mapdata: TilemapData):
        parallax_layers: list[ParallaxLayer] = []
        i = 0

        surfaces = mapdata.get_image_layer_surfaces()
        for _, surf in surfaces:
            i += 0.1
            if surf is None:
                continue
            target_h = self.camera.viewport_h
            target_w = (surf.width / surf.height) * target_h
            surf = pygame.transform.scale(surf, (target_w, target_h))
            parallax_layer = ParallaxLayer(surf, factor=(i, 0))
            parallax_layers.append(parallax_layer)

        self.parallax = ParallaxBackground(parallax_layers)
