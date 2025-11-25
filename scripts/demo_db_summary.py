import sqlite3
import os
from datetime import datetime

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DEMO_DB = os.path.join(REPO_ROOT, 'instance', 'demo.db')

if not os.path.exists(DEMO_DB):
    print(f"Demo DB not found at {DEMO_DB}")
    raise SystemExit(1)

print(f"Opening demo DB: {DEMO_DB}\n")
conn = sqlite3.connect(DEMO_DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

def q(sql, params=()):
    cur.execute(sql, params)
    return cur.fetchall()

# Users
users = q("SELECT user_id, name, email, role FROM users ORDER BY user_id LIMIT 20")
print(f"Users (showing up to 20): {len(users)} rows")
for u in users[:10]:
    role = u['role'] if 'role' in u.keys() else 'N/A'
    print(f" - id={u['user_id']}, name={u['name']}, email={u['email']}, role={role}")

u_count = q("SELECT COUNT(*) as cnt FROM users")[0]['cnt']
owners_count = q("SELECT COUNT(*) as cnt FROM users WHERE role = 'owner'")[0]['cnt']
customers_count = q("SELECT COUNT(*) as cnt FROM users WHERE role = 'customer'")[0]['cnt']
print(f"\nSummary users -> total={u_count}, owners={owners_count}, customers={customers_count}")

# Lots
lots_count = q("SELECT COUNT(*) as cnt FROM lots")[0]['cnt']
print(f"Lots total: {lots_count}")
lot_samples = q("SELECT lot_id, owner_id, location FROM lots ORDER BY lot_id LIMIT 5")
print("Sample lots:")
for l in lot_samples:
    print(f" - lot_id={l['lot_id']}, owner_id={l['owner_id']}, location={l['location']}")

# Spots
spots_total = q("SELECT COUNT(*) as cnt FROM spots")[0]['cnt']
print(f"\nSpots total: {spots_total}")

# Bookings
bookings_total = q("SELECT COUNT(*) as cnt FROM bookings")[0]['cnt']
print(f"Bookings total: {bookings_total}")

# future / active bookings
now = datetime.now()
# Parse string -> compare just with string 'YYYY-MM-DD HH:MM:SS' format used in demo generator
cur.execute("SELECT COUNT(*) FROM bookings WHERE datetime(end_time) > datetime('now')")
active_count = cur.fetchone()[0]
print(f"Active/future bookings (end_time > now): {active_count}")

# Show demo owner & demo customer records
demo_owner = q("SELECT user_id, name, email FROM users WHERE email = 'demo.owner@smartparking.com'")
demo_cust = q("SELECT user_id, name, email FROM users WHERE email = 'demo.customer@smartparking.com'")
print('\nDemo owner record:')
print(demo_owner[0] if demo_owner else 'Not found')
print('\nDemo customer record:')
print(demo_cust[0] if demo_cust else 'Not found')

# Show some recent bookings (user=demo.customer)
if demo_cust:
    user_id = demo_cust[0]['user_id']
    cur.execute("SELECT COUNT(*) FROM bookings WHERE user_id = ?", (user_id,))
    cnt = cur.fetchone()[0]
    print(f"\nDemo customer booking count: {cnt}")
    cur.execute("SELECT booking_id, lot_id, spot_id, start_time, end_time FROM bookings WHERE user_id = ? ORDER BY start_time DESC LIMIT 10", (user_id,))
    rows = cur.fetchall()
    print('Recent bookings for demo.customer (up to 10):')
    for r in rows:
        print(f" - id={r['booking_id']}, lot={r['lot_id']}, spot={r['spot_id']}, start={r['start_time']}, end={r['end_time']}")

conn.close()