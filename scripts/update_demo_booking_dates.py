"""
Update bookings in the demo database so they fall in the current month.

This script only touches `instance/demo.db` and will not modify your primary user database.
Usage:
  - Dry-run: python scripts/update_demo_booking_dates.py
  - Apply changes: python scripts/update_demo_booking_dates.py --apply

Behavior:
  - Finds the demo owner (`demo.owner@smartparking.com`) and updates bookings for lots owned by that user.
  - For each booking it preserves the time-of-day and booking duration, but sets the start_date to a day in the current month (1..28).
  - A backup of `instance/demo.db` is saved as `instance/demo.db.bak` before applying changes.

"""
import argparse
import os
import sqlite3
from datetime import datetime, timedelta
import shutil
import subprocess

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DEMO_DB = os.path.join(REPO_ROOT, 'instance', 'demo.db')
BACKUP_DB = os.path.join(REPO_ROOT, 'instance', 'demo.db.bak')
DEMO_OWNER_EMAIL = 'demo.owner@smartparking.com'


def parse_dt(s):
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S.%f"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            pass
    return None


def format_dt(dt):
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def main(apply=False, source_db=None, dest_db=None, git_head=False):
    if not os.path.exists(DEMO_DB):
        # If a custom source was provided, check that
        if source_db and os.path.exists(source_db):
            pass
        else:
            print(f"Demo DB not found at {DEMO_DB}")
        raise SystemExit(1)

    # If git_head requested, export demo.db from HEAD to a temp path
    if git_head:
        git_source = os.path.join(REPO_ROOT, 'instance', 'demo_from_git.db')
        print(f"Exporting committed demo.db from git HEAD to: {git_source}")
        with open(git_source, 'wb') as f:
            subprocess.run(['git', 'show', 'HEAD:instance/demo.db'], check=True, stdout=f)
        source_db = git_source

    if source_db:
        if not os.path.exists(source_db):
            print(f"Source DB not found at {source_db}")
            raise SystemExit(1)
        db_to_open = source_db
    else:
        db_to_open = DEMO_DB

    print(f"Opening demo DB: {db_to_open}")
    if apply and dest_db is None:
        print(f"Backing up demo DB to: {BACKUP_DB}")
        shutil.copyfile(DEMO_DB, BACKUP_DB)

    conn = sqlite3.connect(db_to_open)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Find demo owner ID
    cur.execute("SELECT user_id FROM users WHERE email = ?", (DEMO_OWNER_EMAIL,))
    owner_row = cur.fetchone()
    if not owner_row:
        print(f"Demo owner ({DEMO_OWNER_EMAIL}) not found in demo DB. Aborting.")
        conn.close()
        return
    owner_id = owner_row['user_id']
    print(f"Found demo owner id={owner_id}")

    # Find lots for this owner
    cur.execute("SELECT lot_id FROM lots WHERE owner_id = ?", (owner_id,))
    lots = [row['lot_id'] for row in cur.fetchall()]
    if not lots:
        print(f"No lots found for owner id={owner_id}. Aborting.")
        conn.close()
        return
    print(f"Owner has lots: {lots}")

    # Get bookings for these lots
    placeholders = ','.join(['?'] * len(lots))
    cur.execute(f"SELECT booking_id, start_time, end_time, total_cost, lot_id FROM bookings WHERE lot_id IN ({placeholders}) ORDER BY start_time ASC", lots)
    bookings = cur.fetchall()
    print(f"Found {len(bookings)} bookings across demo owner lots")

    # Current year/month
    now = datetime.now()
    year = now.year
    month = now.month

    updates = []
    for i, b in enumerate(bookings):
        b_id = b['booking_id']
        start_str = b['start_time']
        end_str = b['end_time']
        start_dt = parse_dt(start_str)
        end_dt = parse_dt(end_str)
        if not start_dt or not end_dt:
            print(f"Skipping booking {b_id} due to unparseable dates: start={start_str} end={end_str}")
            continue
        duration = end_dt - start_dt

        # Use day distribution across 1..28 to avoid month overflow
        day = (i % 28) + 1
        # Keep time-of-day
        new_start = datetime(year, month, day, start_dt.hour, start_dt.minute, start_dt.second)
        new_end = new_start + duration

        updates.append((b_id, format_dt(new_start), format_dt(new_end), b['lot_id']))

    if not updates:
        print("No bookings to update.")
        conn.close()
        return

    print('\nSample planned updates (first 5):')
    for u in updates[:5]:
        print(f" - booking_id={u[0]}, lot_id={u[3]}, start={u[1]}, end={u[2]}")

    if not apply:
        print('\nDry run mode - no changes were applied. Run with --apply to actually update demo.db')
        conn.close()
        return

    print('\nApplying updates...')
    for u in updates:
        b_id, new_start_str, new_end_str, lot_id = u
        cur.execute("UPDATE bookings SET start_time = ?, end_time = ? WHERE booking_id = ?", (new_start_str, new_end_str, b_id))

    conn.commit()

    # If the destination path is specified and differs from the source, copy modified db to dest
    if dest_db and os.path.exists(dest_db) and dest_db != db_to_open:
        print(f"Copying updated DB to destination: {dest_db}")
        conn.close()
        shutil.copyfile(db_to_open, dest_db)
        conn = sqlite3.connect(dest_db)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

    # Show analytics per lot to confirm current-month bookings
    for lot_id in lots:
        cur.execute(
            """
            SELECT
                COUNT(*) as total_bookings,
                SUM(total_cost) as total_revenue,
                AVG(total_cost) as avg_booking_value,
                AVG((julianday(end_time) - julianday(start_time)) * 24) as avg_duration_hours
            FROM bookings
            WHERE lot_id = ?
            AND strftime('%Y-%m', start_time) = strftime('%Y-%m', 'now')
            """,
            (lot_id,)
        )
        row = cur.fetchone()
        print(f"\nLot {lot_id} - This month summary: bookings={row['total_bookings'] or 0}, revenue={row['total_revenue'] or 0}, avg_value={round(row['avg_booking_value'] or 0,2)}, avg_duration_hours={round(row['avg_duration_hours'] or 0,2)}")

    conn.close()
    print('\nUpdate complete. Keep a backup at demo.db.bak in the instance folder.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true', help='Apply the changes (default is dry-run)')
    parser.add_argument('--source', help='Source DB to read from (defaults to instance/demo.db)')
    parser.add_argument('--dest', help='Destination DB to write to (defaults to instance/demo.db)')
    parser.add_argument('--git-head', action='store_true', help='Extract demo.db from git HEAD and use that as source')
    args = parser.parse_args()
    main(apply=args.apply, source_db=args.source, dest_db=args.dest, git_head=args.git_head)
