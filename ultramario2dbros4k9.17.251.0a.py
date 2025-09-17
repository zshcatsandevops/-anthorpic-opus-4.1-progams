import pygame
import sys
import random
from enum import IntEnum
from functools import lru_cache

# Initialize Pygame
pygame.init()

# Constants - OPTIMIZED FOR 600x400
SCREEN_WIDTH = 600
SCREEN_HEIGHT = 400
TILE_SIZE = 24
FPS = 60

# NES Color Palette (converted to tuples once)
class Colors:
    SKY_BLUE = (107, 140, 255)
    BROWN = (139, 69, 19)
    RED = (184, 0, 0)
    GREEN = (0, 168, 0)
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    YELLOW = (248, 208, 0)
    ORANGE = (248, 128, 0)
    LIGHT_GREEN = (136, 208, 88)
    DARK_GREEN = (0, 100, 0)
    PATH_COLOR = (216, 184, 92)
    PURPLE = (128, 0, 128)
    FLAME_ORANGE = (248, 88, 0)
    FLAME_YELLOW = (248, 216, 0)
    MARIO_RED = (216, 40, 0)
    MARIO_BLUE = (0, 0, 184)
    MARIO_BROWN = (136, 64, 0)
    MARIO_SKIN = (255, 180, 180)

# Game physics
GRAVITY = 0.6
PLAYER_SPEED = 4
JUMP_POWER = -14
ENEMY_SPEED = 1.5
MAX_VEL_Y = 10

# Game states using IntEnum for faster comparisons
class GameState(IntEnum):
    OVERWORLD = 0
    PLAYING = 1
    LEVEL_COMPLETE = 2
    GAME_OVER = 3
    WIN = 4

# Set up the display
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("ULTRA MARIO 2D BROS")
clock = pygame.time.Clock()

# Font loading with fallback
try:
    font = pygame.font.Font("prstart.ttf", 12)
    title_font = pygame.font.Font("prstart.ttf", 28)
except:
    font = pygame.font.SysFont("Arial", 12, bold=True)
    title_font = pygame.font.SysFont("Arial", 28, bold=True)

# Surface Cache - Create surfaces once and reuse
class SurfaceCache:
    def __init__(self):
        self.surfaces = {}
        self._create_all_surfaces()
    
    def _create_all_surfaces(self):
        """Pre-create all game surfaces for optimal performance"""
        # Block surface
        block = pygame.Surface((TILE_SIZE, TILE_SIZE)).convert()
        block.fill(Colors.BROWN)
        pygame.draw.rect(block, (101, 67, 33), (0, 0, TILE_SIZE, TILE_SIZE), 2)
        pygame.draw.rect(block, (160, 82, 45), (3, 3, TILE_SIZE-6, TILE_SIZE-6))
        self.surfaces['block'] = block
        
        # Question block
        qblock = pygame.Surface((TILE_SIZE, TILE_SIZE)).convert()
        qblock.fill(Colors.YELLOW)
        pygame.draw.rect(qblock, (180, 150, 0), (0, 0, TILE_SIZE, TILE_SIZE), 2)
        pygame.draw.rect(qblock, (220, 180, 0), (3, 3, TILE_SIZE-6, TILE_SIZE-6))
        pygame.draw.rect(qblock, (248, 216, 0), (6, 6, TILE_SIZE-12, TILE_SIZE-12))
        pygame.draw.rect(qblock, (180, 150, 0), (9, 9, TILE_SIZE-18, TILE_SIZE-18))
        # Question mark
        pygame.draw.rect(qblock, Colors.BLACK, (10, 7, 3, 9))
        pygame.draw.rect(qblock, Colors.BLACK, (7, 10, 9, 3))
        pygame.draw.rect(qblock, Colors.BLACK, (10, 16, 3, 3))
        self.surfaces['question_block'] = qblock
        
        # Ground surface
        ground = pygame.Surface((TILE_SIZE, TILE_SIZE)).convert()
        ground.fill(Colors.BROWN)
        pygame.draw.rect(ground, (101, 67, 33), (0, 0, TILE_SIZE, TILE_SIZE), 2)
        pygame.draw.line(ground, (101, 67, 33), (0, TILE_SIZE-3), (TILE_SIZE, TILE_SIZE-3), 2)
        self.surfaces['ground'] = ground
        
        # Pipe surface
        pipe = pygame.Surface((TILE_SIZE*2, TILE_SIZE*2)).convert()
        pipe.fill(Colors.GREEN)
        pygame.draw.rect(pipe, (0, 100, 0), (0, 0, TILE_SIZE*2, TILE_SIZE*2), 2)
        pygame.draw.rect(pipe, (0, 128, 0), (3, 3, TILE_SIZE*2-6, TILE_SIZE*2-6))
        self.surfaces['pipe'] = pipe
        
        # Goomba surface
        goomba = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA).convert_alpha()
        pygame.draw.ellipse(goomba, Colors.BROWN, (1, 1, TILE_SIZE-2, TILE_SIZE-2))
        pygame.draw.ellipse(goomba, Colors.BLACK, (6, 6, 3, 3))
        pygame.draw.ellipse(goomba, Colors.BLACK, (15, 6, 3, 3))
        pygame.draw.arc(goomba, Colors.BLACK, (7, 12, 9, 6), 0, 3.14, 2)
        pygame.draw.ellipse(goomba, (250, 200, 150), (4, 18, 5, 3))
        pygame.draw.ellipse(goomba, (250, 200, 150), (15, 18, 5, 3))
        self.surfaces['goomba'] = goomba
        
        # Koopa surface
        koopa = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA).convert_alpha()
        pygame.draw.ellipse(koopa, (0, 150, 0), (1, 1, TILE_SIZE-2, TILE_SIZE-2))
        pygame.draw.ellipse(koopa, (0, 100, 0), (4, 4, TILE_SIZE-8, TILE_SIZE-8))
        pygame.draw.ellipse(koopa, (0, 180, 0), (6, 1, 12, 9))
        pygame.draw.ellipse(koopa, Colors.BLACK, (9, 4, 3, 3))
        pygame.draw.ellipse(koopa, Colors.BLACK, (15, 4, 3, 3))
        pygame.draw.ellipse(koopa, (0, 180, 0), (3, 15, 6, 4))
        pygame.draw.ellipse(koopa, (0, 180, 0), (15, 15, 6, 4))
        self.surfaces['koopa'] = koopa
        
        # Coin surface
        coin = pygame.Surface((TILE_SIZE//2, TILE_SIZE), pygame.SRCALPHA).convert_alpha()
        pygame.draw.ellipse(coin, Colors.YELLOW, (0, 3, TILE_SIZE//2, TILE_SIZE-6))
        pygame.draw.ellipse(coin, (220, 180, 0), (1, 4, TILE_SIZE//2-2, TILE_SIZE-8))
        self.surfaces['coin'] = coin
        
        # Mario surface
        mario = self._create_mario_surface()
        self.surfaces['mario'] = mario
        
        # Flag surface
        flag = pygame.Surface((TILE_SIZE, TILE_SIZE*4), pygame.SRCALPHA).convert_alpha()
        pygame.draw.rect(flag, (200, 200, 200), (10, 0, 3, TILE_SIZE*4))
        pygame.draw.polygon(flag, Colors.RED, [(10, 0), (10, 15), (22, 7)])
        self.surfaces['flag'] = flag
        
        # Grass surface
        grass = pygame.Surface((TILE_SIZE, TILE_SIZE)).convert()
        grass.fill(Colors.LIGHT_GREEN)
        for _ in range(5):
            x = random.randint(1, TILE_SIZE-1)
            y = random.randint(1, TILE_SIZE-1)
            pygame.draw.line(grass, Colors.DARK_GREEN, (x, y), (x, y-2), 1)
        self.surfaces['grass'] = grass
        
        # Path surface
        path = pygame.Surface((TILE_SIZE, TILE_SIZE)).convert()
        path.fill(Colors.PATH_COLOR)
        self.surfaces['path'] = path
        
        # Flame particle
        particle = pygame.Surface((3, 3), pygame.SRCALPHA).convert_alpha()
        pygame.draw.circle(particle, Colors.FLAME_YELLOW, (1, 1), 1)
        self.surfaces['flame'] = particle
    
    def _create_mario_surface(self):
        """Create Mario sprite with proper NES style"""
        mario = pygame.Surface((TILE_SIZE, TILE_SIZE*2), pygame.SRCALPHA).convert_alpha()
        
        # Optimized drawing using direct rect calls
        rects = [
            (Colors.MARIO_RED, (4, 3, 16, 8)),      # Hat
            (Colors.MARIO_SKIN, (4, 11, 16, 8)),    # Face
            (Colors.BLACK, (8, 13, 2, 2)),          # Left eye
            (Colors.BLACK, (14, 13, 2, 2)),         # Right eye
            (Colors.BLACK, (8, 15, 8, 2)),          # Mustache
            (Colors.MARIO_BROWN, (4, 3, 4, 2)),     # Left hair
            (Colors.MARIO_BROWN, (16, 3, 4, 2)),    # Right hair
            (Colors.MARIO_BLUE, (4, 19, 16, 12)),   # Overalls
            (Colors.YELLOW, (11, 24, 2, 2)),        # Button
            (Colors.MARIO_SKIN, (2, 19, 3, 6)),     # Left arm
            (Colors.MARIO_SKIN, (19, 19, 3, 6)),    # Right arm
            (Colors.MARIO_BLUE, (6, 31, 4, 9)),     # Left leg
            (Colors.MARIO_BLUE, (14, 31, 4, 9)),    # Right leg
            (Colors.BLACK, (4, 40, 8, 4)),          # Left shoe
            (Colors.BLACK, (12, 40, 8, 4)),         # Right shoe
        ]
        
        for color, rect in rects:
            pygame.draw.rect(mario, color, rect)
        
        return mario
    
    def get(self, name):
        """Get cached surface by name"""
        return self.surfaces.get(name)

# Initialize surface cache
surface_cache = SurfaceCache()

# Optimized sprite classes with better collision detection
class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = surface_cache.get('mario')
        self.rect = self.image.get_rect(topleft=(x, y))
        self.vel_x = 0
        self.vel_y = 0
        self.on_ground = False
        self.direction = 1
        self.coins_collected = 0
        self.enemies_defeated = 0
        
        # Collision optimization - smaller rect for more accurate collisions
        self.collision_rect = pygame.Rect(x+4, y+4, TILE_SIZE-8, TILE_SIZE*2-8)

    def update(self, tiles, enemies, coins, flag):
        # Apply gravity with terminal velocity
        self.vel_y = min(self.vel_y + GRAVITY, MAX_VEL_Y)

        # Move horizontally
        self.rect.x += self.vel_x
        self.collision_rect.x = self.rect.x + 4
        self._check_horizontal_collisions(tiles)

        # Move vertically
        self.rect.y += self.vel_y
        self.collision_rect.y = self.rect.y + 4
        self.on_ground = False
        self._check_vertical_collisions(tiles)

        # Check enemy collisions (optimized with early exit)
        for enemy in enemies:
            if self.collision_rect.colliderect(enemy.rect):
                if self.vel_y > 0 and self.rect.bottom < enemy.rect.centery:
                    enemy.kill()
                    self.vel_y = -6
                    self.enemies_defeated += 1
                    return (GameState.PLAYING, 0, 200)
                else:
                    return (GameState.GAME_OVER, 0, 0)

        # Check coin collisions
        coins_hit = pygame.sprite.spritecollide(self, coins, True)
        if coins_hit:
            self.coins_collected += len(coins_hit)
            return (GameState.PLAYING, len(coins_hit) * 100, 0)

        # Check flag collision
        if self.rect.colliderect(flag.rect):
            return (GameState.LEVEL_COMPLETE, 0, 0)

        # Check if fell off
        if self.rect.top > SCREEN_HEIGHT:
            return (GameState.GAME_OVER, 0, 0)

        return (GameState.PLAYING, 0, 0)

    def _check_horizontal_collisions(self, tiles):
        for tile in tiles:
            if self.collision_rect.colliderect(tile.rect):
                if self.vel_x > 0:
                    self.rect.right = tile.rect.left + 4
                    self.collision_rect.right = tile.rect.left
                elif self.vel_x < 0:
                    self.rect.left = tile.rect.right - 4
                    self.collision_rect.left = tile.rect.right
                break  # Early exit after first collision

    def _check_vertical_collisions(self, tiles):
        for tile in tiles:
            if self.collision_rect.colliderect(tile.rect):
                if self.vel_y > 0:
                    self.rect.bottom = tile.rect.top + 4
                    self.collision_rect.bottom = tile.rect.top
                    self.vel_y = 0
                    self.on_ground = True
                elif self.vel_y < 0:
                    self.rect.top = tile.rect.bottom - 4
                    self.collision_rect.top = tile.rect.bottom
                    self.vel_y = 0
                break  # Early exit

class Tile(pygame.sprite.Sprite):
    __slots__ = ['image', 'rect']  # Memory optimization
    
    def __init__(self, x, y, surface):
        super().__init__()
        self.image = surface
        self.rect = self.image.get_rect(topleft=(x, y))

class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, enemy_type="goomba"):
        super().__init__()
        self.image = surface_cache.get(enemy_type)
        self.rect = self.image.get_rect(topleft=(x, y))
        self.direction = -1
        self.speed = ENEMY_SPEED
        self.enemy_type = enemy_type
        
        # Pre-calculate edge check offsets
        self.edge_offset = 3

    def update(self, tiles):
        # Move
        self.rect.x += self.direction * self.speed

        # Optimized collision and edge detection
        for tile in tiles:
            if self.rect.colliderect(tile.rect):
                self.direction *= -1
                return

        # Edge detection with cached offset
        check_x = self.rect.left if self.direction < 0 else self.rect.right
        check_rect = pygame.Rect(check_x, self.rect.bottom + self.edge_offset, 1, 1)

        if not any(check_rect.colliderect(tile.rect) for tile in tiles):
            self.direction *= -1

class Coin(pygame.sprite.Sprite):
    __slots__ = ['image', 'rect']
    
    def __init__(self, x, y):
        super().__init__()
        self.image = surface_cache.get('coin')
        self.rect = self.image.get_rect(topleft=(x, y))

class Flag(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = surface_cache.get('flag')
        self.rect = self.image.get_rect(bottomleft=(x, y))

class LevelNode(pygame.sprite.Sprite):
    def __init__(self, x, y, level_num):
        super().__init__()
        self.image = pygame.Surface((TILE_SIZE*2, TILE_SIZE*2), pygame.SRCALPHA).convert_alpha()
        pygame.draw.rect(self.image, Colors.PURPLE, (0, 0, TILE_SIZE*2, TILE_SIZE*2), border_radius=6)
        pygame.draw.rect(self.image, (180, 100, 220), (3, 3, TILE_SIZE*2-6, TILE_SIZE*2-6), border_radius=5)
        
        level_text = font.render(str(level_num), True, Colors.WHITE)
        text_rect = level_text.get_rect(center=(TILE_SIZE, TILE_SIZE))
        self.image.blit(level_text, text_rect)
        
        self.rect = self.image.get_rect(center=(x, y))
        self.level_num = level_num

class FlameParticle(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = surface_cache.get('flame')
        self.rect = self.image.get_rect(center=(x, y))
        self.vel_x = random.uniform(-1, 1)
        self.vel_y = random.uniform(-3, -1)
        self.lifetime = random.randint(15, 30)

    def update(self):
        self.rect.x += self.vel_x
        self.rect.y += self.vel_y
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.kill()

# Optimized Game class
class Game:
    def __init__(self):
        self.score = 0
        self.lives = 3
        self.level = 1
        self.max_level = 8
        self.game_state = GameState.OVERWORLD
        self.initial_coin_count = 0
        self.flame_particles = pygame.sprite.Group()
        
        # Pre-create text surfaces that don't change often
        self._create_static_texts()
        self.create_overworld()
    
    def _create_static_texts(self):
        """Pre-render static text for better performance"""
        self.title_text = title_font.render("ULTRA MARIO 2D BROS", True, Colors.RED)
        self.instructions_text = font.render("ARROWS: NAVIGATE  ENTER: SELECT", True, Colors.WHITE)
        
        # Game state messages
        self.game_over_text = font.render("GAME OVER", True, Colors.WHITE)
        self.out_of_lives_text = font.render("OUT OF LIVES", True, Colors.WHITE)
        self.level_complete_text = font.render("LEVEL COMPLETE!", True, Colors.WHITE)
        self.you_win_text = font.render("YOU WIN!", True, Colors.WHITE)
        self.press_enter_text = font.render("PRESS ENTER", True, Colors.WHITE)
        
        # Create overlay surface once
        self.overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.overlay.fill((0, 0, 0, 150))

    def create_overworld(self):
        self.overworld_sprites = pygame.sprite.Group()
        self.level_nodes = pygame.sprite.Group()

        # Pre-calculated positions
        grass_positions = [(x, y) for x in range(0, SCREEN_WIDTH, TILE_SIZE) 
                          for y in range(SCREEN_HEIGHT - TILE_SIZE*2, SCREEN_HEIGHT, TILE_SIZE)
                          if (x // TILE_SIZE) % 2 == 0 and (y // TILE_SIZE) % 2 == 0]
        
        for x, y in grass_positions:
            tile = Tile(x, y, surface_cache.get('grass'))
            self.overworld_sprites.add(tile)

        # Create path
        path_points = [
            (80, 350), (160, 350), (160, 280), (240, 280),
            (240, 220), (320, 220), (320, 280), (400, 280),
            (400, 220), (480, 220), (480, 280), (560, 280)
        ]

        # Optimized path creation
        for i in range(len(path_points)-1):
            start_x, start_y = path_points[i]
            end_x, end_y = path_points[i+1]

            if start_x == end_x:  # Vertical
                for y in range(start_y, end_y, TILE_SIZE if start_y < end_y else -TILE_SIZE):
                    self.overworld_sprites.add(Tile(start_x, y, surface_cache.get('path')))
            else:  # Horizontal
                for x in range(start_x, end_x, TILE_SIZE if start_x < end_x else -TILE_SIZE):
                    self.overworld_sprites.add(Tile(x, start_y, surface_cache.get('path')))

        # Create level nodes
        level_positions = [
            (80, 350), (160, 280), (240, 220), (320, 280),
            (400, 220), (480, 280), (560, 280)
        ]

        for i, pos in enumerate(level_positions):
            node = LevelNode(pos[0], pos[1], i+1)
            self.level_nodes.add(node)
            self.overworld_sprites.add(node)

        # Create player
        self.overworld_player = Player(80, 350 - TILE_SIZE*2)
        self.overworld_sprites.add(self.overworld_player)
        
        self.level_nodes_list = list(self.level_nodes)  # Cache for faster access
        self.current_node = 1

    def reset_level(self):
        self.all_sprites = pygame.sprite.Group()
        self.tiles = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.coins = pygame.sprite.Group()

        # Calculate level width
        self.level_width = SCREEN_WIDTH * (1 + self.level // 2)

        # Generate level with optimized loops
        ground_tiles = []
        for x in range(0, self.level_width, TILE_SIZE):
            ground_tiles.append(Tile(x, SCREEN_HEIGHT - TILE_SIZE, surface_cache.get('ground')))
            
            # Platform generation with reduced random calls
            if x > SCREEN_WIDTH//2 and x < self.level_width - SCREEN_WIDTH//2:
                rand_val = random.random()
                if rand_val < 0.2:
                    height = random.randint(3, 5)
                    y_start = SCREEN_HEIGHT - TILE_SIZE * height
                    
                    for y in range(y_start, SCREEN_HEIGHT - TILE_SIZE, TILE_SIZE):
                        ground_tiles.append(Tile(x, y, surface_cache.get('block')))
                    
                    # Add coins and enemies
                    if random.random() < 0.7:
                        self.coins.add(Coin(x + TILE_SIZE//4, y_start - TILE_SIZE//2))
                    
                    if random.random() < 0.4:
                        enemy_type = "koopa" if self.level > 3 else "goomba"
                        self.enemies.add(Enemy(x, y_start - TILE_SIZE, enemy_type))
        
        self.tiles.add(ground_tiles)

        # Add pipes
        pipe_x = SCREEN_WIDTH + 100
        self.tiles.add(Tile(pipe_x, SCREEN_HEIGHT - TILE_SIZE*2, surface_cache.get('pipe')))

        # Add question blocks
        for x in range(SCREEN_WIDTH//2, self.level_width - SCREEN_WIDTH//2, 150):
            if random.random() < 0.6:
                y = SCREEN_HEIGHT - TILE_SIZE * random.randint(3, 4)
                self.tiles.add(Tile(x, y, surface_cache.get('question_block')))
                
                if random.random() < 0.5:
                    self.coins.add(Coin(x + TILE_SIZE//4, y - TILE_SIZE))

        # Add flag
        self.flag = Flag(self.level_width - 80, SCREEN_HEIGHT - TILE_SIZE)
        self.all_sprites.add(self.tiles, self.enemies, self.coins, self.flag)

        # Create player
        self.player = Player(50, SCREEN_HEIGHT - TILE_SIZE * 3)
        self.all_sprites.add(self.player)

        self.camera_x = 0
        self.initial_coin_count = len(self.coins)

    def handle_input(self, event):
        """Centralized input handling for cleaner code"""
        if event.type == pygame.KEYDOWN:
            if self.game_state == GameState.OVERWORLD:
                if event.key == pygame.K_RIGHT and self.current_node < len(self.level_nodes):
                    self.current_node += 1
                    self._move_overworld_player()
                elif event.key == pygame.K_LEFT and self.current_node > 1:
                    self.current_node -= 1
                    self._move_overworld_player()
                elif event.key == pygame.K_RETURN:
                    self.level = self.current_node
                    self.reset_level()
                    self.game_state = GameState.PLAYING

            elif self.game_state == GameState.PLAYING:
                if event.key == pygame.K_LEFT:
                    self.player.vel_x = -PLAYER_SPEED
                    self.player.direction = -1
                elif event.key == pygame.K_RIGHT:
                    self.player.vel_x = PLAYER_SPEED
                    self.player.direction = 1
                elif event.key == pygame.K_SPACE and self.player.on_ground:
                    self.player.vel_y = JUMP_POWER
                elif event.key == pygame.K_ESCAPE:
                    self.game_state = GameState.OVERWORLD

            elif self.game_state in [GameState.GAME_OVER, GameState.LEVEL_COMPLETE, GameState.WIN]:
                if event.key == pygame.K_RETURN:
                    self._handle_game_state_transition()

        elif event.type == pygame.KEYUP:
            if event.key in [pygame.K_LEFT, pygame.K_RIGHT] and self.game_state == GameState.PLAYING:
                self.player.vel_x = 0

    def _move_overworld_player(self):
        """Move player to current node position"""
        if self.current_node <= len(self.level_nodes_list):
            node = self.level_nodes_list[self.current_node-1]
            self.overworld_player.rect.centerx = node.rect.centerx
            self.overworld_player.rect.bottom = node.rect.top

    def _handle_game_state_transition(self):
        """Handle transitions between game states"""
        if self.game_state == GameState.GAME_OVER:
            self.lives -= 1
            if self.lives > 0:
                self.reset_level()
                self.game_state = GameState.PLAYING
        elif self.game_state == GameState.LEVEL_COMPLETE:
            self.score += (self.initial_coin_count - len(self.coins)) * 100
            self.score += self.player.enemies_defeated * 200
            if self.level < self.max_level:
                self.game_state = GameState.OVERWORLD
                self.current_node = min(self.current_node + 1, len(self.level_nodes))
                self._move_overworld_player()
            else:
                self.game_state = GameState.WIN
        elif self.game_state == GameState.WIN:
            self.__init__()

    def update(self):
        """Update game logic"""
        if self.game_state == GameState.PLAYING:
            # Update player
            result = self.player.update(self.tiles, self.enemies, self.coins, self.flag)
            game_state, coin_points, enemy_points = result
            
            self.score += coin_points + enemy_points
            
            if game_state != GameState.PLAYING:
                self.game_state = game_state
            
            # Update enemies
            self.enemies.update(self.tiles)
            
            # Update camera
            self.camera_x = max(0, min(
                self.player.rect.centerx - SCREEN_WIDTH // 2,
                self.level_width - SCREEN_WIDTH
            ))

        # Update flame particles
        if random.random() < 0.3:
            self.flame_particles.add(FlameParticle(
                random.randint(0, SCREEN_WIDTH),
                SCREEN_HEIGHT
            ))
        self.flame_particles.update()

    def draw(self):
        """Optimized drawing with reduced function calls"""
        if self.game_state == GameState.OVERWORLD:
            screen.fill(Colors.SKY_BLUE)
            screen.blit(self.title_text, (SCREEN_WIDTH//2 - self.title_text.get_width()//2, 15))
            self.overworld_sprites.draw(screen)
            self.flame_particles.draw(screen)
            screen.blit(self.instructions_text, 
                       (SCREEN_WIDTH//2 - self.instructions_text.get_width()//2, 80))
        else:
            screen.fill(Colors.SKY_BLUE)
            
            # Draw sprites with camera offset (batch where possible)
            for sprite in self.all_sprites:
                screen.blit(sprite.image, (sprite.rect.x - self.camera_x, sprite.rect.y))

        self.draw_ui()
        
        if self.game_state not in [GameState.PLAYING, GameState.OVERWORLD]:
            self.draw_message()

    def draw_ui(self):
        """Draw UI elements with cached text where possible"""
        # Dynamic text that changes frequently
        score_text = font.render(f"SCORE: {self.score}", True, Colors.WHITE)
        screen.blit(score_text, (15, 15))
        
        lives_text = font.render(f"LIVES: {self.lives}", True, Colors.WHITE)
        screen.blit(lives_text, (15, 35))
        
        if self.game_state == GameState.OVERWORLD:
            level_text = font.render(f"LEVEL: {self.current_node}", True, Colors.WHITE)
            coins = self.overworld_player.coins_collected
        else:
            level_text = font.render(f"WORLD 1-{self.level}", True, Colors.WHITE)
            coins = self.player.coins_collected
        
        screen.blit(level_text, (SCREEN_WIDTH - 120, 15))
        
        coins_text = font.render(f"COINS: {coins}", True, Colors.WHITE)
        screen.blit(coins_text, (SCREEN_WIDTH - 120, 35))

    def draw_message(self):
        """Draw game state messages using cached surfaces"""
        screen.blit(self.overlay, (0, 0))
        
        if self.game_state == GameState.GAME_OVER:
            text = self.game_over_text if self.lives > 0 else self.out_of_lives_text
        elif self.game_state == GameState.LEVEL_COMPLETE:
            text = self.level_complete_text
        elif self.game_state == GameState.WIN:
            text = self.you_win_text
        else:
            return
        
        text_x = SCREEN_WIDTH // 2 - text.get_width() // 2
        screen.blit(text, (text_x, SCREEN_HEIGHT // 2 - 40))
        
        restart_x = SCREEN_WIDTH // 2 - self.press_enter_text.get_width() // 2
        screen.blit(self.press_enter_text, (restart_x, SCREEN_HEIGHT // 2 + 10))

    def run(self):
        """Main game loop"""
        running = True
        
        while running:
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                else:
                    self.handle_input(event)
            
            # Update
            self.update()
            
            # Draw
            self.draw()
            
            # Flip display and maintain framerate
            pygame.display.flip()
            clock.tick(FPS)
        
        pygame.quit()
        sys.exit()

# Start the game
if __name__ == "__main__":
    game = Game()
    game.run()
