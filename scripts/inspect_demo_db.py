import sqlite3
import os
from datetime import datetime

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DEMO_DB = os.path.join(REPO_ROOT, 'instance', 'demo.db')
TARGET_EMAIL = 'demo.customer@smartparking.com'

if not os.path.exists(DEMO_DB):
    print(f"Demo DB not found at {DEMO_DB}")
    raise SystemExit(1)

print(f"Opening demo DB: {DEMO_DB}")
conn = sqlite3.connect(DEMO_DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("SELECT user_id, name, email FROM users WHERE email = ?", (TARGET_EMAIL,))
user = cur.fetchone()
if not user:
    print(f"Demo user not found: {TARGET_EMAIL}")
    conn.close()
    raise SystemExit(1)

user_id = user['user_id']
print(f"Found demo user: id={user_id}, name={user['name']}, email={user['email']}")

cur.execute("SELECT COUNT(*) as cnt FROM bookings WHERE user_id = ?", (user_id,))
total = cur.fetchone()['cnt']
print(f"Total bookings for user: {total}")

# Fetch recent bookings
cur.execute("SELECT booking_id, lot_id, spot_id, start_time, end_time, total_cost FROM bookings WHERE user_id = ? ORDER BY start_time DESC LIMIT 50", (user_id,))
rows = cur.fetchall()

now = datetime.now()
future = []
for r in rows:
    start = r['start_time']
    end = r['end_time']
    # Try parsing common formats
    parsed_end = None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S.%f"):
        try:
            parsed_end = datetime.strptime(end, fmt)
            break
        except Exception:
            continue
    if parsed_end is None:
        # fallback: skip
        continue
    if parsed_end > now:
        future.append(dict(r))

print(f"Future/active bookings (end_time > now): {len(future)}")
if future:
    print("Sample future bookings:")
    for b in future[:10]:
        print(f" - booking_id={b['booking_id']}, lot={b['lot_id']}, spot={b['spot_id']}, start={b['start_time']}, end={b['end_time']}, cost={b['total_cost']}")
else:
    print("No future bookings found for demo customer.")

print("-- Recent bookings (up to 10):")
for r in rows[:10]:
    print(f"booking_id={r['booking_id']}, lot={r['lot_id']}, spot={r['spot_id']}, start={r['start_time']}, end={r['end_time']}, cost={r['total_cost']}")

conn.close()