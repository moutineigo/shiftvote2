"""
Shift Vote 2 API (Flask, SQLite)
Replacement for the old Google Apps Script + Spreadsheet backend.
Deployed as Sakura CGI, called cross-origin from GitHub Pages.

Endpoints (all GET with query params, to stay CORS-preflight-free):
  ?action=meta&month=YYYY-MM
  ?action=all&month=YYYY-MM        (meta + responses + comments in one call)
  ?action=responses&month=YYYY-MM
  ?action=set&month_key=&member_id=&date=&value=
  ?action=setmemberlock&member_id=&locked=true|false&month_key=
  ?action=setcomment&month_key=&member_id=&comment=
"""
import os
import sqlite3
from datetime import datetime, timezone
from flask import Flask, request, jsonify

app = Flask(__name__)

DATA_DIR = os.environ.get(
    'SHIFTVOTE_DATA_DIR',
    os.path.abspath(os.path.join(os.path.dirname(__file__), 'local-data')),
)
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, 'shiftvote.db')

DEFAULT_CHOICES = ['ー', '〇', '×', '△', '？']

# CORS: GitHub Pages prod + local Vite dev servers
ALLOWED_ORIGINS = {
    'https://moutineigo.github.io',
    'http://localhost:5173',
    'http://127.0.0.1:5173',
    'http://localhost:4173',
    'http://127.0.0.1:4173',
}


@app.after_request
def add_cors_headers(resp):
    origin = request.headers.get('Origin')
    if origin in ALLOWED_ORIGINS:
        resp.headers['Access-Control-Allow-Origin'] = origin
        resp.headers['Vary'] = 'Origin'
    return resp


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    return conn


def init_db():
    conn = get_db()
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
    conn.commit()
    conn.close()


init_db()


def now_iso():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def parse_choices(s):
    s = (s or '').strip()
    if not s:
        return list(DEFAULT_CHOICES)
    return [x.strip() for x in s.split(',') if x.strip()]


def get_config(conn):
    row = conn.execute('SELECT * FROM config WHERE id = 1').fetchone()
    if not row:
        return {}
    return dict(row)


def get_meta(conn, month_key):
    cfg = get_config(conn)
    active_month = str(cfg.get('month_key') or '')
    month = month_key if month_key else active_month
    if not month:
        raise ValueError('month is required (query month=YYYY-MM or config.month_key)')

    choices = parse_choices(cfg.get('choices'))

    members = [
        {
            'member_id': r['member_id'],
            'member_name': r['member_name'],
            'locked': bool(r['locked']),
        }
        for r in conn.execute(
            'SELECT * FROM members WHERE active = 1 ORDER BY sort ASC'
        ).fetchall()
    ]

    dates = [
        {
            'date': r['date'],
            'weekday': r['weekday'],
            'time': r['time'],
            'place': r['place'],
            'note': r['note'],
        }
        for r in conn.execute(
            'SELECT * FROM dates WHERE month_key = ? AND active = 1 '
            'ORDER BY (sort IS NULL), sort ASC, date ASC',
            (month,),
        ).fetchall()
    ]

    return {
        'ok': True,
        'month_key': month,
        'title': cfg.get('title') or '',
        'deadline': cfg.get('deadline') or '',
        'note': cfg.get('note') or '',
        'ui_refresh_sec': cfg.get('ui_refresh_sec') or 0,
        'choices': choices,
        'members': members,
        'dates': dates,
    }


def get_responses(conn, month_key):
    if not month_key:
        return {'ok': True, 'month_key': '', 'responses': []}
    rows = conn.execute(
        'SELECT member_id, date, value, updated_at FROM responses WHERE month_key = ?',
        (month_key,),
    ).fetchall()
    return {
        'ok': True,
        'month_key': month_key,
        'responses': [dict(r) for r in rows],
    }


def get_comments(conn, month_key):
    if not month_key:
        return []
    rows = conn.execute(
        'SELECT month_key, member_id, comment, updated_at FROM comments WHERE month_key = ?',
        (month_key,),
    ).fetchall()
    return [dict(r) for r in rows]


def set_response(conn, p):
    month_key = str(p.get('month_key') or '').strip()
    member_id = str(p.get('member_id') or '').strip()
    date = str(p.get('date') or '').strip()
    value = str(p.get('value') or '').strip()

    if not month_key or not member_id or not date:
        return {'ok': False, 'error': 'missing fields: month_key, member_id, date are required'}

    cfg = get_config(conn)
    allowed = set(parse_choices(cfg.get('choices')) or DEFAULT_CHOICES)
    v = value if value else 'ー'
    if v not in allowed:
        return {'ok': False, 'error': f'value not allowed: {v}'}

    date_row = conn.execute(
        'SELECT 1 FROM dates WHERE month_key = ? AND date = ? AND active = 1',
        (month_key, date),
    ).fetchone()
    if not date_row:
        return {'ok': False, 'error': f'date not in dates table for month={month_key}: {date}'}

    member_row = conn.execute(
        'SELECT 1 FROM members WHERE member_id = ? AND active = 1', (member_id,)
    ).fetchone()
    if not member_row:
        return {'ok': False, 'error': f'member_id not in members table (active only): {member_id}'}

    now = now_iso()
    conn.execute(
        """
        INSERT INTO responses (month_key, member_id, date, value, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT (month_key, member_id, date)
        DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
        """,
        (month_key, member_id, date, v, now),
    )
    conn.commit()
    return {'ok': True}


def set_member_lock(conn, p):
    member_id = str(p.get('member_id') or '').strip()
    locked_str = str(p.get('locked') or '').strip().lower()
    if not member_id:
        return {'ok': False, 'error': 'member_id required'}
    if locked_str not in ('true', 'false'):
        return {'ok': False, 'error': 'locked must be true/false'}
    locked = 1 if locked_str == 'true' else 0

    cur = conn.execute(
        'UPDATE members SET locked = ? WHERE member_id = ?', (locked, member_id)
    )
    if cur.rowcount == 0:
        return {'ok': False, 'error': f'member_id not found: {member_id}'}
    conn.commit()
    return {'ok': True}


def set_comment(conn, p):
    month_key = str(p.get('month_key') or '').strip()
    member_id = str(p.get('member_id') or '').strip()
    comment = str(p.get('comment') or '')
    if not month_key or not member_id:
        return {'ok': False, 'error': 'missing fields: month_key, member_id are required'}
    if len(comment) > 1000:
        comment = comment[:1000]

    now = now_iso()
    conn.execute(
        """
        INSERT INTO comments (month_key, member_id, comment, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT (month_key, member_id)
        DO UPDATE SET comment = excluded.comment, updated_at = excluded.updated_at
        """,
        (month_key, member_id, comment, now),
    )
    conn.commit()
    return {'ok': True}


@app.route('/', methods=['GET', 'OPTIONS'])
def index():
    if request.method == 'OPTIONS':
        return ('', 204)

    action = (request.args.get('action') or '').lower().strip()
    month = (request.args.get('month') or '').strip()

    conn = get_db()
    try:
        if action == 'meta':
            return jsonify(get_meta(conn, month))

        if action == 'all':
            meta = get_meta(conn, month)
            mk = meta.get('month_key') or month
            resp = get_responses(conn, mk)
            comments = get_comments(conn, mk)
            return jsonify({
                'ok': True,
                'meta': meta,
                'responses': resp.get('responses', []),
                'comments': comments,
            })

        if action == 'responses':
            return jsonify(get_responses(conn, month))

        if action == 'set':
            payload = {
                'month_key': request.args.get('month_key', ''),
                'member_id': request.args.get('member_id', ''),
                'date': request.args.get('date', ''),
                'value': request.args.get('value', ''),
            }
            return jsonify(set_response(conn, payload))

        if action == 'setmemberlock':
            payload = {
                'month_key': request.args.get('month_key', ''),
                'member_id': request.args.get('member_id', ''),
                'locked': request.args.get('locked', ''),
            }
            return jsonify(set_member_lock(conn, payload))

        if action == 'setcomment':
            payload = {
                'month_key': request.args.get('month_key', ''),
                'member_id': request.args.get('member_id', ''),
                'comment': request.args.get('comment', ''),
            }
            return jsonify(set_comment(conn, payload))

        return jsonify({'ok': False, 'error': 'unknown action'}), 400
    except Exception as err:  # noqa: BLE001 - surface any error as JSON, mirrors old GAS behavior
        return jsonify({'ok': False, 'error': str(err)}), 500
    finally:
        conn.close()


if __name__ == '__main__':
    app.run(port=5177, debug=True)
