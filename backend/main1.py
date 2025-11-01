from flask import Flask, request, render_template, redirect, url_for
import sqlite3
import os

app = Flask(__name__)

def get_db():
    db_path = os.path.join(os.path.dirname(__file__), "tech_service.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/")
def dashboard():
    return render_template("dashboard.html")

@app.route("/registration")
def registration():
    return render_template("registration.html")

@app.route("/register", methods=["POST"])
def register():
    # Здесь логика регистрации: сохранить пользователя, проверить email, хешировать пароль и т.д.
    return redirect(url_for("dashboard"))  # или куда тебе нужно

@app.route("/equipment-registry")
def equipment_registry():
    return render_template("equipment.html")

@app.route("/planning")
def work_planning():
    return render_template("planning.html")

@app.route("/reports")
def reports():
    return render_template("reports.html")

@app.route("/create-request-form")
def create_request_form():
    return render_template("TO.html")

@app.route("/create-request", methods=["POST"])
def create_request():
    form = request.form
    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO client (название_организации, контактное_лицо, телефон, email, адрес)
            VALUES (?, ?, ?, ?, ?)
        """, (
            form.get("company"),
            form.get("contact"),
            form.get("phone"),
            form.get("email"),
            form.get("address")
        ))
        client_id = cur.lastrowid

        cur.execute("""
            INSERT INTO equipment (client_id, название, дата_установки, место_установки, текущий_статус)
            VALUES (?, ?, ?, ?, ?)
        """, (
            client_id,
            form.get("equipment"),
            form.get("install_date"),
            form.get("location"),
            form.get("equipment_status")
        ))

        cur.execute("""
            INSERT INTO service_request (client_id, дата_заявки, описание_проблемы, статус, место_ремонта)
            VALUES (?, DATE('now'), ?, ?, ?)
        """, (
            client_id,
            form.get("problem"),
            "новая",
            form.get("location")
        ))

        conn.commit()
    except Exception as e:
        conn.rollback()
        return f"Ошибка при вставке: {e}"
    finally:
        conn.close()

    return redirect(url_for("dashboard"))

if __name__ == "__main__":
    app.run(debug=True)
