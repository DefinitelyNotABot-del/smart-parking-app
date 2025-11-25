import sqlite3
import os
from datetime import datetime, timedelta

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DEMO_DB = os.path.join(REPO_ROOT, 'instance', 'demo.db')

if not os.path.exists(DEMO_DB):
    print(f"Demo DB not found at {DEMO_DB}")
    raise SystemExit(1)

print(f"Opening demo DB: {DEMO_DB}\n")
conn = sqlite3.connect(DEMO_DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Find demo customer
cur.execute("SELECT user_id FROM users WHERE email = 'demo.customer@smartparking.com'")
row = cur.fetchone()
if not row:
    print("Demo customer user not found")
    conn.close()
    raise SystemExit(1)

user_id = row['user_id']
print(f"Demo customer id: {user_id}\n")

# Get available lots
cur.execute("SELECT DISTINCT lot_id FROM lots ORDER BY lot_id")
lot_rows = cur.fetchall()
if len(lot_rows) < 2:
    print("Less than 2 lots found; nothing to do.")
    conn.close()
    raise SystemExit(1)

# Choose first two lots
target_lots = [lot_rows[0]['lot_id'], lot_rows[1]['lot_id']]
print(f"Target lots to book (first two): {target_lots}\n")

now = datetime.now()
start_time = (now - timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
end_time = (now + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
duration_hours = ( (now + timedelta(days=30)) - (now - timedelta(minutes=30)) ).total_seconds() / 3600.0

inserted = 0

# For each target lot, pick up to N spots and create a booking per spot
N_SPOTS_PER_LOT = 8
for lot_id in target_lots:
    cur.execute("SELECT spot_id, price_per_hour FROM spots WHERE lot_id = ? ORDER BY spot_id LIMIT ?", (lot_id, N_SPOTS_PER_LOT))
    spots = cur.fetchall()
    if not spots:
        print(f"No spots found for lot {lot_id}, skipping")
        continue
    for s in spots:
        spot_id = s['spot_id']
        price = s['price_per_hour'] if s['price_per_hour'] is not None else 30.0
        total_cost = round(price * duration_hours, 2)
        try:
            cur.execute(
                "INSERT INTO bookings (user_id, lot_id, spot_id, start_time, end_time, total_cost, price_per_hour) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user_id, lot_id, spot_id, start_time, end_time, total_cost, price)
            )
            inserted += 1
        except Exception as e:
            # Ignore insert errors (e.g., duplicates)
            print(f"Failed to insert booking for lot={lot_id}, spot={spot_id}: {e}")

conn.commit()
conn.close()
print(f"Inserted {inserted} future bookings for demo customer (start={start_time}, end={end_time})")