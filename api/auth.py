"""Real authentication system with JWT and bcrypt (no SheetsDB)."""
import bcrypt
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from datetime import timedelta
import os

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# In-memory user store (populated from defaults or env)
_users = {}

def _init_default_users():
    default_users = [
        {"username": "secretaire", "password": "sec123", "role": "secretaire"},
        {"username": "admin01", "password": "admin123", "role": "admin"},
        {"username": "dr.martin", "password": "martin2024", "role": "medical"},
        {"username": "dr.sophie", "password": "sophie2024", "role": "medical"},
        {"username": "dr.pierre", "password": "pierre2024", "role": "medical"},
        {"username": "dr.isabelle", "password": "isabelle2024", "role": "medical"},
        {"username": "dr.jeanluc", "password": "jeanluc2024", "role": "medical"},
        {"username": "dr.catherine", "password": "catherine2024", "role": "medical"},
        {"username": "dr.philippe", "password": "philippe2024", "role": "medical"},
        {"username": "dr.marie", "password": "marie2024", "role": "medical"},
        {"username": "dr.ayoub", "password": "ayoub2024", "role": "medical"},
        {"username": "dr.hassin", "password": "hassin2024", "role": "medical"},
    ]
    import json
    env_users = os.getenv('USERS_JSON')
    if env_users:
        try:
            default_users = json.loads(env_users)
        except Exception:
            pass
    for u in default_users:
        hashed = bcrypt.hashpw(u['password'].encode(), bcrypt.gensalt()).decode()
        _users[u['username'].lower()] = {
            'username': u['username'],
            'password_hash': hashed,
            'role': u['role'],
            'user_id': u.get('user_id', u['username']),
        }

_init_default_users()

def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())

@auth_bp.route('/login', methods=['POST'])
def login():
    import time
    start_time = time.time()
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        if not username or not password:
            return jsonify({"success": False, "error": "Nom d'utilisateur et mot de passe requis"}), 400
        user = _users.get(username.lower())
        if not user:
            return jsonify({"success": False, "error": "Identifiants invalides"}), 401
        if not verify_password(password, user['password_hash']):
            return jsonify({"success": False, "error": "Identifiants invalides"}), 401
        access_token = create_access_token(
            identity=username,
            expires_delta=timedelta(hours=24)
        )
        elapsed = (time.time() - start_time) * 1000
        print(f"[Auth] Login {elapsed:.1f}ms - {username}")
        return jsonify({
            "success": True,
            "token": access_token,
            "user": {
                "username": user['username'],
                "role": user['role'],
                "user_id": user['user_id']
            }
        }), 200
    except Exception as e:
        elapsed = (time.time() - start_time) * 1000
        print(f"[Auth] Login error: {e} ({elapsed:.1f}ms)")
        return jsonify({"success": False, "error": "Erreur interne"}), 500

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    role = data.get('role', 'patient')
    if not username or not password:
        return jsonify({"error": "Nom d'utilisateur et mot de passe requis"}), 400
    if role not in ['patient', 'secretaire', 'medical', 'admin']:
        return jsonify({"error": "Rôle invalide"}), 400
    if username.lower() in _users:
        return jsonify({"error": "Nom d'utilisateur déjà existant"}), 409
    import uuid
    user_id = str(uuid.uuid4())
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    _users[username.lower()] = {
        'username': username,
        'password_hash': hashed,
        'role': role,
        'user_id': user_id,
    }
    return jsonify({
        "success": True,
        "message": "Utilisateur créé avec succès",
        "user": {"user_id": user_id, "username": username, "role": role}
    }), 201

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    current_user = get_jwt_identity()
    user = _users.get(current_user.lower())
    if not user:
        return jsonify({"error": "Utilisateur non trouvé"}), 404
    return jsonify({"user": {
        "username": user['username'],
        "role": user['role'],
        "user_id": user['user_id']
    }}), 200

@auth_bp.route('/users', methods=['GET'])
@jwt_required()
def list_users():
    current_user = get_jwt_identity()
    user = _users.get(current_user.lower())
    if not user or user['role'] != 'admin':
        return jsonify({"error": "Accès administrateur requis"}), 403
    safe_users = [{'user_id': u['user_id'], 'username': u['username'], 'role': u['role']} for u in _users.values()]
    return jsonify({"users": safe_users}), 200
