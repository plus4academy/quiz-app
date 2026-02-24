from flask import Flask
from datetime import timedelta
import secrets

from blueprints.admin import admin_bp
from blueprints.auth import auth_bp
from blueprints.core import core_bp
from blueprints.quiz import quiz_bp
from services.sqlite_store import init_db


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = secrets.token_hex(32)
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)

    init_db()

    app.register_blueprint(core_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(quiz_bp)
    app.register_blueprint(admin_bp)

    register_error_handlers(app)
    return app


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(404)
    def not_found(_error):
        from flask import render_template

        return render_template('error.html', message='Page not found'), 404

    @app.errorhandler(500)
    def server_error(_error):
        from flask import render_template

        return render_template('error.html', message='Internal server error'), 500
