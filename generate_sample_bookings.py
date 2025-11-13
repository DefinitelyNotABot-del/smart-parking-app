"""
Generate sample bookings to populate database for testing analytics
Run this to see the analytics dashboard with real data!
"""
import sqlite3
from datetime import datetime, timedelta
import random

DB_PATH = 'parking.db'

def generate_sample_bookings():
    """Generate sample bookings for existing lots"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get existing lots
    cursor.execute("SELECT lot_id, owner_id FROM lots")
    lots = cursor.fetchall()
    
    if not lots:
        print("❌ No lots found! Please create lots first from owner dashboard.")
        return
    
    # Get existing spots
    cursor.execute("SELECT lot_id, spot_id, type FROM spots")
    spots = cursor.fetchall()
    
    if not spots:
        print("❌ No spots found! Please add spots to your lots first.")
        return
    
    # Get or create sample customers
    cursor.execute("SELECT user_id FROM users WHERE role='customer'")
    customers = cursor.fetchall()
    
    if not customers:
        print("Creating sample customers...")
        sample_customers = [
            ('John Doe', 'john@example.com', 'password123', 'customer'),
            ('Jane Smith', 'jane@example.com', 'password123', 'customer'),
            ('Bob Wilson', 'bob@example.com', 'password123', 'customer'),
            ('Alice Brown', 'alice@example.com', 'password123', 'customer'),
            ('Charlie Davis', 'charlie@example.com', 'password123', 'customer'),
        ]
        for name, email, pwd, role in sample_customers:
            try:
                cursor.execute(
                    "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
                    (name, email, pwd, role)
                )
            except sqlite3.IntegrityError:
                pass  # User already exists
        conn.commit()
        
        cursor.execute("SELECT user_id FROM users WHERE role='customer'")
        customers = cursor.fetchall()
    
    customer_ids = [c[0] for c in customers]
    
    print(f"📊 Generating sample bookings...")
    print(f"   Found {len(lots)} lots, {len(spots)} spots, {len(customers)} customers")
    
    # Generate bookings for the last 60 days
    bookings_created = 0
    now = datetime.now()
    
    for lot_id, owner_id in lots:
        # Get spots for this lot
        lot_spots = [(s[1], s[2]) for s in spots if s[0] == lot_id]
        
        if not lot_spots:
            continue
        
        # Get pricing for this lot
        cursor.execute("SELECT large_price_per_hour, motorcycle_price_per_hour FROM lots WHERE lot_id = ?", (lot_id,))
        pricing = cursor.fetchone()
        large_price = pricing[0] or 50.0
        small_price = pricing[1] or 20.0
        
        # Generate 30-100 bookings per lot
        num_bookings = random.randint(30, 100)
        
        for _ in range(num_bookings):
            # Random date in last 60 days
            days_ago = random.randint(0, 60)
            start_date = now - timedelta(days=days_ago)
            
            # Random time between 6 AM and 10 PM
            start_hour = random.randint(6, 22)
            start_date = start_date.replace(hour=start_hour, minute=random.randint(0, 59))
            
            # Random duration 1-8 hours
            duration_hours = random.uniform(1, 8)
            end_date = start_date + timedelta(hours=duration_hours)
            
            # Random spot
            spot_id, spot_type = random.choice(lot_spots)
            
            # Calculate price
            price_per_hour = small_price if spot_type in ['small', 'motorcycle'] else large_price
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
                pass  # Booking conflict, skip
    
    conn.commit()
    conn.close()
    
    print(f"✅ Created {bookings_created} sample bookings!")
    print(f"📈 Refresh the lot analytics page to see data!")
    print(f"\n💡 Tip: The AI predictions use the trained models + these bookings for better accuracy")

if __name__ == "__main__":
    print("=" * 60)
    print("🎲 SAMPLE DATA GENERATOR")
    print("=" * 60)
    print("This will create realistic bookings for your parking lots")
    print("so you can see the analytics dashboard with actual data.\n")
    
    generate_sample_bookings()
