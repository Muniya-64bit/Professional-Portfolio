"""Create test user accounts for KVPL system."""
import psycopg
import os
from dotenv import load_dotenv
import bcrypt
from datetime import datetime

load_dotenv('.env')
conn = psycopg.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

# Test credentials (with strong passwords: 8+ chars, uppercase, lowercase, digit, special char)
test_users = [
    {
        'email': 'admin@kvpl.com',
        'password': 'Admin@123kvpl',
        'full_name': 'Admin User',
        'role': 'admin'
    },
    {
        'email': 'manager@kvpl.com',
        'password': 'Manager@2024kvpl',
        'full_name': 'Estate Manager',
        'role': 'estate_manager'
    },
    {
        'email': 'supervisor@kvpl.com',
        'password': 'Supervisor@2024',
        'full_name': 'Field Supervisor',
        'role': 'field_supervisor'
    },
    {
        'email': 'agronomist@kvpl.com',
        'password': 'Agronomist@2024',
        'full_name': 'Agronomist',
        'role': 'agronomist'
    }
]

print("Creating test user accounts...")
print("-" * 50)

for user in test_users:
    # Hash password
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(user['password'].encode('utf-8'), salt).decode('utf-8')
    
    # Insert user
    cur.execute('''
        INSERT INTO "user" (email, password_hash, full_name, name, role, is_active, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, TRUE, %s, %s)
        ON CONFLICT (email) DO UPDATE SET password_hash = %s, full_name = %s, name = %s
    ''', (user['email'], hashed, user['full_name'], user['full_name'], user['role'], datetime.utcnow(), datetime.utcnow(), hashed, user['full_name'], user['full_name']))
    
    print(f"✅ {user['email']} ({user['full_name']})")

conn.commit()
conn.close()

print("\n" + "=" * 50)
print("🔓 TEST CREDENTIALS")
print("=" * 50)
for user in test_users:
    print(f"\nEmail:    {user['email']}")
    print(f"Password: {user['password']}")
print("\n" + "=" * 50)
