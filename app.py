from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from pymongo import MongoClient
from dotenv import load_dotenv
from ai_service import solve_doubt, explain_code, interview_prep, mock_interview
from auth import auth_bp
from payments import payments_bp
import os

load_dotenv()

app = Flask(__name__)
CORS(app)

# ─── JWT CONFIG ───────────────────────────────────────────────────────────────
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "changeme123")
jwt = JWTManager(app)

# ─── MONGODB ──────────────────────────────────────────────────────────────────
client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017/"))
app.db = client["dsa_mentor"]

# ─── BLUEPRINTS ───────────────────────────────────────────────────────────────
app.register_blueprint(auth_bp,     url_prefix="/api/auth")
app.register_blueprint(payments_bp, url_prefix="/api/payments")


# ─── HEALTH CHECK ─────────────────────────────────────────────────────────────
@app.route("/api/health")
def health():
    return jsonify({"message": "DSA Mentor AI is alive! 🚀"})


# ─── 1. DSA MENTOR ────────────────────────────────────────────────────────────
@app.route("/api/ask", methods=["POST"])
def ask():
    data        = request.get_json()
    code        = data.get("code", "")
    question    = data.get("question", "")
    mode        = data.get("mode", "debug")
    target_lang = data.get("target_lang", "Python")

    if not code.strip() and not question.strip():
        return jsonify({"error": "Please provide code or a question"}), 400

    try:
        return jsonify({"response": solve_doubt(code, question, mode, target_lang)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── 2. CODE EXPLAINER ────────────────────────────────────────────────────────
@app.route("/api/explain", methods=["POST"])
def explain():
    data     = request.get_json()
    code     = data.get("code", "")
    mode     = data.get("mode", "explain")
    language = data.get("language", "")

    if not code.strip():
        return jsonify({"error": "Please provide code"}), 400

    try:
        return jsonify({"response": explain_code(code, mode, language)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── 3. INTERVIEW PREP ────────────────────────────────────────────────────────
@app.route("/api/interview", methods=["POST"])
def interview():
    data          = request.get_json()
    topic         = data.get("topic", "Arrays")
    difficulty    = data.get("difficulty", "Medium")
    question_type = data.get("question_type", "Coding")

    try:
        return jsonify({"response": interview_prep(topic, difficulty, question_type)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── 4. MOCK INTERVIEW ────────────────────────────────────────────────────────
@app.route("/api/mock", methods=["POST"])
def mock():
    data         = request.get_json()
    stage        = data.get("stage", "start")
    user_message = data.get("message", "")
    history      = data.get("history", [])

    try:
        return jsonify({"response": mock_interview(stage, user_message, history)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── RUN ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, port=5000)