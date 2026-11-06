import math
import random
import pygame
from pygame.math import Vector2
import config as C
from ai import a_star


def _norm(v):
    return v.normalize() if v.length_squared() > 1e-9 else Vector2()


def _clamp(v, m):
    return v.normalize() * m if v.length_squared() > m * m else v


def _cell(x, y):
    return int(x // C.TILE), int(y // C.TILE)


def _blocked(tilemap, x, y, r):
    for px, py in ((x - r, y - r), (x + r, y - r), (x - r, y + r), (x + r, y + r)):
        if tilemap.is_blocked(int(px // C.TILE), int(py // C.TILE)):
            return True
    return False


def _dir_name(v):
    if abs(v.x) > abs(v.y):
        return "right" if v.x > 0 else "left"
    return "down" if v.y > 0 else "up"


class Mover:
    def __init__(self, pos, radius):
        self.pos = Vector2(pos)
        self.vel = Vector2()
        self.radius = radius
        self.direction = "down"
        self.anim = 0.0
        self.block_rect = None
        self.sprite_scale = 1.0

    def _pen_blocks(self, x, y):
        return self.block_rect is not None and self.block_rect.collidepoint(x, y)

    def _frame(self):
        if self.vel.length_squared() < 64:
            return 1
        return 1 + (int(self.anim * 8) % 2)

    def _blit(self, surface, camera, assets, key):
        spr = assets.get_sprite(key, self.direction, self._frame())
        if self.sprite_scale != 1.0:
            spr = pygame.transform.scale_by(spr, self.sprite_scale)
        sx, sy = camera.apply(self.pos)
        surface.blit(spr, (sx - spr.get_width() // 2, sy - spr.get_height() // 2))
        return spr, sx, sy

    def _integrate(self, dt, tilemap):
        nx = self.pos.x + self.vel.x * dt
        if not _blocked(tilemap, nx, self.pos.y, self.radius) and not self._pen_blocks(nx, self.pos.y):
            self.pos.x = nx
        ny = self.pos.y + self.vel.y * dt
        if not _blocked(tilemap, self.pos.x, ny, self.radius) and not self._pen_blocks(self.pos.x, ny):
            self.pos.y = ny
        self.pos.x = max(self.radius, min(self.pos.x, tilemap.w * C.TILE - self.radius))
        self.pos.y = max(self.radius, min(self.pos.y, tilemap.h * C.TILE - self.radius))


class Dog(Mover):
    def __init__(self, pos):
        super().__init__(pos, 12)
        self.stamina = C.STAMINA_MAX
        self.sprite_scale = 0.78

    def update(self, dt, keys, tilemap):
        move = Vector2()
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            move.x -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            move.x += 1
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            move.y -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            move.y += 1
        moving = move.length_squared() > 0
        sprint = moving and self.stamina > 0 and (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT])
        if sprint:
            self.stamina = max(0.0, self.stamina - C.STAMINA_DRAIN * dt)
        else:
            self.stamina = min(C.STAMINA_MAX, self.stamina + C.STAMINA_REGEN * dt)
        if moving:
            move = move.normalize()
            self.direction = _dir_name(move)
            self.vel = move * (C.DOG_SPRINT if sprint else C.DOG_SPEED)
        else:
            self.vel = Vector2()
        self.anim += dt
        self._integrate(dt, tilemap)

    def draw(self, surface, camera, assets):
        self._blit(surface, camera, assets, "dog")


class Sheep(Mover):
    def __init__(self, pos):
        super().__init__(pos, 10)
        self.state = "graze"
        self.penned = False
        self.lost = False
        self.wander = Vector2()
        self.wander_t = random.uniform(0, 2)
        self.scare_t = 0.0

    def _wander_dir(self, dt):
        self.wander_t -= dt
        if self.wander_t <= 0:
            a = random.uniform(0, math.tau)
            self.wander = Vector2(math.cos(a), math.sin(a))
            self.wander_t = random.uniform(1.0, 2.5)
        return self.wander

    def _avoid(self, tilemap):
        v = Vector2()
        cx, cy = _cell(self.pos.x, self.pos.y)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if tilemap.is_blocked(cx + dx, cy + dy):
                    center = Vector2((cx + dx + 0.5) * C.TILE, (cy + dy + 0.5) * C.TILE)
                    d = self.pos.distance_to(center)
                    if 1e-5 < d < C.TILE * 1.5:
                        v += (self.pos - center) / d
        return _norm(v)

    def update(self, dt, neighbors, dog, wolves, tilemap):
        if self.penned or self.lost:
            self.vel = Vector2()
            return
        sep = Vector2()
        ali = Vector2()
        coh = Vector2()
        n_nei = 0
        for o in neighbors:
            d = self.pos.distance_to(o.pos)
            if d < 1e-5:
                continue
            if d < C.R_SEP:
                sep += (self.pos - o.pos) / d
            if d < C.R_NEI:
                ali += o.vel
                coh += o.pos
                n_nei += 1
        sep = _norm(sep)
        if n_nei:
            ali = _norm(ali)
            coh = _norm(coh / n_nei - self.pos)

        panic = False
        flee_dog = Vector2()
        flee_wolf = Vector2()
        if dog:
            dd = self.pos.distance_to(dog.pos)
            if 1e-5 < dd < C.R_DOG:
                flee_dog = (self.pos - dog.pos) / dd * min(3.0, C.R_DOG / dd)
                panic = True
        for wolf in wolves:
            dw = self.pos.distance_to(wolf.pos)
            if 1e-5 < dw < C.R_WOLF:
                flee_wolf += (self.pos - wolf.pos) / dw * min(3.0, C.R_WOLF / dw)
                panic = True

        self.scare_t = max(0.0, self.scare_t - dt)
        if self.scare_t > 0 and dog:
            dd = self.pos.distance_to(dog.pos)
            if dd > 1e-5:
                flee_dog += (self.pos - dog.pos) / dd * 3.0
            panic = True

        acc = (C.W_SEP * sep + C.W_ALI * ali + C.W_COH * coh +
               C.W_DOG * flee_dog + C.W_WOLF * flee_wolf + C.W_OBS * self._avoid(tilemap))
        if not panic:
            acc += self._wander_dir(dt) * 0.6

        boost = 1.6 if self.scare_t > 0 else 1.0
        max_speed = C.SHEEP_SPEED * (C.PANIC_MULT if panic else 0.6) * boost
        desired = _norm(acc) * max_speed
        self.vel += (desired - self.vel) * min(1.0, 6 * dt)
        self.vel = _clamp(self.vel, max_speed)
        self.anim += dt
        if self.vel.length_squared() > 64:
            self.direction = _dir_name(self.vel)
        self._integrate(dt, tilemap)

        if panic:
            self.state = "scared"
        elif self.vel.length_squared() > 64:
            self.state = "walk"
        else:
            self.state = "graze"

    def draw(self, surface, camera, assets):
        if self.lost:
            return
        spr = assets.get_sprite("sheep", self.direction, self._frame())
        if self.penned:
            spr = spr.copy()
            spr.set_alpha(150)
        sx, sy = camera.apply(self.pos)
        surface.blit(spr, (sx - spr.get_width() // 2, sy - spr.get_height() // 2))


class Flock:
    def __init__(self, tilemap, pen, count):
        self.sheep = []
        tries = 0
        while len(self.sheep) < count and tries < count * 300:
            tries += 1
            cx = random.randint(1, tilemap.w - 2)
            cy = random.randint(1, tilemap.h - 2)
            if tilemap.is_blocked(cx, cy):
                continue
            px, py = (cx + 0.5) * C.TILE, (cy + 0.5) * C.TILE
            if abs(px - pen.rect.centerx) < 9 * C.TILE and abs(py - pen.rect.centery) < 7 * C.TILE:
                continue
            self.sheep.append(Sheep((px, py)))

    def update(self, dt, dog, wolves, tilemap, pen):
        active = [s for s in self.sheep if not s.penned and not s.lost]
        for s in active:
            s.update(dt, active, dog, wolves, tilemap)
        newly = 0
        for s in active:
            if pen.contains(s.pos):
                s.penned = True
                s.state = "penned"
                s.pos = Vector2(pen.inside_point())
                s.vel = Vector2()
                newly += 1
        return newly

    def counts(self):
        penned = sum(1 for s in self.sheep if s.penned)
        lost = sum(1 for s in self.sheep if s.lost)
        return penned, lost


class Wolf(Mover):
    def __init__(self, pos, speed, vision, lead_time=0.0, retreat_time=1.6, fear_radius=160):
        super().__init__(pos, 12)
        self.speed = speed
        self.vision = vision
        self.lead_time = lead_time
        self.retreat_time = retreat_time
        self.fear_radius = fear_radius
        self.state = "patrol"
        self.target = None
        self.path = []
        self.repath_t = 0.0
        self.wander = Vector2()
        self.wander_t = 0.0
        self.retreat_t = 0.0
        self.attack_range = 18

    def choose_target(self, flock, dog):
        alive = [s for s in flock.sheep if not s.penned and not s.lost]
        if not alive:
            return None
        centroid = Vector2()
        for s in alive:
            centroid += s.pos
        centroid /= len(alive)
        best, best_score = None, -1e18
        for s in alive:
            if self.pos.distance_to(s.pos) > self.vision:
                continue
            d_dog = s.pos.distance_to(dog.pos) if dog else 999
            score = s.pos.distance_to(centroid) + 0.6 * d_dog
            if score > best_score:
                best, best_score = s, score
        return best

    def _move_toward(self, point, dt, tilemap):
        d = Vector2(point) - self.pos
        if d.length_squared() > 1e-6:
            self.vel = d.normalize() * self.speed
            self.direction = _dir_name(d)
        self._integrate(dt, tilemap)

    def _step_path(self, dt, tilemap, goal):
        self.repath_t -= dt
        if self.repath_t <= 0 or not self.path:
            self.path = a_star(tilemap, _cell(self.pos.x, self.pos.y), _cell(goal.x, goal.y))
            self.repath_t = 0.3
        if self.path:
            nc = self.path[0]
            center = Vector2((nc[0] + 0.5) * C.TILE, (nc[1] + 0.5) * C.TILE)
            if self.pos.distance_to(center) < 8:
                self.path.pop(0)
            else:
                self._move_toward(center, dt, tilemap)
        else:
            self._move_toward(goal, dt, tilemap)

    def _patrol(self, dt, tilemap):
        self.wander_t -= dt
        if self.wander_t <= 0 or self.wander.length_squared() == 0:
            a = random.uniform(0, math.tau)
            self.wander = Vector2(math.cos(a), math.sin(a))
            self.wander_t = random.uniform(1.5, 3.0)
        self.vel = self.wander * (self.speed * 0.5)
        self.direction = _dir_name(self.vel)
        self._integrate(dt, tilemap)

    def _retreat(self, dt, dog, tilemap):
        away = (self.pos - dog.pos) if dog else Vector2(1, 0)
        away = away.normalize() if away.length_squared() > 1e-6 else Vector2(1, 0)
        self._move_toward(self.pos + away * 120, dt, tilemap)

    def update(self, dt, flock, dog, tilemap):
        self.anim += dt
        dog_d = self.pos.distance_to(dog.pos) if dog else 1e9
        if dog_d < self.fear_radius and self.state != "retreat":
            self.state = "retreat"
            self.retreat_t = self.retreat_time
            self.target = None
        if self.state == "patrol":
            self._patrol(dt, tilemap)
            t = self.choose_target(flock, dog)
            if t and dog_d > self.fear_radius:
                self.target = t
                self.path = []
                self.repath_t = 0.0
                self.state = "stalk"
        elif self.state == "stalk":
            if self.target is None or self.target.penned or self.target.lost:
                self.state = "patrol"
                self.target = None
            elif self.pos.distance_to(self.target.pos) <= self.attack_range:
                self.state = "attack"
            else:
                self._step_path(dt, tilemap, self.target.pos + self.target.vel * self.lead_time)
        elif self.state == "attack":
            if self.target and not self.target.lost and not self.target.penned:
                self.target.lost = True
                self.target.state = "lost"
            self.target = None
            self.state = "retreat"
            self.retreat_t = self.retreat_time * 0.75
        elif self.state == "retreat":
            self.retreat_t -= dt
            self._retreat(dt, dog, tilemap)
            if self.retreat_t <= 0:
                self.state = "patrol"

    def draw(self, surface, camera, assets):
        self._blit(surface, camera, assets, "wolf")
