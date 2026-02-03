"""
Quiz Web Application - Flask Backend
A complete quiz platform with authentication, timer, and tab switching detection.
Uses MySQL for user auth (credentials + one-attempt gate) and SQLite for local
session tracking and result logging.
"""

from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from datetime import datetime, timedelta
from functools import wraps
import secrets
import sqlite3
import json
import os
import random

import pymysql                                  # pure-Python MySQL driver (handles caching_sha2_password)

from config import MYSQL_CONFIG                 # single source of truth for MySQL creds

# ==========================================================================
# App bootstrap
# ==========================================================================
app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)

# ==========================================================================
# SQLite — local session / result tracking
# ==========================================================================
def init_db():
    """Create SQLite tables if they don't exist."""
    conn = sqlite3.connect('quiz_app.db')
    cur  = conn.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT NOT NULL,
            password      TEXT NOT NULL,
            class_level   TEXT NOT NULL,
            stream        TEXT NOT NULL,
            assigned_set  TEXT NOT NULL,
            login_time    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS test_results (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER,
            username        TEXT NOT NULL,
            class_level     TEXT NOT NULL,
            stream          TEXT NOT NULL,
            assigned_set    TEXT NOT NULL,
            score           INTEGER NOT NULL,
            total_questions INTEGER NOT NULL,
            tab_switches    INTEGER DEFAULT 0,
            submission_type TEXT,
            test_date       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS set_counter (
            id                INTEGER PRIMARY KEY,
            class_level       TEXT NOT NULL,
            stream            TEXT NOT NULL,
            current_set_index INTEGER DEFAULT 0,
            UNIQUE(class_level, stream)
        )
    ''')

    conn.commit()
    conn.close()

init_db()

# ==========================================================================
# MySQL connection helper
# ==========================================================================
def get_mysql_connection():
    """Return a PyMySQL connection.  Credentials come from config.py."""
    return pymysql.connect(
        host=MYSQL_CONFIG['host'],
        user=MYSQL_CONFIG['user'],
        password=MYSQL_CONFIG['password'],
        database=MYSQL_CONFIG['database'],
        charset=MYSQL_CONFIG.get('charset', 'utf8mb4'),
        cursorclass=pymysql.cursors.DictCursor   # rows come back as dicts
    )

# ==========================================================================
# Round-robin question-set assignment (SQLite)
# ==========================================================================
def get_next_set(class_level, stream):
    """Return 'a', 'b', 'c', or 'd' via round-robin across logins."""
    sets = ['a', 'b', 'c', 'd']

    conn = sqlite3.connect('quiz_app.db')
    cur  = conn.cursor()

    # seed row if this class+stream pair has never been seen
    cur.execute('''
        INSERT OR IGNORE INTO set_counter (class_level, stream, current_set_index)
        VALUES (?, ?, 0)
    ''', (class_level, stream))

    cur.execute('''
        SELECT current_set_index FROM set_counter
        WHERE  class_level = ? AND stream = ?
    ''', (class_level, stream))

    row           = cur.fetchone()
    current_index = row[0] if row else 0
    assigned_set  = sets[current_index % len(sets)]

    # bump counter for the next login
    cur.execute('''
        UPDATE set_counter SET current_set_index = ?
        WHERE  class_level = ? AND stream = ?
    ''', ((current_index + 1) % len(sets), class_level, stream))

    conn.commit()
    conn.close()
    return assigned_set

# ==========================================================================
# Question loader  — tries set-specific file first, falls back to shared file
# ==========================================================================
def load_questions(class_level, stream, set_name):
    """
    Attempt to load questions in this priority order:
      1. data/questions_{class}_{stream}_{set}.json   (per-set file)
      2. data/questions_{class}_{stream}.json         (shared file)
    Returns a list of question dicts, or [] if nothing found.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # priority 1 – set-specific file  (e.g. questions_class9_general_a.json)
    set_path = os.path.join(base_dir, f'data/questions_{class_level}_{stream}_{set_name}.json')
    if os.path.exists(set_path):
        with open(set_path, 'r', encoding='utf-8') as fh:
            return json.load(fh)

    # priority 2 – shared file  (e.g. questions_class9_general.json)
    shared_path = os.path.join(base_dir, f'data/questions_{class_level}_{stream}.json')
    if os.path.exists(shared_path):
        with open(shared_path, 'r', encoding='utf-8') as fh:
            return json.load(fh)

    print(f'[WARN] No question file found.  Tried:\n'
          f'       {set_path}\n'
          f'       {shared_path}')
    return []

# ==========================================================================
# Auth decorator
# ==========================================================================
def login_required(f):
    """Redirect to /login if no active session."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper

# ==========================================================================
# Scholarship calculator
# ==========================================================================
def calculate_scholarship(percentage):
    """Return (scholarship_percent, message) tuple."""
    if percentage >= 90:
        return 100, "Full Scholarship - Congratulations!"
    elif percentage >= 75:
        return 50, "Half Scholarship - Well Done!"
    elif percentage >= 60:
        return 25, "Quarter Scholarship - Good Effort!"
    else:
        return 0, "No Scholarship - Keep Trying!"

# ==========================================================================
# Routes
# ==========================================================================

# --------------------------------------------------------------------------
# INDEX  –  smart redirect depending on session state
# --------------------------------------------------------------------------
@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))

    # test already done -> show score
    if 'test_completed' in session:
        return redirect(url_for('score'))

    # test in progress -> resume
    class_level = session.get('class_level')
    stream      = session.get('stream')
    if class_level in ('class9', 'class10'):
        return redirect(url_for('test_page', class_level=class_level))
    return redirect(url_for('test_page', class_level=class_level, stream=stream))

# --------------------------------------------------------------------------
# LOGIN
# --------------------------------------------------------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    GET  – render login form.
    POST – authenticate against MySQL, validate class/stream, start session.
    """
    if request.method == 'POST':
        username    = request.form.get('username', '').strip()
        password    = request.form.get('password', '').strip()
        class_level = request.form.get('class_level', '').strip()
        stream      = request.form.get('stream', '').strip()

        # ── presence check ────────────────────────────────────────────────
        if not all([username, password, class_level]):
            return render_template('login.html',
                                   error="Username, password, and class are required")

        # ── MySQL authentication (plain text password) ────────────────────
        try:
            conn = get_mysql_connection()
            cur  = conn.cursor()

            cur.execute("""
                SELECT id, full_name, username, password, has_attempted_test
                FROM   users
                WHERE  username = %s
            """, (username,))

            user = cur.fetchone()   # dict or None

            if not user:
                cur.close(); conn.close()
                return render_template('login.html',
                                       error="Invalid username or password")

            # Direct password comparison (plain text)
            if user['password'] != password:
                cur.close(); conn.close()
                return render_template('login.html',
                                       error="Invalid username or password")

            if user['has_attempted_test']:
                cur.close(); conn.close()
                return render_template('login.html',
                                       error="You have already attempted the test. "
                                             "Contact the administrator if this is a mistake.")

            cur.close()
            conn.close()

        except pymysql.err.OperationalError as err:
            return render_template('login.html',
                                   error=f"Database connection error: {err}")
        except Exception as err:
            return render_template('login.html',
                                   error=f"Database error: {err}")
        # ── end MySQL auth ────────────────────────────────────────────────

        # ── class / stream validation ─────────────────────────────────────
        valid_classes = ('class9', 'class10', 'class11', 'class12', 'dropper')
        if class_level not in valid_classes:
            return render_template('login.html', error="Invalid class selection")

        if class_level in ('class11', 'class12', 'dropper'):
            if stream not in ('jee', 'neet'):
                return render_template('login.html',
                                       error="Please select a stream (JEE / NEET)")
        else:
            stream = 'general'          # class 9 / 10 have no stream

        # ── assign question set ───────────────────────────────────────────
        assigned_set = get_next_set(class_level, stream)

        # ── log session in SQLite (store plain password) ──────────────────
        conn = sqlite3.connect('quiz_app.db')
        cur  = conn.cursor()
        cur.execute('''
            INSERT INTO users (username, password, class_level, stream, assigned_set)
            VALUES (?, ?, ?, ?, ?)
        ''', (username, password, class_level, stream, assigned_set))
        sqlite_user_id = cur.lastrowid
        conn.commit()
        conn.close()

        # ── populate Flask session ────────────────────────────────────────
        session.permanent        = True
        session['username']      = user['full_name']       # human-readable name for UI
        session['user_id']       = sqlite_user_id          # SQLite PK
        session['mysql_user_id'] = user['id']              # MySQL PK – used for the UPDATE later
        session['class_level']   = class_level
        session['stream']        = stream
        session['assigned_set']  = assigned_set
        session['tab_switches']  = 0
        session['test_start_time'] = datetime.now().isoformat()

        # ── redirect to test ──────────────────────────────────────────────
        if class_level in ('class9', 'class10'):
            return redirect(url_for('test_page', class_level=class_level))
        return redirect(url_for('test_page', class_level=class_level, stream=stream))

    # GET
    return render_template('login.html')

# --------------------------------------------------------------------------
# TEST PAGE
# --------------------------------------------------------------------------
@app.route('/test/<class_level>')
@app.route('/test/<class_level>/<stream>')
@login_required
def test_page(class_level=None, stream=None):
    """Render the test.  Re-checks has_attempted_test on every page-load."""

    # ── guard: already attempted? (survives session replay) ───────────────
    try:
        conn = get_mysql_connection()
        cur  = conn.cursor()
        cur.execute("SELECT has_attempted_test FROM users WHERE id = %s",
                    (session.get('mysql_user_id'),))
        row = cur.fetchone()
        cur.close()
        conn.close()

        if row and row['has_attempted_test']:
            return render_template('error.html',
                                   message="You have already attempted the test.")
    except Exception as err:
        return render_template('error.html', message=f"Database error: {err}")
    # ── end guard ─────────────────────────────────────────────────────────

    if 'test_completed' in session:
        return redirect(url_for('score'))

    if session.get('class_level') != class_level:
        return redirect(url_for('login'))

    # resolve stream
    if class_level in ('class9', 'class10'):
        user_stream = 'general'
    else:
        user_stream = stream if stream else session.get('stream')
        if session.get('stream') != user_stream:
            return redirect(url_for('login'))

    assigned_set = session.get('assigned_set', 'a')
    questions    = load_questions(class_level, user_stream, assigned_set)

    if not questions:
        label = class_level
        if user_stream != 'general':
            label += f" – {user_stream}"
        label += f" – Set {assigned_set.upper()}"
        return render_template('error.html',
                               message=f"No questions available for {label}")

    return render_template('test.html',
                           questions=questions,
                           class_level=class_level,
                           stream=user_stream,
                           assigned_set=assigned_set.upper(),
                           username=session.get('username'))

# --------------------------------------------------------------------------
# SUBMIT TEST  (called by test.js via POST /api/submit_test)
# --------------------------------------------------------------------------
@app.route('/api/submit_test', methods=['POST'])
@login_required
def submit_test():
    """Score answers, lock the attempt in MySQL, persist result in SQLite."""
    try:
        data            = request.get_json()
        answers         = data.get('answers', {})
        tab_switches    = data.get('tab_switches', 0)
        submission_type = data.get('submission_type', 'manual')   # manual | timeout | tab_violation

        class_level  = session.get('class_level')
        stream       = session.get('stream')
        assigned_set = session.get('assigned_set', 'a')
        questions    = load_questions(class_level, stream, assigned_set)

        # ── score ─────────────────────────────────────────────────────────
        correct_count   = 0
        total_questions = len(questions)

        for q in questions:
            qid = str(q['id'])
            if qid in answers and int(answers[qid]) == q['correct']:
                correct_count += 1

        # ── lock attempt in MySQL (do this FIRST – once locked, it stays) ─
        try:
            conn = get_mysql_connection()
            cur  = conn.cursor()
            cur.execute("""
                UPDATE users
                SET    has_attempted_test = TRUE
                WHERE  id = %s
            """, (session.get('mysql_user_id'),))
            conn.commit()
            cur.close()
            conn.close()
        except Exception as err:
            # log but don't abort – the score must still be saved
            print(f"[ERROR] MySQL UPDATE has_attempted_test failed: {err}")

        # ── persist result in SQLite ──────────────────────────────────────
        conn = sqlite3.connect('quiz_app.db')
        cur  = conn.cursor()
        cur.execute('''
            INSERT INTO test_results
            (user_id, username, class_level, stream, assigned_set,
             score, total_questions, tab_switches, submission_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (session.get('user_id'), session.get('username'),
              class_level, stream, assigned_set,
              correct_count, total_questions, tab_switches, submission_type))
        conn.commit()
        conn.close()

        # ── stamp session so /score can render ────────────────────────────
        session['test_completed']  = True
        session['score']           = correct_count
        session['total_questions'] = total_questions
        session['tab_switches']    = tab_switches
        session['submission_type'] = submission_type

        return jsonify({'success': True, 'score': correct_count, 'total': total_questions})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# --------------------------------------------------------------------------
# TAB-SWITCH LOG  (called by test.js)
# --------------------------------------------------------------------------
@app.route('/api/log_tab_switch', methods=['POST'])
@login_required
def log_tab_switch():
    try:
        session['tab_switches'] = session.get('tab_switches', 0) + 1
        return jsonify({'success': True, 'tab_switches': session['tab_switches']})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# --------------------------------------------------------------------------
# SCORE PAGE
# --------------------------------------------------------------------------
@app.route('/score')
@login_required
def score():
    if 'test_completed' not in session:
        return redirect(url_for('index'))

    sc    = session.get('score', 0)
    total = session.get('total_questions', 0)
    pct   = (sc / total * 100) if total > 0 else 0
    s_pct, s_msg = calculate_scholarship(pct)

    return render_template('score.html',
                           username=session.get('username'),
                           class_level=session.get('class_level'),
                           stream=session.get('stream'),
                           assigned_set=session.get('assigned_set', 'a').upper(),
                           score=sc,
                           total=total,
                           percentage=round(pct, 2),
                           scholarship_percent=s_pct,
                           scholarship_message=s_msg,
                           tab_switches=session.get('tab_switches', 0),
                           submission_type=session.get('submission_type', 'manual'))

# --------------------------------------------------------------------------
# LOGOUT
# --------------------------------------------------------------------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --------------------------------------------------------------------------
# ADMIN – quick view of set distribution (SQLite)
# --------------------------------------------------------------------------
@app.route('/admin/set-distribution')
def admin_set_distribution():
    conn = sqlite3.connect('quiz_app.db')
    cur  = conn.cursor()
    cur.execute('''
        SELECT class_level, stream, assigned_set, COUNT(*) as cnt
        FROM   users
        GROUP  BY class_level, stream, assigned_set
        ORDER  BY class_level, stream, assigned_set
    ''')
    rows = cur.fetchall()
    conn.close()
    return jsonify([{'class': r[0], 'stream': r[1], 'set': r[2], 'count': r[3]}
                    for r in rows])

# --------------------------------------------------------------------------
# Error handlers
# --------------------------------------------------------------------------
@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', message="Page not found"), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', message="Internal server error"), 500

# --------------------------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)