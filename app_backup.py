
from flask import Flask, render_template, request, send_file
from pathlib import Path
from io import BytesIO
from datetime import datetime
import sqlite3

from src.health_detector import HealthRiskPredictor

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm


# ==========================================
# 1. CREATE FLASK APPLICATION
# ==========================================

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "database" / "health_history.db"


# ==========================================
# 2. SYMPTOM NAMES
# ==========================================

SYMPTOM_NAMES = {
    "fever": "Fever",
    "cough": "Cough",
    "fatigue": "Fatigue",
    "shortness_of_breath": "Shortness of Breath",
    "chest_pain": "Chest Pain"
}

# Load the existing trained model
predictor = HealthRiskPredictor()


# ==========================================
# 3. DATABASE CONNECTION
# ==========================================

def get_connection():
    DATABASE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )
    return sqlite3.connect(str(DATABASE_PATH))


# ==========================================
# 4. INITIALIZE DATABASE
# ==========================================

def init_database():
    conn = get_connection()

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

    conn.commit()
    conn.close()


# ==========================================
# 5. HOME PAGE
# ==========================================

@app.route("/")
def home():
    return render_template("index.html")


# ==========================================
# 6. HEALTH RISK PREDICTION
# ==========================================

@app.route("/predict", methods=["POST"])
def predict():

    # Read the five symptom inputs from the form
    symptoms = {
        key: 1 if request.form.get(key) == "1" else 0
        for key in SYMPTOM_NAMES
    }

    # Run the existing machine-learning model
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

    # Get selected symptom names
    selected_symptoms = [
        name
        for key, name in SYMPTOM_NAMES.items()
        if symptoms[key] == 1
    ]

    # Store the prediction in SQLite
    conn = get_connection()

    conn.execute("""
        INSERT INTO prediction_history
        (symptoms, health_status, risk_level, risk_score)
        VALUES (?, ?, ?, ?)
    """, (
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


# ==========================================
# 7. VIEW PREDICTION HISTORY
# ==========================================

@app.route("/history")
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
        ORDER BY id DESC
    """)

    history_records = cursor.fetchall()
    conn.close()

    return render_template(
        "history.html",
        history=history_records
    )


# ==========================================
# 8. DOWNLOAD PDF HEALTH REPORT
# ==========================================

@app.route("/download-report")
def download_report():

    # Retrieve the latest saved prediction
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
        ORDER BY id DESC
        LIMIT 1
    """)

    record = cursor.fetchone()
    conn.close()

    if record is None:
        return (
            "Please make a prediction before downloading a report.",
            404
        )

    # Create a PDF in memory
    pdf_buffer = BytesIO()
    pdf = canvas.Canvas(pdf_buffer, pagesize=A4)

    page_width, page_height = A4
    left = 2 * cm
    y = page_height - 2 * cm

    # Write a line of text and start a new page if needed
    def write_line(text, font="Helvetica", size=11, gap=22):
        nonlocal y

        pdf.setFont(font, size)

        # Wrap long text to fit the page width
        max_chars = 90
        words = str(text).split()
        lines = []
        current_line = ""

        for word in words:
            candidate = (
                current_line + " " + word
                if current_line else word
            )

            if len(candidate) > max_chars:
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

    pdf.setTitle("AI Health Detecting System Report")

    # Report heading
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

    # Prediction details
    write_line(
        "Generated: " + datetime.now().strftime("%d-%m-%Y %H:%M")
    )
    write_line(f"Prediction ID: {record[0]}")
    write_line(f"Selected symptoms: {record[1]}")
    write_line(f"Health status: {record[2]}")
    write_line(f"Risk level: {record[3]}")
    write_line(f"Symptom score: {record[4]} out of 5")
    write_line(f"Saved at: {record[5]}")

    # General precautions
    y -= 8

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
        "Seek emergency help for severe breathing difficulty or serious chest pain."
    ]

    for item in precautions:
        write_line("- " + item, size=10, gap=19)

    # General diet recommendations
    y -= 8

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

    # Medical disclaimer
    y -= 8

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

    # Finish the PDF
    pdf.save()
    pdf_buffer.seek(0)

    # Send the PDF to the browser
    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name="health_prediction_report.pdf",
        mimetype="application/pdf"
    )


# ==========================================
# 9. RUN THE APPLICATION
# ==========================================

if __name__ == "__main__":
    init_database()
    app.run(debug=True)
