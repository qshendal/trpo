from flask import Flask, request, render_template
import sqlite3
import os

app = Flask(__name__)

def get_db():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, "tech_service.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/")
def form():
    return render_template("TO.html")

@app.route("/create-request", methods=["POST"])
def create_request():
    form = request.form
    conn = get_db()
    cur = conn.cursor()

    # Вставка клиента
    cur.execute("""
        INSERT INTO client (название_организации, контактное_лицо, телефон, email, адрес)
        VALUES (?, ?, ?, ?, ?)
    """, (
        form["company"],
        form["contact"],
        form["phone"],
        form["email"],
        form["address"]
    ))
    client_id = cur.lastrowid

    # Вставка оборудования
    cur.execute("""
        INSERT INTO equipment (client_id, название, дата_установки, место_установки, текущий_статус)
        VALUES (?, ?, ?, ?, ?)
    """, (
        client_id,
        form["equipment"],
        form["install_date"],
        form["location"],
        form["equipment_status"]
    ))
    equipment_id = cur.lastrowid

    # Вставка заявки
    cur.execute("""
        INSERT INTO service_request (equipment_id, дата_заявки, описание_проблемы, статус)
        VALUES (?, DATE('now'), ?, ?)
    """, (
        equipment_id,
        form["problem"],
        "новая"
    ))

    conn.commit()
    conn.close()
    return "", 204  # Можно заменить на redirect или сообщение

if __name__ == "__main__":
    app.run(debug=True)
