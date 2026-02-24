import pymysql

from config import MYSQL_CONFIG


def get_mysql_connection():
    return pymysql.connect(
        port=MYSQL_CONFIG.get("port", 3306),
        host=MYSQL_CONFIG['host'],
        user=MYSQL_CONFIG['user'],
        password=MYSQL_CONFIG['password'],
        database=MYSQL_CONFIG['database'],
        charset=MYSQL_CONFIG.get('charset', 'utf8mb4'),
        cursorclass=pymysql.cursors.DictCursor,
    )
