from flask import Flask, request, render_template, redirect, url_for
import sqlite3
import os

app = Flask(__name__)

# 🔧 Получение подключения к базе
def get_db():
    db_path = os.path.join(os.path.dirname(__file__), "tech_service.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

# 🏠 Главная страница — форма заявки
@app.route("/")
def show_form():
    return render_template("TO.html")

# 💾 Обработка формы и вставка в базу
@app.route("/create-request", methods=["POST"])
def create_request():
    form = request.form
    conn = get_db()
    cur = conn.cursor()

    # 👤 Вставка клиента
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

    # ⚙️ Вставка оборудования
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
    equipment_id = cur.lastrowid

    # 📝 Вставка заявки
    cur.execute("""
        INSERT INTO service_request (equipment_id, дата_заявки, описание_проблемы, статус)
        VALUES (?, DATE('now'), ?, ?)
    """, (
        equipment_id,
        form.get("problem"),
        "новая"
    ))

    conn.commit()
    conn.close()

    # ✅ Можно вернуть сообщение или перенаправить
    return redirect(url_for("show_form"))

# 🚀 Запуск приложения
if __name__ == "__main__":
    app.run(debug=True)
