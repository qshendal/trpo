from flask import Blueprint, render_template, session, request, redirect, url_for
from models.db import get_db
from security import encrypt_field, decrypt_field
import sqlite3, csv, os, datetime


client_bp = Blueprint("client", __name__, url_prefix="/client")

@client_bp.route("/user-panel")
def user_panel():
    u_name = session.get("user_name")
    return render_template("user.html", user_name=u_name)

@client_bp.route("/my-requests")
def my_requests():
    return render_template("MyRequests.html")

@client_bp.route("/equipment-registry")
def equipment_registry():
    return render_template("equipment.html")

@client_bp.route("/create-request-form")
def create_request_form():
    if "role" not in session:
        session["role"] = "guest"
    return render_template("TO.html")

@client_bp.route("/create-request", methods=["POST"])
def create_request():
    form = request.form
    # Поскольку мы теперь пускаем в форму только через регистрацию, 
    # роль всегда будет "user", а ID всегда будет в сессии.
    role = session.get("role", "guest")
    user_id = session.get("user_id") if role == "user" else None

    # Достаем категорию из скрытого поля (которую мы передали из URL)
    category = form.get("category_from_url", "ОБЩЕЕ")

    conn = get_db()
    cur = conn.cursor()

    try:
        # 🔒 ШИФРОВАНИЕ НЕ ТРОГАЕМ — используем как в оригинале
        cur.execute("""
            INSERT INTO client (название_организации, контактное_лицо, телефон, email, адрес)
            VALUES (?, ?, ?, ?, ?)
        """, (
            form.get("company"),
            encrypt_field(form.get("contact")), 
            encrypt_field(form.get("phone")),
            encrypt_field(form.get("email")),
            encrypt_field(form.get("address"))
        ))
        client_id = cur.lastrowid

        # сохраняем оборудование
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

        # --- РАСПРЕДЕЛЕНИЕ ДАННЫХ ---
        # Склеиваем категорию и проблему, чтобы в админке было видно отдел
        full_problem_description = f"[{category.upper()}] {form.get('problem')}"

        # сохраняем заявку
        cur.execute("""
            INSERT INTO service_request (client_id, users_id, дата_заявки, описание_проблемы, статус, место_ремонта)
            VALUES (?, ?, DATE('now'), ?, ?, ?)
        """, (
            client_id,
            user_id,
            full_problem_description, # Отправляем склеенный текст
            "в ожидании",
            form.get("location")
        ))

        conn.commit()
    except Exception as e:
        conn.rollback()
        return f"Ошибка при вставке: {e}"
    finally:
        conn.close()

    # После успешной заявки отправляем в личный кабинет
    return redirect(url_for("client.user_panel"))

# Измените в Python
@client_bp.route("/guest-entry")
def guest_entry():
    # Получаем категорию из ссылки (если её нет, будет 'general')
    selected_category = request.args.get('category', 'general')
    
    session["role"] = "guest"
    session["selected_category"] = selected_category  # Сохраняем в сессию
    
    return redirect(url_for("client.create_request_form"))

@client_bp.route('/registration')
def registration():
    if request.method == 'POST':
        return redirect(url_for('client.create_request_form'))
    category = request.args.get('category', 'general')
    session['selected_category'] = category  # Сохраняем в "память" браузера
    return render_template('registration.html')