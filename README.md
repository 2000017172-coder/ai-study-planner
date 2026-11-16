# AI-Powered Student Study Planner

A beginner-friendly BTech mini-project built with Python and Streamlit.

## Features
- Add and manage subjects, exam dates, difficulty and confidence levels.
- Generate a weighted study timetable locally (no API key required).
- Download the timetable as a CSV file.
- Record completed study sessions.
- View a dashboard of subjects, upcoming exams and logged study hours.
- Optional Gemini-powered study assistant (requires your own API key).

## Run on Windows
1. Install Python 3.10 or newer from https://www.python.org/downloads/windows/
2. Extract this project ZIP.
3. Open the extracted folder in VS Code.
4. Open Terminal > New Terminal.
5. Create a virtual environment:
   ```powershell
   py -m venv .venv
   ```
6. Activate it:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```
   If PowerShell blocks activation, use Command Prompt:
   ```cmd
   .venv\Scripts\activate.bat
   ```
7. Install dependencies:
   ```powershell
   python -m pip install -r requirements.txt
   ```
8. Start the app:
   ```powershell
   python -m streamlit run app.py
   ```
9. Streamlit opens the app in your browser, usually at http://localhost:8501

## Optional Gemini AI setup
- Create an API key through Google AI Studio: https://aistudio.google.com/app/apikey
- Run the app and paste the key into the password field in the left sidebar.
- The key is not saved by this project; it is held in the current app session and sent to Google's Gemini API only when you press **Ask AI**.
- If you do not have a key, the timetable generator, dashboard, subject manager and progress log still work.

## Data and privacy
- Subject details and study logs are stored locally in `study_planner.db` after the app is first run.
- Do not enter passwords, private identifiers or sensitive personal information.
- Deleting `study_planner.db` resets the local app data.

## Testing checklist
1. Add at least two subjects with different exam dates.
2. Generate a timetable for 5–7 days.
3. Check that the generated plan lists subjects and hours.
4. Download the CSV and open it.
5. Log a study session and verify the dashboard total increases.
6. Delete a test subject and verify it disappears.
7. If using Gemini, test a simple study question and record the actual result.

## Project limitations
- Timetable allocation is a simple weighted heuristic, not a trained machine-learning model.
- Gemini features require internet access and a valid API key.
- The timetable is a recommendation; students should adjust it for lectures, breaks and personal commitments.
- The app does not verify syllabus coverage or guarantee academic results.

## Suggested demonstration
Add sample subjects such as Mathematics, Programming and Physics with different exam dates and difficulty ratings. Generate a 7-day plan, log a study session, and show the dashboard. Use clearly labelled sample data during the presentation.
