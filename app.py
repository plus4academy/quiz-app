from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from datetime import datetime, timedelta
from functools import wraps
from email.message import EmailMessage
import secrets
import sqlite3
import json
import os
import re
import smtplib
from typing import List

import pymysql

from config import MYSQL_CONFIG, SMTP_CONFIG

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)

# ==========================================================================
# SQLite init
# ==========================================================================
def init_db():
    conn = sqlite3.connect('quiz_app.db')
    cur = conn.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            class_level TEXT NOT NULL,
            stream TEXT NOT NULL,
            assigned_set TEXT NOT NULL,
            login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS test_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT NOT NULL,
            class_level TEXT NOT NULL,
            stream TEXT NOT NULL,
            assigned_set TEXT NOT NULL,
            score INTEGER NOT NULL,
            total_questions INTEGER NOT NULL,
            tab_switches INTEGER DEFAULT 0,
            submission_type TEXT,
            test_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS set_counter (
            id INTEGER PRIMARY KEY,
            class_level TEXT NOT NULL,
            stream TEXT NOT NULL,
            current_set_index INTEGER DEFAULT 0,
            UNIQUE(class_level, stream)
        )
    ''')

    conn.commit()
    conn.close()

init_db()

# ==========================================================================
# MySQL helper
# ==========================================================================
def get_mysql_connection():
    return pymysql.connect(
        host=MYSQL_CONFIG['host'],
        user=MYSQL_CONFIG['user'],
        password=MYSQL_CONFIG['password'],
        database=MYSQL_CONFIG['database'],
        charset=MYSQL_CONFIG.get('charset', 'utf8mb4'),
        cursorclass=pymysql.cursors.DictCursor
    )

# ==========================================================================
# Helper: Generate username and password from name + phone
# ==========================================================================
def generate_username(full_name, phone):
    """Generate username: firstname.lastname + last 4 digits of phone"""
    name_parts = full_name.strip().lower().split()
    if len(name_parts) < 2:
        raise ValueError("Full name must include first and last name")
    
    first_name = name_parts[0]
    last_name = name_parts[-1]
    last_4_digits = phone[-4:]
    
    return f"{first_name}.{last_name}{last_4_digits}"

# ==========================================================================
# Helper: Parse promoted_to_class into class_level + stream
# ==========================================================================
def parse_promoted_class(promoted_to_class):
    """
    Input examples: "9", "10", "11 jee", "12 neet", "dropper jee"
    Returns: (class_level, stream)
    """
    parts = promoted_to_class.strip().lower().split()
    
    if len(parts) == 1:
        # "9" or "10"
        return (f"class{parts[0]}", "general")
    elif len(parts) == 2:
        # "11 jee", "12 neet", "dropper jee"
        class_num = parts[0]
        stream = parts[1]
        
        if class_num == "dropper":
            return ("dropper", stream)
        else:
            return (f"class{class_num}", stream)
    else:
        raise ValueError("Invalid promoted_to_class format")

# ==========================================================================
# Round-robin set assignment
# ==========================================================================
def get_next_set(class_level, stream):
    sets = get_available_sets(class_level, stream)
    conn = sqlite3.connect('quiz_app.db')
    cur = conn.cursor()

    cur.execute('''
        INSERT OR IGNORE INTO set_counter (class_level, stream, current_set_index)
        VALUES (?, ?, 0)
    ''', (class_level, stream))

    cur.execute('''
        SELECT current_set_index FROM set_counter
        WHERE class_level = ? AND stream = ?
    ''', (class_level, stream))

    row = cur.fetchone()
    current_index = row[0] if row else 0
    assigned_set = sets[current_index % len(sets)]

    cur.execute('''
        UPDATE set_counter SET current_set_index = ?
        WHERE class_level = ? AND stream = ?
    ''', ((current_index + 1) % len(sets), class_level, stream))

    conn.commit()
    conn.close()
    return assigned_set

# ==========================================================================
# Question loader
# ==========================================================================
def _class_level_aliases(class_level: str) -> List[str]:
    if class_level == 'dropper':
        return ['dropper', 'droppers']
    return [class_level]

def get_available_sets(class_level, stream):
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    aliases = _class_level_aliases(class_level)
    stream_name = stream or 'general'
    found_sets = set()

    for alias in aliases:
        pattern = re.compile(rf'^questions_{re.escape(alias)}_{re.escape(stream_name)}_([a-z])\.json$')
        try:
            for name in os.listdir(base_dir):
                m = pattern.match(name)
                if m:
                    found_sets.add(m.group(1))
        except FileNotFoundError:
            pass

    if found_sets:
        return sorted(found_sets)
    return ['a', 'b', 'c', 'd']

def load_questions(class_level, stream, set_name):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    aliases = _class_level_aliases(class_level)
    stream_name = stream or 'general'

    for alias in aliases:
        set_path = os.path.join(base_dir, f'data/questions_{alias}_{stream_name}_{set_name}.json')
        if os.path.exists(set_path):
            with open(set_path, 'r', encoding='utf-8') as fh:
                return json.load(fh)

    for alias in aliases:
        shared_path = os.path.join(base_dir, f'data/questions_{alias}_{stream_name}.json')
        if os.path.exists(shared_path):
            with open(shared_path, 'r', encoding='utf-8') as fh:
                return json.load(fh)

    # Fallback to first available set to avoid hard-fail on legacy assignments.
    available_sets = get_available_sets(class_level, stream_name)
    for fallback_set in available_sets:
        for alias in aliases:
            fallback_path = os.path.join(base_dir, f'data/questions_{alias}_{stream_name}_{fallback_set}.json')
            if os.path.exists(fallback_path):
                with open(fallback_path, 'r', encoding='utf-8') as fh:
                    return json.load(fh)

    return []

# ==========================================================================
# Auth decorator
# ==========================================================================
def login_required(f):
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
    if percentage >= 100:
        return 95, "Great scholarship opportunity for a brilliant mind - Congratulations!"
    elif percentage >= 90:
        return 70, "What a score - Well Done!"
    elif percentage >= 75:
        return 50, "Good effort!"
    elif percentage >= 50:
        return 25, "Quarter Scholarship - Keep Trying!"
    else:
        return 10, "A scholarship for participation - Don't give up, keep learning!"

def get_test_duration_minutes(class_level):
    duration_map = {
        'class9': 30,
        'class10': 30,
        'class11': 40,
        'class12': 45,
    }
    return duration_map.get(class_level, 60)

# ==========================================================================
# Email helpers
# ==========================================================================
def format_class_label(class_level, stream):
    if class_level == 'dropper':
        return f"Dropper ({stream.upper()})" if stream else "Dropper"

    if class_level.startswith('class'):
        number = class_level.replace('class', '')
        if stream and stream != 'general':
            return f"Class {number} ({stream.upper()})"
        return f"Class {number}"

    return class_level

def send_plain_email(to_address, subject, body):
    if not SMTP_CONFIG.get('host'):
        return False, "SMTP host not configured"

    sender = SMTP_CONFIG.get('sender') or SMTP_CONFIG.get('username')
    if not sender:
        return False, "SMTP sender not configured"

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = to_address
    msg.set_content(body)

    try:
        with smtplib.SMTP(SMTP_CONFIG['host'], SMTP_CONFIG['port'], timeout=10) as smtp:
            if SMTP_CONFIG.get('use_tls', True):
                smtp.starttls()
            if SMTP_CONFIG.get('username') and SMTP_CONFIG.get('password'):
                smtp.login(SMTP_CONFIG['username'], SMTP_CONFIG['password'])
            smtp.send_message(msg)
        return True, "sent"
    except Exception as err:
        return False, str(err)

def send_result_emails(student_name, student_email, phone, class_level, stream, score, total_questions):
    class_label = format_class_label(class_level, stream)
    percentage = round((score / total_questions * 100), 2) if total_questions else 0
    marks = f"{score}/{total_questions} ({percentage}%)"

    subject = "Plus4 Academy Quiz Result"
    body = (
        "Quiz Result Details\n\n"
        f"Student Name: {student_name}\n"
        f"Class: {class_label}\n"
        f"Marks Scored: {marks}\n"
        f"Phone Number: {phone}\n"
    )

    status = {}

    if student_email:
        status['student_email'] = send_plain_email(student_email, subject, body)
    else:
        status['student_email'] = (False, "Student email not available")

    admin_email = 'plus4academy2025@gmail.com'
    admin_subject = f"Quiz Result - {student_name}"
    status['admin_email'] = send_plain_email(admin_email, admin_subject, body)

    return status

# ==========================================================================
# ROUTES
# ==========================================================================

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))

    if 'test_completed' in session:
        return redirect(url_for('score'))

    class_level = session.get('class_level')
    stream = session.get('stream')
    if class_level in ('class9', 'class10'):
        return redirect(url_for('test_page', class_level=class_level))
    return redirect(url_for('test_page', class_level=class_level, stream=stream))

# --------------------------------------------------------------------------
# SIGNUP ROUTE
# --------------------------------------------------------------------------
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        promoted_to_class_raw = request.form.get('promoted_to_class', '').strip()
        stream_raw = request.form.get('stream', '').strip()

        # Basic validation
        if not all([full_name, phone, email, password, promoted_to_class_raw]):
            return render_template('signup.html', error="All required fields must be filled")
        
        # Validate password length
        if len(password) < 6:
            return render_template('signup.html', error="Password must be at least 6 characters")

        # Validate phone
        if not re.match(r'^\d{10}$', phone):
            return render_template('signup.html', error="Phone must be 10 digits")

        # Validate email
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            return render_template('signup.html', error="Invalid email format")

        # Build promoted_to_class value for MySQL
        if promoted_to_class_raw in ('11', '12', 'dropper'):
            if not stream_raw:
                return render_template('signup.html', error="Stream required for Class 11, 12, and Dropper")
            promoted_to_class = f"{promoted_to_class_raw} {stream_raw}"
        else:
            promoted_to_class = promoted_to_class_raw  # "9" or "10"

        # Generate username
        try:
            username = generate_username(full_name, phone)
        except ValueError as e:
            return render_template('signup.html', error=str(e))

        # Insert into MySQL
        try:
            conn = get_mysql_connection()
            cur = conn.cursor()

            # Check if username already exists
            cur.execute("SELECT id FROM users WHERE username = %s", (username,))
            if cur.fetchone():
                cur.close()
                conn.close()
                return render_template('signup.html', error="Username already exists. Please contact admin.")

            # Check if phone already exists
            cur.execute("SELECT id FROM users WHERE phone = %s", (phone,))
            if cur.fetchone():
                cur.close()
                conn.close()
                return render_template('signup.html', error="Phone number already registered")

            # Check if email already exists
            cur.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cur.fetchone():
                cur.close()
                conn.close()
                return render_template('signup.html', error="Email already registered")

            # Insert new user
            cur.execute("""
                INSERT INTO users (full_name, phone, email, username, password, promoted_to_class, has_attempted_set)
                VALUES (%s, %s, %s, %s, %s, %s, 0)
            """, (full_name, phone, email, username, password, promoted_to_class))

            conn.commit()
            cur.close()
            conn.close()

            return render_template('signup.html', 
                                   success=f"Account created successfully! Your username is: {username}. Please login to start the test.")

        except Exception as e:
            return render_template('signup.html', error=f"Database error: {e}")

    return render_template('signup.html')

# --------------------------------------------------------------------------
# LOGIN ROUTE (UPDATED)
# --------------------------------------------------------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not all([username, password]):
            return render_template('login.html', error="Username and password required")

        try:
            conn = get_mysql_connection()
            cur = conn.cursor()

            cur.execute("""
                SELECT id, full_name, phone, email, username, password, promoted_to_class, has_attempted_set
                FROM users
                WHERE username = %s
            """, (username,))

            user = cur.fetchone()

            if not user:
                cur.close()
                conn.close()
                return render_template('login.html', error="Invalid username or password")

            if user['password'] != password:
                cur.close()
                conn.close()
                return render_template('login.html', error="Invalid username or password")

            if user['has_attempted_set'] == 1:
                cur.close()
                conn.close()
                return render_template('login.html', 
                                       error="You have already attempted the test. Only one attempt is allowed.")

            cur.close()
            conn.close()

        except Exception as err:
            return render_template('login.html', error=f"Database error: {err}")

        # Parse promoted_to_class into class_level + stream
        class_level, stream = parse_promoted_class(user['promoted_to_class'])

        # Assign question set
        assigned_set = get_next_set(class_level, stream)

        # Log in SQLite
        conn = sqlite3.connect('quiz_app.db')
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO users (username, password, class_level, stream, assigned_set)
            VALUES (?, ?, ?, ?, ?)
        ''', (username, password, class_level, stream, assigned_set))
        sqlite_user_id = cur.lastrowid
        conn.commit()
        conn.close()

        # Set session
        session.permanent = True
        session['username'] = user['full_name']
        session['full_name'] = user['full_name']
        session['phone'] = user['phone']
        session['email'] = user['email']
        session['user_id'] = sqlite_user_id
        session['mysql_user_id'] = user['id']
        session['class_level'] = class_level
        session['stream'] = stream
        session['assigned_set'] = assigned_set
        session['tab_switches'] = 0
        session['test_start_time'] = datetime.now().isoformat()

        # Redirect to test
        if class_level in ('class9', 'class10'):
            return redirect(url_for('test_page', class_level=class_level))
        return redirect(url_for('test_page', class_level=class_level, stream=stream))

    return render_template('login.html')

# --------------------------------------------------------------------------
# TEST PAGE (MARK ATTEMPTED ON START)
# --------------------------------------------------------------------------
@app.route('/test/<class_level>')
@app.route('/test/<class_level>/<stream>')
@login_required
def test_page(class_level=None, stream=None):
    # Check if already attempted
    try:
        conn = get_mysql_connection()
        cur = conn.cursor()
        cur.execute("SELECT has_attempted_set FROM users WHERE id = %s",
                    (session.get('mysql_user_id'),))
        row = cur.fetchone()

        if row and row['has_attempted_set'] == 1:
            cur.close()
            conn.close()
            return render_template('error.html',
                                   message="You have already attempted the test. Only one attempt is allowed.")

        # ðŸ”¥ MARK TEST AS ATTEMPTED RIGHT NOW (when test starts)
        cur.execute("UPDATE users SET has_attempted_set = 1 WHERE id = %s",
                    (session.get('mysql_user_id'),))
        conn.commit()
        cur.close()
        conn.close()

    except Exception as err:
        return render_template('error.html', message=f"Database error: {err}")

    if 'test_completed' in session:
        return redirect(url_for('score'))

    if session.get('class_level') != class_level:
        return redirect(url_for('login'))

    # Resolve stream
    if class_level in ('class9', 'class10'):
        user_stream = 'general'
    else:
        user_stream = stream if stream else session.get('stream')
        if session.get('stream') != user_stream:
            return redirect(url_for('login'))

    assigned_set = session.get('assigned_set', 'a')
    questions = load_questions(class_level, user_stream, assigned_set)

    if not questions:
        label = class_level
        if user_stream != 'general':
            label += f" - {user_stream}"
        label += f" - Set {assigned_set.upper()}"
        return render_template('error.html',
                               message=f"No questions available for {label}")

    return render_template('test.html',
                           questions=questions,
                           class_level=class_level,
                           stream=user_stream,
                           assigned_set=assigned_set.upper(),
                           test_duration_minutes=get_test_duration_minutes(class_level),
                           username=session.get('username'))

# --------------------------------------------------------------------------
# SUBMIT TEST
# --------------------------------------------------------------------------
@app.route('/api/submit_test', methods=['POST'])
@login_required
def submit_test():
    try:
        data = request.get_json()
        answers = data.get('answers', {})
        tab_switches = data.get('tab_switches', 0)
        submission_type = data.get('submission_type', 'manual')

        class_level = session.get('class_level')
        stream = session.get('stream')
        assigned_set = session.get('assigned_set', 'a')
        questions = load_questions(class_level, stream, assigned_set)

        # Score
        correct_count = 0
        total_questions = len(questions)

        for q in questions:
            qid = str(q['id'])
            if qid in answers and int(answers[qid]) == q['correct']:
                correct_count += 1

        # Save to SQLite
        conn = sqlite3.connect('quiz_app.db')
        cur = conn.cursor()
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

        # Update session
        session['test_completed'] = True
        session['score'] = correct_count
        session['total_questions'] = total_questions
        session['tab_switches'] = tab_switches
        session['submission_type'] = submission_type

        email_status = send_result_emails(
            student_name=session.get('full_name', session.get('username')),
            student_email=session.get('email', ''),
            phone=session.get('phone', ''),
            class_level=class_level,
            stream=stream,
            score=correct_count,
            total_questions=total_questions
        )

        return jsonify({
            'success': True,
            'score': correct_count,
            'total': total_questions,
            'email_status': {
                'student': email_status['student_email'][0],
                'admin': email_status['admin_email'][0]
            }
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# --------------------------------------------------------------------------
# TAB-SWITCH LOG
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

    sc = session.get('score', 0)
    total = session.get('total_questions', 0)
    pct = (sc / total * 100) if total > 0 else 0
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
# ADMIN
# --------------------------------------------------------------------------
@app.route('/admin/set-distribution')
def admin_set_distribution():
    conn = sqlite3.connect('quiz_app.db')
    cur = conn.cursor()
    cur.execute('''
        SELECT class_level, stream, assigned_set, COUNT(*) as cnt
        FROM users
        GROUP BY class_level, stream, assigned_set
        ORDER BY class_level, stream, assigned_set
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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

