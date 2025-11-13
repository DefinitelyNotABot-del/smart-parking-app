"""
Master Training Script - Trains all 4 ML models
Run this script to train all AI models for the Smart Parking system
"""
import subprocess
import sys
import os
from datetime import datetime

print("\n" + "="*70)
print("SMART PARKING - AI MODEL TRAINING SUITE")
print("="*70)
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# Get the directory of this script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Define all training scripts
training_scripts = [
    {
        'name': 'Occupancy Prediction Model',
        'file': 'train_occupancy_model.py',
        'description': 'Predicts parking lot occupancy rates'
    },
    {
        'name': 'Price Optimization Model',
        'file': 'train_pricing_model.py',
        'description': 'Recommends optimal dynamic pricing'
    },
    {
        'name': 'User Preference Learning Model',
        'file': 'train_preference_model.py',
        'description': 'Learns user booking preferences'
    },
    {
        'name': 'Time-Series Forecasting Model',
        'file': 'train_forecasting_model.py',
        'description': 'Forecasts future availability patterns'
    }
]

results = []

for i, script in enumerate(training_scripts, 1):
    print(f"\n[{i}/{len(training_scripts)}] Training: {script['name']}")
    print(f"Description: {script['description']}")
    print("-" * 70)
    
    script_path = os.path.join(script_dir, script['file'])
    
    try:
        # Run the training script
        result = subprocess.run(
            [sys.executable, script_path],
            cwd=script_dir,
            capture_output=False,
            text=True,
            check=True
        )
        
        results.append({
            'name': script['name'],
            'status': 'SUCCESS',
            'error': None
        })
        
    except subprocess.CalledProcessError as e:
        results.append({
            'name': script['name'],
            'status': 'FAILED',
            'error': str(e)
        })
        print(f"\n❌ ERROR: Training failed for {script['name']}")
        print(f"Error: {e}")
    except Exception as e:
        results.append({
            'name': script['name'],
            'status': 'FAILED',
            'error': str(e)
        })
        print(f"\n❌ ERROR: Unexpected error in {script['name']}")
        print(f"Error: {e}")

# Print summary
print("\n\n" + "="*70)
print("TRAINING SUMMARY")
print("="*70 + "\n")

success_count = sum(1 for r in results if r['status'] == 'SUCCESS')
total_count = len(results)

for result in results:
    status_icon = "✓" if result['status'] == 'SUCCESS' else "✗"
    print(f"{status_icon} {result['name']:<45} {result['status']}")
    if result['error']:
        print(f"  Error: {result['error']}")

print("\n" + "-"*70)
print(f"Successfully trained: {success_count}/{total_count} models")
print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# List generated model files
print("\n" + "="*70)
print("GENERATED MODEL FILES")
print("="*70 + "\n")

model_files = [
    'occupancy_model.pkl',
    'pricing_model.pkl',
    'preference_model.pkl',
    'preference_scaler.pkl',
    'forecasting_model.pkl'
]

for model_file in model_files:
    model_path = os.path.join(script_dir, model_file)
    if os.path.exists(model_path):
        size_mb = os.path.getsize(model_path) / (1024 * 1024)
        print(f"✓ {model_file:<35} {size_mb:.2f} MB")
    else:
        print(f"✗ {model_file:<35} NOT FOUND")

if success_count == total_count:
    print("\n" + "="*70)
    print("🎉 ALL MODELS TRAINED SUCCESSFULLY!")
    print("="*70)
    print("\nYou can now integrate these models into your Flask application.")
    print("Model files are saved in: " + script_dir)
else:
    print("\n" + "="*70)
    print("⚠️  SOME MODELS FAILED TO TRAIN")
    print("="*70)
    print("\nPlease check the errors above and ensure all dependencies are installed.")
    print("Run: pip install -r requirements.txt")

print()
