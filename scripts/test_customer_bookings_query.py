import sqlite3
import os

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DEMO_DB = os.path.join(REPO_ROOT, 'instance', 'demo.db')

conn = sqlite3.connect(DEMO_DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

user_id = 2
cur.execute("""
SELECT b.booking_id, b.lot_id, b.spot_id, s.type, l.location, l.latitude, l.longitude, b.start_time, b.end_time,
       b.total_cost, b.price_per_hour
FROM bookings b
JOIN spots s ON b.lot_id = s.lot_id AND b.spot_id = s.spot_id
JOIN lots l ON s.lot_id = l.lot_id
WHERE b.user_id = ?
AND datetime(b.end_time) > datetime('now')
ORDER BY b.start_time ASC
""", (user_id,))
rows = cur.fetchall()
print(f"Found {len(rows)} active bookings for user {user_id}")
for r in rows:
    print(dict(r))

conn.close()
