import os
import pygame
import config as C

SCALE = C.TILE // 16


class AssetManager:
    def __init__(self, images_dir="assets/images"):
        self.index = {}
        if os.path.isdir(images_dir):
            for dirpath, _, files in os.walk(images_dir):
                for f in files:
                    if f.lower().endswith(".png"):
                        self.index[os.path.splitext(f)[0]] = os.path.join(dirpath, f)
        self.cache = {}

    def _placeholder(self, key):
        surf = pygame.Surface((C.TILE, C.TILE), pygame.SRCALPHA)
        surf.fill(C.COLORS.get(key, (160, 90, 160)))
        return surf

    def _load(self, name):
        if name in self.cache:
            return self.cache[name]
        path = self.index.get(name)
        img = None
        if path:
            try:
                img = pygame.image.load(path).convert_alpha()
            except pygame.error:
                img = pygame.image.load(path)
            if SCALE != 1:
                img = pygame.transform.scale_by(img, SCALE)
        self.cache[name] = img
        return img

    def sprite(self, name):
        return self._load(name)

    def get_sprite(self, key, direction="down", frame=1):
        img = self._load(f"{key}-{direction}-{frame}")
        if img is None:
            img = self._load(f"{key}-{direction}") or self._load(key)
        if img is None:
            img = self.cache.setdefault("__ph_" + key, self._placeholder(key))
        return img
