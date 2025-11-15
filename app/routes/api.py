from flask import Blueprint, jsonify, request, session, current_app
from werkzeug.security import check_password_hash, generate_password_hash
import sqlite3
from datetime import datetime, timedelta
import os

from ..db import get_cursor, get_db
from ..utils import (
    predict_occupancy, optimize_price, recommend_spot_for_user, forecast_peak_hours,
    format_datetime, coerce_price, get_spot_default_price, is_demo_account,
    create_booking, spot_is_available, get_future_bookings, load_model, AI_MODELS,
    parse_datetime, default_booking_window, calculate_total_cost, get_duration_hours
)
from nlp_parser import parser as nlp_parser 
from .. import socketio

bp = Blueprint('api', __name__, url_prefix='/api')

@bp.route('/me')
def get_me():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"message": "Unauthorized"}), 401
    cursor = get_cursor()
    cursor.execute("SELECT COUNT(*) FROM lots WHERE owner_id = ?", (user_id,))
    lot_count = cursor.fetchone()[0]
    return jsonify({'name': session.get('name'), 'role': session.get('role'), 'is_owner': lot_count > 0})

@bp.route('/debug/session')
def debug_session():
    return jsonify({
        "user_id": session.get('user_id'),
        "name": session.get('name'),
        "email": session.get('email'),
        "role": session.get('role'),
        "is_demo": session.get('is_demo'),
        "database": current_app.config['DEMO_DATABASE'] if session.get('is_demo') else current_app.config['DATABASE']
    })

@bp.route('/logout')
def logout_user():
    session.clear()
    return jsonify({"message": "Logout successful"})

@bp.route('/lots', methods=['GET'])
def get_lots():
    user_id = session.get('user_id')
    if not user_id or session.get('role') != 'owner':
        return jsonify({"message": "Unauthorized"}), 401

    cursor = get_cursor()
    cursor.execute("SELECT * FROM lots WHERE owner_id = ?", (user_id,))
    lots = [dict(row) for row in cursor.fetchall()]
    now_iso = format_datetime(datetime.utcnow())
    for lot in lots:
        cursor.execute( "SELECT spot_id, type, price_per_hour FROM spots WHERE lot_id = ?", (lot['lot_id'],) )
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
        lot['price_by_type'] = { spot_type: round(sum(values) / len(values), 2) for spot_type, values in price_groups.items() }
        cursor.execute( "SELECT COUNT(DISTINCT spot_id) FROM bookings WHERE lot_id = ? AND ? BETWEEN start_time AND end_time", (lot['lot_id'], now_iso) )
        lot['occupied_spots'] = cursor.fetchone()[0]
        cursor.execute( "SELECT COUNT(*) FROM bookings WHERE lot_id = ? AND start_time >= ?", (lot['lot_id'], now_iso) )
        lot['upcoming_bookings'] = cursor.fetchone()[0]
    response = jsonify(lots)
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response

@bp.route('/lot', methods=['POST'])
def create_lot():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"message": "Unauthorized"}), 401

    data = request.get_json()
    db = get_db()
    cursor = db.cursor()
    sql = "INSERT INTO lots (owner_id, location, latitude, longitude) VALUES (?, ?, ?, ?)"
    params = (user_id, data.get('location'), data.get('latitude'), data.get('longitude'))
    cursor.execute(sql, params)
    lot_id = cursor.lastrowid

    large_price = coerce_price(data.get('large_price_per_hour'), get_spot_default_price('large'))
    motorcycle_price = coerce_price(data.get('motorcycle_price_per_hour'), get_spot_default_price('motorcycle'))
    large_total = int(data.get('large_spots') or 0)
    motorcycle_total = int(data.get('motorcycle_spots') or 0)

    spot_num = 1
    for _ in range(large_total):
        cursor.execute("INSERT INTO spots (lot_id, spot_id, type, status, price_per_hour) VALUES (?, ?, ?, ?, ?)", (lot_id, spot_num, 'large', 'available', large_price))
        spot_num += 1
    for _ in range(motorcycle_total):
        cursor.execute("INSERT INTO spots (lot_id, spot_id, type, status, price_per_hour) VALUES (?, ?, ?, ?, ?)", (lot_id, spot_num, 'motorcycle', 'available', motorcycle_price))
        spot_num += 1

    db.commit()
    return jsonify({"message": "Lot created successfully", "lot_id": lot_id})

@bp.route('/lot/<int:lot_id>', methods=['GET', 'PUT', 'DELETE'])
def lot_detail(lot_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"message": "Unauthorized"}), 401

    if request.method == 'GET':
        user_role = session.get('role')
        cursor = get_cursor()
        if user_role == 'owner':
            cursor.execute("SELECT * FROM lots WHERE lot_id = ? AND owner_id = ?", (lot_id, user_id))
        else:
            cursor.execute("SELECT * FROM lots WHERE lot_id = ?", (lot_id,))
        lot = cursor.fetchone()
        if not lot:
            return jsonify({"message": "Lot not found"}), 404
        lot = dict(lot)
        cursor.execute("SELECT spot_id, type, status, price_per_hour FROM spots WHERE lot_id = ? ORDER BY spot_id ASC", (lot_id,))
        spots = []
        for row in cursor.fetchall():
            spot = dict(row)
            if user_role == 'owner':
                spot['bookings'] = get_future_bookings(lot_id, row['spot_id'])
            spots.append(spot)
        lot['spots'] = spots
        lot['total_spots'] = len(lot['spots'])
        return jsonify(lot)

    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT owner_id FROM lots WHERE lot_id = ?", (lot_id,))
    lot_owner = cursor.fetchone()
    if not lot_owner or lot_owner['owner_id'] != user_id:
        return jsonify({"message": "Unauthorized to modify this lot"}), 403

    if request.method == 'PUT':
        data = request.get_json()
        params = (data.get('location'), data.get('latitude'), data.get('longitude'), lot_id)
        cursor.execute("UPDATE lots SET location = ?, latitude = ?, longitude = ? WHERE lot_id = ?", params)
        cursor.execute("DELETE FROM spots WHERE lot_id = ?", (lot_id,))
        large_price = coerce_price(data.get('large_price_per_hour'), get_spot_default_price('large'))
        motorcycle_price = coerce_price(data.get('motorcycle_price_per_hour'), get_spot_default_price('motorcycle'))
        large_total = int(data.get('large_spots') or 0)
        motorcycle_total = int(data.get('motorcycle_spots') or 0)
        spot_num = 1
        for _ in range(large_total):
            cursor.execute("INSERT INTO spots (lot_id, spot_id, type, status, price_per_hour) VALUES (?, ?, ?, ?, ?)", (lot_id, spot_num, 'large', 'available', large_price))
            spot_num += 1
        for _ in range(motorcycle_total):
            cursor.execute("INSERT INTO spots (lot_id, spot_id, type, status, price_per_hour) VALUES (?, ?, ?, ?, ?)", (lot_id, spot_num, 'motorcycle', 'available', motorcycle_price))
            spot_num += 1
        db.commit()
        return jsonify({"message": "Lot updated successfully"})

    if request.method == 'DELETE':
        cursor.execute("DELETE FROM bookings WHERE lot_id = ?", (lot_id,))
        cursor.execute("DELETE FROM spots WHERE lot_id = ?", (lot_id,))
        cursor.execute("DELETE FROM lots WHERE lot_id = ?", (lot_id,))
        db.commit()
        socketio.emit('status_change', {'lot_id': lot_id, 'action': 'lot_deleted'})
        return jsonify({"message": "Lot deleted successfully"})

@bp.route('/lot/<int:lot_id>/spot', methods=['POST'])
def add_spot(lot_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"message": "Unauthorized"}), 401

    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT owner_id FROM lots WHERE lot_id = ?", (lot_id,))
    lot_owner = cursor.fetchone()
    if not lot_owner or lot_owner['owner_id'] != user_id:
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
        "INSERT INTO spots (lot_id, spot_id, type, status, price_per_hour) VALUES (?, ?, ?, ?, ?)",
        (lot_id, next_spot_id, spot_type, spot_status, price_per_hour)
    )
    db.commit()
    socketio.emit('status_change', {'lot_id': lot_id, 'action': 'spot_added'})
    return jsonify({
        "message": "Spot added successfully",
        "spot_id": next_spot_id,
        "price_per_hour": price_per_hour
    })

@bp.route('/lot/<int:lot_id>/spot/<int:spot_id>', methods=['PUT', 'DELETE'])
def spot_detail(lot_id, spot_id):
    user_id = session.get('user_id')
    if not user_id: return jsonify({"message": "Unauthorized"}), 401
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT owner_id FROM lots WHERE lot_id = ?", (lot_id,))
    lot_owner = cursor.fetchone()
    if not lot_owner or lot_owner['owner_id'] != user_id:
        return jsonify({"message": "Unauthorized to modify spots in this lot"}), 403
    
    if request.method == 'PUT':
        data = request.get_json()
        cursor.execute("SELECT type, status FROM spots WHERE lot_id = ? AND spot_id = ?", (lot_id, spot_id))
        existing_spot = cursor.fetchone()
        if not existing_spot: return jsonify({"message": "Spot not found"}), 404
        spot_type = data.get('type', existing_spot['type'])
        if spot_type == 'small': spot_type = 'motorcycle'
        price_per_hour = coerce_price(data.get('price_per_hour'), get_spot_default_price(spot_type))
        cursor.execute("UPDATE spots SET type = ?, status = ?, price_per_hour = ? WHERE lot_id = ? AND spot_id = ?", (spot_type, data.get('status', 'available'), price_per_hour, lot_id, spot_id))
        db.commit()
        socketio.emit('status_change', {'lot_id': lot_id, 'spot_id': spot_id, 'action': 'spot_updated'})
        return jsonify({"message": "Spot updated successfully", "price_per_hour": price_per_hour})

    if request.method == 'DELETE':
        cursor.execute("DELETE FROM bookings WHERE lot_id = ? AND spot_id = ?", (lot_id, spot_id))
        cursor.execute("DELETE FROM spots WHERE lot_id = ? AND spot_id = ?", (lot_id, spot_id))
        db.commit()
        socketio.emit('status_change', {'lot_id': lot_id, 'spot_id': spot_id, 'action': 'spot_deleted'})
        return jsonify({"message": "Spot deleted successfully"})

@bp.route('/lot/<int:lot_id>/bookings', methods=['GET'])
def get_lot_bookings(lot_id):
    user_id = session.get('user_id')
    if not user_id or session.get('role') != 'owner':
        return jsonify({"message": "Unauthorized"}), 401

    cursor = get_cursor()
    cursor.execute("SELECT owner_id FROM lots WHERE lot_id = ?", (lot_id,))
    lot_row = cursor.fetchone()
    if not lot_row or lot_row['owner_id'] != user_id:
        return jsonify({"message": "Unauthorized"}), 403

    cursor.execute(
        """
        SELECT b.booking_id, b.spot_id, b.start_time, b.end_time, b.total_cost, b.price_per_hour,
               u.name as customer_name
        FROM bookings b
        JOIN spots s ON b.lot_id = s.lot_id AND b.spot_id = s.spot_id
        WHERE b.start_time >= ? AND b.spot_id IN (
            SELECT spot_id FROM spots WHERE lot_id = ?
        )
        ORDER BY b.start_time ASC
        """,
        (format_datetime(datetime.utcnow() - timedelta(days=1)), lot_id)
    )

    bookings = [dict(row) for row in cursor.fetchall()]
    return jsonify(bookings)

@bp.route('/lot/<int:lot_id>/analytics', methods=['GET'])
def get_lot_analytics(lot_id):
    if 'user_id' not in session or session.get('role') != 'owner':
        return jsonify({"message": "Unauthorized"}), 401
    try:
        cursor = get_cursor()
        user_id = session['user_id']
        current_app.logger.info(f"Loading analytics for lot {lot_id}, owner {user_id}")
        cursor.execute("SELECT * FROM lots WHERE lot_id = ? AND owner_id = ?", (lot_id, user_id))
        lot = cursor.fetchone()
        if not lot:
            current_app.logger.warning(f"Lot {lot_id} not found for owner {user_id}")
            return jsonify({"message": "Lot not found or you don't have permission"}), 404
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
        cursor.execute("""
            SELECT
                COUNT(*) as total_bookings,
                SUM(total_cost) as total_revenue
            FROM bookings
            WHERE lot_id = ?
            AND strftime('%Y-%m', start_time) = strftime('%Y-%m', 'now', '-1 month')
        """, (lot_id,))
        last_month = dict(cursor.fetchone())
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
        growth_rate = 0
        if last_month['total_revenue'] and last_month['total_revenue'] > 0:
            growth_rate = ((current_month['total_revenue'] or 0) - last_month['total_revenue']) / last_month['total_revenue'] * 100
        cursor.execute("SELECT COUNT(*) as count FROM bookings WHERE lot_id = ?", (lot_id,))
        has_booking_history = cursor.fetchone()['count'] > 0
        lot_dict = dict(lot)
        predictions = []
        pricing_recommendations = []
        if has_booking_history:
            now = datetime.now()
            for hour_offset in range(0, 24, 3):
                target_time = now + timedelta(hours=hour_offset)
                pred = predict_occupancy(lot_id, target_time)
                if pred:
                    predictions.append({
                        "time": target_time.strftime("%H:%M"),
                        "hour_offset": hour_offset,
                        "occupancy_rate": pred['occupancy_rate'],
                        "predicted_occupied": pred['predicted_occupied']
                    })
            base_price = lot_dict.get('large_price_per_hour', 50.0)
            for occupancy in [30, 50, 70, 90]:
                try:
                    price_rec = optimize_price(lot_id, 'large', occupancy, base_price)
                    if price_rec and 'optimal_price' in price_rec:
                        pricing_recommendations.append({
                            "occupancy_level": occupancy,
                            "recommended_price": price_rec['optimal_price'],
                            "current_price": base_price,
                            "increase_percentage": ((price_rec['optimal_price'] - base_price) / base_price * 100) if base_price > 0 else 0
                        })
                except Exception as e:
                    current_app.logger.warning(f"Price optimization failed for occupancy {occupancy}: {e}")
                    continue
        else:
            current_app.logger.info(f"No booking history for lot {lot_id} - skipping AI predictions")
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
        current_app.logger.error(f"Analytics error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@bp.route('/validate-booking/<spot_id>')
def validate_booking(spot_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"valid": False}), 401

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

@bp.route('/reset-database', methods=['POST'])
def reset_database():
    if os.environ.get('FLASK_ENV') == 'development':
        from ..services.db_setup import init_db_for_path
        init_db_for_path(current_app.config['DATABASE'], force_reset=True)
        return jsonify({"message": "Database has been reset."})
    else:
        return jsonify({"message": "This action is not allowed in the current environment."}), 403

@bp.route('/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "database": "connected" if os.path.exists(current_app.config['DATABASE']) else "not_initialized",
        "nlp_parser": "local_rule_based"
    })

# --- AI PREDICTION API ENDPOINTS ---
@bp.route('/ai/predict-occupancy/<int:lot_id>', methods=['GET'])
def api_predict_occupancy(lot_id):
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
        current_app.logger.error(f"Occupancy prediction error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@bp.route('/ai/optimize-price', methods=['POST'])
def api_optimize_price():
    try:
        data = request.get_json()
        lot_id = data.get('lot_id')
        spot_type = data.get('spot_type', 'car')
        current_occupancy = data.get('current_occupancy', 50)
        base_price = data.get('base_price', get_spot_default_price(spot_type))
        optimal_price = optimize_price(lot_id, spot_type, current_occupancy, base_price)
        return jsonify({
            "success": True,
            "base_price": base_price,
            "optimal_price": optimal_price,
            "price_change_percent": round(((optimal_price - base_price) / base_price) * 100, 1),
            "recommendation": "Surge pricing" if optimal_price > base_price * 1.2 else "Discount pricing" if optimal_price < base_price * 0.9 else "Standard pricing"
        })
    except Exception as e:
        current_app.logger.error(f"Price optimization error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@bp.route('/ai/recommend-spot', methods=['POST'])
def api_recommend_spot():
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
        current_app.logger.error(f"Spot recommendation error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@bp.route('/ai/forecast/<int:lot_id>', methods=['GET'])
def api_forecast_peak(lot_id):
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
        current_app.logger.error(f"Forecast error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@bp.route('/ai/status', methods=['GET'])
def api_ai_status():
    from ..utils import AI_MODELS # Import AI_MODELS here
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

@bp.route('/end-parking', methods=['POST'])
def end_parking_route():
    return jsonify({"message": "Bookings now end automatically when the reserved time finishes. No manual action needed."}), 410

@bp.route('/bookings')
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
    bookings = [dict(row) for row in cursor.fetchall()]
    return jsonify(bookings)

@bp.route('/smart-search', methods=['POST'])
def smart_search_route():
    payload = request.get_json() or {}
    user_request = (payload.get('user_request') or '').strip()
    requested_start = payload.get('start_time')
    requested_end = payload.get('end_time')

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

    available_spots = [
        dict(row) for row in cursor.fetchall() 
        if spot_is_available(row['lot_id'], row['spot_id'], start_iso, end_iso)
    ]

    if not available_spots:
        return jsonify({"message": "No parking spots available for the selected time window."}), 404

    result = nlp_parser.find_best_match(user_request, available_spots)

    if 'error' in result:
        return jsonify(result), 404

    selected_spot = next((spot for spot in available_spots if int(spot['spot_id']) == int(result['spot_id'])), None)
    if not selected_spot:
        return jsonify({"message": "Matching spot not available for the requested window."}), 404

    price_per_hour = selected_spot['price_per_hour'] or get_spot_default_price(selected_spot['type'])
    total_cost = calculate_total_cost(price_per_hour, start_dt, end_dt)
    
    result.update({
        'price_per_hour': price_per_hour,
        'estimated_cost': total_cost,
        'start_time': start_iso,
        'end_time': end_iso,
        'duration_hours': get_duration_hours(start_dt, end_dt),
        'lot_id': selected_spot['lot_id'],
        'bookings': get_future_bookings(selected_spot['lot_id'], selected_spot['spot_id'])
    })
    return jsonify(result)

@bp.route('/book-spot', methods=['POST'])
def book_spot_route():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"message": "Unauthorized"}), 401

    payload = request.get_json() or {}
    lot_id = payload.get('lot_id')
    spot_id = payload.get('spot_id')
    start_dt = parse_datetime(payload.get('start_time'))
    end_dt = parse_datetime(payload.get('end_time'))

    if not all([lot_id, spot_id, start_dt, end_dt]):
        return jsonify({"message": "Missing booking parameters"}), 400
    if end_dt <= start_dt:
        return jsonify({"message": "End time must be after start time."}), 400

    cursor = get_cursor()
    cursor.execute("SELECT price_per_hour, type FROM spots WHERE lot_id = ? AND spot_id = ?", (lot_id, spot_id))
    spot_row = cursor.fetchone()
    if not spot_row:
        return jsonify({"message": "Spot not found."}), 404

    price_per_hour = spot_row['price_per_hour'] or get_spot_default_price(spot_row['type'])
    booking, error = create_booking(int(lot_id), int(spot_id), user_id, start_dt, end_dt, price_per_hour)
    
    if error:
        return jsonify({"message": error}), 409

    socketio.emit('status_change', {'lot_id': lot_id, 'spot_id': spot_id, 'status': 'booked'})
    return jsonify({"message": "Booking confirmed!", "booking": booking})