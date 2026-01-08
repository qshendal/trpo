from flask import Blueprint, render_template, session, redirect, url_for

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

@admin_bp.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@admin_bp.route("/reports")
def reports():
    return render_template("reports.html")

@admin_bp.route("/masters")
def masters():
    return render_template("masters.html")

@admin_bp.route("/planning")
def work_planning():
    return render_template("planning.html")

@admin_bp.route('/logout')
def logout():
    session.clear()
    return redirect('/')