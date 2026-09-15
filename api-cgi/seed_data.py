"""
Monthly setup script for shiftvote2.

Edit MONTH_KEY / TITLE / DEADLINE / DATES below for each new month, then run:
  - locally (against local-data/shiftvote.db, for testing):
      python seed_data.py
  - on the server (against production data), via SSH:
      SHIFTVOTE_DATA_DIR=/home/eigo55/shiftvote2-data ~/venv/bin/python seed_data.py

This only touches config/members/dates — existing responses/comments are
never deleted, so re-running it (e.g. to fix a typo in a date's place) is
always safe. To add a member, add a row to MEMBERS and re-run; to retire one,
set active=0 instead of deleting the row (keeps their historical responses
meaningful).
"""
import os
import sqlite3

DATA_DIR = os.environ.get(
    'SHIFTVOTE_DATA_DIR',
    os.path.abspath(os.path.join(os.path.dirname(__file__), 'local-data')),
)
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, 'shiftvote.db')

MONTH_KEY = '2026-10'
TITLE = f'{MONTH_KEY}のシフト'
DEADLINE = '2026-09-30'
CHOICES = 'ー,〇,×,△,？'
NOTE = f'{MONTH_KEY.replace("-", "")}シフト表'
UI_REFRESH_SEC = 60

# member_id, member_name, sort (active always 1; edit the DB directly, or
# add a retire step here, if someone needs to be deactivated)
MEMBERS = [
    ('21', '鴨藤', 1),
    ('22', '間渕', 2),
    ('23', '丹生', 3),
    ('24', '米山', 4),
    ('25', '大竹', 5),
    ('26', '松井', 6),
    ('27', '植平', 7),
    ('28', '永田', 8),
    ('29', '牧野', 9),
    ('30', '粟倉', 10),
    ('31', '宏和', 11),
    ('32', '斎藤', 12),
    ('33', '櫻谷', 13),
    ('34', '加藤', 14),
    ('35', '野中', 15),
    ('36', '山崎', 16),
    ('38', '太田', 18),
    ('41', '田中', 20),
    ('43', '慎一', 21),
]

# date, weekday, time, place, note
DATES = [
    ('2026-10-02', '金', '18:45-21:00', '磐田南部中学', ''),
    ('2026-10-03', '土', '8:30-12:00', '兎山球場', '練習試合(御前崎BBC)'),
    ('2026-10-04', '日', '13:00-17:00', '兎山球場（仮）', ''),
    ('2026-10-05', '月', '18:45-21:00', '磐田南部中学', ''),
    ('2026-10-07', '水', '18:45-21:00', '城山中学', ''),
    ('2026-10-09', '金', '18:45-21:00', '磐田南部中学', ''),
    ('2026-10-10', '土', '8:30-12:00', '兎山球場', '練習試合(細江中学)'),
    ('2026-10-11', '日', '8:30-12:00', '兎山球場', '体験会'),
    ('2026-10-12', '月', '8:30-17:00', '豊田球場', '南側駐車場使用不可'),
    ('2026-10-14', '水', '18:45-21:00', '城山中学', ''),
    ('2026-10-16', '金', '18:45-21:00', '磐田南部中学', ''),
    ('2026-10-17', '土', '8:30-12:00', '兎山球場', '練習試合(丸塚/中部中学)'),
    ('2026-10-18', '日', '13:00-17:00', '豊田球場', ''),
    ('2026-10-19', '月', '18:45-21:00', '磐田南部中学', ''),
    ('2026-10-21', '水', '18:45-21:00', '城山中学', ''),
    ('2026-10-23', '金', '18:45-21:00', '磐田南部中学', ''),
    ('2026-10-24', '土', '8:30-12:00', '兎山球場', '体験会'),
    ('2026-10-25', '日', '8:30-12:00', '入野中学校', '練習試合(レイカーズ)'),
    ('2026-10-26', '月', '18:45-21:00', '磐田南部中学', ''),
    ('2026-10-28', '水', '18:45-21:00', '城山中学', ''),
    ('2026-10-30', '金', '18:45-21:00', '磐田南部中学', ''),
    ('2026-10-31', '土', '', '中学クラブ秋季大会', ''),
]


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS config (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            month_key TEXT NOT NULL,
            title TEXT NOT NULL DEFAULT '',
            deadline TEXT NOT NULL DEFAULT '',
            choices TEXT NOT NULL DEFAULT 'ー,〇,×,△,？',
            active INTEGER NOT NULL DEFAULT 1,
            note TEXT NOT NULL DEFAULT '',
            ui_refresh_sec INTEGER NOT NULL DEFAULT 60
        );
        CREATE TABLE IF NOT EXISTS members (
            member_id TEXT PRIMARY KEY,
            member_name TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            sort INTEGER NOT NULL DEFAULT 0,
            locked INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS dates (
            month_key TEXT NOT NULL,
            date TEXT NOT NULL,
            weekday TEXT NOT NULL DEFAULT '',
            time TEXT NOT NULL DEFAULT '',
            place TEXT NOT NULL DEFAULT '',
            note TEXT NOT NULL DEFAULT '',
            active INTEGER NOT NULL DEFAULT 1,
            sort INTEGER,
            PRIMARY KEY (month_key, date)
        );
        CREATE TABLE IF NOT EXISTS responses (
            month_key TEXT NOT NULL,
            member_id TEXT NOT NULL,
            date TEXT NOT NULL,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (month_key, member_id, date)
        );
        CREATE TABLE IF NOT EXISTS comments (
            month_key TEXT NOT NULL,
            member_id TEXT NOT NULL,
            comment TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL,
            PRIMARY KEY (month_key, member_id)
        );
        """
    )

    conn.execute(
        """
        INSERT INTO config (id, month_key, title, deadline, choices, active, note, ui_refresh_sec)
        VALUES (1, ?, ?, ?, ?, 1, ?, ?)
        ON CONFLICT (id) DO UPDATE SET
            month_key = excluded.month_key,
            title = excluded.title,
            deadline = excluded.deadline,
            choices = excluded.choices,
            active = 1,
            note = excluded.note,
            ui_refresh_sec = excluded.ui_refresh_sec
        """,
        (MONTH_KEY, TITLE, DEADLINE, CHOICES, NOTE, UI_REFRESH_SEC),
    )

    for member_id, member_name, sort in MEMBERS:
        conn.execute(
            """
            INSERT INTO members (member_id, member_name, active, sort, locked)
            VALUES (?, ?, 1, ?, 0)
            ON CONFLICT (member_id) DO UPDATE SET
                member_name = excluded.member_name,
                active = 1,
                sort = excluded.sort
            """,
            (member_id, member_name, sort),
        )

    for date, weekday, time, place, note in DATES:
        conn.execute(
            """
            INSERT INTO dates (month_key, date, weekday, time, place, note, active)
            VALUES (?, ?, ?, ?, ?, ?, 1)
            ON CONFLICT (month_key, date) DO UPDATE SET
                weekday = excluded.weekday,
                time = excluded.time,
                place = excluded.place,
                note = excluded.note,
                active = 1
            """,
            (MONTH_KEY, date, weekday, time, place, note),
        )

    conn.commit()
    conn.close()
    print(f'Seeded {MONTH_KEY}: {len(MEMBERS)} members, {len(DATES)} dates. DB: {DB_PATH}')


if __name__ == '__main__':
    main()
