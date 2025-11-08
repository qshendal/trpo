from flask import Flask, request, render_template, redirect, url_for, jsonify, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "your_secret_key"

def get_db():
    db_path = os.path.join(os.path.dirname(__file__), "tech_service.db")
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/")
def entry_point():
    return render_template("enter.html")

@app.route("/register", methods=["POST"])
def register():
    name = request.form["name"]
    email = request.form["email"]
    password = request.form["password"]
    confirm = request.form["confirm"]

    if password != confirm:
        return render_template("enter.html", reg_error="Пароли не совпадают")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE name = ? OR email = ?", (name, email))
    existing = cur.fetchone()
    if existing:
        conn.close()
        return render_template("enter.html", reg_error="Пользователь с таким именем или email уже существует")

    try:
        cur.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)", (name, email, password))
        conn.commit()
        user_id = cur.lastrowid
    except Exception as e:
        conn.rollback()
        return render_template("enter.html", reg_error=f"Ошибка при регистрации: {e}")
    finally:
        conn.close()

    session["role"] = "user"
    session["user_id"] = user_id
    return redirect(url_for("user_panel"))

@app.route("/login", methods=["POST"])
def login():
    name = request.form["name"]
    password = request.form["password"]

    if name == "admin_techservice" and password == "123456":
        session["role"] = "admin"
        return redirect(url_for("dashboard"))

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE name = ? AND password = ?", (name, password))
    user = cur.fetchone()
    conn.close()

    if user:
        session["role"] = "user"
        session["user_id"] = user["id"]
        return redirect(url_for("user_panel"))
    else:
        return render_template("enter.html", login_error="Неверный логин или пароль")

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/user-panel")
def user_panel():
    return render_template("user.html")

@app.route("/my-requests")
def my_requests():
    return render_template("MyRequests.html")

@app.route("/registration")
def registration():
    return render_template("registration.html")

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
    role = session.get("role", "guest")
    return render_template("TO.html", role=role)

@app.route("/create-request", methods=["POST"])
def create_request():
    form = request.form
    user_id = session.get("user_id")
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
            INSERT INTO service_request (client_id, users_id, дата_заявки, описание_проблемы, статус, место_ремонта)
            VALUES (?, ?, DATE('now'), ?, ?, ?)
        """, (
            client_id,
            user_id,
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

    role = session.get("role", "guest")
    if role == "user":
        return redirect(url_for("user_panel"))
    else:
        return redirect(url_for("entry_point"))

@app.route("/api/my-requests")
def api_my_requests():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify([])

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT sr.id, sr.дата_заявки, sr.описание_проблемы, sr.статус,
               eq.название AS оборудование
        FROM service_request sr
        JOIN equipment eq ON eq.client_id = sr.client_id
        WHERE sr.users_id = ?
        ORDER BY sr.дата_заявки DESC
    """, (user_id,))
    rows = cur.fetchall()
    conn.close()

    tasks = []
    for row in rows:
        tasks.append({
            "name": row["оборудование"],
            "type": row["статус"],
            "deadline": row["дата_заявки"],
            "description": row["описание_проблемы"]
        })

    return jsonify(tasks)

@app.route("/api/requests")
def api_requests():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT sr.id, sr.дата_заявки, sr.описание_проблемы, sr.статус,
               eq.название AS оборудование
        FROM service_request sr
        JOIN equipment eq ON eq.client_id = sr.client_id
        ORDER BY sr.дата_заявки DESC
    """)
    rows = cur.fetchall()
    conn.close()

    tasks = []
    for row in rows:
        tasks.append({
            "name": row["оборудование"],
            "type": row["статус"],
            "deadline": row["дата_заявки"],
            "priorityText": "Высокий",
            "priorityClass": "high"
        })

    return jsonify(tasks)

@app.route("/api/active-count")
def api_active_count():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) AS count
        FROM service_request
        WHERE статус IN ('новая', 'в работе')
    """)
    count = cur.fetchone()["count"]
    conn.close()
    return jsonify({"count": count})

if __name__ == "__main__":
    app.run(debug=True)