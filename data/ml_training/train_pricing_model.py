"""
Price Optimization Model - Gradient Boosting
Recommends optimal pricing based on demand, occupancy, and market conditions
"""
import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib
import os
from datetime import datetime

print("\n" + "="*70)
print("PRICE OPTIMIZATION MODEL TRAINING")
print("="*70 + "\n")

# Load data
data_dir = os.path.join(os.path.dirname(__file__), 'ml_data')
print(f"Loading data from: {data_dir}")

pricing_df = pd.read_csv(os.path.join(data_dir, 'pricing_history.csv'))
print(f"✓ Loaded {len(pricing_df):,} pricing records")

# Feature Engineering
print("\nEngineering features...")

pricing_df['timestamp'] = pd.to_datetime(pricing_df['timestamp'])

# Encode categorical variables
spot_type_mapping = {'car': 0, 'bike': 1, 'large': 2}
pricing_df['spot_type_encoded'] = pricing_df['spot_type'].map(spot_type_mapping)

demand_mapping = {'Low': 0, 'Medium': 1, 'High': 2, 'Critical': 3}
pricing_df['demand_encoded'] = pricing_df['demand_level'].map(demand_mapping)

# Price elasticity features
pricing_df['price_to_competitor_ratio'] = pricing_df['dynamic_price'] / pricing_df['competitor_avg_price']
pricing_df['revenue_per_booking'] = pricing_df['revenue_generated'] / (pricing_df['bookings_last_hour'] + 1)

# Time features
pricing_df['hour_sin'] = np.sin(2 * np.pi * pricing_df['hour'] / 24)
pricing_df['hour_cos'] = np.cos(2 * np.pi * pricing_df['hour'] / 24)
pricing_df['day_sin'] = np.sin(2 * np.pi * pricing_df['day_of_week'] / 7)
pricing_df['day_cos'] = np.cos(2 * np.pi * pricing_df['day_of_week'] / 7)

# Target: We want to predict optimal dynamic_price that maximizes revenue
# But we'll train on actual revenue_generated and booking_conversion_rate

# Select features
feature_columns = [
    'lot_id', 'spot_type_encoded', 'base_price', 'demand_encoded',
    'occupancy_rate', 'bookings_last_hour', 'competitor_avg_price',
    'hour', 'day_of_week', 'booking_conversion_rate', 'time_until_full',
    'hour_sin', 'hour_cos', 'day_sin', 'day_cos',
    'price_to_competitor_ratio'
]

X = pricing_df[feature_columns]
y = pricing_df['dynamic_price']  # Predict optimal price

print(f"Features: {len(feature_columns)}")
print(f"Target: dynamic_price (optimal price)")

# Split data
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, shuffle=True
)

print(f"\nTraining samples: {len(X_train):,}")
print(f"Testing samples: {len(X_test):,}")

# Train Gradient Boosting Model
print("\nTraining Gradient Boosting Regressor...")
print("  n_estimators: 150")
print("  max_depth: 5")
print("  learning_rate: 0.1")

model = GradientBoostingRegressor(
    n_estimators=150,
    max_depth=5,
    learning_rate=0.1,
    min_samples_split=10,
    min_samples_leaf=5,
    random_state=42,
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
print(f"  MAE:  ₹{train_mae:.2f} (average price error)")
print(f"  RMSE: ₹{train_rmse:.2f}")
print(f"  R²:   {train_r2:.4f}")

print("\nTest Set (Unseen Data):")
print(f"  MAE:  ₹{test_mae:.2f} (average price error)")
print(f"  RMSE: ₹{test_rmse:.2f}")
print(f"  R²:   {test_r2:.4f}")

# Feature Importance
print("\nTop 10 Most Important Features:")
feature_importance = pd.DataFrame({
    'feature': feature_columns,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)

for idx, row in feature_importance.head(10).iterrows():
    print(f"  {row['feature']:.<35} {row['importance']:.4f}")

# Save model and metadata
model_dir = os.path.dirname(__file__)
model_path = os.path.join(model_dir, 'pricing_model.pkl')
metadata_path = os.path.join(model_dir, 'pricing_model_metadata.txt')

print(f"\nSaving model to: {model_path}")
joblib.dump(model, model_path)

# Save metadata
with open(metadata_path, 'w', encoding='utf-8') as f:
    f.write("PRICE OPTIMIZATION MODEL\n")
    f.write("="*70 + "\n\n")
    f.write(f"Trained: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write(f"Algorithm: Gradient Boosting Regressor\n")
    f.write(f"Training samples: {len(X_train):,}\n")
    f.write(f"Test samples: {len(X_test):,}\n\n")
    f.write("PERFORMANCE METRICS\n")
    f.write("-"*70 + "\n")
    f.write(f"Test MAE:  ₹{test_mae:.2f}\n")
    f.write(f"Test RMSE: ₹{test_rmse:.2f}\n")
    f.write(f"Test R²:   {test_r2:.4f}\n\n")
    f.write("FEATURES\n")
    f.write("-"*70 + "\n")
    for feat in feature_columns:
        f.write(f"  - {feat}\n")
    f.write("\n")
    f.write("TOP 10 FEATURE IMPORTANCE\n")
    f.write("-"*70 + "\n")
    for idx, row in feature_importance.head(10).iterrows():
        f.write(f"  {row['feature']:.<35} {row['importance']:.4f}\n")

print("✓ Model saved successfully!")

# Example predictions
print("\n" + "="*70)
print("EXAMPLE PRICE RECOMMENDATIONS")
print("="*70)

scenarios = [
    {
        'name': 'High Demand - Car Spot',
        'lot_id': 1, 'spot_type_encoded': 0, 'base_price': 45, 'demand_encoded': 2,
        'occupancy_rate': 85, 'bookings_last_hour': 25, 'competitor_avg_price': 50,
        'hour': 18, 'day_of_week': 2, 'booking_conversion_rate': 0.35, 'time_until_full': 20
    },
    {
        'name': 'Low Demand - Bike Spot',
        'lot_id': 3, 'spot_type_encoded': 1, 'base_price': 15, 'demand_encoded': 0,
        'occupancy_rate': 30, 'bookings_last_hour': 5, 'competitor_avg_price': 18,
        'hour': 14, 'day_of_week': 6, 'booking_conversion_rate': 0.15, 'time_until_full': 180
    },
    {
        'name': 'Critical Demand - Large Spot',
        'lot_id': 2, 'spot_type_encoded': 2, 'base_price': 75, 'demand_encoded': 3,
        'occupancy_rate': 95, 'bookings_last_hour': 40, 'competitor_avg_price': 85,
        'hour': 8, 'day_of_week': 1, 'booking_conversion_rate': 0.45, 'time_until_full': 5
    }
]

for scenario in scenarios:
    scenario_df = pd.DataFrame([scenario])
    
    # Add cyclical features
    scenario_df['hour_sin'] = np.sin(2 * np.pi * scenario_df['hour'] / 24)
    scenario_df['hour_cos'] = np.cos(2 * np.pi * scenario_df['hour'] / 24)
    scenario_df['day_sin'] = np.sin(2 * np.pi * scenario_df['day_of_week'] / 7)
    scenario_df['day_cos'] = np.cos(2 * np.pi * scenario_df['day_of_week'] / 7)
    scenario_df['price_to_competitor_ratio'] = scenario_df['base_price'] / scenario_df['competitor_avg_price']
    
    optimal_price = model.predict(scenario_df[feature_columns])[0]
    
    print(f"\n{scenario['name']}")
    print(f"  Base Price: ₹{scenario['base_price']:.2f}/hr")
    print(f"  Competitor Avg: ₹{scenario['competitor_avg_price']:.2f}/hr")
    print(f"  Recommended Price: ₹{optimal_price:.2f}/hr")
    print(f"  Price Change: {((optimal_price - scenario['base_price']) / scenario['base_price'] * 100):+.1f}%")

print("\n" + "="*70)
print("MODEL TRAINING COMPLETE!")
print("="*70 + "\n")
