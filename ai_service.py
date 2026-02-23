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

def interview_prep(topic, difficulty, question_type):
    prompt = f"""Generate a DSA interview question with full solution.

Topic: {topic}
Difficulty: {difficulty}
Type: {question_type}

Respond with:
1. Question — Clear problem statement with example input/output
2. Hint — One small nudge without giving away the answer
3. Approach — Step by step strategy to solve it
4. Solution Code — Clean Python solution with comments
5. Complexity — Time and space complexity
6. Follow-up — One harder variation of this problem"""

    return call_ai(
        system_prompt="You are an expert DSA interview coach. Generate clear, realistic interview questions.",
        user_prompt=prompt
    )


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