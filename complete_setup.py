"""
Complete Database Setup - Initialize DB and Create Demo Accounts
Run this FIRST before starting the Flask app
"""
import sqlite3
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import random

DEMO_DB_PATH = 'demo.db'
REGULAR_DB_PATH = 'parking.db'

def init_database(db_path, db_name):
    """Initialize database with all required tables"""
    print(f"🔧 Initializing {db_name}...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'customer'
        )
    """)
    
    # Lots table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lots (
            lot_id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER NOT NULL,
            location TEXT NOT NULL,
            latitude REAL,
            longitude REAL,
            large_price_per_hour REAL DEFAULT 50.0,
            motorcycle_price_per_hour REAL DEFAULT 15.0,
            large_spots INTEGER DEFAULT 0,
            motorcycle_spots INTEGER DEFAULT 0,
            total_spots INTEGER DEFAULT 0,
            occupied_spots INTEGER DEFAULT 0,
            FOREIGN KEY (owner_id) REFERENCES users(user_id)
        )
    """)
    
    # Spots table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS spots (
            lot_id INTEGER,
            spot_id INTEGER,
            type TEXT NOT NULL,
            status TEXT DEFAULT 'available',
            price_per_hour REAL,
            PRIMARY KEY (lot_id, spot_id),
            FOREIGN KEY (lot_id) REFERENCES lots(lot_id)
        )
    """)
    
    # Bookings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            lot_id INTEGER NOT NULL,
            spot_id INTEGER NOT NULL,
            start_time DATETIME NOT NULL,
            end_time DATETIME NOT NULL,
            total_cost REAL NOT NULL,
            price_per_hour REAL NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (lot_id, spot_id) REFERENCES spots(lot_id, spot_id)
        )
    """)
    
    conn.commit()
    conn.close()
    print(f"   ✅ {db_name} tables created")

def setup_demo_accounts():
    """Create demo accounts with pre-loaded data"""
    conn = sqlite3.connect(DEMO_DB_PATH)
    cursor = conn.cursor()
    
    print("\n" + "=" * 70)
    print("🎯 DEMO ACCOUNT SETUP")
    print("=" * 70)
    
    # Demo credentials
    DEMO_OWNER_EMAIL = 'demo.owner@smartparking.com'
    DEMO_CUSTOMER_EMAIL = 'demo.customer@smartparking.com'
    DEMO_PASSWORD = 'demo123'
    
    # Create demo owner
    print("\n1️⃣ Creating demo owner account...")
    try:
        hashed_pwd = generate_password_hash(DEMO_PASSWORD)
        cursor.execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
            ('Demo Owner Account', DEMO_OWNER_EMAIL, hashed_pwd, 'owner')
        )
        demo_owner_id = cursor.lastrowid
        print(f"   ✅ Created: {DEMO_OWNER_EMAIL}")
    except sqlite3.IntegrityError:
        cursor.execute("SELECT user_id FROM users WHERE email = ?", (DEMO_OWNER_EMAIL,))
        demo_owner_id = cursor.fetchone()[0]
        print(f"   ℹ️  Already exists: {DEMO_OWNER_EMAIL}")
    
    # Create demo customer
    print("\n2️⃣ Creating demo customer account...")
    try:
        hashed_pwd = generate_password_hash(DEMO_PASSWORD)
        cursor.execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
            ('Demo Customer Account', DEMO_CUSTOMER_EMAIL, hashed_pwd, 'customer')
        )
        demo_customer_id = cursor.lastrowid
        print(f"   ✅ Created: {DEMO_CUSTOMER_EMAIL}")
    except sqlite3.IntegrityError:
        cursor.execute("SELECT user_id FROM users WHERE email = ?", (DEMO_CUSTOMER_EMAIL,))
        demo_customer_id = cursor.fetchone()[0]
        print(f"   ℹ️  Already exists: {DEMO_CUSTOMER_EMAIL}")
    
    conn.commit()
    
    # Create parking lots
    print("\n3️⃣ Creating parking lots...")
    demo_lots = [
        ('Downtown Business District', 28.6139, 77.2090, 100, 30, 60.0, 25.0),
        ('Airport Terminal Parking', 28.5562, 77.1000, 150, 50, 80.0, 30.0),
        ('Shopping Mall Complex', 28.5355, 77.3910, 80, 40, 45.0, 20.0),
        ('Residential Area Hub', 28.7041, 77.1025, 60, 35, 35.0, 15.0),
    ]
    
    lot_ids = []
    for location, lat, lng, large, small, large_price, small_price in demo_lots:
        cursor.execute("SELECT lot_id FROM lots WHERE owner_id = ? AND location = ?", 
                      (demo_owner_id, location))
        existing = cursor.fetchone()
        
        if existing:
            lot_id = existing[0]
            print(f"   ℹ️  Already exists: {location}")
        else:
            cursor.execute("""
                INSERT INTO lots (owner_id, location, latitude, longitude,
                                large_price_per_hour, motorcycle_price_per_hour,
                                large_spots, motorcycle_spots, total_spots, occupied_spots)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (demo_owner_id, location, lat, lng, large_price, small_price,
                  large, small, large + small, 0))
            lot_id = cursor.lastrowid
            print(f"   ✅ Created: {location}")
        
        lot_ids.append((lot_id, large, small, large_price, small_price))
    
    conn.commit()
    
    # Create spots
    print("\n4️⃣ Creating parking spots...")
    total_spots = 0
    spot_data = []
    
    for lot_id, large_count, small_count, large_price, small_price in lot_ids:
        # Large spots
        for spot_num in range(1, large_count + 1):
            cursor.execute("""
                INSERT OR IGNORE INTO spots (lot_id, spot_id, type, status, price_per_hour)
                VALUES (?, ?, ?, ?, ?)
            """, (lot_id, spot_num, 'large', 'available', large_price))
            spot_data.append((lot_id, spot_num, 'large'))
            total_spots += 1
        
        # Small spots
        for spot_num in range(large_count + 1, large_count + small_count + 1):
            cursor.execute("""
                INSERT OR IGNORE INTO spots (lot_id, spot_id, type, status, price_per_hour)
                VALUES (?, ?, ?, ?, ?)
            """, (lot_id, spot_num, 'small', 'available', small_price))
            spot_data.append((lot_id, spot_num, 'small'))
            total_spots += 1
    
    conn.commit()
    print(f"   ✅ Created {total_spots} spots")
    
    # Create additional customers
    print("\n5️⃣ Creating additional demo customers...")
    demo_customers = [
        ('Alice Johnson', 'alice.demo@example.com'),
        ('Bob Smith', 'bob.demo@example.com'),
        ('Carol White', 'carol.demo@example.com'),
    ]
    
    customer_ids = [demo_customer_id]
    for name, email in demo_customers:
        try:
            hashed_pwd = generate_password_hash('demo123')
            cursor.execute(
                "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
                (name, email, hashed_pwd, 'customer')
            )
            customer_ids.append(cursor.lastrowid)
        except sqlite3.IntegrityError:
            cursor.execute("SELECT user_id FROM users WHERE email = ?", (email,))
            result = cursor.fetchone()
            if result:
                customer_ids.append(result[0])
    
    conn.commit()
    print(f"   ✅ Total {len(customer_ids)} customers")
    
    # Generate bookings
    print("\n6️⃣ Generating booking history...")
    bookings_created = 0
    now = datetime.now()
    
    for lot_id, large_count, small_count, large_price, small_price in lot_ids:
        lot_spots = [(s[1], s[2]) for s in spot_data if s[0] == lot_id]
        num_bookings = random.randint(50, 120)
        
        for _ in range(num_bookings):
            days_ago = int(random.triangular(0, 90, 10))
            start_date = now - timedelta(days=days_ago)
            
            hour_weights = [1]*6 + [3, 5, 4] + [2]*5 + [1] + [4, 5, 3] + [2]*6
            start_hour = random.choices(range(24), weights=hour_weights)[0]
            start_date = start_date.replace(hour=start_hour, minute=random.randint(0, 59))
            
            duration_hours = random.choices([1, 2, 3, 4, 5, 6, 8], 
                                          weights=[5, 20, 25, 25, 15, 5, 3])[0]
            end_date = start_date + timedelta(hours=duration_hours)
            
            spot_id, spot_type = random.choice(lot_spots)
            price_per_hour = small_price if spot_type == 'small' else large_price
            
            if start_hour in [8, 9, 17, 18]:
                price_per_hour *= random.uniform(1.1, 1.3)
            
            total_cost = price_per_hour * duration_hours
            customer_id = random.choice(customer_ids)
            
            try:
                cursor.execute("""
                    INSERT INTO bookings (user_id, lot_id, spot_id, start_time, end_time,
                                        total_cost, price_per_hour)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (customer_id, lot_id, spot_id,
                      start_date.strftime("%Y-%m-%d %H:%M:%S"),
                      end_date.strftime("%Y-%m-%d %H:%M:%S"),
                      total_cost, price_per_hour))
                bookings_created += 1
            except:
                pass
    
    conn.commit()
    conn.close()
    
    print(f"   ✅ Created {bookings_created} bookings")
    
    print("\n" + "=" * 70)
    print("✅ SETUP COMPLETE!")
    print("=" * 70)
    print("\n📋 DEMO CREDENTIALS:")
    print(f"\n   🏢 Owner: {DEMO_OWNER_EMAIL}")
    print(f"   👤 Customer: {DEMO_CUSTOMER_EMAIL}")
    print(f"   🔑 Password: {DEMO_PASSWORD}")
    print(f"\n   📊 Pre-loaded: 4 lots, {total_spots} spots, {bookings_created} bookings")
    print("\n💡 OTHER USERS:")
    print("   - Register with any other email to create your own data")
    print("   - Your data will be completely separate from demo accounts")
    print("\n🚀 Now run: python app.py")
    print("=" * 70)

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🚀 SMART PARKING - DATABASE SETUP")
    print("=" * 70)
    
    # Initialize demo database with demo accounts
    print("\n📊 DEMO DATABASE (demo.db)")
    print("   - Used by: demo.owner@smartparking.com, demo.customer@smartparking.com")
    print("   - Contains: Pre-loaded lots, spots, and bookings")
    print("   - Safe from wipes: Separate from regular users")
    init_database(DEMO_DB_PATH, "demo.db")
    setup_demo_accounts()
    
    # Initialize regular user database (empty)
    print("\n" + "=" * 70)
    print("\n📊 REGULAR USER DATABASE (parking.db)")
    print("   - Used by: All other registered users")
    print("   - Contains: User-created data only")
    print("   - Can be reset: Without affecting demos")
    init_database(REGULAR_DB_PATH, "parking.db")
    print("   ✅ parking.db initialized (empty, ready for users)")
    
    print("\n" + "=" * 70)
    print("✅ SETUP COMPLETE!")
    print("=" * 70)
    print("\n🗄️  TWO SEPARATE DATABASES:")
    print("   demo.db      → Demo accounts (pre-loaded)")
    print("   parking.db   → Regular users (empty)")
    print("\n🚀 Now run: python app.py")
    print("=" * 70)
