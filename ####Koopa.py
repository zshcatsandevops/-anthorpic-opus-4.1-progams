import pygame
import sys
import math
import random
import json
from pygame.locals import *
from enum import Enum

# Constants
SCALE = 2
TILE = 16
WIDTH = int(400 * SCALE)
HEIGHT = int(240 * SCALE)
FPS = 60

# SMB3 NES Palette
SMB3_PALETTE = [
    (0, 0, 0), (252, 252, 252), (248, 248, 248), (188, 188, 188),
    (124, 124, 124), (64, 64, 64), (0, 0, 252), (0, 120, 248),
    (0, 188, 252), (104, 216, 252), (184, 248, 252), (0, 0, 188),
    (0, 88, 248), (0, 144, 252), (104, 168, 252), (0, 252, 252),
    (0, 252, 0), (0, 188, 0), (0, 144, 0), (88, 216, 0),
    (184, 248, 24), (248, 216, 0), (252, 184, 0), (248, 120, 0),
    (252, 60, 0), (252, 0, 0), (188, 0, 0), (124, 0, 0),
    (252, 0, 252), (248, 88, 152), (252, 120, 120), (252, 160, 68),
    (252, 184, 184), (252, 216, 120), (252, 252, 184), (216, 252, 120),
    (184, 252, 184), (184, 252, 252), (120, 216, 252), (120, 184, 252),
    (152, 120, 248), (216, 120, 252), (252, 120, 252), (252, 160, 252),
    (252, 216, 252), (164, 228, 252), (184, 184, 252), (216, 184, 248)
]

# Power-up states (SMB3 style)
class PowerState(Enum):
    SMALL = 0
    BIG = 1
    FIRE = 2
    RACCOON = 3
    FROG = 4
    HAMMER = 5
    TANOOKI = 6

# Game State
class GameState:
    def __init__(self):
        self.lives = 5
        self.coins = 0
        self.score = 0
        self.power_state = PowerState.SMALL
        self.p_meter = 0  # SMB3 P-meter for running/flying
        self.world = 1
        self.level = 1
        self.inventory = []  # SMB3 style item inventory
        self.cards = []  # End level cards (mushroom, flower, star)
        self.completed_levels = set()
        self.unlocked_worlds = [1]
        self.koopa_coins = 0  # Special currency
        
state = GameState()

# Scene management
SCENES = []
def push(scene): SCENES.append(scene)
def pop(): SCENES.pop() if SCENES else None
def clear(): SCENES.clear()

class Scene:
    def handle(self, events, keys): pass
    def update(self, dt): pass
    def draw(self, surf): pass

# World Themes (All Koopa Themed)
WORLD_THEMES = {
    1: {"name": "KOOPA GRASSLANDS", "sky": 15, "ground": 17, "music": "overworld"},
    2: {"name": "KOOPA DESERT", "sky": 31, "ground": 30, "music": "desert"},
    3: {"name": "KOOPA BEACH", "sky": 14, "ground": 15, "music": "water"},
    4: {"name": "GIANT KOOPA LAND", "sky": 11, "ground": 18, "music": "giant"},
    5: {"name": "SKY KOOPA KINGDOM", "sky": 37, "ground": 36, "music": "sky"},
    6: {"name": "ICE KOOPA CAVERN", "sky": 38, "ground": 39, "music": "ice"},
    7: {"name": "PIPE KOOPA MAZE", "sky": 10, "ground": 19, "music": "pipe"},
    8: {"name": "KOOPA CASTLE", "sky": 25, "ground": 26, "music": "castle"},
    9: {"name": "STAR KOOPA ROAD", "sky": 0, "ground": 44, "music": "star"}  # Bonus world
}

# Different Koopa Types for variety
class KoopaType(Enum):
    GREEN = 0      # Basic walking
    RED = 1        # Smart, doesn't fall off edges
    BLUE = 2       # Can kick shells
    YELLOW = 3     # Follows player
    PARA = 4       # Flying koopa
    HAMMER = 5     # Hammer Brother
    FIRE = 6       # Fire Brother
    BOOMERANG = 7  # Boomerang Brother
    SLEDGE = 8     # Heavy Hammer Brother
    LAKITU = 9     # Cloud riding, throws spinies
    MAGIKOOPA = 10 # Magic attacks
    BOOM_BOOM = 11 # Mini boss

# Enhanced Entity System
class Entity:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = 0
        self.vy = 0
        self.width = TILE
        self.height = TILE
        self.on_ground = False
        self.in_water = False
        self.facing_right = True
        self.active = True
        self.animation_timer = 0
        self.frame = 0
        
    def get_rect(self):
        return pygame.Rect(self.x, self.y, self.width, self.height)
        
    def check_collision(self, other):
        return self.get_rect().colliderect(other.get_rect())
        
    def apply_physics(self, dt, gravity=0.5):
        if not self.on_ground and not self.in_water:
            self.vy += gravity * dt * 60
        elif self.in_water:
            self.vy *= 0.95  # Water resistance
            
        self.x += self.vx * dt * 60
        self.y += self.vy * dt * 60
        
    def check_collisions(self, colliders):
        self.on_ground = False
        rect = self.get_rect()
        
        for collider in colliders:
            if rect.colliderect(collider):
                # Bottom collision
                if self.vy > 0 and rect.bottom > collider.top and rect.top < collider.top:
                    self.y = collider.top - self.height
                    self.vy = 0
                    self.on_ground = True
                # Top collision  
                elif self.vy < 0 and rect.top < collider.bottom and rect.bottom > collider.bottom:
                    self.y = collider.bottom
                    self.vy = 0
                # Right collision
                if self.vx > 0 and rect.right > collider.left and rect.left < collider.left:
                    self.x = collider.left - self.width
                    self.vx = 0
                # Left collision
                elif self.vx < 0 and rect.left < collider.right and rect.right > collider.right:
                    self.x = collider.right
                    self.vx = 0

# Player Class - A Heroic Koopa!
class KoopaPlayer(Entity):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.width = TILE
        self.height = TILE if state.power_state == PowerState.SMALL else TILE * 2
        self.run_speed = 2.5
        self.walk_speed = 1.5
        self.jump_power = -6
        self.super_jump_power = -8  # With P-meter full
        self.p_meter_charge = 0
        self.can_fly = False
        self.fly_timer = 0
        self.tail_spinning = False
        self.tail_spin_timer = 0
        self.invincible_timer = 0
        self.shell_sliding = False
        
    def update(self, dt, keys, colliders, enemies):
        # Handle input
        moving = False
        
        # Horizontal movement
        if keys[K_LEFT]:
            self.facing_right = False
            if keys[K_LSHIFT] or keys[K_z]:  # Run button
                self.vx = -self.run_speed
                self.p_meter_charge = min(self.p_meter_charge + dt, 1.0)
            else:
                self.vx = -self.walk_speed
                self.p_meter_charge = max(self.p_meter_charge - dt * 2, 0)
            moving = True
        elif keys[K_RIGHT]:
            self.facing_right = True
            if keys[K_LSHIFT] or keys[K_z]:  # Run button
                self.vx = self.run_speed
                self.p_meter_charge = min(self.p_meter_charge + dt, 1.0)
            else:
                self.vx = self.walk_speed
                self.p_meter_charge = max(self.p_meter_charge - dt * 2, 0)
            moving = True
        else:
            self.vx *= 0.9  # Friction
            self.p_meter_charge = max(self.p_meter_charge - dt * 3, 0)
            
        # Jumping and flying
        if keys[K_SPACE] or keys[K_x]:
            if self.on_ground:
                if self.p_meter_charge >= 0.9:
                    self.vy = self.super_jump_power
                    if state.power_state == PowerState.RACCOON:
                        self.can_fly = True
                        self.fly_timer = 2.0  # Can fly for 2 seconds
                else:
                    self.vy = self.jump_power
            elif self.can_fly and self.fly_timer > 0:
                self.vy = -3  # Flying upward
                self.fly_timer -= dt
                
        # Tail spin (Raccoon/Tanooki power)
        if (keys[K_LCTRL] or keys[K_c]) and state.power_state in [PowerState.RACCOON, PowerState.TANOOKI]:
            self.tail_spinning = True
            self.tail_spin_timer = 0.3
            self.vy = min(self.vy, 1)  # Slow fall
            
        if self.tail_spin_timer > 0:
            self.tail_spin_timer -= dt
        else:
            self.tail_spinning = False
            
        # Shell slide (when small)
        if keys[K_DOWN] and state.power_state == PowerState.SMALL and abs(self.vx) > 1:
            self.shell_sliding = True
            self.height = TILE // 2
        else:
            self.shell_sliding = False
            self.height = TILE if state.power_state == PowerState.SMALL else TILE * 2
            
        # Update physics
        self.apply_physics(dt)
        self.check_collisions(colliders)
        
        # Update invincibility
        if self.invincible_timer > 0:
            self.invincible_timer -= dt
            
        # Check enemy collisions
        for enemy in enemies:
            if enemy.active and self.check_collision(enemy):
                if self.shell_sliding:
                    enemy.active = False
                    state.score += 200
                elif self.tail_spinning and isinstance(enemy, Koopa):
                    enemy.flip()
                    state.score += 100
                elif self.vy > 0 and self.y < enemy.y:  # Jumping on enemy
                    enemy.active = False
                    self.vy = self.jump_power / 2
                    state.score += 100
                elif self.invincible_timer <= 0:
                    self.take_damage()
                    
        # Update animation
        if moving:
            self.animation_timer += dt
            if self.animation_timer > 0.1:
                self.animation_timer = 0
                self.frame = (self.frame + 1) % 4
        else:
            self.frame = 0
            
        # Reset fly ability when landing
        if self.on_ground:
            self.can_fly = False
            self.fly_timer = 0
            
    def take_damage(self):
        if state.power_state != PowerState.SMALL:
            state.power_state = PowerState(state.power_state.value - 1) if state.power_state.value > 1 else PowerState.SMALL
            self.invincible_timer = 2.0
        else:
            state.lives -= 1
            if state.lives <= 0:
                push(GameOverScene())
            else:
                self.respawn()
                
    def respawn(self):
        self.x = 50
        self.y = 100
        self.vx = 0
        self.vy = 0
        state.power_state = PowerState.SMALL
        
    def draw(self, surf, cam):
        if self.invincible_timer > 0 and int(self.invincible_timer * 10) % 2 == 0:
            return  # Flashing invincibility
            
        x = int(self.x - cam)
        y = int(self.y)
        
        # Draw based on power state
        if state.power_state == PowerState.SMALL:
            # Small Koopa Hero
            pygame.draw.ellipse(surf, SMB3_PALETTE[17], (x+2, y+4, 12, 10))  # Green shell
            if not self.shell_sliding:
                pygame.draw.circle(surf, SMB3_PALETTE[31], (x+8, y+2), 4)  # Head
                
        elif state.power_state == PowerState.BIG:
            # Big Koopa
            pygame.draw.ellipse(surf, SMB3_PALETTE[17], (x+2, y+12, 14, 14))  # Shell
            pygame.draw.circle(surf, SMB3_PALETTE[31], (x+8, y+4), 6)  # Head
            pygame.draw.rect(surf, SMB3_PALETTE[31], (x+4, y+20, 3, 6))  # Left leg
            pygame.draw.rect(surf, SMB3_PALETTE[31], (x+10, y+20, 3, 6))  # Right leg
            
        elif state.power_state == PowerState.FIRE:
            # Fire Koopa
            pygame.draw.ellipse(surf, SMB3_PALETTE[24], (x+2, y+12, 14, 14))  # Red shell
            pygame.draw.circle(surf, SMB3_PALETTE[31], (x+8, y+4), 6)  # Head
            # Draw fire on shell
            pygame.draw.circle(surf, SMB3_PALETTE[25], (x+8, y+18), 2)
            
        elif state.power_state == PowerState.RACCOON:
            # Raccoon Koopa
            pygame.draw.ellipse(surf, SMB3_PALETTE[30], (x+2, y+12, 14, 14))  # Brown shell
            pygame.draw.circle(surf, SMB3_PALETTE[31], (x+8, y+4), 6)  # Head
            # Draw tail
            if self.tail_spinning:
                angle = self.tail_spin_timer * 20
                tail_x = x + 14 + math.cos(angle) * 8
                tail_y = y + 18 + math.sin(angle) * 4
                pygame.draw.circle(surf, SMB3_PALETTE[30], (int(tail_x), int(tail_y)), 3)
            else:
                pygame.draw.ellipse(surf, SMB3_PALETTE[30], (x+14, y+16, 8, 4))
                
        # Draw P-meter
        if self.p_meter_charge > 0:
            meter_width = int(self.p_meter_charge * 20)
            pygame.draw.rect(surf, SMB3_PALETTE[0], (x-2, y-8, 24, 4))
            pygame.draw.rect(surf, SMB3_PALETTE[25], (x, y-6, meter_width, 2))
            if self.p_meter_charge >= 0.9:
                pygame.draw.rect(surf, SMB3_PALETTE[1], (x+20, y-7, 3, 3))  # P

# Enemy Koopa Classes
class Koopa(Entity):
    def __init__(self, x, y, koopa_type=KoopaType.GREEN):
        super().__init__(x, y)
        self.koopa_type = koopa_type
        self.in_shell = False
        self.shell_timer = 0
        self.shell_spinning = False
        self.patrol_speed = 0.8
        self.vx = -self.patrol_speed
        
        # Type-specific attributes
        if koopa_type == KoopaType.PARA:
            self.can_fly = True
            self.wing_flap = 0
            self.hover_height = y
            
        elif koopa_type == KoopaType.HAMMER:
            self.throw_timer = 0
            self.hammers = []
            
    def update(self, dt, colliders):
        if self.in_shell:
            self.shell_timer -= dt
            if self.shell_timer <= 0:
                self.in_shell = False
                self.height = TILE
                
        if not self.in_shell:
            # Type-specific behavior
            if self.koopa_type == KoopaType.GREEN:
                # Basic walking
                self.vx = -self.patrol_speed if not self.facing_right else self.patrol_speed
                
            elif self.koopa_type == KoopaType.RED:
                # Smart - doesn't fall off edges
                edge_check = pygame.Rect(
                    self.x + (self.width if self.vx > 0 else -1),
                    self.y + self.height + 1,
                    1, 1
                )
                edge_found = False
                for collider in colliders:
                    if edge_check.colliderect(collider):
                        edge_found = True
                        break
                if not edge_found and self.on_ground:
                    self.vx *= -1
                    self.facing_right = not self.facing_right
                    
            elif self.koopa_type == KoopaType.PARA:
                # Flying pattern
                self.wing_flap += dt * 5
                self.y = self.hover_height + math.sin(self.wing_flap) * 20
                
            elif self.koopa_type == KoopaType.HAMMER:
                # Throw hammers periodically
                self.throw_timer += dt
                if self.throw_timer > 1.5:
                    self.throw_hammer()
                    self.throw_timer = 0
                    
        else:
            # Shell behavior
            if self.shell_spinning:
                self.vx *= 0.98  # Friction
                if abs(self.vx) < 0.1:
                    self.shell_spinning = False
                    
        self.apply_physics(dt)
        self.check_collisions(colliders)
        
        # Wall bounce
        old_x = self.x
        self.x += self.vx * dt * 60
        new_rect = self.get_rect()
        for collider in colliders:
            if new_rect.colliderect(collider):
                self.x = old_x
                self.vx *= -1
                self.facing_right = not self.facing_right
                break
                
    def flip(self):
        self.in_shell = True
        self.shell_timer = 5.0
        self.height = TILE // 2
        self.vx = 0
        
    def kick_shell(self, direction):
        if self.in_shell and not self.shell_spinning:
            self.shell_spinning = True
            self.vx = 5 * direction
            
    def throw_hammer(self):
        # Create hammer projectile
        pass
        
    def draw(self, surf, cam):
        if not self.active:
            return
            
        x = int(self.x - cam)
        y = int(self.y)
        
        # Color based on type
        shell_colors = {
            KoopaType.GREEN: SMB3_PALETTE[17],
            KoopaType.RED: SMB3_PALETTE[24],
            KoopaType.BLUE: SMB3_PALETTE[14],
            KoopaType.YELLOW: SMB3_PALETTE[22],
            KoopaType.PARA: SMB3_PALETTE[36],
            KoopaType.HAMMER: SMB3_PALETTE[0],
            KoopaType.FIRE: SMB3_PALETTE[25],
            KoopaType.BOOMERANG: SMB3_PALETTE[15]
        }
        
        shell_color = shell_colors.get(self.koopa_type, SMB3_PALETTE[17])
        
        if self.in_shell:
            # Draw just shell
            pygame.draw.ellipse(surf, shell_color, (x, y+4, 16, 12))
            # Shell pattern
            pygame.draw.arc(surf, SMB3_PALETTE[0], (x+2, y+5, 12, 10), 0, math.pi, 2)
        else:
            # Draw full koopa
            pygame.draw.ellipse(surf, shell_color, (x+1, y+8, 14, 12))  # Shell
            
            # Head
            pygame.draw.circle(surf, SMB3_PALETTE[31], (x+8, y+4), 5)
            
            # Eyes
            eye_offset = 0 if self.facing_right else 2
            pygame.draw.circle(surf, SMB3_PALETTE[0], (x+6+eye_offset, y+3), 1)
            pygame.draw.circle(surf, SMB3_PALETTE[0], (x+10-eye_offset, y+3), 1)
            
            # Feet
            foot_offset = int(self.animation_timer * 10) % 2 * 2
            pygame.draw.rect(surf, SMB3_PALETTE[31], (x+3, y+18, 3, 4))
            pygame.draw.rect(surf, SMB3_PALETTE[31], (x+11, y+18+foot_offset, 3, 4))
            
            # Wings for Para-Koopa
            if self.koopa_type == KoopaType.PARA:
                wing_offset = int(math.sin(self.wing_flap) * 3)
                pygame.draw.ellipse(surf, SMB3_PALETTE[1], (x-4, y+6+wing_offset, 6, 8))
                pygame.draw.ellipse(surf, SMB3_PALETTE[1], (x+14, y+6-wing_offset, 6, 8))
                
        self.animation_timer += 0.016  # ~60fps

# Overworld Map (Mario Forever Style)
class OverworldMap(Scene):
    def __init__(self):
        self.player_pos = [1, 1]  # Grid position
        self.camera = [0, 0]
        self.animation_timer = 0
        self.selected_level = None
        
        # Map layout - Mario Forever style with branching paths
        self.map_data = self.generate_map()
        self.path_connections = self.generate_paths()
        
    def generate_map(self):
        # Create a grid-based map with level nodes and paths
        map_width = 20
        map_height = 15
        
        map_grid = []
        for y in range(map_height):
            row = []
            for x in range(map_width):
                tile = "grass"
                
                # Place level nodes
                if (x + y) % 4 == 0 and x > 0 and x < map_width - 1:
                    if y < 5:
                        tile = f"level_{1}_{(x//4)+1}"  # World 1 levels
                    elif y < 10:
                        tile = f"level_{2}_{(x//4)+1}"  # World 2 levels
                    else:
                        tile = f"level_{3}_{(x//4)+1}"  # World 3 levels
                        
                # Paths
                elif (x + y) % 2 == 0:
                    tile = "path"
                    
                # Decorations
                elif random.random() < 0.1:
                    tile = random.choice(["tree", "rock", "flower"])
                    
                row.append(tile)
            map_grid.append(row)
            
        return map_grid
        
    def generate_paths(self):
        # Connect levels with paths
        connections = {}
        # Add path logic here
        return connections
        
    def handle(self, events, keys):
        for event in events:
            if event.type == KEYDOWN:
                # Movement on map
                if event.key == K_LEFT:
                    self.move_player(-1, 0)
                elif event.key == K_RIGHT:
                    self.move_player(1, 0)
                elif event.key == K_UP:
                    self.move_player(0, -1)
                elif event.key == K_DOWN:
                    self.move_player(0, 1)
                elif event.key == K_RETURN or event.key == K_SPACE:
                    self.enter_level()
                elif event.key == K_ESCAPE:
                    push(TitleScreen())
                    
    def move_player(self, dx, dy):
        new_x = self.player_pos[0] + dx
        new_y = self.player_pos[1] + dy
        
        # Check bounds
        if 0 <= new_x < len(self.map_data[0]) and 0 <= new_y < len(self.map_data):
            tile = self.map_data[new_y][new_x]
            if tile in ["path", "grass"] or tile.startswith("level_"):
                self.player_pos = [new_x, new_y]
                
    def enter_level(self):
        tile = self.map_data[self.player_pos[1]][self.player_pos[0]]
        if tile.startswith("level_"):
            parts = tile.split("_")
            world = int(parts[1])
            level = int(parts[2])
            state.world = world
            state.level = level
            push(LevelScene(world, level))
            
    def update(self, dt):
        self.animation_timer += dt
        
        # Update camera to follow player
        target_cam_x = self.player_pos[0] * TILE - WIDTH // 2
        target_cam_y = self.player_pos[1] * TILE - HEIGHT // 2
        
        self.camera[0] += (target_cam_x - self.camera[0]) * 0.1
        self.camera[1] += (target_cam_y - self.camera[1]) * 0.1
        
        # Clamp camera
        self.camera[0] = max(0, min(self.camera[0], len(self.map_data[0]) * TILE - WIDTH))
        self.camera[1] = max(0, min(self.camera[1], len(self.map_data) * TILE - HEIGHT))
        
    def draw(self, surf):
        # Draw sky gradient
        for i in range(HEIGHT):
            color_val = int(100 + i * 0.3)
            color = (min(color_val, 150), min(color_val + 50, 200), min(color_val + 100, 255))
            pygame.draw.line(surf, color, (0, i), (WIDTH, i))
            
        # Draw map tiles
        start_x = int(self.camera[0] // TILE)
        start_y = int(self.camera[1] // TILE)
        end_x = min(start_x + WIDTH // TILE + 2, len(self.map_data[0]))
        end_y = min(start_y + HEIGHT // TILE + 2, len(self.map_data))
        
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                if 0 <= y < len(self.map_data) and 0 <= x < len(self.map_data[0]):
                    tile = self.map_data[y][x]
                    draw_x = x * TILE - self.camera[0]
                    draw_y = y * TILE - self.camera[1]
                    
                    if tile == "grass":
                        pygame.draw.rect(surf, SMB3_PALETTE[17], (draw_x, draw_y, TILE, TILE))
                    elif tile == "path":
                        pygame.draw.rect(surf, SMB3_PALETTE[30], (draw_x, draw_y, TILE, TILE))
                        pygame.draw.circle(surf, SMB3_PALETTE[31], (draw_x + TILE//2, draw_y + TILE//2), 3)
                    elif tile.startswith("level_"):
                        # Draw level node
                        parts = tile.split("_")
                        world_num = parts[1]
                        
                        # Level platform
                        pygame.draw.rect(surf, SMB3_PALETTE[24], (draw_x-4, draw_y-4, TILE+8, TILE+8))
                        pygame.draw.rect(surf, SMB3_PALETTE[25], (draw_x, draw_y, TILE, TILE))
                        
                        # Level icon (mini castle/fort)
                        if parts[2] == "4":  # Castle level
                            pygame.draw.polygon(surf, SMB3_PALETTE[0], [
                                (draw_x+2, draw_y+12),
                                (draw_x+8, draw_y+4),
                                (draw_x+14, draw_y+12)
                            ])
                        else:  # Regular level
                            pygame.draw.rect(surf, SMB3_PALETTE[31], (draw_x+4, draw_y+4, 8, 8))
                            
                        # Check if completed
                        level_id = f"{world_num}-{parts[2]}"
                        if level_id in state.completed_levels:
                            # Draw flag
                            pygame.draw.rect(surf, SMB3_PALETTE[1], (draw_x+12, draw_y+2, 2, 10))
                            pygame.draw.polygon(surf, SMB3_PALETTE[24], [
                                (draw_x+14, draw_y+2),
                                (draw_x+20, draw_y+5),
                                (draw_x+14, draw_y+8)
                            ])
                    elif tile == "tree":
                        # Draw tree
                        pygame.draw.rect(surf, SMB3_PALETTE[30], (draw_x+6, draw_y+10, 4, 6))
                        pygame.draw.circle(surf, SMB3_PALETTE[17], (draw_x+8, draw_y+6), 6)
                    elif tile == "rock":
                        pygame.draw.ellipse(surf, SMB3_PALETTE[3], (draw_x+2, draw_y+8, 12, 8))
                    elif tile == "flower":
                        pygame.draw.rect(surf, SMB3_PALETTE[17], (draw_x+7, draw_y+10, 2, 6))
                        pygame.draw.circle(surf, SMB3_PALETTE[28], (draw_x+8, draw_y+8), 3)
                        
        # Draw player (Koopa hero on map)
        player_x = self.player_pos[0] * TILE - self.camera[0]
        player_y = self.player_pos[1] * TILE - self.camera[1]
        
        # Animated koopa
        bounce = math.sin(self.animation_timer * 5) * 2
        pygame.draw.ellipse(surf, SMB3_PALETTE[14], 
                          (player_x+2, player_y+4-bounce, 12, 10))
        pygame.draw.circle(surf, SMB3_PALETTE[31], 
                         (player_x+8, player_y+2-bounce), 4)
                         
        # HUD
        self.draw_hud(surf)
        
    def draw_hud(self, surf):
        # Top bar
        pygame.draw.rect(surf, SMB3_PALETTE[0], (0, 0, WIDTH, 30))
        pygame.draw.rect(surf, SMB3_PALETTE[11], (0, 28, WIDTH, 2))
        
        font = pygame.font.SysFont("Arial", 16, bold=True)
        
        # Lives
        lives_text = font.render(f"KOOPA x{state.lives}", True, SMB3_PALETTE[1])
        surf.blit(lives_text, (10, 6))
        
        # Coins
        coins_text = font.render(f"COINS: {state.coins}", True, SMB3_PALETTE[22])
        surf.blit(coins_text, (150, 6))
        
        # Score
        score_text = font.render(f"SCORE: {state.score:06d}", True, SMB3_PALETTE[1])
        surf.blit(score_text, (300, 6))
        
        # P-meter indicator
        if state.power_state != PowerState.SMALL:
            power_text = font.render(f"POWER: {state.power_state.name}", True, SMB3_PALETTE[25])
            surf.blit(power_text, (500, 6))
            
        # Cards collected
        if state.cards:
            cards_text = font.render(f"CARDS: {len(state.cards)}/3", True, SMB3_PALETTE[31])
            surf.blit(cards_text, (650, 6))

# Level Scene
class LevelScene(Scene):
    def __init__(self, world, level):
        self.world = world
        self.level = level
        self.player = KoopaPlayer(100, 100)
        self.enemies = []
        self.items = []
        self.blocks = []
        self.colliders = []
        self.camera = 0
        self.time_limit = 300
        self.level_width = 3200  # SMB3 style wider levels
        self.background_offset = 0
        
        # Generate level
        self.generate_level()
        
    def generate_level(self):
        # Create procedural level based on world theme
        theme = WORLD_THEMES[self.world]
        
        # Ground
        for x in range(0, self.level_width, TILE):
            # Variable ground height
            ground_height = HEIGHT - 100 + int(math.sin(x / 200) * 30)
            for y in range(ground_height, HEIGHT, TILE):
                rect = pygame.Rect(x, y, TILE, TILE)
                self.colliders.append(rect)
                
        # Platforms
        for i in range(20):
            x = random.randint(200, self.level_width - 200)
            y = random.randint(HEIGHT - 250, HEIGHT - 150)
            width = random.randint(3, 8) * TILE
            
            for px in range(x, x + width, TILE):
                rect = pygame.Rect(px, y, TILE, TILE)
                self.colliders.append(rect)
                
        # Question blocks and bricks
        for i in range(30):
            x = random.randint(100, self.level_width - 100)
            y = random.randint(HEIGHT - 300, HEIGHT - 180)
            block_type = random.choice(["?", "brick", "!"])  # ! is SMB3 style switch block
            self.blocks.append({"x": x, "y": y, "type": block_type, "hit": False})
            self.colliders.append(pygame.Rect(x, y, TILE, TILE))
            
        # Enemies - all Koopa variants
        for i in range(15 + self.level * 3):
            x = random.randint(300, self.level_width - 100)
            y = HEIGHT - 150
            
            # Variety of koopa types
            if self.world == 1:
                enemy_type = random.choice([KoopaType.GREEN, KoopaType.GREEN, KoopaType.RED])
            elif self.world == 2:
                enemy_type = random.choice([KoopaType.RED, KoopaType.YELLOW, KoopaType.PARA])
            elif self.world == 3:
                enemy_type = random.choice([KoopaType.BLUE, KoopaType.PARA, KoopaType.GREEN])
            elif self.world == 4:
                enemy_type = random.choice([KoopaType.HAMMER, KoopaType.RED, KoopaType.PARA])
            elif self.world == 5:
                enemy_type = random.choice([KoopaType.PARA, KoopaType.PARA, KoopaType.YELLOW])
            elif self.world == 6:
                enemy_type = random.choice([KoopaType.BLUE, KoopaType.RED, KoopaType.HAMMER])
            elif self.world == 7:
                enemy_type = random.choice([KoopaType.FIRE, KoopaType.BOOMERANG, KoopaType.HAMMER])
            else:  # World 8
                enemy_type = random.choice([KoopaType.HAMMER, KoopaType.FIRE, KoopaType.BOOMERANG, KoopaType.MAGIKOOPA])
                
            self.enemies.append(Koopa(x, y, enemy_type))
            
        # Goal card roulette at end (SMB3 style)
        self.goal_x = self.level_width - 100
        
    def handle(self, events, keys):
        for event in events:
            if event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    pop()  # Return to overworld
                    
    def update(self, dt):
        keys = pygame.key.get_pressed()
        
        # Update player
        self.player.update(dt, keys, self.colliders, self.enemies)
        
        # Update enemies
        for enemy in self.enemies:
            if enemy.active:
                enemy.update(dt, self.colliders)
                
        # Update camera (smooth follow)
        target_cam = self.player.x - WIDTH // 2
        self.camera += (target_cam - self.camera) * 0.1
        self.camera = max(0, min(self.camera, self.level_width - WIDTH))
        
        # Parallax background
        self.background_offset = self.camera * 0.3
        
        # Check block collisions
        player_rect = self.player.get_rect()
        for block in self.blocks:
            if not block["hit"]:
                block_rect = pygame.Rect(block["x"], block["y"], TILE, TILE)
                if player_rect.colliderect(block_rect) and self.player.vy < 0:
                    # Hit block from below
                    block["hit"] = True
                    self.player.vy = 0
                    
                    if block["type"] == "?":
                        # Spawn power-up
                        state.coins += 1
                        state.score += 200
                    elif block["type"] == "!":
                        # P-switch effect
                        pass
                        
        # Check if reached goal
        if self.player.x >= self.goal_x:
            # Level complete!
            state.completed_levels.add(f"{self.world}-{self.level}")
            
            # Get random card
            card = random.choice(["mushroom", "flower", "star"])
            state.cards.append(card)
            
            # Check for bonus
            if len(state.cards) >= 3:
                if state.cards[-3:] == ["star", "star", "star"]:
                    state.lives += 5
                elif state.cards[-3:] == ["mushroom", "mushroom", "mushroom"]:
                    state.lives += 2
                elif state.cards[-3:] == ["flower", "flower", "flower"]:
                    state.lives += 3
                else:
                    state.lives += 1
                state.cards = []
                
            pop()  # Return to overworld
            
        # Update timer
        self.time_limit -= dt
        if self.time_limit <= 0:
            self.player.take_damage()
            self.time_limit = 300
            
    def draw(self, surf):
        # Draw background layers (parallax)
        theme = WORLD_THEMES[self.world]
        
        # Sky
        surf.fill(SMB3_PALETTE[theme["sky"]])
        
        # Hills/mountains background
        for i in range(5):
            hill_x = i * 200 - self.background_offset % 200
            hill_y = HEIGHT - 200
            hill_width = 150
            hill_height = 100
            
            points = [
                (hill_x, HEIGHT),
                (hill_x + hill_width // 2, hill_y),
                (hill_x + hill_width, HEIGHT)
            ]
            pygame.draw.polygon(surf, SMB3_PALETTE[theme["ground"] - 3], points)
            
        # Clouds
        for i in range(10):
            cloud_x = i * 150 - (self.camera * 0.5) % 150
            cloud_y = 50 + (i % 3) * 30
            
            pygame.draw.ellipse(surf, SMB3_PALETTE[1], (cloud_x, cloud_y, 40, 20))
            pygame.draw.ellipse(surf, SMB3_PALETTE[1], (cloud_x+15, cloud_y-5, 35, 20))
            pygame.draw.ellipse(surf, SMB3_PALETTE[1], (cloud_x+25, cloud_y, 30, 18))
            
        # Draw level elements
        for collider in self.colliders:
            if collider.x - self.camera < -TILE or collider.x - self.camera > WIDTH:
                continue
                
            x = collider.x - self.camera
            y = collider.y
            
            # Ground tiles with pattern
            if y >= HEIGHT - 100:
                pygame.draw.rect(surf, SMB3_PALETTE[theme["ground"]], (x, y, TILE, TILE))
                # Grass on top
                if y < HEIGHT - 80:
                    pygame.draw.rect(surf, SMB3_PALETTE[17], (x, y, TILE, 3))
            else:
                # Platform blocks
                pygame.draw.rect(surf, SMB3_PALETTE[30], (x, y, TILE, TILE))
                pygame.draw.rect(surf, SMB3_PALETTE[31], (x+2, y+2, TILE-4, TILE-4))
                
        # Draw blocks
        for block in self.blocks:
            x = block["x"] - self.camera
            if x < -TILE or x > WIDTH:
                continue
                
            y = block["y"]
            
            if not block["hit"]:
                if block["type"] == "?":
                    # Question block
                    pygame.draw.rect(surf, SMB3_PALETTE[22], (x, y, TILE, TILE))
                    pygame.draw.rect(surf, SMB3_PALETTE[23], (x+2, y+2, TILE-4, TILE-4))
                    # ? mark
                    font = pygame.font.SysFont("Arial", 12, bold=True)
                    q_mark = font.render("?", True, SMB3_PALETTE[1])
                    surf.blit(q_mark, (x+5, y+2))
                elif block["type"] == "brick":
                    # Brick block
                    pygame.draw.rect(surf, SMB3_PALETTE[30], (x, y, TILE, TILE))
                    pygame.draw.line(surf, SMB3_PALETTE[31], (x, y+8), (x+TILE, y+8))
                    pygame.draw.line(surf, SMB3_PALETTE[31], (x+8, y), (x+8, y+8))
                    pygame.draw.line(surf, SMB3_PALETTE[31], (x+8, y+8), (x+8, y+TILE))
                elif block["type"] == "!":
                    # P-switch block
                    pygame.draw.rect(surf, SMB3_PALETTE[14], (x, y, TILE, TILE))
                    pygame.draw.rect(surf, SMB3_PALETTE[15], (x+2, y+2, TILE-4, TILE-4))
                    font = pygame.font.SysFont("Arial", 12, bold=True)
                    p_mark = font.render("P", True, SMB3_PALETTE[1])
                    surf.blit(p_mark, (x+5, y+2))
            else:
                # Hit block (empty)
                pygame.draw.rect(surf, SMB3_PALETTE[4], (x, y, TILE, TILE))
                
        # Draw enemies
        for enemy in self.enemies:
            if enemy.active:
                enemy.draw(surf, self.camera)
                
        # Draw player
        self.player.draw(surf, self.camera)
        
        # Draw goal
        goal_x = self.goal_x - self.camera
        if -50 < goal_x < WIDTH + 50:
            # Goal post
            pygame.draw.rect(surf, SMB3_PALETTE[3], (goal_x, HEIGHT - 200, 4, 100))
            # Card roulette box
            pygame.draw.rect(surf, SMB3_PALETTE[22], (goal_x - 20, HEIGHT - 220, 40, 30))
            pygame.draw.rect(surf, SMB3_PALETTE[1], (goal_x - 18, HEIGHT - 218, 36, 26))
            
            # Animated card
            card_types = ["🍄", "🌻", "⭐"]
            card_index = int(self.player.animation_timer * 5) % 3
            font = pygame.font.SysFont("Arial", 16)
            card_text = font.render(card_types[card_index], True, SMB3_PALETTE[0])
            surf.blit(card_text, (goal_x - 8, HEIGHT - 210))
            
        # Draw HUD
        self.draw_hud(surf)
        
    def draw_hud(self, surf):
        # Bottom info panel (SMB3 style)
        pygame.draw.rect(surf, SMB3_PALETTE[0], (0, HEIGHT - 40, WIDTH, 40))
        pygame.draw.rect(surf, SMB3_PALETTE[11], (0, HEIGHT - 42, WIDTH, 2))
        
        font = pygame.font.SysFont("Arial", 14, bold=True)
        
        # World-Level
        world_text = font.render(f"WORLD {self.world}-{self.level}", True, SMB3_PALETTE[1])
        surf.blit(world_text, (10, HEIGHT - 30))
        
        # Time
        time_color = SMB3_PALETTE[1] if self.time_limit > 50 else SMB3_PALETTE[24]
        time_text = font.render(f"TIME: {int(self.time_limit)}", True, time_color)
        surf.blit(time_text, (150, HEIGHT - 30))
        
        # Coins
        coin_text = font.render(f"COINS: {state.coins}", True, SMB3_PALETTE[22])
        surf.blit(coin_text, (280, HEIGHT - 30))
        
        # Score
        score_text = font.render(f"SCORE: {state.score:08d}", True, SMB3_PALETTE[1])
        surf.blit(score_text, (420, HEIGHT - 30))
        
        # Lives
        lives_text = font.render(f"KOOPAS: {state.lives}", True, SMB3_PALETTE[17])
        surf.blit(lives_text, (600, HEIGHT - 30))
        
        # P-meter bar
        if self.player.p_meter_charge > 0:
            meter_x = WIDTH - 150
            meter_y = HEIGHT - 30
            pygame.draw.rect(surf, SMB3_PALETTE[4], (meter_x, meter_y, 100, 10))
            pygame.draw.rect(surf, SMB3_PALETTE[25], (meter_x, meter_y, int(100 * self.player.p_meter_charge), 10))
            if self.player.p_meter_charge >= 0.9:
                p_text = font.render("P", True, SMB3_PALETTE[1])
                surf.blit(p_text, (meter_x + 105, meter_y - 2))

# Title Screen
class TitleScreen(Scene):
    def __init__(self):
        self.timer = 0
        self.logo_y = -100
        self.logo_target = HEIGHT // 2 - 80
        self.demo_timer = 0
        
    def handle(self, events, keys):
        for event in events:
            if event.type == KEYDOWN:
                if event.key in [K_RETURN, K_SPACE]:
                    push(OverworldMap())
                    
    def update(self, dt):
        self.timer += dt
        self.demo_timer += dt
        
        # Animate logo
        if self.logo_y < self.logo_target:
            self.logo_y += 3
            
    def draw(self, surf):
        # Animated gradient background
        for i in range(HEIGHT):
            val = int(abs(math.sin(self.timer + i * 0.01)) * 50)
            color = (val, val + 20, val + 80)
            pygame.draw.line(surf, color, (0, i), (WIDTH, i))
            
        # Main logo box
        box_width = 500
        box_height = 150
        box_x = (WIDTH - box_width) // 2
        box_y = self.logo_y
        
        # Box shadow
        pygame.draw.rect(surf, SMB3_PALETTE[0], (box_x + 5, box_y + 5, box_width, box_height))
        
        # Main box
        pygame.draw.rect(surf, SMB3_PALETTE[31], (box_x, box_y, box_width, box_height))
        pygame.draw.rect(surf, SMB3_PALETTE[22], (box_x + 5, box_y + 5, box_width - 10, box_height - 10))
        
        # Title text
        title_font = pygame.font.SysFont("Arial", 48, bold=True)
        title = title_font.render("KOOPA KINGDOM", True, SMB3_PALETTE[1])
        title_shadow = title_font.render("KOOPA KINGDOM", True, SMB3_PALETTE[0])
        surf.blit(title_shadow, (box_x + (box_width - title.get_width()) // 2 + 3, box_y + 20 + 3))
        surf.blit(title, (box_x + (box_width - title.get_width()) // 2, box_y + 20))
        
        subtitle_font = pygame.font.SysFont("Arial", 24)
        subtitle = subtitle_font.render("SUPER MARIO BROS 3 STYLE", True, SMB3_PALETTE[24])
        surf.blit(subtitle, (box_x + (box_width - subtitle.get_width()) // 2, box_y + 80))
        
        edition_font = pygame.font.SysFont("Arial", 18)
        edition = edition_font.render("All-Koopa Edition", True, SMB3_PALETTE[17])
        surf.blit(edition, (box_x + (box_width - edition.get_width()) // 2, box_y + 110))
        
        # Animated koopas parade
        for i in range(8):
            koopa_x = (i * 120 + self.demo_timer * 50) % (WIDTH + 100) - 50
            koopa_y = HEIGHT - 100 + math.sin(self.demo_timer * 3 + i) * 20
            
            # Different koopa types
            koopa_colors = [
                SMB3_PALETTE[17],  # Green
                SMB3_PALETTE[24],  # Red
                SMB3_PALETTE[14],  # Blue
                SMB3_PALETTE[22],  # Yellow
                SMB3_PALETTE[28],  # Purple (Magikoopa)
                SMB3_PALETTE[30],  # Brown (Hammer Bro)
                SMB3_PALETTE[25],  # Orange (Fire Bro)
                SMB3_PALETTE[15],  # Cyan (Boomerang Bro)
            ]
            
            # Draw koopa
            pygame.draw.ellipse(surf, koopa_colors[i % 8], (koopa_x, koopa_y + 5, 20, 15))
            pygame.draw.circle(surf, SMB3_PALETTE[31], (koopa_x + 10, koopa_y), 7)
            
            # Special features for different types
            if i % 8 == 4:  # Magikoopa
                # Wand
                pygame.draw.rect(surf, SMB3_PALETTE[22], (koopa_x + 18, koopa_y - 5, 10, 2))
                pygame.draw.circle(surf, SMB3_PALETTE[1], (koopa_x + 28, koopa_y - 4), 3)
            elif i % 8 == 5:  # Hammer Bro
                # Hammer
                pygame.draw.rect(surf, SMB3_PALETTE[4], (koopa_x + 18, koopa_y - 8, 8, 3))
                pygame.draw.rect(surf, SMB3_PALETTE[30], (koopa_x + 22, koopa_y - 12, 2, 8))
                
        # Press Start flashing
        if int(self.timer * 2) % 2 == 0:
            start_font = pygame.font.SysFont("Arial", 28, bold=True)
            start_text = start_font.render("PRESS ENTER TO START", True, SMB3_PALETTE[1])
            start_shadow = start_font.render("PRESS ENTER TO START", True, SMB3_PALETTE[0])
            surf.blit(start_shadow, (WIDTH // 2 - start_text.get_width() // 2 + 2, HEIGHT - 50 + 2))
            surf.blit(start_text, (WIDTH // 2 - start_text.get_width() // 2, HEIGHT - 50))
            
        # Copyright
        copy_font = pygame.font.SysFont("Arial", 12)
        copy_text = copy_font.render("© 2024 Koopa Productions - A SMB3 Tribute", True, SMB3_PALETTE[3])
        surf.blit(copy_text, (WIDTH // 2 - copy_text.get_width() // 2, HEIGHT - 20))

# Game Over Scene
class GameOverScene(Scene):
    def __init__(self):
        self.timer = 3
        
    def update(self, dt):
        self.timer -= dt
        if self.timer <= 0:
            clear()
            push(TitleScreen())
            
    def draw(self, surf):
        surf.fill(SMB3_PALETTE[0])
        
        font = pygame.font.SysFont("Arial", 48, bold=True)
        text = font.render("GAME OVER", True, SMB3_PALETTE[24])
        surf.blit(text, (WIDTH // 2 - text.get_width() // 2, HEIGHT // 2 - 50))
        
        score_font = pygame.font.SysFont("Arial", 24)
        score_text = score_font.render(f"Final Score: {state.score}", True, SMB3_PALETTE[1])
        surf.blit(score_text, (WIDTH // 2 - score_text.get_width() // 2, HEIGHT // 2 + 20))

# Main game loop
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Koopa Kingdom - Super Mario Bros 3 Style")
    clock = pygame.time.Clock()
    
    # Start with title screen
    push(TitleScreen())
    
    running = True
    while running and SCENES:
        dt = clock.tick(FPS) / 1000.0
        
        events = pygame.event.get()
        keys = pygame.key.get_pressed()
        
        for event in events:
            if event.type == QUIT:
                running = False
                
        # Update and draw current scene
        if SCENES:
            current_scene = SCENES[-1]
            current_scene.handle(events, keys)
            current_scene.update(dt)
            current_scene.draw(screen)
            
        pygame.display.flip()
        
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
