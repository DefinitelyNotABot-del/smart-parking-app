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

# --- App Initialization ---
logging.basicConfig(level=logging.INFO)
load_dotenv()

app = Flask(__name__)
# CRITICAL: Load secret key from environment variable for production
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev_fallback_secret_key_12345')
socketio = SocketIO(app)

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
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS spots (
            spot_id INTEGER PRIMARY KEY AUTOINCREMENT,
            lot_id INTEGER,
            type TEXT NOT NULL,
            status TEXT NOT NULL,
            booked_by_user_id INTEGER,
            FOREIGN KEY (lot_id) REFERENCES lots (lot_id),
            FOREIGN KEY (booked_by_user_id) REFERENCES users (user_id)
        )
    """)

    db.commit()

@app.cli.command('init-db')
def init_db_command():
    """CLI command to clear the existing data and create new tables."""
    init_db(force_reset=True)
    click.echo('Initialized the database.')


# --- AI Smart Search Function ---
async def ai_smart_search(user_request, available_spots):
    """Calls the Gemini API to find the best parking spot and get an explanation."""
    if genai is None:
        return {"error": "google.generativeai package not installed."}
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {"error": "GEMINI_API_KEY not found."}

    genai.configure(api_key=api_key)
    # Use gemini-1.5-flash for better stability and response format
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"""
    You are a helpful parking assistant. Your goal is to find the single best parking spot for a user based on their request and provide a very brief explanation for your choice.
    User request: '{user_request}'
    Here is a list of available parking spots: {available_spots}
    Based on the user's request, which is the single best spot? Please return ONLY a valid JSON object with two keys: 'spot_id' (as an integer) and 'explanation' (as a string). Do not include any other text or markdown formatting.
    Example response: {{"spot_id": 1, "explanation": "This spot is closest to your destination"}}
    """
    try:
        response = await model.generate_content_async(prompt)
        cleaned_response = response.text.strip().replace("```json", "").replace("```", "").strip()
        app.logger.info(f"Gemini response: {cleaned_response}")
        return json.loads(cleaned_response)
    except json.JSONDecodeError as e:
        app.logger.error(f"JSON decode error from Gemini: {cleaned_response}")
        return {"error": f"Invalid JSON from AI: {str(e)}"}
    except Exception as e:
        app.logger.error(f"Error calling Gemini API: {e}")
        return {"error": f"Gemini API error: {str(e)}"}

# --- Booking Function ---
def book_spot(spot_id, user_id):
    """Updates a row in the 'spots' table to book a spot."""
    sql = f"UPDATE spots SET status = 'occupied', booked_by_user_id = ? WHERE spot_id = ? AND status = 'available'"
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute(sql, (user_id, spot_id))
        db.commit()
        return cursor.rowcount > 0
    except Exception as e:
        app.logger.error(f"Error creating booking for spot {spot_id}: {e}")
        get_db().rollback()
        return False

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
    cursor.execute(f"""
        SELECT s.spot_id, s.type, s.status, l.location
        FROM spots s JOIN lots l ON s.lot_id = l.lot_id
        WHERE s.booked_by_user_id = ?
    """, (user_id,))
    bookings = [dict(row) for row in cursor.fetchall()]
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
async def smart_search_route():
    user_request = request.get_json().get('user_request')
    app.logger.info(f"Smart search request: {user_request}")
    
    cursor = get_cursor()
    cursor.execute("SELECT s.spot_id, l.location, s.type, l.latitude, l.longitude FROM spots s JOIN lots l ON s.lot_id = l.lot_id WHERE s.status = 'available'")
    
    available_spots, spot_details = [], {}
    for row in cursor.fetchall():
        spot_id = str(row['spot_id'])
        available_spots.append({'spot_id': spot_id, 'location': row['location'], 'type': row['type']})
        spot_details[spot_id] = {'latitude': row['latitude'], 'longitude': row['longitude']}

    app.logger.info(f"Found {len(available_spots)} available spots")

    if not available_spots:
        return jsonify({"message": "No available spots."})

    result = await ai_smart_search(user_request, available_spots)
    app.logger.info(f"AI search result: {result}")
    
    if 'error' in result:
        app.logger.error(f"Smart search error: {result['error']}")
        return jsonify(result), 500

    returned_spot_id = str(result.get('spot_id')) if result.get('spot_id') is not None else None
    if returned_spot_id not in {str(s['spot_id']) for s in available_spots}:
        fallback_spot_id = available_spots[0]['spot_id']
        result['spot_id'] = fallback_spot_id
        result['explanation'] = f"(AI suggested an invalid spot, so we picked one for you) {result.get('explanation', '')}"

    if 'spot_id' in result and result['spot_id'] in spot_details:
        result.update(spot_details[result['spot_id']])

    return jsonify(result)

@app.route('/api/book-spot', methods=['POST'])
def book_spot_route():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"message": "Unauthorized"}), 401

    spot_id = request.get_json().get('spot_id')
    if book_spot(spot_id, user_id):
        socketio.emit('status_change', {'spot_id': spot_id, 'status': 'occupied'})
        return jsonify({"message": f"Booking confirmed for Spot {spot_id}!"})
    else:
        return jsonify({"message": "Booking failed."}), 500

@app.route('/api/end-parking', methods=['POST'])
def end_parking_route():
    user_id = session.get('user_id')
    if not user_id: return jsonify({"message": "Unauthorized"}), 401

    spot_id = request.get_json().get('spot_id')
    cursor = get_cursor()
    cursor.execute(f"SELECT s.booked_by_user_id, l.user_id as lot_owner_id FROM spots s JOIN lots l ON s.lot_id = l.lot_id WHERE s.spot_id = ?", (spot_id,))
    result = cursor.fetchone()

    if not result: return jsonify({"message": "Spot not found"}), 404

    if user_id != result['booked_by_user_id'] and user_id != result['lot_owner_id']:
        return jsonify({"message": "Unauthorized to end parking for this spot"}), 403

    try:
        db = get_db()
        cursor.execute(f"UPDATE spots SET status = 'available', booked_by_user_id = NULL WHERE spot_id = ?", (spot_id,))
        db.commit()
        socketio.emit('status_change', {'spot_id': spot_id, 'status': 'available'})
        return jsonify({"message": f"Parking ended for Spot {spot_id}!"})
    except Exception as e:
        app.logger.error(f"Error ending parking for spot {spot_id}: {e}")
        get_db().rollback()
        return jsonify({"message": "Failed to end parking."}), 500

@app.route('/api/lots', methods=['GET'])
def get_lots():
    user_id = session.get('user_id')
    if not user_id or session.get('role') != 'owner':
        return jsonify({"message": "Unauthorized"}), 401

    cursor = get_cursor()
    cursor.execute(f"SELECT * FROM lots WHERE user_id = ?", (user_id,))
    lots = [dict(row) for row in cursor.fetchall()]
    for lot in lots:
        cursor.execute(f"SELECT type, COUNT(*) as count FROM spots WHERE lot_id = ? GROUP BY type", (lot['lot_id'],))
        lot['spots'] = {row['type']: row['count'] for row in cursor.fetchall()}
        lot['total_spots'] = sum(lot['spots'].values())
        cursor.execute(f"SELECT COUNT(*) FROM spots WHERE lot_id = ? AND status = 'occupied'", (lot['lot_id'],))
        lot['occupied_spots'] = cursor.fetchone()[0]
    
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

    spots = []
    for _ in range(int(data.get('large_spots', 0))): spots.append((lot_id, 'large', 'available'))
    for _ in range(int(data.get('motorcycle_spots', 0))): spots.append((lot_id, 'motorcycle', 'available'))

    if spots:
        spot_sql = f"INSERT INTO spots (lot_id, type, status) VALUES (?, ?, ?)"
        cursor.executemany(spot_sql, spots)

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
    cursor.execute(f"SELECT * FROM spots WHERE lot_id = ?", (lot_id,))
    lot['spots'] = [dict(row) for row in cursor.fetchall()]
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

    cursor.execute(f"DELETE FROM spots WHERE lot_id = ?", (lot_id,))
    spots = []
    for _ in range(int(data.get('large_spots', 0))): spots.append((lot_id, 'large', 'available'))
    for _ in range(int(data.get('motorcycle_spots', 0))): spots.append((lot_id, 'motorcycle', 'available'))

    if spots:
        spot_sql = f"INSERT INTO spots (lot_id, type, status) VALUES (?, ?, ?)"
        cursor.executemany(spot_sql, spots)

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

    cursor.execute(f"DELETE FROM spots WHERE lot_id = ?", (lot_id,))
    cursor.execute(f"DELETE FROM lots WHERE lot_id = ?", (lot_id,))
    db.commit()
    return jsonify({"message": "Lot deleted successfully"})

# ... (spot CRUD routes can be refactored similarly if needed) ...

@app.route('/api/validate-booking/<spot_id>')
def validate_booking(spot_id):
    user_id = session.get('user_id')
    if not user_id: return jsonify({"valid": False}), 401

    cursor = get_cursor()
    cursor.execute(f"SELECT booked_by_user_id FROM spots WHERE spot_id = ?", (spot_id,))
    result = cursor.fetchone()

    return jsonify({"valid": result and result['booked_by_user_id'] == user_id})

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
