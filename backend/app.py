import os
import logging
from dotenv import load_dotenv

# Load environment variables BEFORE importing auth module
load_dotenv()

from flask import Flask, jsonify, request
from flask_cors import CORS
from auth import (
    signup_user, login_user, get_user_profile, token_required,
    verify_token, validate_password_strength, rate_limit
)
from labour import labour_bp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)
app.register_blueprint(labour_bp)

# Basic routes
@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "KVPL API", "version": "1.0.0"})

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

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
    
    result, status = signup_user(email, password, full_name, role='manager')
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
    """Verify token validity."""
    return jsonify({
        'message': 'Token is valid',
        'user': request.user
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
    
    new_token = generate_token(user_id, email)
    return jsonify({
        'message': 'Token refreshed successfully',
        'token': new_token
    }), 200

@app.route("/api/auth/logout", methods=["POST"])
@token_required
def logout():
    """Logout user (token invalidation handled on client side)."""
    return jsonify({
        'message': 'Logged out successfully'
    }), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
