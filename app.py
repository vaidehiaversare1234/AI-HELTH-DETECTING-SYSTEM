
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    send_file,
    session,
    flash
)
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from pathlib import Path
from io import BytesIO
from datetime import datetime
import sqlite3

from src.health_detector import HealthRiskPredictor

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm


# --------------------------------------------------
# 1. APPLICATION SETUP
# --------------------------------------------------

app = Flask(__name__)

# For local college project testing.
# Change this to a long, random secret before deployment.
app.secret_key = "change-this-to-a-long-random-secret"

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "database" / "health_history.db"

SYMPTOM_NAMES = {
    "fever": "Fever",
    "cough": "Cough",
    "fatigue": "Fatigue",
    "shortness_of_breath": "Shortness of Breath",
    "chest_pain": "Chest Pain"
}

predictor = HealthRiskPredictor()


# --------------------------------------------------
# 2. DATABASE CONNECTION
# --------------------------------------------------

def get_connection():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(DATABASE_PATH))
    return conn


# --------------------------------------------------
# 3. CREATE DATABASE TABLES
# --------------------------------------------------

def init_database():
    conn = get_connection()

    # Users table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Prediction history table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS prediction_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symptoms TEXT NOT NULL,
            health_status TEXT NOT NULL,
            risk_level TEXT NOT NULL,
            risk_score INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Add user_id to an existing database if it is missing.
    columns = conn.execute(
        "PRAGMA table_info(prediction_history)"
    ).fetchall()

    column_names = [column[1] for column in columns]

    if "user_id" not in column_names:
        conn.execute("""
            ALTER TABLE prediction_history
            ADD COLUMN user_id INTEGER
        """)

    conn.commit()
    conn.close()


# --------------------------------------------------
# 4. LOGIN REQUIRED DECORATOR
# --------------------------------------------------

def login_required(view_function):
    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "error")
            return redirect(url_for("login"))

        return view_function(*args, **kwargs)

    return wrapped_view


# --------------------------------------------------
# 5. REGISTRATION PAGE
# --------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("Please fill in all fields.", "error")
            return redirect(url_for("register"))

        if len(password) < 8:
            flash(
                "Password must contain at least 8 characters.",
                "error"
            )
            return redirect(url_for("register"))

        conn = get_connection()

        try:
            conn.execute("""
                INSERT INTO users (name, email, password)
                VALUES (?, ?, ?)
            """, (
                name,
                email,
                generate_password_hash(password)
            ))

            conn.commit()

        except sqlite3.IntegrityError:
            flash(
                "This email is already registered. Please log in.",
                "error"
            )
            return redirect(url_for("login"))

        finally:
            conn.close()

        flash(
            "Account created successfully. Please log in.",
            "success"
        )

        return redirect(url_for("login"))

    return render_template("register.html")


# --------------------------------------------------
# 6. LOGIN PAGE
# --------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        conn = get_connection()

        user = conn.execute("""
            SELECT id, name, email, password
            FROM users
            WHERE email = ?
        """, (email,)).fetchone()

        conn.close()

        if user and check_password_hash(user[3], password):
            session.clear()
            session["user_id"] = user[0]
            session["user_name"] = user[1]

            return redirect(url_for("home"))

        flash("Invalid email or password.", "error")
        return redirect(url_for("login"))

    return render_template("login.html")


# --------------------------------------------------
# 7. LOGOUT
# --------------------------------------------------

@app.route("/logout")
def logout():
    session.clear()

    flash("You have been logged out.", "success")

    return redirect(url_for("login"))


# --------------------------------------------------
# 8. HOME PAGE
# --------------------------------------------------

@app.route("/")
@login_required
def home():
    return render_template("index.html")


# --------------------------------------------------
# 9. HEALTH PREDICTION
# --------------------------------------------------

@app.route("/predict", methods=["POST"])
@login_required
def predict():

    # Read the selected symptoms from the form.
    symptoms = {
        key: 1 if request.form.get(key) == "1" else 0
        for key in SYMPTOM_NAMES
    }

    # Get prediction from the existing prediction model.
    result = predictor.predict(symptoms)

    risk_level = str(result["risk_level"])

    if risk_level.lower() == "low":
        status = "Low Risk"

    elif risk_level.lower() == "medium":
        status = "Needs Attention"

    elif risk_level.lower() == "high":
        status = "High Risk"

    else:
        status = risk_level

    result["status"] = status

    # Get the names of selected symptoms.
    selected_symptoms = [
        name
        for key, name in SYMPTOM_NAMES.items()
        if symptoms[key] == 1
    ]

    # Save prediction for the currently logged-in user.
    conn = get_connection()

    conn.execute("""
        INSERT INTO prediction_history
        (
            user_id,
            symptoms,
            health_status,
            risk_level,
            risk_score
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        session["user_id"],
        ", ".join(selected_symptoms) or "None selected",
        status,
        risk_level,
        result["score"]
    ))

    conn.commit()
    conn.close()

    return render_template(
        "result.html",
        result=result,
        selected_symptoms=selected_symptoms
    )


# --------------------------------------------------
# 10. USER'S PREDICTION HISTORY
# --------------------------------------------------

@app.route("/history")
@login_required
def history():

    conn = get_connection()

    cursor = conn.execute("""
        SELECT
            id,
            symptoms,
            health_status,
            risk_level,
            risk_score,
            created_at
        FROM prediction_history
        WHERE user_id = ?
        ORDER BY id DESC
    """, (session["user_id"],))

    history_records = cursor.fetchall()

    conn.close()

    return render_template(
        "history.html",
        history=history_records
    )


# --------------------------------------------------
# 11. DOWNLOAD PDF REPORT
# --------------------------------------------------

@app.route("/download-report")
@login_required
def download_report():

    # Fetch the latest report belonging to this user.
    conn = get_connection()

    cursor = conn.execute("""
        SELECT
            id,
            symptoms,
            health_status,
            risk_level,
            risk_score,
            created_at
        FROM prediction_history
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 1
    """, (session["user_id"],))

    record = cursor.fetchone()

    conn.close()

    if record is None:
        return (
            "Please make a prediction before downloading a report.",
            404
        )

    # Create the PDF in memory.
    pdf_buffer = BytesIO()

    pdf = canvas.Canvas(pdf_buffer, pagesize=A4)

    page_width, page_height = A4
    left = 2 * cm
    y = page_height - 2 * cm

    # Helper function to write text and wrap long lines.
    def write_line(text, font="Helvetica", size=11, gap=22):
        nonlocal y

        pdf.setFont(font, size)

        words = str(text).split()
        lines = []
        current_line = ""

        for word in words:
            candidate = (
                current_line + " " + word
                if current_line
                else word
            )

            if len(candidate) > 85:
                if current_line:
                    lines.append(current_line)

                current_line = word
            else:
                current_line = candidate

        if current_line:
            lines.append(current_line)

        if not lines:
            lines = [""]

        for line in lines:
            if y < 2 * cm:
                pdf.showPage()
                y = page_height - 2 * cm
                pdf.setFont(font, size)

            pdf.drawString(left, y, line)
            y -= gap

    # PDF title and prediction details.
    pdf.setTitle("AI Health Detecting System Report")

    write_line(
        "AI HEALTH DETECTING SYSTEM",
        "Helvetica-Bold",
        18,
        32
    )

    write_line(
        "Health Prediction Report",
        "Helvetica-Bold",
        14,
        30
    )

    write_line(
        "Generated: " + datetime.now().strftime("%d-%m-%Y %H:%M")
    )

    write_line(f"Prediction ID: {record[0]}")
    write_line(f"Selected symptoms: {record[1]}")
    write_line(f"Health status: {record[2]}")
    write_line(f"Risk level: {record[3]}")
    write_line(f"Symptom score: {record[4]} out of 5")
    write_line(f"Saved at: {record[5]}")

    y -= 8

    # General precautions.
    write_line(
        "GENERAL PRECAUTIONS",
        "Helvetica-Bold",
        13,
        25
    )

    precautions = [
        "Rest and avoid overexertion.",
        "Drink fluids unless medically restricted.",
        "Seek medical advice if symptoms persist or worsen.",
        "Seek emergency help for severe breathing difficulty "
        "or serious chest pain."
    ]

    for item in precautions:
        write_line("- " + item, size=10, gap=19)

    y -= 8

    # General diet recommendations.
    write_line(
        "GENERAL DIET RECOMMENDATIONS",
        "Helvetica-Bold",
        13,
        25
    )

    diet = [
        "Drink water regularly, unless medically restricted.",
        "Choose balanced meals with fruits and vegetables.",
        "Include suitable sources of protein in meals.",
        "Follow advice from your healthcare professional."
    ]

    for item in diet:
        write_line("- " + item, size=10, gap=19)

    y -= 8

    # Medical disclaimer.
    write_line(
        "MEDICAL DISCLAIMER",
        "Helvetica-Bold",
        12,
        22
    )

    write_line(
        "This educational project is not a medical diagnostic tool.",
        size=9,
        gap=15
    )

    write_line(
        "Its predictions may be inaccurate. Do not delay medical care.",
        size=9,
        gap=15
    )

    write_line(
        "Consult a qualified healthcare professional for medical advice.",
        size=9,
        gap=15
    )

    write_line(
        "Seek emergency help for severe or life-threatening symptoms.",
        size=9,
        gap=15
    )

    # Finish the PDF.
    pdf.save()
    pdf_buffer.seek(0)

    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name="health_prediction_report.pdf",
        mimetype="application/pdf"
    )


# --------------------------------------------------
# 12. RUN THE APPLICATION
# --------------------------------------------------

if __name__ == "__main__":
    init_database()
    app.run(debug=True)