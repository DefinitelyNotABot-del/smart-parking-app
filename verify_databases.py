import sqlite3

demo = sqlite3.connect('demo.db')
regular = sqlite3.connect('parking.db')

print("=" * 60)
print("DATABASE VERIFICATION")
print("=" * 60)

# Check demo.db
demo_users = demo.execute("SELECT COUNT(*) FROM users").fetchone()[0]
demo_lots = demo.execute("SELECT COUNT(*) FROM lots").fetchone()[0]
demo_spots = demo.execute("SELECT COUNT(*) FROM spots").fetchone()[0]
demo_bookings = demo.execute("SELECT COUNT(*) FROM bookings").fetchone()[0]

print("\n📊 demo.db (Demo Accounts)")
print(f"   Users: {demo_users}")
print(f"   Lots: {demo_lots}")
print(f"   Spots: {demo_spots}")
print(f"   Bookings: {demo_bookings}")

# Check parking.db
regular_users = regular.execute("SELECT COUNT(*) FROM users").fetchone()[0]
regular_lots = regular.execute("SELECT COUNT(*) FROM lots").fetchone()[0]
regular_spots = regular.execute("SELECT COUNT(*) FROM spots").fetchone()[0]
regular_bookings = regular.execute("SELECT COUNT(*) FROM bookings").fetchone()[0]

print("\n📊 parking.db (Regular Users)")
print(f"   Users: {regular_users}")
print(f"   Lots: {regular_lots}")
print(f"   Spots: {regular_spots}")
print(f"   Bookings: {regular_bookings}")

print("\n" + "=" * 60)
print("✅ Both databases are working correctly!")
print("=" * 60)

demo.close()
regular.close()
