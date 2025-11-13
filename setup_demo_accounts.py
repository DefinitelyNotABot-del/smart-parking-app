"""
Setup Demo Accounts with Pre-generated Data
Run this once to create demo accounts and populate with sample data
"""
import sqlite3
from datetime import datetime, timedelta
import random

DB_PATH = 'parking.db'

# Demo account credentials
DEMO_ACCOUNTS = {
    'owner': {
        'email': 'demo.owner@smartparking.com',
        'password': 'demo123',
        'name': 'Demo Owner Account'
    },
    'customer': {
        'email': 'demo.customer@smartparking.com', 
        'password': 'demo123',
        'name': 'Demo Customer Account'
    }
}

def setup_demo_data():
    """Create demo accounts and populate with comprehensive data"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("=" * 70)
    print("🎯 DEMO ACCOUNT SETUP")
    print("=" * 70)
    
    # Create demo owner account
    print("\n1️⃣ Creating demo owner account...")
    try:
        cursor.execute(
            "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
            (DEMO_ACCOUNTS['owner']['name'], 
             DEMO_ACCOUNTS['owner']['email'],
             DEMO_ACCOUNTS['owner']['password'],  # In production, hash this!
             'owner')
        )
        demo_owner_id = cursor.lastrowid
        print(f"   ✅ Created owner: {DEMO_ACCOUNTS['owner']['email']}")
    except sqlite3.IntegrityError:
        cursor.execute("SELECT user_id FROM users WHERE email = ?", 
                      (DEMO_ACCOUNTS['owner']['email'],))
        demo_owner_id = cursor.fetchone()[0]
        print(f"   ℹ️  Owner already exists: {DEMO_ACCOUNTS['owner']['email']}")
    
    # Create demo customer account
    print("\n2️⃣ Creating demo customer account...")
    try:
        cursor.execute(
            "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
            (DEMO_ACCOUNTS['customer']['name'],
             DEMO_ACCOUNTS['customer']['email'],
             DEMO_ACCOUNTS['customer']['password'],
             'customer')
        )
        demo_customer_id = cursor.lastrowid
        print(f"   ✅ Created customer: {DEMO_ACCOUNTS['customer']['email']}")
    except sqlite3.IntegrityError:
        cursor.execute("SELECT user_id FROM users WHERE email = ?",
                      (DEMO_ACCOUNTS['customer']['email'],))
        demo_customer_id = cursor.fetchone()[0]
        print(f"   ℹ️  Customer already exists: {DEMO_ACCOUNTS['customer']['email']}")
    
    conn.commit()
    
    # Create parking lots for demo owner
    print("\n3️⃣ Creating parking lots for demo owner...")
    demo_lots = [
        ('Downtown Business District', 28.6139, 77.2090, 100, 30, 60.0, 25.0),
        ('Airport Terminal Parking', 28.5562, 77.1000, 150, 50, 80.0, 30.0),
        ('Shopping Mall Complex', 28.5355, 77.3910, 80, 40, 45.0, 20.0),
        ('Residential Area Hub', 28.7041, 77.1025, 60, 35, 35.0, 15.0),
    ]
    
    lot_ids = []
    for location, lat, lng, large_spots, small_spots, large_price, small_price in demo_lots:
        try:
            cursor.execute("""
                INSERT INTO lots (owner_id, location, latitude, longitude, 
                                large_price_per_hour, motorcycle_price_per_hour,
                                large_spots, motorcycle_spots, total_spots, occupied_spots)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (demo_owner_id, location, lat, lng, large_price, small_price,
                  large_spots, small_spots, large_spots + small_spots, 0))
            lot_id = cursor.lastrowid
            lot_ids.append((lot_id, large_spots, small_spots, large_price, small_price))
            print(f"   ✅ Created: {location}")
        except sqlite3.IntegrityError:
            pass
    
    conn.commit()
    
    # Create spots for each lot
    print("\n4️⃣ Creating parking spots...")
    total_spots = 0
    spot_data = []
    
    for lot_id, large_count, small_count, large_price, small_price in lot_ids:
        # Create large spots
        for spot_num in range(1, large_count + 1):
            cursor.execute("""
                INSERT OR IGNORE INTO spots (lot_id, spot_id, type, status, price_per_hour)
                VALUES (?, ?, ?, ?, ?)
            """, (lot_id, spot_num, 'large', 'available', large_price))
            spot_data.append((lot_id, spot_num, 'large'))
            total_spots += 1
        
        # Create small spots
        for spot_num in range(large_count + 1, large_count + small_count + 1):
            cursor.execute("""
                INSERT OR IGNORE INTO spots (lot_id, spot_id, type, status, price_per_hour)
                VALUES (?, ?, ?, ?, ?)
            """, (lot_id, spot_num, 'small', 'available', small_price))
            spot_data.append((lot_id, spot_num, 'small'))
            total_spots += 1
    
    conn.commit()
    print(f"   ✅ Created {total_spots} parking spots")
    
    # Create additional demo customers
    print("\n5️⃣ Creating additional demo customers...")
    demo_customers = [
        ('Alice Johnson', 'alice.demo@example.com', 'demo123'),
        ('Bob Smith', 'bob.demo@example.com', 'demo123'),
        ('Carol White', 'carol.demo@example.com', 'demo123'),
        ('David Brown', 'david.demo@example.com', 'demo123'),
        ('Eve Davis', 'eve.demo@example.com', 'demo123'),
    ]
    
    customer_ids = [demo_customer_id]
    for name, email, pwd in demo_customers:
        try:
            cursor.execute(
                "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
                (name, email, pwd, 'customer')
            )
            customer_ids.append(cursor.lastrowid)
        except sqlite3.IntegrityError:
            cursor.execute("SELECT user_id FROM users WHERE email = ?", (email,))
            result = cursor.fetchone()
            if result:
                customer_ids.append(result[0])
    
    conn.commit()
    print(f"   ✅ Created {len(customer_ids)} demo customers")
    
    # Generate realistic bookings
    print("\n6️⃣ Generating booking history (last 90 days)...")
    bookings_created = 0
    now = datetime.now()
    
    for lot_id, large_count, small_count, large_price, small_price in lot_ids:
        # Get spots for this lot
        lot_spots = [(s[1], s[2]) for s in spot_data if s[0] == lot_id]
        
        # Generate 50-150 bookings per lot
        num_bookings = random.randint(50, 150)
        
        for _ in range(num_bookings):
            # Random date in last 90 days, weighted toward recent
            days_ago = int(random.triangular(0, 90, 10))
            start_date = now - timedelta(days=days_ago)
            
            # Peak hours: 8-10 AM, 5-7 PM get more bookings
            hour_weights = [1]*6 + [3, 5, 4] + [2]*5 + [1] + [4, 5, 3] + [2]*6
            start_hour = random.choices(range(24), weights=hour_weights)[0]
            start_date = start_date.replace(hour=start_hour, minute=random.randint(0, 59))
            
            # Duration: mostly 2-4 hours, some longer
            duration_hours = random.choices(
                [1, 2, 3, 4, 5, 6, 8, 10],
                weights=[5, 20, 25, 25, 15, 5, 3, 2]
            )[0]
            end_date = start_date + timedelta(hours=duration_hours)
            
            # Random spot
            spot_id, spot_type = random.choice(lot_spots)
            
            # Price
            price_per_hour = small_price if spot_type == 'small' else large_price
            # Add some price variation (surge pricing simulation)
            if start_hour in [8, 9, 17, 18]:  # Peak hours
                price_per_hour *= random.uniform(1.1, 1.4)
            total_cost = price_per_hour * duration_hours
            
            # Random customer
            customer_id = random.choice(customer_ids)
            
            try:
                cursor.execute("""
                    INSERT INTO bookings (
                        user_id, lot_id, spot_id,
                        start_time, end_time,
                        total_cost, price_per_hour
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    customer_id, lot_id, spot_id,
                    start_date.strftime("%Y-%m-%d %H:%M:%S"),
                    end_date.strftime("%Y-%m-%d %H:%M:%S"),
                    total_cost, price_per_hour
                ))
                bookings_created += 1
            except sqlite3.IntegrityError:
                pass
    
    conn.commit()
    conn.close()
    
    print(f"   ✅ Created {bookings_created} historical bookings")
    
    print("\n" + "=" * 70)
    print("✅ DEMO SETUP COMPLETE!")
    print("=" * 70)
    print("\n📋 DEMO CREDENTIALS:")
    print(f"\n   🏢 Demo Owner Account:")
    print(f"      Email: {DEMO_ACCOUNTS['owner']['email']}")
    print(f"      Password: {DEMO_ACCOUNTS['owner']['password']}")
    print(f"      - Has 4 parking lots with {total_spots} spots")
    print(f"      - Has {bookings_created} historical bookings")
    print(f"      - Revenue analytics fully populated")
    
    print(f"\n   👤 Demo Customer Account:")
    print(f"      Email: {DEMO_ACCOUNTS['customer']['email']}")
    print(f"      Password: {DEMO_ACCOUNTS['customer']['password']}")
    print(f"      - Can search and book parking spots")
    print(f"      - AI recommendations available")
    
    print("\n💡 OTHER USERS:")
    print("   - Any other email can register and create their own data")
    print("   - Their data is completely separate from demo accounts")
    print("   - They start with empty lots and build their own portfolio")
    
    print("\n🚀 Ready to test! Login with demo credentials to see populated analytics!")
    print("=" * 70)

if __name__ == "__main__":
    setup_demo_data()
