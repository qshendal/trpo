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
    if "role" not in session:
        session["role"] = "guest"
    return render_template("TO.html")

@app.route("/guest-entry")
def guest_entry():
    session["role"] = "guest"
    return redirect(url_for("create_request_form"))

@app.route("/registration")
def registration():
    session["role"] = "user"
    return render_template("registration.html", role="user")

@app.route("/create-request", methods=["POST"])
def create_request():
    form = request.form
    role = session.get("role", "guest")
    user_id = session.get("user_id") if role == "user" else None

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
            "в ожидании",
            form.get("location")
        ))

        conn.commit()
    except Exception as e:
        conn.rollback()
        return f"Ошибка при вставке: {e}"
    finally:
        conn.close()

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

@app.route("/api/new-requests")
def api_new_requests():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT sr.id,
               sr.дата_заявки,
               sr.описание_проблемы,
               sr.статус,
               sr.место_ремонта,
               sr.приоритет,
               eq.название AS оборудование,
               eq.дата_установки,
               eq.место_установки,
               eq.текущий_статус,
               cl.название_организации,
               cl.контактное_лицо,
               cl.телефон,
               cl.email,
               cl.адрес
        FROM service_request sr
        JOIN equipment eq ON eq.client_id = sr.client_id
        JOIN client cl ON cl.id = sr.client_id
        WHERE sr.статус = 'в ожидании'
        ORDER BY sr.дата_заявки DESC
    """)
    rows = cur.fetchall()
    conn.close()

    tasks = []
    for row in rows:
        priority = row["приоритет"] or ""
        priority_map = {
            "высокий": ("Высокий", "high"),
            "средний": ("Средний", "medium"),
            "низкий": ("Низкий", "low")
        }
        priority_text, priority_class = priority_map.get(priority.lower(), ("Не задан", "none"))

        tasks.append({
            "id": row["id"],
            "name": row["оборудование"],
            "type": row["статус"],
            "deadline": row["дата_заявки"],
            "description": row["описание_проблемы"],
            "repair_location": row["место_ремонта"],
            "priority": priority,
            "equipment": row["оборудование"],
            "install_date": row["дата_установки"],
            "location": row["место_установки"],
            "equipment_status": row["текущий_статус"],
            "company": row["название_организации"],
            "contact": row["контактное_лицо"],
            "phone": row["телефон"],
            "email": row["email"],
            "address": row["адрес"],
            "priorityText": priority_text,
            "priorityClass": priority_class
        })

    return jsonify(tasks)

@app.route("/api/active-requests")
def api_active_requests():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT sr.id, sr.дата_заявки, sr.описание_проблемы, sr.статус, sr.приоритет,
               eq.название AS оборудование
        FROM service_request sr
        JOIN equipment eq ON eq.client_id = sr.client_id
        WHERE sr.статус = 'в работе'
        ORDER BY
            CASE LOWER(sr.приоритет)
                WHEN 'высокий' THEN 1
             WHEN 'средний' THEN 2
                WHEN 'низкий' THEN 3
                ELSE 4
            END,
            sr.дата_заявки DESC
    """)
    rows = cur.fetchall()
    conn.close()

    tasks = []
    for row in rows:
        priority = row["приоритет"] or ""
        priority_map = {
            "высокий": ("Высокий", "high"),
            "средний": ("Средний", "medium"),
            "низкий": ("Низкий", "low")
        }
        priority_text, priority_class = priority_map.get(priority.lower(), ("Не задан", "none"))

        tasks.append({
            "name": row["оборудование"],
            "type": row["статус"],
            "deadline": row["дата_заявки"],
            "description": row["описание_проблемы"],
            "priorityText": priority_text,
            "priorityClass": priority_class
        })

    return jsonify(tasks)

@app.route("/api/activate-request/<int:request_id>", methods=["POST"])
def activate_request(request_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE service_request SET статус = 'в работе' WHERE id = ?", (request_id,))
    conn.commit()
    conn.close()
    return "", 204

@app.route("/api/active-count")
def api_active_count():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) AS count
        FROM service_request
        WHERE статус IN ('в работе')
    """)
    count = cur.fetchone()["count"]
    conn.close()
    return jsonify({"count": count})

@app.route("/api/set-priority/<int:request_id>", methods=["POST"])
def set_priority(request_id):
    priority = request.json.get("priority")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE service_request SET приоритет = ? WHERE id = ?", (priority, request_id))
    conn.commit()
    conn.close()
    return "", 204

@app.route("/api/set-location/<int:request_id>", methods=["POST"])
def set_location(request_id):
    location = request.json.get("location")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE service_request SET место_ремонта = ? WHERE id = ?", (location, request_id))
    conn.commit()
    conn.close()
    return "", 204

@app.route("/api/delete-request/<int:request_id>", methods=["POST"])
def delete_request(request_id):
    reason = request.json.get("reason")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM service_request WHERE id = ?", (request_id,))
    conn.commit()
    conn.close()
    return "", 204

@app.route("/api/calendar-tasks")
def api_calendar_tasks():
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT sr.id,
            sr.дата_заявки,
            sr.описание_проблемы,
            sr.приоритет,
            t.фио AS исполнитель,
            eq.название AS оборудование
        FROM service_request sr
        JOIN equipment eq ON eq.client_id = sr.client_id
        LEFT JOIN technician t ON t.id = sr.technician_id
        WHERE sr.статус = 'в работе'
        ORDER BY sr.дата_заявки DESC
    """)
    rows = cur.fetchall()
    conn.close()

    tasks = []
    for row in rows:
        priority = row["приоритет"] or ""
        priority_map = {
            "высокий": "Высокий",
            "средний": "Средний",
            "низкий": "Низкий",
        }
        priority_text = priority_map.get(priority.lower(), "Не задан")

        tasks.append({
            "id": row["id"],
            "name": row["оборудование"],
            "deadline": row["дата_заявки"],
            "executor": row["исполнитель"] if row["исполнитель"] else None,
            "priority": priority_text
        })

    return jsonify(tasks)

@app.route("/api/add-part", methods=["POST"])
def api_add_part():
    data = request.get_json()
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO part (название, артикул, цена, количество, порог)
        VALUES (?, ?, ?, ?, ?)
    """, (
        data.get("название"),
        data.get("артикул"),
        float(data.get("цена") or 0),
        int(data.get("количество") or 0),
        int(data.get("порог") or 0)
    ))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route("/api/parts", methods=["GET"])
def get_parts():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM part")
    rows = cur.fetchall()
    conn.close()

    parts = []
    for row in rows:
        parts.append({
            "id": row[0],
            "название": row[1],
            "артикул": row[2],
            "цена": row[3],
            "количество": row[4],
            "порог": row[5]
        })

    return jsonify(parts)

@app.route("/api/delete-part/<int:part_id>", methods=["POST"])
def delete_part(part_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM part WHERE id = ?", (part_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route("/api/update-part/<int:part_id>", methods=["POST"])
def update_part(part_id):
    data = request.get_json()
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        UPDATE part SET
          название = ?,
          артикул = ?,
          цена = ?,
          количество = ?,
          порог = ?
        WHERE id = ?
    """, (
        data["название"],
        data["артикул"],
        data["цена"],
        data["количество"],
        data["порог"],
        part_id
    ))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})


@app.route("/api/low-stock")
def low_stock():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM part WHERE количество < порог")
    rows = cur.fetchall()
    conn.close()

    parts = []
    for row in rows:
        parts.append({
            "id": row[0],
            "название": row[1],
            "артикул": row[2],
            "цена": row[3],
            "количество": row[4],
            "порог": row[5]
        })

    return jsonify(parts)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)