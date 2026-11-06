import os
import pygame
import config as C

# У нас тайли намальовані 16x16, а гра працює при TILE=32 -> збільшуємо вдвічі.
SCALE = C.TILE // 16


class AssetManager:
    # Відповідає за всі картинки: знаходить файли, масштабує, видає спрайт або заглушку.
    def __init__(self, images_dir="assets/images"):
        self.index = {}  # словник: ім'я файлу без розширення -> повний шлях до нього
        if os.path.isdir(images_dir):
            # Проходимо всі підпапки й запам'ятовуємо кожен .png.
            for dirpath, _, files in os.walk(images_dir):
                for f in files:
                    if f.lower().endswith(".png"):
                        self.index[os.path.splitext(f)[0]] = os.path.join(dirpath, f)
        self.cache = {}  # кеш уже завантажених картинок, щоб не читати їх з диска щокадру

    def _placeholder(self, key):
        # Якщо картинки немає - малюємо кольоровий квадрат-заглушку (колір з таблиці).
        surf = pygame.Surface((C.TILE, C.TILE), pygame.SRCALPHA)
        surf.fill(C.COLORS.get(key, (160, 90, 160)))
        return surf

    def _load(self, name):
        # Завантажує картинку за іменем один раз і кладе в кеш.
        if name in self.cache:
            return self.cache[name]          # вже завантажували - віддаємо з кешу
        path = self.index.get(name)
        img = None
        if path:
            try:
                img = pygame.image.load(path).convert_alpha()  # з прозорістю
            except pygame.error:
                img = pygame.image.load(path)                  # запасний варіант
            if SCALE != 1:
                img = pygame.transform.scale_by(img, SCALE)    # збільшуємо до розміру гри
        self.cache[name] = img  # запам'ятовуємо в кеш
        return img

    def sprite(self, name):
        # Проста видача картинки за точним іменем (для тайлів, дерев, паркана тощо).
        return self._load(name)

    def get_sprite(self, key, direction="down", frame=1):
        # Видача спрайта персонажа: шукаємо від найдетальнішого імені до найпростішого.
        img = self._load(f"{key}-{direction}-{frame}")          # напр. "dog-down-1"
        if img is None:
            img = self._load(f"{key}-{direction}") or self._load(key)
        if img is None:
            img = self.cache.setdefault("__ph_" + key, self._placeholder(key))  # заглушка
        return img
