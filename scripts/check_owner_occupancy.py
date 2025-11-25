import sqlite3
import os
from datetime import datetime

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DEMO_DB = os.path.join(REPO_ROOT, 'instance', 'demo.db')
conn = sqlite3.connect(DEMO_DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Get lot ids
cur.execute("SELECT DISTINCT lot_id FROM lots ORDER BY lot_id")
lots = [r['lot_id'] for r in cur.fetchall()]

now = datetime.now()
now_iso_tz = now.strftime("%Y-%m-%dT%H:%M:%SZ")
print(f"Now (ISO T Z): {now_iso_tz}")
print(f"Now (space): {now.strftime('%Y-%m-%d %H:%M:%S')}\n")

for lot_id in lots:
    # Using BETWEEN with ISO T format (how get_lots uses now_iso)
    cur.execute("SELECT COUNT(DISTINCT spot_id) as cnt FROM bookings WHERE lot_id = ? AND ? BETWEEN start_time AND end_time", (lot_id, now_iso_tz))
    between_cnt = cur.fetchone()['cnt']
    # Using datetime(...) comparison
    cur.execute("SELECT COUNT(DISTINCT spot_id) as cnt FROM bookings WHERE lot_id = ? AND datetime(start_time) <= datetime('now') AND datetime(end_time) > datetime('now')", (lot_id,))
    datetime_cnt = cur.fetchone()['cnt']
    print(f"Lot {lot_id}: BETWEEN-count={between_cnt}, datetime-count={datetime_cnt}")

conn.close()
