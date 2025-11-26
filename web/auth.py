from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from . import db
from .models import User

auth = Blueprint('auth', __name__)

@auth.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        password2 = request.form.get("password2")

        if not username or not email or not password or not password2:
            flash("Please fill out all fields.", "error")
        elif password != password2:
            flash("Passwords must match.", "error")
        else:
            user_exists = User.query.filter(
                (User.username == username) | (User.email == email)
            ).first()
            if user_exists:
                flash("Username or email already exists.", "error")
            else:
                new_user = User(username=username, email=email)
                new_user.set_password(password)
                db.session.add(new_user)
                db.session.commit()
                flash("Registration successful. Please log in.", "success")
                return redirect(url_for('auth.login'))

    return render_template("register.html")

@auth.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash("Invalid email or password.", "error")
            return redirect(url_for("auth.login"))
        
        login_user(user)
        flash("Logged in successfully.", "success")
        return redirect(url_for("main.dashboard"))

    return render_template("login.html")

@auth.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have logged out.", "success")
    return redirect(url_for("auth.login"))
