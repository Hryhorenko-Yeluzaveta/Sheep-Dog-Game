import os
import sqlite3
from datetime import datetime

DDL = """
CREATE TABLE IF NOT EXISTS player (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nickname TEXT UNIQUE NOT NULL,
  created_at TEXT NOT NULL,
  best_score INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS difficulty (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  wolf_mult REAL NOT NULL,
  base_required INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS session (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  player_id INTEGER NOT NULL REFERENCES player(id),
  difficulty_id INTEGER REFERENCES difficulty(id),
  started_at TEXT NOT NULL,
  ended_at TEXT,
  result TEXT,
  total_score INTEGER DEFAULT 0,
  days_done INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS day_result (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id INTEGER NOT NULL REFERENCES session(id),
  day_number INTEGER NOT NULL,
  sheep_total INTEGER NOT NULL,
  sheep_saved INTEGER NOT NULL,
  sheep_lost INTEGER NOT NULL,
  time_taken REAL NOT NULL,
  score INTEGER NOT NULL,
  completed INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS event_type (
  id INTEGER PRIMARY KEY,
  code TEXT UNIQUE NOT NULL,
  description TEXT
);
CREATE TABLE IF NOT EXISTS event (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  day_id INTEGER NOT NULL REFERENCES day_result(id),
  type_id INTEGER NOT NULL REFERENCES event_type(id),
  t REAL NOT NULL,
  x INTEGER,
  y INTEGER
);
CREATE TABLE IF NOT EXISTS achievement (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT
);
CREATE TABLE IF NOT EXISTS player_achievement (
  player_id INTEGER NOT NULL REFERENCES player(id),
  achievement_id INTEGER NOT NULL REFERENCES achievement(id),
  earned_at TEXT NOT NULL,
  PRIMARY KEY (player_id, achievement_id)
);
"""

EVENT_TYPES = [
    (1, "SHEEP_PENNED", "Sheep entered the pen"),
    (2, "SHEEP_LOST", "Sheep taken by the wolf"),
    (3, "WOLF_SPOTTED", "Wolf started hunting"),
    (4, "DOG_SCARED_WOLF", "Dog scared the wolf away"),
    (5, "DAY_START", "Day started"),
    (6, "DAY_END", "Day ended"),
]

DIFFICULTIES = [
    (1, "Easy", 0.8, 4),
    (2, "Normal", 1.0, 5),
    (3, "Hard", 1.3, 6),
]

ACHIEVEMENTS = {
    "NO_LOSS": (1, "Spotless", "Finish a day without losing a sheep"),
    "FAST_DAY": (2, "Quick Herder", "Finish a day in under 60 seconds"),
    "SEASON_WIN": (3, "Survivor", "Survive the whole season"),
    "WOLF_BRAVE": (4, "Wolfsbane", "Scare the wolf away 10 times"),
}


class Database:
    def __init__(self, path=None):
        if path is None:
            base = os.path.dirname(os.path.abspath(__file__))
            path = os.path.join(base, "data", "sirko.db")
        d = os.path.dirname(path)
        if d:
            os.makedirs(d, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(DDL)
        self._seed()
        self.event_type_ids = {code: tid for tid, code, _ in EVENT_TYPES}

    def _seed(self):
        c = self.conn
        c.executemany("INSERT OR IGNORE INTO event_type(id, code, description) VALUES (?,?,?)", EVENT_TYPES)
        c.executemany("INSERT OR IGNORE INTO difficulty(id, name, wolf_mult, base_required) VALUES (?,?,?,?)", DIFFICULTIES)
        c.executemany("INSERT OR IGNORE INTO achievement(id, name, description) VALUES (?,?,?)",
                      [(aid, name, desc) for aid, name, desc in ACHIEVEMENTS.values()])
        c.commit()

    def _now(self):
        return datetime.now().isoformat(timespec="seconds")

    def get_or_create_player(self, nickname):
        c = self.conn
        c.execute("INSERT OR IGNORE INTO player(nickname, created_at) VALUES (?,?)", (nickname, self._now()))
        c.commit()
        row = c.execute("SELECT id FROM player WHERE nickname = ?", (nickname,)).fetchone()
        return row[0]

    def start_session(self, player_id, difficulty_id):
        cur = self.conn.execute(
            "INSERT INTO session(player_id, difficulty_id, started_at) VALUES (?,?,?)",
            (player_id, difficulty_id, self._now()))
        self.conn.commit()
        return cur.lastrowid

    def insert_day_result(self, session_id, day_number, total, saved, lost, time_taken, score, completed):
        cur = self.conn.execute(
            "INSERT INTO day_result(session_id, day_number, sheep_total, sheep_saved, sheep_lost, time_taken, score, completed) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (session_id, day_number, total, saved, lost, time_taken, score, completed))
        self.conn.commit()
        return cur.lastrowid

    def add_events(self, day_id, events):
        rows = []
        for code, t, x, y in events:
            tid = self.event_type_ids.get(code)
            if tid:
                rows.append((day_id, tid, t, x, y))
        if rows:
            self.conn.executemany("INSERT INTO event(day_id, type_id, t, x, y) VALUES (?,?,?,?,?)", rows)
            self.conn.commit()

    def finish_session(self, session_id, result, total_score, days_done):
        self.conn.execute(
            "UPDATE session SET ended_at=?, result=?, total_score=?, days_done=? WHERE id=?",
            (self._now(), result, total_score, days_done, session_id))
        self.conn.commit()

    def update_best(self, player_id, score):
        self.conn.execute("UPDATE player SET best_score=? WHERE id=? AND best_score < ?",
                          (score, player_id, score))
        self.conn.commit()

    def award(self, player_id, code):
        ach = ACHIEVEMENTS.get(code)
        if not ach:
            return
        self.conn.execute(
            "INSERT OR IGNORE INTO player_achievement(player_id, achievement_id, earned_at) VALUES (?,?,?)",
            (player_id, ach[0], self._now()))
        self.conn.commit()

    def top_sessions(self, limit=8):
        return self.conn.execute(
            "SELECT p.nickname, s.total_score, s.days_done, s.result, s.ended_at "
            "FROM session s JOIN player p ON p.id = s.player_id "
            "WHERE s.ended_at IS NOT NULL "
            "ORDER BY s.total_score DESC, s.ended_at DESC LIMIT ?", (limit,)).fetchall()

    def player_stats(self, player_id):
        best = self.conn.execute("SELECT best_score FROM player WHERE id=?", (player_id,)).fetchone()
        games = self.conn.execute("SELECT COUNT(*) FROM session WHERE player_id=? AND ended_at IS NOT NULL",
                                  (player_id,)).fetchone()
        saved = self.conn.execute(
            "SELECT COALESCE(SUM(d.sheep_saved),0) FROM day_result d "
            "JOIN session s ON s.id = d.session_id WHERE s.player_id=?", (player_id,)).fetchone()
        return {"best": best[0] if best else 0, "games": games[0], "saved": saved[0]}
