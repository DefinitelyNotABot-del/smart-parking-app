import sqlite3

conn = sqlite3.connect('parking.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]
print("Tables:", tables)

if 'lots' in tables:
    cursor.execute("SELECT COUNT(*) FROM lots")
    print(f"Lots count: {cursor.fetchone()[0]}")
    
if 'bookings' in tables:
    cursor.execute("SELECT COUNT(*) FROM bookings")
    print(f"Bookings count: {cursor.fetchone()[0]}")
    
conn.close()
