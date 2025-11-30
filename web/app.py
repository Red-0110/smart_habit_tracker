from web import create_app, db
from flask import render_template, request, redirect, url_for, flash
from web.models import HabitLog, Habit

app = create_app()

@app.route("/")
def dashboard():
    logs = HabitLog.query.order_by(HabitLog.date.desc()).all()
    return render_template("dashboard.html", logs=logs)

@app.route("/log", methods=["POST"])
def log_activity():
    habit_id = request.form.get("habit_id")  
    if habit_id:
        try:
            habit = Habit.query.get(int(habit_id))
            if not habit:
                flash("Habit not found.", "error")
                return redirect(url_for("dashboard"))

            new_log = HabitLog(habit_id=habit.id, completed=True)
            db.session.add(new_log)
            db.session.commit()
            flash("Habit logged successfully!", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error logging habit: {e}", "error")
    else:
        flash("No habit selected.", "warning")

    return redirect(url_for("dashboard"))

@app.route("/login", methods=["GET", "POST"])
def login():
    return "<h1>Login placeholder</h1>"

if __name__ == "__main__":
    print("Flask is starting...")
    app.run(debug=True)
