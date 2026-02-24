from flask import Blueprint, jsonify

from services.sqlite_store import get_sqlite_connection

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/admin/set-distribution')
def admin_set_distribution():
    conn = get_sqlite_connection()
    cur = conn.cursor()
    cur.execute(
        '''
        SELECT class_level, stream, assigned_set, COUNT(*) as cnt
        FROM users
        GROUP BY class_level, stream, assigned_set
        ORDER BY class_level, stream, assigned_set
        '''
    )
    rows = cur.fetchall()
    conn.close()
    return jsonify([{'class': row[0], 'stream': row[1], 'set': row[2], 'count': row[3]} for row in rows])
