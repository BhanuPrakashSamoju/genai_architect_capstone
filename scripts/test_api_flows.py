import os
import csv
import requests
import jwt
import datetime

API_BASE = os.getenv('API_BASE', 'http://localhost:8000')
API_PREFIX = os.getenv('API_PREFIX', '/api/v1')
ADMIN_JWT_KEY = os.getenv('ADMIN_JWT_KEY')

print('Testing API flows against', API_BASE + API_PREFIX)

# 1) Read CSV for a user (if present)
csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'customer_data', 'customer_tokens.csv')
user = None
if os.path.exists(csv_path):
    with open(csv_path, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            user = row
            break

if user:
    print('Found user in CSV:', user.get('user_name'))
    # Try user login via API
    login_url = f"{API_BASE}{API_PREFIX}/auth/login"
    resp = requests.post(login_url, json={'username': user.get('user_name'), 'password': user.get('password')}, timeout=60)
    print('Login response:', resp.status_code, resp.text[:200])
    if resp.status_code == 200:
        token = resp.json()['token']
        headers = {'Authorization': f'Bearer {token}'}
        # Call customer loans
        loans_url = f"{API_BASE}{API_PREFIX}/customer/loans"
        r = requests.get(loans_url, headers=headers, timeout=60)
        print('Customer loans status:', r.status_code, 'count:', len(r.json()) if r.status_code==200 else r.text)
        # Call chat
        chat_url = f"{API_BASE}{API_PREFIX}/chat/"
        payload = {'message': 'Show summary of my loans', 'session_id': None}
        r2 = requests.post(chat_url, json=payload, headers=headers, timeout=60)
        print('Chat call status:', r2.status_code, r2.text[:300])
    else:
        print('User login failed; response:', resp.text)
else:
    print('No customer_tokens.csv found or no rows inside. Skipping user flow.')

# Admin flow
if ADMIN_JWT_KEY:
    print('Testing admin flow')
    payload = {'sub': 'admin', 'iat': int(datetime.datetime.utcnow().timestamp()), 'exp': int((datetime.datetime.utcnow() + datetime.timedelta(days=7)).timestamp())}
    admin_token = jwt.encode(payload, ADMIN_JWT_KEY, algorithm='HS256')
    headers = {'Authorization': f'Bearer {admin_token}'}
    r = requests.get(f"{API_BASE}{API_PREFIX}/admin/users", headers=headers, timeout=10)
    print('/admin/users', r.status_code, r.text[:400])
else:
    print('No ADMIN_JWT_KEY in env; skipping admin tests')
