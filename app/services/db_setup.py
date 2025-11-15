import sqlite3

# =============================================================================
# DATABASE SCHEMA CONSTANTS - SINGLE SOURCE OF TRUTH
# =============================================================================
# All database table names and column names are defined here as constants.
# Use these constants throughout the codebase to prevent typos and ensure
# consistency. This prevents issues like owner_id vs user_id mismatches.
#
# NAMING CONVENTION:
#   - Table constants: TABLE_<NAME> (e.g., TABLE_USERS)
#   - Column constants: COL_<TABLE>_<COLUMN> (e.g., COL_USER_ID)
#   - Type constants: SPOT_TYPE_<TYPE>, ROLE_<ROLE>, etc.
# =============================================================================

# --- Table Names ---
TABLE_USERS = 'users'
TABLE_LOTS = 'lots'
TABLE_SPOTS = 'spots'
TABLE_BOOKINGS = 'bookings'

# Column Names - Users Table
COL_USER_ID = 'user_id'
COL_USER_NAME = 'name'
COL_USER_EMAIL = 'email'
COL_USER_PASSWORD_HASH = 'password_hash'
COL_USER_ROLE = 'role'

# Column Names - Lots Table
COL_LOT_ID = 'lot_id'
COL_LOT_USER_ID = 'owner_id'  # Foreign key to users (column is named owner_id in existing DBs)
COL_LOT_LOCATION = 'location'
COL_LOT_LATITUDE = 'latitude'
COL_LOT_LONGITUDE = 'longitude'

# Column Names - Spots Table
COL_SPOT_ID = 'spot_id'
COL_SPOT_LOT_ID = 'lot_id'  # Foreign key to lots
COL_SPOT_TYPE = 'type'
COL_SPOT_STATUS = 'status'
COL_SPOT_BOOKED_BY = 'booked_by_user_id'
COL_SPOT_PRICE = 'price_per_hour'
COL_SPOT_DISPLAY_ORDER = 'display_order'

# Column Names - Bookings Table
COL_BOOKING_ID = 'booking_id'
COL_BOOKING_LOT_ID = 'lot_id'
COL_BOOKING_SPOT_ID = 'spot_id'
COL_BOOKING_USER_ID = 'user_id'
COL_BOOKING_START = 'start_time'
COL_BOOKING_END = 'end_time'
COL_BOOKING_STATUS = 'booking_status'
# COL_BOOKING_CREATED = 'created_at' # Removed as per previous fix

# User Roles
ROLE_CUSTOMER = 'customer'
ROLE_OWNER = 'owner'


def init_db_for_path(db_path, force_reset=False):
    """Creates the database tables for a specific database path."""
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    cursor = db.cursor()

    if force_reset:
        cursor.execute("DROP TABLE IF EXISTS spots")
        cursor.execute("DROP TABLE IF EXISTS lots")
        cursor.execute("DROP TABLE IF EXISTS users")
        cursor.execute("DROP TABLE IF EXISTS bookings")


    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_USERS} (
            {COL_USER_ID} INTEGER PRIMARY KEY AUTOINCREMENT,
            {COL_USER_NAME} TEXT NOT NULL,
            {COL_USER_EMAIL} TEXT NOT NULL UNIQUE,
            {COL_USER_PASSWORD_HASH} TEXT NOT NULL
        )
    """)
    try:
        cursor.execute(f"ALTER TABLE {TABLE_USERS} ADD COLUMN {COL_USER_ROLE} TEXT NOT NULL DEFAULT '{ROLE_CUSTOMER}'")
    except sqlite3.OperationalError:
        db.rollback()
    else:
        db.commit()
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_LOTS} (
            {COL_LOT_ID} INTEGER PRIMARY KEY AUTOINCREMENT,
            {COL_LOT_USER_ID} INTEGER,
            {COL_LOT_LOCATION} TEXT NOT NULL,
            {COL_LOT_LATITUDE} REAL,
            {COL_LOT_LONGITUDE} REAL,
            FOREIGN KEY ({COL_LOT_USER_ID}) REFERENCES {TABLE_USERS} ({COL_USER_ID}),
            UNIQUE({COL_LOT_USER_ID}, {COL_LOT_LOCATION})
        )
    """)
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_SPOTS} (
            {COL_SPOT_ID} INTEGER NOT NULL,
            {COL_SPOT_LOT_ID} INTEGER NOT NULL,
            {COL_SPOT_TYPE} TEXT NOT NULL,
            {COL_SPOT_STATUS} TEXT NOT NULL,
            {COL_SPOT_BOOKED_BY} INTEGER,
            {COL_SPOT_PRICE} REAL DEFAULT 30.0,
            {COL_SPOT_DISPLAY_ORDER} INTEGER DEFAULT 0,
            PRIMARY KEY ({COL_SPOT_LOT_ID}, {COL_SPOT_ID}),
            FOREIGN KEY ({COL_SPOT_LOT_ID}) REFERENCES {TABLE_LOTS} ({COL_LOT_ID}),
            FOREIGN KEY ({COL_SPOT_BOOKED_BY}) REFERENCES {TABLE_USERS} ({COL_USER_ID})
        )
    """)

    try:
        cursor.execute(f"ALTER TABLE {TABLE_SPOTS} ADD COLUMN {COL_SPOT_PRICE} REAL DEFAULT 30.0")
        db.commit()
    except sqlite3.OperationalError:
        db.rollback()

    try:
        cursor.execute(f"ALTER TABLE {TABLE_SPOTS} ADD COLUMN {COL_SPOT_DISPLAY_ORDER} INTEGER DEFAULT 0")
        db.commit()
    except sqlite3.OperationalError:
        db.rollback()

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_BOOKINGS} (
            {COL_BOOKING_ID} INTEGER PRIMARY KEY AUTOINCREMENT,
            {COL_BOOKING_LOT_ID} INTEGER NOT NULL,
            {COL_BOOKING_SPOT_ID} INTEGER NOT NULL,
            {COL_BOOKING_USER_ID} INTEGER NOT NULL,
            {COL_BOOKING_START} TEXT NOT NULL,
            {COL_BOOKING_END} TEXT NOT NULL,
            {COL_SPOT_PRICE} REAL NOT NULL,
            total_cost REAL NOT NULL,
            FOREIGN KEY ({COL_BOOKING_LOT_ID}, {COL_BOOKING_SPOT_ID}) REFERENCES {TABLE_SPOTS} ({COL_SPOT_LOT_ID}, {COL_SPOT_ID}),
            FOREIGN KEY ({COL_BOOKING_USER_ID}) REFERENCES {TABLE_USERS} ({COL_USER_ID})
        )
    """)

    try:
        cursor.execute("ALTER TABLE bookings ADD COLUMN lot_id INTEGER")
        db.commit()
    except sqlite3.OperationalError:
        db.rollback()

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bookings_spot_time ON bookings (spot_id, start_time, end_time)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bookings_user ON bookings (user_id)")

    db.commit()
    db.close()
