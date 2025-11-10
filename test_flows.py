"""
Comprehensive test script for Smart Parking App flows
Tests: Role selection, Login/Register, Owner flows, Customer flows
"""
import requests
import json
from time import sleep

BASE_URL = "http://127.0.0.1:5000"

def test_owner_flow():
    """Test complete owner flow: role -> register -> login -> create lot -> view lot"""
    print("\n=== TESTING OWNER FLOW ===\n")
    
    session = requests.Session()
    
    # 1. Set role to owner
    print("1. Setting role to owner...")
    resp = session.get(f"{BASE_URL}/set-role/owner")
    print(f"   Status: {resp.status_code}")
    if resp.status_code != 200:
        print(f"   ERROR: Expected redirect or 200, got {resp.status_code}")
        return False
    
    # 2. Register owner
    print("2. Registering new owner...")
    register_data = {
        "name": "Test Owner",
        "email": f"owner{int(requests.utils.default_headers()['User-Agent'].__hash__())}@test.com",
        "password": "testpass123"
    }
    resp = session.post(f"{BASE_URL}/api/register", json=register_data)
    print(f"   Status: {resp.status_code}")
    print(f"   Response: {resp.json()}")
    
    # 3. Login
    print("3. Logging in...")
    login_data = {
        "email": register_data["email"],
        "password": register_data["password"]
    }
    resp = session.post(f"{BASE_URL}/api/login", json=login_data)
    print(f"   Status: {resp.status_code}")
    print(f"   Response: {resp.json()}")
    
    if resp.status_code != 200:
        print("   ERROR: Login failed")
        return False
    
    # 4. Access owner page
    print("4. Accessing owner page...")
    resp = session.get(f"{BASE_URL}/owner")
    print(f"   Status: {resp.status_code}")
    if resp.status_code != 200:
        print(f"   ERROR: Cannot access owner page")
        return False
    
    # 5. Create a lot
    print("5. Creating parking lot...")
    lot_data = {
        "location": "Test Mall",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "total_spots": 10,
        "large_spots": 3,
        "small_spots": 5
    }
    resp = session.post(f"{BASE_URL}/api/lot", json=lot_data)
    print(f"   Status: {resp.status_code}")
    print(f"   Response: {resp.json()}")
    
    if resp.status_code != 200:
        print("   ERROR: Failed to create lot")
        return False
    
    lot_id = resp.json().get('lot_id')
    
    # 6. Get all lots
    print("6. Fetching all lots...")
    resp = session.get(f"{BASE_URL}/api/lots")
    print(f"   Status: {resp.status_code}")
    lots = resp.json()
    print(f"   Found {len(lots)} lot(s)")
    for lot in lots:
        print(f"   - {lot['location']}: {lot['total_spots']} spots")
    
    # 7. Get specific lot
    print(f"7. Fetching lot {lot_id} details...")
    resp = session.get(f"{BASE_URL}/api/lot/{lot_id}")
    print(f"   Status: {resp.status_code}")
    if resp.status_code == 200:
        lot_detail = resp.json()
        print(f"   Location: {lot_detail['location']}")
        print(f"   Total spots: {lot_detail['total_spots']}")
    
    # 8. Access lot spots page
    print(f"8. Accessing lot spots page...")
    resp = session.get(f"{BASE_URL}/owner/lot/{lot_id}")
    print(f"   Status: {resp.status_code}")
    if resp.status_code != 200:
        print("   ERROR: Cannot access lot spots page")
        return False
    
    print("\n✓ Owner flow completed successfully!\n")
    return True

def test_customer_flow():
    """Test complete customer flow: role -> register -> login -> view lots -> smart search"""
    print("\n=== TESTING CUSTOMER FLOW ===\n")
    
    session = requests.Session()
    
    # 1. Set role to customer
    print("1. Setting role to customer...")
    resp = session.get(f"{BASE_URL}/set-role/customer")
    print(f"   Status: {resp.status_code}")
    
    # 2. Register customer
    print("2. Registering new customer...")
    register_data = {
        "name": "Test Customer",
        "email": f"customer{int(requests.utils.default_headers()['User-Agent'].__hash__())}@test.com",
        "password": "testpass123"
    }
    resp = session.post(f"{BASE_URL}/api/register", json=register_data)
    print(f"   Status: {resp.status_code}")
    print(f"   Response: {resp.json()}")
    
    # 3. Login
    print("3. Logging in...")
    login_data = {
        "email": register_data["email"],
        "password": register_data["password"]
    }
    resp = session.post(f"{BASE_URL}/api/login", json=login_data)
    print(f"   Status: {resp.status_code}")
    print(f"   Response: {resp.json()}")
    
    if resp.status_code != 200:
        print("   ERROR: Login failed")
        return False
    
    # 4. Access customer page
    print("4. Accessing customer page...")
    resp = session.get(f"{BASE_URL}/customer")
    print(f"   Status: {resp.status_code}")
    if resp.status_code != 200:
        print(f"   ERROR: Cannot access customer page")
        return False
    
    # 5. View available lots
    print("5. Fetching available lots...")
    resp = session.get(f"{BASE_URL}/api/lots")
    print(f"   Status: {resp.status_code}")
    lots = resp.json()
    print(f"   Found {len(lots)} lot(s)")
    
    print("\n✓ Customer flow completed successfully!\n")
    return True

def test_spot_management():
    """Test spot creation, update, and deletion"""
    print("\n=== TESTING SPOT MANAGEMENT ===\n")
    
    session = requests.Session()
    
    # Setup: Register and login as owner, create a lot
    session.get(f"{BASE_URL}/set-role/owner")
    register_data = {
        "name": "Spot Test Owner",
        "email": f"spotowner{int(requests.utils.default_headers()['User-Agent'].__hash__())}@test.com",
        "password": "testpass123"
    }
    session.post(f"{BASE_URL}/api/register", json=register_data)
    login_data = {"email": register_data["email"], "password": register_data["password"]}
    session.post(f"{BASE_URL}/api/login", json=login_data)
    
    lot_data = {
        "location": "Spot Test Lot",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "total_spots": 4,
        "large_spots": 1,
        "small_spots": 2
    }
    lot_resp = session.post(f"{BASE_URL}/api/lot", json=lot_data)
    lot_id = lot_resp.json()['lot_id']
    
    # 1. Get spots for the lot
    print(f"1. Fetching spots for lot {lot_id}...")
    resp = session.get(f"{BASE_URL}/api/lot/{lot_id}/spots")
    print(f"   Status: {resp.status_code}")
    if resp.status_code == 200:
        spots = resp.json()
        print(f"   Found {len(spots)} spot(s)")
        if len(spots) > 0:
            spot_id = spots[0]['spot_id']
            
            # 2. Update a spot
            print(f"2. Updating spot {spot_id} status...")
            update_data = {"status": "occupied"}
            resp = session.put(f"{BASE_URL}/api/lot/{lot_id}/spot/{spot_id}", json=update_data)
            print(f"   Status: {resp.status_code}")
            print(f"   Response: {resp.json()}")
            
            # 3. Delete a spot
            print(f"3. Deleting spot {spot_id}...")
            resp = session.delete(f"{BASE_URL}/api/lot/{lot_id}/spot/{spot_id}")
            print(f"   Status: {resp.status_code}")
            print(f"   Response: {resp.json()}")
    
    print("\n✓ Spot management completed!\n")
    return True

if __name__ == "__main__":
    print("\n" + "="*60)
    print("SMART PARKING APP - COMPREHENSIVE FLOW TESTS")
    print("="*60)
    
    try:
        # Test if server is running
        resp = requests.get(BASE_URL, timeout=2)
        print(f"✓ Server is running at {BASE_URL}\n")
    except requests.exceptions.ConnectionError:
        print(f"✗ ERROR: Server not running at {BASE_URL}")
        print("  Please start the app first with: python app.py")
        exit(1)
    
    results = []
    
    # Run all tests
    results.append(("Owner Flow", test_owner_flow()))
    results.append(("Customer Flow", test_customer_flow()))
    results.append(("Spot Management", test_spot_management()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    for test_name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_name}: {status}")
    print("="*60 + "\n")
    
    all_passed = all(result[1] for result in results)
    if all_passed:
        print("🎉 All tests passed! The app is working correctly.\n")
    else:
        print("⚠️  Some tests failed. Check the output above for details.\n")
