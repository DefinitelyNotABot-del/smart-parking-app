import requests

BASE = 'http://127.0.0.1:5000'

def test_login(email, password, role=None):
    payload = {'email': email, 'password': password}
    if role:
        payload['role'] = role
    r = requests.post(BASE + '/api/login', json=payload)
    print('POST /api/login', email, '->', r.status_code)
    try:
        print(r.json())
    except Exception:
        print(r.text)

if __name__ == '__main__':
    test_login('demo.owner@smartparking.com', 'demo123')
    test_login('demo.customer@smartparking.com', 'demo123')
    # Wrong password
    test_login('demo.owner@smartparking.com', 'wrongpass')
    # Bad email
    test_login('demo.owner@smartparking.com200349', 'demo123')
