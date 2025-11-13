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

# --- App Initialization ---
logging.basicConfig(level=logging.INFO)
load_dotenv()

app = Flask(__name__)
# CRITICAL: Load secret key from environment variable for production
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev_fallback_secret_key_12345')
socketio = SocketIO(app)

DEFAULT_PRICING = {
    'large': 50.0,
    'car': 40.0,
    'motorcycle': 15.0,
    'bike': 15.0,
    'truck': 75.0
}

TIME_FORMAT = "%Y-%m-%dT%H:%M"

# --- Database Configuration & Management ---
DB_FILE = "data/parking.db"

def get_db():
    """Opens a new database connection if there is none yet for the current application context."""
    if 'db' not in g:
        os.makedirs("data", exist_ok=True)
        g.db = sqlite3.connect(DB_FILE)
        g.db.row_factory = sqlite3.Row
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

def init_db(force_reset=False):
    """Creates the database tables."""
    db = get_db()
    cursor = db.cursor()

    if force_reset:
        cursor.execute("DROP TABLE IF EXISTS spots")
        cursor.execute("DROP TABLE IF EXISTS lots")
        cursor.execute("DROP TABLE IF EXISTS users")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL
        )
    """)
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'customer'")
    except sqlite3.OperationalError:
        db.rollback()
    else:
        db.commit()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lots (
            lot_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            location TEXT NOT NULL,
            latitude REAL,
            longitude REAL,
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            UNIQUE(user_id, location)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS spots (
            spot_id INTEGER NOT NULL,
            lot_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            status TEXT NOT NULL,
            booked_by_user_id INTEGER,
            price_per_hour REAL DEFAULT 30.0,
            display_order INTEGER DEFAULT 0,
            PRIMARY KEY (lot_id, spot_id),
            FOREIGN KEY (lot_id) REFERENCES lots (lot_id),
            FOREIGN KEY (booked_by_user_id) REFERENCES users (user_id)
        )
    """)

    try:
        cursor.execute("ALTER TABLE spots ADD COLUMN price_per_hour REAL DEFAULT 30.0")
        db.commit()
    except sqlite3.OperationalError:
        db.rollback()

    try:
        cursor.execute("ALTER TABLE spots ADD COLUMN display_order INTEGER DEFAULT 0")
        db.commit()
    except sqlite3.OperationalError:
        db.rollback()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
            lot_id INTEGER NOT NULL,
            spot_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            price_per_hour REAL NOT NULL,
            total_cost REAL NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (lot_id, spot_id) REFERENCES spots (lot_id, spot_id),
            FOREIGN KEY (user_id) REFERENCES users (user_id)
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


# --- AI Smart Search Function ---
async def ai_smart_search(user_request, available_spots):
    """Calls the Gemini API to find the best parking spot and get an explanation."""
    import asyncio
    
    if genai is None:
        return {"error": "google.generativeai package not installed."}
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {"error": "GEMINI_API_KEY not found."}

    genai.configure(api_key=api_key)
    # Use gemini-1.5-flash for better stability and response format
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"""
    You are a helpful parking assistant. Be VERY brief.
    User wants: '{user_request}'
    Available spots: {available_spots[:3]}  
    Return ONLY valid JSON: {{"spot_id": <number>, "explanation": "<10 words max>"}}
    """
    try:
        # Set a 15 second timeout for Gemini API
        response = await asyncio.wait_for(
            model.generate_content_async(prompt),
            timeout=15.0
        )
        cleaned_response = response.text.strip().replace("```json", "").replace("```", "").strip()
        app.logger.info(f"Gemini response: {cleaned_response}")
        return json.loads(cleaned_response)
    except asyncio.TimeoutError:
        app.logger.error("Gemini API timeout after 15 seconds")
        # Return first available spot as fallback
        return {
            "spot_id": available_spots[0]['spot_id'],
            "explanation": "Quick pick - AI timed out"
        }
    except json.JSONDecodeError as e:
        app.logger.error(f"JSON decode error from Gemini: {cleaned_response if 'cleaned_response' in locals() else 'no response'}")
        return {
            "spot_id": available_spots[0]['spot_id'],
            "explanation": "Quick pick - AI response invalid"
        }
    except Exception as e:
        app.logger.error(f"Error calling Gemini API: {e}")
        return {
            "spot_id": available_spots[0]['spot_id'],
            "explanation": f"Quick pick - API error"
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
    name, email, password = data.get('name'), data.get('email'), data.get('password')

    if not name or not email or not password:
        return jsonify({"message": "Missing required fields"}), 400

    hashed_password = generate_password_hash(password)
    sql = f"INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)"

    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute(sql, (name, email, hashed_password))
        db.commit()
        return jsonify({"message": "User registered successfully"})
    except (sqlite3.IntegrityError, Exception):
        get_db().rollback()
        return jsonify({"message": "Email already exists"}), 400

@app.route('/api/login', methods=['POST'])
def login_user():
    data = request.get_json()
    email, password, requested_role = data.get('email'), data.get('password'), data.get('role')

    if not email or not password:
        return jsonify({"message": "Missing required fields"}), 400

    cursor = get_cursor()
    cursor.execute(f"SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()

    if user and check_password_hash(user['password_hash'], password):
        session['user_id'], session['name'] = user['user_id'], user['name']
        session['role'] = requested_role if requested_role in ['customer', 'owner'] else session.get('role', 'customer')
        return jsonify({"message": "Login successful", "redirect": url_for(f'{session["role"]}_page')})
    else:
        return jsonify({"message": "Invalid email or password"}), 401

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
        SELECT s.spot_id, s.type, s.price_per_hour, s.display_order, l.location, l.latitude, l.longitude, l.lot_id
        FROM spots s
        JOIN lots l ON s.lot_id = l.lot_id
        ORDER BY s.display_order ASC
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
                'lot_id': row['lot_id'],
                'display_order': row['display_order']
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

    # Create spots with per-lot IDs and display_order
    spot_num = 1
    for i in range(large_total):
        cursor.execute(
            "INSERT INTO spots (lot_id, spot_id, type, status, price_per_hour, display_order) VALUES (?, ?, ?, ?, ?, ?)",
            (lot_id, spot_num, 'large', 'available', large_price, spot_num)
        )
        spot_num += 1
    for i in range(motorcycle_total):
        cursor.execute(
            "INSERT INTO spots (lot_id, spot_id, type, status, price_per_hour, display_order) VALUES (?, ?, ?, ?, ?, ?)",
            (lot_id, spot_num, 'motorcycle', 'available', motorcycle_price, spot_num)
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
    cursor.execute(f"SELECT spot_id, type, status, price_per_hour, display_order FROM spots WHERE lot_id = ? ORDER BY display_order ASC", (lot_id,))
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

    # Create spots with per-lot IDs and display_order
    spot_num = 1
    for i in range(large_total):
        cursor.execute(
            "INSERT INTO spots (lot_id, spot_id, type, status, price_per_hour, display_order) VALUES (?, ?, ?, ?, ?, ?)",
            (lot_id, spot_num, 'large', 'available', large_price, spot_num)
        )
        spot_num += 1
    for i in range(motorcycle_total):
        cursor.execute(
            "INSERT INTO spots (lot_id, spot_id, type, status, price_per_hour, display_order) VALUES (?, ?, ?, ?, ?, ?)",
            (lot_id, spot_num, 'motorcycle', 'available', motorcycle_price, spot_num)
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
    display_order = data.get('display_order', 999)

    # Get next spot_id for this lot
    cursor.execute("SELECT MAX(spot_id) FROM spots WHERE lot_id = ?", (lot_id,))
    max_spot = cursor.fetchone()[0]
    next_spot_id = (max_spot or 0) + 1

    cursor.execute(
        f"INSERT INTO spots (lot_id, spot_id, type, status, price_per_hour, display_order) VALUES (?, ?, ?, ?, ?, ?)",
        (lot_id, next_spot_id, spot_type, spot_status, price_per_hour, display_order)
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
        "SELECT type, status, display_order FROM spots WHERE lot_id = ? AND spot_id = ?",
        (lot_id, spot_id)
    )
    existing_spot = cursor.fetchone()
    if not existing_spot:
        return jsonify({"message": "Spot not found"}), 404

    spot_type = data.get('type', existing_spot['type'])
    spot_status = data.get('status', existing_spot['status'] or 'available')
    price_per_hour = data.get('price_per_hour')
    display_order = data.get('display_order', existing_spot['display_order'])

    if spot_type == 'small':
        spot_type = 'motorcycle'

    if not spot_type:
        spot_type = existing_spot['type']

    price_per_hour = coerce_price(price_per_hour, get_spot_default_price(spot_type))

    cursor.execute(
        f"UPDATE spots SET type = ?, status = ?, price_per_hour = ?, display_order = ? WHERE lot_id = ? AND spot_id = ?",
        (spot_type, spot_status, price_per_hour, display_order, lot_id, spot_id)
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
        "gemini_api": "configured" if os.getenv('GEMINI_API_KEY') else "not_configured",
        "gemini_key_length": len(os.getenv('GEMINI_API_KEY', '')) if os.getenv('GEMINI_API_KEY') else 0
    })

@app.route('/api/test-gemini', methods=['GET'])
async def test_gemini():
    """Test Gemini API directly"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return jsonify({"error": "GEMINI_API_KEY not configured"}), 500
    
    try:
        if genai is None:
            return jsonify({"error": "google-generativeai not installed"}), 500
            
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        test_prompt = "Say 'Hello, I am working!' in JSON format with a key 'message'"
        response = await model.generate_content_async(test_prompt)
        
        return jsonify({
            "success": True,
            "raw_response": response.text,
            "api_key_prefix": api_key[:10] + "..." if len(api_key) > 10 else "too_short"
        })
    except Exception as e:
        return jsonify({
            "error": str(e),
            "error_type": type(e).__name__,
            "api_key_prefix": api_key[:10] + "..." if len(api_key) > 10 else "too_short"
        }), 500

if __name__ == '__main__':
    with app.app_context():
        init_db()
    socketio.run(app, debug=True)

# Initialize database on startup (for production)
with app.app_context():
    init_db()
