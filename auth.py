from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
import bcrypt
from datetime import datetime
from bson import ObjectId

auth_bp = Blueprint("auth", __name__)

def get_db():
    return current_app.db


@auth_bp.route("/register", methods=["POST"])
def register():
    db   = get_db()
    data = request.get_json()

    name     = data.get("name", "").strip()
    email    = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not name or not email or not password:
        return jsonify({"error": "All fields required"}), 400

    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    if db.users.find_one({"email": email}):
        return jsonify({"error": "Email already registered"}), 409

    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

    user = {
        "name":         name,
        "email":        email,
        "password":     hashed,
        "plan":         "free",
        "doubts_today": 0,
        "last_reset":   datetime.utcnow().strftime("%Y-%m-%d"),
        "total_doubts": 0,
        "created_at":   datetime.utcnow(),
    }

    result = db.users.insert_one(user)
    token  = create_access_token(identity=str(result.inserted_id))

    return jsonify({
        "message": "Account created!",
        "token": token,
        "user": {
            "id":    str(result.inserted_id),
            "name":  name,
            "email": email,
            "plan":  "free",
        }
    }), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    db   = get_db()
    data = request.get_json()

    email    = data.get("email", "").strip().lower()
    password = data.get("password", "")

    user = db.users.find_one({"email": email})
    if not user:
        return jsonify({"error": "Invalid email or password"}), 401

    if not bcrypt.checkpw(password.encode("utf-8"), user["password"]):
        return jsonify({"error": "Invalid email or password"}), 401

    token = create_access_token(identity=str(user["_id"]))

    return jsonify({
        "token": token,
        "user": {
            "id":    str(user["_id"]),
            "name":  user["name"],
            "email": user["email"],
            "plan":  user.get("plan", "free"),
        }
    }), 200


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_profile():
    db      = get_db()
    user_id = get_jwt_identity()
    user    = db.users.find_one({"_id": ObjectId(user_id)})

    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "id":           str(user["_id"]),
        "name":         user["name"],
        "email":        user["email"],
        "plan":         user.get("plan", "free"),
        "doubts_today": user.get("doubts_today", 0),
        "total_doubts": user.get("total_doubts", 0),
    }), 200