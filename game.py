import sys
import math
import random
import pygame
from pygame.math import Vector2
import config as C
import story
from assets import AssetManager
from audio import SoundManager
from database import Database
from world import TileMap, Camera, Pen
from entities import Dog, Flock, Wolf


UI_FONT = "verdana,segoeui,arial"
TITLE_FONT = "georgia,constantia,timesnewroman,serif"


def make_font(size, bold=False):
    return pygame.font.SysFont(UI_FONT, size, bold=bold)


def make_title(size, bold=False):
    return pygame.font.SysFont(TITLE_FONT, size, bold=bold)


def lerp_color(a, b, t):
    return (int(a[0] + (b[0] - a[0]) * t),
            int(a[1] + (b[1] - a[1]) * t),
            int(a[2] + (b[2] - a[2]) * t))


def day_score(saved, lost, time_left, completed):
    s = saved * 100 - lost * 40
    if completed:
        s += int(time_left) * 3
    return max(0, s)


class Scene:
    def __init__(self, game):
        self.game = game

    def handle_event(self, event):
        pass

    def update(self, dt):
        pass

    def draw(self, surface):
        pass


class DialogBox:
    def __init__(self, lines, sound=None):
        self.lines = list(lines)
        self.i = 0
        self.active = len(self.lines) > 0
        self.sound = sound
        self.font = make_title(22)
        self.small = make_title(18, bold=True)
        self._speak()

    def _speak(self):
        if self.active and self.sound and self.lines[self.i][0]:
            self.sound.play_voice()

    def _advance(self):
        if self.sound:
            self.sound.stop_voice()
        self.i += 1
        if self.i >= len(self.lines):
            self.active = False
        else:
            self._speak()

    def handle_event(self, event):
        if not self.active:
            return
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_e):
            self._advance()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._advance()

    def _wrapped(self, surface, text, x, y, maxw):
        line = ""
        for word in text.split(" "):
            test = (line + " " + word).strip()
            if self.font.size(test)[0] > maxw and line:
                surface.blit(self.font.render(line, True, (236, 236, 232)), (x, y))
                y += 28
                line = word
            else:
                line = test
        if line:
            surface.blit(self.font.render(line, True, (236, 236, 232)), (x, y))

    def draw(self, surface):
        if not self.active:
            return
        speaker, text = self.lines[self.i]
        box = pygame.Rect(50, C.SCREEN_H - 150, C.SCREEN_W - 100, 120)
        panel = pygame.Surface(box.size, pygame.SRCALPHA)
        panel.fill((18, 22, 28, 232))
        surface.blit(panel, box.topleft)
        pygame.draw.rect(surface, (184, 150, 96), box, 2, border_radius=8)
        if speaker:
            surface.blit(self.small.render(speaker, True, (232, 196, 120)), (box.x + 18, box.y + 12))
        self._wrapped(surface, text, box.x + 18, box.y + 42, box.w - 36)
        hint = self.small.render("[Space] continue", True, (150, 158, 168))
        surface.blit(hint, (box.right - hint.get_width() - 16, box.bottom - 26))


class Button:
    def __init__(self, rect, text, size=28):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = make_font(size, bold=True)

    def draw(self, surface, selected):
        base = (74, 104, 64) if selected else (46, 64, 46)
        edge = (240, 210, 130) if selected else (150, 170, 150)
        r = self.rect.inflate(12, 6) if selected else self.rect
        pygame.draw.rect(surface, base, r, border_radius=10)
        pygame.draw.rect(surface, edge, r, 3, border_radius=10)
        col = (255, 244, 210) if selected else (220, 228, 218)
        label = self.font.render(self.text, True, col)
        surface.blit(label, label.get_rect(center=r.center))

    def hit(self, pos):
        return self.rect.inflate(12, 6).collidepoint(pos)


class MenuScene(Scene):
    SKY_TOP = (28, 32, 70)
    SKY_HORIZON = (244, 158, 92)
    HILL = (44, 72, 44)
    HILL_BACK = (34, 58, 40)

    def __init__(self, game):
        super().__init__(game)
        self.game.sound.play_music("music_menu")
        self.t = 0.0
        self.title_font = make_title(96, bold=True)
        self.sub_font = make_title(26)
        self.label_font = make_font(20)
        self.tip_font = make_font(18)
        self.name = game.last_name
        cx = C.SCREEN_W // 2
        self.items = [("play", Button((cx - 100, 360, 200, 50), "Play")),
                      ("records", Button((cx - 100, 422, 200, 50), "Records")),
                      ("quit", Button((cx - 100, 484, 200, 50), "Quit"))]
        self.selected = 0
        self.hill_y = 430
        self.stars = [(random.randint(0, C.SCREEN_W), random.randint(0, self.hill_y - 60),
                       random.uniform(0, math.tau), random.uniform(1.5, 3.5)) for _ in range(70)]
        self.clouds = [[random.randint(0, C.SCREEN_W), random.randint(50, 220),
                        random.uniform(0.7, 1.4), random.uniform(6, 16)] for _ in range(4)]
        self.sheep_spots = [(140, 452), (210, 470), (300, 458), (720, 466), (800, 450)]
        self.bg = self._build_bg()

    def _build_bg(self):
        surf = pygame.Surface((C.SCREEN_W, C.SCREEN_H))
        for y in range(self.hill_y):
            surf.fill(lerp_color(self.SKY_TOP, self.SKY_HORIZON, y / self.hill_y), (0, y, C.SCREEN_W, 1))
        surf.fill(self.HILL, (0, self.hill_y, C.SCREEN_W, C.SCREEN_H - self.hill_y))
        pygame.draw.ellipse(surf, (255, 240, 210), (760, 70, 110, 110))
        pygame.draw.ellipse(surf, self.SKY_HORIZON, (780, 72, 110, 110))
        pygame.draw.ellipse(surf, self.HILL_BACK, (-120, self.hill_y - 90, 520, 220))
        pygame.draw.ellipse(surf, self.HILL_BACK, (620, self.hill_y - 70, 540, 200))
        return surf

    def _draw_cloud(self, surface, x, y, s):
        cloud = pygame.Surface((int(130 * s), int(60 * s)), pygame.SRCALPHA)
        for ox, oy, r in ((20, 30, 22), (50, 22, 28), (82, 32, 24), (40, 36, 20)):
            pygame.draw.ellipse(cloud, (240, 230, 235, 150),
                                (int(ox * s), int(oy * s), int(r * 2 * s), int(r * 1.6 * s)))
        surface.blit(cloud, (x, y))

    def _draw_sheep(self, surface, x, y, phase):
        yy = y + math.sin(self.t * 2 + phase) * 1.5
        pygame.draw.ellipse(surface, (236, 236, 230), (x, yy, 26, 18))
        pygame.draw.circle(surface, (60, 60, 64), (int(x + 22), int(yy + 6)), 5)
        pygame.draw.circle(surface, (40, 42, 46), (int(x + 4), int(yy + 16)), 2)
        pygame.draw.circle(surface, (40, 42, 46), (int(x + 20), int(yy + 16)), 2)

    def update(self, dt):
        self.t += dt
        for c in self.clouds:
            c[0] += c[3] * dt
            if c[0] > C.SCREEN_W + 20:
                c[0] = -180
                c[1] = random.randint(50, 220)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_DOWN:
                self.selected = (self.selected + 1) % len(self.items)
            elif event.key == pygame.K_UP:
                self.selected = (self.selected - 1) % len(self.items)
            elif event.key == pygame.K_RETURN:
                self._activate(self.items[self.selected][0])
            elif event.key == pygame.K_ESCAPE:
                self.game.running = False
            elif event.key == pygame.K_BACKSPACE:
                self.name = self.name[:-1]
            elif event.unicode and event.unicode.isprintable() and len(self.name) < 14 and event.unicode not in "\r\t":
                self.name += event.unicode
        elif event.type == pygame.MOUSEMOTION:
            for idx, (_, btn) in enumerate(self.items):
                if btn.hit(event.pos):
                    self.selected = idx
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for name, btn in self.items:
                if btn.hit(event.pos):
                    self._activate(name)

    def _activate(self, name):
        self.game.sound.play_sfx("ui_click")
        if name == "play":
            self.game.start_new_game(self.name)
        elif name == "records":
            self.game.player_id = self.game.db.get_or_create_player(self.name.strip() or "Shepherd")
            self.game.last_name = self.name.strip() or "Shepherd"
            self.game.scene = RecordsScene(self.game)
        elif name == "quit":
            self.game.running = False

    def draw(self, surface):
        surface.blit(self.bg, (0, 0))
        for x, y, ph, sp in self.stars:
            if 120 + 110 * math.sin(self.t * sp + ph) > 150:
                surface.fill((255, 255, 240), (x, y, 2, 2))
        for c in self.clouds:
            self._draw_cloud(surface, int(c[0]), int(c[1]), c[2])
        for i, (sx, sy) in enumerate(self.sheep_spots):
            self._draw_sheep(surface, sx, sy, i * 1.3)
        bob = math.sin(self.t * 1.5) * 4
        title = self.title_font.render(story.GAME_TITLE, True, (250, 240, 220))
        shadow = self.title_font.render(story.GAME_TITLE, True, (30, 30, 40))
        tr = title.get_rect(center=(C.SCREEN_W // 2, 140 + bob))
        surface.blit(shadow, shadow.get_rect(center=(tr.centerx + 3, tr.centery + 3)))
        surface.blit(title, tr)
        sub = self.sub_font.render(story.GAME_SUBTITLE, True, (250, 226, 200))
        surface.blit(sub, sub.get_rect(center=(C.SCREEN_W // 2, 205 + bob)))

        box = pygame.Rect(C.SCREEN_W // 2 - 150, 290, 300, 44)
        pygame.draw.rect(surface, (30, 40, 34), box, border_radius=8)
        pygame.draw.rect(surface, (150, 170, 150), box, 2, border_radius=8)
        caret = "_" if int(self.t * 2) % 2 == 0 else " "
        name_txt = self.label_font.render("Name: " + (self.name or "Shepherd") + caret, True, (235, 235, 225))
        surface.blit(name_txt, name_txt.get_rect(midleft=(box.x + 14, box.centery)))

        for idx, (_, btn) in enumerate(self.items):
            btn.draw(surface, idx == self.selected)
        tip = self.tip_font.render("Type your name  -  WASD/Arrows move  -  Shift sprint  -  Space bark  -  F11 window", True, (235, 235, 230))
        surface.blit(tip, tip.get_rect(center=(C.SCREEN_W // 2, C.SCREEN_H - 20)))


class PlayScene(Scene):
    def __init__(self, game, day_index):
        super().__init__(game)
        self.day_index = day_index
        self.cfg = C.DAYS[day_index]
        w, h = self.cfg["world"]
        self.tilemap = TileMap(w, h)
        pen_w, pen_h = 8, 5
        pen_cx, pen_cy = w // 2 - pen_w // 2, 1
        self.tilemap.clear_rect(pen_cx - 1, pen_cy - 1, pen_w + 2, pen_h + 2)
        self.pen = Pen(pen_cx, pen_cy, pen_w, pen_h)
        self.camera = Camera(w * C.TILE, h * C.TILE)
        dog_cx = pen_cx + pen_w // 2
        dog_cy = pen_cy + pen_h + 1
        self.tilemap.clear_rect(dog_cx - 1, pen_cy, 3, pen_h + 3)
        self.dog = Dog((dog_cx * C.TILE + C.TILE // 2, dog_cy * C.TILE))
        self.dog.block_rect = self.pen.rect.inflate(self.dog.radius * 2, self.dog.radius * 2)
        self.flock = Flock(self.tilemap, self.pen, self.cfg["sheep_total"])
        day = self.cfg["day"]
        lead = min(0.7, 0.12 * day)
        retreat = max(0.7, 1.6 - 0.15 * day)
        fear = max(110, 170 - 8 * day)
        self.wolves = []
        spawns = [(2, h - 3), (w - 3, h - 3), (w // 2, h - 2)]
        for i in range(self.cfg["wolves"]):
            sx, sy = spawns[i % len(spawns)]
            self.tilemap.clear_rect(max(0, sx - 1), max(0, sy - 1), 3, 3)
            wolf = Wolf((sx * C.TILE, sy * C.TILE), self.cfg["wolf_speed"],
                        self.cfg["vision"], lead, retreat, fear)
            wolf.block_rect = self.pen.rect.inflate(wolf.radius * 2, wolf.radius * 2)
            self.wolves.append(wolf)
        self.time_left = float(self.cfg["time"])
        self.font = make_font(20, bold=True)
        self.dialog = DialogBox(story.day_intro(self.cfg["day"]), self.game.sound)
        self.events = []
        self.ended = False
        self.prev_lost = 0
        self.prev_states = [w.state for w in self.wolves]
        self.wolf_scared = 0
        self.bark_cd = 0.0
        self.howled = False
        self.baa_t = random.uniform(4.0, 9.0)
        self.paused = False
        self.pause_font = make_title(52, bold=True)
        pcx = C.SCREEN_W // 2
        self.pause_buttons = [("resume", Button((pcx - 120, 310, 240, 52), "Resume", 26)),
                              ("menu", Button((pcx - 120, 380, 240, 52), "Quit to Menu", 24))]
        self.pause_sel = 0
        self.game.sound.play_music("music_day")
        self._log("DAY_START", self.dog.pos)

    def _log(self, code, pos):
        t = round(self.cfg["time"] - self.time_left, 2)
        self.events.append((code, t, int(pos[0]), int(pos[1])))

    def _bark(self):
        if self.bark_cd > 0:
            return
        self.bark_cd = 0.7
        self.game.sound.play_sfx("dog_bark")
        self.game.sound.play_sfx("sheep_scared", 0.6)
        for s in self.flock.sheep:
            if s.penned or s.lost:
                continue
            d = self.dog.pos.distance_to(s.pos)
            if 1e-5 < d < 170:
                s.vel += (s.pos - self.dog.pos) / d * 160
                s.state = "scared"

    def handle_event(self, event):
        if self.dialog.active:
            self.dialog.handle_event(event)
            return
        if self.paused:
            self._handle_pause_event(event)
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.paused = True
                self.game.sound.play_sfx("ui_click")
            elif event.key == pygame.K_SPACE:
                self._bark()

    def _handle_pause_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_p):
                self._pause_action("resume")
            elif event.key in (pygame.K_m, pygame.K_q):
                self._pause_action("menu")
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._pause_action(self.pause_buttons[self.pause_sel][0])
            elif event.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_TAB):
                self.pause_sel = 1 - self.pause_sel
        elif event.type == pygame.MOUSEMOTION:
            for i, (_, btn) in enumerate(self.pause_buttons):
                if btn.hit(event.pos):
                    self.pause_sel = i
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for name, btn in self.pause_buttons:
                if btn.hit(event.pos):
                    self._pause_action(name)

    def _pause_action(self, name):
        self.game.sound.play_sfx("ui_click")
        if name == "resume":
            self.paused = False
        else:
            self.game.change_scene("menu")

    def update(self, dt):
        if self.dialog.active or self.ended or self.paused:
            return
        self.bark_cd = max(0.0, self.bark_cd - dt)
        keys = pygame.key.get_pressed()
        self.dog.update(dt, keys, self.tilemap)
        newly = self.flock.update(dt, self.dog, self.wolves, self.tilemap, self.pen)
        for w in self.wolves:
            w.update(dt, self.flock, self.dog, self.tilemap)
        self.camera.follow(self.dog.pos)
        self.time_left = max(0.0, self.time_left - dt)

        if newly:
            self.game.sound.play_sfx("sheep_penned")
            for _ in range(newly):
                self._log("SHEEP_PENNED", self.pen.rect.center)

        penned, lost = self.flock.counts()
        if lost > self.prev_lost:
            for _ in range(lost - self.prev_lost):
                self._log("SHEEP_LOST", self.dog.pos)
            self.game.sound.play_sfx("sheep_lost")
            self.prev_lost = lost

        for i, w in enumerate(self.wolves):
            if self.prev_states[i] != w.state:
                if w.state == "stalk":
                    self._log("WOLF_SPOTTED", w.pos)
                    if not self.howled:
                        self.howled = True
                        self.game.sound.play_sfx("wolf_howl")
                    else:
                        self.game.sound.play_sfx("wolf_growl")
                elif w.state == "retreat" and w.pos.distance_to(self.dog.pos) < w.fear_radius + 12:
                    self._log("DOG_SCARED_WOLF", w.pos)
                    self.wolf_scared += 1
                self.prev_states[i] = w.state

        self.baa_t -= dt
        if self.baa_t <= 0:
            self.baa_t = random.uniform(5.0, 11.0)
            if any(not s.penned and not s.lost for s in self.flock.sheep):
                self.game.sound.play_sfx("sheep_baa", 0.4)

        self._check_end(penned, lost)

    def _check_end(self, penned, lost):
        total = self.cfg["sheep_total"]
        if lost > self.cfg["max_lost"]:
            return self._finish(False, penned, lost)
        if penned + lost >= total or self.time_left <= 0:
            return self._finish(penned >= self.cfg["required"], penned, lost)

    def _finish(self, completed, penned, lost):
        if self.ended:
            return
        self.ended = True
        self._log("DAY_END", self.dog.pos)
        time_taken = round(self.cfg["time"] - self.time_left, 1)
        score = day_score(penned, lost, self.time_left, completed)
        if completed:
            self.game.sound.play_sfx("day_win")
        self.game.on_day_end({
            "day": self.cfg["day"], "total": self.cfg["sheep_total"],
            "saved": penned, "lost": lost, "time_taken": time_taken,
            "score": score, "completed": completed, "events": self.events,
            "wolf_scared": self.wolf_scared,
        })

    def _draw_hud(self, surface):
        penned, lost = self.flock.counts()
        bar = pygame.Surface((C.SCREEN_W, 40), pygame.SRCALPHA)
        bar.fill((0, 0, 0, 120))
        surface.blit(bar, (0, 0))
        field = self.cfg["sheep_total"] - penned - lost
        txt = (f"Day {self.cfg['day']}     Sunset {int(self.time_left)}s     "
               f"Penned {penned}/{self.cfg['required']}     On field {field}     Lost {lost}/{self.cfg['max_lost']}")
        surface.blit(self.font.render(txt, True, (240, 240, 235)), (14, 10))
        frac = self.dog.stamina / C.STAMINA_MAX
        pygame.draw.rect(surface, (40, 40, 40), (14, C.SCREEN_H - 30, 180, 16), border_radius=4)
        col = (90, 190, 90) if frac > 0.3 else (210, 120, 60)
        pygame.draw.rect(surface, col, (14, C.SCREEN_H - 30, int(180 * frac), 16), border_radius=4)
        surface.blit(self.font.render("Stamina", True, (230, 230, 230)), (14, C.SCREEN_H - 54))

    def draw(self, surface):
        surface.fill((20, 30, 20))
        tm, cam, assets = self.tilemap, self.camera, self.game.assets
        tm.draw_ground(surface, cam, assets)
        self.pen.draw(surface, cam, assets)

        drawables = [((cy + 1) * C.TILE, cx, cy, name) for cx, cy, name in tm.visible_obstacles(cam)]
        ents = [self.dog] + self.wolves + [s for s in self.flock.sheep if not s.lost]
        items = [(d[0], "obs", d) for d in drawables] + [(e.pos.y, "ent", e) for e in ents]
        items.sort(key=lambda it: it[0])
        for _, kind, data in items:
            if kind == "obs":
                tm.blit_obstacle(surface, cam, assets, data[1], data[2], data[3])
            else:
                data.draw(surface, cam, assets)

        self._draw_hud(surface)
        if self.dialog.active:
            self.dialog.draw(surface)
        elif self.paused:
            self._draw_pause(surface)

    def _draw_pause(self, surface):
        dim = pygame.Surface((C.SCREEN_W, C.SCREEN_H), pygame.SRCALPHA)
        dim.fill((10, 14, 20, 180))
        surface.blit(dim, (0, 0))
        title = self.pause_font.render("Paused", True, (250, 240, 220))
        surface.blit(title, title.get_rect(center=(C.SCREEN_W // 2, 230)))
        for i, (_, btn) in enumerate(self.pause_buttons):
            btn.draw(surface, i == self.pause_sel)


class InterludeScene(Scene):
    def __init__(self, game, stats):
        super().__init__(game)
        self.stats = stats
        self.t = 0.0
        self.title_font = make_title(40, bold=True)
        self.font = make_font(24)
        self.dialog = DialogBox(story.day_win(stats["day"]), self.game.sound)
        self.cont = Button((C.SCREEN_W // 2 - 110, 500, 220, 52), "Continue")

    def update(self, dt):
        self.t += dt

    def handle_event(self, event):
        if self.dialog.active:
            self.dialog.handle_event(event)
            return
        if (event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE)) or \
           (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.cont.hit(event.pos)):
            self.game.sound.play_sfx("ui_click")
            self.game.continue_to_next_day()

    def draw(self, surface):
        for y in range(C.SCREEN_H):
            surface.fill(lerp_color((24, 28, 52), (60, 48, 60), y / C.SCREEN_H), (0, y, C.SCREEN_W, 1))
        pygame.draw.ellipse(surface, (250, 240, 210), (120, 60, 90, 90))
        pygame.draw.rect(surface, (34, 44, 36), (0, 470, C.SCREEN_W, C.SCREEN_H - 470))
        pygame.draw.rect(surface, (110, 80, 50), (640, 360, 240, 120), border_radius=6)
        pygame.draw.rect(surface, (150, 110, 70), (640, 360, 240, 120), 4, border_radius=6)

        title = self.title_font.render(f"Day {self.stats['day']} - safe in the pen", True, (250, 240, 220))
        surface.blit(title, title.get_rect(center=(C.SCREEN_W // 2, 110)))
        lines = [f"Sheep saved: {self.stats['saved']} / {self.stats['total']}",
                 f"Lost to the wolf: {self.stats['lost']}",
                 f"Day score: {self.stats['score']}      Season total: {self.game.total_score}"]
        for i, ln in enumerate(lines):
            t = self.font.render(ln, True, (235, 235, 225))
            surface.blit(t, t.get_rect(center=(C.SCREEN_W // 2, 190 + i * 36)))

        if self.dialog.active:
            self.dialog.draw(surface)
        else:
            self.cont.draw(surface, True)


class GameoverScene(Scene):
    def __init__(self, game, result):
        super().__init__(game)
        self.result = result
        self.game.finalize_session(result)
        if result == "win":
            self.game.sound.play_music("music_menu")
        else:
            self.game.sound.play_music("game_over", loop=False)
        self.title_font = make_title(64, bold=True)
        self.font = make_font(24)
        self.dialog = DialogBox(story.ending(game.lost_total), self.game.sound)
        cx = C.SCREEN_W // 2
        self.buttons = [("records", Button((cx - 230, 520, 200, 50), "Records")),
                        ("menu", Button((cx + 30, 520, 200, 50), "Menu"))]
        self.selected = 0

    def handle_event(self, event):
        if self.dialog.active:
            self.dialog.handle_event(event)
            return
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_TAB):
                self.selected = 1 - self.selected
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._activate(self.buttons[self.selected][0])
        elif event.type == pygame.MOUSEMOTION:
            for idx, (_, btn) in enumerate(self.buttons):
                if btn.hit(event.pos):
                    self.selected = idx
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for name, btn in self.buttons:
                if btn.hit(event.pos):
                    self._activate(name)

    def _activate(self, name):
        self.game.sound.play_sfx("ui_click")
        if name == "records":
            self.game.scene = RecordsScene(self.game)
        else:
            self.game.change_scene("menu")

    def draw(self, surface):
        win = self.result == "win"
        top = (34, 50, 70) if win else (54, 30, 30)
        for y in range(C.SCREEN_H):
            surface.fill(lerp_color(top, (18, 20, 26), y / C.SCREEN_H), (0, y, C.SCREEN_W, 1))
        title = self.title_font.render("The flock is safe" if win else "A hard autumn",
                                        True, (250, 240, 210) if win else (240, 200, 190))
        surface.blit(title, title.get_rect(center=(C.SCREEN_W // 2, 120)))
        lines = [f"Season score: {self.game.total_score}",
                 f"Sheep saved: {self.game.saved_total}      Lost: {self.game.lost_total}",
                 f"Days survived: {self.game.days_done} / {len(C.DAYS)}"]
        for i, ln in enumerate(lines):
            t = self.font.render(ln, True, (235, 235, 225))
            surface.blit(t, t.get_rect(center=(C.SCREEN_W // 2, 200 + i * 38)))
        if self.dialog.active:
            self.dialog.draw(surface)
        else:
            for idx, (_, btn) in enumerate(self.buttons):
                btn.draw(surface, idx == self.selected)


class RecordsScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.rows = game.db.top_sessions(8)
        self.stats = game.db.player_stats(game.player_id) if game.player_id else None
        self.title_font = make_title(48, bold=True)
        self.font = make_font(22)
        self.small = make_font(18)
        self.back = Button((C.SCREEN_W // 2 - 100, 560, 200, 46), "Back")

    def handle_event(self, event):
        if (event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN)) or \
           (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.back.hit(event.pos)):
            self.game.sound.play_sfx("ui_click")
            self.game.change_scene("menu")

    def draw(self, surface):
        for y in range(C.SCREEN_H):
            surface.fill(lerp_color((30, 40, 60), (16, 20, 28), y / C.SCREEN_H), (0, y, C.SCREEN_W, 1))
        title = self.title_font.render("Records", True, (250, 240, 220))
        surface.blit(title, title.get_rect(center=(C.SCREEN_W // 2, 70)))

        cols = [("#", 180), ("Name", 240), ("Score", 470), ("Days", 600), ("Result", 700)]
        for name, x in cols:
            surface.blit(self.font.render(name, True, (210, 200, 140)), (x, 140))
        pygame.draw.line(surface, (120, 120, 130), (170, 170), (790, 170), 1)
        if not self.rows:
            msg = self.font.render("No finished games yet - go herd some sheep!", True, (220, 220, 215))
            surface.blit(msg, msg.get_rect(center=(C.SCREEN_W // 2, 240)))
        for i, (nick, score, days, result, _) in enumerate(self.rows):
            y = 185 + i * 34
            vals = [(str(i + 1), 180), (nick[:16], 240), (str(score), 470), (str(days), 600), (result or "-", 700)]
            for v, x in vals:
                surface.blit(self.font.render(v, True, (235, 235, 230)), (x, y))

        if self.stats:
            s = self.stats
            line = f"{self.game.last_name}:   best {s['best']}   -   games {s['games']}   -   total saved {s['saved']}"
            t = self.small.render(line, True, (200, 215, 200))
            surface.blit(t, t.get_rect(center=(C.SCREEN_W // 2, 500)))
        self.back.draw(surface, True)


class Game:
    def __init__(self):
        pygame.init()
        try:
            self.screen = pygame.display.set_mode((C.SCREEN_W, C.SCREEN_H),
                                                  pygame.SCALED | pygame.FULLSCREEN, vsync=1)
        except pygame.error:
            self.screen = pygame.display.set_mode((C.SCREEN_W, C.SCREEN_H), pygame.SCALED)
        pygame.display.set_caption(C.TITLE)
        self.clock = pygame.time.Clock()
        self.assets = AssetManager()
        self.sound = SoundManager()
        self.db = Database()
        self.running = True
        self.last_name = ""
        self.player_id = None
        self.session_id = None
        self.session_open = False
        self.day_index = 0
        self.saved_total = 0
        self.lost_total = 0
        self.total_score = 0
        self.days_done = 0
        self.wolf_scared_total = 0
        self.had_no_loss = False
        self.had_fast_day = False
        self.scene = None
        self.change_scene("menu")

    def change_scene(self, name):
        if name == "menu":
            self.scene = MenuScene(self)
        elif name == "records":
            self.scene = RecordsScene(self)

    def start_new_game(self, name):
        name = (name or "").strip() or "Shepherd"
        self.last_name = name
        self.player_id = self.db.get_or_create_player(name)
        self.session_id = self.db.start_session(self.player_id, C.DEFAULT_DIFFICULTY)
        self.session_open = True
        self.day_index = 0
        self.saved_total = self.lost_total = self.total_score = self.days_done = 0
        self.wolf_scared_total = 0
        self.had_no_loss = self.had_fast_day = False
        self.scene = PlayScene(self, 0)

    def on_day_end(self, stats):
        day_id = self.db.insert_day_result(
            self.session_id, stats["day"], stats["total"], stats["saved"],
            stats["lost"], stats["time_taken"], stats["score"], 1 if stats["completed"] else 0)
        self.db.add_events(day_id, stats["events"])
        self.saved_total += stats["saved"]
        self.lost_total += stats["lost"]
        self.total_score += stats["score"]
        self.wolf_scared_total += stats["wolf_scared"]
        if stats["completed"]:
            self.days_done += 1
            if stats["lost"] == 0:
                self.had_no_loss = True
            if stats["time_taken"] < 60:
                self.had_fast_day = True
            if self.day_index >= len(C.DAYS) - 1:
                self.scene = GameoverScene(self, "win")
            else:
                self.scene = InterludeScene(self, stats)
        else:
            self.scene = GameoverScene(self, "lose")

    def continue_to_next_day(self):
        self.day_index += 1
        self.scene = PlayScene(self, self.day_index)

    def finalize_session(self, result):
        if not self.session_open:
            return
        self.session_open = False
        self.db.finish_session(self.session_id, result, self.total_score, self.days_done)
        self.db.update_best(self.player_id, self.total_score)
        if result == "win":
            self.db.award(self.player_id, "SEASON_WIN")
        if self.had_no_loss:
            self.db.award(self.player_id, "NO_LOSS")
        if self.had_fast_day:
            self.db.award(self.player_id, "FAST_DAY")
        if self.wolf_scared_total >= 10:
            self.db.award(self.player_id, "WOLF_BRAVE")

    def run(self):
        while self.running:
            dt = self.clock.tick(C.FPS) / 1000.0
            if dt > 0.05:
                dt = 0.05
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                    pygame.display.toggle_fullscreen()
                else:
                    self.scene.handle_event(event)
            self.scene.update(dt)
            self.scene.draw(self.screen)
            pygame.display.flip()
        pygame.quit()
        sys.exit()
