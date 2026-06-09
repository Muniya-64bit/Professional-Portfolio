import os
import logging
from dotenv import load_dotenv

# Load environment variables BEFORE importing auth module
load_dotenv()

from flask import Flask, jsonify, request
from flask_cors import CORS
from auth import (
    signup_user, login_user, get_user_profile, token_required,
    verify_token, validate_password_strength, rate_limit, invalidate_token,
    is_admin, admin_required, get_all_users, create_user_by_admin,
)
from labour import labour_bp
from water import water_bp
from reports import reports_bp
from roi import roi_bp
from fertilizer import fertilizer_bp
from scheduler import maybe_start_scheduler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Roles that admin may assign when creating a system account.
ALLOWED_SYSTEM_ROLES = {'admin', 'estate_manager', 'manager'}

app = Flask(__name__)
CORS(app, 
     origins=["http://localhost:3000", "http://127.0.0.1:3000"],
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
app.register_blueprint(labour_bp)
app.register_blueprint(water_bp)
app.register_blueprint(reports_bp)
app.register_blueprint(fertilizer_bp)
app.register_blueprint(roi_bp)

# Start the monthly labour scheduler at import time so it runs under wsgi/gunicorn
# too (not only `python app.py`). Gating inside ensures exactly one process owns
# it — see scheduler.maybe_start_scheduler / _scheduler_enabled.
maybe_start_scheduler()

# Basic routes
@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "KVPL API", "version": "1.0.0"})

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/api/scheduler/status", methods=["GET"])
@token_required
def scheduler_status():
    """Return the scheduler's running state, next fire time, and last run result."""
    from scheduler import _scheduler, _last_run, SCHEDULER_TIMEZONE
    if _scheduler is None or not _scheduler.running:
        return jsonify({
            'running': False,
            'timezone': SCHEDULER_TIMEZONE,
            'jobs': [],
            'last_run': _last_run,
        }), 200

    jobs = []
    for job in _scheduler.get_jobs():
        next_run = job.next_run_time
        jobs.append({
            'id':           job.id,
            'next_run_utc': next_run.isoformat() if next_run else None,
            'next_run_local': (next_run.astimezone().isoformat() if next_run else None),
            'trigger':      str(job.trigger),
        })

    return jsonify({
        'running':  _scheduler.running,
        'timezone': SCHEDULER_TIMEZONE,
        'jobs':     jobs,
        'last_run': _last_run,
    }), 200

@app.route("/api/estates/public", methods=["GET"])
@token_required
def public_estates():
    """Authenticated estate list (id + name) for the admin user-creation form."""
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
@app.route("/api/auth/users", methods=["GET"])
@token_required
@admin_required
def list_users():
    """Admin only: list all system users."""
    result, status = get_all_users()
    return jsonify(result), status


@app.route("/api/auth/users", methods=["POST"])
@token_required
@admin_required
def create_user():
    """Admin only: create a new system user (admin, estate_manager, manager)."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    email     = data.get('email', '').strip()
    password  = data.get('password', '')
    full_name = data.get('full_name', '').strip()
    role      = data.get('role', 'manager')
    estate_id = data.get('estate_id') or None

    if not email or not password or not full_name:
        return jsonify({'error': 'Email, password, and full name are required'}), 400
    if '@' not in email:
        return jsonify({'error': 'Invalid email format'}), 400

    is_strong, message = validate_password_strength(password)
    if not is_strong:
        return jsonify({'error': message}), 400

    if role not in ALLOWED_SYSTEM_ROLES:
        return jsonify({'error': 'Invalid role'}), 400
    if role == 'manager' and not estate_id:
        return jsonify({'error': 'estate_id is required for the manager role'}), 400

    result, status = create_user_by_admin(email, password, full_name, role=role, estate_id=estate_id)
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
    # The scheduler is started at import time by maybe_start_scheduler() above.
    # Under the debug reloader only the worker (WERKZEUG_RUN_MAIN == 'true')
    # enables it, so the monthly job is never registered twice.
    app.run(host="0.0.0.0", port=5000, debug=True)
