import sqlite3


DATABASE_NAME = "database/health_history.db"


def create_database():
    conn = sqlite3.connect(DATABASE_NAME)

    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prediction_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symptoms TEXT NOT NULL,
            health_status TEXT NOT NULL,
            risk_level TEXT NOT NULL,
            risk_score INTEGER NOT NULL,
            prediction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def save_prediction(symptoms, health_status, risk_level, risk_score):
    conn = sqlite3.connect(DATABASE_NAME)

    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO prediction_history
        (symptoms, health_status, risk_level, risk_score)
        VALUES (?, ?, ?, ?)
    """, (
        symptoms,
        health_status,
        risk_level,
        risk_score
    ))

    conn.commit()
    conn.close()


def get_prediction_history():
    conn = sqlite3.connect(DATABASE_NAME)

    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, symptoms, health_status, risk_level,
               risk_score, prediction_date
        FROM prediction_history
        ORDER BY id DESC
    """)

    history = cursor.fetchall()

    conn.close()

    return history