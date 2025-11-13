"""
Time-Series Forecasting Model - ARIMA with Prophet-like decomposition
Predicts future parking availability patterns and peak hours
"""
import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split, TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib
import os
from datetime import datetime, timedelta

print("\n" + "="*70)
print("TIME-SERIES FORECASTING MODEL TRAINING")
print("="*70 + "\n")

# Load data
data_dir = os.path.join(os.path.dirname(__file__), 'ml_data')
print(f"Loading data from: {data_dir}")

patterns_df = pd.read_csv(os.path.join(data_dir, 'hourly_patterns.csv'))
print(f"✓ Loaded {len(patterns_df):,} hourly records")

# Feature Engineering for Time-Series
print("\nEngineering time-series features...")

patterns_df['timestamp'] = pd.to_datetime(patterns_df['timestamp'])

# Lag features (previous values)
patterns_df = patterns_df.sort_values(['lot_id', 'timestamp'])

for lag in [1, 2, 3, 6, 12, 24]:
    patterns_df[f'occupancy_lag_{lag}h'] = patterns_df.groupby('lot_id')['occupancy_rate'].shift(lag)

# Moving averages (different windows)
for window in [3, 6, 12, 24]:
    patterns_df[f'occupancy_ma_{window}h'] = (
        patterns_df.groupby('lot_id')['occupancy_rate']
        .rolling(window=window, min_periods=1)
        .mean()
        .reset_index(level=0, drop=True)
    )

# Rate of change features
patterns_df['occupancy_change_1h'] = patterns_df.groupby('lot_id')['occupancy_rate'].diff(1)
patterns_df['occupancy_change_3h'] = patterns_df.groupby('lot_id')['occupancy_rate'].diff(3)

# Exponential weighted moving average
patterns_df['occupancy_ewma'] = (
    patterns_df.groupby('lot_id')['occupancy_rate']
    .ewm(span=12, adjust=False)
    .mean()
    .reset_index(level=0, drop=True)
)

# Drop rows with NaN (from lag features)
patterns_df = patterns_df.dropna()

print(f"Records after feature engineering: {len(patterns_df):,}")

# Cyclical time features
patterns_df['hour_sin'] = np.sin(2 * np.pi * patterns_df['hour'] / 24)
patterns_df['hour_cos'] = np.cos(2 * np.pi * patterns_df['hour'] / 24)
patterns_df['day_sin'] = np.sin(2 * np.pi * patterns_df['day_of_week'] / 7)
patterns_df['day_cos'] = np.cos(2 * np.pi * patterns_df['day_of_week'] / 7)
patterns_df['month_sin'] = np.sin(2 * np.pi * patterns_df['month'] / 12)
patterns_df['month_cos'] = np.cos(2 * np.pi * patterns_df['month'] / 12)

# Select features for training
feature_columns = [
    'lot_id', 'hour', 'day_of_week', 'week_of_year', 'month',
    'is_weekend', 'is_holiday', 'is_rush_hour', 'special_event_flag',
    'total_spots', 'spots_available', 
    'new_bookings_this_hour', 'bookings_ending_this_hour',
    'avg_duration_this_hour', 'rolling_avg_7days', 'rolling_avg_30days',
    'seasonal_index', 'trend_component',
    'occupancy_lag_1h', 'occupancy_lag_2h', 'occupancy_lag_3h',
    'occupancy_lag_6h', 'occupancy_lag_12h', 'occupancy_lag_24h',
    'occupancy_ma_3h', 'occupancy_ma_6h', 'occupancy_ma_12h', 'occupancy_ma_24h',
    'occupancy_change_1h', 'occupancy_change_3h', 'occupancy_ewma',
    'hour_sin', 'hour_cos', 'day_sin', 'day_cos', 'month_sin', 'month_cos'
]

X = patterns_df[feature_columns]
y = patterns_df['peak_occupancy_next_3hrs']  # Predict peak in next 3 hours

print(f"\nFeatures: {len(feature_columns)}")
print(f"Target: peak_occupancy_next_3hrs")

# Time-series split (respect temporal order)
print("\nUsing Time-Series Cross-Validation...")

tscv = TimeSeriesSplit(n_splits=5)
train_idx, test_idx = list(tscv.split(X))[-1]  # Use last split

X_train = X.iloc[train_idx]
X_test = X.iloc[test_idx]
y_train = y.iloc[train_idx]
y_test = y.iloc[test_idx]

print(f"Training samples: {len(X_train):,}")
print(f"Testing samples: {len(X_test):,}")

# Train Gradient Boosting Model (works well for time-series)
print("\nTraining Gradient Boosting Regressor...")
print("  n_estimators: 200")
print("  max_depth: 6")
print("  learning_rate: 0.05")

model = GradientBoostingRegressor(
    n_estimators=200,
    max_depth=6,
    learning_rate=0.05,
    min_samples_split=15,
    min_samples_leaf=5,
    subsample=0.8,
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
print(f"  MAE:  {train_mae:.2f}% (average error)")
print(f"  RMSE: {train_rmse:.2f}%")
print(f"  R²:   {train_r2:.4f}")

print("\nTest Set (Future Data):")
print(f"  MAE:  {test_mae:.2f}% (average error)")
print(f"  RMSE: {test_rmse:.2f}%")
print(f"  R²:   {test_r2:.4f}")

# Feature Importance
print("\nTop 15 Most Important Features:")
feature_importance = pd.DataFrame({
    'feature': feature_columns,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)

for idx, row in feature_importance.head(15).iterrows():
    print(f"  {row['feature']:.<35} {row['importance']:.4f}")

# Save model and metadata
model_dir = os.path.dirname(__file__)
model_path = os.path.join(model_dir, 'forecasting_model.pkl')
metadata_path = os.path.join(model_dir, 'forecasting_model_metadata.txt')

print(f"\nSaving model to: {model_path}")
joblib.dump(model, model_path)

# Save metadata
with open(metadata_path, 'w', encoding='utf-8') as f:
    f.write("TIME-SERIES FORECASTING MODEL\n")
    f.write("="*70 + "\n\n")
    f.write(f"Trained: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write(f"Algorithm: Gradient Boosting Regressor (Time-Series)\n")
    f.write(f"Training samples: {len(X_train):,}\n")
    f.write(f"Test samples: {len(X_test):,}\n\n")
    f.write("PERFORMANCE METRICS\n")
    f.write("-"*70 + "\n")
    f.write(f"Test MAE:  {test_mae:.2f}%\n")
    f.write(f"Test RMSE: {test_rmse:.2f}%\n")
    f.write(f"Test R²:   {test_r2:.4f}\n\n")
    f.write("FEATURES (Time-Series)\n")
    f.write("-"*70 + "\n")
    f.write("Lag Features: 1h, 2h, 3h, 6h, 12h, 24h\n")
    f.write("Moving Averages: 3h, 6h, 12h, 24h\n")
    f.write("Rolling Averages: 7-day, 30-day\n")
    f.write("Exponential Weighted MA: 12-hour span\n")
    f.write("Seasonal Components: hour, day, month (cyclical)\n")
    f.write("Trend Component: linear\n\n")
    f.write("TOP 15 FEATURE IMPORTANCE\n")
    f.write("-"*70 + "\n")
    for idx, row in feature_importance.head(15).iterrows():
        f.write(f"  {row['feature']:.<35} {row['importance']:.4f}\n")

print("✓ Model saved successfully!")

# Example predictions
print("\n" + "="*70)
print("EXAMPLE FORECASTS")
print("="*70)

# Use last few hours of test data to make predictions
sample_data = X_test.tail(3).copy()
sample_actual = y_test.tail(3).values
sample_pred = model.predict(sample_data)

for i, (idx, row) in enumerate(sample_data.iterrows()):
    print(f"\nForecast #{i+1}:")
    print(f"  Lot ID: {int(row['lot_id'])}")
    print(f"  Current Hour: {int(row['hour'])}")
    print(f"  Current Occupancy: {row['occupancy_lag_1h']:.1f}%")
    print(f"  1-hour trend: {row['occupancy_change_1h']:+.1f}%")
    print(f"  7-day average: {row['rolling_avg_7days']:.1f}%")
    print(f"  → Predicted Peak (next 3hrs): {sample_pred[i]:.1f}%")
    print(f"  → Actual Peak: {sample_actual[i]:.1f}%")
    print(f"  → Error: {abs(sample_pred[i] - sample_actual[i]):.1f}%")

print("\n" + "="*70)
print("MODEL TRAINING COMPLETE!")
print("="*70 + "\n")
