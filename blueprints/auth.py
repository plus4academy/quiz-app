from datetime import datetime

from flask import Blueprint, redirect, render_template, request, session, url_for

from services.mysql_store import get_mysql_connection
from services.set_assignment_service import get_next_set
from services.sqlite_store import get_sqlite_connection
from utils.user_utils import (
    generate_username,
    is_valid_email,
    is_valid_phone,
    parse_promoted_class,
)

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        promoted_to_class_raw = request.form.get('promoted_to_class', '').strip()
        stream_raw = request.form.get('stream', '').strip()

        if not all([full_name, phone, email, password, promoted_to_class_raw]):
            return render_template('signup.html', error='All required fields must be filled')

        if len(password) < 6:
            return render_template('signup.html', error='Password must be at least 6 characters')

        if not is_valid_phone(phone):
            return render_template('signup.html', error='Phone must be 10 digits')

        if not is_valid_email(email):
            return render_template('signup.html', error='Invalid email format')

        if promoted_to_class_raw in ('11', '12', 'dropper'):
            if not stream_raw:
                return render_template('signup.html', error='Stream required for Class 11, 12, and Dropper')
            promoted_to_class = f'{promoted_to_class_raw} {stream_raw}'
        else:
            promoted_to_class = promoted_to_class_raw

        try:
            username = generate_username(full_name, phone)
        except ValueError as err:
            return render_template('signup.html', error=str(err))

        try:
            conn = get_mysql_connection()
            cur = conn.cursor()

            cur.execute('SELECT id FROM users WHERE username = %s', (username,))
            if cur.fetchone():
                cur.close()
                conn.close()
                return render_template('signup.html', error='Username already exists. Please contact admin.')

            cur.execute('SELECT id FROM users WHERE phone = %s', (phone,))
            if cur.fetchone():
                cur.close()
                conn.close()
                return render_template('signup.html', error='Phone number already registered')

            cur.execute('SELECT id FROM users WHERE email = %s', (email,))
            if cur.fetchone():
                cur.close()
                conn.close()
                return render_template('signup.html', error='Email already registered')

            cur.execute(
                '''
                INSERT INTO users (full_name, phone, email, username, password, promoted_to_class, has_attempted_set)
                VALUES (%s, %s, %s, %s, %s, %s, 0)
                ''',
                (full_name, phone, email, username, password, promoted_to_class),
            )

            conn.commit()
            cur.close()
            conn.close()

            return render_template(
                'signup.html',
                success=f'Account created successfully! Your username is: {username}. Please login to start the test.',
            )

        except Exception as err:
            return render_template('signup.html', error=f'Database error: {err}')

    return render_template('signup.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not all([username, password]):
            return render_template('login.html', error='Username and password required')

        try:
            conn = get_mysql_connection()
            cur = conn.cursor()

            cur.execute(
                '''
                SELECT id, full_name, phone, email, username, password, promoted_to_class, has_attempted_set
                FROM users
                WHERE username = %s
                ''',
                (username,),
            )

            user = cur.fetchone()

            if not user:
                cur.close()
                conn.close()
                return render_template('login.html', error='Invalid username or password')

            if user['password'] != password:
                cur.close()
                conn.close()
                return render_template('login.html', error='Invalid username or password')

            if user['has_attempted_set'] == 1:
                cur.close()
                conn.close()
                return render_template(
                    'login.html',
                    error='You have already attempted the test. Only one attempt is allowed.',
                )

            cur.close()
            conn.close()

        except Exception as err:
            return render_template('login.html', error=f'Database error: {err}')

        class_level, stream = parse_promoted_class(user['promoted_to_class'])
        assigned_set = get_next_set(class_level, stream)

        sqlite_conn = get_sqlite_connection()
        sqlite_cur = sqlite_conn.cursor()
        sqlite_cur.execute(
            '''
            INSERT INTO users (username, password, class_level, stream, assigned_set)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (username, password, class_level, stream, assigned_set),
        )
        sqlite_user_id = sqlite_cur.lastrowid
        sqlite_conn.commit()
        sqlite_conn.close()

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

        if class_level in ('class9', 'class10'):
            return redirect(url_for('quiz.test_page', class_level=class_level))
        return redirect(url_for('quiz.test_page', class_level=class_level, stream=stream))

    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
