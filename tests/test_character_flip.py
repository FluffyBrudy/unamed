import pygame
import pytest
from tilemap_parser import RectangleShape

from src.entities.knight import Soilder
from src.loader import LevelData, SharedData


@pytest.fixture(scope="module")
def initialized_game():
    pygame.init()
    surface = pygame.display.set_mode((800, 600))
    SharedData().preload()
    LevelData().preload("untitled.json")
    yield surface
    pygame.quit()


def test_character_base_tile_size_and_flip_consistency(initialized_game):
    soldier = Soilder(1560.2, 178.257)
    assert soldier.base_tile_size == (192, 192)

    # In idle state (192x192)
    soldier.current_state = "idle"
    soldier.flip_character_shape(True)
    shape_idle_flipped = soldier.collision_shape
    assert isinstance(shape_idle_flipped, RectangleShape)

    # In heavy_attack1 state (672x210 frame size)
    soldier.current_state = "heavy_attack1"
    soldier.flip_character_shape(True)
    shape_attack_flipped = soldier.collision_shape
    assert isinstance(shape_attack_flipped, RectangleShape)

    # Both flipped shapes must have the exact same offset (anchored to base_tile_size)
    assert shape_idle_flipped.offset == shape_attack_flipped.offset

    # Unflipping restores original collision shape
    soldier.flip_character_shape(False)
    assert soldier.collision_shape == soldier.original_collision_shape


def test_soilder_flipping_while_attacking_maintains_y_position(initialized_game):
    soldier = Soilder(1560.2, 178.25720608559953)
    soldier.on_ground = True
    initial_y = soldier.y

    # Enter pressed (attack mode)
    soldier.keys_pressed[pygame.K_RETURN] = True
    soldier.update(1 / 60)
    assert soldier.current_state == "heavy_attack1"

    # Alternate flipping left and right for 60 frames
    for step in range(60):
        if step % 6 == 0:
            turn_left = (step // 6) % 2 == 0
            soldier.keys_pressed[pygame.K_LEFT] = turn_left
            soldier.keys_pressed[pygame.K_RIGHT] = not turn_left
        soldier.update(1 / 60)

    # Verify y has not exploded and character stays grounded
    assert soldier.on_ground is True
    assert soldier.vy == 0.0
    assert abs(soldier.y - initial_y) < 1.0
