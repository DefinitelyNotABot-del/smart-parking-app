"""
User Preference Learning Model - K-Nearest Neighbors
Recommends parking spots based on user's historical behavior and preferences
"""
import pandas as pd
import numpy as np
from sklearn.neighbors import KNeighborsRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib
import os
from datetime import datetime

print("\n" + "="*70)
print("USER PREFERENCE LEARNING MODEL TRAINING")
print("="*70 + "\n")

# Load data
data_dir = os.path.join(os.path.dirname(__file__), 'ml_data')
print(f"Loading data from: {data_dir}")

behavior_df = pd.read_csv(os.path.join(data_dir, 'user_behavior.csv'))
users_df = pd.read_csv(os.path.join(data_dir, 'synthetic_users.csv'))
print(f"✓ Loaded {len(behavior_df):,} booking records")
print(f"✓ Loaded {len(users_df):,} user profiles")

# Feature Engineering
print("\nEngineering features...")

behavior_df['time_of_arrival'] = pd.to_datetime(behavior_df['time_of_arrival'])
behavior_df['hour_of_arrival'] = behavior_df['time_of_arrival'].dt.hour
behavior_df['day_of_week'] = behavior_df['time_of_arrival'].dt.dayofweek

# Encode categorical variables
spot_type_mapping = {'car': 0, 'bike': 1, 'large': 2}
behavior_df['spot_type_encoded'] = behavior_df['spot_type'].map(spot_type_mapping)

time_slot_mapping = {'Morning': 0, 'Afternoon': 1, 'Evening': 2, 'Night': 3}
behavior_df['time_slot_encoded'] = behavior_df['preferred_time_slot'].map(time_slot_mapping)

price_sens_mapping = {'low': 0, 'medium': 1, 'high': 2}
behavior_df['price_sens_encoded'] = behavior_df['price_sensitivity'].map(price_sens_mapping)

# Aggregate user-level statistics
user_stats = behavior_df.groupby('user_id').agg({
    'lot_id': lambda x: x.mode()[0] if len(x.mode()) > 0 else x.iloc[0],  # Most frequent lot
    'duration_hours': 'mean',
    'price_per_hour': 'mean',
    'distance_from_destination': 'mean',
    'booking_id': 'count'  # Total bookings
}).reset_index()

user_stats.columns = ['user_id', 'preferred_lot', 'avg_duration', 'avg_price_paid', 
                      'avg_distance', 'total_bookings']

# Merge with behavior data
behavior_df = behavior_df.merge(user_stats, on='user_id', how='left')

# Create recommendation score (target variable)
# Score based on: how often user books this type of lot at this time
behavior_df['preference_score'] = (
    behavior_df['booking_frequency'] / 100 +  # Normalized frequency
    (1 - behavior_df['distance_from_destination'] / 1500) +  # Closer is better
    behavior_df['location_consistency'] +  # Consistent location preference
    (1 / (behavior_df['advance_booking_time'] + 1))  # Spontaneous bookings = higher score
)

# Select features for training
feature_columns = [
    'lot_id', 'spot_type_encoded', 'price_per_hour', 'distance_from_destination',
    'hour_of_arrival', 'day_of_week', 'time_slot_encoded', 'duration_hours',
    'booking_frequency', 'price_sens_encoded', 'location_consistency',
    'advance_booking_time', 'preferred_lot', 'avg_price_paid', 'avg_distance'
]

X = behavior_df[feature_columns]
y = behavior_df['preference_score']

print(f"Features: {len(feature_columns)}")
print(f"Target: preference_score (0-4, higher = more preferred)")

# Split data
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, shuffle=True
)

print(f"\nTraining samples: {len(X_train):,}")
print(f"Testing samples: {len(X_test):,}")

# Scale features (KNN requires normalization)
print("\nNormalizing features...")
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# Train KNN Model
print("\nTraining K-Nearest Neighbors Regressor...")
print("  n_neighbors: 15")
print("  weights: distance")
print("  metric: euclidean")

model = KNeighborsRegressor(
    n_neighbors=15,
    weights='distance',
    metric='euclidean',
    n_jobs=-1
)

model.fit(X_train_scaled, y_train)
print("✓ Training complete!")

# Evaluate model
print("\nEvaluating model performance...")

y_pred_train = model.predict(X_train_scaled)
y_pred_test = model.predict(X_test_scaled)

train_mae = mean_absolute_error(y_train, y_pred_train)
test_mae = mean_absolute_error(y_test, y_pred_test)

train_rmse = np.sqrt(mean_squared_error(y_train, y_pred_train))
test_rmse = np.sqrt(mean_squared_error(y_test, y_pred_test))

train_r2 = r2_score(y_train, y_pred_train)
test_r2 = r2_score(y_test, y_pred_test)

print("\nTraining Set:")
print(f"  MAE:  {train_mae:.4f} (average score error)")
print(f"  RMSE: {train_rmse:.4f}")
print(f"  R²:   {train_r2:.4f}")

print("\nTest Set (Unseen Data):")
print(f"  MAE:  {test_mae:.4f} (average score error)")
print(f"  RMSE: {test_rmse:.4f}")
print(f"  R²:   {test_r2:.4f}")

# Save model, scaler, and metadata
model_dir = os.path.dirname(__file__)
model_path = os.path.join(model_dir, 'preference_model.pkl')
scaler_path = os.path.join(model_dir, 'preference_scaler.pkl')
metadata_path = os.path.join(model_dir, 'preference_model_metadata.txt')

print(f"\nSaving model to: {model_path}")
joblib.dump(model, model_path)
joblib.dump(scaler, scaler_path)

# Save metadata
with open(metadata_path, 'w', encoding='utf-8') as f:
    f.write("USER PREFERENCE LEARNING MODEL\n")
    f.write("="*70 + "\n\n")
    f.write(f"Trained: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write(f"Algorithm: K-Nearest Neighbors Regressor\n")
    f.write(f"Training samples: {len(X_train):,}\n")
    f.write(f"Test samples: {len(X_test):,}\n\n")
    f.write("PERFORMANCE METRICS\n")
    f.write("-"*70 + "\n")
    f.write(f"Test MAE:  {test_mae:.4f}\n")
    f.write(f"Test RMSE: {test_rmse:.4f}\n")
    f.write(f"Test R²:   {test_r2:.4f}\n\n")
    f.write("FEATURES (Normalized)\n")
    f.write("-"*70 + "\n")
    for feat in feature_columns:
        f.write(f"  - {feat}\n")
    f.write("\n")
    f.write("NOTE: Features are scaled using StandardScaler\n")
    f.write("Scaler saved to: preference_scaler.pkl\n")

print("✓ Model and scaler saved successfully!")

# Example predictions
print("\n" + "="*70)
print("EXAMPLE PREFERENCE PREDICTIONS")
print("="*70)

scenarios = [
    {
        'name': 'Frequent Commuter - Office Lot',
        'lot_id': 2, 'spot_type_encoded': 0, 'price_per_hour': 60, 
        'distance_from_destination': 200, 'hour_of_arrival': 8, 'day_of_week': 1,
        'time_slot_encoded': 0, 'duration_hours': 8, 'booking_frequency': 100,
        'price_sens_encoded': 0, 'location_consistency': 0.8, 'advance_booking_time': 24,
        'preferred_lot': 2, 'avg_price_paid': 58, 'avg_distance': 250
    },
    {
        'name': 'Weekend Shopper - Mall',
        'lot_id': 1, 'spot_type_encoded': 0, 'price_per_hour': 45,
        'distance_from_destination': 100, 'hour_of_arrival': 14, 'day_of_week': 6,
        'time_slot_encoded': 1, 'duration_hours': 2.5, 'booking_frequency': 30,
        'price_sens_encoded': 1, 'location_consistency': 0.4, 'advance_booking_time': 3,
        'preferred_lot': 1, 'avg_price_paid': 42, 'avg_distance': 300
    },
    {
        'name': 'Price-Sensitive Resident',
        'lot_id': 3, 'spot_type_encoded': 1, 'price_per_hour': 20,
        'distance_from_destination': 50, 'hour_of_arrival': 19, 'day_of_week': 4,
        'time_slot_encoded': 2, 'duration_hours': 10, 'booking_frequency': 60,
        'price_sens_encoded': 2, 'location_consistency': 0.9, 'advance_booking_time': 6,
        'preferred_lot': 3, 'avg_price_paid': 22, 'avg_distance': 80
    }
]

for scenario in scenarios:
    scenario_df = pd.DataFrame([scenario])
    scenario_scaled = scaler.transform(scenario_df[feature_columns])
    
    preference_score = model.predict(scenario_scaled)[0]
    
    print(f"\n{scenario['name']}")
    print(f"  Lot ID: {scenario['lot_id']}")
    print(f"  Distance: {scenario['distance_from_destination']}m")
    print(f"  Price: ₹{scenario['price_per_hour']}/hr")
    print(f"  → Preference Score: {preference_score:.3f}/4.0")
    print(f"  → Match Quality: {'Excellent' if preference_score > 3 else 'Good' if preference_score > 2 else 'Fair'}")

print("\n" + "="*70)
print("MODEL TRAINING COMPLETE!")
print("="*70 + "\n")
