from flask import Blueprint, render_template, session, request, redirect, url_for
from models.db import get_db

client_bp = Blueprint("client", __name__, url_prefix="/client")

@client_bp.route("/user-panel")
def user_panel():
    return render_template("user.html")

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
        return redirect(url_for("client.user_panel"))
    else:
        return redirect(url_for("auth.entry_point"))

@client_bp.route("/guest-entry")
def guest_entry():
    session["role"] = "guest"
    return redirect(url_for("client.create_request_form"))

@client_bp.route("/registration")
def registration():
    session["role"] = "user"
    return render_template("registration.html", role="user")
