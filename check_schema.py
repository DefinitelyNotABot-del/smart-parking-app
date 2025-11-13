import sqlite3

print("=" * 60)
print("CHECKING DATABASE SCHEMAS")
print("=" * 60)

# Check demo.db
conn = sqlite3.connect('demo.db')
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(lots)")
cols = cursor.fetchall()
print("\n📊 demo.db - lots table columns:")
for col in cols:
    print(f"   {col[1]} ({col[2]})")

# Check if there's an owner_id column
cursor.execute("SELECT * FROM lots LIMIT 1")
row = cursor.fetchone()
cursor.execute("PRAGMA table_info(lots)")
col_names = [c[1] for c in cursor.fetchall()]
print(f"\n   Column names: {col_names}")

# Get lot data
cursor.execute("SELECT lot_id, location, owner_id FROM lots")
lots = cursor.fetchall()
print(f"\n   Lots in demo.db:")
for lot in lots:
    print(f"      Lot {lot[0]}: {lot[1]} (owner_id: {lot[2]})")

conn.close()

# Check user IDs
conn = sqlite3.connect('demo.db')
cursor = conn.cursor()
cursor.execute("SELECT user_id, email, role FROM users")
users = cursor.fetchall()
print(f"\n   Users in demo.db:")
for user in users:
    print(f"      User {user[0]}: {user[1]} ({user[2]})")
conn.close()

print("\n" + "=" * 60)
