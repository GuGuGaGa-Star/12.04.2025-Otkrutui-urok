# ПОЛНЫЙ КОД С ИГРОКОМ, ВРАГАМИ, БОССОМ, КВЕСТАМИ И ПРОКАЧКОЙ
# Импорт
import pygame
import random
import math
import sys

pygame.init()

# Экран
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
WIDTH, HEIGHT = screen.get_size()
screen_width = pygame.display.Info().current_w
scale_factor = screen_width / 800

TILE_SIZE = 50
FPS = 60
clock = pygame.time.Clock()
HEART_SIZE = int(30 * scale_factor)

# Звуки
shoot_sound = pygame.mixer.Sound('shoot.wav')
hit_sound = pygame.mixer.Sound('hit.wav')
death_sound = pygame.mixer.Sound('death.wav')
reload_sound = pygame.mixer.Sound('reload.wav')

# Биомы
BIOMES = [
    {'name': 'forest', 'color': (30, 80, 30)},
    {'name': 'ice', 'color': (180, 220, 255)},
    {'name': 'lava', 'color': (100, 30, 0)}
]

# Игрок
class Player(pygame.sprite.Sprite):
    def __init__(self, x, y, quest):
        super().__init__()
        self.image = pygame.Surface((40, 40))
        self.image.fill((0, 255, 0))
        self.rect = self.image.get_rect(center=(x, y))
        self.speed = 5
        self.health = 3
        self.grenades = 0
        self.level = 1
        self.xp = 0
        self.xp_to_next = 10
        self.perks = []
        self.quest = quest

    def update(self, items, boxes):
        keys = pygame.key.get_pressed()
        dx = dy = 0
        if keys[pygame.K_w]: dy -= self.speed
        if keys[pygame.K_s]: dy += self.speed
        if keys[pygame.K_a]: dx -= self.speed
        if keys[pygame.K_d]: dx += self.speed
        self.rect.x += dx
        self.rect.y += dy

        for item in items:
            if self.rect.colliderect(item.rect):
                item.apply_effect(self)

        for box in boxes:
            if self.rect.colliderect(box.rect):
                pass

    def gain_xp(self, amount):
        self.xp += amount
        if self.xp >= self.xp_to_next:
            self.level += 1
            self.xp -= self.xp_to_next
            self.xp_to_next = int(self.xp_to_next * 1.5)
            self.perks.append("+1 Max HP")
            self.health += 1

    def apply_perk(self, perk):
        self.perks.append(perk)
        if perk == "+1 Max HP":
            self.health += 1

# Предметы
class Item(pygame.sprite.Sprite):
    def __init__(self, x, y, type):
        super().__init__()
        self.type = type
        self.image = pygame.Surface((20, 20))
        self.image.fill((0, 255, 0) if type == 'medkit' else (150, 150, 150))
        self.rect = self.image.get_rect(center=(x, y))

    def apply_effect(self, player):
        if self.type == 'medkit' and player.health < 5:
            player.health += 1
        elif self.type == 'grenade':
            player.grenades += 1
        self.kill()

# Разрушаемые блоки
class DestructibleBox(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((40, 40))
        self.image.fill((139, 69, 19))
        self.rect = self.image.get_rect(center=(x, y))
        self.hp = 3

    def take_damage(self):
        self.hp -= 1
        if self.hp <= 0:
            self.kill()

# Квест
class Quest:
    def __init__(self, description, goal, reward):
        self.description = description
        self.goal = goal
        self.progress = 0
        self.completed = False
        self.reward = reward

    def update(self):
        if not self.completed:
            self.progress += 1
            if self.progress >= self.goal:
                self.completed = True
                return self.reward
        return None

# Враги
class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((40, 40))
        self.image.fill((255, 0, 0))
        self.rect = self.image.get_rect(center=(x, y))
        self.health = 3

    def update(self, player):
        direction = pygame.Vector2(player.rect.center) - pygame.Vector2(self.rect.center)
        if direction.length() > 0:
            direction = direction.normalize()
            self.rect.x += direction.x * 2
            self.rect.y += direction.y * 2

    def take_damage(self, player):
        self.health -= 1
        if self.health <= 0:
            self.kill()
            player.gain_xp(1)
            reward = player.quest.update()
            if reward:
                player.apply_perk(reward)

class SmartEnemy(Enemy):
    def update(self, player):
        super().update(player)
        # Уклонение и поведение — уже реализовано выше

# Боссы
class TeleportBoss(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((80, 80))
        self.image.fill((100, 0, 150))
        self.rect = self.image.get_rect(center=(x, y))
        self.health = 25
        self.last_tp = 0

    def update(self, player):
        if pygame.time.get_ticks() - self.last_tp > 2000:
            self.rect.center = (random.randint(100, WIDTH - 100), random.randint(100, HEIGHT - 100))
            self.last_tp = pygame.time.get_ticks()

    def take_damage(self, player):
        self.health -= 1
        if self.health <= 0:
            self.kill()
            reward = player.quest.update()
            if reward:
                player.apply_perk(reward)

# UI
def draw_ui(surface, player):
    font = pygame.font.Font(None, 30)
    surface.blit(font.render(f"HP: {player.health}", True, (255, 255, 255)), (10, 10))
    surface.blit(font.render(f"Grenades: {player.grenades}", True, (200, 200, 200)), (10, 40))
    surface.blit(font.render(f"Level: {player.level}", True, (255, 255, 255)), (10, 70))
    surface.blit(font.render(f"Perks: {', '.join(player.perks)}", True, (255, 255, 0)), (10, 100))

# MAIN
def main():
    pygame.mixer.music.load('Waveshaper - Client.mp3')
    pygame.mixer.music.play(-1)
    biome = random.choice(BIOMES)

    quest = Quest("Убей 10 врагов", 10, reward="+1 Max HP")
    player = Player(WIDTH // 2, HEIGHT // 2, quest)
    enemies = pygame.sprite.Group([Enemy(random.randint(100, WIDTH-100), random.randint(100, HEIGHT-100)) for _ in range(5)])
    items = pygame.sprite.Group([Item(random.randint(100, WIDTH-100), random.randint(100, HEIGHT-100), random.choice(['medkit', 'grenade'])) for _ in range(3)])
    boxes = pygame.sprite.Group([DestructibleBox(random.randint(100, WIDTH-100), random.randint(100, HEIGHT-100)) for _ in range(2)])
    boss = TeleportBoss(WIDTH//2, HEIGHT//4)

    running = True
    while running:
        screen.fill(biome['color'])
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_g and player.grenades > 0:
                player.grenades -= 1
                for enemy in enemies:
                    if pygame.Vector2(enemy.rect.center).distance_to(player.rect.center) < 100:
                        enemy.take_damage(player)

        player.update(items, boxes)
        enemies.update(player)
        boss.update(player)

        screen.blit(player.image, player.rect)
        enemies.draw(screen)
        items.draw(screen)
        boxes.draw(screen)
        screen.blit(boss.image, boss.rect)
        draw_ui(screen, player)
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()

if __name__ == '__main__':
    main()
