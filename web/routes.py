from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user, logout_user
from datetime import datetime, timedelta, timezone
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from . import db, csrf
from .models import User, Habit, HabitLog, HabitCategory

main = Blueprint("main", __name__)

def _ts_col():
    """Return the timestamp-like column on HabitLog (`timestamp` or legacy `date`)."""
    col = getattr(HabitLog, "timestamp", getattr(HabitLog, "date", None))
    if col is None:
        raise RuntimeError("HabitLog needs a `timestamp` or `date` column.")
    return col

def _user_filter(query):
    """Filter by current user if the column exists; otherwise return the query unchanged."""
    if hasattr(HabitLog, "user_id"):
        return query.filter(HabitLog.user_id == current_user.id)
    return query

@main.route("/")
@login_required
def home():
    return redirect(url_for("main.dashboard"))

@main.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    ts_col = _ts_col()

    if request.method == "POST":
        habit_id = request.form.get("habit_id")
        completed = request.form.get("completed") == "on"

        if not habit_id:
            flash("Please select a habit.", "danger")
            return redirect(url_for("main.dashboard"))

        new_log = HabitLog(
            habit_id=int(habit_id),
            completed=completed,
            # only set user_id if it exists in your schema
            **({"user_id": current_user.id} if hasattr(HabitLog, "user_id") else {})
        )
        db.session.add(new_log)
        db.session.commit()
        flash("Habit logged!", "success")
        return redirect(url_for("main.dashboard"))

    # --- Data for the page ---
    # Logged entries (called 'habits' in your template)
    base_query = HabitLog.query
    base_query = _user_filter(base_query)
    habits = base_query.order_by(ts_col.desc()).all()

    # If you want the <select> in the form to list actual Habit names,
    # fetch them here. (Template currently loops over 'habits' for both,
    # so this is just available if/when you update the template.)
    user_habits = Habit.query.filter_by(user_id=current_user.id).order_by(Habit.name.asc()).all() if hasattr(Habit, "user_id") else []

    today = datetime.utcnow().date()
    last_seven_days = [(today - timedelta(days=i)) for i in range(6, -1, -1)]

    # Completed count by weekday (for charts)
    completion_data = {}
    for day in last_seven_days:
        q = HabitLog.query
        q = _user_filter(q)
        count = q.filter(
            func.date(ts_col) == day,
            HabitLog.completed.is_(True)
        ).count()
        completion_data[day.strftime("%A")] = count

    # Streaks
    all_completed = HabitLog.query
    all_completed = _user_filter(all_completed)
    all_completed = all_completed.filter(HabitLog.completed.is_(True)).order_by(ts_col.asc()).all()

    longest_streak = 0
    current_streak = 0
    last_day = None
    for log in all_completed:
        ts = getattr(log, "timestamp", None) or getattr(log, "date", None)
        if ts is None:
            continue
        log_day = ts.date()
        if last_day and (log_day - last_day).days == 1:
            current_streak += 1
        else:
            current_streak = 1
        longest_streak = max(longest_streak, current_streak)
        last_day = log_day

    # Totals & percentages
    total_q = _user_filter(HabitLog.query)
    total_habits = total_q.count()
    completed_habits = total_q.filter(HabitLog.completed.is_(True)).count()
    percent_closed = (completed_habits / total_habits * 100) if total_habits else 0

    # Completed today
    completed_today = _user_filter(HabitLog.query).filter(
        func.date(ts_col) == today,
        HabitLog.completed.is_(True)
    ).count()
    show_no_habits_nudge = completed_today == 0

    # Placeholders for removed category feature
    categories = (HabitCategory.query
                  .filter_by(user_id=current_user.id)
                  .order_by(HabitCategory.name.asc())
                  .all())
    
    category_counts = {
        c.id: Habit.query.filter_by(user_id=current_user.id, category_id=c.id).count()
        for c in categories
    }

    # Heatmap (last 60 days)
    last_sixty = [(today - timedelta(days=i)) for i in range(59, -1, -1)]
    heatmap_data = []
    for day in last_sixty:
        c = _user_filter(HabitLog.query).filter(
            func.date(ts_col) == day,
            HabitLog.completed.is_(True)
        ).count()
        heatmap_data.append((day.strftime("%Y-%m-%d"), c))

    # Nudge placeholders expected by template
    shown_count = 0
    closed_count = 0
    time_to_first_nudge = None

    return render_template(
        "dashboard.html",
        habits=habits,                    # logs list (matches your template name)
        categories=categories,            # empty (feature deferred)
        heatmap_data=heatmap_data,
        completion_data=completion_data,
        streak=current_streak,
        longest_streak=longest_streak,
        percent_closed=percent_closed,
        category_counts=category_counts,
        shown_count=shown_count,
        closed_count=closed_count,
        completed_this_week=completed_habits,  # reusing weekly for now
        time_to_first_nudge=time_to_first_nudge,
        labels=[d.strftime("%A") for d in last_seven_days],
        total_completed=completed_habits,
        total_incomplete=max(0, total_habits - completed_habits),
        data=[completion_data[d.strftime("%A")] for d in last_seven_days],
        completed_per_day=[completion_data[d.strftime("%A")] for d in last_seven_days],
        show_no_habits_nudge=show_no_habits_nudge,
        user_habits=user_habits           # available if you later fix the <select>
    )

@main.route("/log", methods=["POST"])
@login_required
def log_habit():
    ts_col = _ts_col()
    habit_id = request.form.get("habit_id")
    completed = request.form.get("completed") == "on"

    if habit_id:
        new_log = HabitLog(
            habit_id=int(habit_id),
            completed=completed,
            **({"user_id": current_user.id} if hasattr(HabitLog, "user_id") else {})
        )
        db.session.add(new_log)
        db.session.commit()
        flash("Habit logged!", "success")
    else:
        flash("Please select a habit.", "danger")

    return redirect(url_for("main.dashboard"))

@main.route("/habits/new", methods=["POST"])
@login_required
def create_habit():
    name = (request.form.get("habit_name") or "").strip()
    description = (request.form.get("description") or "").strip()
    cat_raw = request.form.get("category_id")

    if not name:
        flash("Habit name is required.", "danger")
        return redirect(url_for("main.dashboard"))

    # Optional: prevent duplicate names per user
    if Habit.query.filter_by(user_id=current_user.id, name=name).first():
        flash("You already have a habit with that name.", "warning")
        return redirect(url_for("main.dashboard"))

    habit = Habit(name=name, description=description or None, user_id=current_user.id)

    # Optional category assignment (only if it belongs to the current user)
    if cat_raw and cat_raw.isdigit():
        cat = HabitCategory.query.filter_by(id=int(cat_raw), user_id=current_user.id).first()
        if not cat:
            flash("Invalid category.", "danger")
            return redirect(url_for("main.dashboard"))
        habit.category_id = cat.id

    db.session.add(habit)
    db.session.commit()
    flash(f'Added habit “{name}”.', "success")
    return redirect(url_for("main.dashboard"))

@main.route("/add_category", methods=["POST"])
@login_required
def add_category():
    name = (request.form.get("category_name") or request.form.get("name") or "").strip()
    if not name:
        flash("Category name is required.", "danger")
        return redirect(url_for("main.dashboard"))

    try:
        db.session.add(HabitCategory(name=name, user_id=current_user.id))
        db.session.commit()
        flash(f'Created category “{name}”.', "success")
    except IntegrityError:
        db.session.rollback()
        flash(f'Category “{name}” already exists.', "warning")

    return redirect(url_for("main.dashboard"))

@main.route("/delete_category/<int:category_id>", methods=["POST"])
@login_required
def delete_category(category_id):
    cat = HabitCategory.query.filter_by(id=category_id, user_id=current_user.id).first()
    if not cat:
        flash("Category not found.", "danger")
        return redirect(url_for("main.dashboard"))

    # block deletion if any habit still uses it
    in_use = Habit.query.filter_by(user_id=current_user.id, category_id=cat.id).first()
    if in_use:
        flash("Cannot delete: category is assigned to one or more habits.", "warning")
        return redirect(url_for("main.dashboard"))

    db.session.delete(cat)
    db.session.commit()
    flash("Category deleted.", "success")
    return redirect(url_for("main.dashboard"))
    
@main.route("/complete/<int:habit_id>", methods=["POST"])
@login_required
def complete_habit(habit_id):
    habit = HabitLog.query.get_or_404(habit_id)
    if hasattr(habit, "user_id") and habit.user_id != current_user.id:
        flash("Unauthorized", "danger")
        return redirect(url_for("main.dashboard"))
    habit.completed = True
    db.session.commit()
    flash("Habit marked as completed.", "success")
    return redirect(url_for("main.dashboard"))

@main.route("/logs/<int:log_id>/delete", methods=["POST"], endpoint="delete_log")
@login_required
def delete_log(log_id):
    log = HabitLog.query.filter_by(id=log_id, user_id=current_user.id).first_or_404()
    db.session.delete(log)
    db.session.commit()
    flash("Log entry deleted.", "success")
    return redirect(url_for("main.dashboard"))

@main.route("/habits/<int:habit_id>/delete", methods=["POST"])
@login_required
def delete_habit_entity(habit_id):
    habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first_or_404()
    db.session.delete(habit)  # cascades to logs thanks to relationship config
    db.session.commit()
    flash("Habit deleted.", "success")
    return redirect(url_for("main.dashboard"))

@main.route("/habits/<int:habit_id>/rename", methods=["POST"])
@login_required
def rename_habit(habit_id):
    habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first_or_404()
    new_name = (request.form.get("habit_name") or "").strip()
    if not new_name:
        flash("New name is required.", "danger")
        return redirect(url_for("main.dashboard"))
    if Habit.query.filter_by(user_id=current_user.id, name=new_name).first():
        flash("You already have a habit with that name.", "warning")
        return redirect(url_for("main.dashboard"))
    habit.name = new_name
    db.session.commit()
    flash("Habit renamed.", "success")
    return redirect(url_for("main.dashboard"))

@main.route("/settings", methods=["GET"])
@login_required
def settings():
    # Minimal placeholder to render your settings page
    return render_template("settings.html", user=current_user)

@main.route("/delete_account", methods=["POST"])
@login_required
def delete_account():
    # Defensive: only run filters if those columns exist
    if hasattr(HabitLog, "user_id"):
        HabitLog.query.filter_by(user_id=current_user.id).delete()
    if hasattr(Habit, "user_id"):
        Habit.query.filter_by(user_id=current_user.id).delete()

    user = User.query.get(current_user.id)
    if user:
        db.session.delete(user)
        db.session.commit()

    logout_user()
    flash("Your account has been deleted.", "info")
    return redirect(url_for("auth.login"))

@csrf.exempt
@main.route("/log_nudge_event", methods=["POST"])
@login_required
def log_nudge_event():
    data = request.get_json() or {}
    action = data.get("action")
    print(f"Nudge event: {action} for user {current_user.id}")
    return jsonify({"status": "ok"}), 200

@main.route("/habits/complete-all", methods=["POST"], endpoint="complete_all_habits")
@login_required
def complete_all_habits():
    """Create one completion log for each of the current user's habits today (UTC), avoiding duplicates."""
    habits = Habit.query.filter_by(user_id=current_user.id).all()

    now = datetime.now(timezone.utc)
    start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    end = start + timedelta(days=1)

    created = 0
    for h in habits:
        # only add a log if none exists today for this habit+user
        already = (
            HabitLog.query.filter(
                HabitLog.user_id == current_user.id,
                HabitLog.habit_id == h.id,
                HabitLog.timestamp >= start,
                HabitLog.timestamp < end,
            ).first()
        )
        if not already:
            db.session.add(
                HabitLog(
                    timestamp=now,
                    completed=True,
                    habit_id=h.id,
                    user_id=current_user.id,
                )
            )
            created += 1

    db.session.commit()
    flash(f"Marked {created} habit(s) as completed for today.")
    return redirect(url_for("main.dashboard"))