import pygame
import random
import math
import sys

pygame.init()

screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
WIDTH, HEIGHT = screen.get_size()
screen_width = pygame.display.Info().current_w
scale_factor = screen_width / 800

TILE_SIZE = 50
FPS = 60

clock = pygame.time.Clock()

HEART_SIZE = int(30 * scale_factor)
directions = {
    'UP': (0, HEIGHT - 40),
    'DOWN': (0, -HEIGHT + 40),
    'LEFT': (WIDTH - 40, 0),
    'RIGHT': (-WIDTH + 40, 0)
}
global ammo_bonus
RELOAD_EVENT = pygame.USEREVENT + 1
HEART_SIZE = 30

shoot_sound = pygame.mixer.Sound('shoot.wav')
hit_sound = pygame.mixer.Sound('hit.wav')
death_sound = pygame.mixer.Sound('death.wav')
reload_sound = pygame.mixer.Sound('reload.wav')
buy_sound = pygame.mixer.Sound('buy.wav')

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
        self.speed = 6
        self.ammo = 6
        self.reloading = False
        self.health = 3
        self.last_reload_time = 0
        self.current_weapon = 0
        self.alive = True
        self.dead_enemy = 0
        self.weapons = ["pistol", "shotgun"]
        self.unlocked_weapons = ["pistol", "shotgun"]
        self.weapon_images = {
            "pistol": pygame.transform.scale(pygame.image.load("pistol.png"), (40, 15)),
            "shotgun": pygame.transform.scale(pygame.image.load("shotgun.png"), (int(screen_width // 16), int(scale_factor * 25))),
            "smg": pygame.transform.scale(pygame.image.load("smg.png"), (int(screen_width // 12), int(scale_factor * 15))),
            "laser": pygame.transform.scale(pygame.image.load("laser.png"), (int(screen_width // 14), int(scale_factor * 18))),
            "rocket": pygame.transform.scale(pygame.image.load("rocket.png"), (int(screen_width // 16), int(scale_factor * 25)))
        }
        self.weapon_offset = 25
        self.invincible_time = 0
        self.dodge_cooldown = 0
        self.dodge_duration = 150
        self.direction = pygame.Vector2(0, 0)
        self.dodging = False
        self.dodge_start_time = 0
        self.rotation_angle = 0
        self.rotation_speed = 100
        self.room = Room
        self.xp = 0
        self.level = 1
        self.xp_to_next = 10
        self.perks = []
        self.choosing_perk = False
        self.perk_options = []
        self.bullet_bounce = False
        self.extra_projectiles = False
        self.crit_chance = 0.0
        self.DodgePlus = 0
        self.reload_time = 0
        self.just_took_damage = False
        self.damage_effect_time = 0
        self.chips = 0
        self.relic = None

    def update(self, keys, walls, current_time):
        if not self.alive:
            return

        if self.dodging:

            if current_time - self.dodge_start_time < self.dodge_duration:

                elapsed_time = (current_time - self.dodge_start_time) / 1000
                self.rotation_angle += self.rotation_speed * elapsed_time


                self.rotation_angle = self.rotation_angle % 360


                self.rect.x += self.direction.x * 10
                self.rect.y += self.direction.y * 10
            else:

                self.dodging = False
                self.rotation_angle = 0

        else:

            old_rect = self.rect.copy()
            self.direction = pygame.Vector2(0, 0)
            if keys[pygame.K_w]: self.direction.y = -1
            if keys[pygame.K_s]: self.direction.y = 1
            if keys[pygame.K_a]: self.direction.x = -1
            if keys[pygame.K_d]: self.direction.x = 1

            if self.direction.length() > 0:
                self.direction.normalize_ip()


            self.rect.x += self.direction.x * self.speed
            self.rect.y += self.direction.y * self.speed


            for wall in walls:
                if self.rect.colliderect(wall):
                    self.rect = old_rect
                    break


        if self.reloading and current_time - self.last_reload_time >= 1000 - self.reload_time:
            self.ammo = 6
            self.reloading = False


        if keys[pygame.K_SPACE] and not self.dodging and current_time - self.dodge_cooldown > 1000 - self.DodgePlus:
            self.dodge()
            self.dodge_cooldown = current_time


        if self.invincible_time > 0 and current_time - self.invincible_time > 100:
            self.invincible_time = 0

    def use_relic(self):
        if self.relic:
            self.relic.activate(self, Room.current_room)

    def gain_xp(self, amount):
        self.xp += amount
        if self.xp >= self.xp_to_next:
            self.level_up()

    def level_up(self):
        self.level += 1
        self.xp -= self.xp_to_next
        self.xp_to_next = int(self.xp_to_next * 1.5)
        self.choosing_perk = True
        self.perk_options = random.sample([
            "+1 Max HP", "+10% Speed", "+1 Dodge",
            "Faster Reload", "+20% Crit Chance"
        ], 3)

    def apply_perk(self, perk):
        if perk == "+1 Max HP":
            self.health += 1
        elif perk == "+Speed":
            self.speed += 0.5
        elif perk == "+1 Dodge":
            self.DodgePlus += 200
        elif perk == "Faster Reload":
            self.reload_time += 400
        elif perk == "+20% Crit Chance":
            self.crit_chance += 0.2
        self.perks.append(perk)
        self.choosing_perk = False

    def dodge(self):
        self.invincible_time = pygame.time.get_ticks()
        self.dodging = True
        self.dodge_start_time = pygame.time.get_ticks()

        self.rect.x += self.direction.x * 25
        self.rect.y += self.direction.y * 25

    def draw_weapon(self, surface, mouse_pos):
        current_weapon_name = self.unlocked_weapons[self.current_weapon]
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
        weapon = self.unlocked_weapons[self.current_weapon]

        if weapon == "shotgun":
            if self.ammo >= 3 and not self.reloading:
                shoot_sound.play()
                self.ammo -= 3

                for _ in range(8):
                    spread = random.uniform(-15, 15)
                    angle = math.atan2(target_pos[1] - self.rect.centery, target_pos[0] - self.rect.centerx)
                    angle += math.radians(spread)
                    dx = math.cos(angle) * 10
                    dy = math.sin(angle) * 10
                    bullet = Bullet(self.rect.centerx, self.rect.centery,
                                    (self.rect.centerx + dx * 10, self.rect.centery + dy * 10),
                                    "player", is_shotgun=True)
                    bullet.speed = 20
                    bullet.piercing = False
                    bullets.add(bullet)

                angle_back = math.atan2(self.rect.centery - target_pos[1], self.rect.centerx - target_pos[0])
                self.rect.x += int(math.cos(angle_back) * 10)
                self.rect.y += int(math.sin(angle_back) * 10)

            elif self.ammo < 3 and not self.reloading:
                self.reload()

        elif weapon == "smg":
            if self.ammo > 0 and not self.reloading:
                shoot_sound.play()
                for _ in range(2):
                    spread = random.uniform(-0.7, 0.7)
                    angle = math.atan2(target_pos[1] - self.rect.centery, target_pos[0] - self.rect.centerx) + spread
                    dx = math.cos(angle) * 3
                    dy = math.sin(angle) * 3
                    bullet = Bullet(self.rect.centerx, self.rect.centery,
                                    (self.rect.centerx + dx, self.rect.centery + dy),"player", is_shotgun=False)
                    bullets.add(bullet)

                if random.random() < 0.3:
                    extra_bullet = Bullet(self.rect.centerx, self.rect.centery,
                                          (self.rect.centerx + dx, self.rect.centery + dy),
                                          "player", is_shotgun=False)
                    bullets.add(extra_bullet)

                self.ammo -= 1
            else:
                self.reload()

        elif weapon == "laser":
            if self.ammo > 0 and not self.reloading:
                shoot_sound.play()
                angle = math.atan2(target_pos[1] - self.rect.centery, target_pos[0] - self.rect.centerx)
                dx = math.cos(angle)
                dy = math.sin(angle)
                laser_end = pygame.Vector2(self.rect.centerx + dx * 1000, self.rect.centery + dy * 1000)

                pygame.draw.line(screen, (0, 255, 255), self.rect.center, laser_end, 4)
                for enemy in list(Room.current_room.enemies):
                    if pygame.Rect(enemy.rect).clipline(self.rect.center, laser_end):
                        enemy.take_damage(self)

                self.ammo -= 1
            else:
                self.reload()

        elif weapon == "rocket":
            if self.ammo > 0 and not self.reloading:
                shoot_sound.play()
                bullet = Bullet(self.rect.centerx, self.rect.centery, target_pos, "player", self.speed * 0.5)
                bullet.image.fill((255, 120, 0))
                bullet.explodes = True
                bullets.add(bullet)
                self.ammo -= 1
            else:
                self.reload()
        else:
            if self.ammo > 0 and not self.reloading:
                shoot_sound.play()
                bullet = Bullet(self.rect.centerx, self.rect.centery, target_pos, "player", self.speed)
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
        if self.invincible_time == 0:
            hit_sound.play()
            self.health -= 1
            self.just_took_damage = True
            self.damage_effect_time = pygame.time.get_ticks()
            shake_start_time = pygame.time.get_ticks()
            if self.health <= 0:
                death_sound.play()
                self.alive = False
                self.room.room_count = 0


    def reset(self, x, y):
        self.health = 3
        self.rect.center = (x, y)
        self.ammo = 6
        self.reloading = False
        self.alive = True

    def switch_weapon(self, direction):
        self.current_weapon = (self.current_weapon + direction) % len(self.unlocked_weapons)

class BloodParticle(pygame.sprite.Sprite):
    def __init__(self, x, y, dx, dy, color=(255, 0, 0)):
        super().__init__()
        self.size = random.randint(4, 8)
        self.image = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        self.color = color
        pygame.draw.circle(self.image, self.color, (self.size // 2, self.size // 2), self.size // 2)
        self.rect = self.image.get_rect(center=(x, y))
        self.dx = dx
        self.dy = dy
        self.gravity = 0.1
        self.life_time = random.randint(30, 60)
        self.alpha = 255

    def update(self):
        self.rect.x += self.dx
        self.rect.y += self.dy
        self.dy += self.gravity

        self.life_time -= 1
        self.alpha -= 5

        self.image = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        pygame.draw.circle(self.image, self.color, (self.size // 2, self.size // 2), self.size // 2)
        self.image.set_alpha(self.alpha)

        if self.life_time <= 0 or self.alpha <= 0:
            self.kill()

class WindParticle(pygame.sprite.Sprite):
    def __init__(self, x, y, direction):
        super().__init__()
        self.image = pygame.Surface((4, 4), pygame.SRCALPHA)
        self.image.fill((200, 200, 255))
        self.rect = self.image.get_rect(center=(x, y))
        self.velocity = direction * random.uniform(1.0, 2.5)
        self.life = random.randint(30, 60)

    def update(self):
        self.rect.x += self.velocity.x
        self.rect.y += self.velocity.y
        self.life -= 1
        if self.life <= 0:
            self.kill()




class Relic:
    def __init__(self, name, cooldown):
        self.name = name
        self.cooldown = cooldown

    def activate(self, player, room):
        pass

class BerserkRelic(Relic):
    def __init__(self):
        super().__init__("Berserkiyum", 20000)  # 20 секунд кулдаун
        self.duration = 5000  # 5 секунд эффект

    def activate(self, player, room):
        player.berserk_active = True
        player.berserk_start_time = pygame.time.get_ticks()


class Trader(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((50, 70))
        self.image.fill((255, 215, 0))
        self.rect = self.image.get_rect(center=(x, y))
        self.weapon_options = ["smg", "laser", "rocket"]
        self.prices = [5, 7, 10]

    def interact(self, player, index):
        if player.chips >= self.prices[index]:
            new_weapon = self.weapon_options[index]
            if new_weapon not in player.unlocked_weapons:
                player.unlocked_weapons.append(new_weapon)
                player.chips -= self.prices[index]
                self.weapon_options[index] = "SOLD"
                self.prices[index] = 0
                buy_sound.play()



class SpikeTrap(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((50, 50))
        self.image.fill((144, 144, 144))
        self.rect = self.image.get_rect(topleft=(x, y))
        self.damage_timer = 0

    def update(self, player, current_time):
        if self.rect.colliderect(player.rect):
            if current_time - self.damage_timer > 1000:
                player.take_damage()
                self.damage_timer = current_time


class ExplosiveBarrel(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((40, 60))
        self.image.fill((255, 120, 0))
        self.rect = self.image.get_rect(center=(x, y))
        self.health = 2

    def take_damage(self, player, room):
        self.health -= 1
        if self.health <= 0:
            self.explode(player, room)

    def explode(self, player, room):
        explosion_radius = 300
        explosion_center = pygame.Vector2(self.rect.center)
        for enemy in list(room.enemies):
            if explosion_center.distance_to(enemy.rect.center) <= explosion_radius:
                enemy.take_damage(player)

        for _ in range(20):
            dx = random.uniform(-3, 3)
            dy = random.uniform(-3, 3)
            blood_particles.add(BloodParticle(self.rect.centerx, self.rect.centery, dx, dy, (255, 140, 0)))
        self.kill()


class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, target_pos, shooter, is_shotgun=False):
        super().__init__()
        self.image = pygame.Surface((10, 10))
        self.image.fill((255, 255, 0))
        self.rect = self.image.get_rect(center=(x, y))
        self.speed = 10
        self.shooter = shooter
        self.origin = pygame.Vector2(x, y)
        self.is_shotgun = is_shotgun
        self.piercing = False
        self.explodes = False


        angle = math.atan2(target_pos[1] - y, target_pos[0] - x)
        if hasattr(Room, 'current_room') and Room.current_room.event == "bullet_drift":
            angle += random.uniform(-0.25, 0.25)
        self.dx = math.cos(angle) * self.speed
        self.dy = math.sin(angle) * self.speed
        if hasattr(Room, 'current_room') and Room.current_room.event == "bullet_drift":
            wind = Room.current_room.wind_direction
            self.dx += wind.x
            self.dy += wind.y


    def update(self):
        self.rect.x += self.dx
        self.rect.y += self.dy
        if not (0 <= self.rect.x <= WIDTH and 0 <= self.rect.y <= HEIGHT):
            self.kill()

    def check_collision(self, target, player):
        if self.rect.colliderect(target.rect):
            if hasattr(target, 'take_damage'):
                damage = 1
                if player.crit_chance > 0 and random.random() < player.crit_chance:
                    damage *= 2
                for _ in range(damage):
                    target.take_damage(player)
                self.create_blood_splash(target)

            if self.explodes:
                self.explode_area(player)

            if not self.piercing:
                self.kill()

            if self.is_shotgun:
                distance = self.origin.distance_to(pygame.Vector2(target.rect.center))
                if distance < 100:
                    target.take_damage(player)
                    self.create_blood_splash(target)
                elif distance < 200:
                    if random.random() < 0.5:
                        target.take_damage(player)
                        self.create_blood_splash(target)
                elif distance < 200:
                    if random.random() < 0.5:
                        target.take_damage(player)
                        self.create_blood_splash(target)
            else:
                target.take_damage(player)
                self.create_blood_splash(target)
            self.kill()

    def explode_area(self, player):
        flash = pygame.Surface((WIDTH, HEIGHT))
        flash.set_alpha(80)
        flash.fill((255, 200, 100))
        screen.blit(flash, (0, 0))
        explosion_radius = 300
        explosion_center = pygame.Vector2(self.rect.center)
        for enemy in list(Room.current_room.enemies):
            if explosion_center.distance_to(enemy.rect.center) <= explosion_radius:
                enemy.take_damage(player)
        for _ in range(15):
            dx = random.uniform(-3, 3)
            dy = random.uniform(-3, 3)
            blood_particles.add(BloodParticle(self.rect.centerx, self.rect.centery, dx, dy, (255, 140, 0)))
        for enemy in list(Room.current_room.enemies):
            if explosion_center.distance_to(enemy.rect.center) <= explosion_radius:
                enemy.take_damage(player)
                knockback = pygame.Vector2(enemy.rect.center) - explosion_center
                if knockback.length() > 0:
                    knockback.normalize_ip()
                    enemy.rect.x += int(knockback.x * 40)
                    enemy.rect.y += int(knockback.y * 40)


    def create_blood_splash(self, target):

        for _ in range(10):
            dx = random.uniform(-2, 2)
            dy = random.uniform(-2, 2)
            blood_particle = BloodParticle(target.rect.centerx, target.rect.centery, dx, dy)
            blood_particles.add(blood_particle)


blood_particles = pygame.sprite.Group()

class TeleportBoss(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((60, 50))
        self.image.fill((100, 0, 150))
        self.rect = self.image.get_rect(center=(x, y))
        self.speed = 2
        self.shoot_delay = 1000
        self.last_shot_time = pygame.time.get_ticks()
        self.health = 4
        self.last_tp = 0

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
        if pygame.time.get_ticks() - self.last_tp > 1500:
            self.rect.center = (random.randint(100, WIDTH - 100), random.randint(100, HEIGHT - 100))
            self.last_tp = pygame.time.get_ticks()

    def explode_gore(self):
        for _ in range(50):
            dx = random.uniform(-6, 6)
            dy = random.uniform(-6, 6)
            size = random.randint(3, 8)
            color = random.choice([(255, 0, 0), (200, 0, 0), (120, 0, 0)])
            particle = BloodParticle(self.rect.centerx, self.rect.centery, dx, dy, color)
            particle.size = size
            blood_particles.add(particle)

    def take_damage(self, player):
        hit_sound.play()
        self.health -= 1
        if self.health <= 0:
            death_sound.play()
            self.explode_gore()
            self.kill()
            player.gain_xp(10)
            player.chips += 4



class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((40, 40))
        self.image.fill((255, 0, 0))
        self.rect = self.image.get_rect(center=(x, y))
        self.speed = 2
        self.shoot_delay = 1000
        self.last_shot_time = pygame.time.get_ticks()
        self.health = 4

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

    def explode_gore(self):
        for _ in range(50):
            dx = random.uniform(-6, 6)
            dy = random.uniform(-6, 6)
            size = random.randint(3, 8)
            color = random.choice([(255, 0, 0), (200, 0, 0), (120, 0, 0)])
            particle = BloodParticle(self.rect.centerx, self.rect.centery, dx, dy, color)
            particle.size = size
            blood_particles.add(particle)

    def take_damage(self, player):
        hit_sound.play()
        self.health -= 1
        if self.health <= 0:
            death_sound.play()
            self.explode_gore()
            self.kill()
            player.gain_xp(2)
            player.chips += 1

class ChasingEnemy(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((40, 40))
        self.image.fill((0, 0, 255))
        self.rect = self.image.get_rect(center=(x, y))
        self.speed = 4
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

    def explode_gore(self):
        for _ in range(50):
            dx = random.uniform(-6, 6)
            dy = random.uniform(-6, 6)
            size = random.randint(3, 8)
            color = random.choice([(255, 0, 0), (200, 0, 0), (120, 0, 0)])
            particle = BloodParticle(self.rect.centerx, self.rect.centery, dx, dy, color)
            particle.size = size
            blood_particles.add(particle)

    def take_damage(self, player):
        hit_sound.play()
        self.health -= 1
        if self.health <= 0:
            death_sound.play()
            self.explode_gore()
            self.kill()
            player.gain_xp(5)
            player.chips += 2

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


class Boss(pygame.sprite.Sprite):
    def __init__(self, x, y, level=1):
        super().__init__()
        self.image = pygame.Surface((80, 80))
        self.image.fill((128, 0, 128))
        self.rect = self.image.get_rect(center=(x, y))
        self.health = 20 + level + 5
        self.speed = 1.5 + level * 0.1
        self.shoot_delay = max(200, 500 - level * 30)
        self.last_shot_time = pygame.time.get_ticks()
        self.phase = 1
        self.room = Room
        self.level = level


    def update(self, player, bullets, current_time):
        direction = pygame.Vector2(player.rect.center) - pygame.Vector2(self.rect.center)
        if direction.length() > 0:
            direction = direction.normalize()
            self.rect.x += direction.x * self.speed
            self.rect.y += direction.y * self.speed

        if current_time - self.last_shot_time >= self.shoot_delay:
            if self.phase == 1:
                self.shoot(bullets, player.rect.center)
            elif self.phase == 2:
                for offset in [-0.2, 0, 0.2]:
                    angle = math.atan2(player.rect.centery - self.rect.centery, player.rect.centerx - self.rect.centerx) + offset
                    dx = math.cos(angle) * 10
                    dy = math.sin(angle) * 10
                    bullet = Bullet(self.rect.centerx, self.rect.centery, (self.rect.centerx + dx, self.rect.centery + dy), "enemy")
                    bullets.add(bullet)
            self.last_shot_time = current_time

        if self.health < (20 + self.level + 5) // 2:
            self.phase = 2

    def shoot(self, bullets, target_pos):
        bullet = Bullet(self.rect.centerx, self.rect.centery, target_pos, "enemy")
        bullets.add(bullet)

    def take_damage(self, player):
        hit_sound.play()
        self.health -= 1
        if self.health <= 0:
            death_sound.play()
            self.kill()
            self.room.boss = None
            player.gain_xp(20)
            player.chips += 8


class Room:
    room_count = 0
    walls_count = 5

    def __init__(self):
        Room.room_count += 1
        self.walls = self.generate_walls()
        self.enemies = pygame.sprite.Group()
        self.boss = None
        self.traps = pygame.sprite.Group()
        self.barrels = pygame.sprite.Group()
        self.ammo_bonus = 0
        self.event = random.choice([None, "fog", "strong_enemies", "bullet_drift"])
        self.wind_direction = pygame.Vector2(0, 0)
        self.trader = None
        self.chips = pygame.sprite.Group()





        if Room.room_count % 10 == 0:
            self.boss = Boss(WIDTH // 2, HEIGHT // 2, Room.room_count // 10)
        elif random.randint(1, 8) == 1:
            self.trader = Trader(WIDTH // 2, HEIGHT // 2)
            self.enemies = pygame.sprite.Group()
        else:
            normal_count = min(3 + Room.room_count // 2, 10)
            chasing_count = min(Room.room_count // 2, 10)
            teleporting_count = min(Room.room_count // 4, 10)
            for _ in range(normal_count):
                self.enemies.add(Enemy(random.randint(50, WIDTH - 50), random.randint(50, HEIGHT - 50)))
            for _ in range(chasing_count):
                self.enemies.add(ChasingEnemy(random.randint(50, WIDTH - 50), random.randint(50, HEIGHT - 50)))
            for _ in range(teleporting_count):
                self.enemies.add(TeleportBoss(random.randint(50, WIDTH - 50), random.randint(50, HEIGHT - 50)))
        for _ in range(3):
            trap_x = random.randint(100, WIDTH - 100)
            trap_y = random.randint(100, HEIGHT - 100)
            self.traps.add(SpikeTrap(trap_x, trap_y))

        for _ in range(random.randint(1, 2)):
            bx = random.randint(100, WIDTH - 100)
            by = random.randint(100, HEIGHT - 100)
            self.barrels.add(ExplosiveBarrel(bx, by))

        if self.event == "strong_enemies":
            for enemy in self.enemies:
                enemy.health += 1
                enemy.speed += 0.5
        if self.event == "bullet_drift":
            angle = random.uniform(0, 2 * math.pi)
            self.wind_direction = pygame.Vector2(math.cos(angle), math.sin(angle)) * 0.3

    def generate_walls(self):
        walls = []
        max_tries = 100
        grid_size = 100
        grid_width = WIDTH // grid_size
        grid_height = HEIGHT // grid_size
        grid = [[False for _ in range(grid_width)] for _ in range(grid_height)]

        attempts = 0

        while attempts < max_tries and len(walls) < Room.walls_count + Room.room_count:
            width = random.randint(200, 400)
            height = random.choice([20, random.randint(100, 300)])


            x_grid = random.randint(1, grid_width - 2)
            y_grid = random.randint(1, grid_height - 2)


            x = x_grid * grid_size
            y = y_grid * grid_size


            can_place_wall = True
            for dx in range(x_grid, min(x_grid + (width // grid_size), grid_width)):
                for dy in range(y_grid, min(y_grid + (height // grid_size), grid_height)):
                    if grid[dy][dx]:
                        can_place_wall = False
                        break
                if not can_place_wall:
                    break

            if can_place_wall:
                new_wall = pygame.Rect(x, y, width, height)
                walls.append(new_wall)


                for dx in range(x_grid, min(x_grid + (width // grid_size), grid_width)):
                    for dy in range(y_grid, min(y_grid + (height // grid_size), grid_height)):
                        grid[dy][dx] = True

            attempts += 1

        return walls

    def draw(self, surface):
        for wall in self.walls:
            pygame.draw.rect(surface, (127, 180, 240), wall)
        if self.event == "fog":
            fog = pygame.Surface((WIDTH, HEIGHT))
            fog.set_alpha(120)
            fog.fill((100, 100, 100))
            surface.blit(fog, (0, 0))

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
            if hasattr(room, 'boss') and room.boss and room.boss.alive():
                return room

            transition()
            new_room = Room()
            player.rect.x += directions[transition_dir][0]
            player.rect.y += directions[transition_dir][1]
            while any(player.rect.colliderect(wall) for wall in new_room.walls):
                player.rect.y -= 5
            return new_room
        return room


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
    start_text = font.render("Press Enter to Start", True, (255, 255, 255))


    background_image = pygame.image.load("background_menu.png")
    background_image = pygame.transform.scale(background_image, (WIDTH, HEIGHT))


    logo_image = pygame.image.load("logo.png")
    logo_image = pygame.transform.scale(logo_image, (550, 225))

    while True:
        screen.fill((0, 0, 0))
        screen.blit(background_image, (0, 0))


        screen.blit(start_text, (WIDTH // 2 - start_text.get_width() // 2, HEIGHT // 2))
        screen.blit(logo_image, (WIDTH // 2 - logo_image.get_width() // 2, HEIGHT // 6))

        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    return



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
    current_music_type = "normal"
    trader_music = 'mystery_shop.wav'
    pygame.mixer.music.load('Waveshaper - Client.mp3') #music
    pygame.mixer.music.set_volume(0.1)
    pygame.mixer.music.play(-1, 0.0)
    show_main_menu()
    running = True
    player = Player(WIDTH // 2, HEIGHT // 2)
    room = Room()
    bullets = pygame.sprite.Group()
    enemy_bullets = pygame.sprite.Group()
    all_sprites = pygame.sprite.Group(player)
    shake_duration = 300
    shake_start_time = 0
    wind_particles = pygame.sprite.Group()

    while running:
        screen.fill((30, 30, 30))
        keys = pygame.key.get_pressed()
        current_time = pygame.time.get_ticks()
        if player.just_took_damage:
            if pygame.time.get_ticks() - player.damage_effect_time < 150:
                red_flash = pygame.Surface((WIDTH, HEIGHT))
                red_flash.fill((255, 0, 0))
                red_flash.set_alpha(90)
                screen.blit(red_flash, (0, 0))
            else:
                player.just_took_damage = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                player.shoot(bullets, pygame.mouse.get_pos())
            if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                if not player.alive:
                    player.reset(WIDTH // 2, HEIGHT // 2)
                    player.xp = 0
                    player.level = 1
                    player.xp_to_next = 10
                    player.perks = []
                    player.bullet_bounce = False
                    player.extra_projectiles = False
                    player.crit_chance = 0.0
                    player.DodgePlus = 0
                    player.reload_time = 0
                    player.chips = 100
                    room = Room()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_p:
                pause_game()
            if event.type == pygame.MOUSEWHEEL:
                player.switch_weapon(event.y)
            if event.type == pygame.KEYDOWN and event.key == pygame.K_m:
                show_main_menu()

            if event.type == pygame.KEYDOWN:
                if room.trader and player.rect.colliderect(room.trader.rect):
                    if event.key == pygame.K_1:
                        room.trader.interact(player, 0)
                    elif event.key == pygame.K_2:
                        room.trader.interact(player, 1)
                    elif event.key == pygame.K_3:
                        room.trader.interact(player, 2)

        room = check_room_transition(player, room)

        Room.current_room = room

        if room.trader and current_music_type != "trader":
            pygame.mixer.music.load(trader_music)
            pygame.mixer.music.play(-1)
            current_music_type = "trader"
        elif not room.trader and current_music_type != "normal":
            pygame.mixer.music.load('Waveshaper - Client.mp3')
            pygame.mixer.music.play(-1)
            current_music_type = "normal"

        all_sprites.update(keys, room.walls, current_time)

        for enemy in room.enemies:
            if isinstance(enemy, ChasingEnemy):
                enemy.update(player, enemy_bullets, current_time, room.walls)
            else:
                enemy.update(player, enemy_bullets, current_time)

        bullets.update()
        enemy_bullets.update()

        for bullet in bullets:
            for barrel in list(room.barrels):
                if bullet.rect.colliderect(barrel.rect):
                    barrel.take_damage(player, room)
                    bullet.kill()

            for enemy in room.enemies:
                bullet.check_collision(enemy, player)
        for bullet in enemy_bullets:
            if bullet.shooter == "enemy" and bullet.rect.colliderect(player.rect):
                player.take_damage()
                bullet.kill()

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

        font = pygame.font.Font(None, 30)
        level_text = font.render(f"Level: {player.level}", True, (255, 255, 255))
        xp_text = font.render(f"XP: {player.xp}/{player.xp_to_next}", True, (100, 255, 100))

        screen.blit(level_text, (10, 50))
        screen.blit(xp_text, (10, 80))

        if room.event:
            font = pygame.font.Font(None, 30)
            text = font.render(f"Room Event: {room.event}", True, (255, 255, 0))
            screen.blit(text, (WIDTH - 250, 10))

        if room.event == "bullet_drift":
            wind = room.wind_direction
            wind_angle = math.atan2(wind.y, wind.x)
            x = WIDTH - 100
            y = HEIGHT - 100
            length = 40
            end_x = x + math.cos(wind_angle) * length
            end_y = y + math.sin(wind_angle) * length
            pygame.draw.line(screen, (180, 180, 255), (x, y), (end_x, end_y), 4)
            pygame.draw.circle(screen, (200, 200, 255), (x, y), 8)

        if player.choosing_perk:
            font = pygame.font.Font(None, 36)
            choice_text = font.render("Choose a perk:", True, (255, 255, 255))
            screen.blit(choice_text, (WIDTH // 2 - 100, HEIGHT // 3 - 40))

            for i, perk in enumerate(player.perk_options):
                perk_text = font.render(f"{i + 1}. {perk}", True, (200, 200, 50))
                screen.blit(perk_text, (WIDTH // 2 - 100, HEIGHT // 3 + i * 40))



            pygame.display.flip()

            waiting = True
            while waiting:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        sys.exit()
                    if event.type == pygame.KEYDOWN:
                        if event.key in [pygame.K_1, pygame.K_KP1]:
                            player.apply_perk(player.perk_options[0])
                            waiting = False
                        elif event.key in [pygame.K_2, pygame.K_KP2]:
                            player.apply_perk(player.perk_options[1])
                            waiting = False
                        elif event.key in [pygame.K_3, pygame.K_KP3]:
                            player.apply_perk(player.perk_options[2])
                            waiting = False
                    if event.type == pygame.KEYDOWN:
                        if room.trader and player.rect.colliderect(room.trader.rect):
                            if event.key == pygame.K_1:
                                room.trader.interact(player, 0)
                            elif event.key == pygame.K_2:
                                room.trader.interact(player, 1)
                            elif event.key == pygame.K_3:
                                room.trader.interact(player, 2)
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:  # ПКМ
                        current_time = pygame.time.get_ticks()
                        if player.relic and current_time - player.last_relic_use > player.relic_cooldown:
                            player.use_relic()
                            player.last_relic_use = current_time

        if pygame.time.get_ticks() - shake_start_time < shake_duration:
            shake_offset = [random.randint(-5, 5), random.randint(-5, 5)]
            screen.blit(screen.copy(), shake_offset)
        room.draw(screen)
        room.enemies.draw(screen)
        all_sprites.draw(screen)
        bullets.draw(screen)
        room.traps.update(player, current_time)
        room.traps.draw(screen)
        room.barrels.draw(screen)
        chip_text = font.render(f"Chips: {player.chips}", True, (0, 255, 255))
        screen.blit(chip_text, (10, 110))

        room.chips.update()
        room.chips.draw(screen)

        for chip in room.chips:
            if player.rect.colliderect(chip.rect):
                chip.collect(player)

        if room.trader:
            screen.blit(room.trader.image, room.trader.rect)
            font = pygame.font.Font(None, 24)
            if player.rect.colliderect(room.trader.rect):
                for i, option in enumerate(room.trader.weapon_options):
                    display_text = f"{i + 1}. {option} - {room.trader.prices[i]} chips"
                    if option == "SOLD":
                        text_color = (255, 0, 0)
                        display_text = f"{i + 1}. SOLD"
                    else:
                        text_color = (255, 255, 255)
                    text = font.render(display_text, True, text_color)
                    screen.blit(text, (room.trader.rect.x, room.trader.rect.bottom + i * 25))

        if room.event == "fog":
            fog_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            fog_surface.fill((50, 50, 50, 220))
            screen.blit(fog_surface, (0, 0))

        if player.relic:
            remaining = max(0, (player.relic_cooldown - (pygame.time.get_ticks() - player.last_relic_use)) // 1000)
            relic_text = font.render(f"Relic ({player.relic.name}): {remaining}s", True, (100, 200, 255))
            screen.blit(relic_text, (WIDTH - 250, HEIGHT - 40))

        enemy_bullets.draw(screen)
        room = check_room_transition(player, room)
        if room.event == "bullet_drift":
            if random.random() < 0.4:
                spawn_x = random.randint(0, WIDTH)
                spawn_y = random.randint(0, HEIGHT)
                wind_particles.add(WindParticle(spawn_x, spawn_y, room.wind_direction))

            wind_particles.update()
            wind_particles.draw(screen)

        player.draw_weapon(screen, pygame.mouse.get_pos())

        if room.boss and room.boss.health >= 0:
            screen.blit(room.boss.image, room.boss.rect)
            for bullet in bullets:
                bullet.check_collision(room.boss, player)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


def explosion_effect(player):
    for enemy in Room.current_room.enemies:
        if pygame.Vector2(enemy.rect.center).distance_to(player.rect.center) <= 150:
            enemy.take_damage(player)



if __name__ == "__main__":
    main()
