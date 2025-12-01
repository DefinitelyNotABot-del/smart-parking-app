"""
Generate realistic demo bookings for current month with:
- Some bookings active RIGHT NOW (occupied spots)
- Bookings concentrated in early days of the month
- Realistic durations (1-8 hours, not 49+ hours)
- Realistic prices (₹30-150/hour range)

Usage:
  python scripts/generate_realistic_demo_bookings.py --apply
"""
import argparse
import os
import sqlite3
import random
from datetime import datetime, timedelta
import shutil

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DEMO_DB = os.path.join(REPO_ROOT, 'instance', 'demo.db')
BACKUP_DB = os.path.join(REPO_ROOT, 'instance', 'demo.db.before_realistic.bak')


def format_dt(dt):
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def main(apply=False):
    if not os.path.exists(DEMO_DB):
        print(f"Demo DB not found at {DEMO_DB}")
        raise SystemExit(1)

    print(f"Opening demo DB: {DEMO_DB}")
    if apply:
        print(f"Backing up demo DB to: {BACKUP_DB}")
        shutil.copyfile(DEMO_DB, BACKUP_DB)

    conn = sqlite3.connect(DEMO_DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Get demo owner
    cur.execute("SELECT user_id FROM users WHERE email = 'demo.owner@smartparking.com'")
    owner = cur.fetchone()
    if not owner:
        print("Demo owner not found!")
        return
    owner_id = owner['user_id']

    # Get demo customers
    cur.execute("SELECT user_id FROM users WHERE role = 'customer'")
    customers = [row['user_id'] for row in cur.fetchall()]
    print(f"Found {len(customers)} customers")

    # Get lots owned by demo owner
    cur.execute("SELECT lot_id, location FROM lots WHERE owner_id = ?", (owner_id,))
    lots = cur.fetchall()
    print(f"Found {len(lots)} lots")

    # Get spots per lot
    lot_spots = {}
    for lot in lots:
        cur.execute("SELECT spot_id, type, price_per_hour FROM spots WHERE lot_id = ?", (lot['lot_id'],))
        lot_spots[lot['lot_id']] = [dict(row) for row in cur.fetchall()]
        print(f"  Lot {lot['lot_id']} ({lot['location']}): {len(lot_spots[lot['lot_id']])} spots")

    # Delete existing bookings for demo owner's lots
    lot_ids = [lot['lot_id'] for lot in lots]
    placeholders = ','.join(['?'] * len(lot_ids))
    
    if not apply:
        cur.execute(f"SELECT COUNT(*) as cnt FROM bookings WHERE lot_id IN ({placeholders})", lot_ids)
        existing = cur.fetchone()['cnt']
        print(f"\nWould delete {existing} existing bookings")
    else:
        cur.execute(f"DELETE FROM bookings WHERE lot_id IN ({placeholders})", lot_ids)
        print(f"\nDeleted existing bookings")

    # Current time
    now = datetime.now()
    year = now.year
    month = now.month
    day = now.day
    hour = now.hour

    new_bookings = []

    # Configuration per lot for realistic data
    lot_config = {
        1: {'name': 'Downtown Business District', 'base_price': 50, 'busy_hours': range(8, 20), 'bookings_target': 45},
        2: {'name': 'Airport Terminal Parking', 'base_price': 80, 'busy_hours': range(4, 24), 'bookings_target': 55},
        3: {'name': 'Shopping Mall Complex', 'base_price': 40, 'busy_hours': range(10, 22), 'bookings_target': 35},
        4: {'name': 'Residential Area Hub', 'base_price': 30, 'busy_hours': range(18, 24), 'bookings_target': 40},
    }

    for lot in lots:
        lot_id = lot['lot_id']
        spots = lot_spots[lot_id]
        config = lot_config.get(lot_id, {'base_price': 50, 'busy_hours': range(8, 20), 'bookings_target': 30})
        
        print(f"\nGenerating bookings for Lot {lot_id} ({lot['location']})...")

        # 1. Create ACTIVE bookings (spots occupied RIGHT NOW)
        num_active = random.randint(5, min(15, len(spots) // 10 + 5))
        active_spots = random.sample(spots, num_active)
        
        for spot in active_spots:
            # Started 1-3 hours ago, ends 1-4 hours from now
            hours_ago = random.randint(1, 3)
            duration = random.randint(2, 6)
            start = now - timedelta(hours=hours_ago)
            end = start + timedelta(hours=duration)
            
            price = spot['price_per_hour'] or config['base_price']
            # Add some variance
            price = price * random.uniform(0.9, 1.2)
            total = round(price * duration, 2)
            
            customer = random.choice(customers)
            new_bookings.append({
                'lot_id': lot_id,
                'spot_id': spot['spot_id'],
                'user_id': customer,
                'start_time': format_dt(start),
                'end_time': format_dt(end),
                'price_per_hour': round(price, 2),
                'total_cost': total
            })

        # 2. Create completed bookings for today (earlier today)
        if hour > 6:
            num_today_completed = random.randint(3, 10)
            for _ in range(num_today_completed):
                spot = random.choice(spots)
                # Completed earlier today
                start_hour = random.randint(0, max(0, hour - 3))
                duration = random.randint(1, 4)
                start = datetime(year, month, day, start_hour, random.randint(0, 59), 0)
                end = start + timedelta(hours=duration)
                
                # Make sure it ended before now
                if end > now:
                    end = now - timedelta(minutes=random.randint(10, 60))
                    duration = (end - start).total_seconds() / 3600
                
                if duration > 0:
                    price = spot['price_per_hour'] or config['base_price']
                    price = price * random.uniform(0.85, 1.15)
                    total = round(price * duration, 2)
                    
                    customer = random.choice(customers)
                    new_bookings.append({
                        'lot_id': lot_id,
                        'spot_id': spot['spot_id'],
                        'user_id': customer,
                        'start_time': format_dt(start),
                        'end_time': format_dt(end),
                        'price_per_hour': round(price, 2),
                        'total_cost': total
                    })

        # 3. Create upcoming bookings (later today and tomorrow)
        num_upcoming = random.randint(5, 15)
        for _ in range(num_upcoming):
            spot = random.choice(spots)
            # Starts in 1-36 hours
            hours_ahead = random.randint(1, 36)
            duration = random.randint(1, 6)
            start = now + timedelta(hours=hours_ahead)
            end = start + timedelta(hours=duration)
            
            price = spot['price_per_hour'] or config['base_price']
            price = price * random.uniform(0.9, 1.1)
            total = round(price * duration, 2)
            
            customer = random.choice(customers)
            new_bookings.append({
                'lot_id': lot_id,
                'spot_id': spot['spot_id'],
                'user_id': customer,
                'start_time': format_dt(start),
                'end_time': format_dt(end),
                'price_per_hour': round(price, 2),
                'total_cost': total
            })

        # 4. Fill rest of month with realistic bookings
        remaining = config['bookings_target'] - len([b for b in new_bookings if b['lot_id'] == lot_id])
        for i in range(max(0, remaining)):
            spot = random.choice(spots)
            
            # Spread across days 1-28
            booking_day = random.randint(1, 28)
            booking_hour = random.choice(list(config['busy_hours']))
            duration = random.randint(1, 8)
            
            try:
                start = datetime(year, month, booking_day, booking_hour, random.randint(0, 59), 0)
                end = start + timedelta(hours=duration)
            except ValueError:
                continue
            
            price = spot['price_per_hour'] or config['base_price']
            price = price * random.uniform(0.8, 1.25)
            total = round(price * duration, 2)
            
            customer = random.choice(customers)
            new_bookings.append({
                'lot_id': lot_id,
                'spot_id': spot['spot_id'],
                'user_id': customer,
                'start_time': format_dt(start),
                'end_time': format_dt(end),
                'price_per_hour': round(price, 2),
                'total_cost': total
            })

    print(f"\nTotal new bookings to create: {len(new_bookings)}")

    # Count active bookings (happening right now)
    active_count = sum(1 for b in new_bookings 
                       if datetime.strptime(b['start_time'], '%Y-%m-%d %H:%M:%S') <= now <= datetime.strptime(b['end_time'], '%Y-%m-%d %H:%M:%S'))
    print(f"Active bookings (right now): {active_count}")

    # Show sample
    print("\nSample bookings (first 10):")
    for b in new_bookings[:10]:
        print(f"  Lot {b['lot_id']}, Spot {b['spot_id']}: {b['start_time']} - {b['end_time']}, ₹{b['total_cost']}")

    if not apply:
        print("\nDry run mode. Run with --apply to save changes.")
        conn.close()
        return

    # Insert new bookings
    print("\nInserting bookings...")
    for b in new_bookings:
        cur.execute("""
            INSERT INTO bookings (lot_id, spot_id, user_id, start_time, end_time, price_per_hour, total_cost)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (b['lot_id'], b['spot_id'], b['user_id'], b['start_time'], b['end_time'], b['price_per_hour'], b['total_cost']))

    conn.commit()

    # Verify and show stats
    print("\n--- This Month Stats per Lot ---")
    for lot in lots:
        lot_id = lot['lot_id']
        cur.execute("""
            SELECT
                COUNT(*) as total_bookings,
                SUM(total_cost) as total_revenue,
                AVG(total_cost) as avg_booking_value,
                AVG((julianday(end_time) - julianday(start_time)) * 24) as avg_duration_hours
            FROM bookings
            WHERE lot_id = ?
            AND strftime('%Y-%m', start_time) = strftime('%Y-%m', 'now')
        """, (lot_id,))
        row = cur.fetchone()
        print(f"Lot {lot_id} ({lot['location']}):")
        print(f"  Bookings: {row['total_bookings'] or 0}")
        print(f"  Revenue: ₹{round(row['total_revenue'] or 0, 2)}")
        print(f"  Avg Value: ₹{round(row['avg_booking_value'] or 0, 2)}")
        print(f"  Avg Duration: {round(row['avg_duration_hours'] or 0, 1)}h")

        # Count currently active
        cur.execute("""
            SELECT COUNT(*) as cnt FROM bookings
            WHERE lot_id = ?
            AND datetime(start_time) <= datetime('now')
            AND datetime(end_time) > datetime('now')
        """, (lot_id,))
        active = cur.fetchone()['cnt']
        print(f"  Currently Occupied: {active} spots")

    conn.close()
    print("\n✅ Done! Realistic demo data generated.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true', help='Apply changes (default is dry-run)')
    args = parser.parse_args()
    main(apply=args.apply)
