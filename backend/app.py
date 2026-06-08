import os
import logging
from dotenv import load_dotenv

# Load environment variables BEFORE importing auth module
load_dotenv()

from flask import Flask, jsonify, request
from flask_cors import CORS
from auth import (
    signup_user, login_user, get_user_profile, token_required,
    verify_token, validate_password_strength, rate_limit, invalidate_token
)
from labour import labour_bp
from water import water_bp
from reports import reports_bp
from fertilizer import fertilizer_bp
from scheduler import start_scheduler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Roles a user may self-select at signup (testing convenience).
ALLOWED_SIGNUP_ROLES = {'admin', 'estate_manager', 'manager'}

app = Flask(__name__)
CORS(app)
app.register_blueprint(labour_bp)
app.register_blueprint(water_bp)
app.register_blueprint(reports_bp)
app.register_blueprint(fertilizer_bp)

# Start the monthly labour-plan scheduler under a WSGI server (gunicorn imports
# this module as 'app'). For the `python app.py` dev runner it is started in the
# __main__ block below instead, so the debug reloader doesn't double-start it.
if __name__ != "__main__":
    start_scheduler()

# Basic routes
@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "KVPL API", "version": "1.0.0"})

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/api/estates/public", methods=["GET"])
def public_estates():
    """Unauthenticated estate list (id + name) for the signup estate selector."""
    from auth import get_db_connection
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name FROM estate ORDER BY name")
            return jsonify([{'id': str(r[0]), 'name': r[1]} for r in cur.fetchall()]), 200
    except Exception as e:
        logger.error("public_estates error: %s", e, exc_info=True)
        return jsonify({'error': 'Failed to load estates'}), 500
    finally:
        conn.close()

# Auth routes
@app.route("/api/auth/signup", methods=["POST"])
@rate_limit('/api/auth/signup', max_attempts=5, window_seconds=900)
def signup():
    """Register new user."""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    email = data.get('email', '').strip()
    password = data.get('password', '')
    full_name = data.get('full_name', '').strip()
    
    # Validation
    if not email or not password or not full_name:
        return jsonify({'error': 'Email, password, and full name are required'}), 400
    
    if '@' not in email:
        return jsonify({'error': 'Invalid email format'}), 400
    
    # Validate password strength
    is_strong, message = validate_password_strength(password)
    if not is_strong:
        return jsonify({'error': message}), 400

    # Role selection (testing convenience — lock this down later).
    role = data.get('role', 'manager')
    if role not in ALLOWED_SIGNUP_ROLES:
        return jsonify({'error': 'Invalid role'}), 400

    # A manager is scoped to one estate, so they must be assigned one.
    estate_id = data.get('estate_id')
    if role == 'manager' and not estate_id:
        return jsonify({'error': 'estate_id is required for the manager role'}), 400

    result, status = signup_user(email, password, full_name, role=role, estate_id=estate_id)
    return jsonify(result), status

@app.route("/api/auth/login", methods=["POST"])
@rate_limit('/api/auth/login', max_attempts=5, window_seconds=900)
def login():
    """Login user."""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    email = data.get('email', '').strip()
    password = data.get('password', '')
    
    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400
    
    result, status = login_user(email, password)
    return jsonify(result), status

@app.route("/api/auth/verify", methods=["POST"])
@token_required
def verify():
    """Verify token validity and return full user profile."""
    user_id = request.user.get('user_id')
    result, status = get_user_profile(user_id)
    if status != 200:
        return jsonify({'error': 'User not found'}), 401
    return jsonify({
        'message': 'Token is valid',
        'user': result['user']
    }), 200

@app.route("/api/auth/profile", methods=["GET"])
@token_required
def profile():
    """Get current user profile."""
    user_id = request.user.get('user_id')
    result, status = get_user_profile(user_id)
    return jsonify(result), status

@app.route("/api/auth/refresh", methods=["POST"])
@token_required
def refresh():
    """Refresh token."""
    from auth import generate_token
    user_id = request.user.get('user_id')
    email = request.user.get('email')
    role = request.user.get('role')
    estate_id = request.user.get('estate_id')

    new_token = generate_token(user_id, email, role, estate_id)
    return jsonify({
        'message': 'Token refreshed successfully',
        'token': new_token
    }), 200

@app.route("/api/auth/logout", methods=["POST"])
@token_required
def logout():
    """Logout user and blacklist the token."""
    invalidate_token(request.token)
    return jsonify({
        'message': 'Logged out successfully'
    }), 200

if __name__ == "__main__":
    # Under the debug reloader the parent process has WERKZEUG_RUN_MAIN unset and
    # only watches files; the worker sets it to 'true'. Start the scheduler only
    # in the worker so the monthly job isn't registered twice.
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        start_scheduler()
    app.run(host="0.0.0.0", port=5000, debug=True)
