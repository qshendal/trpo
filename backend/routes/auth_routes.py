from flask import Blueprint, render_template, request, redirect, url_for, session
from models.db import get_db

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
    return redirect(url_for("client.user_panel"))

@auth_bp.route("/login", methods=["POST"])
def login():
    name = request.form["name"]
    password = request.form["password"]

    if name == "admin_techservice" and password == "123456":
        session["role"] = "admin"
        return redirect(url_for("admin.dashboard"))

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE name = ? AND password = ?", (name, password))
    user = cur.fetchone()
    conn.close()

    if user:
        session["role"] = "user"
        session["user_id"] = user["id"]
        return redirect(url_for("client.user_panel"))
    else:
        return render_template("enter.html", login_error="Неверный логин или пароль")
