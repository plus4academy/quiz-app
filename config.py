# config.py — MySQL configuration (single source of truth)
# Edit ONLY this file when credentials change. app.py reads from here.

import os
from urllib.parse import urlparse

def _to_bool(value, default=True):
    if value is None:
        return default
    return str(value).strip().lower() in ('1', 'true', 'yes', 'on')

# Railway provides DATABASE_URL
database_url = os.getenv('DATABASE_URL')

if database_url:
    # Production: Parse Railway's MYSQL_URL
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
SMTP_CONFIG = {
    'host': os.getenv('SMTP_HOST', ''),
    'port': int(os.getenv('SMTP_PORT', '587')),
    'username': os.getenv('SMTP_USERNAME', ''),
    'password': os.getenv('SMTP_PASSWORD', ''),
    'sender': os.getenv('SMTP_SENDER', os.getenv('SMTP_USERNAME', '')),
    'use_tls': _to_bool(os.getenv('SMTP_USE_TLS', 'true')),
}


# from werkzeug.security import generate_password_hash

# password = "test1234"                          # whatever you want the password to be
# hashed   = generate_password_hash(password)
# print(hashed)
