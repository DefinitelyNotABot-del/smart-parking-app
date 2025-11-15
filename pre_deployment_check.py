"""
Pre-Deployment Verification Script
Run this before deploying to cloud to catch issues early!
"""
import os
import sys
import importlib.util

print("\n" + "="*70)
print("🔍 SMART PARKING APP - CLOUD DEPLOYMENT READINESS CHECK")
print("="*70 + "\n")

issues_found = 0

# Check 1: Critical files exist
print("1️⃣ Checking critical files...")
required_files = [
    'run.py',
    'requirements.txt',
    'Dockerfile',
    'startup.sh',
    'complete_setup.py',
    'app/__init__.py',
    'app/routes/api.py',
    'templates/customer.html',
    'templates/owner.html'
]

for file in required_files:
    if os.path.exists(file):
        print(f"   ✅ {file}")
    else:
        print(f"   ❌ MISSING: {file}")
        issues_found += 1

# Check 2: Dependencies can be imported
print("\n2️⃣ Checking Python dependencies...")
critical_imports = [
    'flask',
    'flask_socketio',
    'eventlet',
    'gunicorn',
    'werkzeug',
    'sqlite3',
    'pandas',
    'numpy',
    'joblib'
]

for module_name in critical_imports:
    try:
        __import__(module_name)
        print(f"   ✅ {module_name}")
    except ImportError:
        print(f"   ❌ MISSING: {module_name}")
        issues_found += 1

# Check 3: App can be created
print("\n3️⃣ Checking Flask app creation...")
try:
    from app import create_app
    app = create_app()
    print("   ✅ Flask app created successfully")
    print(f"   ℹ️  Instance path: {app.instance_path}")
    print(f"   ℹ️  Database: {app.config.get('DATABASE')}")
    print(f"   ℹ️  Demo DB: {app.config.get('DEMO_DATABASE')}")
except Exception as e:
    print(f"   ❌ FAILED: {e}")
    issues_found += 1

# Check 4: Database paths are correct
print("\n4️⃣ Checking database configuration...")
try:
    from app import create_app
    app = create_app()
    
    db_path = app.config.get('DATABASE')
    demo_db_path = app.config.get('DEMO_DATABASE')
    
    if 'instance' in db_path:
        print(f"   ✅ Regular DB path correct: {db_path}")
    else:
        print(f"   ❌ Regular DB path wrong: {db_path}")
        issues_found += 1
    
    if 'instance' in demo_db_path:
        print(f"   ✅ Demo DB path correct: {demo_db_path}")
    else:
        print(f"   ❌ Demo DB path wrong: {demo_db_path}")
        issues_found += 1
        
except Exception as e:
    print(f"   ❌ FAILED: {e}")
    issues_found += 1

# Check 5: SocketIO configuration
print("\n5️⃣ Checking SocketIO configuration...")
try:
    from app import socketio
    print("   ✅ SocketIO imported successfully")
except Exception as e:
    print(f"   ❌ FAILED: {e}")
    issues_found += 1

# Check 6: Blueprints registered
print("\n6️⃣ Checking Flask blueprints...")
try:
    from app import create_app
    app = create_app()
    blueprints = list(app.blueprints.keys())
    
    required_blueprints = ['auth', 'owner', 'customer', 'api']
    for bp in required_blueprints:
        if bp in blueprints:
            print(f"   ✅ {bp} blueprint registered")
        else:
            print(f"   ❌ MISSING: {bp} blueprint")
            issues_found += 1
            
except Exception as e:
    print(f"   ❌ FAILED: {e}")
    issues_found += 1

# Check 7: Critical routes exist
print("\n7️⃣ Checking critical API routes...")
try:
    from app import create_app
    app = create_app()
    
    with app.test_client() as client:
        # Test basic routes exist
        routes_to_check = [
            ('/', 200, 'Role page'),
            ('/api/health', 200, 'Health check'),
        ]
        
        for route, expected_status, description in routes_to_check:
            try:
                response = client.get(route)
                if response.status_code in [200, 302, 401]:  # 401 is OK for protected routes
                    print(f"   ✅ {description}: {route}")
                else:
                    print(f"   ⚠️  {description}: {route} (status: {response.status_code})")
            except Exception as e:
                print(f"   ❌ {description}: {route} - {e}")
                issues_found += 1
                
except Exception as e:
    print(f"   ❌ FAILED: {e}")
    issues_found += 1

# Check 8: Dockerfile configuration
print("\n8️⃣ Checking Dockerfile...")
try:
    with open('Dockerfile', 'r') as f:
        dockerfile_content = f.read()
        
    checks = [
        ('eventlet' in dockerfile_content, 'Uses eventlet workers'),
        ('run:app' in dockerfile_content, 'Correct entry point (run:app)'),
        ('$PORT' in dockerfile_content, 'Dynamic port configuration'),
        ('auto-initialize' in dockerfile_content or 'automatically' in dockerfile_content, 'Database auto-initialization'),
    ]
    
    for check, description in checks:
        if check:
            print(f"   ✅ {description}")
        else:
            print(f"   ❌ MISSING: {description}")
            issues_found += 1
            
except Exception as e:
    print(f"   ❌ FAILED: {e}")
    issues_found += 1

# Check 9: Instance directory can be created
print("\n9️⃣ Checking instance directory...")
try:
    os.makedirs('instance', exist_ok=True)
    print("   ✅ Instance directory exists/created")
except Exception as e:
    print(f"   ❌ FAILED: {e}")
    issues_found += 1

# Final Report
print("\n" + "="*70)
if issues_found == 0:
    print("🎉 ALL CHECKS PASSED! Your app is ready for cloud deployment!")
    print("="*70)
    print("\n📝 Next steps:")
    print("   1. Test locally: python run.py")
    print("   2. Test with gunicorn: gunicorn --bind 0.0.0.0:8000 --worker-class eventlet --workers 1 run:app")
    print("   3. Deploy to cloud (push to GitHub or use Azure CLI)")
    print("   4. Monitor logs during first deployment")
    print("\n✅ Deployment confidence: HIGH\n")
    sys.exit(0)
else:
    print(f"❌ FOUND {issues_found} ISSUE(S) - Fix these before deploying!")
    print("="*70)
    print("\n🔧 Review the errors above and fix them.")
    print("   Then run this script again.\n")
    sys.exit(1)
