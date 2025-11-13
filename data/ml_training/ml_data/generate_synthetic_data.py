"""
Synthetic Data Generator for Smart Parking ML Models
Uses numpy's statistical distributions and realistic patterns to generate training data
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import os

# Set random seeds for reproducibility
np.random.seed(42)
random.seed(42)

# ==================== CONFIGURATION ====================
CONFIG = {
    'num_users': 500,
    'num_lots': 5,
    'start_date': '2025-01-01',
    'end_date': '2025-06-30',
    'base_occupancy_weekday': 0.65,
    'base_occupancy_weekend': 0.45,
    'rush_hour_multiplier': 1.3,
    'weather_impact_rain': 0.15,
    'weather_impact_snow': 0.25,
    'seasonal_variation': 0.2,
    'user_behavior_variance': 0.25,
    'price_elasticity': -0.3,  # % change in demand per % change in price
}

LOT_PROFILES = [
    {'lot_id': 1, 'location': 'Downtown Mall', 'category': 'mall', 'capacity': 150, 'base_price_car': 45, 'has_ev': True},
    {'lot_id': 2, 'location': 'Office District', 'category': 'office', 'capacity': 200, 'base_price_car': 60, 'has_ev': True},
    {'lot_id': 3, 'location': 'Residential Area', 'category': 'residential', 'capacity': 80, 'base_price_car': 25, 'has_ev': False},
    {'lot_id': 4, 'location': 'Transit Hub', 'category': 'transit', 'capacity': 300, 'base_price_car': 35, 'has_ev': True},
    {'lot_id': 5, 'location': 'Hospital Complex', 'category': 'hospital', 'capacity': 120, 'base_price_car': 50, 'has_ev': True},
]

USER_TYPES = {
    'commuter': {'weight': 0.40, 'weekday_prob': 0.85, 'avg_duration': 8, 'price_sensitivity': 'low'},
    'shopper': {'weight': 0.25, 'weekday_prob': 0.40, 'avg_duration': 2, 'price_sensitivity': 'medium'},
    'visitor': {'weight': 0.20, 'weekday_prob': 0.50, 'avg_duration': 3, 'price_sensitivity': 'medium'},
    'resident': {'weight': 0.15, 'weekday_prob': 0.60, 'avg_duration': 12, 'price_sensitivity': 'high'},
}

HOLIDAYS = [
    '2025-01-01',  # New Year
    '2025-01-26',  # Republic Day
    '2025-03-14',  # Holi
    '2025-04-18',  # Good Friday
    '2025-05-01',  # Labour Day
    '2025-06-06',  # Eid
]

# ==================== HELPER FUNCTIONS ====================

def generate_weather(date):
    """Generate realistic weather with seasonal patterns"""
    month = date.month
    
    # Summer months have less rain/snow
    if month in [4, 5, 6]:
        weather_probs = [0.80, 0.15, 0.01, 0.04]  # Clear, Rain, Snow, Cloudy
        temp_range = (25, 40)
    # Monsoon months
    elif month in [7, 8, 9]:
        weather_probs = [0.50, 0.40, 0.0, 0.10]
        temp_range = (22, 32)
    # Winter months
    else:
        weather_probs = [0.65, 0.20, 0.08, 0.07]
        temp_range = (5, 20)
    
    weather = np.random.choice(['Clear', 'Rain', 'Snow', 'Cloudy'], p=weather_probs)
    temp = np.random.uniform(*temp_range)
    
    return weather, round(temp, 1)

def get_occupancy_multiplier(hour, day_of_week, lot_category, is_holiday):
    """Calculate realistic occupancy multiplier based on time and context"""
    base = 1.0
    
    # Holiday effect
    if is_holiday:
        base *= 0.60
    
    # Category-specific patterns
    if lot_category == 'office':
        if day_of_week < 5:  # Weekday
            if 7 <= hour <= 9:
                base *= 1.5  # Morning rush
            elif 17 <= hour <= 19:
                base *= 1.4  # Evening rush
            elif 10 <= hour <= 16:
                base *= 1.2  # Business hours
            elif hour < 6 or hour > 20:
                base *= 0.2  # Off hours
        else:  # Weekend
            base *= 0.15  # Almost empty on weekends
    
    elif lot_category == 'mall':
        if day_of_week >= 5:  # Weekend
            if 11 <= hour <= 20:
                base *= 1.6  # Peak shopping hours
            elif 10 <= hour < 11 or 20 < hour <= 22:
                base *= 1.2
        else:  # Weekday
            if 18 <= hour <= 21:
                base *= 1.3  # Evening shopping
            elif 12 <= hour <= 14:
                base *= 1.1  # Lunch hours
    
    elif lot_category == 'transit':
        if day_of_week < 5:
            if 6 <= hour <= 9:
                base *= 1.7  # Morning commute
            elif 16 <= hour <= 19:
                base *= 1.6  # Evening commute
        else:
            base *= 0.8  # Lower weekend transit
    
    elif lot_category == 'hospital':
        # Hospitals have more stable patterns
        if 8 <= hour <= 18:
            base *= 1.3  # Visiting hours
        elif hour < 6:
            base *= 0.6  # Early morning
    
    elif lot_category == 'residential':
        if hour >= 19 or hour <= 7:
            base *= 1.4  # Evening/night parking
        else:
            base *= 0.6  # Day time lower
    
    return base

def generate_user_profile(user_id):
    """Generate a realistic user profile with consistent behavior"""
    user_type = np.random.choice(
        list(USER_TYPES.keys()),
        p=[v['weight'] for v in USER_TYPES.values()]
    )
    
    profile = USER_TYPES[user_type].copy()
    profile['user_id'] = user_id
    profile['user_type'] = user_type
    
    # Assign preferred locations based on user type
    if user_type == 'commuter':
        profile['preferred_lots'] = [2, 4]  # Office, Transit
    elif user_type == 'shopper':
        profile['preferred_lots'] = [1, 3]  # Mall, Residential
    elif user_type == 'visitor':
        profile['preferred_lots'] = list(range(1, 6))  # Any
    else:  # resident
        profile['preferred_lots'] = [3, 5]  # Residential, Hospital
    
    # Preferred time slots
    if user_type == 'commuter':
        profile['preferred_hours'] = list(range(7, 10)) + list(range(17, 20))
    elif user_type == 'shopper':
        profile['preferred_hours'] = list(range(11, 21))
    else:
        profile['preferred_hours'] = list(range(6, 23))
    
    # Spot type preference
    spot_prefs = ['car', 'car', 'car', 'bike', 'large']  # 60% car, 20% bike, 20% large
    profile['preferred_spot'] = random.choice(spot_prefs)
    
    return profile

# ==================== DATA GENERATORS ====================

def generate_synthetic_users():
    """Generate synthetic user profiles"""
    print("Generating synthetic users...")
    users = []
    
    for user_id in range(1, CONFIG['num_users'] + 1):
        profile = generate_user_profile(user_id)
        
        users.append({
            'user_id': user_id,
            'user_type': profile['user_type'],
            'registration_date': (datetime.strptime(CONFIG['start_date'], '%Y-%m-%d') - 
                                 timedelta(days=random.randint(30, 365))).strftime('%Y-%m-%d'),
            'preferred_spot_type': profile['preferred_spot'],
            'price_sensitivity': profile['price_sensitivity'],
            'avg_booking_duration_hours': profile['avg_duration'],
        })
    
    df = pd.DataFrame(users)
    return df

def generate_lot_features():
    """Generate parking lot feature data"""
    print("Generating lot features...")
    lots = []
    
    for lot in LOT_PROFILES:
        lots.append({
            'lot_id': lot['lot_id'],
            'location': lot['location'],
            'category': lot['category'],
            'total_capacity': lot['capacity'],
            'has_ev_charging': lot['has_ev'],
            'has_security': True,
            'distance_to_transit_meters': random.randint(100, 2000),
            'base_price_car': lot['base_price_car'],
            'base_price_bike': lot['base_price_car'] * 0.3,
            'base_price_large': lot['base_price_car'] * 1.5,
        })
    
    df = pd.DataFrame(lots)
    return df

def generate_events_calendar():
    """Generate events that impact parking demand"""
    print("Generating events calendar...")
    events = []
    
    start = datetime.strptime(CONFIG['start_date'], '%Y-%m-%d')
    end = datetime.strptime(CONFIG['end_date'], '%Y-%m-%d')
    
    # Major events (~2 per month)
    num_events = 12
    for i in range(num_events):
        event_date = start + timedelta(days=random.randint(0, (end - start).days))
        
        event_types = [
            ('Concert', 5000, 2.0),
            ('Sports Match', 8000, 3.0),
            ('Conference', 2000, 1.0),
            ('Festival', 10000, 5.0),
            ('Exhibition', 3000, 2.0),
        ]
        
        event_type, attendance, radius = random.choice(event_types)
        
        events.append({
            'event_date': event_date.strftime('%Y-%m-%d'),
            'event_name': f"{event_type} {i+1}",
            'event_location': random.choice([lot['location'] for lot in LOT_PROFILES]),
            'expected_attendance': attendance,
            'impact_radius_km': radius,
        })
    
    df = pd.DataFrame(events)
    df = df.sort_values('event_date').reset_index(drop=True)
    return df

def generate_historical_occupancy():
    """Generate historical occupancy data (most comprehensive dataset)"""
    print("Generating historical occupancy data...")
    records = []
    
    start = datetime.strptime(CONFIG['start_date'], '%Y-%m-%d')
    end = datetime.strptime(CONFIG['end_date'], '%Y-%m-%d')
    
    holidays = [datetime.strptime(h, '%Y-%m-%d').date() for h in HOLIDAYS]
    events_df = generate_events_calendar()
    event_dates = set(pd.to_datetime(events_df['event_date']).dt.date)
    
    current = start
    
    while current <= end:
        for hour in range(24):
            timestamp = current.replace(hour=hour, minute=0, second=0)
            day_of_week = timestamp.weekday()
            is_weekend = day_of_week >= 5
            is_holiday = timestamp.date() in holidays
            has_event = timestamp.date() in event_dates
            
            weather, temp = generate_weather(timestamp)
            
            for lot in LOT_PROFILES:
                lot_id = lot['lot_id']
                capacity = lot['capacity']
                category = lot['category']
                
                # Base occupancy
                base_occ = CONFIG['base_occupancy_weekend'] if is_weekend else CONFIG['base_occupancy_weekday']
                
                # Apply multipliers
                multiplier = get_occupancy_multiplier(hour, day_of_week, category, is_holiday)
                
                # Weather impact
                if weather == 'Rain':
                    multiplier *= (1 + CONFIG['weather_impact_rain'])
                elif weather == 'Snow':
                    multiplier *= (1 + CONFIG['weather_impact_snow'])
                
                # Event impact
                if has_event:
                    multiplier *= 1.3
                
                # Add some randomness
                noise = np.random.normal(0, CONFIG['user_behavior_variance'])
                
                occupancy_rate = np.clip(base_occ * multiplier + noise, 0.05, 0.98)
                occupied_spots = int(capacity * occupancy_rate)
                
                records.append({
                    'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    'lot_id': lot_id,
                    'day_of_week': day_of_week,
                    'hour': hour,
                    'is_weekend': int(is_weekend),
                    'is_holiday': int(is_holiday),
                    'weather_condition': weather,
                    'temperature': temp,
                    'total_spots': capacity,
                    'occupied_spots': occupied_spots,
                    'occupancy_rate': round(occupancy_rate * 100, 2),
                    'nearby_event': int(has_event),
                    'month': timestamp.month,
                    'is_rush_hour': int((7 <= hour <= 9) or (17 <= hour <= 19)),
                })
        
        current += timedelta(days=1)
    
    df = pd.DataFrame(records)
    return df

def generate_pricing_history(occupancy_df):
    """Generate dynamic pricing data based on occupancy"""
    print("Generating pricing history...")
    records = []
    
    # Sample every 6 hours instead of every hour to reduce size
    sampled_occupancy = occupancy_df[occupancy_df['hour'].isin([0, 6, 12, 18])].copy()
    
    for _, row in sampled_occupancy.iterrows():
        lot = next(l for l in LOT_PROFILES if l['lot_id'] == row['lot_id'])
        
        for spot_type in ['car', 'bike', 'large']:
            base_price = lot['base_price_car']
            if spot_type == 'bike':
                base_price *= 0.3
            elif spot_type == 'large':
                base_price *= 1.5
            
            # Dynamic pricing based on occupancy
            occ_rate = row['occupancy_rate'] / 100
            if occ_rate > 0.85:
                price_multiplier = 1.5  # Surge pricing
            elif occ_rate > 0.70:
                price_multiplier = 1.2
            elif occ_rate < 0.30:
                price_multiplier = 0.8  # Discount
            else:
                price_multiplier = 1.0
            
            dynamic_price = base_price * price_multiplier
            
            # Demand level
            if occ_rate > 0.85:
                demand = 'Critical'
            elif occ_rate > 0.65:
                demand = 'High'
            elif occ_rate > 0.40:
                demand = 'Medium'
            else:
                demand = 'Low'
            
            # Simulate bookings based on price and demand
            bookings_last_hour = int(row['occupied_spots'] * 0.15 * (1 + CONFIG['price_elasticity'] * (price_multiplier - 1)))
            
            # Revenue calculation
            revenue = dynamic_price * bookings_last_hour
            
            # Conversion rate (lower prices = higher conversion)
            conversion_rate = np.clip(0.25 / price_multiplier, 0.05, 0.50)
            
            records.append({
                'timestamp': row['timestamp'],
                'lot_id': row['lot_id'],
                'spot_type': spot_type,
                'base_price': round(base_price, 2),
                'dynamic_price': round(dynamic_price, 2),
                'demand_level': demand,
                'occupancy_rate': row['occupancy_rate'],
                'bookings_last_hour': bookings_last_hour,
                'competitor_avg_price': round(base_price * np.random.uniform(0.9, 1.1), 2),
                'day_of_week': row['day_of_week'],
                'hour': row['hour'],
                'revenue_generated': round(revenue, 2),
                'booking_conversion_rate': round(conversion_rate, 3),
                'time_until_full': max(0, int((100 - row['occupancy_rate']) * 2)),  # Minutes
            })
    
    df = pd.DataFrame(records)
    return df

def generate_user_behavior(users_df, occupancy_df):
    """Generate user booking behavior data"""
    print("Generating user behavior data...")
    records = []
    
    booking_id = 1
    
    for _, user in users_df.iterrows():
        user_id = user['user_id']
        user_type = user['user_type']
        profile = USER_TYPES[user_type]
        
        # Number of bookings per user (varies by type)
        if user_type == 'commuter':
            num_bookings = random.randint(80, 120)  # Frequent
        elif user_type == 'resident':
            num_bookings = random.randint(40, 80)
        else:
            num_bookings = random.randint(20, 50)
        
        preferred_lots = generate_user_profile(user_id)['preferred_lots']
        preferred_hours = generate_user_profile(user_id)['preferred_hours']
        
        for _ in range(num_bookings):
            # Pick a random timestamp from occupancy data
            sample = occupancy_df.sample(1).iloc[0]
            
            # Bias towards preferred lots and hours
            if random.random() < 0.7:  # 70% prefer their usual
                lot_id = random.choice(preferred_lots)
                hour = random.choice(preferred_hours)
                timestamp = pd.to_datetime(sample['timestamp']).replace(hour=hour)
            else:
                lot_id = sample['lot_id']
                timestamp = pd.to_datetime(sample['timestamp'])
            
            lot = next(l for l in LOT_PROFILES if l['lot_id'] == lot_id)
            
            # Duration with variance
            avg_duration = profile['avg_duration']
            duration = max(0.5, np.random.normal(avg_duration, avg_duration * 0.3))
            
            # Price sensitivity affects choice
            base_price = lot['base_price_car']
            if user['preferred_spot_type'] == 'bike':
                base_price *= 0.3
            elif user['preferred_spot_type'] == 'large':
                base_price *= 1.5
            
            # Advance booking time
            if user_type == 'commuter':
                advance_hours = random.randint(12, 48)
            else:
                advance_hours = random.randint(1, 12)
            
            time_of_booking = timestamp - timedelta(hours=advance_hours)
            
            # Time slot
            hour = timestamp.hour
            if 6 <= hour < 12:
                time_slot = 'Morning'
            elif 12 <= hour < 17:
                time_slot = 'Afternoon'
            elif 17 <= hour < 21:
                time_slot = 'Evening'
            else:
                time_slot = 'Night'
            
            records.append({
                'user_id': user_id,
                'booking_id': booking_id,
                'lot_id': lot_id,
                'spot_type': user['preferred_spot_type'],
                'location': lot['location'],
                'distance_from_destination': random.randint(50, 1500),
                'price_per_hour': round(base_price, 2),
                'duration_hours': round(duration, 2),
                'time_of_booking': time_of_booking.strftime('%Y-%m-%d %H:%M:%S'),
                'time_of_arrival': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'preferred_time_slot': time_slot,
                'booking_frequency': num_bookings,
                'avg_duration': round(avg_duration, 2),
                'price_sensitivity': user['price_sensitivity'],
                'location_consistency': round(len(preferred_lots) / CONFIG['num_lots'], 2),
                'advance_booking_time': advance_hours,
                'cancellation_history': random.randint(0, num_bookings // 10),
            })
            
            booking_id += 1
    
    df = pd.DataFrame(records)
    return df

def generate_hourly_patterns(occupancy_df):
    """Generate time-series specific patterns with rolling averages"""
    print("Generating hourly patterns...")
    
    # Use occupancy_df as base and add time-series features
    df = occupancy_df.copy()
    
    # Add week of year
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['week_of_year'] = df['timestamp'].dt.isocalendar().week
    
    # Calculate available spots
    df['spots_available'] = df['total_spots'] - df['occupied_spots']
    
    # Simulate bookings starting and ending
    df['new_bookings_this_hour'] = (df['occupied_spots'] * np.random.uniform(0.1, 0.2, len(df))).astype(int)
    df['bookings_ending_this_hour'] = (df['occupied_spots'] * np.random.uniform(0.08, 0.18, len(df))).astype(int)
    
    # Average duration this hour
    df['avg_duration_this_hour'] = np.random.uniform(1.5, 4.5, len(df)).round(2)
    
    # Rolling averages (by lot)
    for lot_id in df['lot_id'].unique():
        lot_mask = df['lot_id'] == lot_id
        lot_data = df[lot_mask].sort_values('timestamp')
        
        # 7-day rolling average
        df.loc[lot_mask, 'rolling_avg_7days'] = (
            lot_data['occupancy_rate'].rolling(window=24*7, min_periods=1).mean().values
        )
        
        # 30-day rolling average
        df.loc[lot_mask, 'rolling_avg_30days'] = (
            lot_data['occupancy_rate'].rolling(window=24*30, min_periods=1).mean().values
        )
    
    # Peak occupancy prediction (next 3 hours)
    df['peak_occupancy_next_3hrs'] = df.groupby('lot_id')['occupancy_rate'].transform(
        lambda x: x.rolling(window=3, min_periods=1).max().shift(-3).fillna(x)
    )
    
    # Seasonal index (multiplicative)
    df['seasonal_index'] = 1.0 + 0.2 * np.sin(2 * np.pi * df['month'] / 12)
    
    # Trend component (slight upward trend over time)
    df['trend_component'] = 1.0 + 0.0001 * np.arange(len(df))
    
    # Special event flag
    df['special_event_flag'] = df['nearby_event']
    
    # Round values
    df['rolling_avg_7days'] = df['rolling_avg_7days'].round(2)
    df['rolling_avg_30days'] = df['rolling_avg_30days'].round(2)
    df['peak_occupancy_next_3hrs'] = df['peak_occupancy_next_3hrs'].round(2)
    df['seasonal_index'] = df['seasonal_index'].round(3)
    df['trend_component'] = df['trend_component'].round(4)
    
    # Convert timestamp back to string
    df['timestamp'] = df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
    
    return df

# ==================== MAIN EXECUTION ====================

def main():
    print("\n" + "="*60)
    print("Smart Parking ML Data Generator")
    print("="*60 + "\n")
    
    # Create output directory
    output_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate all datasets
    print(f"\nConfiguration:")
    print(f"  Date Range: {CONFIG['start_date']} to {CONFIG['end_date']}")
    print(f"  Users: {CONFIG['num_users']}")
    print(f"  Parking Lots: {CONFIG['num_lots']}")
    print(f"  Expected Bookings: ~{CONFIG['num_users'] * 60}\n")
    
    # 1. Users
    users_df = generate_synthetic_users()
    users_path = os.path.join(output_dir, 'synthetic_users.csv')
    users_df.to_csv(users_path, index=False)
    print(f"✓ Saved: synthetic_users.csv ({len(users_df)} rows)")
    
    # 2. Lot Features
    lots_df = generate_lot_features()
    lots_path = os.path.join(output_dir, 'lot_features.csv')
    lots_df.to_csv(lots_path, index=False)
    print(f"✓ Saved: lot_features.csv ({len(lots_df)} rows)")
    
    # 3. Events
    events_df = generate_events_calendar()
    events_path = os.path.join(output_dir, 'events_calendar.csv')
    events_df.to_csv(events_path, index=False)
    print(f"✓ Saved: events_calendar.csv ({len(events_df)} rows)")
    
    # 4. Historical Occupancy (takes longest)
    occupancy_df = generate_historical_occupancy()
    occupancy_path = os.path.join(output_dir, 'historical_occupancy.csv')
    occupancy_df.to_csv(occupancy_path, index=False)
    print(f"✓ Saved: historical_occupancy.csv ({len(occupancy_df)} rows)")
    
    # 5. Pricing History
    pricing_df = generate_pricing_history(occupancy_df)
    pricing_path = os.path.join(output_dir, 'pricing_history.csv')
    pricing_df.to_csv(pricing_path, index=False)
    print(f"✓ Saved: pricing_history.csv ({len(pricing_df)} rows)")
    
    # 6. User Behavior
    behavior_df = generate_user_behavior(users_df, occupancy_df)
    behavior_path = os.path.join(output_dir, 'user_behavior.csv')
    behavior_df.to_csv(behavior_path, index=False)
    print(f"✓ Saved: user_behavior.csv ({len(behavior_df)} rows)")
    
    # 7. Hourly Patterns
    patterns_df = generate_hourly_patterns(occupancy_df)
    patterns_path = os.path.join(output_dir, 'hourly_patterns.csv')
    patterns_df.to_csv(patterns_path, index=False)
    print(f"✓ Saved: hourly_patterns.csv ({len(patterns_df)} rows)")
    
    print("\n" + "="*60)
    print("Data Generation Complete!")
    print("="*60)
    
    # Summary statistics
    total_size_mb = sum([
        os.path.getsize(p) for p in [
            users_path, lots_path, events_path, occupancy_path,
            pricing_path, behavior_path, patterns_path
        ]
    ]) / (1024 * 1024)
    
    print(f"\nTotal files: 7")
    print(f"Total size: {total_size_mb:.2f} MB")
    print(f"Total records: {len(users_df) + len(lots_df) + len(events_df) + len(occupancy_df) + len(pricing_df) + len(behavior_df) + len(patterns_df):,}")
    print(f"\nFiles saved in: {output_dir}\n")

if __name__ == "__main__":
    main()
