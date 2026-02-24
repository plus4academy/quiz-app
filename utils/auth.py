from functools import wraps

from flask import redirect, session, url_for


def login_required(view_fn):
    @wraps(view_fn)
    def wrapper(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('auth.login'))
        return view_fn(*args, **kwargs)

    return wrapper
