import os
import sqlite3
import secrets
import csv
import hashlib
from datetime import datetime, timedelta

import bcrypt
import jwt

# Paths
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOAN_DB = os.path.join(ROOT, "dataset", "LoanDB_BlueLoans4all.sqlite")
OUT_DIR = os.path.join(ROOT, "database", "customer_data")
USER_DB = os.path.join(OUT_DIR, "loan_user_db.sqlite")
TOKEN_CSV = os.path.join(OUT_DIR, "customer_tokens.csv")
JWT_SECRET_FILE = os.path.join(OUT_DIR, ".jwt_secret")

# DB table
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS customer_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id TEXT NOT NULL UNIQUE,
    user_name TEXT NOT NULL,
    password_hash BLOB NOT NULL,
    email TEXT,
    jwt_token_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def load_unique_customer_ids(loan_db_path):
    conn = sqlite3.connect(loan_db_path)
    cur = conn.cursor()
    # Attempt common table names that might hold customers
    candidates = []
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    for row in cur.fetchall():
        candidates.append(row[0])

    # Search for columns named customer_id in tables
    customer_ids = set()
    for t in candidates:
        try:
            cur.execute(f"PRAGMA table_info({t});")
            cols = [c[1] for c in cur.fetchall()]
            if 'customer_id' in cols:
                cur.execute(f"SELECT DISTINCT customer_id FROM {t} WHERE customer_id IS NOT NULL;")
                for r in cur.fetchall():
                    customer_ids.add(str(r[0]))
        except Exception:
            continue

    conn.close()
    return sorted(customer_ids)


def random_username(customer_id):
    # Use a short random suffix to ensure uniqueness and a readable prefix
    suffix = secrets.token_hex(3)
    return f"user_{customer_id}_{suffix}"[:64]


def random_password(length=16):
    return secrets.token_urlsafe(length)[:length]


def ensure_jwt_secret(path):
    if os.path.exists(path):
        with open(path, 'rb') as f:
            return f.read().strip()
    secret = secrets.token_urlsafe(64)
    # write with restrictive permissions
    with open(path, 'w') as f:
        f.write(secret)
    os.chmod(path, 0o600)
    return secret


def create_jwt_for_user(customer_id, secret):
    now = datetime.utcnow()
    payload = {
        'sub': customer_id,
        'iat': int(now.timestamp()),
        'exp': int((now + timedelta(days=30)).timestamp()),
    }
    token = jwt.encode(payload, secret, algorithm='HS256')
    return token


def hash_token(token):
    # store SHA-256 hex of token (fast) - alternative is to bcrypt the token
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    customer_ids = load_unique_customer_ids(LOAN_DB)
    if not customer_ids:
        print("No customer_id values found in loan DB. Exiting.")
        return

    jwt_secret = ensure_jwt_secret(JWT_SECRET_FILE)

    # Create user DB
    conn = sqlite3.connect(USER_DB)
    cur = conn.cursor()
    cur.execute(CREATE_TABLE_SQL)
    conn.commit()

    # Prepare CSV to store raw tokens for administrator distribution. Keep secure.
    csv_file = open(TOKEN_CSV, 'w', newline='')
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow(['customer_id', 'user_name', 'password', 'email', 'jwt_token'])

    for cid in customer_ids:
        user_name = random_username(cid)
        password = random_password(16)
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        email = f"{user_name}@example.com"

        token = create_jwt_for_user(cid, jwt_secret)
        token_hash = hash_token(token)

        created_at = datetime.utcnow().isoformat() + 'Z'

        cur.execute(
            "INSERT OR IGNORE INTO customer_data (customer_id, user_name, password_hash, email, jwt_token_hash, created_at) VALUES (?,?,?,?,?,?)",
            (cid, user_name, password_hash, email, token_hash, created_at)
        )

        csv_writer.writerow([cid, user_name, password, email, token])

    conn.commit()
    conn.close()
    csv_file.close()

    # Restrict permissions on generated files
    os.chmod(USER_DB, 0o600)
    os.chmod(TOKEN_CSV, 0o600)

    print(f"Created user DB at: {USER_DB}")
    print(f"Raw tokens CSV at: {TOKEN_CSV} (keep it secure!)")
    print(f"JWT secret at: {JWT_SECRET_FILE} (permissions 600)")


if __name__ == '__main__':
    main()
