from flask import Flask, render_template, request, jsonify, session, redirect, url_for
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

# --- Database Setup Function ---
def setup_database(force_reset=False):
    """
    Creates the users, lots, and spots tables in SQLite.
    If force_reset is True, it will drop the tables first.
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    if force_reset:
        cursor.execute("DROP TABLE IF EXISTS spots")
        cursor.execute("DROP TABLE IF EXISTS lots")
        cursor.execute("DROP TABLE IF EXISTS users")

    # Create users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL
        )
    """)

    # Create lots table
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

    # Create spots table
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

    conn.commit()
    conn.close()

app = Flask(__name__)
app.secret_key = os.urandom(24)
socketio = SocketIO(app)

# --- Initialization ---
load_dotenv()
DB_FILE = "data/parking.db"

setup_database()

# --- AI Smart Search Function ---
async def ai_smart_search(user_request, available_spots):
    """Calls the Gemini API to find the best parking spot and get an explanation.

    This function is defensive: if the `google.generativeai` package isn't
    installed or the `GEMINI_API_KEY` is not set, it returns a clear error
    dictionary instead of raising an exception so the app can continue to run.
    """
    if genai is None:
        return {"error": "google.generativeai package not installed."}

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {"error": "GEMINI_API_KEY not found."}

    # Configure the client and call the model
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-pro-latest')

    prompt = f"""
    You are a helpful parking assistant. Your goal is to find the single best parking spot for a user based on their request and explain your choice.

    User request: '{user_request}'

    Here is a list of available parking spots:
    {available_spots}

    Based on the user's request, which is the single best spot? Please return a JSON object with two keys: 'spot_id' and 'explanation'. The explanation should be a short sentence explaining why you chose that spot.
    """

    try:
        response = await model.generate_content_async(prompt)
        # Some model responses include markdown fences; strip them and parse JSON
        cleaned_response = response.text.strip().replace("```json", "").replace("```", "").strip()
        result = json.loads(cleaned_response)
        return result
    except Exception as e:
        return {"error": str(e)}

# --- Booking Function ---
def book_spot(spot_id, user_id):
    """
    Updates a row in the 'spots' table to book a spot.
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("UPDATE spots SET status = 'occupied', booked_by_user_id = ? WHERE spot_id = ?", (user_id, spot_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error creating booking: {e}")
        return False

# --- Flask Routes ---
@app.route('/')
def role_page():
    return render_template('role.html')

@app.route('/login')
def login_page():
    return render_template('index.html')

@app.route('/set-role/<role>')
def set_role(role):
    if role in ['customer', 'owner']:
        session['role'] = role
    return redirect(url_for('login_page'))

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

@app.route('/api/register', methods=['POST'])
def register_user():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')

    if not name or not email or not password:
        return jsonify({"message": "Missing required fields"}), 400

    hashed_password = generate_password_hash(password)

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)", (name, email, hashed_password))
        conn.commit()
        conn.close()
        return jsonify({"message": "User registered successfully"})
    except sqlite3.IntegrityError:
        return jsonify({"message": "Email already exists"}), 400

@app.route('/api/login', methods=['POST'])
def login_user():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"message": "Missing required fields"}), 400

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()

    if user and check_password_hash(user['password_hash'], password):
        session['user_id'] = user['user_id']
        role = session.get('role', 'customer') # Default to customer
        session['role'] = role
        redirect_url = url_for(f'{role}_page')
        return jsonify({"message": "Login successful", "redirect": redirect_url})
    else:
        return jsonify({"message": "Invalid email or password"}), 401

@app.route('/api/logout')
def logout_user():
    session.pop('user_id', None)
    return jsonify({"message": "Logout successful"})

@app.route('/api/smart-search', methods=['POST'])
async def smart_search_route():
    data = request.get_json()
    user_request = data.get('user_request')
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT s.spot_id, l.location, s.type, l.latitude, l.longitude FROM spots s JOIN lots l ON s.lot_id = l.lot_id WHERE s.status = 'available'")
    rows = cursor.fetchall()
    conn.close()
    
    available_spots = []
    spot_details = {}
    for row in rows:
        spot_id = str(row[0])
        available_spots.append({
            'spot_id': spot_id,
            'location': row[1],
            'type': row[2]
        })
        spot_details[spot_id] = {
            'latitude': row[3],
            'longitude': row[4]
        }

    if not available_spots:
        return jsonify({"message": "No available spots."})

    result = await ai_smart_search(user_request, available_spots)
    
    if 'spot_id' in result:
        spot_id = result['spot_id']
        if spot_id in spot_details:
            result.update(spot_details[spot_id])

    return jsonify(result)

@app.route('/api/book-spot', methods=['POST'])
def book_spot_route():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"message": "Unauthorized"}), 401

    data = request.get_json()
    spot_id = data.get('spot_id')
    
    if book_spot(spot_id, user_id):
        socketio.emit('status_change', {'spot_id': spot_id, 'status': 'occupied'})
        return jsonify({"message": f"Booking confirmed for Spot {spot_id}!"})
    else:
        return jsonify({"message": "Booking failed."})

@app.route('/api/end-parking', methods=['POST'])
def end_parking_route():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"message": "Unauthorized"}), 401

    data = request.get_json()
    spot_id = data.get('spot_id')

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT booked_by_user_id FROM spots WHERE spot_id = ?", (spot_id,))
    booked_by_user_id = cursor.fetchone()

    if not booked_by_user_id or booked_by_user_id[0] != user_id:
        conn.close()
        return jsonify({"message": "Unauthorized to end parking for this spot"}), 403

    try:
        cursor.execute("UPDATE spots SET status = 'available', booked_by_user_id = NULL WHERE spot_id = ?", (spot_id,))
        conn.commit()
        conn.close()
        socketio.emit('status_change', {'spot_id': spot_id, 'status': 'available'})
        return jsonify({"message": f"Parking ended for Spot {spot_id}!"})
    except Exception as e:
        print(f"Error ending parking: {e}")
        conn.close()
        return jsonify({"message": "Failed to end parking."}), 500
@app.route('/api/lots', methods=['GET'])
def get_lots():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"message": "Unauthorized"}), 401

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM lots WHERE user_id = ?", (user_id,))
    lots = [dict(row) for row in cursor.fetchall()]
    for lot in lots:
        cursor.execute("SELECT type, COUNT(*) as count FROM spots WHERE lot_id = ? GROUP BY type", (lot['lot_id'],))
        lot['spots'] = {row['type']: row['count'] for row in cursor.fetchall()}
        lot['total_spots'] = sum(lot['spots'].values())
        cursor.execute("SELECT COUNT(*) FROM spots WHERE lot_id = ? AND status = 'occupied'", (lot['lot_id'],))
        lot['occupied_spots'] = cursor.fetchone()[0]
    conn.close()
    return jsonify(lots)

@app.route('/api/lot', methods=['POST'])
def create_lot():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"message": "Unauthorized"}), 401

    data = request.get_json()
    location = data.get('location')
    total_spots = int(data.get('total_spots'))
    large_spots = int(data.get('large_spots'))
    small_spots = int(data.get('small_spots'))
    motorcycle_spots = total_spots - large_spots - small_spots
    latitude = data.get('latitude')
    longitude = data.get('longitude')

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO lots (user_id, location, latitude, longitude) VALUES (?, ?, ?, ?)", (user_id, location, latitude, longitude))
    lot_id = cursor.lastrowid

    spots = []
    for _ in range(large_spots):
        spots.append((lot_id, 'large', 'available'))
    for _ in range(small_spots):
        spots.append((lot_id, 'compact', 'available'))
    for _ in range(motorcycle_spots):
        spots.append((lot_id, 'motorcycle', 'available'))

    cursor.executemany("INSERT INTO spots (lot_id, type, status) VALUES (?, ?, ?)", spots)

    conn.commit()
    conn.close()
    return jsonify({"message": "Lot created successfully"})

@app.route('/api/lot/<int:lot_id>', methods=['GET'])
def get_lot(lot_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"message": "Unauthorized"}), 401

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM lots WHERE lot_id = ? AND user_id = ?", (lot_id, user_id,))
    lot = cursor.fetchone()
    if not lot:
        conn.close()
        return jsonify({"message": "Lot not found or unauthorized"}), 404
    lot = dict(lot)
    cursor.execute("SELECT * FROM spots WHERE lot_id = ?", (lot_id,))
    lot['spots'] = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(lot)

@app.route('/api/lot/<int:lot_id>', methods=['PUT'])
def update_lot(lot_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"message": "Unauthorized"}), 401

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM lots WHERE lot_id = ?", (lot_id,))
    lot_owner_id = cursor.fetchone()
    if not lot_owner_id or lot_owner_id[0] != user_id:
        conn.close()
        return jsonify({"message": "Unauthorized to update this lot"}), 403

    data = request.get_json()
    location = data.get('location')
    total_spots = int(data.get('total_spots'))
    large_spots = int(data.get('large_spots'))
    small_spots = int(data.get('small_spots'))
    motorcycle_spots = total_spots - large_spots - small_spots
    latitude = data.get('latitude')
    longitude = data.get('longitude')

    cursor.execute("UPDATE lots SET location = ?, latitude = ?, longitude = ? WHERE lot_id = ?", (location, latitude, longitude, lot_id))

    # Delete existing spots and create new ones
    cursor.execute("DELETE FROM spots WHERE lot_id = ?", (lot_id,))
    spots = []
    for _ in range(large_spots):
        spots.append((lot_id, 'large', 'available'))
    for _ in range(small_spots):
        spots.append((lot_id, 'compact', 'available'))
    for _ in range(motorcycle_spots):
        spots.append((lot_id, 'motorcycle', 'available'))

    cursor.executemany("INSERT INTO spots (lot_id, type, status) VALUES (?, ?, ?)", spots)

    conn.commit()
    conn.close()
    return jsonify({"message": "Lot updated successfully"})

@app.route('/api/lot/<int:lot_id>', methods=['DELETE'])
def delete_lot(lot_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"message": "Unauthorized"}), 401

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM lots WHERE lot_id = ?", (lot_id,))
    lot_owner_id = cursor.fetchone()
    if not lot_owner_id or lot_owner_id[0] != user_id:
        conn.close()
        return jsonify({"message": "Unauthorized to delete this lot"}), 403

    cursor.execute("DELETE FROM spots WHERE lot_id = ?", (lot_id,))
    cursor.execute("DELETE FROM lots WHERE lot_id = ?", (lot_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Lot deleted successfully"})

@app.route('/api/lot/<int:lot_id>/spot', methods=['POST'])
def create_spot(lot_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"message": "Unauthorized"}), 401

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM lots WHERE lot_id = ?", (lot_id,))
    lot_owner_id = cursor.fetchone()
    if not lot_owner_id or lot_owner_id[0] != user_id:
        conn.close()
        return jsonify({"message": "Unauthorized to add spot to this lot"}), 403

    data = request.get_json()
    spot_type = data.get('type')
    status = data.get('status')
    
    cursor.execute("INSERT INTO spots (lot_id, type, status) VALUES (?, ?, ?)", (lot_id, spot_type, status))
    conn.commit()
    conn.close()
    return jsonify({"message": "Spot created successfully"})

@app.route('/api/lot/<int:lot_id>/spot/<int:spot_id>', methods=['PUT'])
def update_spot(lot_id, spot_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"message": "Unauthorized"}), 401

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM lots WHERE lot_id = ?", (lot_id,))
    lot_owner_id = cursor.fetchone()
    if not lot_owner_id or lot_owner_id[0] != user_id:
        conn.close()
        return jsonify({"message": "Unauthorized to update spot in this lot"}), 403

    data = request.get_json()
    spot_type = data.get('type')
    status = data.get('status')
    
    cursor.execute("UPDATE spots SET type = ?, status = ? WHERE spot_id = ? AND lot_id = ?", (spot_type, status, spot_id, lot_id))
    conn.commit()
    conn.close()
    return jsonify({"message": "Spot updated successfully"})

@app.route('/api/lot/<int:lot_id>/spot/<int:spot_id>', methods=['DELETE'])
def delete_spot(lot_id, spot_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"message": "Unauthorized"}), 401

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM lots WHERE lot_id = ?", (lot_id,))
    lot_owner_id = cursor.fetchone()
    if not lot_owner_id or lot_owner_id[0] != user_id:
        conn.close()
        return jsonify({"message": "Unauthorized to delete spot from this lot"}), 403

    cursor.execute("DELETE FROM spots WHERE spot_id = ? AND lot_id = ?", (spot_id, lot_id))
    conn.commit()
    conn.close()
    return jsonify({"message": "Spot deleted successfully"})

@app.route('/api/validate-booking/<spot_id>')
def validate_booking(spot_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"valid": False}), 401

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT booked_by_user_id FROM spots WHERE spot_id = ?", (spot_id,))
    result = cursor.fetchone()
    conn.close()

    if result and result[0] == user_id:
        return jsonify({"valid": True})
    else:
        return jsonify({"valid": False})

@app.route('/api/reset-database', methods=['POST'])

def reset_database():
    if os.environ.get('FLASK_ENV') == 'development':
        setup_database(force_reset=True)
        return jsonify({"message": "Database has been reset."})
    else:
        return jsonify({"message": "This action is not allowed in the current environment."}), 403

if __name__ == '__main__':
    socketio.run(app, debug=True)