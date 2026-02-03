# config.py — MySQL configuration (single source of truth)
# Edit ONLY this file when credentials change. app.py reads from here.

MYSQL_CONFIG = {
    'host':     'localhost',
    'user':     'root',                # NOT 'root@localhost' — @localhost is the host
    'password': 'evoljonny',
    'database': 'plusfouracademy',
    'charset':  'utf8mb4',
}

# from werkzeug.security import generate_password_hash

# password = "test1234"                          # whatever you want the password to be
# hashed   = generate_password_hash(password)
# print(hashed)