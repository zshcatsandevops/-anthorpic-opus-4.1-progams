import pygame
import sys
import random

# Initialize Pygame
pygame.init()

# Constants - UPDATED FOR 600x400
SCREEN_WIDTH = 600
SCREEN_HEIGHT = 400
TILE_SIZE = 24  # Reduced tile size for 600x400 resolution
FPS = 60

# NES Color Palette
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
MARIO_BROWN = (136, 64, 0)  # For Mario's hair

# Game physics (NES-like but adjusted for 600x400)
GRAVITY = 0.6  # Slightly reduced gravity
PLAYER_SPEED = 4  # Slightly reduced speed
JUMP_POWER = -14  # Slightly reduced jump power
ENEMY_SPEED = 1.5  # Slightly reduced enemy speed

# Game states
STATE_OVERWORLD = 0
STATE_PLAYING = 1
STATE_LEVEL_COMPLETE = 2
STATE_GAME_OVER = 3
STATE_WIN = 4

# Set up the display
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("ULTRA MARIO 2D BROS")
clock = pygame.time.Clock()

# Try to load a pixel font, fall back to system font
try:
    font = pygame.font.Font("prstart.ttf", 12)  # Reduced font size
except:
    font = pygame.font.SysFont("Arial", 12, bold=True)

# Create surfaces for game elements (sizes based on TILE_SIZE=24)
def create_block_surface():
    block = pygame.Surface((TILE_SIZE, TILE_SIZE))
    block.fill(BROWN)
    pygame.draw.rect(block, (101, 67, 33), (0, 0, TILE_SIZE, TILE_SIZE), 2)
    pygame.draw.rect(block, (160, 82, 45), (3, 3, TILE_SIZE-6, TILE_SIZE-6))  # Adjusted inner rect
    return block

def create_question_block_surface():
    block = pygame.Surface((TILE_SIZE, TILE_SIZE))
    block.fill(YELLOW)
    pygame.draw.rect(block, (180, 150, 0), (0, 0, TILE_SIZE, TILE_SIZE), 2)
    pygame.draw.rect(block, (220, 180, 0), (3, 3, TILE_SIZE-6, TILE_SIZE-6))  # Adjusted
    pygame.draw.rect(block, (248, 216, 0), (6, 6, TILE_SIZE-12, TILE_SIZE-12))  # Adjusted
    pygame.draw.rect(block, (180, 150, 0), (9, 9, TILE_SIZE-18, TILE_SIZE-18))  # Adjusted
    # Add question mark (scaled down positions)
    pygame.draw.rect(block, BLACK, (10, 7, 3, 9))  # Eye
    pygame.draw.rect(block, BLACK, (7, 10, 9, 3))  # Mouth top
    pygame.draw.rect(block, BLACK, (10, 16, 3, 3))  # Mouth bottom
    return block

def create_ground_surface():
    ground = pygame.Surface((TILE_SIZE, TILE_SIZE))
    ground.fill(BROWN)
    pygame.draw.rect(ground, (101, 67, 33), (0, 0, TILE_SIZE, TILE_SIZE), 2)
    pygame.draw.line(ground, (101, 67, 33), (0, TILE_SIZE-3), (TILE_SIZE, TILE_SIZE-3), 2)  # Adjusted line position
    return ground

def create_pipe_surface():
    pipe = pygame.Surface((TILE_SIZE*2, TILE_SIZE*2))
    pipe.fill(GREEN)
    pygame.draw.rect(pipe, (0, 100, 0), (0, 0, TILE_SIZE*2, TILE_SIZE*2), 2)
    pygame.draw.rect(pipe, (0, 128, 0), (3, 3, TILE_SIZE*2-6, TILE_SIZE*2-6))  # Adjusted
    return pipe

def create_goomba_surface():
    goomba = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    pygame.draw.ellipse(goomba, (139, 69, 19), (1, 1, TILE_SIZE-2, TILE_SIZE-2))  # Body (adjusted)
    pygame.draw.ellipse(goomba, BLACK, (6, 6, 3, 3))  # Eye (adjusted)
    pygame.draw.ellipse(goomba, BLACK, (15, 6, 3, 3))  # Eye (adjusted)
    pygame.draw.arc(goomba, BLACK, (7, 12, 9, 6), 0, 3.14, 2)  # Mouth (adjusted)
    pygame.draw.ellipse(goomba, (250, 200, 150), (4, 3, 5, 3))  # Foot (adjusted)
    pygame.draw.ellipse(goomba, (250, 200, 150), (15, 3, 5, 3))  # Foot (adjusted)
    return goomba

def create_koopa_surface():
    koopa = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    # Shell
    pygame.draw.ellipse(koopa, (0, 150, 0), (1, 1, TILE_SIZE-2, TILE_SIZE-2))  # Adjusted
    pygame.draw.ellipse(koopa, (0, 100, 0), (4, 4, TILE_SIZE-8, TILE_SIZE-8))  # Adjusted
    # Head
    pygame.draw.ellipse(koopa, (0, 180, 0), (6, 1, 12, 9))  # Adjusted
    # Eyes
    pygame.draw.ellipse(koopa, BLACK, (9, 4, 3, 3))  # Adjusted
    pygame.draw.ellipse(koopa, BLACK, (15, 4, 3, 3))  # Adjusted
    # Feet
    pygame.draw.ellipse(koopa, (0, 180, 0), (3, 15, 6, 4))  # Adjusted
    pygame.draw.ellipse(koopa, (0, 180, 0), (15, 15, 6, 4))  # Adjusted
    return koopa

def create_coin_surface():
    coin = pygame.Surface((TILE_SIZE//2, TILE_SIZE), pygame.SRCALPHA)
    pygame.draw.ellipse(coin, YELLOW, (0, 3, TILE_SIZE//2, TILE_SIZE-6))  # Adjusted
    pygame.draw.ellipse(coin, (220, 180, 0), (1, 4, TILE_SIZE//2-2, TILE_SIZE-8))  # Adjusted
    return coin

def create_mario_surface():
    # Create a surface with transparency
    mario = pygame.Surface((TILE_SIZE, TILE_SIZE*2), pygame.SRCALPHA)
    
    # Draw Mario in NES style - more accurate to original
    # Hat/head
    pygame.draw.rect(mario, MARIO_RED, (4, 3, 16, 8))  # Hat
    pygame.draw.rect(mario, (255, 180, 180), (4, 11, 16, 8))  # Face
    
    # Eyes
    pygame.draw.rect(mario, BLACK, (8, 13, 2, 2))  # Left eye
    pygame.draw.rect(mario, BLACK, (14, 13, 2, 2))  # Right eye
    
    # Mustache
    pygame.draw.rect(mario, BLACK, (8, 15, 8, 2))
    
    # Hair
    pygame.draw.rect(mario, MARIO_BROWN, (4, 3, 4, 2))
    pygame.draw.rect(mario, MARIO_BROWN, (16, 3, 4, 2))
    
    # Body
    pygame.draw.rect(mario, MARIO_RED, (4, 19, 16, 8))  # Shirt
    
    # Overalls
    pygame.draw.rect(mario, MARIO_BLUE, (4, 19, 16, 12))
    pygame.draw.rect(mario, MARIO_BLUE, (4, 19, 6, 12))  # Left strap
    pygame.draw.rect(mario, MARIO_BLUE, (14, 19, 6, 12))  # Right strap
    
    # Button
    pygame.draw.rect(mario, YELLOW, (11, 24, 2, 2))
    
    # Arms
    pygame.draw.rect(mario, (255, 180, 180), (2, 19, 3, 6))  # Left arm
    pygame.draw.rect(mario, (255, 180, 180), (19, 19, 3, 6))  # Right arm
    
    # Legs
    pygame.draw.rect(mario, MARIO_BLUE, (6, 31, 4, 9))  # Left leg
    pygame.draw.rect(mario, MARIO_BLUE, (14, 31, 4, 9))  # Right leg
    
    # Shoes
    pygame.draw.rect(mario, BLACK, (4, 40, 8, 4))  # Left shoe
    pygame.draw.rect(mario, BLACK, (12, 40, 8, 4))  # Right shoe
    
    return mario

def create_flag_surface():
    flag = pygame.Surface((TILE_SIZE, TILE_SIZE*4), pygame.SRCALPHA)  # Slightly shorter flagpole for 400px height
    # Pole
    pygame.draw.rect(flag, (200, 200, 200), (10, 0, 3, TILE_SIZE*4))  # Adjusted position/width
    # Flag
    pygame.draw.polygon(flag, RED, [(10, 0), (10, 15), (22, 7)])  # Adjusted
    return flag

def create_grass_surface():
    grass = pygame.Surface((TILE_SIZE, TILE_SIZE))
    grass.fill(LIGHT_GREEN)
    # Add some grass details
    for _ in range(5):
        x = random.randint(1, TILE_SIZE-1)
        y = random.randint(1, TILE_SIZE-1)
        pygame.draw.line(grass, DARK_GREEN, (x, y), (x, y-2), 1)  # Slightly shorter grass
    return grass

def create_path_surface():
    path = pygame.Surface((TILE_SIZE, TILE_SIZE))
    path.fill(PATH_COLOR)
    # Add some path details
    for _ in range(3):
        x = random.randint(1, TILE_SIZE-1)
        y = random.randint(1, TILE_SIZE-1)
        pygame.draw.line(path, (200, 160, 70), (x, y), (x+2, y), 1)  # Slightly shorter detail
    return path

def create_flame_particle():
    particle = pygame.Surface((3, 3), pygame.SRCALPHA)  # Slightly smaller particle
    pygame.draw.circle(particle, FLAME_YELLOW, (1, 1), 1)  # Smaller circle
    return particle

# Game classes (Logic mostly unchanged, positions/sizes use TILE_SIZE)
class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = create_mario_surface()
        self.rect = self.image.get_rect(topleft=(x, y))
        self.vel_x = 0
        self.vel_y = 0
        self.on_ground = False
        self.direction = 1  # 1 for right, -1 for left
        self.coins_collected = 0
        self.enemies_defeated = 0

    def update(self, tiles, enemies, coins, flag):
        # Apply gravity
        self.vel_y += GRAVITY
        if self.vel_y > 10:
            self.vel_y = 10

        # Move horizontally
        self.rect.x += self.vel_x
        self.check_horizontal_collisions(tiles)

        # Move vertically
        self.rect.y += self.vel_y
        self.on_ground = False
        self.check_vertical_collisions(tiles)

        # Check for enemy collisions
        for enemy in enemies:
            if self.rect.colliderect(enemy.rect):
                if self.vel_y > 0 and self.rect.bottom < enemy.rect.centery:
                    enemy.kill()
                    self.vel_y = -6  # Slightly reduced bounce
                    self.enemies_defeated += 1
                    return (STATE_PLAYING, 0, 200)  # 200 points for defeating enemy
                else:
                    return (STATE_GAME_OVER, 0, 0)

        # Check for coin collisions
        coins_collected = pygame.sprite.spritecollide(self, coins, True)
        if coins_collected:
            self.coins_collected += len(coins_collected)
            return (STATE_PLAYING, len(coins_collected) * 100, 0)  # 100 points per coin

        # Check for flag collision
        if pygame.sprite.collide_rect(self, flag):
            return (STATE_LEVEL_COMPLETE, 0, 0)

        # Check if fell off the screen
        if self.rect.top > SCREEN_HEIGHT:
            return (STATE_GAME_OVER, 0, 0)

        return (STATE_PLAYING, 0, 0)

    def check_horizontal_collisions(self, tiles):
        for tile in tiles:
            if self.rect.colliderect(tile.rect):
                if self.vel_x > 0:
                    self.rect.right = tile.rect.left
                elif self.vel_x < 0:
                    self.rect.left = tile.rect.right

    def check_vertical_collisions(self, tiles):
        for tile in tiles:
            if self.rect.colliderect(tile.rect):
                if self.vel_y > 0:
                    self.rect.bottom = tile.rect.top
                    self.vel_y = 0
                    self.on_ground = True
                elif self.vel_y < 0:
                    self.rect.top = tile.rect.bottom
                    self.vel_y = 0

class Tile(pygame.sprite.Sprite):
    def __init__(self, x, y, surface):
        super().__init__()
        self.image = surface
        self.rect = self.image.get_rect(topleft=(x, y))

class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, enemy_type="goomba"):
        super().__init__()
        if enemy_type == "goomba":
            self.image = create_goomba_surface()
        else:  # koopa
            self.image = create_koopa_surface()
        self.rect = self.image.get_rect(topleft=(x, y))
        self.direction = -1
        self.speed = ENEMY_SPEED
        self.enemy_type = enemy_type

    def update(self, tiles):
        self.rect.x += self.direction * self.speed

        # Check for collisions with tiles
        for tile in tiles:
            if self.rect.colliderect(tile.rect):
                self.direction *= -1
                break

        # Check if at edge of platform
        check_x = self.rect.left if self.direction < 0 else self.rect.right
        check_y = self.rect.bottom + 3  # Adjusted check distance
        edge_check = pygame.Rect(check_x, check_y, 1, 1)

        on_platform = False
        for tile in tiles:
            if edge_check.colliderect(tile.rect):
                on_platform = True
                break

        if not on_platform:
            self.direction *= -1

class Coin(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = create_coin_surface()
        self.rect = self.image.get_rect(topleft=(x, y))

class Flag(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = create_flag_surface()
        self.rect = self.image.get_rect(bottomleft=(x, y))

class LevelNode(pygame.sprite.Sprite):
    def __init__(self, x, y, level_num):
        super().__init__()
        self.image = pygame.Surface((TILE_SIZE*2, TILE_SIZE*2), pygame.SRCALPHA)
        pygame.draw.rect(self.image, PURPLE, (0, 0, TILE_SIZE*2, TILE_SIZE*2), border_radius=6)  # Slightly smaller radius
        pygame.draw.rect(self.image, (180, 100, 220), (3, 3, TILE_SIZE*2-6, TILE_SIZE*2-6), border_radius=5)  # Adjusted
        level_text = font.render(str(level_num), True, WHITE)
        text_x = TILE_SIZE - level_text.get_width()//2
        text_y = TILE_SIZE - level_text.get_height()//2
        # Ensure text doesn't go out of bounds
        text_x = max(0, min(text_x, TILE_SIZE*2 - level_text.get_width()))
        text_y = max(0, min(text_y, TILE_SIZE*2 - level_text.get_height()))
        self.image.blit(level_text, (text_x, text_y))
        self.rect = self.image.get_rect(center=(x, y))
        self.level_num = level_num

class FlameParticle(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = create_flame_particle()
        self.rect = self.image.get_rect(center=(x, y))
        self.vel_x = random.uniform(-1, 1)
        self.vel_y = random.uniform(-3, -1)
        self.lifetime = random.randint(15, 30)  # Slightly reduced lifetime

    def update(self):
        self.rect.x += self.vel_x
        self.rect.y += self.vel_y
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.kill()

# Game setup
class Game:
    def __init__(self):
        self.score = 0
        self.lives = 3
        self.level = 1
        self.max_level = 8
        self.game_state = STATE_OVERWORLD
        self.initial_coin_count = 0
        self.flame_particles = pygame.sprite.Group()
        self.create_overworld()

    def create_overworld(self):
        self.overworld_sprites = pygame.sprite.Group()
        self.level_nodes = pygame.sprite.Group()

        # Create overworld terrain (adjusted for 600x400)
        for x in range(0, SCREEN_WIDTH, TILE_SIZE):
            for y in range(SCREEN_HEIGHT - TILE_SIZE*2, SCREEN_HEIGHT, TILE_SIZE):  # Reduced height
                if (x // TILE_SIZE) % 2 == 0 and (y // TILE_SIZE) % 2 == 0:
                    tile = Tile(x, y, create_grass_surface())
                    self.overworld_sprites.add(tile)

        # Create path (adjusted positions for 600x400)
        path_points = [
            (80, 350), (160, 350), (160, 280), (240, 280),
            (240, 220), (320, 220), (320, 280), (400, 280),
            (400, 220), (480, 220), (480, 280), (560, 280)
        ]

        for i in range(len(path_points)-1):
            start_x, start_y = path_points[i]
            end_x, end_y = path_points[i+1]

            if start_x == end_x:  # Vertical path
                step = TILE_SIZE if start_y < end_y else -TILE_SIZE
                for y in range(start_y, end_y, step):
                    tile = Tile(start_x, y, create_path_surface())
                    self.overworld_sprites.add(tile)
            else:  # Horizontal path
                step = TILE_SIZE if start_x < end_x else -TILE_SIZE
                for x in range(start_x, end_x, step):
                    tile = Tile(x, start_y, create_path_surface())
                    self.overworld_sprites.add(tile)

        # Create level nodes (adjusted positions)
        level_positions = [
            (80, 350), (160, 280), (240, 220), (320, 280),
            (400, 220), (480, 280), (560, 280)
        ]

        for i, pos in enumerate(level_positions):
            node = LevelNode(pos[0], pos[1], i+1)
            self.level_nodes.add(node)
            self.overworld_sprites.add(node)

        # Create player on overworld
        self.overworld_player = Player(80, 350 - TILE_SIZE*2)  # Adjusted start position
        self.overworld_sprites.add(self.overworld_player)

        # Set current level node
        self.current_node = 1

    def reset_level(self):
        self.all_sprites = pygame.sprite.Group()
        self.tiles = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.coins = pygame.sprite.Group()

        # Create level layout based on level number (adjusted width for 600x400)
        level_width = SCREEN_WIDTH * (1 + self.level // 2)  # Scaled down level width

        for x in range(0, level_width, TILE_SIZE):
            # Ground
            self.tiles.add(Tile(x, SCREEN_HEIGHT - TILE_SIZE, create_ground_surface()))

            # Random platforms
            if random.random() < 0.2 and x > SCREEN_WIDTH//2 and x < level_width - SCREEN_WIDTH//2:  # Adjusted spawn range
                height = random.randint(3, 5)  # Slightly reduced max height
                for y in range(SCREEN_HEIGHT - TILE_SIZE * height, SCREEN_HEIGHT - TILE_SIZE, TILE_SIZE):
                    self.tiles.add(Tile(x, y, create_block_surface()))

                # Add coins on platforms
                if random.random() < 0.7:
                    self.coins.add(Coin(x + TILE_SIZE//4, SCREEN_HEIGHT - TILE_SIZE * height - TILE_SIZE//2))

                # Add enemies on platforms
                if random.random() < 0.4:
                    enemy_type = "koopa" if self.level > 3 else "goomba"
                    self.enemies.add(Enemy(x, SCREEN_HEIGHT - TILE_SIZE * height - TILE_SIZE, enemy_type))

        # Add pipes (adjusted position)
        pipe_x = SCREEN_WIDTH + 100
        self.tiles.add(Tile(pipe_x, SCREEN_HEIGHT - TILE_SIZE*2, create_pipe_surface()))

        # Add question blocks
        for x in range(SCREEN_WIDTH//2, level_width - SCREEN_WIDTH//2, 150):  # Adjusted spacing
            if random.random() < 0.6:
                y = SCREEN_HEIGHT - TILE_SIZE * random.randint(3, 4)  # Slightly reduced max height
                self.tiles.add(Tile(x, y, create_question_block_surface()))

                # Coin above question block
                if random.random() < 0.5:
                    self.coins.add(Coin(x + TILE_SIZE//4, y - TILE_SIZE))

        # Add flag at the end
        self.flag = Flag(level_width - 80, SCREEN_HEIGHT - TILE_SIZE)  # Adjusted position
        self.all_sprites.add(self.tiles, self.enemies, self.coins, self.flag)

        # Create player
        self.player = Player(50, SCREEN_HEIGHT - TILE_SIZE * 3)
        self.all_sprites.add(self.player)

        self.camera_x = 0
        self.initial_coin_count = len(self.coins)
        self.level_width = level_width

    def run(self):
        running = True
        while running:
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                if event.type == pygame.KEYDOWN:
                    if self.game_state == STATE_OVERWORLD:
                        if event.key == pygame.K_RIGHT and self.current_node < len(self.level_nodes):
                            self.current_node += 1
                            # Move player to next node
                            nodes = list(self.level_nodes)
                            if self.current_node <= len(nodes):
                                self.overworld_player.rect.centerx = nodes[self.current_node-1].rect.centerx
                                self.overworld_player.rect.bottom = nodes[self.current_node-1].rect.top
                        elif event.key == pygame.K_LEFT and self.current_node > 1:
                            self.current_node -= 1
                            # Move player to previous node
                            nodes = list(self.level_nodes)
                            self.overworld_player.rect.centerx = nodes[self.current_node-1].rect.centerx
                            self.overworld_player.rect.bottom = nodes[self.current_node-1].rect.top
                        elif event.key == pygame.K_RETURN:
                            self.level = self.current_node
                            self.reset_level()
                            self.game_state = STATE_PLAYING

                    elif self.game_state == STATE_PLAYING:
                        if event.key == pygame.K_LEFT:
                            self.player.vel_x = -PLAYER_SPEED
                            self.player.direction = -1
                        if event.key == pygame.K_RIGHT:
                            self.player.vel_x = PLAYER_SPEED
                            self.player.direction = 1
                        if event.key == pygame.K_SPACE and self.player.on_ground:
                            self.player.vel_y = JUMP_POWER
                        if event.key == pygame.K_ESCAPE:
                            self.game_state = STATE_OVERWORLD

                    elif self.game_state in [STATE_GAME_OVER, STATE_LEVEL_COMPLETE, STATE_WIN]:
                        if event.key == pygame.K_RETURN:
                            if self.game_state == STATE_GAME_OVER:
                                self.lives -= 1
                                if self.lives > 0:
                                    self.reset_level()
                                    self.game_state = STATE_PLAYING
                                else:
                                    self.game_state = STATE_GAME_OVER
                            elif self.game_state == STATE_LEVEL_COMPLETE:
                                # Add bonus for completing level
                                self.score += (self.initial_coin_count - len(self.coins)) * 100
                                self.score += self.player.enemies_defeated * 200
                                if self.level < self.max_level:
                                    self.game_state = STATE_OVERWORLD
                                    # Move to next level on overworld
                                    self.current_node += 1
                                    nodes = list(self.level_nodes)
                                    if self.current_node <= len(nodes):
                                        self.overworld_player.rect.centerx = nodes[self.current_node-1].rect.centerx
                                        self.overworld_player.rect.bottom = nodes[self.current_node-1].rect.top
                                else:
                                    self.game_state = STATE_WIN
                            elif self.game_state == STATE_WIN:
                                self.__init__()

                if event.type == pygame.KEYUP:
                    if event.key in [pygame.K_LEFT, pygame.K_RIGHT]:
                        if self.game_state == STATE_PLAYING:
                            self.player.vel_x = 0

            # Update game state
            if self.game_state == STATE_PLAYING:
                # Update player and check game state
                result = self.player.update(self.tiles, self.enemies, self.coins, self.flag)
                game_state, coin_points, enemy_points = result

                # Update score
                self.score += coin_points + enemy_points

                if game_state != STATE_PLAYING:
                    self.game_state = game_state

                # Update enemies
                self.enemies.update(self.tiles)

                # Update camera to follow player
                self.camera_x = self.player.rect.centerx - SCREEN_WIDTH // 2
                self.camera_x = max(0, min(self.camera_x, self.level_width - SCREEN_WIDTH))

            # Update flame particles
            if random.random() < 0.3:
                self.flame_particles.add(FlameParticle(
                    random.randint(0, SCREEN_WIDTH),
                    SCREEN_HEIGHT
                ))
            self.flame_particles.update()

            # Draw everything
            if self.game_state == STATE_OVERWORLD:
                screen.fill(SKY_BLUE)

                # Draw title (adjusted size/position)
                title_font = pygame.font.SysFont("Arial", 28, bold=True)  # Smaller title font
                title = title_font.render("ULTRA MARIO 2D BROS", True, RED)
                screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 15))  # Higher position

                self.overworld_sprites.draw(screen)

                # Draw flame particles
                self.flame_particles.draw(screen)

                # Draw instructions (adjusted position)
                instructions = font.render("ARROWS: NAVIGATE  ENTER: SELECT", True, WHITE)
                screen.blit(instructions, (SCREEN_WIDTH//2 - instructions.get_width()//2, 80))  # Higher position

            else:
                screen.fill(SKY_BLUE)

                # Draw all sprites with camera offset
                for sprite in self.all_sprites:
                    screen.blit(sprite.image, (sprite.rect.x - self.camera_x, sprite.rect.y))

            # Draw UI
            self.draw_ui()

            # Draw game state messages
            if self.game_state != STATE_PLAYING and self.game_state != STATE_OVERWORLD:
                self.draw_message()

            pygame.display.flip()
            clock.tick(FPS)

        pygame.quit()
        sys.exit()

    def draw_ui(self):
        # Draw score
        score_text = font.render(f"SCORE: {self.score}", True, WHITE)
        screen.blit(score_text, (15, 15))  # Adjusted position

        # Draw lives
        lives_text = font.render(f"LIVES: {self.lives}", True, WHITE)
        screen.blit(lives_text, (15, 35))  # Adjusted position

        # Draw level
        if self.game_state == STATE_OVERWORLD:
            level_text = font.render(f"LEVEL: {self.current_node}", True, WHITE)
        else:
            level_text = font.render(f"WORLD 1-{self.level}", True, WHITE)
        screen.blit(level_text, (SCREEN_WIDTH - 120, 15))  # Adjusted position

        # Draw coins
        if self.game_state == STATE_OVERWORLD:
            coins_text = font.render(f"COINS: {self.overworld_player.coins_collected}", True, WHITE)
        else:
            coins_text = font.render(f"COINS: {self.player.coins_collected}", True, WHITE)
        screen.blit(coins_text, (SCREEN_WIDTH - 120, 35))  # Adjusted position

    def draw_message(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, 0))

        if self.game_state == STATE_GAME_OVER:
            if self.lives > 0:
                text = font.render("GAME OVER", True, WHITE)
                restart = font.render("PRESS ENTER", True, WHITE)
            else:
                text = font.render("OUT OF LIVES", True, WHITE)
                restart = font.render("PRESS ENTER", True, WHITE)
        elif self.game_state == STATE_LEVEL_COMPLETE:
            text = font.render("LEVEL COMPLETE!", True, WHITE)
            restart = font.render("PRESS ENTER", True, WHITE)
        elif self.game_state == STATE_WIN:
            text = font.render("YOU WIN!", True, WHITE)
            restart = font.render("PRESS ENTER", True, WHITE)

        screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, SCREEN_HEIGHT // 2 - 40))  # Adjusted Y
        screen.blit(restart, (SCREEN_WIDTH // 2 - restart.get_width() // 2, SCREEN_HEIGHT // 2 + 10))  # Adjusted Y

# Start the game
if __name__ == "__main__":
    game = Game()
    game.run()import pygame
import sys
import random

# Initialize Pygame
pygame.init()

# Constants - UPDATED FOR 600x400
SCREEN_WIDTH = 600
SCREEN_HEIGHT = 400
TILE_SIZE = 24  # Reduced tile size for 600x400 resolution
FPS = 60

# NES Color Palette
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
MARIO_BROWN = (136, 64, 0)  # For Mario's hair

# Game physics (NES-like but adjusted for 600x400)
GRAVITY = 0.6  # Slightly reduced gravity
PLAYER_SPEED = 4  # Slightly reduced speed
JUMP_POWER = -14  # Slightly reduced jump power
ENEMY_SPEED = 1.5  # Slightly reduced enemy speed

# Game states
STATE_OVERWORLD = 0
STATE_PLAYING = 1
STATE_LEVEL_COMPLETE = 2
STATE_GAME_OVER = 3
STATE_WIN = 4

# Set up the display
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("ULTRA MARIO 2D BROS")
clock = pygame.time.Clock()

# Try to load a pixel font, fall back to system font
try:
    font = pygame.font.Font("prstart.ttf", 12)  # Reduced font size
except:
    font = pygame.font.SysFont("Arial", 12, bold=True)

# Create surfaces for game elements (sizes based on TILE_SIZE=24)
def create_block_surface():
    block = pygame.Surface((TILE_SIZE, TILE_SIZE))
    block.fill(BROWN)
    pygame.draw.rect(block, (101, 67, 33), (0, 0, TILE_SIZE, TILE_SIZE), 2)
    pygame.draw.rect(block, (160, 82, 45), (3, 3, TILE_SIZE-6, TILE_SIZE-6))  # Adjusted inner rect
    return block

def create_question_block_surface():
    block = pygame.Surface((TILE_SIZE, TILE_SIZE))
    block.fill(YELLOW)
    pygame.draw.rect(block, (180, 150, 0), (0, 0, TILE_SIZE, TILE_SIZE), 2)
    pygame.draw.rect(block, (220, 180, 0), (3, 3, TILE_SIZE-6, TILE_SIZE-6))  # Adjusted
    pygame.draw.rect(block, (248, 216, 0), (6, 6, TILE_SIZE-12, TILE_SIZE-12))  # Adjusted
    pygame.draw.rect(block, (180, 150, 0), (9, 9, TILE_SIZE-18, TILE_SIZE-18))  # Adjusted
    # Add question mark (scaled down positions)
    pygame.draw.rect(block, BLACK, (10, 7, 3, 9))  # Eye
    pygame.draw.rect(block, BLACK, (7, 10, 9, 3))  # Mouth top
    pygame.draw.rect(block, BLACK, (10, 16, 3, 3))  # Mouth bottom
    return block

def create_ground_surface():
    ground = pygame.Surface((TILE_SIZE, TILE_SIZE))
    ground.fill(BROWN)
    pygame.draw.rect(ground, (101, 67, 33), (0, 0, TILE_SIZE, TILE_SIZE), 2)
    pygame.draw.line(ground, (101, 67, 33), (0, TILE_SIZE-3), (TILE_SIZE, TILE_SIZE-3), 2)  # Adjusted line position
    return ground

def create_pipe_surface():
    pipe = pygame.Surface((TILE_SIZE*2, TILE_SIZE*2))
    pipe.fill(GREEN)
    pygame.draw.rect(pipe, (0, 100, 0), (0, 0, TILE_SIZE*2, TILE_SIZE*2), 2)
    pygame.draw.rect(pipe, (0, 128, 0), (3, 3, TILE_SIZE*2-6, TILE_SIZE*2-6))  # Adjusted
    return pipe

def create_goomba_surface():
    goomba = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    pygame.draw.ellipse(goomba, (139, 69, 19), (1, 1, TILE_SIZE-2, TILE_SIZE-2))  # Body (adjusted)
    pygame.draw.ellipse(goomba, BLACK, (6, 6, 3, 3))  # Eye (adjusted)
    pygame.draw.ellipse(goomba, BLACK, (15, 6, 3, 3))  # Eye (adjusted)
    pygame.draw.arc(goomba, BLACK, (7, 12, 9, 6), 0, 3.14, 2)  # Mouth (adjusted)
    pygame.draw.ellipse(goomba, (250, 200, 150), (4, 3, 5, 3))  # Foot (adjusted)
    pygame.draw.ellipse(goomba, (250, 200, 150), (15, 3, 5, 3))  # Foot (adjusted)
    return goomba

def create_koopa_surface():
    koopa = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    # Shell
    pygame.draw.ellipse(koopa, (0, 150, 0), (1, 1, TILE_SIZE-2, TILE_SIZE-2))  # Adjusted
    pygame.draw.ellipse(koopa, (0, 100, 0), (4, 4, TILE_SIZE-8, TILE_SIZE-8))  # Adjusted
    # Head
    pygame.draw.ellipse(koopa, (0, 180, 0), (6, 1, 12, 9))  # Adjusted
    # Eyes
    pygame.draw.ellipse(koopa, BLACK, (9, 4, 3, 3))  # Adjusted
    pygame.draw.ellipse(koopa, BLACK, (15, 4, 3, 3))  # Adjusted
    # Feet
    pygame.draw.ellipse(koopa, (0, 180, 0), (3, 15, 6, 4))  # Adjusted
    pygame.draw.ellipse(koopa, (0, 180, 0), (15, 15, 6, 4))  # Adjusted
    return koopa

def create_coin_surface():
    coin = pygame.Surface((TILE_SIZE//2, TILE_SIZE), pygame.SRCALPHA)
    pygame.draw.ellipse(coin, YELLOW, (0, 3, TILE_SIZE//2, TILE_SIZE-6))  # Adjusted
    pygame.draw.ellipse(coin, (220, 180, 0), (1, 4, TILE_SIZE//2-2, TILE_SIZE-8))  # Adjusted
    return coin

def create_mario_surface():
    # Create a surface with transparency
    mario = pygame.Surface((TILE_SIZE, TILE_SIZE*2), pygame.SRCALPHA)
    
    # Draw Mario in NES style - more accurate to original
    # Hat/head
    pygame.draw.rect(mario, MARIO_RED, (4, 3, 16, 8))  # Hat
    pygame.draw.rect(mario, (255, 180, 180), (4, 11, 16, 8))  # Face
    
    # Eyes
    pygame.draw.rect(mario, BLACK, (8, 13, 2, 2))  # Left eye
    pygame.draw.rect(mario, BLACK, (14, 13, 2, 2))  # Right eye
    
    # Mustache
    pygame.draw.rect(mario, BLACK, (8, 15, 8, 2))
    
    # Hair
    pygame.draw.rect(mario, MARIO_BROWN, (4, 3, 4, 2))
    pygame.draw.rect(mario, MARIO_BROWN, (16, 3, 4, 2))
    
    # Body
    pygame.draw.rect(mario, MARIO_RED, (4, 19, 16, 8))  # Shirt
    
    # Overalls
    pygame.draw.rect(mario, MARIO_BLUE, (4, 19, 16, 12))
    pygame.draw.rect(mario, MARIO_BLUE, (4, 19, 6, 12))  # Left strap
    pygame.draw.rect(mario, MARIO_BLUE, (14, 19, 6, 12))  # Right strap
    
    # Button
    pygame.draw.rect(mario, YELLOW, (11, 24, 2, 2))
    
    # Arms
    pygame.draw.rect(mario, (255, 180, 180), (2, 19, 3, 6))  # Left arm
    pygame.draw.rect(mario, (255, 180, 180), (19, 19, 3, 6))  # Right arm
    
    # Legs
    pygame.draw.rect(mario, MARIO_BLUE, (6, 31, 4, 9))  # Left leg
    pygame.draw.rect(mario, MARIO_BLUE, (14, 31, 4, 9))  # Right leg
    
    # Shoes
    pygame.draw.rect(mario, BLACK, (4, 40, 8, 4))  # Left shoe
    pygame.draw.rect(mario, BLACK, (12, 40, 8, 4))  # Right shoe
    
    return mario

def create_flag_surface():
    flag = pygame.Surface((TILE_SIZE, TILE_SIZE*4), pygame.SRCALPHA)  # Slightly shorter flagpole for 400px height
    # Pole
    pygame.draw.rect(flag, (200, 200, 200), (10, 0, 3, TILE_SIZE*4))  # Adjusted position/width
    # Flag
    pygame.draw.polygon(flag, RED, [(10, 0), (10, 15), (22, 7)])  # Adjusted
    return flag

def create_grass_surface():
    grass = pygame.Surface((TILE_SIZE, TILE_SIZE))
    grass.fill(LIGHT_GREEN)
    # Add some grass details
    for _ in range(5):
        x = random.randint(1, TILE_SIZE-1)
        y = random.randint(1, TILE_SIZE-1)
        pygame.draw.line(grass, DARK_GREEN, (x, y), (x, y-2), 1)  # Slightly shorter grass
    return grass

def create_path_surface():
    path = pygame.Surface((TILE_SIZE, TILE_SIZE))
    path.fill(PATH_COLOR)
    # Add some path details
    for _ in range(3):
        x = random.randint(1, TILE_SIZE-1)
        y = random.randint(1, TILE_SIZE-1)
        pygame.draw.line(path, (200, 160, 70), (x, y), (x+2, y), 1)  # Slightly shorter detail
    return path

def create_flame_particle():
    particle = pygame.Surface((3, 3), pygame.SRCALPHA)  # Slightly smaller particle
    pygame.draw.circle(particle, FLAME_YELLOW, (1, 1), 1)  # Smaller circle
    return particle

# Game classes (Logic mostly unchanged, positions/sizes use TILE_SIZE)
class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = create_mario_surface()
        self.rect = self.image.get_rect(topleft=(x, y))
        self.vel_x = 0
        self.vel_y = 0
        self.on_ground = False
        self.direction = 1  # 1 for right, -1 for left
        self.coins_collected = 0
        self.enemies_defeated = 0

    def update(self, tiles, enemies, coins, flag):
        # Apply gravity
        self.vel_y += GRAVITY
        if self.vel_y > 10:
            self.vel_y = 10

        # Move horizontally
        self.rect.x += self.vel_x
        self.check_horizontal_collisions(tiles)

        # Move vertically
        self.rect.y += self.vel_y
        self.on_ground = False
        self.check_vertical_collisions(tiles)

        # Check for enemy collisions
        for enemy in enemies:
            if self.rect.colliderect(enemy.rect):
                if self.vel_y > 0 and self.rect.bottom < enemy.rect.centery:
                    enemy.kill()
                    self.vel_y = -6  # Slightly reduced bounce
                    self.enemies_defeated += 1
                    return (STATE_PLAYING, 0, 200)  # 200 points for defeating enemy
                else:
                    return (STATE_GAME_OVER, 0, 0)

        # Check for coin collisions
        coins_collected = pygame.sprite.spritecollide(self, coins, True)
        if coins_collected:
            self.coins_collected += len(coins_collected)
            return (STATE_PLAYING, len(coins_collected) * 100, 0)  # 100 points per coin

        # Check for flag collision
        if pygame.sprite.collide_rect(self, flag):
            return (STATE_LEVEL_COMPLETE, 0, 0)

        # Check if fell off the screen
        if self.rect.top > SCREEN_HEIGHT:
            return (STATE_GAME_OVER, 0, 0)

        return (STATE_PLAYING, 0, 0)

    def check_horizontal_collisions(self, tiles):
        for tile in tiles:
            if self.rect.colliderect(tile.rect):
                if self.vel_x > 0:
                    self.rect.right = tile.rect.left
                elif self.vel_x < 0:
                    self.rect.left = tile.rect.right

    def check_vertical_collisions(self, tiles):
        for tile in tiles:
            if self.rect.colliderect(tile.rect):
                if self.vel_y > 0:
                    self.rect.bottom = tile.rect.top
                    self.vel_y = 0
                    self.on_ground = True
                elif self.vel_y < 0:
                    self.rect.top = tile.rect.bottom
                    self.vel_y = 0

class Tile(pygame.sprite.Sprite):
    def __init__(self, x, y, surface):
        super().__init__()
        self.image = surface
        self.rect = self.image.get_rect(topleft=(x, y))

class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, enemy_type="goomba"):
        super().__init__()
        if enemy_type == "goomba":
            self.image = create_goomba_surface()
        else:  # koopa
            self.image = create_koopa_surface()
        self.rect = self.image.get_rect(topleft=(x, y))
        self.direction = -1
        self.speed = ENEMY_SPEED
        self.enemy_type = enemy_type

    def update(self, tiles):
        self.rect.x += self.direction * self.speed

        # Check for collisions with tiles
        for tile in tiles:
            if self.rect.colliderect(tile.rect):
                self.direction *= -1
                break

        # Check if at edge of platform
        check_x = self.rect.left if self.direction < 0 else self.rect.right
        check_y = self.rect.bottom + 3  # Adjusted check distance
        edge_check = pygame.Rect(check_x, check_y, 1, 1)

        on_platform = False
        for tile in tiles:
            if edge_check.colliderect(tile.rect):
                on_platform = True
                break

        if not on_platform:
            self.direction *= -1

class Coin(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = create_coin_surface()
        self.rect = self.image.get_rect(topleft=(x, y))

class Flag(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = create_flag_surface()
        self.rect = self.image.get_rect(bottomleft=(x, y))

class LevelNode(pygame.sprite.Sprite):
    def __init__(self, x, y, level_num):
        super().__init__()
        self.image = pygame.Surface((TILE_SIZE*2, TILE_SIZE*2), pygame.SRCALPHA)
        pygame.draw.rect(self.image, PURPLE, (0, 0, TILE_SIZE*2, TILE_SIZE*2), border_radius=6)  # Slightly smaller radius
        pygame.draw.rect(self.image, (180, 100, 220), (3, 3, TILE_SIZE*2-6, TILE_SIZE*2-6), border_radius=5)  # Adjusted
        level_text = font.render(str(level_num), True, WHITE)
        text_x = TILE_SIZE - level_text.get_width()//2
        text_y = TILE_SIZE - level_text.get_height()//2
        # Ensure text doesn't go out of bounds
        text_x = max(0, min(text_x, TILE_SIZE*2 - level_text.get_width()))
        text_y = max(0, min(text_y, TILE_SIZE*2 - level_text.get_height()))
        self.image.blit(level_text, (text_x, text_y))
        self.rect = self.image.get_rect(center=(x, y))
        self.level_num = level_num

class FlameParticle(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = create_flame_particle()
        self.rect = self.image.get_rect(center=(x, y))
        self.vel_x = random.uniform(-1, 1)
        self.vel_y = random.uniform(-3, -1)
        self.lifetime = random.randint(15, 30)  # Slightly reduced lifetime

    def update(self):
        self.rect.x += self.vel_x
        self.rect.y += self.vel_y
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.kill()

# Game setup
class Game:
    def __init__(self):
        self.score = 0
        self.lives = 3
        self.level = 1
        self.max_level = 8
        self.game_state = STATE_OVERWORLD
        self.initial_coin_count = 0
        self.flame_particles = pygame.sprite.Group()
        self.create_overworld()

    def create_overworld(self):
        self.overworld_sprites = pygame.sprite.Group()
        self.level_nodes = pygame.sprite.Group()

        # Create overworld terrain (adjusted for 600x400)
        for x in range(0, SCREEN_WIDTH, TILE_SIZE):
            for y in range(SCREEN_HEIGHT - TILE_SIZE*2, SCREEN_HEIGHT, TILE_SIZE):  # Reduced height
                if (x // TILE_SIZE) % 2 == 0 and (y // TILE_SIZE) % 2 == 0:
                    tile = Tile(x, y, create_grass_surface())
                    self.overworld_sprites.add(tile)

        # Create path (adjusted positions for 600x400)
        path_points = [
            (80, 350), (160, 350), (160, 280), (240, 280),
            (240, 220), (320, 220), (320, 280), (400, 280),
            (400, 220), (480, 220), (480, 280), (560, 280)
        ]

        for i in range(len(path_points)-1):
            start_x, start_y = path_points[i]
            end_x, end_y = path_points[i+1]

            if start_x == end_x:  # Vertical path
                step = TILE_SIZE if start_y < end_y else -TILE_SIZE
                for y in range(start_y, end_y, step):
                    tile = Tile(start_x, y, create_path_surface())
                    self.overworld_sprites.add(tile)
            else:  # Horizontal path
                step = TILE_SIZE if start_x < end_x else -TILE_SIZE
                for x in range(start_x, end_x, step):
                    tile = Tile(x, start_y, create_path_surface())
                    self.overworld_sprites.add(tile)

        # Create level nodes (adjusted positions)
        level_positions = [
            (80, 350), (160, 280), (240, 220), (320, 280),
            (400, 220), (480, 280), (560, 280)
        ]

        for i, pos in enumerate(level_positions):
            node = LevelNode(pos[0], pos[1], i+1)
            self.level_nodes.add(node)
            self.overworld_sprites.add(node)

        # Create player on overworld
        self.overworld_player = Player(80, 350 - TILE_SIZE*2)  # Adjusted start position
        self.overworld_sprites.add(self.overworld_player)

        # Set current level node
        self.current_node = 1

    def reset_level(self):
        self.all_sprites = pygame.sprite.Group()
        self.tiles = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.coins = pygame.sprite.Group()

        # Create level layout based on level number (adjusted width for 600x400)
        level_width = SCREEN_WIDTH * (1 + self.level // 2)  # Scaled down level width

        for x in range(0, level_width, TILE_SIZE):
            # Ground
            self.tiles.add(Tile(x, SCREEN_HEIGHT - TILE_SIZE, create_ground_surface()))

            # Random platforms
            if random.random() < 0.2 and x > SCREEN_WIDTH//2 and x < level_width - SCREEN_WIDTH//2:  # Adjusted spawn range
                height = random.randint(3, 5)  # Slightly reduced max height
                for y in range(SCREEN_HEIGHT - TILE_SIZE * height, SCREEN_HEIGHT - TILE_SIZE, TILE_SIZE):
                    self.tiles.add(Tile(x, y, create_block_surface()))

                # Add coins on platforms
                if random.random() < 0.7:
                    self.coins.add(Coin(x + TILE_SIZE//4, SCREEN_HEIGHT - TILE_SIZE * height - TILE_SIZE//2))

                # Add enemies on platforms
                if random.random() < 0.4:
                    enemy_type = "koopa" if self.level > 3 else "goomba"
                    self.enemies.add(Enemy(x, SCREEN_HEIGHT - TILE_SIZE * height - TILE_SIZE, enemy_type))

        # Add pipes (adjusted position)
        pipe_x = SCREEN_WIDTH + 100
        self.tiles.add(Tile(pipe_x, SCREEN_HEIGHT - TILE_SIZE*2, create_pipe_surface()))

        # Add question blocks
        for x in range(SCREEN_WIDTH//2, level_width - SCREEN_WIDTH//2, 150):  # Adjusted spacing
            if random.random() < 0.6:
                y = SCREEN_HEIGHT - TILE_SIZE * random.randint(3, 4)  # Slightly reduced max height
                self.tiles.add(Tile(x, y, create_question_block_surface()))

                # Coin above question block
                if random.random() < 0.5:
                    self.coins.add(Coin(x + TILE_SIZE//4, y - TILE_SIZE))

        # Add flag at the end
        self.flag = Flag(level_width - 80, SCREEN_HEIGHT - TILE_SIZE)  # Adjusted position
        self.all_sprites.add(self.tiles, self.enemies, self.coins, self.flag)

        # Create player
        self.player = Player(50, SCREEN_HEIGHT - TILE_SIZE * 3)
        self.all_sprites.add(self.player)

        self.camera_x = 0
        self.initial_coin_count = len(self.coins)
        self.level_width = level_width

    def run(self):
        running = True
        while running:
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                if event.type == pygame.KEYDOWN:
                    if self.game_state == STATE_OVERWORLD:
                        if event.key == pygame.K_RIGHT and self.current_node < len(self.level_nodes):
                            self.current_node += 1
                            # Move player to next node
                            nodes = list(self.level_nodes)
                            if self.current_node <= len(nodes):
                                self.overworld_player.rect.centerx = nodes[self.current_node-1].rect.centerx
                                self.overworld_player.rect.bottom = nodes[self.current_node-1].rect.top
                        elif event.key == pygame.K_LEFT and self.current_node > 1:
                            self.current_node -= 1
                            # Move player to previous node
                            nodes = list(self.level_nodes)
                            self.overworld_player.rect.centerx = nodes[self.current_node-1].rect.centerx
                            self.overworld_player.rect.bottom = nodes[self.current_node-1].rect.top
                        elif event.key == pygame.K_RETURN:
                            self.level = self.current_node
                            self.reset_level()
                            self.game_state = STATE_PLAYING

                    elif self.game_state == STATE_PLAYING:
                        if event.key == pygame.K_LEFT:
                            self.player.vel_x = -PLAYER_SPEED
                            self.player.direction = -1
                        if event.key == pygame.K_RIGHT:
                            self.player.vel_x = PLAYER_SPEED
                            self.player.direction = 1
                        if event.key == pygame.K_SPACE and self.player.on_ground:
                            self.player.vel_y = JUMP_POWER
                        if event.key == pygame.K_ESCAPE:
                            self.game_state = STATE_OVERWORLD

                    elif self.game_state in [STATE_GAME_OVER, STATE_LEVEL_COMPLETE, STATE_WIN]:
                        if event.key == pygame.K_RETURN:
                            if self.game_state == STATE_GAME_OVER:
                                self.lives -= 1
                                if self.lives > 0:
                                    self.reset_level()
                                    self.game_state = STATE_PLAYING
                                else:
                                    self.game_state = STATE_GAME_OVER
                            elif self.game_state == STATE_LEVEL_COMPLETE:
                                # Add bonus for completing level
                                self.score += (self.initial_coin_count - len(self.coins)) * 100
                                self.score += self.player.enemies_defeated * 200
                                if self.level < self.max_level:
                                    self.game_state = STATE_OVERWORLD
                                    # Move to next level on overworld
                                    self.current_node += 1
                                    nodes = list(self.level_nodes)
                                    if self.current_node <= len(nodes):
                                        self.overworld_player.rect.centerx = nodes[self.current_node-1].rect.centerx
                                        self.overworld_player.rect.bottom = nodes[self.current_node-1].rect.top
                                else:
                                    self.game_state = STATE_WIN
                            elif self.game_state == STATE_WIN:
                                self.__init__()

                if event.type == pygame.KEYUP:
                    if event.key in [pygame.K_LEFT, pygame.K_RIGHT]:
                        if self.game_state == STATE_PLAYING:
                            self.player.vel_x = 0

            # Update game state
            if self.game_state == STATE_PLAYING:
                # Update player and check game state
                result = self.player.update(self.tiles, self.enemies, self.coins, self.flag)
                game_state, coin_points, enemy_points = result

                # Update score
                self.score += coin_points + enemy_points

                if game_state != STATE_PLAYING:
                    self.game_state = game_state

                # Update enemies
                self.enemies.update(self.tiles)

                # Update camera to follow player
                self.camera_x = self.player.rect.centerx - SCREEN_WIDTH // 2
                self.camera_x = max(0, min(self.camera_x, self.level_width - SCREEN_WIDTH))

            # Update flame particles
            if random.random() < 0.3:
                self.flame_particles.add(FlameParticle(
                    random.randint(0, SCREEN_WIDTH),
                    SCREEN_HEIGHT
                ))
            self.flame_particles.update()

            # Draw everything
            if self.game_state == STATE_OVERWORLD:
                screen.fill(SKY_BLUE)

                # Draw title (adjusted size/position)
                title_font = pygame.font.SysFont("Arial", 28, bold=True)  # Smaller title font
                title = title_font.render("ULTRA MARIO 2D BROS", True, RED)
                screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 15))  # Higher position

                self.overworld_sprites.draw(screen)

                # Draw flame particles
                self.flame_particles.draw(screen)

                # Draw instructions (adjusted position)
                instructions = font.render("ARROWS: NAVIGATE  ENTER: SELECT", True, WHITE)
                screen.blit(instructions, (SCREEN_WIDTH//2 - instructions.get_width()//2, 80))  # Higher position

            else:
                screen.fill(SKY_BLUE)

                # Draw all sprites with camera offset
                for sprite in self.all_sprites:
                    screen.blit(sprite.image, (sprite.rect.x - self.camera_x, sprite.rect.y))

            # Draw UI
            self.draw_ui()

            # Draw game state messages
            if self.game_state != STATE_PLAYING and self.game_state != STATE_OVERWORLD:
                self.draw_message()

            pygame.display.flip()
            clock.tick(FPS)

        pygame.quit()
        sys.exit()

    def draw_ui(self):
        # Draw score
        score_text = font.render(f"SCORE: {self.score}", True, WHITE)
        screen.blit(score_text, (15, 15))  # Adjusted position

        # Draw lives
        lives_text = font.render(f"LIVES: {self.lives}", True, WHITE)
        screen.blit(lives_text, (15, 35))  # Adjusted position

        # Draw level
        if self.game_state == STATE_OVERWORLD:
            level_text = font.render(f"LEVEL: {self.current_node}", True, WHITE)
        else:
            level_text = font.render(f"WORLD 1-{self.level}", True, WHITE)
        screen.blit(level_text, (SCREEN_WIDTH - 120, 15))  # Adjusted position

        # Draw coins
        if self.game_state == STATE_OVERWORLD:
            coins_text = font.render(f"COINS: {self.overworld_player.coins_collected}", True, WHITE)
        else:
            coins_text = font.render(f"COINS: {self.player.coins_collected}", True, WHITE)
        screen.blit(coins_text, (SCREEN_WIDTH - 120, 35))  # Adjusted position

    def draw_message(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, 0))

        if self.game_state == STATE_GAME_OVER:
            if self.lives > 0:
                text = font.render("GAME OVER", True, WHITE)
                restart = font.render("PRESS ENTER", True, WHITE)
            else:
                text = font.render("OUT OF LIVES", True, WHITE)
                restart = font.render("PRESS ENTER", True, WHITE)
        elif self.game_state == STATE_LEVEL_COMPLETE:
            text = font.render("LEVEL COMPLETE!", True, WHITE)
            restart = font.render("PRESS ENTER", True, WHITE)
        elif self.game_state == STATE_WIN:
            text = font.render("YOU WIN!", True, WHITE)
            restart = font.render("PRESS ENTER", True, WHITE)

        screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, SCREEN_HEIGHT // 2 - 40))  # Adjusted Y
        screen.blit(restart, (SCREEN_WIDTH // 2 - restart.get_width() // 2, SCREEN_HEIGHT // 2 + 10))  # Adjusted Y

# Start the game
if __name__ == "__main__":
    game = Game()
    game.run()
