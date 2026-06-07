"""Authentication utilities for KVPL system."""
import os
import jwt
import bcrypt
import psycopg
import logging
import re
from datetime import datetime, timedelta
from functools import wraps
from collections import defaultdict
from flask import request, jsonify, current_app

# Configure logging
logger = logging.getLogger(__name__)

# Validate SECRET_KEY is set
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable is required for JWT token generation")

# Token blacklist for logout (in production, use Redis)
_token_blacklist = set()

# Rate limiting storage (IP -> {endpoint: [(timestamp, attempts), ...]})
_rate_limit_store = defaultdict(lambda: defaultdict(list))

def get_db_connection():
    """Get database connection from environment."""
    try:
        conn = psycopg.connect(os.getenv('DATABASE_URL'))
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {e}", exc_info=True)
        return None

def hash_password(password):
    """Hash password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password, hashed):
    """Verify password against hash."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def validate_password_strength(password):
    """
    Validate password meets security requirements.
    Requirements:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    
    Returns: (is_valid, message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r'\d', password):
        return False, "Password must contain at least one digit"
    
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'",.<>?]', password):
        return False, "Password must contain at least one special character (!@#$%^&*...)"
    
    return True, "Password is strong"

def rate_limit(endpoint, max_attempts=5, window_seconds=900):
    """
    Rate limiting decorator (5 attempts per 15 minutes per IP).
    Prevents brute force attacks on auth endpoints.
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            client_ip = request.remote_addr
            now = datetime.utcnow()
            window_start = now - timedelta(seconds=window_seconds)
            
            # Clean old attempts
            _rate_limit_store[client_ip][endpoint] = [
                (ts, count) for ts, count in _rate_limit_store[client_ip][endpoint]
                if ts > window_start
            ]
            
            # Count recent attempts
            recent_attempts = sum(count for _, count in _rate_limit_store[client_ip][endpoint])
            
            if recent_attempts >= max_attempts:
                logger.warning(f"Rate limit exceeded for IP {client_ip} on {endpoint}")
                return jsonify({'error': 'Too many attempts. Try again later.'}), 429
            
            # Record attempt
            _rate_limit_store[client_ip][endpoint].append((now, 1))
            
            return f(*args, **kwargs)
        return decorated
    return decorator

def generate_token(user_id, email, expires_in_days=7):
    """Generate JWT token with expiration."""
    payload = {
        'user_id': str(user_id),
        'email': email,
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(days=expires_in_days)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

def verify_token(token):
    """Verify JWT token and check blacklist."""
    try:
        # Check if token is blacklisted
        if token in _token_blacklist:
            return None
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def invalidate_token(token):
    """Add token to blacklist (logout)."""
    _token_blacklist.add(token)

def token_required(f):
    """Decorator to require valid token."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Get token from Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({'error': 'Invalid token format'}), 401
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        request.user = payload
        request.token = token
        return f(*args, **kwargs)
    
    return decorated

def signup_user(email, password, full_name, role='estate_manager'):
    """Create new user account."""
    conn = get_db_connection()
    if not conn:
        return {'error': 'Database connection failed'}, 500
    
    try:
        with conn.cursor() as cur:
            # Check if user exists
            cur.execute('SELECT id FROM "user" WHERE email = %s', (email,))
            if cur.fetchone():
                logger.info(f"Signup attempted with existing email: {email}")
                return {'error': 'Email already registered'}, 400
            
            # Hash password
            hashed_password = hash_password(password)
            
            # Insert user
            cur.execute('''
                INSERT INTO "user" (email, password_hash, full_name, name, role, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id, email, full_name, role
            ''', (email, hashed_password, full_name, full_name, role, datetime.utcnow(), datetime.utcnow()))
            
            user = cur.fetchone()
            conn.commit()
            
            if user:
                user_id, user_email, user_name, user_role = user
                token = generate_token(user_id, user_email)
                logger.info(f"User created successfully: {user_email}")
                return {
                    'message': 'User created successfully',
                    'user': {
                        'id': str(user_id),
                        'email': user_email,
                        'full_name': user_name,
                        'role': user_role
                    },
                    'token': token
                }, 201
    except Exception as e:
        conn.rollback()
        logger.error(f"Signup error: {e}", exc_info=True)
        return {'error': 'Failed to create user account'}, 500
    finally:
        conn.close()
    
    return {'error': 'Failed to create user'}, 500

def login_user(email, password):
    """Authenticate user with email and password."""
    conn = get_db_connection()
    if not conn:
        return {'error': 'Database connection failed'}, 500
    
    try:
        with conn.cursor() as cur:
            cur.execute('''
                SELECT id, email, password_hash, full_name, role
                FROM "user"
                WHERE email = %s
            ''', (email,))
            
            user = cur.fetchone()
            conn.close()
            
            if not user:
                logger.warning(f"Login failed - user not found: {email}")
                return {'error': 'Invalid email or password'}, 401
            
            user_id, user_email, password_hash, full_name, role = user
            
            # Verify password
            if not verify_password(password, password_hash):
                logger.warning(f"Login failed - invalid password for: {email}")
                return {'error': 'Invalid email or password'}, 401
            
            # Generate token
            token = generate_token(user_id, user_email)
            logger.info(f"User logged in successfully: {email}")
            
            return {
                'message': 'Login successful',
                'user': {
                    'id': str(user_id),
                    'email': user_email,
                    'full_name': full_name,
                    'role': role
                },
                'token': token,
                'expires_in': 604800  # 7 days in seconds
            }, 200
    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        return {'error': 'Authentication failed'}, 500

def get_user_profile(user_id):
    """Get user profile by ID."""
    conn = get_db_connection()
    if not conn:
        return {'error': 'Database connection failed'}, 500
    
    try:
        with conn.cursor() as cur:
            cur.execute('''
                SELECT id, email, full_name, role, created_at
                FROM "user"
                WHERE id = %s::uuid
            ''', (user_id,))
            
            user = cur.fetchone()
            conn.close()
            
            if not user:
                return {'error': 'User not found'}, 404
            
            user_id, email, full_name, role, created_at = user
            return {
                'user': {
                    'id': str(user_id),
                    'email': email,
                    'full_name': full_name,
                    'role': role,
                    'created_at': created_at.isoformat() if created_at else None
                }
            }, 200
    except Exception as e:
        logger.error(f"Get profile error: {e}", exc_info=True)
        return {'error': 'Failed to retrieve user profile'}, 500
