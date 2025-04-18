import pygame
import random
import math
import sys

pygame.init()

WIDTH, HEIGHT = 800, 600
TILE_SIZE = 50
FPS = 60

screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

directions = {'UP': (0, HEIGHT - 40), 'DOWN': (0, -HEIGHT + 40), 'LEFT': (WIDTH - 40, 0), 'RIGHT': (-WIDTH + 40, 0)}

RELOAD_EVENT = pygame.USEREVENT + 1
HEART_SIZE = 30

shoot_sound = pygame.mixer.Sound('shoot.wav')
hit_sound = pygame.mixer.Sound('hit.wav')
death_sound = pygame.mixer.Sound('death.wav')
reload_sound = pygame.mixer.Sound('reload.wav')

# ===== ФУНКЦИЯ ВИДИМОСТИ =====
def has_line_of_sight(start_pos, end_pos, walls):
    line = pygame.Rect(0, 0, 1, 1)
    steps = int(pygame.Vector2(end_pos).distance_to(start_pos) // 5)
    for i in range(steps):
        x = start_pos[0] + (end_pos[0] - start_pos[0]) * i / steps
        y = start_pos[1] + (end_pos[1] - start_pos[1]) * i / steps
        point = pygame.Rect(x, y, 2, 2)
        if any(point.colliderect(wall) for wall in walls):
            return False
    return True

class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((40, 40))
        self.image.fill((0, 255, 0))
        self.rect = self.image.get_rect(center=(x, y))
        self.speed = 5
        self.ammo = 6
        self.reloading = False
        self.health = 3
        self.last_reload_time = 0
        self.weapons = ["pistol", "shotgun"]
        self.current_weapon = 0
        self.alive = True
        self.dead_enemy = 0
        self.weapon_images = {
            "pistol": pygame.transform.scale(pygame.image.load("pistol.png"), (40, 15)),
            "shotgun": pygame.transform.scale(pygame.image.load("shotgun.png"), (50, 20))
        }
        self.weapon_offset = 25

    def update(self, keys, walls, current_time):
        if not self.alive:
            return  # Поки мертвий, не рухаємося
        old_rect = self.rect.copy()
        if keys[pygame.K_w]: self.rect.y -= self.speed
        if keys[pygame.K_s]: self.rect.y += self.speed
        if keys[pygame.K_a]: self.rect.x -= self.speed
        if keys[pygame.K_d]: self.rect.x += self.speed
        for wall in walls:
            if self.rect.colliderect(wall):
                self.rect = old_rect
                break
        if self.reloading and current_time - self.last_reload_time >= 1000:
            self.ammo = 6
            self.reloading = False

    def draw_weapon(self, surface, mouse_pos):
        current_weapon_name = self.weapons[self.current_weapon]
        weapon_image = self.weapon_images[current_weapon_name]

        dx = mouse_pos[0] - self.rect.centerx
        dy = mouse_pos[1] - self.rect.centery
        angle = math.degrees(math.atan2(dy, dx))

        rotated_image = pygame.transform.rotate(weapon_image, -angle)
        rotated_rect = rotated_image.get_rect()

        offset_x = math.cos(math.radians(angle)) * self.weapon_offset
        offset_y = math.sin(math.radians(angle)) * self.weapon_offset
        weapon_pos = (self.rect.centerx + offset_x - rotated_rect.width // 2,
                      self.rect.centery + offset_y - rotated_rect.height // 2)

        surface.blit(rotated_image, weapon_pos)

    def shoot(self, bullets, target_pos):
        if not self.alive:
            return  # Не стріляємо, коли мертвий
        if self.weapons[self.current_weapon] == "shotgun":
            if self.ammo >= 3 and not self.reloading:
                shoot_sound.play()
                for _ in range(5):
                    spread_angle = random.uniform(-15, 15)
                    angle = math.atan2(target_pos[1] - self.rect.centery, target_pos[0] - self.rect.centerx)
                    angle += math.radians(spread_angle)
                    dx = math.cos(angle) * 10
                    dy = math.sin(angle) * 10
                    bullet = Bullet(self.rect.centerx, self.rect.centery,
                                    (self.rect.centerx + dx, self.rect.centery + dy), "player", is_shotgun=True)
                    bullets.add(bullet)
                self.ammo -= 3
            elif self.ammo < 3 and not self.reloading:
                self.reload()
        else:
            if self.ammo > 0 and not self.reloading:
                shoot_sound.play()
                bullet = Bullet(self.rect.centerx, self.rect.centery, target_pos, "player")
                bullets.add(bullet)
                self.ammo -= 1
            elif self.ammo == 0 and not self.reloading:
                self.reload()

    def reload(self):
        self.reloading = True
        self.last_reload_time = pygame.time.get_ticks()
        reload_sound.play()

    def draw_current_weapon(surface, player, x, y):
        font = pygame.font.Font(None, 30)
        weapon_text = font.render(f"Weapon: {player.weapons[player.current_weapon]}", True, (255, 255, 255))
        surface.blit(weapon_text, (x, y))

    def take_damage(self):
        hit_sound.play()
        self.health -= 1
        if self.health <= 0:
            death_sound.play()
            self.alive = False  # Персонаж вмирає, але залишається на екрані

    def reset(self, x, y):
        self.health = 3
        self.rect.center = (x, y)
        self.ammo = 6
        self.reloading = False
        self.alive = True  # Відновлюємо персонажа

    def switch_weapon(self, direction):
        self.current_weapon = (self.current_weapon + direction) % len(self.weapons)
        print("Текущее оружие:", self.weapons[self.current_weapon])


class BloodParticle(pygame.sprite.Sprite):
    def __init__(self, x, y, dx, dy, color=(255, 0, 0)):
        super().__init__()
        self.image = pygame.Surface((5, 5), pygame.SRCALPHA)  # Прозрачный фон для крови
        self.color = color
        self.image.fill(self.color)
        self.rect = self.image.get_rect(center=(x, y))
        self.dx = dx
        self.dy = dy
        self.life_time = random.randint(30, 60)  # Случайное время жизни для разнообразия
        self.size = random.randint(3, 6)  # Случайный размер частицы
        self.alpha = 255  # Прозрачность

    def update(self):
        # Двигаем частицу
        self.rect.x += self.dx
        self.rect.y += self.dy

        # Уменьшаем время жизни и размер
        self.life_time -= 1
        self.alpha -= 5  # Уменьшаем прозрачность

        # Применяем изменения размера и прозрачности
        self.image = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        pygame.draw.circle(self.image, self.color, (self.size // 2, self.size // 2), self.size // 2)
        self.image.set_alpha(self.alpha)

        if self.life_time <= 0 or self.alpha <= 0:
            self.kill()  # Убираем частицу, когда она исчезает

class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, target_pos, shooter, is_shotgun=False):
        super().__init__()
        self.image = pygame.Surface((10, 10))
        self.image.fill((255, 255, 0))  # Желтый цвет пули
        self.rect = self.image.get_rect(center=(x, y))
        self.speed = 10
        self.shooter = shooter
        self.origin = pygame.Vector2(x, y)
        self.is_shotgun = is_shotgun
        angle = math.atan2(target_pos[1] - y, target_pos[0] - x)
        self.dx = math.cos(angle) * self.speed
        self.dy = math.sin(angle) * self.speed

    def update(self):
        self.rect.x += self.dx
        self.rect.y += self.dy
        if not (0 <= self.rect.x <= WIDTH and 0 <= self.rect.y <= HEIGHT):
            self.kill()

    def check_collision(self, target):
        if self.rect.colliderect(target.rect):
            if self.is_shotgun:
                distance = self.origin.distance_to(pygame.Vector2(target.rect.center))
                if distance < 100:
                    target.take_damage()
                    # Генерация зелёной крови при попадании
                    self.create_blood_splash(target)
                elif distance < 200:
                    if random.random() < 0.5:
                        target.take_damage()
                        self.create_blood_splash(target)
            else:
                target.take_damage()
                # Генерация зелёной крови при попадании
                self.create_blood_splash(target)
            self.kill()

    def create_blood_splash(self, target):
        # Создаем несколько частиц крови, которые будут разбегаться
        for _ in range(10):  # Количество частиц
            dx = random.uniform(-2, 2)
            dy = random.uniform(-2, 2)
            blood_particle = BloodParticle(target.rect.centerx, target.rect.centery, dx, dy)
            blood_particles.add(blood_particle)

# Создание группы для частиц крови
blood_particles = pygame.sprite.Group()


class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((40, 40))
        self.image.fill((255, 0, 0))
        self.rect = self.image.get_rect(center=(x, y))
        self.speed = 2
        self.shoot_delay = 1000
        self.last_shot_time = pygame.time.get_ticks()
        self.health = 3

    def update(self, player, bullets, current_time):
        if pygame.sprite.collide_rect(self, player):
            if self.rect.centerx < player.rect.centerx:
                self.rect.x += self.speed
            elif self.rect.centerx > player.rect.centerx:
                self.rect.x -= self.speed
            if self.rect.centery < player.rect.centery:
                self.rect.y += self.speed
            elif self.rect.centery > player.rect.centery:
                self.rect.y -= self.speed

        if current_time - self.last_shot_time >= self.shoot_delay:
            self.shoot(bullets, player.rect.center)
            self.last_shot_time = current_time

    def shoot(self, bullets, target_pos):
        bullet = Bullet(self.rect.centerx, self.rect.centery, target_pos, "enemy")
        bullets.add(bullet)

    def take_damage(self):
        hit_sound.play()
        self.health -= 1
        if self.health <= 0:
            death_sound.play()
            self.kill()

class ChasingEnemy(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((40, 40))
        self.image.fill((0, 0, 255))  # Синий для отличия
        self.rect = self.image.get_rect(center=(x, y))
        self.speed = 3
        self.shoot_delay = 1000
        self.last_shot_time = pygame.time.get_ticks()
        self.health = 3

    def update(self, player, bullets, current_time, walls):
        if has_line_of_sight(self.rect.center, player.rect.center, walls):
            direction = pygame.Vector2(player.rect.center) - pygame.Vector2(self.rect.center)
            if direction.length() > 0:
                direction = direction.normalize()
                self.rect.x += direction.x * self.speed
                self.rect.y += direction.y * self.speed

        if current_time - self.last_shot_time >= self.shoot_delay:
            if has_line_of_sight(self.rect.center, player.rect.center, walls):
                self.shoot(bullets, player.rect.center)
                self.last_shot_time = current_time

    def shoot(self, bullets, target_pos):
        bullet = Bullet(self.rect.centerx, self.rect.centery, target_pos, "enemy")
        bullets.add(bullet)

    def take_damage(self):
        hit_sound.play()
        self.health -= 1
        if self.health <= 0:
            death_sound.play()
            self.kill()

class Game:
    def __init__(self):
        self.level = 1
        self.enemy_count = 2
        self.enemy_speed = 2
        self.enemy_health = 3

def check_room_transition(player, room):
    transition_dir = None
    if player.rect.left > WIDTH:
        transition_dir = 'RIGHT'
    elif player.rect.right < 0:
        transition_dir = 'LEFT'
    elif player.rect.top > HEIGHT:
        transition_dir = 'DOWN'
    elif player.rect.bottom < 0:
        transition_dir = 'UP'

    if transition_dir:
        transition()
        new_room = Room()
        player.rect.x += directions[transition_dir][0]
        player.rect.y += directions[transition_dir][1]
        while any(player.rect.colliderect(wall) for wall in new_room.walls):
            player.rect.y -= 5
        return new_room
    return room

class Room:
    room_count = 0  # Статическая переменная, чтобы отслеживать прогресс

    def __init__(self):
        Room.room_count += 1
        self.walls = self.generate_walls()
        self.enemies = pygame.sprite.Group()

        # Кол-во обычных врагов
        normal_count = min(3 + Room.room_count // 1, 3)
        # Кол-во синих врагов
        chasing_count = min(Room.room_count // 1, 2)

        for _ in range(normal_count):
            self.enemies.add(Enemy(random.randint(50, WIDTH - 50), random.randint(50, HEIGHT - 50)))
        for _ in range(chasing_count):
            self.enemies.add(ChasingEnemy(random.randint(50, WIDTH - 50), random.randint(50, HEIGHT - 50)))

    def generate_walls(self):
        walls = []
        for _ in range(3):
            width = random.randint(200, 400)
            height = 20 if random.choice([True, False]) else random.randint(100, 300)
            x = random.randint(50, WIDTH - width - 50)
            y = random.randint(50, HEIGHT - height - 50)
            new_wall = pygame.Rect(x, y, width, height)
            if not any(new_wall.colliderect(w) for w in walls):
                walls.append(new_wall)
        return walls

    def draw(self, surface):
        for wall in self.walls:
            pygame.draw.rect(surface, (127, 180, 240), wall)

def draw_health_bar(surface, health, x, y):
    for i in range(health):
        pygame.draw.rect(surface, (255, 0, 0), (x + i * (HEART_SIZE + 5), y, HEART_SIZE, HEART_SIZE))
        pygame.draw.rect(surface, (255, 255, 255), (x + i * (HEART_SIZE + 5), y, HEART_SIZE, HEART_SIZE), 2)


def transition():
    for alpha in range(0, 255, 10):
        fade = pygame.Surface((WIDTH, HEIGHT))
        fade.fill((0, 0, 0))
        fade.set_alpha(alpha)
        screen.blit(fade, (0, 0))
        pygame.display.update()
        pygame.time.delay(20)


def pause_game():
    paused = True
    font = pygame.font.Font(None, 74)
    pause_text = font.render("PAUSED", True, (255, 0, 0))
    while paused:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_p:
                paused = False

        screen.fill((0, 0, 0))
        screen.blit(pause_text, (WIDTH // 2 - pause_text.get_width() // 2, HEIGHT // 2 - pause_text.get_height() // 2))
        pygame.display.update()
        clock.tick(5)


def draw_ammo_bar(surface, ammo, reloading, x, y):
    for i in range(6):
        color = (255, 255, 0) if i < ammo else (100, 100, 100)
        pygame.draw.rect(surface, color, (x + i * 20, y, 15, 30))
        pygame.draw.rect(surface, (255, 255, 255), (x + i * 20, y, 15, 30), 2)

    if reloading:
        font = pygame.font.Font(None, 30)
        reload_text = font.render("Reloading...", True, (255, 0, 0))
        surface.blit(reload_text, (x, y + 30))



def show_main_menu():
    font = pygame.font.Font(None, 74)
    title_text = font.render("Main Menu", True, (255, 255, 255))
    start_text = font.render("Press Enter to Start", True, (255, 255, 255))

    while True:
        screen.fill((0, 0, 0))
        screen.blit(title_text, (WIDTH // 2 - title_text.get_width() // 2, HEIGHT // 3))
        screen.blit(start_text, (WIDTH // 2 - start_text.get_width() // 2, HEIGHT // 2))

        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    return  # Переходимо до гри



    while True:
        screen.fill((0, 0, 0))
        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return


def main():
    running = True
    game = Game()
    player = Player(WIDTH // 2, HEIGHT // 2)
    room = Room()
    bullets = pygame.sprite.Group()
    enemy_bullets = pygame.sprite.Group()
    all_sprites = pygame.sprite.Group(player)

    while running:
        screen.fill((30, 30, 30))
        keys = pygame.key.get_pressed()
        current_time = pygame.time.get_ticks()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                player.shoot(bullets, pygame.mouse.get_pos())
            if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                if not player.alive:
                    player.reset(WIDTH // 2, HEIGHT // 2)
                    room = Room()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_p:
                pause_game()
            if event.type == pygame.MOUSEWHEEL:
                player.switch_weapon(event.y)
            if event.type == pygame.KEYDOWN and event.key == pygame.K_m:
                show_main_menu()

        room = check_room_transition(player, room)

        all_sprites.update(keys, room.walls, current_time)

        for enemy in room.enemies:
            if isinstance(enemy, ChasingEnemy):
                enemy.update(player, enemy_bullets, current_time, room.walls)
            else:
                enemy.update(player, enemy_bullets, current_time)

        bullets.update()
        enemy_bullets.update()

        for bullet in bullets:
            for enemy in room.enemies:
                bullet.check_collision(enemy)
        for bullet in enemy_bullets:
            if bullet.shooter == "enemy" and bullet.rect.colliderect(player.rect):
                player.take_damage()
                bullet.kill()

        # Обновляем и рисуем частицы крови
        blood_particles.update()
        blood_particles.draw(screen)

        if player.health <= 0:
            for enemy in room.enemies:
                enemy.shoot_delay = float('inf')
            font = pygame.font.Font(None, 74)
            restart_text = font.render("You Lost! Press R to Restart", True, (255, 255, 255))
            screen.blit(restart_text, (WIDTH // 2 - restart_text.get_width() // 2, HEIGHT // 2))

        draw_health_bar(screen, player.health, 10, 10)
        draw_ammo_bar(screen, player.ammo, player.reloading, 10, HEIGHT - 50)

        room.draw(screen)
        room.enemies.draw(screen)
        all_sprites.draw(screen)
        bullets.draw(screen)
        enemy_bullets.draw(screen)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()