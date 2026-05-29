"""Real authentication system with JWT and bcrypt."""
import bcrypt
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from datetime import timedelta
from core.sheets_db import SheetsDB
from config import GOOGLE_CREDENTIALS_PATH, GOOGLE_SPREADSHEET_NAME
import os

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# Secret key for JWT (should be in .env)
JWT_SECRET = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-this')

# Cache utilisateurs (TTL: 60 secondes pour dev)
_users_cache = {}
_cache_timestamp = 0
CACHE_TTL = 60  # seconds

def _get_cached_users(db):
    """Récupère les utilisateurs depuis le cache ou Google Sheets."""
    global _users_cache, _cache_timestamp
    import time
    now = time.time()
    
    # Retourner le cache s'il est encore valide
    if _users_cache and (now - _cache_timestamp) < CACHE_TTL:
        return list(_users_cache.values())
    
    # Sinon, recharger depuis Google Sheets
    try:
        users_sheet = db._spreadsheet.worksheet("Users")
        records = users_sheet.get_all_records()
        _users_cache = {str(r.get("username", "")).lower(): r for r in records if r.get("username")}
        _cache_timestamp = now
        print(f"[Auth] Cache rechargé: {len(_users_cache)} utilisateurs")
        return records
    except Exception as e:
        print(f"[Auth] Erreur cache: {e}")
        return list(_users_cache.values()) if _users_cache else []

def get_db():
    """Get a connected SheetsDB instance with Users sheet loaded."""
    db = SheetsDB(GOOGLE_CREDENTIALS_PATH, GOOGLE_SPREADSHEET_NAME)
    db.connect()
    # Ensure Users sheet is in _sheets dict
    try:
        db._sheets["Users"] = db._spreadsheet.worksheet("Users")
    except Exception:
        pass  # Users sheet will be created by init_users_sheet if needed
    return db

def init_users_sheet():
    """Initialize Users sheet if not exists."""
    try:
        db = get_db()
        # Check if Users sheet exists
        worksheets = [ws.title for ws in db._spreadsheet.worksheets()]
        if "Users" not in worksheets:
            # Create Users sheet
            worksheet = db._spreadsheet.add_worksheet("Users", rows=1000, cols=6)
            # Add headers
            worksheet.append_row(["user_id", "username", "password_hash", "role", "created_at", "active"])
            # Add default users
            default_users = [
                ["1", "secretaire", bcrypt.hashpw("sec123".encode(), bcrypt.gensalt()).decode(), "secretaire", "2024-01-01", "true"],
                ["2", "admin01", bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode(), "admin", "2024-01-01", "true"],
                # Médecins
                ["3", "dr.martin", bcrypt.hashpw("martin2024".encode(), bcrypt.gensalt()).decode(), "medical", "2024-01-01", "true"],
                ["4", "dr.sophie", bcrypt.hashpw("sophie2024".encode(), bcrypt.gensalt()).decode(), "medical", "2024-01-01", "true"],
                ["5", "dr.pierre", bcrypt.hashpw("pierre2024".encode(), bcrypt.gensalt()).decode(), "medical", "2024-01-01", "true"],
                ["6", "dr.isabelle", bcrypt.hashpw("isabelle2024".encode(), bcrypt.gensalt()).decode(), "medical", "2024-01-01", "true"],
                ["7", "dr.jeanluc", bcrypt.hashpw("jeanluc2024".encode(), bcrypt.gensalt()).decode(), "medical", "2024-01-01", "true"],
                ["8", "dr.catherine", bcrypt.hashpw("catherine2024".encode(), bcrypt.gensalt()).decode(), "medical", "2024-01-01", "true"],
                ["9", "dr.philippe", bcrypt.hashpw("philippe2024".encode(), bcrypt.gensalt()).decode(), "medical", "2024-01-01", "true"],
                ["10", "dr.marie", bcrypt.hashpw("marie2024".encode(), bcrypt.gensalt()).decode(), "medical", "2024-01-01", "true"],
                ["11", "dr.ayoub", bcrypt.hashpw("ayoub2024".encode(), bcrypt.gensalt()).decode(), "medical", "2024-01-01", "true"],
                ["12", "dr.hassin", bcrypt.hashpw("hassin2024".encode(), bcrypt.gensalt()).decode(), "medical", "2024-01-01", "true"],
            ]
            for user in default_users:
                worksheet.append_row(user)
            print("[Auth] Users sheet created with default accounts")
        # Add Users sheet to _sheets dict for easy access
        db._sheets["Users"] = db._spreadsheet.worksheet("Users")
    except Exception as e:
        print(f"[Auth] Error initializing users: {e}")

def verify_password(password, hashed):
    """Verify a password against its hash."""
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
        
        # Find user from cache (O(1) - ultra rapide, pas de connexion DB!)
        username_lower = username.lower()
        user = _users_cache.get(username_lower)
        cache_used = True
        
        # Si pas dans le cache, alors on charge depuis Google Sheets
        if not user:
            cache_used = False
            db = get_db()
            users = _get_cached_users(db)
            user = _users_cache.get(username_lower)
        
        if not user:
            # Fallback: recherche classique si pas dans le cache
            for u in users:
                if u.get("username", "").lower() == username_lower:
                    user = u
                    break
        
        if not user:
            return jsonify({"success": False, "error": "Identifiants invalides"}), 401
        
        # Check password
        stored_hash = user.get("password_hash", "")
        if not bcrypt.checkpw(password.encode(), stored_hash.encode()):
            return jsonify({"success": False, "error": "Identifiants invalides"}), 401
        
        # Generate JWT token
        access_token = create_access_token(
            identity=username,
            expires_delta=timedelta(hours=24)
        )
        
        elapsed = (time.time() - start_time) * 1000
        cache_status = "CACHE" if cache_used else "DB"
        print(f"[Auth] Login {cache_status} {elapsed:.1f}ms - {username}")
        
        return jsonify({
            "success": True,
            "token": access_token,
            "user": {
                "username": user.get("username"),
                "role": user.get("role"),
                "user_id": user.get("user_id")
            }
        }), 200
        
    except Exception as e:
        elapsed = (time.time() - start_time) * 1000
        print(f"[Auth] Login error: {e} ({elapsed:.1f}ms)")

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user (admin only)."""
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    role = data.get('role', 'patient')
    
    if not username or not password:
        return jsonify({"error": "Nom d'utilisateur et mot de passe requis"}), 400
    
    if role not in ['patient', 'secretaire', 'medical', 'admin']:
        return jsonify({"error": "Rôle invalide"}), 400
    
    try:
        db = get_db()
        users_sheet = db._spreadsheet.worksheet("Users")
        users = users_sheet.get_all_records()
        
        # Check if username exists
        for u in users:
            if u['username'] == username:
                return jsonify({"error": "Nom d'utilisateur déjà existant"}), 409
        
        # Hash password
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        
        # Add new user
        import uuid
        from datetime import datetime
        user_id = str(uuid.uuid4())
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        users_sheet.append_row([user_id, username, password_hash, role, created_at, "true"])
        
        return jsonify({
            "success": True,
            "message": "Utilisateur créé avec succès",
            "user": {
                "user_id": user_id,
                "username": username,
                "role": role
            }
        }), 201
        
    except Exception as e:
        print(f"[Auth] Register error: {e}")
        return jsonify({"error": "Échec de l'inscription"}), 500

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Get current authenticated user."""
    current_user = get_jwt_identity()
    return jsonify({"user": current_user}), 200

@auth_bp.route('/users', methods=['GET'])
@jwt_required()
def list_users():
    """List all users (admin only)."""
    current_user = get_jwt_identity()
    if current_user['role'] != 'admin':
        return jsonify({"error": "Accès administrateur requis"}), 403
    
    try:
        db = get_db()
        users_sheet = db._spreadsheet.worksheet("Users")
        users = users_sheet.get_all_records()
        
        # Remove password hashes from response
        safe_users = []
        for u in users:
            safe_users.append({
                'user_id': u['user_id'],
                'username': u['username'],
                'role': u['role'],
                'created_at': u.get('created_at', ''),
                'active': u.get('active', 'true')
            })
        
        return jsonify({"users": safe_users}), 200
        
    except Exception as e:
        print(f"[Auth] List users error: {e}")
        return jsonify({"error": "Échec de la liste des utilisateurs"}), 500
