"""
Occupancy Prediction Model - Random Forest Regressor
Predicts parking lot occupancy rate based on time, weather, and historical patterns
"""
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib
import os
from datetime import datetime

print("\n" + "="*70)
print("OCCUPANCY PREDICTION MODEL TRAINING")
print("="*70 + "\n")

# Load data
data_dir = os.path.join(os.path.dirname(__file__), 'ml_data')
print(f"Loading data from: {data_dir}")

occupancy_df = pd.read_csv(os.path.join(data_dir, 'historical_occupancy.csv'))
print(f"✓ Loaded {len(occupancy_df):,} occupancy records")

# Feature Engineering
print("\nEngineering features...")

# Convert timestamp
occupancy_df['timestamp'] = pd.to_datetime(occupancy_df['timestamp'])

# Create additional features
occupancy_df['day_of_month'] = occupancy_df['timestamp'].dt.day
occupancy_df['week_of_year'] = occupancy_df['timestamp'].dt.isocalendar().week
occupancy_df['is_month_start'] = (occupancy_df['timestamp'].dt.day <= 7).astype(int)
occupancy_df['is_month_end'] = (occupancy_df['timestamp'].dt.day >= 24).astype(int)

# Encode categorical variables
weather_mapping = {'Clear': 0, 'Rain': 1, 'Snow': 2, 'Cloudy': 3}
occupancy_df['weather_encoded'] = occupancy_df['weather_condition'].map(weather_mapping)

# Cyclical encoding for hour and day of week (captures circular nature)
occupancy_df['hour_sin'] = np.sin(2 * np.pi * occupancy_df['hour'] / 24)
occupancy_df['hour_cos'] = np.cos(2 * np.pi * occupancy_df['hour'] / 24)
occupancy_df['day_sin'] = np.sin(2 * np.pi * occupancy_df['day_of_week'] / 7)
occupancy_df['day_cos'] = np.cos(2 * np.pi * occupancy_df['day_of_week'] / 7)

# Select features for training
feature_columns = [
    'lot_id', 'hour', 'day_of_week', 'month', 'day_of_month', 'week_of_year',
    'is_weekend', 'is_holiday', 'is_rush_hour', 'nearby_event',
    'is_month_start', 'is_month_end',
    'weather_encoded', 'temperature', 'total_spots',
    'hour_sin', 'hour_cos', 'day_sin', 'day_cos'
]

X = occupancy_df[feature_columns]
y = occupancy_df['occupancy_rate']

print(f"Features: {len(feature_columns)}")
print(f"Target: occupancy_rate (0-100%)")

# Split data (80% train, 20% test)
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, shuffle=True
)

print(f"\nTraining samples: {len(X_train):,}")
print(f"Testing samples: {len(X_test):,}")

# Train Random Forest Model
print("\nTraining Random Forest Regressor...")
print("  n_estimators: 100")
print("  max_depth: 20")
print("  min_samples_split: 10")

model = RandomForestRegressor(
    n_estimators=100,
    max_depth=20,
    min_samples_split=10,
    min_samples_leaf=5,
    random_state=42,
    n_jobs=-1,
    verbose=0
)

model.fit(X_train, y_train)
print("✓ Training complete!")

# Evaluate model
print("\nEvaluating model performance...")

y_pred_train = model.predict(X_train)
y_pred_test = model.predict(X_test)

train_mae = mean_absolute_error(y_train, y_pred_train)
test_mae = mean_absolute_error(y_test, y_pred_test)

train_rmse = np.sqrt(mean_squared_error(y_train, y_pred_train))
test_rmse = np.sqrt(mean_squared_error(y_test, y_pred_test))

train_r2 = r2_score(y_train, y_pred_train)
test_r2 = r2_score(y_test, y_pred_test)

print("\nTraining Set:")
print(f"  MAE:  {train_mae:.2f}% (average error)")
print(f"  RMSE: {train_rmse:.2f}%")
print(f"  R²:   {train_r2:.4f} (variance explained)")

print("\nTest Set (Unseen Data):")
print(f"  MAE:  {test_mae:.2f}% (average error)")
print(f"  RMSE: {test_rmse:.2f}%")
print(f"  R²:   {test_r2:.4f} (variance explained)")

# Feature Importance
print("\nTop 10 Most Important Features:")
feature_importance = pd.DataFrame({
    'feature': feature_columns,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)

for idx, row in feature_importance.head(10).iterrows():
    print(f"  {row['feature']:.<30} {row['importance']:.4f}")

# Save model and metadata
model_dir = os.path.dirname(__file__)
model_path = os.path.join(model_dir, 'occupancy_model.pkl')
metadata_path = os.path.join(model_dir, 'occupancy_model_metadata.txt')

print(f"\nSaving model to: {model_path}")
joblib.dump(model, model_path)

# Save metadata
with open(metadata_path, 'w', encoding='utf-8') as f:
    f.write("OCCUPANCY PREDICTION MODEL\n")
    f.write("="*70 + "\n\n")
    f.write(f"Trained: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write(f"Algorithm: Random Forest Regressor\n")
    f.write(f"Training samples: {len(X_train):,}\n")
    f.write(f"Test samples: {len(X_test):,}\n\n")
    f.write("PERFORMANCE METRICS\n")
    f.write("-"*70 + "\n")
    f.write(f"Test MAE:  {test_mae:.2f}%\n")
    f.write(f"Test RMSE: {test_rmse:.2f}%\n")
    f.write(f"Test R²:   {test_r2:.4f}\n\n")
    f.write("FEATURES\n")
    f.write("-"*70 + "\n")
    for feat in feature_columns:
        f.write(f"  - {feat}\n")
    f.write("\n")
    f.write("TOP 10 FEATURE IMPORTANCE\n")
    f.write("-"*70 + "\n")
    for idx, row in feature_importance.head(10).iterrows():
        f.write(f"  {row['feature']:.<30} {row['importance']:.4f}\n")

print("✓ Model saved successfully!")

# Example predictions
print("\n" + "="*70)
print("EXAMPLE PREDICTIONS")
print("="*70)

# Test scenarios
scenarios = [
    {
        'name': 'Monday Morning Rush - Downtown Mall',
        'lot_id': 1, 'hour': 8, 'day_of_week': 0, 'month': 6, 'day_of_month': 15,
        'week_of_year': 24, 'is_weekend': 0, 'is_holiday': 0, 'is_rush_hour': 1,
        'nearby_event': 0, 'is_month_start': 0, 'is_month_end': 0,
        'weather_encoded': 0, 'temperature': 25, 'total_spots': 150
    },
    {
        'name': 'Saturday Afternoon - Mall',
        'lot_id': 1, 'hour': 14, 'day_of_week': 5, 'month': 6, 'day_of_month': 20,
        'week_of_year': 25, 'is_weekend': 1, 'is_holiday': 0, 'is_rush_hour': 0,
        'nearby_event': 0, 'is_month_start': 0, 'is_month_end': 0,
        'weather_encoded': 1, 'temperature': 28, 'total_spots': 150
    },
    {
        'name': 'Tuesday Evening - Office District',
        'lot_id': 2, 'hour': 18, 'day_of_week': 1, 'month': 6, 'day_of_month': 10,
        'week_of_year': 23, 'is_weekend': 0, 'is_holiday': 0, 'is_rush_hour': 1,
        'nearby_event': 0, 'is_month_start': 0, 'is_month_end': 0,
        'weather_encoded': 0, 'temperature': 30, 'total_spots': 200
    }
]

for scenario in scenarios:
    scenario_df = pd.DataFrame([scenario])
    
    # Add cyclical features
    scenario_df['hour_sin'] = np.sin(2 * np.pi * scenario_df['hour'] / 24)
    scenario_df['hour_cos'] = np.cos(2 * np.pi * scenario_df['hour'] / 24)
    scenario_df['day_sin'] = np.sin(2 * np.pi * scenario_df['day_of_week'] / 7)
    scenario_df['day_cos'] = np.cos(2 * np.pi * scenario_df['day_of_week'] / 7)
    
    prediction = model.predict(scenario_df[feature_columns])[0]
    
    print(f"\n{scenario['name']}")
    print(f"  Predicted Occupancy: {prediction:.1f}%")
    print(f"  Available Spots: ~{int(scenario['total_spots'] * (1 - prediction/100))}")

print("\n" + "="*70)
print("MODEL TRAINING COMPLETE!")
print("="*70 + "\n")
