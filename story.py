# Кожна репліка - це пара (хто говорить, що говорить). Порожнє ім'я "" - ремарка без голосу.
GAME_TITLE = "SIRKO"
GAME_SUBTITLE = "A Shepherd's First Autumn"

# Пролог - показується один раз на початку першого дня.
PROLOGUE = [
    ("", "The Carpathian hills, the last warm week before winter."),
    ("Mykola", "Come here, pup. Sit with an old man a moment."),
    ("Mykola", "This flock is all your mistress and I have left. When the snow comes, their wool and milk carry us to spring."),
    ("Mykola", "Lose too many and the village takes back the high pasture. Then there's nothing left to come back to."),
    ("Mykola", "Up on the ridge lives the Grey One. Years ago he took my old dog, Buryan - the bravest friend I ever had."),
    ("Mykola", "You have his eyes, Sirko. You're his son. Maybe his courage too."),
    ("Mykola", "So earn your name, boy. Bring every sheep home, night after night, till the first snow."),
]

# Вступні репліки перед кожним днем. Словник: номер дня -> список реплік.
# День 1 = пролог + дві репліки.
DAY_INTRO = {
    1: PROLOGUE + [
        ("Mykola", "Easy now - just the near meadow tonight. Pen them before the sun sinks behind the firs."),
        ("Mykola", "Go on. Let me see your father in you."),
    ],
    2: [
        ("Mykola", "You slept by the gate all night, guarding them. Good lad."),
        ("Mykola", "The Grey One came down to the stream at dawn. He's testing you, Sirko."),
        ("Mykola", "More sheep on the slope today. Keep them close, and keep your eyes on the trees."),
    ],
    3: [
        ("Mykola", "The tax man rode through the valley. If the flock thins, he'll know."),
        ("Mykola", "Don't let a single ewe stray - a lone sheep is a gift to that old wolf."),
        ("Mykola", "I believe in you more than my own tired legs now."),
    ],
    4: [
        ("Mykola", "There are two shadows on the ridge. The Grey One hunts with a younger wolf now."),
        ("Mykola", "They'll split the flock to scatter it. Bark, circle, drive them together."),
        ("Mykola", "Buryan faced a whole pack once. You can face two."),
    ],
    5: [
        ("Mykola", "Smell that on the wind? First snow by nightfall. This is the last drive, Sirko."),
        ("Mykola", "Get them into the warm barn and the farm is saved - we winter through."),
        ("Mykola", "The Grey One knows it too. He'll come for everything tonight. Go, son. Finish what your father started."),
    ],
}

# Репліки після успішно пройденого дня (показуються на сценці біля кошари).
DAY_WIN = {
    1: [("Mykola", "Every one home on your first night. Buryan would be proud. I am.")],
    2: [("Mykola", "The flock already turns when you bark. You're learning their hearts.")],
    3: [("Mykola", "Halfway through the autumn, and the tax man has nothing to count against us.")],
    4: [("Mykola", "Two wolves, and you still brought them in. You're no pup anymore.")],
    5: [("Mykola", "Look - first snow, and the whole hillside safe behind you.")],
}

# Три варіанти кінцівки сезону - залежно від того, скільки овець втрачено всього.
ENDING_PERFECT = [   # ідеальна: жодної втрати
    ("", "First snow settles over a full, warm barn."),
    ("Mykola", "Not one sheep lost all season. In forty years on these hills, I never did that."),
    ("Mykola", "The pasture is ours for another year. The farm lives because of you."),
    ("Mykola", "You're not Buryan's son anymore, Sirko. You're Sirko. My shepherd."),
]
ENDING_GOOD = [      # добра: кілька втрат
    ("", "Snow falls soft on the ridge. The barn is loud with sheep."),
    ("Mykola", "We lost a few to the Grey One. But the flock is warm and the farm stands."),
    ("Mykola", "You held the line, lad. Rest now - winter is long, and you've earned it."),
]
ENDING_FAIL = [      # поразка: багато втрат
    ("", "The wind turns bitter. Half the pens stand empty."),
    ("Mykola", "The village will take the high pasture come spring. I can't fault you - the Grey One was always too much for one dog."),
    ("Mykola", "Don't hang your head, pup. Buryan lost his first winter too. The hills will test us again."),
]


# Віддає вступні репліки для дня (або запасну фразу, якщо дня немає в словнику).
def day_intro(day):
    return DAY_INTRO.get(day, [("Mykola", "Bring them home, Sirko.")])


# Віддає репліку після перемоги в дні.
def day_win(day):
    return DAY_WIN.get(day, [("Mykola", "Well done, lad.")])


# Обирає кінцівку за кількістю втрачених овець за весь сезон.
def ending(lost_total):
    if lost_total == 0:
        return ENDING_PERFECT
    if lost_total <= 4:
        return ENDING_GOOD
    return ENDING_FAIL
