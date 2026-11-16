import os
import sqlite3
import json
from datetime import date, datetime, timedelta
from pathlib import Path

import requests
import streamlit as st

APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / "study_planner.db"
GEMINI_MODEL = "gemini-2.5-flash"

st.set_page_config(page_title="AI Study Planner", page_icon="📚", layout="wide")

def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                exam_date TEXT NOT NULL,
                difficulty INTEGER NOT NULL,
                confidence INTEGER NOT NULL,
                notes TEXT DEFAULT ''
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS study_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER NOT NULL,
                study_date TEXT NOT NULL,
                hours REAL NOT NULL,
                completed INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY(subject_id) REFERENCES subjects(id)
            )
        """)

def load_subjects():
    with get_connection() as conn:
        return conn.execute("SELECT * FROM subjects ORDER BY exam_date").fetchall()

def add_subject(name, exam_date, difficulty, confidence, notes):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO subjects(name, exam_date, difficulty, confidence, notes) VALUES (?, ?, ?, ?, ?)",
            (name.strip(), exam_date.isoformat(), difficulty, confidence, notes.strip())
        )

def delete_subject(subject_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM study_log WHERE subject_id = ?", (subject_id,))
        conn.execute("DELETE FROM subjects WHERE id = ?", (subject_id,))

def add_study_log(subject_id, study_date, hours):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO study_log(subject_id, study_date, hours, completed) VALUES (?, ?, ?, 1)",
            (subject_id, study_date.isoformat(), hours)
        )

def get_study_logs():
    with get_connection() as conn:
        return conn.execute("""
            SELECT study_log.*, subjects.name AS subject_name
            FROM study_log JOIN subjects ON subjects.id = study_log.subject_id
            ORDER BY study_date DESC
        """).fetchall()

def build_local_plan(subjects, daily_hours, start_date, end_date):
    """Create a simple weighted study plan without an external AI service."""
    if not subjects:
        return []
    days = max(1, (end_date - start_date).days + 1)
    plan = []
    weights = []
    for s in subjects:
        days_left = max(1, (date.fromisoformat(s["exam_date"]) - start_date).days)
        difficulty = int(s["difficulty"])
        confidence = int(s["confidence"])
        # Higher difficulty and lower confidence increase priority.
        weight = (difficulty * 1.4) + ((6 - confidence) * 1.2) + (7 / min(days_left, 7))
        weights.append((s, weight))
    total_weight = sum(w for _, w in weights)
    for offset in range(days):
        current = start_date + timedelta(days=offset)
        if current > end_date:
            break
        remaining = [item for item in weights if date.fromisoformat(item[0]["exam_date"]) >= current]
        if not remaining:
            continue
        remaining_total = sum(w for _, w in remaining)
        sessions = []
        for subject, weight in remaining:
            hours = round(daily_hours * weight / remaining_total, 1)
            if hours >= 0.2:
                sessions.append({
                    "date": current.isoformat(),
                    "subject": subject["name"],
                    "hours": hours,
                    "reason": "Weighted by difficulty, confidence and exam proximity."
                })
        # Adjust rounding so daily allocation does not exceed the chosen limit.
        total = sum(x["hours"] for x in sessions)
        if total > daily_hours and sessions:
            excess = round(total - daily_hours, 1)
            sessions[-1]["hours"] = max(0.2, round(sessions[-1]["hours"] - excess, 1))
        plan.extend(sessions)
    return plan

def ask_gemini(prompt, api_key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={api_key}"
    payload = {"contents": [{"parts": [{"text": prompt}]}],
               "generationConfig": {"temperature": 0.4, "maxOutputTokens": 1800}}
    response = requests.post(url, json=payload, timeout=35)
    response.raise_for_status()
    data = response.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]

initialize_db()

st.title("📚 AI-Powered Student Study Planner")
st.caption("Plan smarter, prepare steadily, and track your study progress.")
st.info("This student project includes a local timetable generator. Add a Gemini API key in the sidebar to enable AI-generated advice and the AI study assistant.")

with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input("Gemini API key (optional)", type="password",
                            help="Your key is used only when you request an AI response.")
    st.caption("No API key? The timetable generator still works locally.")
    st.divider()
    st.markdown("**How to use**")
    st.markdown("1. Add your subjects.\n2. Generate a timetable.\n3. Record completed study sessions.\n4. Ask the AI assistant for study tips (API key required).")

tab1, tab2, tab3, tab4 = st.tabs(["🏠 Dashboard", "📘 Subjects", "🗓️ Study Planner", "🤖 AI Assistant"])

subjects = load_subjects()
logs = get_study_logs()

with tab1:
    st.subheader("Your study overview")
    c1, c2, c3 = st.columns(3)
    c1.metric("Subjects added", len(subjects))
    c2.metric("Study hours logged", round(sum(float(x["hours"]) for x in logs), 1))
    upcoming = [s for s in subjects if date.fromisoformat(s["exam_date"]) >= date.today()]
    c3.metric("Upcoming exams", len(upcoming))
    st.divider()
    if subjects:
        st.markdown("### Upcoming examinations")
        for s in subjects:
            exam = date.fromisoformat(s["exam_date"])
            days_left = (exam - date.today()).days
            label = "Today" if days_left == 0 else ("Past date" if days_left < 0 else f"{days_left} days left")
            st.write(f"**{s['name']}** — {exam.strftime('%d %b %Y')} · {label}")
    else:
        st.write("No subjects yet. Open the **Subjects** tab to add your first subject.")
    if logs:
        st.markdown("### Recent study activity")
        for item in logs[:5]:
            st.write(f"• {item['study_date']} — {item['subject_name']}: {item['hours']} hour(s)")

with tab2:
    st.subheader("Manage your subjects")
    with st.form("subject_form", clear_on_submit=True):
        name = st.text_input("Subject name", placeholder="e.g. Programming for Problem Solving")
        exam_date = st.date_input("Examination date", value=date.today() + timedelta(days=14),
                                  min_value=date.today())
        col_a, col_b = st.columns(2)
        difficulty = col_a.slider("Difficulty (1 = easy, 5 = difficult)", 1, 5, 3)
        confidence = col_b.slider("Your confidence (1 = low, 5 = high)", 1, 5, 3)
        notes = st.text_area("Topics or notes (optional)")
        submitted = st.form_submit_button("Add subject")
        if submitted:
            if name.strip():
                add_subject(name, exam_date, difficulty, confidence, notes)
                st.success(f"Added {name}.")
                st.rerun()
            else:
                st.error("Please enter a subject name.")
    st.markdown("### Saved subjects")
    subjects = load_subjects()
    if subjects:
        for s in subjects:
            col1, col2 = st.columns([5, 1])
            col1.write(f"**{s['name']}** · Exam: {s['exam_date']} · Difficulty: {s['difficulty']}/5 · Confidence: {s['confidence']}/5")
            if col2.button("Delete", key=f"delete_{s['id']}"):
                delete_subject(s["id"])
                st.rerun()
            if s["notes"]:
                st.caption(s["notes"])
    else:
        st.caption("Your subjects will appear here.")

with tab3:
    st.subheader("Generate your study timetable")
    subjects = load_subjects()
    if not subjects:
        st.warning("Add at least one subject in the Subjects tab first.")
    else:
        c1, c2 = st.columns(2)
        daily_hours = c1.slider("Available study hours per day", 1, 12, 4)
        horizon = c2.slider("Plan for the next (days)", 1, 30, 7)
        if st.button("✨ Generate study plan", type="primary"):
            start = date.today()
            end = start + timedelta(days=horizon - 1)
            plan = build_local_plan(subjects, daily_hours, start, end)
            st.session_state["study_plan"] = plan
            st.session_state["plan_start"] = start.isoformat()
            st.session_state["plan_end"] = end.isoformat()
        plan = st.session_state.get("study_plan", [])
        if plan:
            st.success("Your timetable is ready. Treat it as a suggested plan and adjust it around classes and breaks.")
            for day in sorted(set(x["date"] for x in plan)):
                st.markdown(f"**{datetime.strptime(day, '%Y-%m-%d').strftime('%A, %d %b')}**")
                day_items = [x for x in plan if x["date"] == day]
                for item in day_items:
                    st.write(f"• {item['subject']}: **{item['hours']} hour(s)**")
            st.download_button("Download timetable (CSV)", 
                data="Date,Subject,Hours,Reason\n" + "\n".join(
                    f"{x['date']},{json.dumps(x['subject'])},{x['hours']},{json.dumps(x['reason'])}" for x in plan),
                file_name="study_timetable.csv", mime="text/csv")
    st.divider()
    st.markdown("### Log a completed study session")
    subjects = load_subjects()
    if subjects:
        options = {s["name"]: s["id"] for s in subjects}
        with st.form("log_form", clear_on_submit=True):
            selected = st.selectbox("Subject", list(options.keys()))
            log_date = st.date_input("Study date", value=date.today())
            hours = st.number_input("Hours studied", min_value=0.25, max_value=12.0, value=1.0, step=0.25)
            if st.form_submit_button("Save study session"):
                add_study_log(options[selected], log_date, hours)
                st.success("Study session saved.")
                st.rerun()
    else:
        st.caption("Add a subject before logging a study session.")

with tab4:
    st.subheader("AI study assistant")
    st.write("Ask for a revision strategy, topic breakdown, or general study advice.")
    question = st.text_area("Your question", placeholder="How should I revise three subjects in one week?")
    if st.button("Ask AI"):
        if not question.strip():
            st.warning("Enter a question first.")
        elif not api_key.strip():
            st.warning("Add your Gemini API key in the sidebar to use the AI assistant. The timetable feature works without it.")
        else:
            context = "\n".join([f"- {s['name']}: exam {s['exam_date']}, difficulty {s['difficulty']}/5, confidence {s['confidence']}/5" for s in load_subjects()])
            prompt = ("You are a supportive study-planning assistant for a college student. "
                      "Give practical, safe, realistic advice. Do not guarantee grades. "
                      f"\nStudent subjects:\n{context or 'No subjects added.'}\nQuestion: {question}")
            with st.spinner("Getting study advice..."):
                try:
                    st.markdown(ask_gemini(prompt, api_key))
                except Exception as exc:
                    st.error(f"AI request failed: {exc}. Check your API key and internet connection.")
    st.caption("AI responses can be inaccurate. Verify important academic information with your course materials or faculty.")

st.divider()
st.caption("Mini Project 1 · AI-Based Application Development | Student Study Planner")
