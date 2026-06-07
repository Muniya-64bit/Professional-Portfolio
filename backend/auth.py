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

def generate_token(user_id, email, role=None, estate_id=None, expires_in_days=7):
    """Generate JWT token with expiration.

    role + estate_id are embedded so authorization decisions can be made without
    a per-request DB lookup. estate_id scopes read-only 'manager' users.
    """
    payload = {
        'user_id': str(user_id),
        'email': email,
        'role': role,
        'estate_id': str(estate_id) if estate_id else None,
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


# ── Role-based authorization ──────────────────────────────────────────────────
# Two tiers: FULL_ACCESS_ROLES can read + write across all estates; everyone else
# ('manager') is read-only and scoped to their own estate_id.
FULL_ACCESS_ROLES = {'admin', 'estate_manager'}


def is_full_access():
    """True if the current request's user may write and see all estates."""
    return (getattr(request, 'user', {}) or {}).get('role') in FULL_ACCESS_ROLES


def write_required(f):
    """Block read-only roles (e.g. 'manager') from any mutating endpoint.

    Must be applied *after* token_required (i.e. listed below it) so that
    request.user has already been populated from the JWT.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not is_full_access():
            return jsonify({'error': 'Insufficient permissions'}), 403
        return f(*args, **kwargs)
    return decorated


def effective_estate_id(requested):
    """Resolve which estate the current user may act on.

    Returns (estate_id, error_response_or_None):
      - full-access roles: the requested value is passed through unchanged
        (None means "all estates").
      - manager: forced to their own estate; a request for a different estate
        returns a 403 error response.
    """
    if is_full_access():
        return requested, None
    own = (getattr(request, 'user', {}) or {}).get('estate_id')
    if requested and str(requested) != str(own):
        return None, (jsonify({'error': 'Forbidden: outside your estate'}), 403)
    return own, None


def signup_user(email, password, full_name, role='manager', estate_id=None):
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
                INSERT INTO "user" (email, password_hash, full_name, name, role, estate_id, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, email, full_name, role, estate_id
            ''', (email, hashed_password, full_name, full_name, role, estate_id,
                  datetime.utcnow(), datetime.utcnow()))

            user = cur.fetchone()
            conn.commit()

            if user:
                user_id, user_email, user_name, user_role, user_estate_id = user
                token = generate_token(user_id, user_email, user_role, user_estate_id)
                logger.info(f"User created successfully: {user_email}")
                return {
                    'message': 'User created successfully',
                    'user': {
                        'id': str(user_id),
                        'email': user_email,
                        'full_name': user_name,
                        'role': user_role,
                        'estate_id': str(user_estate_id) if user_estate_id else None
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
                SELECT id, email, password_hash, full_name, role, estate_id
                FROM "user"
                WHERE email = %s
            ''', (email,))
            user = cur.fetchone()

        if not user:
            logger.warning(f"Login failed - user not found: {email}")
            return {'error': 'Invalid email or password'}, 401

        user_id, user_email, password_hash, full_name, role, estate_id = user

        if not verify_password(password, password_hash):
            logger.warning(f"Login failed - invalid password for: {email}")
            return {'error': 'Invalid email or password'}, 401

        token = generate_token(user_id, user_email, role, estate_id)
        logger.info(f"User logged in successfully: {email}")

        return {
            'message': 'Login successful',
            'user': {
                'id': str(user_id),
                'email': user_email,
                'full_name': full_name,
                'role': role,
                'estate_id': str(estate_id) if estate_id else None
            },
            'token': token,
            'expires_in': 604800
        }, 200
    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        return {'error': 'Authentication failed'}, 500
    finally:
        conn.close()

def get_user_profile(user_id):
    """Get user profile by ID."""
    conn = get_db_connection()
    if not conn:
        return {'error': 'Database connection failed'}, 500
    
    try:
        with conn.cursor() as cur:
            cur.execute('''
                SELECT id, email, full_name, role, estate_id, created_at
                FROM "user"
                WHERE id = %s::uuid
            ''', (user_id,))

            user = cur.fetchone()
            conn.close()

            if not user:
                return {'error': 'User not found'}, 404

            user_id, email, full_name, role, estate_id, created_at = user
            return {
                'user': {
                    'id': str(user_id),
                    'email': email,
                    'full_name': full_name,
                    'role': role,
                    'estate_id': str(estate_id) if estate_id else None,
                    'created_at': created_at.isoformat() if created_at else None
                }
            }, 200
    except Exception as e:
        logger.error(f"Get profile error: {e}", exc_info=True)
        return {'error': 'Failed to retrieve user profile'}, 500
