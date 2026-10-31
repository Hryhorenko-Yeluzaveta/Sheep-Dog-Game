import random
import pygame
import config as C

SCATTER = ["rock-1", "rock-2", "rock-3", "rock-4", "small-tree",
           "small-tree", "big-stump", "Big-tree", "Big-tree"]
FOREST = ["Big-tree", "Big-tree", "small-tree", "big-stump"]


class TileMap:
    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.obstacles = {}
        self.decor = {}
        self._generate()

    def _generate(self):
        for x in range(self.w):
            for y in (0, self.h - 1):
                if random.random() < 0.7:
                    self.obstacles[(x, y)] = random.choice(FOREST)
        for y in range(self.h):
            for x in (0, self.w - 1):
                if random.random() < 0.7:
                    self.obstacles[(x, y)] = random.choice(FOREST)
        for _ in range((self.w * self.h) // 20):
            x = random.randint(2, self.w - 3)
            y = random.randint(2, self.h - 3)
            self.obstacles[(x, y)] = random.choice(SCATTER)
        for _ in range((self.w * self.h) // 12):
            x = random.randint(1, self.w - 2)
            y = random.randint(1, self.h - 2)
            if (x, y) not in self.obstacles:
                self.decor[(x, y)] = "grass-with-dirt-in-center"

    def is_blocked(self, cx, cy):
        if cx < 0 or cy < 0 or cx >= self.w or cy >= self.h:
            return True
        return (cx, cy) in self.obstacles

    def clear_rect(self, cx, cy, w, h):
        for y in range(cy, cy + h):
            for x in range(cx, cx + w):
                self.obstacles.pop((x, y), None)
                self.decor.pop((x, y), None)

    def draw_ground(self, surface, camera, assets):
        x0 = max(0, camera.x // C.TILE)
        y0 = max(0, camera.y // C.TILE)
        x1 = min(self.w, (camera.x + C.SCREEN_W) // C.TILE + 1)
        y1 = min(self.h, (camera.y + C.SCREEN_H) // C.TILE + 1)
        grass = assets.sprite("grass")
        for cy in range(y0, y1):
            for cx in range(x0, x1):
                sx, sy = camera.apply((cx * C.TILE, cy * C.TILE))
                surface.blit(grass, (sx, sy))
                if (cx, cy) in self.decor:
                    surface.blit(assets.sprite(self.decor[(cx, cy)]), (sx, sy))

    def blit_obstacle(self, surface, camera, assets, cx, cy, name):
        spr = assets.sprite(name)
        sx, sy = camera.apply((cx * C.TILE + C.TILE // 2, (cy + 1) * C.TILE))
        surface.blit(spr, (sx - spr.get_width() // 2, sy - spr.get_height()))

    def visible_obstacles(self, camera):
        x0 = camera.x // C.TILE - 2
        y0 = camera.y // C.TILE - 2
        x1 = (camera.x + C.SCREEN_W) // C.TILE + 2
        y1 = (camera.y + C.SCREEN_H) // C.TILE + 2
        for (cx, cy), name in self.obstacles.items():
            if x0 <= cx <= x1 and y0 <= cy <= y1:
                yield cx, cy, name


class Camera:
    def __init__(self, world_w, world_h):
        self.world_w = world_w
        self.world_h = world_h
        self.x = 0
        self.y = 0

    def follow(self, pos):
        self.x = int(pos[0] - C.SCREEN_W / 2)
        self.y = int(pos[1] - C.SCREEN_H / 2)
        self.x = max(0, min(self.x, self.world_w - C.SCREEN_W))
        self.y = max(0, min(self.y, self.world_h - C.SCREEN_H))

    def apply(self, pos):
        return (int(pos[0] - self.x), int(pos[1] - self.y))


class Pen:
    def __init__(self, cx, cy, w, h):
        self.cx = cx
        self.cy = cy
        self.w = w
        self.h = h
        self.rect = pygame.Rect(cx * C.TILE, cy * C.TILE, w * C.TILE, h * C.TILE)
        self.gate = pygame.Rect((cx + w // 2) * C.TILE, (cy + h - 1) * C.TILE, C.TILE, C.TILE)

    def contains(self, pos):
        return self.rect.collidepoint(pos)

    def inside_point(self):
        x = random.randint(self.cx + 1, self.cx + self.w - 2)
        y = random.randint(self.cy + 1, self.cy + self.h - 2)
        return (x * C.TILE + C.TILE // 2, y * C.TILE + C.TILE // 2)

    def _blit(self, surface, camera, assets, name, x, y):
        surface.blit(assets.sprite(name), camera.apply((x * C.TILE, y * C.TILE)))

    def draw(self, surface, camera, assets):
        x0, y0 = self.cx, self.cy
        x1, y1 = self.cx + self.w - 1, self.cy + self.h - 1
        gx = x0 + self.w // 2
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if y0 < y < y1 and x0 < x < x1:
                    self._blit(surface, camera, assets, self._dirt(x, y, x0, y0, x1, y1), x, y)
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                name = self._fence(x, y, x0, y0, x1, y1, gx)
                if name:
                    self._blit(surface, camera, assets, name, x, y)

    def _dirt(self, x, y, x0, y0, x1, y1):
        top, bot = y == y0 + 1, y == y1 - 1
        left, right = x == x0 + 1, x == x1 - 1
        if top and left:
            return "grass-with-dirt-right-down-corner"
        if top and right:
            return "grass-with-dirt-left-down-corner"
        if bot and left:
            return "grass-with-dirt-right-up-corner"
        if bot and right:
            return "grass-with-dirt-left-up-corner"
        if top:
            return "grass-with-dirt-down-half"
        if bot:
            return "grass-with-dirt-up-half"
        if left:
            return "grass-with-dirt-right-half"
        if right:
            return "grass-with-dirt-left-half"
        return "dirt"

    def _fence(self, x, y, x0, y0, x1, y1, gx):
        if x == x0 and y == y0:
            return "left-up-corner-fence"
        if x == x1 and y == y0:
            return "right-up-corner-fence"
        if x == x0 and y == y1:
            return "left-down-corner-fence"
        if x == x1 and y == y1:
            return "right-down-corner-fence"
        if y == y1 and x == gx:
            return "horizontal-fence-with-left-gate"
        if y == y1 and x == gx + 1:
            return "horizontal-fence-with-right-gate"
        if y in (y0, y1):
            return "horizontal-fence"
        if x == x0:
            return "vertical-left-side-fence"
        if x == x1:
            return "vertical-right-side-fence"
        return None
