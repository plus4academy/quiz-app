# config.py — MySQL configuration (single source of truth)
# Edit ONLY this file when credentials change. app.py reads from here.

import os
from pathlib import Path
from urllib.parse import urlparse


def _load_local_env():
    """
    Minimal .env loader for local runs without external dependencies.
    Existing process environment values are preserved.
    """
    env_path = Path(__file__).resolve().parent / '.env'
    if not env_path.exists():
        return

    try:
        lines = env_path.read_text(encoding='utf-8').splitlines()
    except OSError:
        return

    for raw in lines:
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue

        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key and key not in os.environ:
            os.environ[key] = value

def _to_bool(value, default=True):
    if value is None:
        return default
    return str(value).strip().lower() in ('1', 'true', 'yes', 'on')


_load_local_env()

# Railway provides DATABASE_URL
database_url = os.getenv('DATABASE_URL')

if database_url:
    # Production: Parse Railway's DATABASE_URL
    url = urlparse(database_url)
    
    MYSQL_CONFIG = {
        'host':     url.hostname,
        'port':     url.port or 3306,
        'user':     url.username,
        'password': url.password,
        'database': url.path[1:] if url.path else 'railway',
        'charset':  'utf8mb4',
    }
else:
    # Local development
    MYSQL_CONFIG = {
        'host':     'localhost',
        'user':     'root',
        'password': 'evoljonny',
        'database': 'plusfouracademy',
        'port':     3306,
        'charset':  'utf8mb4',
    }

# SMTP configuration for result emails
# Reads from Railway environment variables in production
# Reads from .env file in local development
SMTP_CONFIG = {
    'host': os.getenv('SMTP_HOST', ''),
    'port': int(os.getenv('SMTP_PORT', '465')),
    'username': os.getenv('SMTP_USERNAME', ''),
    'password': os.getenv('SMTP_PASSWORD', ''),
    'brevo_api_key': (
        os.getenv('BREVO_API_KEY')
        or os.getenv('SENDINBLUE_API_KEY')
        or os.getenv('SIB_API_KEY')
        or ''
    ),
    'sender': os.getenv('SMTP_SENDER', os.getenv('SMTP_USERNAME', '')),
    'sender_name': os.getenv('SMTP_SENDER_NAME', 'Plus4 Academy'),
    'use_tls': _to_bool(os.getenv('SMTP_USE_TLS', 'false')),
    'use_ssl': _to_bool(os.getenv('SMTP_USE_SSL', 'true')),
    'timeout': int(os.getenv('SMTP_TIMEOUT', '10')),
}

