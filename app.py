from flask import Flask, render_template, request, jsonify, session, redirect, url_for, g
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
try:
    import google.generativeai as genai
except Exception:
    genai = None
import os
from dotenv import load_dotenv
import json
from flask_socketio import SocketIO
import logging
import click
from datetime import datetime, timedelta
from nlp_parser import parser as nlp_parser
import joblib
import numpy as np
import pandas as pd

# --- App Initialization ---
logging.basicConfig(level=logging.INFO)
load_dotenv()

app = Flask(__name__)
# CRITICAL: Load secret key from environment variable for production
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev_fallback_secret_key_12345')
socketio = SocketIO(app)

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
COL_LOT_USER_ID = 'user_id'  # Foreign key to users
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
COL_BOOKING_CREATED = 'created_at'

# Spot Types
SPOT_TYPE_LARGE = 'large'
SPOT_TYPE_MOTORCYCLE = 'motorcycle'
SPOT_TYPE_CAR = 'car'
SPOT_TYPE_BIKE = 'bike'
SPOT_TYPE_TRUCK = 'truck'

# Spot Status
SPOT_STATUS_AVAILABLE = 'available'
SPOT_STATUS_OCCUPIED = 'occupied'
SPOT_STATUS_MAINTENANCE = 'maintenance'

# User Roles
ROLE_CUSTOMER = 'customer'
ROLE_OWNER = 'owner'

DEFAULT_PRICING = {
    SPOT_TYPE_LARGE: 50.0,
    SPOT_TYPE_CAR: 40.0,
    SPOT_TYPE_MOTORCYCLE: 15.0,
    SPOT_TYPE_BIKE: 15.0,
    SPOT_TYPE_TRUCK: 75.0
}

TIME_FORMAT = "%Y-%m-%dT%H:%M"

# --- Demo Account Configuration ---
DEMO_EMAILS = [
    'demo.owner@smartparking.com',
    'demo.customer@smartparking.com'
]
DEMO_DB_PATH = 'demo.db'
REGULAR_DB_PATH = 'parking.db'

def is_demo_account(email):
    """Check if email is a demo account with pre-generated data"""
    return email.lower() in [e.lower() for e in DEMO_EMAILS]

def get_db_path():
    """Get the appropriate database path based on current user"""
    if session.get('is_demo'):
        return DEMO_DB_PATH
    return REGULAR_DB_PATH

# --- AI Model Loading (Lazy Loading for Azure F1 Free Tier) ---
ML_MODELS_DIR = "data/ml_training"
AI_MODELS = {}

def load_model(model_name):
    """Lazy load ML models on-demand to avoid startup timeout on Azure F1"""
    global AI_MODELS
    
    if model_name in AI_MODELS:
        return AI_MODELS[model_name]
    
    model_files = {
        'occupancy': 'occupancy_model.pkl',
        'pricing': 'pricing_model.pkl',
        'preference': 'preference_model.pkl',
        'preference_scaler': 'preference_scaler.pkl',
        'forecasting': 'forecasting_model.pkl'
    }
    
    if model_name not in model_files:
        return None
    
    try:
        model_path = os.path.join(ML_MODELS_DIR, model_files[model_name])
        if not os.path.exists(model_path):
            app.logger.warning(f"Model file not found: {model_path}")
            return None
            
        model = joblib.load(model_path)
        
        # Force single-threaded prediction to avoid Azure F1 timeout
        # Multiprocessing (n_jobs=-1) causes 30-second worker timeouts
        if hasattr(model, 'n_jobs'):
            model.n_jobs = 1
        
        AI_MODELS[model_name] = model
        app.logger.info(f"✓ Loaded {model_name} model on-demand (single-threaded)")
        return AI_MODELS[model_name]
    except Exception as e:
        app.logger.warning(f"Failed to load {model_name} model: {e}")
        return None

def load_ai_models():
    """Optional: Pre-load all models (used for local development)"""
    # On Azure F1, models are lazy-loaded instead
    app.logger.info("AI models configured for lazy loading (Azure F1 optimization)")

# --- Database Configuration & Management ---
DB_FILE = "data/parking.db"

def get_db():
    """Opens a new database connection if there is none yet for the current application context."""
    if 'db' not in g:
        os.makedirs("data", exist_ok=True)
        # Determine which database to use based on session
        # Demo accounts ALWAYS use demo.db, regular users ALWAYS use parking.db
        try:
            if session.get('is_demo'):
                db_path = DEMO_DB_PATH
            else:
                db_path = REGULAR_DB_PATH
        except RuntimeError:
            # Outside request context (e.g., during app startup)
            db_path = REGULAR_DB_PATH
        
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
        g.db_path = db_path  # Track which DB we're using
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    """Closes the database again at the end of the request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def get_cursor():
    """Gets a cursor from the request-bound database connection."""
    return get_db().cursor()

def init_db_for_path(db_path, force_reset=False):
    """Creates the database tables for a specific database path."""
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    cursor = db.cursor()

    if force_reset:
        cursor.execute("DROP TABLE IF EXISTS spots")
        cursor.execute("DROP TABLE IF EXISTS lots")
        cursor.execute("DROP TABLE IF EXISTS users")

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
            {COL_BOOKING_CREATED} TEXT NOT NULL,
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

def init_db(force_reset=False):
    """Creates the database tables using session-aware db path."""
    db_path = get_db_path() if hasattr(g, 'db_path') else REGULAR_DB_PATH
    init_db_for_path(db_path, force_reset)

@app.cli.command('init-db')
def init_db_command():
    """CLI command to clear the existing data and create new tables."""
    init_db(force_reset=True)
    click.echo('Initialized the database.')


def parse_datetime(value):
    """Parse ISO datetime strings coming from the client."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        try:
            return datetime.strptime(value, TIME_FORMAT)
        except ValueError:
            return None


def format_datetime(dt):
    return dt.strftime(TIME_FORMAT)


def default_booking_window():
    """Return a default start/end (next hour) for search fallback."""
    start = datetime.utcnow().replace(second=0, microsecond=0)
    end = start + timedelta(hours=1)
    return start, end


def get_duration_hours(start_dt, end_dt):
    duration = (end_dt - start_dt).total_seconds() / 3600
    if duration <= 0:
        raise ValueError("End time must be after start time")
    return round(duration, 2)


def calculate_total_cost(price_per_hour, start_dt, end_dt):
    hours = get_duration_hours(start_dt, end_dt)
    return round(price_per_hour * hours, 2)


def get_spot_default_price(spot_type):
    return DEFAULT_PRICING.get(spot_type, DEFAULT_PRICING.get('car', 40.0))


def coerce_price(value, fallback):
    """Convert inputs to a sensible price with graceful fallback."""
    try:
        if value is None or value == "":
            return round(float(fallback), 2)
        price = float(value)
        if price < 0:
            raise ValueError("Price must be non-negative")
        return round(price, 2)
    except (TypeError, ValueError):
        app.logger.warning(f"Invalid price input '{value}', using fallback {fallback}")
        return round(float(fallback), 2)


def spot_is_available(lot_id, spot_id, start_iso, end_iso):
    cursor = get_cursor()
    cursor.execute(
        """
        SELECT COUNT(*) FROM bookings
        WHERE lot_id = ? AND spot_id = ?
          AND NOT (? <= start_time OR ? >= end_time)
        """,
        (lot_id, spot_id, end_iso, start_iso)
    )
    return cursor.fetchone()[0] == 0


def get_future_bookings(lot_id, spot_id, limit=20):
    cursor = get_cursor()
    cursor.execute(
        """
        SELECT b.start_time, b.end_time, b.total_cost
        FROM bookings b
        JOIN spots s ON b.spot_id = s.spot_id AND b.lot_id = s.lot_id
        WHERE s.lot_id = ? AND s.spot_id = ? AND b.end_time >= ?
        ORDER BY b.start_time ASC
        LIMIT ?
        """,
        (lot_id, spot_id, format_datetime(datetime.utcnow()), limit)
    )
    return [dict(row) for row in cursor.fetchall()]


# --- AI Prediction Functions ---

def predict_occupancy(lot_id, target_datetime=None):
    """Predict occupancy rate for a parking lot at a specific time"""
    model = load_model('occupancy')
    if model is None:
        return None
    
    if target_datetime is None:
        target_datetime = datetime.now()
    
    # Get lot capacity
    cursor = get_cursor()
    cursor.execute("SELECT COUNT(*) as capacity FROM spots WHERE lot_id = ?", (lot_id,))
    capacity = cursor.fetchone()['capacity']
    
    # Prepare features
    features = {
        'lot_id': lot_id,
        'hour': target_datetime.hour,
        'day_of_week': target_datetime.weekday(),
        'month': target_datetime.month,
        'day_of_month': target_datetime.day,
        'week_of_year': target_datetime.isocalendar()[1],
        'is_weekend': int(target_datetime.weekday() >= 5),
        'is_holiday': 0,  # Could check calendar
        'is_rush_hour': int((7 <= target_datetime.hour <= 9) or (17 <= target_datetime.hour <= 19)),
        'nearby_event': 0,  # Could check events
        'is_month_start': int(target_datetime.day <= 7),
        'is_month_end': int(target_datetime.day >= 24),
        'weather_encoded': 0,  # Default to clear
        'temperature': 25,  # Default temp
        'total_spots': capacity,
        'hour_sin': np.sin(2 * np.pi * target_datetime.hour / 24),
        'hour_cos': np.cos(2 * np.pi * target_datetime.hour / 24),
        'day_sin': np.sin(2 * np.pi * target_datetime.weekday() / 7),
        'day_cos': np.cos(2 * np.pi * target_datetime.weekday() / 7)
    }
    
    df = pd.DataFrame([features])
    prediction = model.predict(df)[0]
    
    return {
        'occupancy_rate': round(prediction, 1),
        'predicted_available': int(capacity * (1 - prediction/100)),
        'predicted_occupied': int(capacity * (prediction/100)),
        'total_capacity': capacity
    }

def optimize_price(lot_id, spot_type, current_occupancy_rate, base_price):
    """Recommend optimal price based on demand and occupancy"""
    model = load_model('pricing')
    if model is None:
        return {'optimal_price': base_price}
    
    now = datetime.now()
    
    # Encode spot type
    spot_type_mapping = {'car': 0, 'bike': 1, 'large': 2, 'motorcycle': 1, 'truck': 2}
    spot_type_encoded = spot_type_mapping.get(spot_type, 0)
    
    # Determine demand level
    if current_occupancy_rate > 85:
        demand_encoded = 3  # Critical
    elif current_occupancy_rate > 65:
        demand_encoded = 2  # High
    elif current_occupancy_rate > 40:
        demand_encoded = 1  # Medium
    else:
        demand_encoded = 0  # Low
    
    # Estimate metrics
    bookings_last_hour = int(current_occupancy_rate * 0.15)
    competitor_avg = base_price * 1.05  # Assume 5% higher competitors
    conversion_rate = 0.25
    time_until_full = max(0, int((100 - current_occupancy_rate) * 2))
    
    features = {
        'lot_id': lot_id,
        'spot_type_encoded': spot_type_encoded,
        'base_price': base_price,
        'demand_encoded': demand_encoded,
        'occupancy_rate': current_occupancy_rate,
        'bookings_last_hour': bookings_last_hour,
        'competitor_avg_price': competitor_avg,
        'hour': now.hour,
        'day_of_week': now.weekday(),
        'booking_conversion_rate': conversion_rate,
        'time_until_full': time_until_full,
        'hour_sin': np.sin(2 * np.pi * now.hour / 24),
        'hour_cos': np.cos(2 * np.pi * now.hour / 24),
        'day_sin': np.sin(2 * np.pi * now.weekday() / 7),
        'day_cos': np.cos(2 * np.pi * now.weekday() / 7),
        'price_to_competitor_ratio': base_price / competitor_avg
    }
    
    df = pd.DataFrame([features])
    optimal_price = model.predict(df)[0]
    
    return {'optimal_price': round(optimal_price, 2)}

def recommend_spot_for_user(user_id, available_spots):
    """Recommend best parking spot based on user preferences"""
    if 'preference' not in AI_MODELS or not available_spots:
        return available_spots[0] if available_spots else None
    
    cursor = get_cursor()
    
    # Get user's booking history
    cursor.execute("""
        SELECT COUNT(*) as total_bookings,
               AVG(julianday(end_time) - julianday(start_time)) * 24 as avg_duration
        FROM bookings WHERE user_id = ?
    """, (user_id,))
    user_stats = cursor.fetchone()
    
    now = datetime.now()
    scores = []
    
    for spot in available_spots:
        spot_type_mapping = {'car': 0, 'bike': 1, 'large': 2, 'motorcycle': 1, 'truck': 2}
        
        features = {
            'lot_id': spot['lot_id'],
            'spot_type_encoded': spot_type_mapping.get(spot['type'], 0),
            'price_per_hour': spot.get('price_per_hour', DEFAULT_PRICING.get(spot['type'], 40)),
            'distance_from_destination': 500,  # Default assumption
            'hour_of_arrival': now.hour,
            'day_of_week': now.weekday(),
            'time_slot_encoded': 0 if now.hour < 12 else 1 if now.hour < 17 else 2,
            'duration_hours': user_stats['avg_duration'] if user_stats['avg_duration'] else 2,
            'booking_frequency': user_stats['total_bookings'] if user_stats['total_bookings'] else 1,
            'price_sens_encoded': 1,  # Medium sensitivity
            'location_consistency': 0.5,
            'advance_booking_time': 1,
            'preferred_lot': spot['lot_id'],
            'avg_price_paid': DEFAULT_PRICING.get(spot['type'], 40),
            'avg_distance': 500
        }
        
        df = pd.DataFrame([features])
        scaler = load_model('preference_scaler')
        model = load_model('preference')
        if scaler and model:
            df_scaled = scaler.transform(df)
            score = model.predict(df_scaled)[0]
        else:
            score = 0.5  # Default score
        
        scores.append({
            'spot': spot,
            'preference_score': score
        })
    
    # Sort by score descending
    scores.sort(key=lambda x: x['preference_score'], reverse=True)
    return scores[0]['spot']

def forecast_peak_hours(lot_id, hours_ahead=3):
    """Forecast peak occupancy in next N hours"""
    if 'forecasting' not in AI_MODELS:
        return None
    
    cursor = get_cursor()
    cursor.execute("SELECT COUNT(*) as capacity FROM spots WHERE lot_id = ?", (lot_id,))
    capacity = cursor.fetchone()['capacity']
    
    # Get current occupancy
    cursor.execute("""
        SELECT COUNT(*) as occupied 
        FROM spots 
        WHERE lot_id = ? AND status = 'occupied'
    """, (lot_id,))
    current_occupied = cursor.fetchone()['occupied']
    current_occupancy = (current_occupied / capacity * 100) if capacity > 0 else 0
    
    now = datetime.now()
    
    # Build features (simplified - would need historical data for real lag features)
    features = {
        'lot_id': lot_id,
        'hour': now.hour,
        'day_of_week': now.weekday(),
        'week_of_year': now.isocalendar()[1],
        'month': now.month,
        'is_weekend': int(now.weekday() >= 5),
        'is_holiday': 0,
        'is_rush_hour': int((7 <= now.hour <= 9) or (17 <= now.hour <= 19)),
        'special_event_flag': 0,
        'total_spots': capacity,
        'spots_available': capacity - current_occupied,
        'new_bookings_this_hour': 5,
        'bookings_ending_this_hour': 3,
        'avg_duration_this_hour': 2.5,
        'rolling_avg_7days': current_occupancy,
        'rolling_avg_30days': current_occupancy,
        'seasonal_index': 1.0,
        'trend_component': 1.0,
        # Lag features (using current as approximation)
        'occupancy_lag_1h': current_occupancy,
        'occupancy_lag_2h': current_occupancy,
        'occupancy_lag_3h': current_occupancy,
        'occupancy_lag_6h': current_occupancy,
        'occupancy_lag_12h': current_occupancy,
        'occupancy_lag_24h': current_occupancy,
        # Moving averages
        'occupancy_ma_3h': current_occupancy,
        'occupancy_ma_6h': current_occupancy,
        'occupancy_ma_12h': current_occupancy,
        'occupancy_ma_24h': current_occupancy,
        # Changes
        'occupancy_change_1h': 0,
        'occupancy_change_3h': 0,
        'occupancy_ewma': current_occupancy,
        # Cyclical features
        'hour_sin': np.sin(2 * np.pi * now.hour / 24),
        'hour_cos': np.cos(2 * np.pi * now.hour / 24),
        'day_sin': np.sin(2 * np.pi * now.weekday() / 7),
        'day_cos': np.cos(2 * np.pi * now.weekday() / 7),
        'month_sin': np.sin(2 * np.pi * now.month / 12),
        'month_cos': np.cos(2 * np.pi * now.month / 12)
    }
    
    df = pd.DataFrame([features])
    model = load_model('forecasting')
    if model:
        peak_prediction = model.predict(df)[0]
    else:
        peak_prediction = current_occupancy  # Fallback to current
    
    return {
        'current_occupancy': round(current_occupancy, 1),
        'peak_occupancy_next_hours': round(peak_prediction, 1),
        'hours_ahead': hours_ahead,
        'recommendation': 'Book now!' if peak_prediction > 85 else 'Good availability' if peak_prediction < 50 else 'Moderate demand'
    }

# --- Booking Utilities ---
def create_booking(lot_id, spot_id, user_id, start_dt, end_dt, price_per_hour):
    start_iso = format_datetime(start_dt)
    end_iso = format_datetime(end_dt)

    if not spot_is_available(lot_id, spot_id, start_iso, end_iso):
        return None, "Spot is no longer available for that time window."

    total_cost = calculate_total_cost(price_per_hour, start_dt, end_dt)

    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO bookings (lot_id, spot_id, user_id, start_time, end_time, price_per_hour, total_cost, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                lot_id,
                spot_id,
                user_id,
                start_iso,
                end_iso,
                price_per_hour,
                total_cost,
                format_datetime(datetime.utcnow())
            )
        )
        db.commit()
    except Exception as exc:
        app.logger.error(f"Booking insert failed for lot {lot_id}, spot {spot_id}: {exc}")
        db.rollback()
        return None, "Failed to create booking."

    return {
        "booking_id": cursor.lastrowid,
        "lot_id": lot_id,
        "spot_id": spot_id,
        "start_time": start_iso,
        "end_time": end_iso,
        "total_cost": total_cost,
        "price_per_hour": price_per_hour
    }, None

# --- Flask Routes ---
@app.route('/')
def role_page():
    return render_template('role.html')

@app.route('/login')
def login_page():
    if 'role' not in request.args and 'role' not in session:
        return redirect(url_for('role_page'))
    return render_template('index.html')

@app.route('/set-role/<role>')
def set_role(role):
    if role in ['customer', 'owner']:
        session['role'] = role
    return redirect(url_for('login_page', role=role))

@app.route('/customer')
def customer_page():
    if 'user_id' not in session or session.get('role') != 'customer':
        return redirect(url_for('role_page'))
    return render_template('customer.html')

@app.route('/owner')
def owner_page():
    if 'user_id' not in session or session.get('role') != 'owner':
        return redirect(url_for('role_page'))
    return render_template('owner.html')

@app.route('/owner/lot/<int:lot_id>')
def lot_spots_page(lot_id):
    if 'user_id' not in session or session.get('role') != 'owner':
        return redirect(url_for('role_page'))
    return render_template('lot_spots.html')

@app.route('/api/customer/bookings')
def get_customer_bookings():
    user_id = session.get('user_id')
    if not user_id or session.get('role') != 'customer':
        return jsonify({"message": "Unauthorized"}), 401

    cursor = get_cursor()
    cursor.execute(
        """
        SELECT b.booking_id, b.lot_id, b.spot_id, s.type, l.location, b.start_time, b.end_time,
               b.total_cost, b.price_per_hour
        FROM bookings b
        JOIN spots s ON b.lot_id = s.lot_id AND b.spot_id = s.spot_id
        JOIN lots l ON s.lot_id = l.lot_id
        WHERE b.user_id = ?
        ORDER BY b.start_time DESC
        """,
        (user_id,)
    )

    bookings = []
    for row in cursor.fetchall():
        booking = dict(row)
        booking['start_time'] = row['start_time']
        booking['end_time'] = row['end_time']
        bookings.append(booking)

    return jsonify(bookings)

@app.route('/api/register', methods=['POST'])
def register_user():
    data = request.get_json()
    name, email, password, role = data.get('name'), data.get('email'), data.get('password'), data.get('role', 'customer')

    if not name or not email or not password:
        return jsonify({"message": "Missing required fields"}), 400
    
    # PREVENT signup with demo account emails
    if is_demo_account(email):
        return jsonify({"message": "Cannot sign up with demo account email. Demo accounts are pre-created."}), 403
    
    # Validate role
    if role not in ['customer', 'owner']:
        role = 'customer'

    hashed_password = generate_password_hash(password)
    sql = f"INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)"

    try:
        # ALWAYS use parking.db for new signups (never demo.db)
        conn = sqlite3.connect(REGULAR_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(sql, (name, email, hashed_password, role))
        conn.commit()
        conn.close()
        return jsonify({"message": "User registered successfully"})
    except sqlite3.IntegrityError:
        return jsonify({"message": "Email already exists"}), 400
    except Exception as e:
        return jsonify({"message": f"Registration failed: {str(e)}"}), 500

@app.route('/api/login', methods=['POST'])
def login_user():
    data = request.get_json()
    email, password, requested_role = data.get('email'), data.get('password'), data.get('role')

    if not email or not password:
        return jsonify({"message": "Missing required fields"}), 400

    # Clear any existing session to prevent demo/user confusion
    session.clear()

    # Check if this is a demo account FIRST - determines which DB to use
    is_demo = is_demo_account(email)
    
    # Route to appropriate database based on email
    db_path = DEMO_DB_PATH if is_demo else REGULAR_DB_PATH
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'], session['name'] = user['user_id'], user['name']
            session['role'] = requested_role if requested_role in ['customer', 'owner'] else user.get('role', 'customer')
            session['is_demo'] = is_demo  # Track if demo account for DB routing
            session['email'] = email  # Store email for DB routing
            
            if session['is_demo']:
                app.logger.info(f"✓ Demo account logged in: {email} (using demo.db)")
            else:
                app.logger.info(f"✓ Regular user logged in: {email} (using parking.db)")
            
            return jsonify({
                "message": "Login successful", 
                "redirect": url_for(f'{session["role"]}_page'),
                "is_demo": session['is_demo']
            })
        else:
            return jsonify({"message": "Invalid email or password"}), 401
    except Exception as e:
        app.logger.error(f"Login error: {e}")
        return jsonify({"message": "Login failed. Please try again."}), 500

@app.route('/switch-role/<new_role>')
def switch_role(new_role):
    if 'user_id' not in session:
        return redirect(url_for('role_page'))
    
    if new_role in ['customer', 'owner']:
        if new_role == 'owner':
            cursor = get_cursor()
            cursor.execute(f"SELECT COUNT(*) FROM lots WHERE user_id = ?", (session['user_id'],))
            if cursor.fetchone()[0] == 0:
                return redirect(url_for('customer_page'))
        session['role'] = new_role
        return redirect(url_for(f'{new_role}_page'))
    
    return redirect(url_for('customer_page'))

@app.route('/api/me')
def get_me():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"message": "Unauthorized"}), 401
    
    cursor = get_cursor()
    cursor.execute(f"SELECT COUNT(*) FROM lots WHERE user_id = ?", (user_id,))
    lot_count = cursor.fetchone()[0]
    
    return jsonify({'name': session.get('name'), 'role': session.get('role'), 'is_owner': lot_count > 0})

@app.route('/api/logout')
def logout_user():
    session.clear()
    return jsonify({"message": "Logout successful"})

@app.route('/api/debug/session')
def debug_session():
    """Debug endpoint to check current session state"""
    return jsonify({
        "user_id": session.get('user_id'),
        "name": session.get('name'),
        "email": session.get('email'),
        "role": session.get('role'),
        "is_demo": session.get('is_demo'),
        "database": DEMO_DB_PATH if session.get('is_demo') else REGULAR_DB_PATH
    })

@app.route('/api/smart-search', methods=['POST'])
def smart_search_route():
    """Natural language parking search with time-based availability and pricing."""
    payload = request.get_json() or {}
    user_request = (payload.get('user_request') or '').strip()
    requested_start = payload.get('start_time')
    requested_end = payload.get('end_time')

    app.logger.info(f"Smart search request: '{user_request}' {requested_start=} {requested_end=}")

    if not user_request:
        return jsonify({"message": "Please enter a search query"}), 400

    start_dt = parse_datetime(requested_start)
    end_dt = parse_datetime(requested_end)
    if not start_dt or not end_dt or end_dt <= start_dt:
        start_dt, end_dt = default_booking_window()
    start_iso = format_datetime(start_dt)
    end_iso = format_datetime(end_dt)

    cursor = get_cursor()
    cursor.execute(
        """
        SELECT s.spot_id, s.type, s.price_per_hour, l.location, l.latitude, l.longitude, l.lot_id
        FROM spots s
        JOIN lots l ON s.lot_id = l.lot_id
        ORDER BY s.spot_id ASC
        """
    )

    available_spots = []
    for row in cursor.fetchall():
        if spot_is_available(row['lot_id'], row['spot_id'], start_iso, end_iso):
            available_spots.append({
                'spot_id': str(row['spot_id']),
                'location': row['location'],
                'type': row['type'],
                'latitude': row['latitude'],
                'longitude': row['longitude'],
                'price_per_hour': row['price_per_hour'],
                'lot_id': row['lot_id']
            })

    app.logger.info(f"Found {len(available_spots)} time-available spots")

    if not available_spots:
        return jsonify({
            "message": "No parking spots available for the selected time window.",
            "start_time": start_iso,
            "end_time": end_iso
        }), 404

    result = nlp_parser.find_best_match(user_request, available_spots)
    app.logger.info(f"NLP match result: {result}")

    if 'error' in result:
        result['start_time'] = start_iso
        result['end_time'] = end_iso
        return jsonify(result), 404

    selected_spot_id = int(result['spot_id'])
    selected_spot = next((spot for spot in available_spots if int(spot['spot_id']) == selected_spot_id), None)
    if not selected_spot:
        return jsonify({
            "message": "Matching spot not available for the requested window. Please try a different time."}), 404

    price_per_hour = selected_spot['price_per_hour'] or get_spot_default_price(selected_spot['type'])
    total_cost = calculate_total_cost(price_per_hour, start_dt, end_dt)
    lot_id = selected_spot['lot_id']

    result.update({
        'price_per_hour': price_per_hour,
        'estimated_cost': total_cost,
        'start_time': start_iso,
        'end_time': end_iso,
        'duration_hours': get_duration_hours(start_dt, end_dt),
        'lot_id': lot_id,
        'bookings': get_future_bookings(lot_id, selected_spot_id)
    })

    # Provide top alternatives for the UI timeline/visualization
    alternatives = []
    for spot in available_spots:
        if int(spot['spot_id']) == selected_spot_id:
            continue
        alternatives.append({
            'spot_id': spot['spot_id'],
            'location': spot['location'],
            'type': spot['type'],
            'price_per_hour': spot['price_per_hour'],
            'lot_id': spot['lot_id'],
            'bookings': get_future_bookings(spot['lot_id'], int(spot['spot_id']), limit=5)
        })
        if len(alternatives) >= 4:
            break

    result['alternatives'] = alternatives
    result['available_spots_count'] = len(available_spots)

    return jsonify(result)

@app.route('/api/book-spot', methods=['POST'])
def book_spot_route():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"message": "Unauthorized"}), 401

    payload = request.get_json() or {}
    spot_id = payload.get('spot_id')
    start_dt = parse_datetime(payload.get('start_time'))
    end_dt = parse_datetime(payload.get('end_time'))

    if not spot_id or not start_dt or not end_dt:
        return jsonify({"message": "Missing booking parameters."}), 400

    if end_dt <= start_dt:
        return jsonify({"message": "End time must be after start time."}), 400

    lot_id = payload.get('lot_id')
    if not lot_id:
        return jsonify({"message": "Missing lot_id parameter."}), 400

    cursor = get_cursor()
    cursor.execute("SELECT price_per_hour, type FROM spots WHERE lot_id = ? AND spot_id = ?", (lot_id, spot_id))
    spot_row = cursor.fetchone()
    if not spot_row:
        return jsonify({"message": "Spot not found."}), 404

    price_per_hour = spot_row['price_per_hour'] or get_spot_default_price(spot_row['type'])
    booking, error = create_booking(int(lot_id), int(spot_id), user_id, start_dt, end_dt, price_per_hour)
    if error:
        return jsonify({"message": error}), 409

    socketio.emit('status_change', {
        'lot_id': lot_id,
        'spot_id': spot_id,
        'status': 'booked',
        'start_time': booking['start_time'],
        'end_time': booking['end_time']
    })

    return jsonify({
        "message": "Booking confirmed!",
        "booking": booking
    })

@app.route('/api/end-parking', methods=['POST'])
def end_parking_route():
    """Legacy endpoint retained for compatibility."""
    return jsonify({
        "message": "Bookings now end automatically when the reserved time finishes. No manual action needed."
    }), 410

@app.route('/api/lots', methods=['GET'])
def get_lots():
    user_id = session.get('user_id')
    if not user_id or session.get('role') != 'owner':
        return jsonify({"message": "Unauthorized"}), 401

    cursor = get_cursor()
    cursor.execute(f"SELECT * FROM lots WHERE user_id = ?", (user_id,))
    lots = [dict(row) for row in cursor.fetchall()]
    now_iso = format_datetime(datetime.utcnow())
    for lot in lots:
        cursor.execute(
            "SELECT spot_id, type, price_per_hour FROM spots WHERE lot_id = ?",
            (lot['lot_id'],)
        )
        spot_rows = cursor.fetchall()
        lot['total_spots'] = len(spot_rows)
        type_counts = {}
        price_groups = {}
        prices = []
        for row in spot_rows:
            type_counts[row['type']] = type_counts.get(row['type'], 0) + 1
            normalized_price = coerce_price(row['price_per_hour'], get_spot_default_price(row['type']))
            prices.append(normalized_price)
            price_groups.setdefault(row['type'], []).append(normalized_price)
        lot['spots'] = type_counts
        lot['average_price_per_hour'] = round(sum(prices) / len(prices), 2) if prices else 0
        lot['price_by_type'] = {
            spot_type: round(sum(values) / len(values), 2)
            for spot_type, values in price_groups.items()
        }

        cursor.execute(
            """
            SELECT COUNT(*) FROM bookings b
            JOIN spots s ON b.spot_id = s.spot_id
            WHERE s.lot_id = ? AND ? BETWEEN b.start_time AND b.end_time
            """,
            (lot['lot_id'], now_iso)
        )
        lot['occupied_spots'] = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT COUNT(*) FROM bookings b
            JOIN spots s ON b.spot_id = s.spot_id
            WHERE s.lot_id = ? AND b.start_time >= ?
            """,
            (lot['lot_id'], now_iso)
        )
        lot['upcoming_bookings'] = cursor.fetchone()[0]
    
    response = jsonify(lots)
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response

@app.route('/api/lot', methods=['POST'])
def create_lot():
    user_id = session.get('user_id')
    if not user_id: return jsonify({"message": "Unauthorized"}), 401

    data = request.get_json()
    db = get_db()
    cursor = db.cursor()
    
    sql = f"INSERT INTO lots (user_id, location, latitude, longitude) VALUES (?, ?, ?, ?)"
    params = (user_id, data.get('location'), data.get('latitude'), data.get('longitude'))
    
    cursor.execute(sql, params)
    lot_id = cursor.lastrowid

    large_price = coerce_price(
        data.get('large_price_per_hour'),
        get_spot_default_price('large')
    )
    motorcycle_price = coerce_price(
        data.get('motorcycle_price_per_hour'),
        get_spot_default_price('motorcycle')
    )
    large_total = int(data.get('large_spots') or 0)
    motorcycle_total = int(data.get('motorcycle_spots') or 0)

    # Create spots with per-lot IDs
    spot_num = 1
    for i in range(large_total):
        cursor.execute(
            "INSERT INTO spots (lot_id, spot_id, type, status, price_per_hour) VALUES (?, ?, ?, ?, ?)",
            (lot_id, spot_num, 'large', 'available', large_price)
        )
        spot_num += 1
    for i in range(motorcycle_total):
        cursor.execute(
            "INSERT INTO spots (lot_id, spot_id, type, status, price_per_hour) VALUES (?, ?, ?, ?, ?)",
            (lot_id, spot_num, 'motorcycle', 'available', motorcycle_price)
        )
        spot_num += 1

    db.commit()
    return jsonify({"message": "Lot created successfully", "lot_id": lot_id})

@app.route('/api/lot/<int:lot_id>', methods=['GET'])
def get_lot(lot_id):
    user_id = session.get('user_id')
    if not user_id: return jsonify({"message": "Unauthorized"}), 401

    cursor = get_cursor()
    cursor.execute(f"SELECT * FROM lots WHERE lot_id = ? AND user_id = ?", (lot_id, user_id))
    lot = cursor.fetchone()
    if not lot: return jsonify({"message": "Lot not found or unauthorized"}), 404
    
    lot = dict(lot)
    cursor.execute(f"SELECT spot_id, type, status, price_per_hour FROM spots WHERE lot_id = ? ORDER BY spot_id ASC", (lot_id,))
    spots = []
    for row in cursor.fetchall():
        spot = dict(row)
        spot['bookings'] = get_future_bookings(lot_id, row['spot_id'])
        spots.append(spot)
    lot['spots'] = spots
    lot['total_spots'] = len(lot['spots'])
    return jsonify(lot)

@app.route('/api/lot/<int:lot_id>', methods=['PUT'])
def update_lot(lot_id):
    user_id = session.get('user_id')
    if not user_id: return jsonify({"message": "Unauthorized"}), 401

    db = get_db()
    cursor = db.cursor()
    cursor.execute(f"SELECT user_id FROM lots WHERE lot_id = ?", (lot_id,))
    lot_owner = cursor.fetchone()
    if not lot_owner or lot_owner['user_id'] != user_id:
        return jsonify({"message": "Unauthorized to update this lot"}), 403

    data = request.get_json()
    params = (data.get('location'), data.get('latitude'), data.get('longitude'), lot_id)
    cursor.execute(f"UPDATE lots SET location = ?, latitude = ?, longitude = ? WHERE lot_id = ?", params)

    cursor.execute(f"SELECT spot_id FROM spots WHERE lot_id = ?", (lot_id,))
    existing_spots = [row['spot_id'] for row in cursor.fetchall()]
    for spot_id_value in existing_spots:
        cursor.execute("DELETE FROM bookings WHERE spot_id = ?", (spot_id_value,))

    cursor.execute(f"DELETE FROM spots WHERE lot_id = ?", (lot_id,))

    large_price = coerce_price(
        data.get('large_price_per_hour'),
        get_spot_default_price('large')
    )
    motorcycle_price = coerce_price(
        data.get('motorcycle_price_per_hour'),
        get_spot_default_price('motorcycle')
    )
    large_total = int(data.get('large_spots') or 0)
    motorcycle_total = int(data.get('motorcycle_spots') or 0)

    # Create spots with per-lot IDs
    spot_num = 1
    for i in range(large_total):
        cursor.execute(
            "INSERT INTO spots (lot_id, spot_id, type, status, price_per_hour) VALUES (?, ?, ?, ?, ?)",
            (lot_id, spot_num, 'large', 'available', large_price)
        )
        spot_num += 1
    for i in range(motorcycle_total):
        cursor.execute(
            "INSERT INTO spots (lot_id, spot_id, type, status, price_per_hour) VALUES (?, ?, ?, ?, ?)",
            (lot_id, spot_num, 'motorcycle', 'available', motorcycle_price)
        )
        spot_num += 1

    db.commit()
    return jsonify({"message": "Lot updated successfully"})

@app.route('/api/lot/<int:lot_id>', methods=['DELETE'])
def delete_lot(lot_id):
    user_id = session.get('user_id')
    if not user_id: return jsonify({"message": "Unauthorized"}), 401

    db = get_db()
    cursor = db.cursor()
    cursor.execute(f"SELECT user_id FROM lots WHERE lot_id = ?", (lot_id,))
    lot_owner = cursor.fetchone()
    if not lot_owner or lot_owner['user_id'] != user_id:
        return jsonify({"message": "Unauthorized to delete this lot"}), 403

    cursor.execute(f"SELECT spot_id FROM spots WHERE lot_id = ?", (lot_id,))
    spot_ids = [row['spot_id'] for row in cursor.fetchall()]
    for spot_id_value in spot_ids:
        cursor.execute("DELETE FROM bookings WHERE spot_id = ?", (spot_id_value,))

    cursor.execute(f"DELETE FROM spots WHERE lot_id = ?", (lot_id,))
    cursor.execute(f"DELETE FROM lots WHERE lot_id = ?", (lot_id,))
    db.commit()
    return jsonify({"message": "Lot deleted successfully"})

# Spot CRUD endpoints
@app.route('/api/lot/<int:lot_id>/spot', methods=['POST'])
def add_spot(lot_id):
    user_id = session.get('user_id')
    if not user_id: 
        return jsonify({"message": "Unauthorized"}), 401

    db = get_db()
    cursor = db.cursor()
    
    # Verify lot ownership
    cursor.execute(f"SELECT user_id FROM lots WHERE lot_id = ?", (lot_id,))
    lot_owner = cursor.fetchone()
    if not lot_owner or lot_owner['user_id'] != user_id:
        return jsonify({"message": "Unauthorized to add spots to this lot"}), 403

    data = request.get_json()
    spot_type = (data.get('type') or 'car').lower()
    spot_status = data.get('status', 'available')
    price_per_hour = data.get('price_per_hour')

    if spot_type == 'small':
        spot_type = 'motorcycle'

    price_per_hour = coerce_price(price_per_hour, get_spot_default_price(spot_type))

    # Get next spot_id for this lot
    cursor.execute("SELECT MAX(spot_id) FROM spots WHERE lot_id = ?", (lot_id,))
    max_spot = cursor.fetchone()[0]
    next_spot_id = (max_spot or 0) + 1

    cursor.execute(
        f"INSERT INTO spots (lot_id, spot_id, type, status, price_per_hour) VALUES (?, ?, ?, ?, ?)",
        (lot_id, next_spot_id, spot_type, spot_status, price_per_hour)
    )
    db.commit()
    
    socketio.emit('status_change', {'lot_id': lot_id, 'action': 'spot_added'})
    return jsonify({
        "message": "Spot added successfully",
        "spot_id": next_spot_id,
        "price_per_hour": price_per_hour
    })

@app.route('/api/lot/<int:lot_id>/spot/<int:spot_id>', methods=['PUT'])
def update_spot(lot_id, spot_id):
    user_id = session.get('user_id')
    if not user_id: 
        return jsonify({"message": "Unauthorized"}), 401

    db = get_db()
    cursor = db.cursor()
    
    # Verify lot ownership
    cursor.execute(f"SELECT user_id FROM lots WHERE lot_id = ?", (lot_id,))
    lot_owner = cursor.fetchone()
    if not lot_owner or lot_owner['user_id'] != user_id:
        return jsonify({"message": "Unauthorized to update spots in this lot"}), 403

    data = request.get_json()

    cursor.execute(
        "SELECT type, status FROM spots WHERE lot_id = ? AND spot_id = ?",
        (lot_id, spot_id)
    )
    existing_spot = cursor.fetchone()
    if not existing_spot:
        return jsonify({"message": "Spot not found"}), 404

    spot_type = data.get('type', existing_spot['type'])
    spot_status = data.get('status', existing_spot['status'] or 'available')
    price_per_hour = data.get('price_per_hour')

    if spot_type == 'small':
        spot_type = 'motorcycle'

    if not spot_type:
        spot_type = existing_spot['type']

    price_per_hour = coerce_price(price_per_hour, get_spot_default_price(spot_type))

    cursor.execute(
        f"UPDATE spots SET type = ?, status = ?, price_per_hour = ? WHERE lot_id = ? AND spot_id = ?",
        (spot_type, spot_status, price_per_hour, lot_id, spot_id)
    )
    db.commit()
    
    socketio.emit('status_change', {'lot_id': lot_id, 'spot_id': spot_id, 'action': 'spot_updated'})
    return jsonify({
        "message": "Spot updated successfully",
        "price_per_hour": price_per_hour
    })

@app.route('/api/lot/<int:lot_id>/spot/<int:spot_id>', methods=['DELETE'])
def delete_spot(lot_id, spot_id):
    user_id = session.get('user_id')
    if not user_id: 
        return jsonify({"message": "Unauthorized"}), 401

    db = get_db()
    cursor = db.cursor()
    
    # Verify lot ownership
    cursor.execute(f"SELECT user_id FROM lots WHERE lot_id = ?", (lot_id,))
    lot_owner = cursor.fetchone()
    if not lot_owner or lot_owner['user_id'] != user_id:
        return jsonify({"message": "Unauthorized to delete spots in this lot"}), 403

    cursor.execute(f"DELETE FROM bookings WHERE lot_id = ? AND spot_id = ?", (lot_id, spot_id))
    cursor.execute(f"DELETE FROM spots WHERE lot_id = ? AND spot_id = ?", (lot_id, spot_id))
    db.commit()
    
    socketio.emit('status_change', {'lot_id': lot_id, 'spot_id': spot_id, 'action': 'spot_deleted'})
    return jsonify({"message": "Spot deleted successfully"})

@app.route('/api/lot/<int:lot_id>/bookings', methods=['GET'])
def get_lot_bookings(lot_id):
    user_id = session.get('user_id')
    if not user_id or session.get('role') != 'owner':
        return jsonify({"message": "Unauthorized"}), 401

    cursor = get_cursor()
    cursor.execute("SELECT user_id FROM lots WHERE lot_id = ?", (lot_id,))
    lot_row = cursor.fetchone()
    if not lot_row or lot_row['user_id'] != user_id:
        return jsonify({"message": "Unauthorized"}), 403

    cursor.execute(
        """
        SELECT b.booking_id, b.spot_id, b.start_time, b.end_time, b.total_cost, b.price_per_hour,
               u.name as customer_name
        FROM bookings b
        JOIN users u ON b.user_id = u.user_id
        WHERE b.start_time >= ? AND b.spot_id IN (
            SELECT spot_id FROM spots WHERE lot_id = ?
        )
        ORDER BY b.start_time ASC
        """,
        (format_datetime(datetime.utcnow() - timedelta(days=1)), lot_id)
    )

    bookings = [dict(row) for row in cursor.fetchall()]
    return jsonify(bookings)

@app.route('/api/validate-booking/<spot_id>')
def validate_booking(spot_id):
    user_id = session.get('user_id')
    if not user_id: return jsonify({"valid": False}), 401

    cursor = get_cursor()
    now_iso = format_datetime(datetime.utcnow())
    cursor.execute(
        """
        SELECT COUNT(*) FROM bookings
        WHERE spot_id = ? AND user_id = ? AND ? BETWEEN start_time AND end_time
        """,
        (spot_id, user_id, now_iso)
    )
    is_valid = cursor.fetchone()[0] > 0

    return jsonify({"valid": is_valid})

@app.route('/api/reset-database', methods=['POST'])
def reset_database():
    if os.environ.get('FLASK_ENV') == 'development':
        init_db(force_reset=True)
        return jsonify({"message": "Database has been reset."})
    else:
        return jsonify({"message": "This action is not allowed in the current environment."}), 403

@app.route('/health')
def health_check():
    """Health check endpoint for Azure"""
    return jsonify({
        "status": "healthy",
        "database": "connected" if os.path.exists(DB_FILE) else "not_initialized",
        "nlp_parser": "local_rule_based"
    })

# Gemini API test endpoint removed - not using external AI APIs
# All AI features now use local ML models (scikit-learn)

# ==================== AI PREDICTION API ENDPOINTS ====================

@app.route('/api/ai/predict-occupancy/<int:lot_id>', methods=['GET'])
def api_predict_occupancy(lot_id):
    """Predict occupancy for a parking lot"""
    try:
        target_time_str = request.args.get('time')
        target_time = datetime.fromisoformat(target_time_str) if target_time_str else None
        
        prediction = predict_occupancy(lot_id, target_time)
        
        if prediction is None:
            return jsonify({"error": "AI model not available"}), 503
        
        return jsonify({
            "success": True,
            "lot_id": lot_id,
            "prediction": prediction,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        app.logger.error(f"Occupancy prediction error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/ai/optimize-price', methods=['POST'])
def api_optimize_price():
    """Get optimal price recommendation"""
    try:
        data = request.get_json()
        lot_id = data.get('lot_id')
        spot_type = data.get('spot_type', 'car')
        current_occupancy = data.get('current_occupancy', 50)
        base_price = data.get('base_price', DEFAULT_PRICING.get(spot_type, 40))
        
        optimal_price = optimize_price(lot_id, spot_type, current_occupancy, base_price)
        
        return jsonify({
            "success": True,
            "base_price": base_price,
            "optimal_price": optimal_price,
            "price_change_percent": round(((optimal_price - base_price) / base_price) * 100, 1),
            "recommendation": "Surge pricing" if optimal_price > base_price * 1.2 else "Discount pricing" if optimal_price < base_price * 0.9 else "Standard pricing"
        })
    except Exception as e:
        app.logger.error(f"Price optimization error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/ai/recommend-spot', methods=['POST'])
def api_recommend_spot():
    """Recommend best spot for user based on preferences"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        data = request.get_json()
        available_spots = data.get('available_spots', [])
        
        if not available_spots:
            return jsonify({"error": "No available spots provided"}), 400
        
        recommended = recommend_spot_for_user(user_id, available_spots)
        
        return jsonify({
            "success": True,
            "recommended_spot": recommended,
            "reason": "Based on your booking history and preferences"
        })
    except Exception as e:
        app.logger.error(f"Spot recommendation error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/ai/forecast/<int:lot_id>', methods=['GET'])
def api_forecast_peak(lot_id):
    """Forecast peak hours for a parking lot"""
    try:
        hours_ahead = int(request.args.get('hours', 3))
        
        forecast = forecast_peak_hours(lot_id, hours_ahead)
        
        if forecast is None:
            return jsonify({"error": "AI model not available"}), 503
        
        return jsonify({
            "success": True,
            "lot_id": lot_id,
            "forecast": forecast,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        app.logger.error(f"Forecast error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/ai/status', methods=['GET'])
def api_ai_status():
    """Check AI models status"""
    return jsonify({
        "ai_enabled": len(AI_MODELS) > 0,
        "models_loaded": list(AI_MODELS.keys()),
        "features": {
            "occupancy_prediction": 'occupancy' in AI_MODELS,
            "price_optimization": 'pricing' in AI_MODELS,
            "user_preferences": 'preference' in AI_MODELS and 'preference_scaler' in AI_MODELS,
            "time_series_forecasting": 'forecasting' in AI_MODELS
        }
    })

@app.route('/api/lot/<int:lot_id>/analytics', methods=['GET'])
def get_lot_analytics(lot_id):
    """Get comprehensive analytics for a parking lot - DATA IS USER-SPECIFIC"""
    if 'user_id' not in session or session.get('role') != 'owner':
        return jsonify({"message": "Unauthorized"}), 401
    
    try:
        cursor = get_cursor()
        user_id = session['user_id']
        
        app.logger.info(f"Loading analytics for lot {lot_id}, owner {user_id}")
        
        # Get lot details - FILTERED BY OWNER
        cursor.execute("SELECT * FROM lots WHERE lot_id = ? AND user_id = ?", (lot_id, user_id))
        lot = cursor.fetchone()
        if not lot:
            app.logger.warning(f"Lot {lot_id} not found for owner {user_id}")
            return jsonify({"message": "Lot not found or you don't have permission"}), 404
        
        # Get current month revenue
        cursor.execute("""
            SELECT 
                COUNT(*) as total_bookings,
                SUM(total_cost) as total_revenue,
                AVG(total_cost) as avg_booking_value,
                AVG((julianday(end_time) - julianday(start_time)) * 24) as avg_duration_hours
            FROM bookings
            WHERE lot_id = ? 
            AND strftime('%Y-%m', start_time) = strftime('%Y-%m', 'now')
        """, (lot_id,))
        current_month = dict(cursor.fetchone())
        
        # Get last month revenue for comparison
        cursor.execute("""
            SELECT 
                COUNT(*) as total_bookings,
                SUM(total_cost) as total_revenue
            FROM bookings
            WHERE lot_id = ? 
            AND strftime('%Y-%m', start_time) = strftime('%Y-%m', 'now', '-1 month')
        """, (lot_id,))
        last_month = dict(cursor.fetchone())
        
        # Get daily revenue for current month
        cursor.execute("""
            SELECT 
                strftime('%Y-%m-%d', start_time) as date,
                COUNT(*) as bookings,
                SUM(total_cost) as revenue
            FROM bookings
            WHERE lot_id = ? 
            AND strftime('%Y-%m', start_time) = strftime('%Y-%m', 'now')
            GROUP BY strftime('%Y-%m-%d', start_time)
            ORDER BY date
        """, (lot_id,))
        daily_revenue = [dict(row) for row in cursor.fetchall()]
        
        # Get peak hours data
        cursor.execute("""
            SELECT 
                strftime('%H', start_time) as hour,
                COUNT(*) as bookings,
                SUM(total_cost) as revenue
            FROM bookings
            WHERE lot_id = ? 
            AND strftime('%Y-%m', start_time) = strftime('%Y-%m', 'now')
            GROUP BY hour
            ORDER BY bookings DESC
            LIMIT 5
        """, (lot_id,))
        peak_hours = [dict(row) for row in cursor.fetchall()]
        
        # Get spot type performance
        cursor.execute("""
            SELECT 
                s.type,
                COUNT(*) as bookings,
                SUM(b.total_cost) as revenue,
                AVG(b.total_cost) as avg_revenue
            FROM bookings b
            JOIN spots s ON b.lot_id = s.lot_id AND b.spot_id = s.spot_id
            WHERE b.lot_id = ? 
            AND strftime('%Y-%m', b.start_time) = strftime('%Y-%m', 'now')
            GROUP BY s.type
        """, (lot_id,))
        spot_performance = [dict(row) for row in cursor.fetchall()]
        
        # Calculate growth
        growth_rate = 0
        if last_month['total_revenue'] and last_month['total_revenue'] > 0:
            growth_rate = ((current_month['total_revenue'] or 0) - last_month['total_revenue']) / last_month['total_revenue'] * 100
        
        # Get AI predictions for next 24 hours
        predictions = []
        now = datetime.now()
        for hour_offset in range(0, 24, 3):  # Every 3 hours
            target_time = now + timedelta(hours=hour_offset)
            pred = predict_occupancy(lot_id, target_time)
            if pred:
                predictions.append({
                    "time": target_time.strftime("%H:%M"),
                    "hour_offset": hour_offset,
                    "occupancy_rate": pred['occupancy_rate'],
                    "predicted_occupied": pred['predicted_occupied']
                })
        
        # Get pricing recommendations for different occupancy levels
        pricing_recommendations = []
        lot_dict = dict(lot)
        base_price = lot_dict.get('large_price_per_hour', 50.0)
        
        for occupancy in [30, 50, 70, 90]:
            try:
                price_rec = optimize_price(
                    lot_id, 
                    'large', 
                    occupancy,
                    base_price
                )
                if price_rec and 'optimal_price' in price_rec:
                    pricing_recommendations.append({
                        "occupancy_level": occupancy,
                        "recommended_price": price_rec['optimal_price'],
                        "current_price": base_price,
                        "increase_percentage": ((price_rec['optimal_price'] - base_price) / base_price * 100) if base_price > 0 else 0
                    })
            except Exception as e:
                app.logger.warning(f"Price optimization failed for occupancy {occupancy}: {e}")
                continue
        
        return jsonify({
            "lot": lot_dict,
            "current_month": current_month,
            "last_month": last_month,
            "growth_rate": round(growth_rate, 2),
            "daily_revenue": daily_revenue,
            "peak_hours": peak_hours,
            "spot_performance": spot_performance,
            "ai_predictions": predictions,
            "pricing_recommendations": pricing_recommendations
        })
        
    except Exception as e:
        app.logger.error(f"Analytics error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    with app.app_context():
        # Initialize both databases on startup
        print("🔧 Initializing databases...")
        
        # Check if databases exist, create if not
        if not os.path.exists(DEMO_DB_PATH):
            print(f"⚠️  {DEMO_DB_PATH} not found. Run: python complete_setup.py")
        
        if not os.path.exists(REGULAR_DB_PATH):
            print(f"📊 Creating {REGULAR_DB_PATH}...")
            init_db()  # Creates parking.db
        
        load_ai_models()  # Load AI models on startup
        print("✅ Ready!")
        
    socketio.run(app, debug=True)

# Initialize database and AI models on startup (for production)
with app.app_context():
    # Initialize regular database if it doesn't exist
    if not os.path.exists(REGULAR_DB_PATH):
        init_db_for_path(REGULAR_DB_PATH)
        app.logger.info(f"Initialized regular database: {REGULAR_DB_PATH}")
    
    # Demo database should come pre-populated from git
    # Only create if missing (shouldn't happen in production)
    if not os.path.exists(DEMO_DB_PATH):
        app.logger.warning(f"Demo database missing! Creating empty one at {DEMO_DB_PATH}")
        init_db_for_path(DEMO_DB_PATH)
    else:
        app.logger.info(f"Using pre-populated demo database: {DEMO_DB_PATH}")
    
    load_ai_models()
