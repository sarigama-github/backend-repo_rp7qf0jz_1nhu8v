import os
import random
import string
from datetime import datetime, timezone
from typing import List, Optional, Literal

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from database import db

app = FastAPI(title="AI Mock Interview API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------------------- Models -----------------------------
class SessionCreate(BaseModel):
    mode: Literal["text", "voice"]
    job_role: str
    experience: str
    company: Optional[str] = None
    difficulty: Literal["Easy", "Intermediate", "Advanced", "Mixed"]
    resume_text: Optional[str] = None


class TextAnswer(BaseModel):
    session_id: str
    question_id: str
    answer: str


# ---------------------------- Utilities ---------------------------
QUESTIONS_BANK = {
    "Easy": [
        ("Explain the difference between HTTP and HTTPS.", "HTTPS is HTTP over TLS providing encryption, integrity, and authentication."),
        ("What is a REST API?", "An architectural style using stateless communication over HTTP with resources identified by URIs."),
    ],
    "Intermediate": [
        ("Describe how you would design a URL shortener.", "Use hash/id mapping, datastore, caching, redirect service, rate limiting, and analytics."),
        ("Explain CAP theorem.", "In distributed systems you can only have two of Consistency, Availability, and Partition tolerance."),
    ],
    "Advanced": [
        ("How does a garbage collector work in managed runtimes?", "It tracks object reachability, reclaims unreachable memory via algorithms like mark-sweep, generational GC."),
        ("What strategies would you use to scale a write-heavy database?", "Sharding, write queues, batching, eventual consistency, appropriate indexes, partitioning."),
    ],
}


def _make_id(prefix: str = "sess") -> str:
    return f"{prefix}_" + ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))


def _pick_question(difficulty: str):
    pool: List = []
    if difficulty == "Mixed":
        for k in ("Easy", "Intermediate", "Advanced"):
            pool.extend([(q, a, k) for q, a in QUESTIONS_BANK[k]])
    else:
        pool = [(q, a, difficulty) for q, a in QUESTIONS_BANK.get(difficulty, [])]
    if not pool:
        pool = [("Tell me about yourself.", "Give a concise summary of your background, achievements, and goals." , difficulty)]
    q, a, level = random.choice(pool)
    return {
        "id": _make_id("q"),
        "text": q,
        "difficulty": level,
        "correct_answer": a,
    }


# ----------------------------- Routes -----------------------------
@app.get("/")
def root():
    return {"message": "AI Mock Interview Backend running"}


@app.get("/api/pricing")
def pricing():
    return {
        "text": {"price": 49, "currency": "INR", "label": "Text Interview"},
        "voice": {"price": 119, "currency": "INR", "label": "Voice Interview"},
        "bundle_note": "4 rounds + instant feedback"
    }


@app.post("/api/resume/extract")
async def extract_resume(file: UploadFile = File(...)):
    content = await file.read()
    text_preview = content[:200].decode(errors="ignore") if content else ""
    skills = ["Python", "APIs", "React", "System Design"]
    return {"status": "ok", "skills": skills, "preview": text_preview}


@app.post("/api/session")
def create_session(payload: SessionCreate):
    session_id = _make_id()
    doc = {
        "_id": session_id,
        "mode": payload.mode,
        "job_role": payload.job_role,
        "experience": payload.experience,
        "company": payload.company,
        "difficulty": payload.difficulty,
        "resume_text": payload.resume_text,
        "paid": True,  # mock as paid after UI payment step
        "progress": {"current": 0, "total": 5},
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    if db is None:
        # Allow app to run even if DB not configured
        return {"session_id": session_id, "progress": doc["progress"]}
    db["session"].insert_one(doc)
    return {"session_id": session_id, "progress": doc["progress"]}


@app.get("/api/text/question")
def get_text_question(session_id: str, difficulty: Optional[str] = None):
    q = _pick_question(difficulty or "Mixed")
    return {
        "question": {
            "id": q["id"],
            "text": q["text"],
            "difficulty": q["difficulty"],
        },
        "progress": {"current": random.randint(1, 5), "total": 5}
    }


@app.post("/api/text/answer")
def submit_text_answer(payload: TextAnswer):
    # rudimentary scoring
    answer_len = len(payload.answer.strip())
    content_score = max(30, min(100, answer_len // 5 + 40))
    correct = content_score > 60
    feedback = {
        "correct": correct,
        "grammar_fixes": "Capitalize proper nouns. Keep sentences concise.",
        "content_score": content_score,
        "correct_answer": "Sample ideal answer with structured points and examples.",
        "next_available": True,
    }
    if db is not None:
        db["response"].insert_one({
            "session_id": payload.session_id,
            "question_id": payload.question_id,
            "answer": payload.answer,
            "feedback": feedback,
            "created_at": datetime.now(timezone.utc),
        })
    return feedback


@app.post("/api/voice/answer")
async def submit_voice_answer(session_id: str = Form(...), question_id: str = Form(...), audio: UploadFile = File(...)):
    # mock analysis
    return {
        "tone": 78,
        "clarity": 82,
        "confidence": 75,
        "grammar": 80,
        "correct_answer": "Ideal answer outline for the asked question.",
    }


@app.get("/api/summary")
def round_summary(session_id: str):
    strengths = ["Clear structure", "Good examples"]
    mistakes = ["Missed edge cases", "Overlong intro"]
    tips = ["Use STAR format", "Quantify impact", "Conclude crisply"]
    return {
        "score": 76,
        "strengths": strengths,
        "mistakes": mistakes,
        "tips": tips,
    }


@app.get("/api/report")
def final_report(session_id: str):
    categories = {
        "Technical": 78,
        "Coding": 72,
        "Logical": 80,
        "HR": 70,
        "Communication": 82,
    }
    plan = [
        "Day 1-2: Review data structures",
        "Day 3-4: Mock interviews (2/day)",
        "Day 5: Behavioral answers",
        "Day 6: System design drills",
        "Day 7: Full-length simulation",
    ]
    return {"categories": categories, "plan": plan, "overall": 76}


@app.post("/api/payment/initiate")
async def payment_initiate(amount: int = Form(...), mode: str = Form(...)):
    return {"status": "success", "transaction_id": _make_id("pay"), "amount": amount, "mode": mode}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    # Env flags
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
