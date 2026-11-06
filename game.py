import sys
import math
import random
import pygame
from pygame.math import Vector2

# Наші власні модулі гри.
import config as C
import story
from assets import AssetManager
from audio import SoundManager
from database import Database
from world import TileMap, Camera, Pen
from entities import Dog, Flock, Wolf

UI_FONT = "verdana,segoeui,arial"                      # для кнопок, HUD
TITLE_FONT = "georgia,constantia,timesnewroman,serif"  # для заголовків і діалогів


def make_font(size, bold=False):
    # Створює шрифт інтерфейсу заданого розміру.
    return pygame.font.SysFont(UI_FONT, size, bold=bold)


def make_title(size, bold=False):
    # Створює "книжковий" шрифт для заголовків/сюжету.
    return pygame.font.SysFont(TITLE_FONT, size, bold=bold)


def lerp_color(a, b, t):
    # Плавний перехід між двома кольорами: t=0 -> колір a, t=1 -> колір b
    # Використовується для градієнтів неба
    return (int(a[0] + (b[0] - a[0]) * t),
            int(a[1] + (b[1] - a[1]) * t),
            int(a[2] + (b[2] - a[2]) * t))


def day_score(saved, lost, time_left, completed):
    # Рахунок за день: +100 за врятовану вівцю, -40 за втрачену
    # + бонус за час, що лишився (лише якщо день зараховано)
    s = saved * 100 - lost * 40
    if completed:
        s += int(time_left) * 3
    return max(0, s)


class Scene:
    # Базовий клас усіх екранів.
    def __init__(self, game):
        self.game = game          # посилання на головний об'єкт гри

    def handle_event(self, event):
        pass                      # обробка вводу (клавіші, миша)

    def update(self, dt):
        pass                      # оновлення логіки за час dt

    def draw(self, surface):
        pass                      # малювання екрана


class DialogBox:
    # Вікно діалогу внизу екрана: показує репліки по черзі з озвученням.
    def __init__(self, lines, sound=None):
        self.lines = list(lines)             # список реплік (пари "хто", "що")
        self.i = 0                           # індекс поточної репліки
        self.active = len(self.lines) > 0    # чи є що показувати (False, якщо список порожній)
        self.sound = sound                   # менеджер звуку (для голосу деда)
        self.font = make_title(22)           # шрифт тексту репліки
        self.small = make_title(18, bold=True)  # шрифт імені та підказки
        self._speak()                        # одразу озвучити першу репліку

    def _speak(self):
        # Запустити голос, якщо діалог активний, звук є і в репліки є той, хто говорить.
        if self.active and self.sound and self.lines[self.i][0]:
            self.sound.play_voice()

    def _advance(self):
        # Перейти до наступної репліки (або закрити діалог, якщо репліки скінчилися).
        if self.sound:
            self.sound.stop_voice()          # приглушити голос попередньої репліки
        self.i += 1
        if self.i >= len(self.lines):
            self.active = False              # реплік більше немає - закриваємось
        else:
            self._speak()                    # озвучити нову репліку

    def handle_event(self, event):
        # Space / Enter / E / клік лівою - наступна репліка.
        if not self.active:
            return
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_e):
            self._advance()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._advance()

    def _wrapped(self, surface, text, x, y, maxw):
        # Малює текст із перенесенням по словах, щоб не вилазив за ширину maxw.
        line = ""
        for word in text.split(" "):             # по одному слову
            test = (line + " " + word).strip()   # пробуємо додати слово в рядок
            if self.font.size(test)[0] > maxw and line:  # якщо рядок став задовгий
                surface.blit(self.font.render(line, True, (236, 236, 232)), (x, y))
                y += 28                          # переходимо на новий рядок нижче
                line = word
            else:
                line = test                      # слово вміщається - лишаємо в рядку
        if line:
            surface.blit(self.font.render(line, True, (236, 236, 232)), (x, y))  # останній рядок

    def draw(self, surface):
        if not self.active:
            return
        speaker, text = self.lines[self.i]       # розпаковуємо пару: ім'я і текст
        box = pygame.Rect(50, C.SCREEN_H - 150, C.SCREEN_W - 100, 120)  # рамка внизу екрана
        panel = pygame.Surface(box.size, pygame.SRCALPHA)
        panel.fill((18, 22, 28, 232))            # напівпрозорий темний фон
        surface.blit(panel, box.topleft)
        pygame.draw.rect(surface, (184, 150, 96), box, 2, border_radius=8)  # рамка зі скругленими кутами
        if speaker:                              # якщо є хто говорить - пишемо ім'я
            surface.blit(self.small.render(speaker, True, (232, 196, 120)), (box.x + 18, box.y + 12))
        self._wrapped(surface, text, box.x + 18, box.y + 42, box.w - 36)   # сам текст із перенесенням
        hint = self.small.render("[Space] continue", True, (150, 158, 168))  # підказка
        surface.blit(hint, (box.right - hint.get_width() - 16, box.bottom - 26))


class Button:
    # Кнопка інтерфейсу: прямокутник із написом, що підсвічується, коли обрана.
    def __init__(self, rect, text, size=28):
        self.rect = pygame.Rect(rect)        # прямокутник кнопки (x, y, ширина, висота)
        self.text = text                     # напис
        self.font = make_font(size, bold=True)

    def draw(self, surface, selected):
        # Малює кнопку; selected=True -> яскравіша й трохи більша.
        base = (74, 104, 64) if selected else (46, 64, 46)     # колір заливки
        edge = (240, 210, 130) if selected else (150, 170, 150)  # колір рамки
        r = self.rect.inflate(12, 6) if selected else self.rect  # обрана - трохи збільшуємо
        pygame.draw.rect(surface, base, r, border_radius=10)     # заливка
        pygame.draw.rect(surface, edge, r, 3, border_radius=10)  # рамка (товщина 3)
        col = (255, 244, 210) if selected else (220, 228, 218)   # колір тексту
        label = self.font.render(self.text, True, col)
        surface.blit(label, label.get_rect(center=r.center))     # напис по центру кнопки

    def hit(self, pos):
        # Чи потрапила точка pos (напр. курсор миші) у кнопку?
        return self.rect.inflate(12, 6).collidepoint(pos)


class MenuScene(Scene):
    # Головне меню: анімоване небо-захід, зорі, хмари, вівці, ввід імені, кнопки.
    SKY_TOP = (28, 32, 70)       # колір неба вгорі (темно-синій)
    SKY_HORIZON = (244, 158, 92)  # колір біля горизонту (теплий помаранчевий)
    HILL = (44, 72, 44)          # передній пагорб
    HILL_BACK = (34, 58, 40)     # дальні пагорби

    def __init__(self, game):
        super().__init__(game)
        self.game.sound.play_music("music_menu")  # вмикаємо музику меню
        self.t = 0.0                           # час від старту меню (для анімацій)
        self.title_font = make_title(96, bold=True)  # шрифт назви
        self.sub_font = make_title(26)         # підзаголовок
        self.label_font = make_font(20)        # поле імені
        self.tip_font = make_font(18)          # підказка внизу
        self.name = game.last_name             # ім'я гравця (запам'ятоване з минулого разу)
        cx = C.SCREEN_W // 2                    # центр екрана по X
        # Кнопки меню: список пар (назва_дії, об'єкт Button).
        self.items = [("play", Button((cx - 100, 360, 200, 50), "Play")),
                      ("records", Button((cx - 100, 422, 200, 50), "Records")),
                      ("quit", Button((cx - 100, 484, 200, 50), "Quit"))]
        self.selected = 0                       # індекс обраної кнопки
        self.hill_y = 430                       # на якій висоті починається пагорб
        # Зорі: список (x, y, фаза, швидкість мерехтіння)
        self.stars = [(random.randint(0, C.SCREEN_W), random.randint(0, self.hill_y - 60),
                       random.uniform(0, math.tau), random.uniform(1.5, 3.5)) for _ in range(70)]
        # Хмари: список [x, y, масштаб, швидкість] - 4 штуки (списки, бо x змінюється).
        self.clouds = [[random.randint(0, C.SCREEN_W), random.randint(50, 220),
                        random.uniform(0.7, 1.4), random.uniform(6, 16)] for _ in range(4)]
        self.sheep_spots = [(140, 452), (210, 470), (300, 458), (720, 466), (800, 450)]  # де стоять вівці
        self.bg = self._build_bg()              # малюємо статичний фон один раз і зберігаємо

    def _build_bg(self):
        # Малює СТАТИЧНУ частину фону один раз (щоб не перемальовувати щокадру).
        surf = pygame.Surface((C.SCREEN_W, C.SCREEN_H))
        for y in range(self.hill_y):  # градієнт неба: рядок за рядком згори вниз
            surf.fill(lerp_color(self.SKY_TOP, self.SKY_HORIZON, y / self.hill_y), (0, y, C.SCREEN_W, 1))
        surf.fill(self.HILL, (0, self.hill_y, C.SCREEN_W, C.SCREEN_H - self.hill_y))  # передній пагорб
        pygame.draw.ellipse(surf, (255, 240, 210), (760, 70, 110, 110))   # місяць (світлий)
        pygame.draw.ellipse(surf, self.SKY_HORIZON, (780, 72, 110, 110))  # тінь на місяці (серп)
        pygame.draw.ellipse(surf, self.HILL_BACK, (-120, self.hill_y - 90, 520, 220))  # дальні пагорби
        pygame.draw.ellipse(surf, self.HILL_BACK, (620, self.hill_y - 70, 540, 200))
        return surf

    def _draw_cloud(self, surface, x, y, s):
        # Хмара = кілька овалів, зібраних докупи на окремій прозорій поверхні. s - масштаб.
        cloud = pygame.Surface((int(130 * s), int(60 * s)), pygame.SRCALPHA)
        for ox, oy, r in ((20, 30, 22), (50, 22, 28), (82, 32, 24), (40, 36, 20)):
            pygame.draw.ellipse(cloud, (240, 230, 235, 150),
                                (int(ox * s), int(oy * s), int(r * 2 * s), int(r * 1.6 * s)))
        surface.blit(cloud, (x, y))

    def _draw_sheep(self, surface, x, y, phase):
        # Вівця = овал (тіло) + голова + дві ніжки. Легко похитується через sin.
        yy = y + math.sin(self.t * 2 + phase) * 1.5   # вертикальне похитування в часі
        pygame.draw.ellipse(surface, (236, 236, 230), (x, yy, 26, 18))       # тіло
        pygame.draw.circle(surface, (60, 60, 64), (int(x + 22), int(yy + 6)), 5)  # голова
        pygame.draw.circle(surface, (40, 42, 46), (int(x + 4), int(yy + 16)), 2)  # ніжка 1
        pygame.draw.circle(surface, (40, 42, 46), (int(x + 20), int(yy + 16)), 2) # ніжка 2

    def update(self, dt):
        # Оновлення анімації меню
        self.t += dt                      # накопичуємо час (ним керуються всі коливання)
        for c in self.clouds:
            c[0] += c[3] * dt             # c[0]=x зсуваємо на швидкість c[3]
            if c[0] > C.SCREEN_W + 20:    # хмара виїхала за правий край
                c[0] = -180               # повертаємо її ліворуч за екран
                c[1] = random.randint(50, 220)  # на нову випадкову висоту

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:                 # натиснули клавішу
            if event.key == pygame.K_DOWN:
                self.selected = (self.selected + 1) % len(self.items)  # вниз по кнопках (по колу)
            elif event.key == pygame.K_UP:
                self.selected = (self.selected - 1) % len(self.items)  # вгору по колу
            elif event.key == pygame.K_RETURN:
                self._activate(self.items[self.selected][0])  # Enter - активувати обрану кнопку
            elif event.key == pygame.K_ESCAPE:
                self.game.running = False                 # Esc - вийти з гри
            elif event.key == pygame.K_BACKSPACE:
                self.name = self.name[:-1]                # стерти останню літеру імені
            elif event.unicode and event.unicode.isprintable() and len(self.name) < 14 and event.unicode not in "\r\t":
                self.name += event.unicode                # друкована літера - додати до імені (макс 14)
        elif event.type == pygame.MOUSEMOTION:            # рух миші - підсвічуємо кнопку під курсором
            for idx, (_, btn) in enumerate(self.items):
                if btn.hit(event.pos):
                    self.selected = idx
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:  # клік лівою
            for name, btn in self.items:
                if btn.hit(event.pos):
                    self._activate(name)

    def _activate(self, name):
        # Реакція на вибір кнопки (з клавіатури чи мишею).
        self.game.sound.play_sfx("ui_click")
        if name == "play":
            self.game.start_new_game(self.name)           # почати нову гру з введеним ім'ям
        elif name == "records":
            # створюємо/знаходимо гравця і відкриваємо екран рекордів
            self.game.player_id = self.game.db.get_or_create_player(self.name.strip() or "Shepherd")
            self.game.last_name = self.name.strip() or "Shepherd"
            self.game.scene = RecordsScene(self.game)
        elif name == "quit":
            self.game.running = False                     # вийти з гри

    def draw(self, surface):
        surface.blit(self.bg, (0, 0))               # 1) готовий статичний фон
        for x, y, ph, sp in self.stars:             # 2) зорі: мерехтять через sin
            if 120 + 110 * math.sin(self.t * sp + ph) > 150:  # показуємо лише коли яскравість висока
                surface.fill((255, 255, 240), (x, y, 2, 2))    # маленька крапка-зірка 2x2
        for c in self.clouds:                       # 3) хмари (рухомі)
            self._draw_cloud(surface, int(c[0]), int(c[1]), c[2])
        for i, (sx, sy) in enumerate(self.sheep_spots):  # 4) вівці на пагорбі
            self._draw_sheep(surface, sx, sy, i * 1.3)

        bob = math.sin(self.t * 1.5) * 4            # легке дихання назви вгору-вниз
        title = self.title_font.render(story.GAME_TITLE, True, (250, 240, 220))
        shadow = self.title_font.render(story.GAME_TITLE, True, (30, 30, 40))  # тінь назви
        tr = title.get_rect(center=(C.SCREEN_W // 2, 140 + bob))
        surface.blit(shadow, shadow.get_rect(center=(tr.centerx + 3, tr.centery + 3)))  # тінь зі зсувом
        surface.blit(title, tr)                     # сама назва поверх тіні
        sub = self.sub_font.render(story.GAME_SUBTITLE, True, (250, 226, 200))
        surface.blit(sub, sub.get_rect(center=(C.SCREEN_W // 2, 205 + bob)))  # підзаголовок

        box = pygame.Rect(C.SCREEN_W // 2 - 150, 290, 300, 44)   # поле вводу імені
        pygame.draw.rect(surface, (30, 40, 34), box, border_radius=8)       # фон поля
        pygame.draw.rect(surface, (150, 170, 150), box, 2, border_radius=8) # рамка поля
        caret = "_" if int(self.t * 2) % 2 == 0 else " "          # миготливий курсор (кожні пів секунди)
        name_txt = self.label_font.render("Name: " + (self.name or "Shepherd") + caret, True, (235, 235, 225))
        surface.blit(name_txt, name_txt.get_rect(midleft=(box.x + 14, box.centery)))

        for idx, (_, btn) in enumerate(self.items):  # малюємо всі кнопки; обрана підсвічена
            btn.draw(surface, idx == self.selected)
        tip = self.tip_font.render("Type your name  -  WASD/Arrows move  -  Shift sprint  -  Space bark  -  F11 window", True, (235, 235, 230))
        surface.blit(tip, tip.get_rect(center=(C.SCREEN_W // 2, C.SCREEN_H - 20)))  # підказка внизу


class PlayScene(Scene):
    # Один ігровий день: карта, кошара, собака, отара, вовки, HUD, пауза.
    def __init__(self, game, day_index):
        super().__init__(game)
        self.day_index = day_index          # номер дня 
        self.cfg = C.DAYS[day_index]         # налаштування цього дня зі словника DAYS
        w, h = self.cfg["world"]             # розмір світу в клітинах

        # КАРТА і КОШАРА
        self.tilemap = TileMap(w, h)         # генеруємо карту (трава, дерева, каміння)
        pen_w, pen_h = 8, 5                  # розмір кошари в клітинах
        pen_cx, pen_cy = w // 2 - pen_w // 2, 1   # кошара вгорі по центру
        self.tilemap.clear_rect(pen_cx - 1, pen_cy - 1, pen_w + 2, pen_h + 2)  # чистимо місце під неї
        self.pen = Pen(pen_cx, pen_cy, pen_w, pen_h)
        self.camera = Camera(w * C.TILE, h * C.TILE)  # камера знає розмір світу в пікселях

        # СОБАКА (гравець)
        dog_cx = pen_cx + pen_w // 2         # під воротами кошари
        dog_cy = pen_cy + pen_h + 1
        self.tilemap.clear_rect(dog_cx - 1, pen_cy, 3, pen_h + 3)  # коридор від воріт униз
        self.dog = Dog((dog_cx * C.TILE + C.TILE // 2, dog_cy * C.TILE))  # позиція в пікселях
        self.dog.block_rect = self.pen.rect.inflate(self.dog.radius * 2, self.dog.radius * 2)  # заборона заходити в кошару

        # ОТАРА
        self.flock = Flock(self.tilemap, self.pen, self.cfg["sheep_total"])  # створює овець

        # ВОВКИ (з адаптацією за днями)
        day = self.cfg["day"]
        lead = min(0.7, 0.12 * day)          # упередження: точніше ціляться з днями
        retreat = max(0.7, 1.6 - 0.15 * day) # швидше повертаються до полювання
        fear = max(110, 170 - 8 * day)       # наглішають (підпускають собаку ближче)
        self.wolves = []
        spawns = [(2, h - 3), (w - 3, h - 3), (w // 2, h - 2)]  # кути спавну подалі від кошари
        for i in range(self.cfg["wolves"]):  # скільки вовків у цей день
            sx, sy = spawns[i % len(spawns)]
            self.tilemap.clear_rect(max(0, sx - 1), max(0, sy - 1), 3, 3)  # чистимо місце спавну
            wolf = Wolf((sx * C.TILE, sy * C.TILE), self.cfg["wolf_speed"],
                        self.cfg["vision"], lead, retreat, fear)
            wolf.block_rect = self.pen.rect.inflate(wolf.radius * 2, wolf.radius * 2)  # теж не заходить у кошару
            self.wolves.append(wolf)

        # --- ТАЙМЕР і стан дня ---
        self.time_left = float(self.cfg["time"])  # секунд до заходу сонця
        self.font = make_font(20, bold=True)      # шрифт HUD
        self.dialog = DialogBox(story.day_intro(self.cfg["day"]), self.game.sound)  # вступні репліки
        self.events = []                     # журнал подій дня (для БД)
        self.ended = False                   # чи день уже завершено
        self.prev_lost = 0                   # скільки овець було втрачено на минулому кадрі
        self.prev_states = [w.state for w in self.wolves]  # стани вовків на минулому кадрі
        self.wolf_scared = 0                 # скільки разів відлякали вовка
        self.bark_cd = 0.0                   # перезарядка гав (щоб не спамити)
        self.howled = False                  # чи вже вив вовк цього дня
        self.baa_t = random.uniform(4.0, 9.0)  # таймер до наступного бекання овець

        # --- ПАУЗА ---
        self.paused = False
        self.pause_font = make_title(52, bold=True)
        pcx = C.SCREEN_W // 2
        self.pause_buttons = [("resume", Button((pcx - 120, 310, 240, 52), "Resume", 26)),
                              ("menu", Button((pcx - 120, 380, 240, 52), "Quit to Menu", 24))]
        self.pause_sel = 0

        self.game.sound.play_music("music_day")   # вмикаємо музику дня
        self._log("DAY_START", self.dog.pos)      # записуємо подію "початок дня"

    def _log(self, code, pos):
        # Записати подію в журнал дня: (код, секунда дня, x, y)
        t = round(self.cfg["time"] - self.time_left, 2)   # яка секунда дня зараз
        self.events.append((code, t, int(pos[0]), int(pos[1])))

    def _bark(self):
        # Гавкіт: лякає ближніх овець і грає звук
        if self.bark_cd > 0:              # ще не перезарядився - виходимо
            return
        self.bark_cd = 0.7                # ставимо перезарядку 0.7 c
        self.game.sound.play_sfx("dog_bark")
        self.game.sound.play_sfx("sheep_scared", 0.6)
        for s in self.flock.sheep:
            if s.penned or s.lost:        # загнаних/втрачених не чіпаємо
                continue
            d = self.dog.pos.distance_to(s.pos)   # відстань від собаки до вівці
            if 1e-5 < d < 170:            # лише ближні вівці (до 170 px)
                s.vel += (s.pos - self.dog.pos) / d * 250  # миттєвий поштовх геть від собаки
                s.scare_t = 0.6           # + 0.6 c посиленого переляку (вівця біжить швидше)
                s.state = "scared"

    def handle_event(self, event):
        # Обробка вводу під час гри
        if self.dialog.active:            # якщо показується діалог - керує ним
            self.dialog.handle_event(event)
            return
        if self.paused:                   # якщо пауза - керує меню паузи
            self._handle_pause_event(event)
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.paused = True        # Esc - поставити на паузу
                self.game.sound.play_sfx("ui_click")
            elif event.key == pygame.K_SPACE:
                self._bark()              # Space - гавкнути

    def _handle_pause_event(self, event):
        # Ввід у меню паузи (клавіші та миша).
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_p):
                self._pause_action("resume")      # Esc/P - продовжити
            elif event.key in (pygame.K_m, pygame.K_q):
                self._pause_action("menu")        # M/Q - у меню
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._pause_action(self.pause_buttons[self.pause_sel][0])  # Enter - обрана кнопка
            elif event.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_TAB):
                self.pause_sel = 1 - self.pause_sel   # перемкнути між 2 кнопками (0<->1)
        elif event.type == pygame.MOUSEMOTION:
            for i, (_, btn) in enumerate(self.pause_buttons):  # підсвітка під курсором
                if btn.hit(event.pos):
                    self.pause_sel = i
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for name, btn in self.pause_buttons:   # клік по кнопці
                if btn.hit(event.pos):
                    self._pause_action(name)

    def _pause_action(self, name):
        # Що робити за вибором у паузі.
        self.game.sound.play_sfx("ui_click")
        if name == "resume":
            self.paused = False           # зняти паузу (повертаємось у гру)
        else:
            self.game.change_scene("menu")

    def update(self, dt):
        # Головний такт гри - викликається щокадру. dt = час цього кадру.
        if self.dialog.active or self.ended or self.paused:
            return                        # під час діалогу/паузи/кінця гра "заморожена"

        self.bark_cd = max(0.0, self.bark_cd - dt)   # зменшуємо перезарядку гавкоту
        keys = pygame.key.get_pressed()   # які клавіші ЗАРАЗ зажаті (для руху собаки)

        # 1) Рухаємо всіх учасників
        self.dog.update(dt, keys, self.tilemap)                       # собака (за клавішами)
        newly = self.flock.update(dt, self.dog, self.wolves, self.tilemap, self.pen)  # отара
        for w in self.wolves:
            w.update(dt, self.flock, self.dog, self.tilemap)          # кожен вовк
        self.camera.follow(self.dog.pos)  # камера їде за собакою
        self.time_left = max(0.0, self.time_left - dt)  # зменшуємо таймер дня

        # 2) Подія: щойно загнали овець (flock.update повернув їх кількість)
        if newly:
            self.game.sound.play_sfx("sheep_penned")
            for _ in range(newly):
                self._log("SHEEP_PENNED", self.pen.rect.center)

        # 3) Подія: вівцю задрав вовк (порівнюємо з кількістю на минулому кадрі)
        penned, lost = self.flock.counts()
        if lost > self.prev_lost:
            for _ in range(lost - self.prev_lost):
                self._log("SHEEP_LOST", self.dog.pos)
            self.game.sound.play_sfx("sheep_lost")
            self.prev_lost = lost         # запам'ятовуємо нове значення

        # 4) Події зміни стану вовка (ловимо момент, коли стан змінився)
        for i, w in enumerate(self.wolves):
            if self.prev_states[i] != w.state:          # стан вовка щойно змінився
                if w.state == "stalk":                  # почав полювання
                    self._log("WOLF_SPOTTED", w.pos)
                    if not self.howled:                 # перша поява за день - виття
                        self.howled = True
                        self.game.sound.play_sfx("wolf_howl")
                    else:                               # далі - рик
                        self.game.sound.play_sfx("wolf_growl")
                elif w.state == "retreat" and w.pos.distance_to(self.dog.pos) < w.fear_radius + 12:
                    self._log("DOG_SCARED_WOLF", w.pos)  # собака відлякала вовка
                    self.wolf_scared += 1
                self.prev_states[i] = w.state           # оновлюємо "минулий стан"

        # 5) Фонове бекання овець час від часу
        self.baa_t -= dt
        if self.baa_t <= 0:
            self.baa_t = random.uniform(5.0, 11.0)      # наступне бекання через 5-11 c
            if any(not s.penned and not s.lost for s in self.flock.sheep):  # якщо є живі вівці
                self.game.sound.play_sfx("sheep_baa", 0.4)

        # 6) Перевірка умов завершення дня
        self._check_end(penned, lost)

    def _check_end(self, penned, lost):
        # Вирішує, чи день уже скінчився.
        total = self.cfg["sheep_total"]
        if lost > self.cfg["max_lost"]:                 # перевищено ліміт втрат - поразка
            return self._finish(False, penned, lost)
        if penned + lost >= total or self.time_left <= 0:  # поле порожнє або сів час
            return self._finish(penned >= self.cfg["required"], penned, lost)

    def _finish(self, completed, penned, lost):
        # Завершує день: рахує очки й передає підсумок у Game.on_day_end.
        if self.ended:                    # захист від подвійного виклику
            return
        self.ended = True
        self._log("DAY_END", self.dog.pos)
        time_taken = round(self.cfg["time"] - self.time_left, 1)   # скільки тривав день
        score = day_score(penned, lost, self.time_left, completed)  # очки за день
        if completed:
            self.game.sound.play_sfx("day_win")
        # Збираємо підсумок дня у словник і віддаємо головному об'єкту гри.
        self.game.on_day_end({
            "day": self.cfg["day"], "total": self.cfg["sheep_total"],
            "saved": penned, "lost": lost, "time_taken": time_taken,
            "score": score, "completed": completed, "events": self.events,
            "wolf_scared": self.wolf_scared,
        })

    def _draw_hud(self, surface):
        # Верхня панель з інформацією + шкала стаміни внизу.
        penned, lost = self.flock.counts()
        bar = pygame.Surface((C.SCREEN_W, 40), pygame.SRCALPHA)
        bar.fill((0, 0, 0, 120))          # напівпрозора темна смуга зверху
        surface.blit(bar, (0, 0))
        field = self.cfg["sheep_total"] - penned - lost   # скільки овець ще на полі
        # f-рядок: вставляємо значення змінних прямо в текст через {...}
        txt = (f"Day {self.cfg['day']}     Sunset {int(self.time_left)}s     "
               f"Penned {penned}/{self.cfg['required']}     On field {field}     Lost {lost}/{self.cfg['max_lost']}")
        surface.blit(self.font.render(txt, True, (240, 240, 235)), (14, 10))
        # Шкала стаміни: довжина заповнення = частка від максимуму.
        frac = self.dog.stamina / C.STAMINA_MAX           # 0..1
        pygame.draw.rect(surface, (40, 40, 40), (14, C.SCREEN_H - 30, 180, 16), border_radius=4)  # фон шкали
        col = (90, 190, 90) if frac > 0.3 else (210, 120, 60)  # зелена, якщо багато; помаранчева, якщо мало
        pygame.draw.rect(surface, col, (14, C.SCREEN_H - 30, int(180 * frac), 16), border_radius=4)  # заповнення
        surface.blit(self.font.render("Stamina", True, (230, 230, 230)), (14, C.SCREEN_H - 54))

    def draw(self, surface):
        surface.fill((20, 30, 20))        # заливаємо фон
        tm, cam, assets = self.tilemap, self.camera, self.game.assets  # короткі імена
        tm.draw_ground(surface, cam, assets)   # земля (трава, плями)
        self.pen.draw(surface, cam, assets)    # кошара (земля + паркан)

        # Y-СОРТУВАННЯ: збираємо перешкоди й усіх персонажів в один список,
        # сортуємо за "ногами" (нижньою точкою) - щоб те, що нижче, малювалось пізніше (спереду).
        drawables = [((cy + 1) * C.TILE, cx, cy, name) for cx, cy, name in tm.visible_obstacles(cam)]
        ents = [self.dog] + self.wolves + [s for s in self.flock.sheep if not s.lost]
        items = [(d[0], "obs", d) for d in drawables] + [(e.pos.y, "ent", e) for e in ents]
        items.sort(key=lambda it: it[0])  # сортуємо за першим числом (глибиною)
        for _, kind, data in items:
            if kind == "obs":
                tm.blit_obstacle(surface, cam, assets, data[1], data[2], data[3])  # дерево/камінь
            else:
                data.draw(surface, cam, assets)  # собака/вовк/вівця малюють себе самі

        self._draw_hud(surface)           # HUD поверх світу
        if self.dialog.active:            # діалог або пауза - найвищий шар
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
    # Сценка між днями: репліка господаря + підсумок дня + кнопка "Continue".
    def __init__(self, game, stats):
        super().__init__(game)
        self.stats = stats             # підсумок дня (словник з PlayScene._finish)
        self.t = 0.0
        self.title_font = make_title(40, bold=True)
        self.font = make_font(24)
        self.dialog = DialogBox(story.day_win(stats["day"]), self.game.sound)  # похвала за день
        self.cont = Button((C.SCREEN_W // 2 - 110, 500, 220, 52), "Continue")

    def update(self, dt):
        self.t += dt

    def handle_event(self, event):
        if self.dialog.active:
            self.dialog.handle_event(event)
            return
        # Enter/Space або клік по "Continue" -> наступний день
        if (event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE)) or \
           (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.cont.hit(event.pos)):
            self.game.sound.play_sfx("ui_click")
            self.game.continue_to_next_day()

    def draw(self, surface):
        for y in range(C.SCREEN_H):       # нічне небо градієнтом
            surface.fill(lerp_color((24, 28, 52), (60, 48, 60), y / C.SCREEN_H), (0, y, C.SCREEN_W, 1))
        pygame.draw.ellipse(surface, (250, 240, 210), (120, 60, 90, 90))   # місяць
        pygame.draw.rect(surface, (34, 44, 36), (0, 470, C.SCREEN_W, C.SCREEN_H - 470))  # земля
        pygame.draw.rect(surface, (110, 80, 50), (640, 360, 240, 120), border_radius=6)   # кошара (силует)
        pygame.draw.rect(surface, (150, 110, 70), (640, 360, 240, 120), 4, border_radius=6)  # її рамка

        title = self.title_font.render(f"Day {self.stats['day']} - safe in the pen", True, (250, 240, 220))
        surface.blit(title, title.get_rect(center=(C.SCREEN_W // 2, 110)))
        # Підсумок дня трьома рядками (беремо числа зі stats).
        lines = [f"Sheep saved: {self.stats['saved']} / {self.stats['total']}",
                 f"Lost to the wolf: {self.stats['lost']}",
                 f"Day score: {self.stats['score']}      Season total: {self.game.total_score}"]
        for i, ln in enumerate(lines):    # кожен рядок нижче попереднього (190 + i*36)
            t = self.font.render(ln, True, (235, 235, 225))
            surface.blit(t, t.get_rect(center=(C.SCREEN_W // 2, 190 + i * 36)))

        if self.dialog.active:            # спершу читаємо репліку, потім з'являється кнопка
            self.dialog.draw(surface)
        else:
            self.cont.draw(surface, True)


class GameoverScene(Scene):
    # Екран кінця сезону: перемога або поразка, рахунок, кінцівка, кнопки.
    def __init__(self, game, result):
        super().__init__(game)
        self.result = result               # "win" або "lose"
        self.game.finalize_session(result) # ЗАПИС підсумку сесії в БД
        if result == "win":
            self.game.sound.play_music("music_menu")
        else:
            self.game.sound.play_music("game_over", loop=False)  # звук поразки один раз
        self.title_font = make_title(64, bold=True)
        self.font = make_font(24)
        self.dialog = DialogBox(story.ending(game.lost_total), self.game.sound)  # кінцівка за втратами
        cx = C.SCREEN_W // 2
        self.buttons = [("records", Button((cx - 230, 520, 200, 50), "Records")),
                        ("menu", Button((cx + 30, 520, 200, 50), "Menu"))]
        self.selected = 0

    def handle_event(self, event):
        if self.dialog.active:            # спершу листаємо кінцівку
            self.dialog.handle_event(event)
            return
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_TAB):
                self.selected = 1 - self.selected   # перемкнути між 2 кнопками
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._activate(self.buttons[self.selected][0])  # активувати обрану кнопку
        elif event.type == pygame.MOUSEMOTION:       # підсвітка кнопки під курсором
            for idx, (_, btn) in enumerate(self.buttons):
                if btn.hit(event.pos):
                    self.selected = idx
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:  # клік
            for name, btn in self.buttons:
                if btn.hit(event.pos):
                    self._activate(name)

    def _activate(self, name):
        # Records -> таблиця рекордів; Menu -> головне меню.
        self.game.sound.play_sfx("ui_click")
        if name == "records":
            self.game.scene = RecordsScene(self.game)
        else:
            self.game.change_scene("menu")

    def draw(self, surface):
        win = self.result == "win"        # True для перемоги - змінює кольори й текст
        top = (34, 50, 70) if win else (54, 30, 30)  # синюватий фон / червонуватий
        for y in range(C.SCREEN_H):       # градієнтний фон
            surface.fill(lerp_color(top, (18, 20, 26), y / C.SCREEN_H), (0, y, C.SCREEN_W, 1))
        title = self.title_font.render("The flock is safe" if win else "A hard autumn",
                                        True, (250, 240, 210) if win else (240, 200, 190))
        surface.blit(title, title.get_rect(center=(C.SCREEN_W // 2, 120)))
        # Підсумки всього сезону (беремо з об'єкта Game, не з одного дня).
        lines = [f"Season score: {self.game.total_score}",
                 f"Sheep saved: {self.game.saved_total}      Lost: {self.game.lost_total}",
                 f"Days survived: {self.game.days_done} / {len(C.DAYS)}"]
        for i, ln in enumerate(lines):
            t = self.font.render(ln, True, (235, 235, 225))
            surface.blit(t, t.get_rect(center=(C.SCREEN_W // 2, 200 + i * 38)))
        if self.dialog.active:            # кінцівка, потім кнопки
            self.dialog.draw(surface)
        else:
            for idx, (_, btn) in enumerate(self.buttons):
                btn.draw(surface, idx == self.selected)


class RecordsScene(Scene):
    # Таблиця рекордів: читає дані з БД і показує топ сесій + статистику гравця.
    def __init__(self, game):
        super().__init__(game)
        self.rows = game.db.top_sessions(8)   # ЧИТАННЯ з БД: топ-8 завершених сесій
        # статистика гравця (або None, якщо гравця ще немає)
        self.stats = game.db.player_stats(game.player_id) if game.player_id else None
        self.title_font = make_title(48, bold=True)
        self.font = make_font(22)
        self.small = make_font(18)
        self.back = Button((C.SCREEN_W // 2 - 100, 560, 200, 46), "Back")

    def handle_event(self, event):
        # Esc/Enter або клік по "Back" -> у меню.
        if (event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN)) or \
           (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.back.hit(event.pos)):
            self.game.sound.play_sfx("ui_click")
            self.game.change_scene("menu")

    def draw(self, surface):
        for y in range(C.SCREEN_H):       # градієнтний фон
            surface.fill(lerp_color((30, 40, 60), (16, 20, 28), y / C.SCREEN_H), (0, y, C.SCREEN_W, 1))
        title = self.title_font.render("Records", True, (250, 240, 220))
        surface.blit(title, title.get_rect(center=(C.SCREEN_W // 2, 70)))

        # Заголовки колонок: пари (текст, x). Фіксовані x вирівнюють таблицю.
        cols = [("#", 180), ("Name", 240), ("Score", 470), ("Days", 600), ("Result", 700)]
        for name, x in cols:
            surface.blit(self.font.render(name, True, (210, 200, 140)), (x, 140))
        pygame.draw.line(surface, (120, 120, 130), (170, 170), (790, 170), 1)  # лінія під заголовками
        if not self.rows:                 # ще немає завершених ігор
            msg = self.font.render("No finished games yet - go herd some sheep!", True, (220, 220, 215))
            surface.blit(msg, msg.get_rect(center=(C.SCREEN_W // 2, 240)))
        for i, (nick, score, days, result, _) in enumerate(self.rows):  # рядок БД -> у змінні
            y = 185 + i * 34              # кожен запис нижче попереднього
            # значення по колонках (на тих самих x, що й заголовки)
            vals = [(str(i + 1), 180), (nick[:16], 240), (str(score), 470), (str(days), 600), (result or "-", 700)]
            for v, x in vals:
                surface.blit(self.font.render(v, True, (235, 235, 230)), (x, y))

        if self.stats:                    # особиста статистика гравця (якщо є)
            s = self.stats
            line = f"{self.game.last_name}:   best {s['best']}   -   games {s['games']}   -   total saved {s['saved']}"
            t = self.small.render(line, True, (200, 215, 200))
            surface.blit(t, t.get_rect(center=(C.SCREEN_W // 2, 500)))
        self.back.draw(surface, True)     # кнопка "Back" (завжди підсвічена)


class Game:
    # Головний об'єкт гри: вікно, головний цикл, поточна сцена, звук, БД, стан сезону.
    def __init__(self):
        pygame.init()
        try:
            # повноекранний режим зі збереженням логічного розміру 960x640
            self.screen = pygame.display.set_mode((C.SCREEN_W, C.SCREEN_H),
                                                  pygame.SCALED | pygame.FULLSCREEN)
        except pygame.error:
            self.screen = pygame.display.set_mode((C.SCREEN_W, C.SCREEN_H), pygame.SCALED)  # запасний варіант
        pygame.display.set_caption(C.TITLE)   # підпис вікна
        self.clock = pygame.time.Clock()      # годинник для обмеження FPS і вимірювання dt
        self.assets = AssetManager()          # менеджер картинок
        self.sound = SoundManager()           # менеджер звуку
        self.db = Database()                  # база даних
        self.running = True                   # прапорець роботи головного циклу

        # --- стан сезону (накопичується за весь забіг) ---
        self.last_name = ""                   # останнє введене ім'я
        self.player_id = None                 # id гравця в БД
        self.session_id = None                # id поточної сесії
        self.session_open = False             # чи сесія ще не завершена (щоб не записати двічі)
        self.day_index = 0                    # поточний день (0..4)
        self.saved_total = 0                  # усього врятовано за сезон
        self.lost_total = 0                   # усього втрачено
        self.total_score = 0                  # загальний рахунок
        self.days_done = 0                    # скільки днів зараховано
        self.wolf_scared_total = 0            # скільки разів відлякали вовка
        self.had_no_loss = False              # чи був день без втрат (для досягнення)
        self.had_fast_day = False             # чи був швидкий день (для досягнення)

        self.scene = None
        self.change_scene("menu")             # стартуємо з меню

    def change_scene(self, name):
        # Перемикання на просту сцену за назвою.
        if name == "menu":
            self.scene = MenuScene(self)
        elif name == "records":
            self.scene = RecordsScene(self)

    def start_new_game(self, name):
        # Почати новий сезон: створити гравця й сесію в БД, обнулити лічильники.
        name = (name or "").strip() or "Shepherd"   # прибрати пробіли; пусте -> "Shepherd"
        self.last_name = name
        self.player_id = self.db.get_or_create_player(name)                 # гравець у БД
        self.session_id = self.db.start_session(self.player_id, C.DEFAULT_DIFFICULTY)  # нова сесія
        self.session_open = True
        self.day_index = 0
        self.saved_total = self.lost_total = self.total_score = self.days_done = 0  # обнулення
        self.wolf_scared_total = 0
        self.had_no_loss = self.had_fast_day = False
        self.scene = PlayScene(self, 0)       # запускаємо перший день

    def on_day_end(self, stats):
        # Викликається з PlayScene, коли день скінчився. Записує день у БД і вирішує, що далі.
        day_id = self.db.insert_day_result(   # ЗАПИС підсумку дня в БД
            self.session_id, stats["day"], stats["total"], stats["saved"],
            stats["lost"], stats["time_taken"], stats["score"], 1 if stats["completed"] else 0)
        self.db.add_events(day_id, stats["events"])   # ЗАПИС подій дня в БД
        # накопичуємо сезонні підсумки
        self.saved_total += stats["saved"]
        self.lost_total += stats["lost"]
        self.total_score += stats["score"]
        self.wolf_scared_total += stats["wolf_scared"]
        if stats["completed"]:                # день зараховано
            self.days_done += 1
            if stats["lost"] == 0:
                self.had_no_loss = True        # день без втрат
            if stats["time_taken"] < 60:
                self.had_fast_day = True       # швидкий день
            if self.day_index >= len(C.DAYS) - 1:   # це був останній день
                self.scene = GameoverScene(self, "win")   # перемога сезону
            else:
                self.scene = InterludeScene(self, stats)  # сценка перед наступним днем
        else:
            self.scene = GameoverScene(self, "lose")      # день провалено -> поразка

    def continue_to_next_day(self):
        # Викликається з InterludeScene кнопкою Continue.
        self.day_index += 1
        self.scene = PlayScene(self, self.day_index)      # запускаємо наступний день

    def finalize_session(self, result):
        # Завершує сесію: пише результат у БД і видає досягнення. Один раз на сесію.
        if not self.session_open:             # вже завершено - виходимо (захист від подвійного запису)
            return
        self.session_open = False
        self.db.finish_session(self.session_id, result, self.total_score, self.days_done)  # фінал сесії
        self.db.update_best(self.player_id, self.total_score)   # оновити найкращий рахунок гравця
        # видача досягнень за умовами
        if result == "win":
            self.db.award(self.player_id, "SEASON_WIN")
        if self.had_no_loss:
            self.db.award(self.player_id, "NO_LOSS")
        if self.had_fast_day:
            self.db.award(self.player_id, "FAST_DAY")
        if self.wolf_scared_total >= 10:
            self.db.award(self.player_id, "WOLF_BRAVE")

    def run(self):
        # ГОЛОВНИЙ ЦИКЛ ГРИ: крутиться, поки running=True.
        while self.running:
            dt = self.clock.tick(C.FPS) / 1000.0   # чекаємо кадр, dt = час кадру в секундах
            if dt > 0.05:
                dt = 0.05                     # обмежуємо dt (якщо завис - щоб усе не "стрибнуло")
            for event in pygame.event.get():  # усі події вводу за цей кадр
                if event.type == pygame.QUIT:
                    self.running = False      # закрили вікно -> вихід
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                    pygame.display.toggle_fullscreen()   # F11 - вікно/повний екран
                else:
                    self.scene.handle_event(event)       # решту віддаємо поточній сцені
            self.scene.update(dt)             # оновлюємо логіку поточної сцени
            self.scene.draw(self.screen)      # малюємо поточну сцену
            pygame.display.flip()             # показуємо намальований кадр на екрані
        pygame.quit()                         # вихід: закриваємо pygame
        sys.exit()
