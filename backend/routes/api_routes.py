from flask import Blueprint, jsonify, request, session
from models.db import get_db
import sqlite3
import csv, os, datetime
from security import decrypt_field, encrypt_field

EXPENSES_FILE = "expenses.csv"

api_bp = Blueprint("api", __name__, url_prefix="/api")

@api_bp.route("/my-requests")
def api_my_requests():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify([])

    conn = get_db()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT sr.id,
               sr.дата_заявки,
               sr.описание_проблемы,
               sr.статус,
               eq.название AS оборудование,
               t.фио AS исполнитель
        FROM service_request sr
        JOIN equipment eq ON eq.client_id = sr.client_id
        LEFT JOIN technician t ON t.id = sr.technician_id
        WHERE sr.users_id = ?
        ORDER BY sr.дата_заявки DESC
    """, (user_id,))
    rows = cur.fetchall()
    conn.close()

    tasks = []
    for row in rows:
        tasks.append({
            "id": row["id"],  # <--- добавляем id заявки!
            "name": row["оборудование"],
            "type": row["статус"],
            "deadline": row["дата_заявки"],
            "description": row["описание_проблемы"],
            "executor": row["исполнитель"] if row["исполнитель"] else None
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

        # 🔓 расшифровываем данные клиента
        contact = decrypt_field(row["контактное_лицо"])
        phone   = decrypt_field(row["телефон"])
        email   = decrypt_field(row["email"])
        address = decrypt_field(row["адрес"])

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
            "contact": contact,   # ← расшифрованное значение
            "phone": phone,       # ← расшифрованное значение
            "email": email,       # ← расшифрованное значение
            "address": address,   # ← расшифрованное значение
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

# Маршрут API для перевода заявки в статус "в работе"
@api_bp.route("/activate-request/<int:request_id>", methods=["POST"])
def activate_request(request_id):
    # Подключаемся к базе данных
    conn = get_db()
    cur = conn.cursor()

    # Обновляем статус заявки по её ID
    cur.execute(
        "UPDATE service_request SET статус = 'в работе' WHERE id = ?",
        (request_id,)
    )

    # Сохраняем изменения
    conn.commit()
    # Закрываем соединение
    conn.close()

    # Возвращаем пустой ответ с кодом 204 (успешно, без содержимого)
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

@api_bp.route("/technician-count")
def technician_count():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM technician")
        count = cur.fetchone()[0]
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
    def fetch_tasks(statuses):
        tasks = []
        with get_db() as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            # если statuses — список, используем IN
            if isinstance(statuses, (list, tuple)):
                placeholders = ",".join("?" for _ in statuses)
                cur.execute(f"""
                    SELECT sr.id,
                           sr.дата_заявки,
                           sr.описание_проблемы,
                           sr.приоритет,
                           sr.users_id,
                           sr.статус,
                           t.фио AS исполнитель,
                           eq.название AS оборудование
                    FROM service_request sr
                    LEFT JOIN equipment eq ON eq.client_id = sr.client_id
                    LEFT JOIN technician t ON t.id = sr.technician_id
                    WHERE sr.статус IN ({placeholders})
                    ORDER BY sr.дата_заявки DESC
                """, statuses)
            else:
                cur.execute("""
                    SELECT sr.id,
                           sr.дата_заявки,
                           sr.описание_проблемы,
                           sr.приоритет,
                           sr.users_id,
                           sr.статус,
                           t.фио AS исполнитель,
                           eq.название AS оборудование
                    FROM service_request sr
                    LEFT JOIN equipment eq ON eq.client_id = sr.client_id
                    LEFT JOIN technician t ON t.id = sr.technician_id
                    WHERE sr.статус = ?
                    ORDER BY sr.дата_заявки DESC
                """, (statuses,))
            rows = cur.fetchall()

            for row in rows:
                priority = row["приоритет"] or ""
                priority_map = {"высокий": "Высокий", "средний": "Средний", "низкий": "Низкий"}
                priority_text = priority_map.get(priority.lower(), "Не задан")

                cur2 = conn.cursor()
                cur2.execute("""
                    SELECT p.название, up.количество
                    FROM used_parts up
                    JOIN part p ON p.id = up.part_id
                    WHERE up.service_request_id = ?
                    LIMIT 1
                """, (row["id"],))
                part_row = cur2.fetchone()
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
                    "assignedPart": assigned_part,
                    "users_id": row["users_id"],
                    "type": row["статус"],
                    "description": row["описание_проблемы"]  # <--- ВОТ ЭТУ СТРОКУ НУЖНО ДОБАВИТЬ!
                })
        return tasks

    result = {
        "active": fetch_tasks("в работе"),
        "awaiting_payment": fetch_tasks(["в ожидании оплаты", "оплачено"]),
        "completed": fetch_tasks("завершена")
    }

    return jsonify(result)


# Маршрут API для добавления новой детали в базу данных
@api_bp.route("/add-part", methods=["POST"])
def api_add_part():
    # Получаем данные из запроса в формате JSON
    data = request.get_json()

    # Подключаемся к базе данных
    conn = get_db()
    cur = conn.cursor()

    # SQL-запрос: вставляем новую запись в таблицу part
    cur.execute("""
        INSERT INTO part (название, артикул, цена, количество, порог)
        VALUES (?, ?, ?, ?, ?)
    """, (
        # Берём значения из JSON, если поле пустое — подставляем 0
        data.get("название"),              # название детали
        data.get("артикул"),               # артикул (уникальный код)
        float(data.get("цена") or 0),      # цена (преобразуем в число с плавающей точкой)
        int(data.get("количество") or 0),  # количество (целое число)
        int(data.get("порог") or 0)        # пороговое значение (например, минимальный остаток)
    ))

    # Сохраняем изменения в базе
    conn.commit()
    # Закрываем соединение
    conn.close()

    # Возвращаем ответ в формате JSON, что операция прошла успешно
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
    conn.row_factory = sqlite3.Row # Это позволит обращаться к полям по именам
    cur = conn.cursor()
    
    # Выбираем мастеров и сразу считаем количество их активных заявок
    cur.execute("""
        SELECT 
            t.id,
            t.фио AS name,
            t.специализация AS specialty,
            t.телефон AS phone,
            t.примечание AS comment,
            (SELECT COUNT(*) FROM service_request sr 
             WHERE sr.technician_id = t.id AND sr.статус = 'в работе') AS active_tasks_count
        FROM technician t
    """)
    rows = cur.fetchall()
    conn.close()
    # Превращаем в список словарей для JSON
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
    

import datetime

@api_bp.route("/unassign-master/<int:request_id>", methods=["POST"])
def unassign_master(request_id):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE service_request SET technician_id = NULL WHERE id = ?", (request_id,))
        # пишем в work_log
        cur.execute("""
            INSERT INTO work_log (service_request_id, дата, описание, исполнитель)
            VALUES (?, ?, ?, ?)
        """, (request_id, datetime.date.today().isoformat(), "Мастер отвязан", None))
        conn.commit()
        return jsonify({"success": True})
    finally:
        conn.close()


@api_bp.route("/unassign-part/<int:request_id>", methods=["POST"])
def unassign_part(request_id):
    conn = get_db()
    cur = conn.cursor()
    try:
        # находим привязанную деталь
        cur.execute("SELECT part_id, количество FROM used_parts WHERE service_request_id = ?", (request_id,))
        row = cur.fetchone()

        if row:
            part_id, qty = row
            # возвращаем количество на склад
            cur.execute("UPDATE part SET количество = количество + ? WHERE id = ?", (qty, part_id))

            # удаляем привязку
            cur.execute("DELETE FROM used_parts WHERE service_request_id = ?", (request_id,))

            # логируем
            cur.execute("""
                INSERT INTO work_log (service_request_id, дата, описание, исполнитель)
                VALUES (?, ?, ?, ?)
            """, (
                request_id,
                datetime.date.today().isoformat(),
                f"Деталь отвязана (вернули {qty} шт.)",
                None
            ))

        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()



@api_bp.route("/complete-task/<int:request_id>", methods=["POST"])
def complete_task(request_id):
    conn = get_db()
    cur = conn.cursor()
    try:
        # переводим заявку в статус "в ожидании оплаты"
        cur.execute("UPDATE service_request SET статус = 'в ожидании оплаты' WHERE id = ?", (request_id,))
        # пишем в work_log
        cur.execute("""
            INSERT INTO work_log (service_request_id, дата, описание, исполнитель)
            VALUES (?, ?, ?, ?)
        """, (request_id, datetime.date.today().isoformat(), "Работа завершена (ожидание оплаты)", None))
        conn.commit()

        # возвращаем обновлённую заявку
        cur.execute("SELECT id, статус FROM service_request WHERE id = ?", (request_id,))
        row = cur.fetchone()
        return jsonify(dict(row)), 200
    finally:
        conn.close()


@api_bp.route("/assign-part/<int:request_id>", methods=["POST"])
def assign_part(request_id):
    data = request.get_json(silent=True) or {}
    part_id = data.get("part_id")
    qty = int(data.get("qty", 1))

    assigned_part = None
    with get_db() as conn:
        cur = conn.cursor()
        try:
            # проверяем остаток на складе
            cur.execute("SELECT количество FROM part WHERE id = ?", (part_id,))
            row = cur.fetchone()
            if not row:
                return jsonify({"error": "Деталь не найдена"}), 404
            available_qty = row[0]

            if available_qty < qty:
                return jsonify({"error": "Недостаточно деталей на складе"}), 400

            # очищаем старые записи для этой заявки
            cur.execute("DELETE FROM used_parts WHERE service_request_id = ?", (request_id,))

            # уменьшаем количество на складе
            cur.execute("UPDATE part SET количество = количество - ? WHERE id = ?", (qty, part_id))

            # добавляем новую деталь в used_parts
            cur.execute("""
                INSERT INTO used_parts (service_request_id, part_id, количество)
                VALUES (?, ?, ?)
            """, (request_id, part_id, qty))

            # логируем действие
            cur.execute("SELECT название FROM part WHERE id = ?", (part_id,))
            part_name = cur.fetchone()[0] if part_id else "Неизвестная деталь"
            cur.execute("""
                INSERT INTO work_log (service_request_id, дата, описание, исполнитель)
                VALUES (?, ?, ?, ?)
            """, (
                request_id,
                datetime.date.today().isoformat(),
                f"Назначена деталь: {part_name} ({qty} шт.)",
                None
            ))

            conn.commit()

            # выбираем назначенную деталь для ответа
            cur.execute("""
                SELECT up.id, p.название AS name, p.артикул AS type, p.цена AS price, up.количество AS qty
                FROM used_parts up
                JOIN part p ON up.part_id = p.id
                WHERE up.service_request_id = ?
            """, (request_id,))
            row = cur.fetchone()
            if row:
                assigned_part = dict(row)

        except Exception as e:
            conn.rollback()
            return jsonify({"error": str(e)}), 500

    return jsonify({"assignedPart": assigned_part})



# Маршрут API для назначения мастера на заявку
@api_bp.route("/assign-masters/<int:request_id>", methods=["POST"])
def assign_master(request_id):
    # Получаем данные из запроса в формате JSON
    data = request.get_json(silent=True) or {}
    masters = data.get("masters", [])
    # Берём первого мастера из списка, если он есть
    technician_id = masters[0] if masters else None

    assigned = []  # список назначенных мастеров (для ответа)
    # Работаем с базой данных через контекстный менеджер
    with get_db() as conn:
        cur = conn.cursor()

        # Обновляем заявку: назначаем мастера по ID
        cur.execute(
            "UPDATE service_request SET technician_id = ? WHERE id = ?",
            (technician_id, request_id)
        )

        # Если мастер назначен
        if technician_id is not None:
            # Получаем данные о мастере из таблицы technician
            cur.execute("""
                SELECT id, фио AS name, специализация AS specialty, телефон AS phone
                FROM technician
                WHERE id = ?
            """, (technician_id,))
            row = cur.fetchone()

            if row:
                # Преобразуем строку в словарь и добавляем в список назначенных
                assigned = [dict(row)]

                # Логируем событие: мастер назначен
                cur.execute("""
                    INSERT INTO work_log (service_request_id, дата, описание, исполнитель)
                    VALUES (?, ?, ?, ?)
                """, (
                    request_id,
                    datetime.date.today().isoformat(),  # текущая дата
                    "Назначен мастер",                   # описание события
                    row["name"]                          # имя исполнителя
                ))
        else:
            # Если мастер отвязан (technician_id = None), логируем это
            cur.execute("""
                INSERT INTO work_log (service_request_id, дата, описание, исполнитель)
                VALUES (?, ?, ?, ?)
            """, (
                request_id,
                datetime.date.today().isoformat(),
                "Мастер отвязан",
                None
            ))

        # Сохраняем изменения
        conn.commit()

    # Возвращаем JSON с назначенными мастерами
    return jsonify({"assignedMasters": assigned})



@api_bp.route("/request-cost/<int:request_id>")
def request_cost(request_id):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT SUM(up.количество * p.цена) AS total
            FROM used_parts up
            JOIN part p ON p.id = up.part_id
            WHERE up.service_request_id = ?
        """, (request_id,))
        row = cur.fetchone()
        total = row["total"] if row and row["total"] is not None else 0

    return jsonify({"total": total})

@api_bp.route("/pay-request/<int:request_id>", methods=["POST"])
def pay_request(request_id):
    data = request.get_json(silent=True) or {}
    card_number = data.get("cardNumber")
    card_expiry = data.get("cardExpiry")
    card_cvc = data.get("cardCVC")

    # базовая проверка
    if not card_number or not card_expiry or not card_cvc:
        return jsonify({"success": False, "error": "Некорректные данные карты"}), 400

    # можно добавить простую валидацию
    import re
    if not re.fullmatch(r"\d{16}", card_number):
        return jsonify({"success": False, "error": "Номер карты должен содержать 16 цифр"}), 400
    if not re.fullmatch(r"(0[1-9]|1[0-2])/\d{2}", card_expiry):
        return jsonify({"success": False, "error": "Срок действия должен быть в формате MM/YY"}), 400
    if not re.fullmatch(r"\d{3}", card_cvc):
        return jsonify({"success": False, "error": "CVC должен содержать 3 цифры"}), 400

    # обновляем статус заявки
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE service_request
            SET статус = 'оплачено'
            WHERE id = ?
        """, (request_id,))
        conn.commit()

    return jsonify({"success": True})

from security import decrypt_field   # подключаем модуль

@api_bp.route("/finalize-task/<int:request_id>", methods=["POST"])
def finalize_task(request_id):
    conn = get_db()
    cur = conn.cursor()

    # обновляем статус заявки
    cur.execute("UPDATE service_request SET статус = 'завершена' WHERE id = ?", (request_id,))

    # считаем стоимость, детали, клиента, контакт и мастера
    cur.execute("""
        SELECT 
            SUM(up.количество * p.цена) AS total_cost,
            GROUP_CONCAT(p.название, ', ') AS parts_list,
            cl.название_организации,
            cl.контактное_лицо,
            t.фио
        FROM service_request sr
        JOIN client cl ON cl.id = sr.client_id
        JOIN technician t ON t.id = sr.technician_id
        LEFT JOIN used_parts up ON up.service_request_id = sr.id
        LEFT JOIN part p ON p.id = up.part_id
        WHERE sr.id = ?
    """, (request_id,))
    row = cur.fetchone()

    total_cost = row[0] or 0
    parts_list = row[1] or "Нет деталей"
    client_name = row[2] or "Неизвестный клиент"

    # 🔓 расшифровываем контактное лицо
    contact_person = decrypt_field(row[3]) if row[3] else "Неизвестный контакт"

    technician_name = row[4] or "Неизвестный мастер"

    # пишем в CSV
    append_expense(request_id, total_cost, client_name, contact_person, parts_list, technician_name)

    # пишем в work_log
    cur.execute("""
        INSERT INTO work_log (service_request_id, дата, описание, исполнитель)
        VALUES (?, ?, ?, ?)
    """, (
        request_id,
        datetime.date.today().isoformat(),
        "Заявка завершена",
        technician_name
    ))

    conn.commit()
    conn.close()

    return "", 204



def append_expense(request_id, amount, client_name, contact_person, parts_list, technician_name):
    file_exists = os.path.isfile(EXPENSES_FILE)
    with open(EXPENSES_FILE, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow([
                "request_id",
                "client",
                "contact_person",
                "parts",
                "amount",
                "technician",
                "date"
            ])
        writer.writerow([
            request_id,
            client_name,
            contact_person,
            parts_list,
            amount,
            technician_name,
            datetime.date.today().isoformat()
        ])


@api_bp.route("/monthly-expenses")
def monthly_expenses():
    import csv, datetime, os
    total = 0
    now = datetime.date.today()
    current_month = now.month
    current_year = now.year

    if not os.path.exists(EXPENSES_FILE):
        return jsonify({"total": 0})

    with open(EXPENSES_FILE, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row = {k.strip("\ufeff"): v for k, v in row.items()}
            try:
                try:
                    date_obj = datetime.date.fromisoformat(row["date"])
                except ValueError:
                    date_obj = datetime.datetime.strptime(row["date"], "%m/%d/%Y").date()

                if date_obj.month == current_month and date_obj.year == current_year:
                    amount = float(row["amount"].replace(" ", "").replace(",", "."))
                    total += amount
            except Exception:
                continue

    return jsonify({"total": total})

@api_bp.route("/expenses-by-day")
def expenses_by_day():
    import csv, datetime, os
    from flask import request, jsonify

    start_str = request.args.get("start")
    end_str = request.args.get("end")

    try:
        start_date = datetime.datetime.strptime(start_str, "%Y-%m-%d").date()
        end_date = datetime.datetime.strptime(end_str, "%Y-%m-%d").date()
    except Exception:
        return jsonify({"error": "Неверный формат даты"}), 400

    daily_totals = {}

    if not os.path.exists(EXPENSES_FILE):
        return jsonify([])

    with open(EXPENSES_FILE, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row = {k.strip("\ufeff"): v for k, v in row.items()}
            try:
                try:
                    date_obj = datetime.datetime.strptime(row["date"], "%m/%d/%Y").date()
                except ValueError:
                    date_obj = datetime.date.fromisoformat(row["date"])

                if start_date <= date_obj <= end_date:
                    amount = float(row["amount"].replace(" ", "").replace(",", "."))
                    key = date_obj.isoformat()
                    daily_totals[key] = daily_totals.get(key, 0) + amount
            except Exception:
                continue


    sorted_report = [{"date": d, "amount": daily_totals[d]} for d in sorted(daily_totals)]
    return jsonify(sorted_report)

@api_bp.route("/maintenance-report")
def maintenance_report():
    import csv, datetime, os
    from flask import request, jsonify

 
    start_str = request.args.get("start")
    end_str = request.args.get("end")

    try:
        start_date = datetime.datetime.strptime(start_str, "%Y-%m-%d").date()
        end_date = datetime.datetime.strptime(end_str, "%Y-%m-%d").date()
    except Exception:
     
        return jsonify({"error": "Неверный формат даты"}), 400

    records = []

    if not os.path.exists(EXPENSES_FILE):
        return jsonify([])
    with open(EXPENSES_FILE, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:

            row = {k.strip("\ufeff"): v for k, v in row.items()}
            try:

                try:
                    date_obj = datetime.datetime.strptime(row["date"], "%m/%d/%Y").date()
                except ValueError:
                    date_obj = datetime.date.fromisoformat(row["date"])


                if start_date <= date_obj <= end_date:
                  
                    records.append({
                        "id": row.get("request_id"),     
                        "date": row.get("date"),          
                        "client": row.get("client"),      
                        "contact_person": row.get("contact_person"), 
                        "parts": row.get("parts"),       
                        "amount": row.get("amount"),     
                        "technician": row.get("technician")
                    })
            except Exception:

                continue

    return jsonify(records)



@api_bp.route("/delete-task/<int:request_id>", methods=["DELETE"])
def delete_task(request_id):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM used_parts WHERE service_request_id = ?", (request_id,))

        cur.execute("DELETE FROM service_request WHERE id = ?", (request_id,))

        conn.commit()
        return "", 204
    except Exception as e:
        conn.rollback()
        print("Ошибка при удалении:", e)
        return {"error": str(e)}, 500
    finally:
        conn.close()

@api_bp.route("/work-log/<int:request_id>")
def get_work_log(request_id):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT дата, описание, исполнитель
            FROM work_log
            WHERE service_request_id = ?
            ORDER BY дата ASC, id ASC
        """, (request_id,))
        rows = cur.fetchall()
        logs = [dict(row) for row in rows]
        return jsonify(logs)
    finally:
        conn.close()
