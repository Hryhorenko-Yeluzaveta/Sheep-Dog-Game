import os
import pygame

EXTS = (".ogg", ".wav", ".mp3")

ALIASES = {
    "music_day": "day_ambient",
    "music_tension": "day_ambient",
    "sheep_baa": "sheep_sound",
    "voice": "man-speak-unintelligibly",
}


class SoundManager:
    def __init__(self, audio_dir="assets/audio"):
        self.dir = audio_dir
        self.sfx = {}
        self.music_path = None
        self.voice_channel = None
        self.enabled = True
        try:
            pygame.mixer.init()
        except pygame.error:
            self.enabled = False

    def _find(self, key):
        base = ALIASES.get(key, key)
        for ext in EXTS:
            path = os.path.join(self.dir, base + ext)
            if os.path.exists(path):
                return path
        return None

    def _get(self, key):
        if key not in self.sfx:
            path = self._find(key)
            try:
                self.sfx[key] = pygame.mixer.Sound(path) if path else None
            except pygame.error:
                self.sfx[key] = None
        return self.sfx[key]

    def play_sfx(self, key, volume=1.0):
        if not self.enabled:
            return
        snd = self._get(key)
        if snd:
            snd.set_volume(volume)
            snd.play()

    def play_voice(self, key="voice", volume=0.8):
        if not self.enabled:
            return
        snd = self._get(key)
        if snd:
            snd.set_volume(volume)
            self.voice_channel = snd.play()

    def stop_voice(self, fade_ms=120):
        if self.voice_channel is not None:
            self.voice_channel.fadeout(fade_ms)
            self.voice_channel = None

    def play_music(self, key, loop=True, volume=0.6):
        if not self.enabled:
            return
        path = self._find(key)
        if path == self.music_path:
            return
        self.music_path = path
        if not path:
            pygame.mixer.music.stop()
            return
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(volume)
            pygame.mixer.music.play(-1 if loop else 0)
        except pygame.error:
            self.music_path = None

    def stop_music(self):
        if self.enabled:
            pygame.mixer.music.stop()
        self.music_path = None
