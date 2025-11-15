import os
import joblib
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from flask import current_app, session

# Note: These functions now rely on the application context for db access and logging.
# They will be called from routes where the context is available.
from .db import get_cursor, get_db

DEFAULT_PRICING = {
    'large': 50.0,
    'car': 40.0,
    'motorcycle': 15.0,
    'bike': 15.0,
    'truck': 75.0
}

TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

DEMO_EMAILS = [
    'demo.owner@smartparking.com',
    'demo.customer@smartparking.com'
]

def is_demo_account(email):
    """Check if email is a demo account with pre-generated data"""
    return email.lower() in [e.lower() for e in DEMO_EMAILS]

# --- AI Model Loading ---
AI_MODELS = {}

def load_model(model_name):
    """Lazy load ML models on-demand. Returns None if model unavailable (cloud-safe)."""
    global AI_MODELS
    if model_name in AI_MODELS:
        return AI_MODELS[model_name]
    
    ML_MODELS_DIR = os.path.join(current_app.root_path, '..', 'data/ml_training')
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
            current_app.logger.info(f"Model file not found (OK for cloud deployment): {model_path}")
            return None
        model = joblib.load(model_path)
        if hasattr(model, 'n_jobs'):
            model.n_jobs = 1  # Critical for Azure F1 tier
        AI_MODELS[model_name] = model
        current_app.logger.info(f"✓ Loaded {model_name} model on-demand (single-threaded)")
        return AI_MODELS[model_name]
    except MemoryError:
        current_app.logger.error(f"Out of memory loading {model_name} - running without AI features")
        return None
    except Exception as e:
        current_app.logger.warning(f"Failed to load {model_name} model (app will work without AI): {e}")
        return None

# --- Utility Functions ---
def parse_datetime(value):
    if not value: return None
    value = value.rstrip('Z') if value.endswith('Z') else value
    try: return datetime.fromisoformat(value)
    except ValueError:
        try: return datetime.strptime(value, TIME_FORMAT)
        except ValueError: return None

def format_datetime(dt):
    return dt.strftime(TIME_FORMAT)

def default_booking_window():
    # Use local time consistently, not UTC
    start = datetime.now().replace(second=0, microsecond=0)
    end = start + timedelta(hours=1)
    return start, end

def get_duration_hours(start_dt, end_dt):
    duration = (end_dt - start_dt).total_seconds() / 3600
    if duration <= 0: raise ValueError("End time must be after start time")
    return round(duration, 2)

def calculate_total_cost(price_per_hour, start_dt, end_dt):
    hours = get_duration_hours(start_dt, end_dt)
    return round(price_per_hour * hours, 2)

def get_spot_default_price(spot_type):
    return DEFAULT_PRICING.get(spot_type, DEFAULT_PRICING.get('car', 40.0))

def coerce_price(value, fallback):
    try:
        if value is None or value == "": return round(float(fallback), 2)
        price = float(value)
        if price < 0: raise ValueError("Price must be non-negative")
        return round(price, 2)
    except (TypeError, ValueError):
        current_app.logger.warning(f"Invalid price input '{value}', using fallback {fallback}")
        return round(float(fallback), 2)

def spot_is_available(lot_id, spot_id, start_iso, end_iso):
    cursor = get_cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM bookings WHERE lot_id = ? AND spot_id = ? AND NOT (? <= start_time OR ? >= end_time)",
        (lot_id, spot_id, end_iso, start_iso)
    )
    return cursor.fetchone()[0] == 0

def get_future_bookings(lot_id, spot_id, limit=20):
    cursor = get_cursor()
    cursor.execute(
        "SELECT b.start_time, b.end_time, b.total_cost FROM bookings b JOIN spots s ON b.spot_id = s.spot_id AND b.lot_id = s.lot_id WHERE s.lot_id = ? AND s.spot_id = ? AND b.end_time >= ? ORDER BY b.start_time ASC LIMIT ?",
        (lot_id, spot_id, format_datetime(datetime.now()), limit)
    )
    return [dict(row) for row in cursor.fetchall()]

# --- AI Prediction Functions ---
def predict_occupancy(lot_id, target_datetime=None):
    model = load_model('occupancy')
    if model is None: return None
    if target_datetime is None: target_datetime = datetime.now()
    cursor = get_cursor()
    cursor.execute("SELECT COUNT(*) as capacity FROM spots WHERE lot_id = ?", (lot_id,))
    capacity = cursor.fetchone()['capacity']
    features = { 'lot_id': lot_id, 'hour': target_datetime.hour, 'day_of_week': target_datetime.weekday(), 'month': target_datetime.month, 'day_of_month': target_datetime.day, 'week_of_year': target_datetime.isocalendar()[1], 'is_weekend': int(target_datetime.weekday() >= 5), 'is_holiday': 0, 'is_rush_hour': int((7 <= target_datetime.hour <= 9) or (17 <= target_datetime.hour <= 19)), 'nearby_event': 0, 'is_month_start': int(target_datetime.day <= 7), 'is_month_end': int(target_datetime.day >= 24), 'weather_encoded': 0, 'temperature': 25, 'total_spots': capacity, 'hour_sin': np.sin(2 * np.pi * target_datetime.hour / 24), 'hour_cos': np.cos(2 * np.pi * target_datetime.hour / 24), 'day_sin': np.sin(2 * np.pi * target_datetime.weekday() / 7), 'day_cos': np.cos(2 * np.pi * target_datetime.weekday() / 7) }
    df = pd.DataFrame([features])
    prediction = model.predict(df)[0]
    return { 'occupancy_rate': round(prediction, 1), 'predicted_available': int(capacity * (1 - prediction/100)), 'predicted_occupied': int(capacity * (prediction/100)), 'total_capacity': capacity }

def optimize_price(lot_id, spot_type, current_occupancy_rate, base_price):
    model = load_model('pricing')
    if model is None: return {'optimal_price': base_price}
    now = datetime.now()
    spot_type_mapping = {'car': 0, 'bike': 1, 'large': 2, 'motorcycle': 1, 'truck': 2}
    spot_type_encoded = spot_type_mapping.get(spot_type, 0)
    if current_occupancy_rate > 85: demand_encoded = 3
    elif current_occupancy_rate > 65: demand_encoded = 2
    elif current_occupancy_rate > 40: demand_encoded = 1
    else: demand_encoded = 0
    bookings_last_hour = int(current_occupancy_rate * 0.15)
    competitor_avg = base_price * 1.05
    conversion_rate = 0.25
    time_until_full = max(0, int((100 - current_occupancy_rate) * 2))
    features = { 'lot_id': lot_id, 'spot_type_encoded': spot_type_encoded, 'base_price': base_price, 'demand_encoded': demand_encoded, 'occupancy_rate': current_occupancy_rate, 'bookings_last_hour': bookings_last_hour, 'competitor_avg_price': competitor_avg, 'hour': now.hour, 'day_of_week': now.weekday(), 'booking_conversion_rate': conversion_rate, 'time_until_full': time_until_full, 'hour_sin': np.sin(2 * np.pi * now.hour / 24), 'hour_cos': np.cos(2 * np.pi * now.hour / 24), 'day_sin': np.sin(2 * np.pi * now.weekday() / 7), 'day_cos': np.cos(2 * np.pi * now.weekday() / 7), 'price_to_competitor_ratio': base_price / competitor_avg }
    df = pd.DataFrame([features])
    optimal_price = model.predict(df)[0]
    return {'optimal_price': round(optimal_price, 2)}

def recommend_spot_for_user(user_id, available_spots):
    model = load_model('preference')
    scaler = load_model('preference_scaler')
    if model is None or scaler is None:
        current_app.logger.warning("Preference model or scaler not available, returning first available spot.")
        return available_spots[0] if available_spots else None

    cursor = get_cursor()
    cursor.execute("SELECT lot_id, spot_id, start_time, end_time FROM bookings WHERE user_id = ? ORDER BY end_time DESC LIMIT 10", (user_id,))
    recent_bookings = cursor.fetchall()

    features = []
    for spot in available_spots:
        # Example features, adapt based on your model's training data
        # This is a placeholder, actual features should match model's expectation
        f = [
            spot.get('lot_id', 0),
            spot.get('spot_id', 0),
            spot.get('price_per_hour', 0),
            1 if spot.get('type') == 'large' else 0,
            1 if spot.get('type') == 'motorcycle' else 0,
            # Add more features that your model was trained on
        ]
        features.append(f)

    if not features:
        return available_spots[0] if available_spots else None

    features_scaled = scaler.transform(features)
    probabilities = model.predict_proba(features_scaled)
    
    # Assuming the model predicts a preference score or probability for each spot
    # We'll take the spot with the highest probability for the 'preferred' class
    preferred_spot_index = np.argmax(probabilities[:, 1]) # Assuming class 1 is 'preferred'

    return available_spots[preferred_spot_index]

def forecast_peak_hours(lot_id, hours_ahead=24):
    model = load_model('forecasting')
    if model is None:
        current_app.logger.warning("Forecasting model not available.")
        return None

    # Generate future time steps for forecasting
    future_times = [datetime.now() + timedelta(hours=i) for i in range(1, hours_ahead + 1)]
    
    forecast_data = []
    for ft in future_times:
        # Features must match what the forecasting model expects
        # This is a placeholder, adapt based on your model's training data
        features = {
            'lot_id': lot_id,
            'hour': ft.hour,
            'day_of_week': ft.weekday(),
            'month': ft.month,
            'day_of_month': ft.day,
            'is_weekend': int(ft.weekday() >= 5),
            'hour_sin': np.sin(2 * np.pi * ft.hour / 24),
            'hour_cos': np.cos(2 * np.pi * ft.hour / 24),
            'day_sin': np.sin(2 * np.pi * ft.weekday() / 7),
            'day_cos': np.cos(2 * np.pi * ft.weekday() / 7),
        }
        forecast_data.append(features)

    if not forecast_data:
        return None

    df_forecast = pd.DataFrame(forecast_data)
    predictions = model.predict(df_forecast)

    results = []
    for i, pred in enumerate(predictions):
        results.append({
            "time": future_times[i].strftime("%Y-%m-%d %H:%M"),
            "predicted_occupancy_rate": round(pred, 2)
        })
    return results

# --- Booking Utilities ---
def create_booking(lot_id, spot_id, user_id, start_dt, end_dt, price_per_hour):
    start_iso = format_datetime(start_dt)
    end_iso = format_datetime(end_dt)
    if not spot_is_available(lot_id, spot_id, start_iso, end_iso):
        return None, "Spot is no longer available for that time window."
    total_cost = calculate_total_cost(price_per_hour, start_dt, end_dt)
    db_conn = get_db()
    cursor = db_conn.cursor()
    try:
        cursor.execute( "INSERT INTO bookings (lot_id, spot_id, user_id, start_time, end_time, price_per_hour, total_cost) VALUES (?, ?, ?, ?, ?, ?, ?)", (lot_id, spot_id, user_id, start_iso, end_iso, price_per_hour, total_cost) )
        db_conn.commit()
    except Exception as exc:
        current_app.logger.error(f"Booking insert failed for lot {lot_id}, spot {spot_id}: {exc}", exc_info=True)
        db_conn.rollback()
        return None, "Failed to create booking."
    return { "booking_id": cursor.lastrowid, "lot_id": lot_id, "spot_id": spot_id, "start_time": start_iso, "end_time": end_iso, "total_cost": total_cost, "price_per_hour": price_per_hour }, None
