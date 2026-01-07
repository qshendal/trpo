from flask import Blueprint, render_template, request, redirect, url_for, session
from models.db import get_db
from werkzeug.security import generate_password_hash, check_password_hash

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/")
def entry_point():
    return render_template("enter.html")

@auth_bp.route("/register", methods=["POST"])
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
        hashed_password = generate_password_hash(password)
        cur.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)", (name, email, hashed_password))
        conn.commit()
        user_id = cur.lastrowid
    except Exception as e:
        conn.rollback()
        return render_template("enter.html", reg_error=f"Ошибка при регистрации: {e}")
    finally:
        conn.close()

    session["role"] = "user"
    session["user_name"] = name
    session["user_id"] = user_id
    return redirect(url_for("client.user_panel"))

@auth_bp.route("/login", methods=["POST"])
def login():
    name = request.form["name"]
    password = request.form["password"]

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE name = ?", (name,))
    user = cur.fetchone()
    conn.close()

    if not user:
        return render_template("enter.html", login_error="Неверный логин или пароль")

    stored_password = user["password"] or ""

    is_hashed = ":" in stored_password

    valid = False
    if is_hashed:
        valid = check_password_hash(stored_password, password)
    else:
        valid = (stored_password == password)

    if not valid:
        return render_template("enter.html", login_error="Неверный логин или пароль")

    session["user_id"] = user["id"]
    session["user_name"] = user["name"]

    # Админа не трогаем — как было
    if user["name"].strip() == "admin_techservice" and user["password"].strip() == "123456":
        session["role"] = "admin"
        return redirect(url_for("admin.dashboard"))
    else:
        session["role"] = "user"
        return redirect(url_for("client.user_panel"))

