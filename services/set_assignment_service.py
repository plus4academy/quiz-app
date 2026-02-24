from services.question_service import get_available_sets
from services.sqlite_store import get_sqlite_connection


def get_next_set(class_level, stream):
    sets = get_available_sets(class_level, stream)
    conn = get_sqlite_connection()
    cur = conn.cursor()

    cur.execute(
        '''
        INSERT OR IGNORE INTO set_counter (class_level, stream, current_set_index)
        VALUES (?, ?, 0)
        ''',
        (class_level, stream),
    )

    cur.execute(
        '''
        SELECT current_set_index FROM set_counter
        WHERE class_level = ? AND stream = ?
        ''',
        (class_level, stream),
    )

    row = cur.fetchone()
    current_index = row[0] if row else 0
    assigned_set = sets[current_index % len(sets)]

    cur.execute(
        '''
        UPDATE set_counter SET current_set_index = ?
        WHERE class_level = ? AND stream = ?
        ''',
        ((current_index + 1) % len(sets), class_level, stream),
    )

    conn.commit()
    conn.close()
    return assigned_set
