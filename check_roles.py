import sqlite3

conn = sqlite3.connect('parking.db')
cursor = conn.cursor()
cursor.execute("SELECT email, role FROM users WHERE email LIKE 'demo%'")
rows = cursor.fetchall()

print("Demo user roles:")
for email, role in rows:
    print(f"  {email}: {role}")

conn.close()
