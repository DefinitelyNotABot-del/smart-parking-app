import sqlite3
from werkzeug.security import check_password_hash

conn = sqlite3.connect('parking.db')
cursor = conn.cursor()
cursor.execute("SELECT email, password_hash FROM users WHERE email LIKE 'demo%'")
rows = cursor.fetchall()

print("Demo accounts in database:")
for email, pwd_hash in rows:
    print(f"\n  Email: {email}")
    print(f"  Hash: {pwd_hash[:60]}...")
    
    # Test if "demo123" works
    if check_password_hash(pwd_hash, "demo123"):
        print("  ✅ Password 'demo123' is correct")
    else:
        print("  ❌ Password 'demo123' does NOT match")

conn.close()
