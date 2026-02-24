from flask import Blueprint, redirect, session, url_for

core_bp = Blueprint('core', __name__)


@core_bp.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('auth.login'))

    if 'test_completed' in session:
        return redirect(url_for('quiz.score'))

    class_level = session.get('class_level')
    stream = session.get('stream')
    if class_level in ('class9', 'class10'):
        return redirect(url_for('quiz.test_page', class_level=class_level))
    return redirect(url_for('quiz.test_page', class_level=class_level, stream=stream))
