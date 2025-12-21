from flask import Blueprint, jsonify, request, session
from models.db import get_db
import sqlite3

api_bp = Blueprint("api", __name__, url_prefix="/api")

@api_bp.route("/my-requests")
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

@api_bp.route("/new-requests")
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

@api_bp.route("/active-requests")
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

@api_bp.route("/activate-request/<int:request_id>", methods=["POST"])
def activate_request(request_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE service_request SET статус = 'в работе' WHERE id = ?", (request_id,))
    conn.commit()
    conn.close()
    return "", 204

@api_bp.route("/active-count")
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

@api_bp.route("/set-priority/<int:request_id>", methods=["POST"])
def set_priority(request_id):
    priority = request.json.get("priority")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE service_request SET приоритет = ? WHERE id = ?", (priority, request_id))
    conn.commit()
    conn.close()
    return "", 204

@api_bp.route("/set-location/<int:request_id>", methods=["POST"])
def set_location(request_id):
    location = request.json.get("location")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE service_request SET место_ремонта = ? WHERE id = ?", (location, request_id))
    conn.commit()
    conn.close()
    return "", 204

@api_bp.route("/delete-request/<int:request_id>", methods=["POST"])
def delete_request(request_id):
    reason = request.json.get("reason")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM service_request WHERE id = ?", (request_id,))
    conn.commit()
    conn.close()
    return "", 204

@api_bp.route("/calendar-tasks")
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

    tasks = []
    for row in rows:
        # приоритет
        priority = row["приоритет"] or ""
        priority_map = {"высокий": "Высокий", "средний": "Средний", "низкий": "Низкий"}
        priority_text = priority_map.get(priority.lower(), "Не задан")

        # назначенная деталь (одна на заявку)
        cur.execute("""
            SELECT p.название, up.количество
            FROM used_parts up
            JOIN part p ON p.id = up.part_id
            WHERE up.service_request_id = ?
            LIMIT 1
        """, (row["id"],))
        part_row = cur.fetchone()
        assigned_part = None
        if part_row:
            assigned_part = {
                "name": part_row["название"],
                "qty": part_row["количество"]
            }

        tasks.append({
            "id": row["id"],
            "name": row["оборудование"],
            "deadline": row["дата_заявки"],
            "executor": row["исполнитель"] if row["исполнитель"] else None,
            "priority": priority_text,
            "assignedPart": assigned_part
        })

    conn.close()
    return jsonify(tasks)


@api_bp.route("/add-part", methods=["POST"])
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

@api_bp.route("/parts", methods=["GET"])
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

@api_bp.route("/delete-part/<int:part_id>", methods=["POST"])
def delete_part(part_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM part WHERE id = ?", (part_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@api_bp.route("/update-part/<int:part_id>", methods=["POST"])
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


@api_bp.route("/low-stock")
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

@api_bp.route("/masters", methods=["GET"])
def get_masters():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            id,
            фио AS name,
            специализация AS specialty,
            телефон AS phone,
            примечание AS comment
        FROM technician
    """)
    rows = cur.fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])



@api_bp.route("/add-master", methods=["POST"])
def add_master():
    data = request.get_json()
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO technician (фио, специализация, телефон, примечание)
        VALUES (?, ?, ?, ?)
    """, (data["name"], data["specialty"], data["phone"], data.get("comment", "")))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})


@api_bp.route("/delete-master/<int:master_id>", methods=["POST"])
def delete_master(master_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM technician WHERE id = ?", (master_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "deleted"})

@api_bp.route("/update-master/<int:master_id>", methods=["POST"])
def update_master(master_id):
    data = request.get_json()
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        UPDATE technician
        SET фио = ?, специализация = ?, телефон = ?, примечание = ?
        WHERE id = ?
    """, (data["name"], data["specialty"], data["phone"], data.get("comment", ""), master_id))
    conn.commit()
    conn.close()
    return jsonify({"status": "updated"})

@api_bp.route("/assign-masters/<int:request_id>", methods=["POST"])
def assign_master(request_id):
    data = request.get_json()
    masters = data.get("masters", [])

    technician_id = masters[0] if masters else None

    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE service_request SET technician_id = ? WHERE id = ?", (technician_id, request_id))
    conn.commit()

    cur.execute("""
        SELECT id, фио AS name, специализация AS specialty, телефон AS phone
        FROM technician
        WHERE id = ?
    """, (technician_id,))
    row = cur.fetchone()
    conn.close()

    return jsonify({"assignedMasters": [dict(row)] if row else []})

@api_bp.route("/assign-part/<int:request_id>", methods=["POST"])
def assign_part(request_id):
    data = request.get_json()
    part_id = data.get("part_id")
    qty = data.get("qty", 1)

    conn = get_db()
    cur = conn.cursor()

    cur.execute("DELETE FROM used_parts WHERE service_request_id = ?", (request_id,))

    cur.execute(
        "INSERT INTO used_parts (service_request_id, part_id, количество) VALUES (?, ?, ?)",
        (request_id, part_id, qty)
    )

    conn.commit()

    cur.execute("""
        SELECT up.id, p.название AS name, p.артикул AS type, p.цена AS price, up.количество AS qty
        FROM used_parts up
        JOIN part p ON up.part_id = p.id
        WHERE up.service_request_id = ?
    """, (request_id,))
    row = cur.fetchone()
    conn.close()

    return jsonify({"assignedPart": dict(row) if row else None})


@api_bp.route("/parts_en", methods=["GET"])
def get_parts_en():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM part")
    rows = cur.fetchall()
    conn.close()

    parts = []
    for row in rows:
        parts.append({
            "id": row[0],
            "name": row[1],
            "type": row[2],
            "price": row[3],
            "quantity": row[4],
            "threshold": row[5]
        })

    return jsonify(parts)

@api_bp.route("/unassign-master/<int:request_id>", methods=["POST"])
def unassign_master(request_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE service_request SET technician_id = NULL WHERE id = ?", (request_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@api_bp.route("/unassign-part/<int:request_id>", methods=["POST"])
def unassign_part(request_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM used_parts WHERE service_request_id = ?", (request_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})
