# -*- coding: utf-8 -*-
import os
import sys
from ursina import *
from ursina.shaders import lit_with_shadows_shader
from ursina.prefabs.first_person_controller import FirstPersonController
import opensimplex
import random
import math
from PIL import Image

# =====================
# CONFIGURATION
# =====================
def configure_environment():
    os.environ['PNMIMAGE_SUPPRESS_WARNINGS'] = '1'
    app = Ursina()
    window.title = "Procedural World"
    window.borderless = True
    window.fullscreen = False
    window.position = (0, 0)
    window.size = (1920, 1080)
    window.icon = None

# =====================
# PROCEDURAL CORE SYSTEMS
# =====================

class ProceduralWorld:
    def __init__(self):
        self.biome_map = {}
        self.loaded_chunks = {}
        self.chunk_pool = []  # Pool of reusable chunk entities
        self.noise_cache = {}  # Cache for noise values
        self.generate_biome_map()

    def generate_biome_map(self):
        points = [(random.uniform(-16, 16), random.uniform(-16, 16)) for _ in range(8)]
        for x in range(-32, 32):
            for z in range(-32, 32):
                closest = min(points, key=lambda p: math.dist((x, z), p))
                self.biome_map[(x, z)] = hash(closest) % 4

    def get_noise(self, x, z):
        if (x, z) not in self.noise_cache:
            self.noise_cache[(x, z)] = opensimplex.noise2(x / 20, z / 20) * 4
        return self.noise_cache[(x, z)]

    def generate_chunk(self, chunk_pos):
        chunk_entities = []
        for x in range(16):
            for z in range(16):
                wx = chunk_pos[0] * 16 + x
                wz = chunk_pos[1] * 16 + z
                biome = self.biome_map.get((wx // 4, wz // 4), 0)

                height = self.get_noise(wx, wz)
                detail = opensimplex.noise2(wx * 3, wz * 3) * 0.5
                y = height + detail
                color = self.get_biome_color(biome, y)

                # Ground block
                entity = self.get_chunk_entity()
                entity.model = 'cube'
                entity.position = (wx, y, wz)
                entity.color = color
                entity.scale = (1, 1, 1)
                entity.collider = 'box' if y <= 2 else None  # Only add colliders to ground
                chunk_entities.append(entity)

                # Trees
                if y > 2 and random.random() < 0.1:  # Increased tree density
                    self.generate_procedural_tree(wx, y + 1, wz)

        self.loaded_chunks[chunk_pos] = chunk_entities

    def get_chunk_entity(self):
        if self.chunk_pool:
            return self.chunk_pool.pop()
        return Entity()

    def unload_chunk(self, chunk_pos):
        if chunk_pos in self.loaded_chunks:
            for entity in self.loaded_chunks[chunk_pos]:
                entity.enabled = False  # Disable instead of destroying
                self.chunk_pool.append(entity)
            del self.loaded_chunks[chunk_pos]

    def get_biome_color(self, biome, y):
        biome_colors = {
            0: lerp(color.green, color.lime, y / 5),  # Forest
            1: lerp(color.orange, color.yellow, y / 5),  # Desert
            2: lerp(color.gray, color.white, y / 5),  # Mountain
            3: lerp(color.blue, color.cyan, y / 5)  # Water
        }
        return biome_colors.get(biome, color.white)

    def generate_procedural_tree(self, x, y, z):
        height = random.randint(3, 6)
        trunk = Entity(model='cube', position=(x, y, z),
                       color=color.brown, collider='box',
                       scale=(0.5, height, 0.5))
        for i in range(height):
            foliage_pos = (x, y + height - i, z)
            Entity(model='sphere', position=foliage_pos,
                   color=lerp(color.green, color.lime, i / height),
                   scale=2 - (i / height))

class GeneratedWeapon(Entity):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.model = 'cube'
        self.scale = (0.3, 0.2, 1)
        self.color = color.gray
        self.fire_mode = random.choice(['single', 'burst'])
        self.ammo = random.randint(30, 60)

# =====================
# MAIN GAME INIT
# =====================
if __name__ == '__main__':
    app = Ursina()

    # World Generation
    world = ProceduralWorld()
    player = FirstPersonController()
    player.gun = GeneratedWeapon(parent=camera, position=(0.5, -0.5, 1))

    # Chunk loading parameters
    chunk_size = 16
    render_distance = 4  # Number of chunks to load in each direction

    def get_chunk(pos):
        return (int(pos[0] // chunk_size), int(pos[2] // chunk_size))

    def update_chunks():
        player_chunk = get_chunk(player.position)
        for cx in range(player_chunk[0] - render_distance, player_chunk[0] + render_distance + 1):
            for cz in range(player_chunk[1] - render_distance, player_chunk[1] + render_distance + 1):
                if (cx, cz) not in world.loaded_chunks:
                    world.generate_chunk((cx, cz))
        # Unload chunks that are too far away
        for chunk_pos in list(world.loaded_chunks.keys()):
            if abs(chunk_pos[0] - player_chunk[0]) > render_distance or abs(chunk_pos[1] - player_chunk[1]) > render_distance:
                world.unload_chunk(chunk_pos)

    # Game Loop
    def update():
        if held_keys['left mouse'] and player.gun.ammo > 0:
            player.gun.ammo -= 1
        update_chunks()

    app.run()
