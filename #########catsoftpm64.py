import pygame
import sys
import math
import random

# Initialize Pygame
pygame.init()

# Constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60
GRAVITY = 0.8
JUMP_STRENGTH = -15
MOVE_SPEED = 5

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 100, 255)
YELLOW = (255, 255, 0)
BROWN = (139, 69, 19)
SKY_BLUE = (135, 206, 235)
PURPLE = (128, 0, 128)
ORANGE = (255, 165, 0)

# World themes
WORLD_COLORS = [
    (135, 206, 235),  # World 1: Sky Blue
    (255, 228, 181),  # World 2: Desert
    (0, 100, 0),      # World 3: Forest Green
    (70, 130, 180),   # World 4: Ice Blue
    (139, 0, 0)       # World 5: Lava Red
]

class Player:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 30, 40)
        self.vel_y = 0
        self.on_ground = False
        self.facing_right = True
        self.animation_timer = 0
        
    def update(self, platforms):
        keys = pygame.key.get_pressed()
        
        # Horizontal movement
        if keys[pygame.K_LEFT]:
            self.rect.x -= MOVE_SPEED
            self.facing_right = False
        if keys[pygame.K_RIGHT]:
            self.rect.x += MOVE_SPEED
            self.facing_right = True
            
        # Jumping
        if keys[pygame.K_SPACE] and self.on_ground:
            self.vel_y = JUMP_STRENGTH
            
        # Apply gravity
        self.vel_y += GRAVITY
        self.rect.y += self.vel_y
        
        # Collision with platforms
        self.on_ground = False
        for platform in platforms:
            if self.rect.colliderect(platform):
                if self.vel_y > 0:  # Falling
                    self.rect.bottom = platform.top
                    self.vel_y = 0
                    self.on_ground = True
                elif self.vel_y < 0:  # Jumping
                    self.rect.top = platform.bottom
                    self.vel_y = 0
                    
        # Keep player on screen
        self.rect.x = max(0, min(self.rect.x, SCREEN_WIDTH - self.rect.width))
        
        # Animation timer
        self.animation_timer += 1
        
    def draw(self, screen, camera_x):
        # Paper Mario style flat character
        draw_rect = self.rect.copy()
        draw_rect.x -= camera_x
        
        # Body
        pygame.draw.rect(screen, RED, draw_rect)
        
        # Paper effect - white outline
        pygame.draw.rect(screen, WHITE, draw_rect, 2)
        
        # Simple face
        eye_y = draw_rect.y + 10
        if self.facing_right:
            pygame.draw.circle(screen, WHITE, (draw_rect.x + 20, eye_y), 3)
            pygame.draw.circle(screen, BLACK, (draw_rect.x + 22, eye_y), 2)
        else:
            pygame.draw.circle(screen, WHITE, (draw_rect.x + 10, eye_y), 3)
            pygame.draw.circle(screen, BLACK, (draw_rect.x + 8, eye_y), 2)

class Enemy:
    def __init__(self, x, y, patrol_width=100):
        self.rect = pygame.Rect(x, y, 30, 30)
        self.vel_x = 2
        self.start_x = x
        self.patrol_width = patrol_width
        
    def update(self):
        self.rect.x += self.vel_x
        if abs(self.rect.x - self.start_x) > self.patrol_width:
            self.vel_x *= -1
            
    def draw(self, screen, camera_x):
        draw_rect = self.rect.copy()
        draw_rect.x -= camera_x
        pygame.draw.rect(screen, PURPLE, draw_rect)
        pygame.draw.rect(screen, WHITE, draw_rect, 2)

class Coin:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 20, 20)
        self.collected = False
        self.bob_timer = random.uniform(0, math.pi * 2)
        
    def update(self):
        self.bob_timer += 0.1
        
    def draw(self, screen, camera_x):
        if not self.collected:
            draw_x = self.rect.x - camera_x
            draw_y = self.rect.y + math.sin(self.bob_timer) * 3
            pygame.draw.circle(screen, YELLOW, (draw_x + 10, int(draw_y) + 10), 10)
            pygame.draw.circle(screen, ORANGE, (draw_x + 10, int(draw_y) + 10), 10, 2)

class Level:
    def __init__(self, world_num, level_num):
        self.world_num = world_num
        self.level_num = level_num
        self.platforms = []
        self.enemies = []
        self.coins = []
        self.goal_rect = None
        self.width = 2000
        self.completed = False
        self.generate_level()
        
    def generate_level(self):
        # Ground platforms
        for i in range(0, self.width, 100):
            self.platforms.append(pygame.Rect(i, 500, 100, 100))
            
        # Additional platforms based on world/level
        platform_count = 5 + self.world_num * 2 + self.level_num
        for i in range(platform_count):
            x = 200 + i * 150
            y = 350 - (i % 3) * 80
            width = 80 + (i % 2) * 40
            self.platforms.append(pygame.Rect(x, y, width, 20))
            
        # Enemies
        enemy_count = 2 + self.world_num + self.level_num
        for i in range(enemy_count):
            x = 300 + i * 200
            y = 470
            self.enemies.append(Enemy(x, y))
            
        # Coins
        coin_count = 5 + self.level_num * 2
        for i in range(coin_count):
            x = 150 + i * 120
            y = 300 + (i % 3) * 50
            self.coins.append(Coin(x, y))
            
        # Goal
        self.goal_rect = pygame.Rect(self.width - 100, 400, 50, 100)
        
    def draw(self, screen, camera_x):
        # Background
        screen.fill(WORLD_COLORS[self.world_num])
        
        # Platforms
        for platform in self.platforms:
            draw_rect = platform.copy()
            draw_rect.x -= camera_x
            color = BROWN if self.world_num < 3 else (BLUE if self.world_num == 3 else BLACK)
            pygame.draw.rect(screen, color, draw_rect)
            pygame.draw.rect(screen, WHITE, draw_rect, 2)
            
        # Goal flag
        if self.goal_rect:
            draw_rect = self.goal_rect.copy()
            draw_rect.x -= camera_x
            pygame.draw.rect(screen, GREEN, draw_rect)
            pygame.draw.rect(screen, WHITE, draw_rect, 3)
            # Flag pole
            pygame.draw.line(screen, BLACK, (draw_rect.x + 25, draw_rect.y), 
                           (draw_rect.x + 25, draw_rect.bottom), 3)

class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Paper Mario 2D Bros")
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = "MENU"  # MENU, LEVEL_SELECT, PLAYING
        self.current_world = 0
        self.current_level_num = 0
        self.levels = self.create_all_levels()
        self.current_level = None
        self.player = None
        self.camera_x = 0
        self.coins_collected = 0
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        
    def create_all_levels(self):
        levels = {}
        for world in range(5):
            for level in range(3):
                levels[(world, level)] = Level(world, level)
        return levels
        
    def start_level(self, world, level_num):
        self.current_world = world
        self.current_level_num = level_num
        self.current_level = self.levels[(world, level_num)]
        self.player = Player(100, 400)
        self.camera_x = 0
        self.state = "PLAYING"
        
    def update_playing(self):
        if not self.current_level:
            return
            
        # Update player
        self.player.update(self.current_level.platforms)
        
        # Update camera
        target_camera = self.player.rect.x - SCREEN_WIDTH // 2
        self.camera_x = max(0, min(target_camera, self.current_level.width - SCREEN_WIDTH))
        
        # Update enemies
        for enemy in self.current_level.enemies:
            enemy.update()
            if self.player.rect.colliderect(enemy.rect):
                # Reset to level start
                self.player.rect.x = 100
                self.player.rect.y = 400
                self.camera_x = 0
                
        # Update and collect coins
        for coin in self.current_level.coins:
            if not coin.collected:
                coin.update()
                if self.player.rect.colliderect(coin.rect):
                    coin.collected = True
                    self.coins_collected += 1
                    
        # Check goal
        if self.current_level.goal_rect and self.player.rect.colliderect(self.current_level.goal_rect):
            self.current_level.completed = True
            self.state = "LEVEL_SELECT"
            
        # Return to menu
        if pygame.key.get_pressed()[pygame.K_ESCAPE]:
            self.state = "LEVEL_SELECT"
            
    def draw_menu(self):
        self.screen.fill(SKY_BLUE)
        
        # Title
        title = self.font.render("PAPER MARIO 2D BROS", True, WHITE)
        title_rect = title.get_rect(center=(SCREEN_WIDTH//2, 150))
        self.screen.blit(title, title_rect)
        
        # Paper effect decoration
        for i in range(5):
            x = 150 + i * 120
            y = 250
            pygame.draw.rect(self.screen, WHITE, (x, y, 80, 100))
            pygame.draw.rect(self.screen, RED, (x+5, y+5, 70, 90))
            
        # Instructions
        start_text = self.small_font.render("Press ENTER to Start", True, WHITE)
        start_rect = start_text.get_rect(center=(SCREEN_WIDTH//2, 400))
        self.screen.blit(start_text, start_rect)
        
        controls = [
            "Arrow Keys: Move",
            "Space: Jump",
            "ESC: Return to Menu"
        ]
        for i, control in enumerate(controls):
            text = self.small_font.render(control, True, WHITE)
            self.screen.blit(text, (SCREEN_WIDTH//2 - 100, 450 + i * 30))
            
    def draw_level_select(self):
        self.screen.fill(BLUE)
        
        # Title
        title = self.font.render("SELECT LEVEL", True, WHITE)
        title_rect = title.get_rect(center=(SCREEN_WIDTH//2, 50))
        self.screen.blit(title, title_rect)
        
        # Draw world/level grid SMB Deluxe style
        for world in range(5):
            world_y = 120 + world * 90
            
            # World label
            world_text = self.small_font.render(f"WORLD {world + 1}", True, WHITE)
            self.screen.blit(world_text, (50, world_y))
            
            for level in range(3):
                level_x = 250 + level * 120
                
                # Level box
                level_data = self.levels[(world, level)]
                if level_data.completed:
                    color = GREEN
                elif world == 0 or self.levels[(max(0, world-1), 2)].completed:
                    color = YELLOW  # Available
                else:
                    color = RED  # Locked
                    
                pygame.draw.rect(self.screen, color, (level_x, world_y, 80, 60))
                pygame.draw.rect(self.screen, WHITE, (level_x, world_y, 80, 60), 3)
                
                # Level number
                level_text = self.small_font.render(f"{level + 1}", True, WHITE)
                text_rect = level_text.get_rect(center=(level_x + 40, world_y + 30))
                self.screen.blit(level_text, text_rect)
                
        # Instructions
        inst_text = self.small_font.render("Click a level or press number keys", True, WHITE)
        self.screen.blit(inst_text, (SCREEN_WIDTH//2 - 150, SCREEN_HEIGHT - 50))
        
    def draw_playing(self):
        if not self.current_level:
            return
            
        # Draw level
        self.current_level.draw(self.screen, self.camera_x)
        
        # Draw enemies
        for enemy in self.current_level.enemies:
            enemy.draw(self.screen, self.camera_x)
            
        # Draw coins
        for coin in self.current_level.coins:
            coin.draw(self.screen, self.camera_x)
            
        # Draw player
        self.player.draw(self.screen, self.camera_x)
        
        # HUD
        hud_text = f"World {self.current_world + 1}-{self.current_level_num + 1}  Coins: {self.coins_collected}"
        text = self.small_font.render(hud_text, True, WHITE)
        pygame.draw.rect(self.screen, BLACK, (10, 10, 300, 30))
        self.screen.blit(text, (15, 15))
        
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                
            if event.type == pygame.KEYDOWN:
                if self.state == "MENU":
                    if event.key == pygame.K_RETURN:
                        self.state = "LEVEL_SELECT"
                        
                elif self.state == "LEVEL_SELECT":
                    # Quick number key selection
                    if event.key >= pygame.K_1 and event.key <= pygame.K_5:
                        world = event.key - pygame.K_1
                        self.start_level(world, 0)
                    elif event.key == pygame.K_ESCAPE:
                        self.state = "MENU"
                        
            if event.type == pygame.MOUSEBUTTONDOWN and self.state == "LEVEL_SELECT":
                mx, my = event.pos
                for world in range(5):
                    world_y = 120 + world * 90
                    for level in range(3):
                        level_x = 250 + level * 120
                        rect = pygame.Rect(level_x, world_y, 80, 60)
                        if rect.collidepoint(mx, my):
                            # Check if level is unlocked
                            if world == 0 or self.levels[(max(0, world-1), 2)].completed:
                                self.start_level(world, level)
                                
    def run(self):
        while self.running:
            self.handle_events()
            
            if self.state == "PLAYING":
                self.update_playing()
                
            # Draw
            if self.state == "MENU":
                self.draw_menu()
            elif self.state == "LEVEL_SELECT":
                self.draw_level_select()
            elif self.state == "PLAYING":
                self.draw_playing()
                
            pygame.display.flip()
            self.clock.tick(FPS)
            
        pygame.quit()
        sys.exit()

# Main execution
if __name__ == "__main__":
    game = Game()
    game.run()
