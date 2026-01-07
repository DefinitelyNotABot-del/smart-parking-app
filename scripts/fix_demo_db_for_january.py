#!/usr/bin/env python3
"""
Fix demo.db for January 2026:
1. Update location names to Bangalore landmarks
2. Shift all booking dates to January 2026
3. Ensure realistic data for "This Month" analytics
"""
import sqlite3
import os
from datetime import datetime, timedelta
import random
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DEMO_DB = os.path.join(REPO_ROOT, 'instance', 'demo.db')

# Bangalore locations with coordinates
BANGALORE_LOCATIONS = {
    1: {
        'location': 'Garuda Mall, Magrath Road',
        'latitude': 12.9716,
        'longitude': 77.6077
    },
    2: {
        'location': 'Kempegowda Airport Terminal',
        'latitude': 13.1986,
        'longitude': 77.7066
    },
    3: {
        'location': 'Orion Mall, Rajajinagar',
        'latitude': 13.0107,
        'longitude': 77.5546
    },
    4: {
        'location': 'Phoenix Marketcity, Whitefield',
        'latitude': 12.9980,
        'longitude': 77.6968
    }
}

def update_locations(cursor):
    """Update lot locations to Bangalore landmarks"""
    print("\n=== Updating Location Names ===")
    for lot_id, data in BANGALORE_LOCATIONS.items():
        cursor.execute("""
            UPDATE lots 
            SET location = ?, latitude = ?, longitude = ?
            WHERE lot_id = ?
        """, (data['location'], data['latitude'], data['longitude'], lot_id))
        print(f"  Lot {lot_id}: {data['location']}")

def shift_bookings_to_january(cursor, target_year=2026, target_month=1):
    """Shift all bookings to January 2026 with realistic distribution"""
    print(f"\n=== Shifting Bookings to {target_month}/{target_year} ===")
    
    # Get current bookings
    cursor.execute("SELECT booking_id, start_time, end_time FROM bookings ORDER BY booking_id")
    bookings = cursor.fetchall()
    
    if not bookings:
        print("  No bookings found to shift!")
        return
    
    now = datetime.now()
    current_day = now.day
    current_hour = now.hour
    
    updated_count = 0
    occupied_count = 0
    
    for booking in bookings:
        booking_id = booking['booking_id']
        old_start = datetime.strptime(booking['start_time'], '%Y-%m-%d %H:%M:%S')
        old_end = datetime.strptime(booking['end_time'], '%Y-%m-%d %H:%M:%S')
        
        # Calculate original duration
        duration = old_end - old_start
        
        # Distribute bookings across the month up to today
        # Some in past (completed), some currently active, some upcoming
        rand_val = random.random()
        
        if rand_val < 0.6:
            # 60% completed bookings (past days)
            new_day = random.randint(1, max(1, current_day - 1))
            new_hour = random.randint(8, 20)
        elif rand_val < 0.85:
            # 25% today's bookings (some completed, some active)
            new_day = current_day
            if random.random() < 0.4:
                # Active now
                new_hour = max(8, current_hour - random.randint(0, 2))
                occupied_count += 1
            else:
                # Completed earlier today
                new_hour = random.randint(8, max(8, current_hour - 2))
        else:
            # 15% upcoming bookings (later today or future days)
            if random.random() < 0.5 and current_hour < 20:
                new_day = current_day
                new_hour = current_hour + random.randint(1, 4)
            else:
                new_day = min(28, current_day + random.randint(1, 5))
                new_hour = random.randint(8, 20)
        
        # Build new timestamps
        try:
            new_start = datetime(target_year, target_month, new_day, new_hour, 
                                random.randint(0, 59), 0)
            new_end = new_start + duration
            
            # Ensure realistic duration (cap at 8 hours)
            if (new_end - new_start).total_seconds() > 8 * 3600:
                new_end = new_start + timedelta(hours=random.uniform(2, 5))
            
            cursor.execute("""
                UPDATE bookings 
                SET start_time = ?, end_time = ?
                WHERE booking_id = ?
            """, (new_start.strftime('%Y-%m-%d %H:%M:%S'), 
                  new_end.strftime('%Y-%m-%d %H:%M:%S'),
                  booking_id))
            updated_count += 1
        except Exception as e:
            print(f"  Error updating booking {booking_id}: {e}")
    
    print(f"  Updated {updated_count} bookings")
    print(f"  ~{occupied_count} currently active bookings")

def add_current_occupancy(cursor, num_occupied=5):
    """Add some currently occupied spots for demo purposes"""
    print(f"\n=== Ensuring {num_occupied} Currently Occupied Spots ===")
    
    now = datetime.now()
    
    # Get available spots
    cursor.execute("""
        SELECT s.lot_id, s.spot_id, s.type, s.price_per_hour
        FROM spots s
        LEFT JOIN bookings b ON s.lot_id = b.lot_id AND s.spot_id = b.spot_id
            AND datetime(b.start_time) <= datetime('now', 'localtime')
            AND datetime(b.end_time) > datetime('now', 'localtime')
        WHERE b.booking_id IS NULL
        LIMIT ?
    """, (num_occupied,))
    
    available = cursor.fetchall()
    
    # Get demo user
    cursor.execute("SELECT user_id FROM users WHERE email LIKE '%demo%' LIMIT 1")
    demo_user = cursor.fetchone()
    user_id = demo_user['user_id'] if demo_user else 1
    
    for spot in available:
        # Create an active booking
        start_time = now - timedelta(hours=random.uniform(0.5, 2))
        end_time = now + timedelta(hours=random.uniform(1, 3))
        duration_hours = (end_time - start_time).total_seconds() / 3600
        price = spot['price_per_hour'] if spot['price_per_hour'] else (30 if spot['type'] == 'small' else 60)
        total_cost = round(price * duration_hours, 2)
        
        cursor.execute("""
            INSERT INTO bookings (lot_id, spot_id, user_id, start_time, end_time, total_cost, price_per_hour)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (spot['lot_id'], spot['spot_id'], user_id,
              start_time.strftime('%Y-%m-%d %H:%M:%S'),
              end_time.strftime('%Y-%m-%d %H:%M:%S'),
              total_cost, price))
        print(f"  Added active booking: Lot {spot['lot_id']} Spot {spot['spot_id']} ({spot['type']})")

def show_summary(cursor):
    """Show summary of demo data"""
    print("\n=== Demo Data Summary ===")
    
    # Locations
    cursor.execute("SELECT lot_id, location FROM lots ORDER BY lot_id")
    print("\nParking Lots:")
    for row in cursor.fetchall():
        print(f"  Lot {row['lot_id']}: {row['location']}")
    
    # Booking stats
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("SELECT COUNT(*) as total FROM bookings")
    total = cursor.fetchone()['total']
    
    cursor.execute("""
        SELECT COUNT(*) as active FROM bookings 
        WHERE datetime(start_time) <= datetime(?) 
        AND datetime(end_time) > datetime(?)
    """, (now_str, now_str))
    active = cursor.fetchone()['active']
    
    cursor.execute("""
        SELECT COUNT(*) as today FROM bookings 
        WHERE date(start_time) = date('now', 'localtime')
    """)
    today = cursor.fetchone()['today']
    
    cursor.execute("""
        SELECT 
            strftime('%Y-%m', start_time) as month,
            COUNT(*) as count,
            SUM(total_cost) as revenue
        FROM bookings
        GROUP BY month
        ORDER BY month DESC
        LIMIT 3
    """)
    print(f"\nBooking Statistics:")
    print(f"  Total bookings: {total}")
    print(f"  Currently active: {active}")
    print(f"  Today's bookings: {today}")
    
    print("\nMonthly Revenue:")
    for row in cursor.fetchall():
        print(f"  {row['month']}: {row['count']} bookings, ₹{row['revenue']:.2f}")

def main():
    apply = '--apply' in sys.argv
    
    if not os.path.exists(DEMO_DB):
        print(f"Error: Demo DB not found at {DEMO_DB}")
        return 1
    
    print(f"Demo DB: {DEMO_DB}")
    print(f"Mode: {'APPLY CHANGES' if apply else 'DRY RUN (use --apply to save)'}")
    
    conn = sqlite3.connect(DEMO_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        update_locations(cursor)
        shift_bookings_to_january(cursor)
        add_current_occupancy(cursor)
        show_summary(cursor)
        
        if apply:
            conn.commit()
            print("\n✅ Changes saved to demo.db")
        else:
            print("\n⚠️  DRY RUN - no changes saved. Use --apply to save.")
            conn.rollback()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        conn.rollback()
        return 1
    finally:
        conn.close()
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
