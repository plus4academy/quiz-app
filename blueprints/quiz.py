from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for

from services.email_service import send_result_emails
from services.mysql_store import get_mysql_connection
from services.question_service import load_questions
from services.sqlite_store import get_sqlite_connection
from utils.auth import login_required
from utils.scoring import calculate_scholarship, get_test_duration_minutes

quiz_bp = Blueprint('quiz', __name__)


def _get_latest_user_contact(mysql_user_id):
    if not mysql_user_id:
        return {}

    try:
        conn = get_mysql_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                'SELECT full_name, phone, email FROM users WHERE id = %s',
                (mysql_user_id,),
            )
            return cur.fetchone() or {}
        finally:
            cur.close()
            conn.close()
    except Exception:
        # Fallback to session values if MySQL is temporarily unavailable.
        return {}


@quiz_bp.route('/test/<class_level>')
@quiz_bp.route('/test/<class_level>/<stream>')
@login_required
def test_page(class_level=None, stream=None):
    try:
        conn = get_mysql_connection()
        cur = conn.cursor()
        cur.execute('SELECT has_attempted_set FROM users WHERE id = %s', (session.get('mysql_user_id'),))
        row = cur.fetchone()

        if row and row['has_attempted_set'] == 1:
            cur.close()
            conn.close()
            return render_template(
                'error.html',
                message='You have already attempted the test. Only one attempt is allowed.',
            )

        cur.execute('UPDATE users SET has_attempted_set = 1 WHERE id = %s', (session.get('mysql_user_id'),))
        conn.commit()
        cur.close()
        conn.close()

    except Exception as err:
        return render_template('error.html', message=f'Database error: {err}')

    if 'test_completed' in session:
        return redirect(url_for('quiz.score'))

    if session.get('class_level') != class_level:
        return redirect(url_for('auth.login'))

    if class_level in ('class9', 'class10'):
        user_stream = 'general'
    else:
        user_stream = stream if stream else session.get('stream')
        if session.get('stream') != user_stream:
            return redirect(url_for('auth.login'))

    assigned_set = session.get('assigned_set', 'a')
    questions = load_questions(class_level, user_stream, assigned_set)

    if not questions:
        label = class_level
        if user_stream != 'general':
            label += f' - {user_stream}'
        label += f' - Set {assigned_set.upper()}'
        return render_template('error.html', message=f'No questions available for {label}')

    return render_template(
        'test.html',
        questions=questions,
        class_level=class_level,
        stream=user_stream,
        assigned_set=assigned_set.upper(),
        test_duration_minutes=get_test_duration_minutes(class_level),
        username=session.get('username'),
    )


@quiz_bp.route('/api/submit_test', methods=['POST'])
@login_required
def submit_test():
    try:
        data = request.get_json() or {}
        answers = data.get('answers', {})
        tab_switches = data.get('tab_switches', 0)
        submission_type = data.get('submission_type', 'manual')

        class_level = session.get('class_level')
        stream = session.get('stream')
        assigned_set = session.get('assigned_set', 'a')
        questions = load_questions(class_level, stream, assigned_set)

        correct_count = 0
        total_questions = len(questions)

        for question in questions:
            qid = str(question['id'])
            if qid in answers and int(answers[qid]) == question['correct']:
                correct_count += 1

        conn = get_sqlite_connection()
        cur = conn.cursor()
        cur.execute(
            '''
            INSERT INTO test_results
            (user_id, username, class_level, stream, assigned_set,
             score, total_questions, tab_switches, submission_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                session.get('user_id'),
                session.get('username'),
                class_level,
                stream,
                assigned_set,
                correct_count,
                total_questions,
                tab_switches,
                submission_type,
            ),
        )
        conn.commit()
        conn.close()

        session['test_completed'] = True
        session['score'] = correct_count
        session['total_questions'] = total_questions
        session['tab_switches'] = tab_switches
        session['submission_type'] = submission_type

        latest_user = _get_latest_user_contact(session.get('mysql_user_id'))
        student_name = (
            latest_user.get('full_name')
            or session.get('full_name')
            or session.get('username')
            or 'Student'
        )
        student_email = (latest_user.get('email') or session.get('email') or '').strip()
        student_phone = latest_user.get('phone') or session.get('phone') or ''

        try:
            email_status = send_result_emails(
                student_name=student_name,
                student_email=student_email,
                phone=student_phone,
                class_level=class_level,
                stream=stream,
                score=correct_count,
                total_questions=total_questions,
            )
        except Exception as err:
            email_status = {
                'student_email': (False, f'email send failed: {err}'),
                'admin_email': (False, f'email send failed: {err}'),
            }

        return jsonify(
            {
                'success': True,
                'score': correct_count,
                'total': total_questions,
                'email_status': {
                    'student': email_status['student_email'][0],
                    'admin': email_status['admin_email'][0],
                    'student_error': email_status['student_email'][1] if not email_status['student_email'][0] else '',
                    'admin_error': email_status['admin_email'][1] if not email_status['admin_email'][0] else '',
                },
            }
        )

    except Exception as err:
        return jsonify({'success': False, 'error': str(err)}), 500


@quiz_bp.route('/api/log_tab_switch', methods=['POST'])
@login_required
def log_tab_switch():
    try:
        session['tab_switches'] = session.get('tab_switches', 0) + 1
        return jsonify({'success': True, 'tab_switches': session['tab_switches']})
    except Exception as err:
        return jsonify({'success': False, 'error': str(err)}), 500


@quiz_bp.route('/score')
@login_required
def score():
    if 'test_completed' not in session:
        return redirect(url_for('core.index'))

    score_value = session.get('score', 0)
    total = session.get('total_questions', 0)
    percentage = (score_value / total * 100) if total > 0 else 0
    scholarship_pct, scholarship_msg = calculate_scholarship(percentage)

    return render_template(
        'score.html',
        username=session.get('username'),
        class_level=session.get('class_level'),
        stream=session.get('stream'),
        assigned_set=session.get('assigned_set', 'a').upper(),
        score=score_value,
        total=total,
        percentage=round(percentage, 2),
        scholarship_percent=scholarship_pct,
        scholarship_message=scholarship_msg,
        tab_switches=session.get('tab_switches', 0),
        submission_type=session.get('submission_type', 'manual'),
    )
