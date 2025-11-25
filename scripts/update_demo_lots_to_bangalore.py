import sqlite3
import os

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DEMO_DB = os.path.join(REPO_ROOT, 'instance', 'demo.db')

if not os.path.exists(DEMO_DB):
    print(f"Demo DB not found at {DEMO_DB}")
    raise SystemExit(1)

# Bangalore coordinates for chosen demo lots
# Lot 1: Downtown Business District -> MG Road / Bangalore center
# Lot 2: Airport Terminal Parking -> Kempegowda International Airport (BLR)
# Lot 3: Shopping Mall Complex -> Koramangala
# Lot 4: Residential Area Hub -> Jayanagar
bangalore_coords = {
    1: (12.9716, 77.5946),   # MG Road / Bangalore center
    2: (13.1986, 77.7066),   # Kempegowda International Airport
    3: (12.9352, 77.6245),   # Koramangala / shopping district
    4: (12.9250, 77.5938)    # Jayanagar / residential
}

print(f"Opening demo DB: {DEMO_DB}\n")
conn = sqlite3.connect(DEMO_DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Show current lot coords
cur.execute("SELECT lot_id, location, latitude, longitude FROM lots ORDER BY lot_id")
rows = cur.fetchall()
print("Current lot coordinates:")
for r in rows:
    print(f" - lot_id={r['lot_id']} location={r['location']} lat={r['latitude']} lon={r['longitude']}")

# Update selected lots
for lot_id, (lat, lon) in bangalore_coords.items():
    cur.execute("UPDATE lots SET latitude = ?, longitude = ? WHERE lot_id = ?", (lat, lon, lot_id))

conn.commit()
print('\nUpdated coordinates for lots 1-4 to Bangalore values.')

# Show updated values
cur.execute("SELECT lot_id, location, latitude, longitude FROM lots ORDER BY lot_id")
rows = cur.fetchall()
print('\nUpdated lot coordinates:')
for r in rows:
    print(f" - lot_id={r['lot_id']} location={r['location']} lat={r['latitude']} lon={r['longitude']}")

conn.close()
print('\nDone.')