import os
import pygame

EXTS = (".ogg", ".wav", ".mp3")

# Логічна назва в коді -> реальне ім'я файлу на диску.
ALIASES = {
    "music_day": "day_ambient",
    "music_tension": "day_ambient",
    "sheep_baa": "sheep_sound",
    "voice": "man-speak-unintelligibly",
}


class SoundManager:
    # Керує всім звуком: музика, ефекти, голос діалогів
    def __init__(self, audio_dir="assets/audio"):
        self.dir = audio_dir          # папка зі звуками
        self.sfx = {}                 # кеш завантажених звукових ефектів
        self.music_path = None        # яка музика грає зараз (щоб не перезапускати ту саму)
        self.voice_channel = None     # канал, на якому звучить голос (щоб його приглушити)
        self.enabled = True           # чи вдалося ввімкнути звук узагалі
        try:
            pygame.mixer.init()       # вмикаємо звукову систему
        except pygame.error:
            self.enabled = False      # немає звукового пристрою - гра працює без звуку

    def _find(self, key):
        # Шукає файл за логічною назвою: спершу псевдонім, потім кожне розширення.
        base = ALIASES.get(key, key)
        for ext in EXTS:
            path = os.path.join(self.dir, base + ext)
            if os.path.exists(path):
                return path           # знайшли - повертаємо шлях
        return None                   # файлу немає

    def _get(self, key):
        # Завантажує ефект один раз і кладе в кеш (None, якщо файлу немає).
        if key not in self.sfx:
            path = self._find(key)
            try:
                self.sfx[key] = pygame.mixer.Sound(path) if path else None
            except pygame.error:
                self.sfx[key] = None
        return self.sfx[key]

    def play_sfx(self, key, volume=1.0):
        # Програти короткий ефект (гавкіт, клік, бекання тощо).
        if not self.enabled:
            return
        snd = self._get(key)
        if snd:
            snd.set_volume(volume)
            snd.play()

    def play_voice(self, key="voice", volume=0.8):
        # Програти голос деда й запам'ятати канал, щоб потім плавно приглушити.
        if not self.enabled:
            return
        snd = self._get(key)
        if snd:
            snd.set_volume(volume)
            self.voice_channel = snd.play()

    def stop_voice(self, fade_ms=120):
        # Плавно згасити голос (коли репліка змінилася чи діалог закрито).
        if self.voice_channel is not None:
            self.voice_channel.fadeout(fade_ms)
            self.voice_channel = None

    def play_music(self, key, loop=True, volume=0.6):
        # Увімкнути фонову музику (за замовчуванням зациклену).
        if not self.enabled:
            return
        path = self._find(key)
        if path == self.music_path:
            return                    # та сама музика вже грає - нічого не робимо
        self.music_path = path
        if not path:
            pygame.mixer.music.stop() # файлу немає - просто зупиняємо музику
            return
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(volume)
            pygame.mixer.music.play(-1 if loop else 0)  # -1 = безкінечно, 0 = один раз
        except pygame.error:
            self.music_path = None

    def stop_music(self):
        # Повністю зупинити музику.
        if self.enabled:
            pygame.mixer.music.stop()
        self.music_path = None
