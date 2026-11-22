import pygame
from pygame import BLEND_RGBA_ADD
from pygame.surface import Surface
from pygkit.lighting import glow_sprite


class GlowSprite:
    def __init__(self, x: float, y: float, r: float = 20) -> None:
        self.x = x
        self.y = y
        self.glow_sprite = glow_sprite(int(r), (177, 217, 155), exponent=4)

    def render(self, surface: Surface, offset: tuple[float, float]):
        x, y = self.x - offset[0], self.y - offset[1]
        if -self.glow_sprite.width < x < surface.width or -self.glow_sprite.height < y < surface.height:
            self.glow_sprite.set_alpha(0)
            surface.blit(self.glow_sprite, (x, y), special_flags=BLEND_RGBA_ADD)
