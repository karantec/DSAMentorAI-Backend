from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from pymongo import MongoClient
import re        # ← add this
import json    
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
import requests
import os
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = "openrouter/free"


# ─── HELPER ──────────────────────────────────────────────────────────────────

def call_ai(system_prompt, user_prompt):
    """Single function to call OpenRouter API."""
    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ]
        }
    )
    data = response.json()
    print("OPENROUTER RAW RESPONSE:", data)  # ← add this
    return data["choices"][0]["message"]["content"]

# ─── 1. DSA MENTOR ───────────────────────────────────────────────────────────

def build_prompt(code, question, mode, target_lang="Python"):
    code_block    = f"\n```\n{code}\n```\n" if code.strip() else "\n(No code provided)\n"
    question_text = question.strip() if question.strip() else "(No specific question)"
    base          = f"User's Code:{code_block}\nUser's Question: {question_text}\n"

    prompts = {
        "debug": f"""{base}
Find the bug(s), explain why it's wrong, show the fixed code, and list edge cases to test.""",

        "optimize": f"""{base}
1. Current time & space complexity
2. Better approach explanation
3. Optimized code
4. New complexity
5. 3 similar LeetCode problems to practice""",

        "beginner": f"""{base}
Explain this like I'm a complete beginner. Use simple words, a real-world analogy,
and add comments to every line of code.""",

        "interview": f"""{base}
Give an interview-ready explanation:
1. Pattern recognition (DP? Graph? Sliding window?)
2. Brute force → optimal progression
3. Key talking points
4. Time & space complexity
5. 3 follow-up questions an interviewer might ask""",

        "convert": f"""{base}
Convert this code to {target_lang}. Show the converted code and explain key differences.""",
    }

    return prompts.get(mode, prompts["debug"])


def solve_doubt(code, question, mode, target_lang="Python"):
    prompt = build_prompt(code, question, mode, target_lang)
    return call_ai(
        system_prompt="You are DSA Mentor AI — an expert DSA and competitive programming tutor. Be concise, structured, and use code blocks for all code.",
        user_prompt=prompt
    )


# ─── 2. CODE EXPLAINER ───────────────────────────────────────────────────────

def explain_code(code, mode, language=""):
    lang_hint = f"The code is written in {language}." if language else ""

    prompts = {
        "explain": f"""You are a code explanation expert.
{lang_hint}
Explain this code in plain English, line by line. Use simple language.
For each section, explain WHAT it does and WHY.

Code:
```
{code}
```""",

        "beginner": f"""You are teaching a complete beginner.
{lang_hint}
Explain this code like I have never programmed before.
- Use simple real-world analogies
- Avoid technical jargon
- Break it into tiny steps
- Add what each line does in simple words

Code:
```
{code}
```""",

        "flowchart": f"""Explain the logical flow of this code.
{lang_hint}
Show how data moves through the program step by step.
Use arrows and simple diagrams using text like:
Input → Step 1 → Step 2 → Output

Code:
```
{code}
```""",

        "complexity": f"""Analyze the time and space complexity of this code.
{lang_hint}
1. Overall Time Complexity with explanation
2. Overall Space Complexity with explanation
3. Break down complexity of each function/loop
4. Suggest how to improve if possible

Code:
```
{code}
```""",
    }

    prompt = prompts.get(mode, prompts["explain"])
    return call_ai(
        system_prompt="You are an expert code explainer. Always be clear, structured and beginner friendly.",
        user_prompt=prompt
    )


# ─── 3. INTERVIEW PREP ───────────────────────────────────────────────────────

@app.route("/api/interview", methods=["POST", "OPTIONS"])
def interview():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    if not OPENROUTER_API_KEY:
        return jsonify({"error": "OPENROUTER_API_KEY not set"}), 500

    data      = request.json or {}
    topic     = data.get("topic", "Arrays")
    difficulty= data.get("difficulty", "Medium")
    q_type    = data.get("question_type", "Coding")
    count     = min(int(data.get("count", 20)), 100)  # cap at 20

    system_prompt = """You are an expert DSA interview question generator.
Generate interview questions in strict JSON format only.
Return ONLY a JSON array with no markdown, no explanation, no code fences — just raw JSON.

Each element must have exactly these keys:
- "title": short question title (string)
- "description": full question with examples/constraints (string)
- "hint": a helpful hint without giving away the solution (string)
- "solution": full solution with code and explanation (string)
"""

    user_msg = f"""Generate exactly {count} {difficulty} {q_type} interview questions on the topic: {topic}.

Return ONLY a valid JSON array like this:
[
  {{
    "title": "Two Sum",
    "description": "Given an array of integers...",
    "hint": "Think about using a hash map...",
    "solution": "Use a dictionary to store seen values..."
  }}
]
"""

    try:
        raw = call_ai(system_prompt, user_msg)

        # Strip markdown fences if model added them
        raw = raw.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        raw = raw.strip()

        questions = json.loads(raw)

        if not isinstance(questions, list):
            raise ValueError("AI did not return a JSON array")

        # Ensure all required keys exist
        clean = []
        for i, q in enumerate(questions):
            clean.append({
                "title":       q.get("title",       f"Question {i+1}"),
                "description": q.get("description", ""),
                "hint":        q.get("hint",        ""),
                "solution":    q.get("solution",    ""),
            })

        return jsonify({"questions": clean})

    except json.JSONDecodeError as e:
        print(f"[JSON PARSE ERROR] {e}\nRaw:\n{raw[:500]}")
        # Fallback: return raw as single question
        return jsonify({"questions": [{"title": "Question 1", "description": raw, "hint": "", "solution": ""}]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── 4. MOCK INTERVIEW ───────────────────────────────────────────────────────

def mock_interview(stage, user_message, history, question=""):
    if stage == "start":
        prompt = """Start a mock coding interview. 
Introduce yourself as the interviewer, greet the candidate warmly,
then ask ONE DSA coding question (medium difficulty).
Be professional but friendly."""

    elif stage == "chat":
        history_text = "\n".join([
            f"{'Interviewer' if m['role'] == 'assistant' else 'Candidate'}: {m['content']}"
            for m in history
        ])
        prompt = f"""You are conducting a mock coding interview.

Conversation so far:
{history_text}

Candidate just said: {user_message}

Respond as the interviewer:
- If they're on the right track, give a small hint or encouragement
- If they're stuck, guide them with a question (don't give the answer directly)
- If they gave a solution, evaluate it, ask about complexity, then ask a follow-up
- Keep it realistic and professional"""

    elif stage == "end":
        history_text = "\n".join([
            f"{'Interviewer' if m['role'] == 'assistant' else 'Candidate'}: {m['content']}"
            for m in history
        ])
        prompt = f"""This mock interview just ended. Based on the conversation:

{history_text}

Give a detailed performance review:
1. Overall Score (out of 10)
2. Strengths — What they did well
3. Areas to Improve — Be specific and constructive
4. Communication — How well they explained their thinking
5. Next Steps — What to study/practice"""

    return call_ai(
        system_prompt="You are an experienced software engineer conducting a technical interview at a top tech company. Be professional, realistic, and helpful.",
        user_prompt=prompt
    )
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