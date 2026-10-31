TILE = 32
SCREEN_W = 960
SCREEN_H = 640
FPS = 60

TITLE = "Sirko"

COLORS = {
    "grass": (76, 110, 70),
    "dog": (70, 110, 200),
    "sheep": (240, 240, 235),
    "sheep_scared": (240, 240, 235),
    "wolf": (150, 50, 50),
    "pen": (140, 100, 60),
    "gate": (190, 150, 90),
    "tree": (40, 70, 40),
    "fence": (110, 80, 50),
    "water": (60, 120, 170),
}

R_SEP = 24
R_NEI = 64
R_DOG = 140
R_WOLF = 180

W_SEP = 1.6
W_ALI = 1.0
W_COH = 0.9
W_DOG = 2.2
W_WOLF = 3.0
W_OBS = 2.0

SHEEP_SPEED = 70
PANIC_MULT = 1.8

DEFAULT_DIFFICULTY = 2

DOG_SPEED = 150
DOG_SPRINT = 240
STAMINA_MAX = 100.0
STAMINA_DRAIN = 35.0
STAMINA_REGEN = 20.0

DAYS = [
    {"day": 1, "world": (34, 22), "sheep_total": 5,  "required": 4,  "max_lost": 1, "time": 60, "wolves": 1, "wolf_speed": 72, "vision": 210},
    {"day": 2, "world": (38, 24), "sheep_total": 7,  "required": 6,  "max_lost": 1, "time": 60, "wolves": 1, "wolf_speed": 80, "vision": 240},
    {"day": 3, "world": (42, 28), "sheep_total": 9,  "required": 7,  "max_lost": 2, "time": 65, "wolves": 1, "wolf_speed": 88, "vision": 270},
    {"day": 4, "world": (46, 30), "sheep_total": 11, "required": 8,  "max_lost": 3, "time": 70, "wolves": 2, "wolf_speed": 94, "vision": 300},
    {"day": 5, "world": (50, 34), "sheep_total": 13, "required": 10, "max_lost": 3, "time": 75, "wolves": 2, "wolf_speed": 102, "vision": 330},
]
