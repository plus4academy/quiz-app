# config.py — MySQL configuration (single source of truth)
# Edit ONLY this file when credentials change. app.py reads from here.

import os
from urllib.parse import urlparse

# Get DATABASE_URL from environment (Railway provides this)
database_url = os.getenv('DATABASE_URL', 'mysql://root:uskuEvQQvvSAkWFsMmYvcAjnrNJUTZeC@mysql.railway.internal:3306/railway')

if database_url:
    # Parse the Railway MySQL URL
    url = urlparse(database_url)
    
    MYSQL_CONFIG = {
        'host':     url.hostname,
        'port':     url.port or 3306,
        'user':     url.username,
        'password': url.password,
        'database': url.path[1:],  # Remove leading '/'
        'charset':  'utf8mb4',
    }
else:
    # Fallback for local development
    MYSQL_CONFIG = {
        'host':     'localhost',
        'user':     'root',
        'password': 'evoljonny',
        'database': 'plusfouracademy',
        'port':     3306,
        'charset':  'utf8mb4',
    }

# from werkzeug.security import generate_password_hash

# password = "test1234"                          # whatever you want the password to be
# hashed   = generate_password_hash(password)

# print(hashed)

