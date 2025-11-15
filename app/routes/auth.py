from flask import (
    Blueprint, jsonify, redirect, render_template, request, session, url_for, current_app
)
from werkzeug.security import check_password_hash, generate_password_hash
import sqlite3

from ..db import get_cursor
from ..utils import is_demo_account

bp = Blueprint('auth', __name__)

@bp.route('/')
def role_page():
    return render_template('role.html')

@bp.route('/login')
def login_page():
    if 'role' not in request.args and 'role' not in session:
        return redirect(url_for('auth.role_page'))
    return render_template('index.html')

@bp.route('/set-role/<role>')
def set_role(role):
    if role in ['customer', 'owner']:
        session['role'] = role
    return redirect(url_for('auth.login_page', role=role))

@bp.route('/api/register', methods=['POST'])
def register_user():
    data = request.get_json()
    name, email, password, role = data.get('name'), data.get('email'), data.get('password'), data.get('role', 'customer')

    if not name or not email or not password:
        return jsonify({"message": "Missing required fields"}), 400
    if is_demo_account(email):
        return jsonify({"message": "Cannot sign up with demo account email. Demo accounts are pre-created."}), 403
    if role not in ['customer', 'owner']:
        role = 'customer'

    hashed_password = generate_password_hash(password)
    sql = "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)"

    try:
        conn = sqlite3.connect(current_app.config['DATABASE'])
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(sql, (name, email, hashed_password, role))
        conn.commit()
        conn.close()
        return jsonify({"message": "User registered successfully"})
    except sqlite3.IntegrityError:
        return jsonify({"message": "Email already exists"}), 400
    except sqlite3.Error as e:
        return jsonify({"message": f"Registration failed: {str(e)}"}), 500

@bp.route('/api/login', methods=['POST'])
def login_user():
    data = request.get_json()
    email, password, requested_role = data.get('email'), data.get('password'), data.get('role')

    if not email or not password:
        return jsonify({"message": "Missing required fields"}), 400

    current_app.logger.debug(f"Attempting login for email: {email}, role: {requested_role}")
    session.clear()
    is_demo = is_demo_account(email)
    db_path = current_app.config['DEMO_DATABASE'] if is_demo else current_app.config['DATABASE']
    current_app.logger.debug(f"Using database: {db_path} (is_demo: {is_demo})")
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()

        if user:
            current_app.logger.debug(f"User found: {user['email']}, stored hash: {user['password_hash']}")
            password_check_result = check_password_hash(user['password_hash'], password)
            current_app.logger.debug(f"Password check result: {password_check_result}")
            if password_check_result:
                session['user_id'], session['name'] = user['user_id'], user['name']
                user_role = user['role'] if 'role' in user.keys() else 'customer'
                session['role'] = requested_role if requested_role in ['customer', 'owner'] else user_role
                session['is_demo'] = is_demo
                session['email'] = email
                
                redirect_url = url_for('customer.customer_page') if session['role'] == 'customer' else url_for('owner.owner_page')

                return jsonify({
                    "message": "Login successful",
                    "redirect": redirect_url,
                    "is_demo": session['is_demo']
                })
        current_app.logger.warning(f"Login failed for email: {email} - Invalid credentials or user not found.")
        return jsonify({"message": "Invalid email or password"}), 401
    except sqlite3.Error as e:
        current_app.logger.error(f"Login failed for email: {email} - Database error: {e}", exc_info=True)
        return jsonify({"message": "Login failed. Please try again."}), 500

@bp.route('/switch-role/<new_role>')
def switch_role(new_role):
    if 'user_id' not in session:
        return redirect(url_for('auth.role_page'))
    if new_role in ['customer', 'owner']:
        if new_role == 'owner':
            cursor = get_cursor()
            cursor.execute("SELECT COUNT(*) FROM lots WHERE owner_id = ?", (session['user_id'],))
            if cursor.fetchone()[0] == 0:
                return redirect(url_for('customer.customer_page'))
        
        redirect_url = url_for('customer.customer_page') if new_role == 'customer' else url_for('owner.owner_page')
        session['role'] = new_role
        return redirect(redirect_url)
    return redirect(url_for('customer.customer_page'))


