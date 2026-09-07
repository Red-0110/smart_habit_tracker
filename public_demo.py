"""Opt-in visitor sandbox. Uses the app's configured database, never a shared login."""
from datetime import datetime, timedelta, timezone
import secrets
import uuid
import click
from flask import Blueprint, abort, current_app, redirect, render_template, request, session, url_for
from flask_login import current_user, login_user, logout_user

KIND = 'habits'
if KIND == 'habits':
    from web import db
    from web.models import User, HabitCategory, Habit, HabitLog
else:
    from app.extensions import db
    from app.models import User, Activity, Session


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class DemoVisitor(db.Model):
    __tablename__ = 'demo_visitors'
    id = db.Column(db.String(32), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)


bp = Blueprint('public_demo', __name__)


def visitor():
    value = session.get('demo_visitor')
    return db.session.get(DemoVisitor, value) if value else None


def remove_visitor(row):
    user = db.session.get(User, row.user_id)
    db.session.delete(row)
    db.session.flush()
    if user:
        db.session.delete(user)
        db.session.flush()


def cleanup(limit=None):
    query = DemoVisitor.query.filter(DemoVisitor.expires_at <= now()).order_by(DemoVisitor.expires_at)
    rows = query.limit(limit).all() if limit else query.all()
    for row in rows:
        remove_visitor(row)
    db.session.commit()
    return len(rows)


def create_visitor():
    key = uuid.uuid4().hex
    created = now()
    user = User(email=f'visitor-{key}@example.invalid')
    if KIND == 'habits':
        user.username = f'Visitor-{key}'
        user.weekly_goal = 15
    # No shared password can authenticate into another visitor's sandbox.
    user.set_password(secrets.token_urlsafe(32))
    db.session.add(user)
    db.session.flush()
    if KIND == 'habits':
        for index, (category_name, name) in enumerate([
            ('Learning', 'Read 20 minutes'), ('Health', 'Morning walk'),
            ('Career', 'Practice Python'), ('Wellbeing', 'Evening journal')]):
            category = HabitCategory(name=category_name, user_id=user.id)
            db.session.add(category)
            db.session.flush()
            habit = Habit(name=name, description='Fictional example habit', user_id=user.id,
                          category_id=category.id, created_at=created-timedelta(days=42))
            db.session.add(habit)
            db.session.flush()
            for offset in range(42):
                day = datetime.combine(created.date()-timedelta(days=offset), datetime.min.time())
                db.session.add(HabitLog(user_id=user.id, habit_id=habit.id,
                    timestamp=day+timedelta(hours=8+index), completed=(offset+index)%5 != 0))
    else:
        activities = []
        for name, category in [('Tennis','Sport'), ('Strength','Gym'), ('Walking','Recovery')]:
            activity = Activity(name=name, category=category, user_id=user.id)
            db.session.add(activity)
            db.session.flush()
            activities.append(activity)
        for offset in range(56):
            if offset % 7 in (2,5):
                continue
            activity = activities[offset%3]
            db.session.add(Session(user_id=user.id, activity_id=activity.id,
                session_date=created.date()-timedelta(days=offset), duration_min=25+(offset%5)*10,
                rpe=2 if activity.name=='Walking' else 4+offset%4,
                notes=['Easy technique practice','Steady effort; felt recovered','Short focused session'][offset%3]))
    row = DemoVisitor(id=key, user_id=user.id, created_at=created,
                      expires_at=created+timedelta(seconds=current_app.config['DEMO_TTL_SECONDS']))
    db.session.add(row)
    db.session.commit()
    session.clear()
    login_user(user)
    session['demo_visitor'] = key
    return row


@bp.get('/demo')
def landing():
    row = visitor()
    return render_template('demo/landing.html', active=bool(row and row.expires_at > now()),
                           title='Smart Habit Tracker' if KIND=='habits' else 'SessionIQ')


@bp.post('/demo/start')
def start():
    row = visitor()
    if row and row.expires_at > now() and current_user.is_authenticated and current_user.id == row.user_id:
        return redirect(url_for('main.dashboard'))
    cleanup(limit=20)
    if DemoVisitor.query.count() >= current_app.config['DEMO_MAX_VISITORS']:
        return render_template('demo/busy.html'), 503
    create_visitor()
    return redirect(url_for('main.dashboard'))


@bp.post('/demo/reset')
def reset():
    row = visitor()
    if not row or row.expires_at <= now() or not current_user.is_authenticated or current_user.id != row.user_id:
        abort(403)
    if (now()-row.created_at).total_seconds() < current_app.config['DEMO_RESET_COOLDOWN_SECONDS']:
        return render_template('demo/busy.html', cooldown=True), 429
    # One transaction replaces only this visitor's records; rollback preserves the old demo on failure.
    remove_visitor(row)
    create_visitor()
    return redirect(url_for('main.dashboard'))


@bp.post('/demo/end')
def end():
    row = visitor()
    if row and current_user.is_authenticated and current_user.id == row.user_id:
        remove_visitor(row)
        db.session.commit()
    logout_user()
    session.clear()
    return redirect(url_for('public_demo.landing'))


def init_public_demo(app):
    if not app.config.get('PUBLIC_DEMO'):
        return
    app.config.setdefault('DEMO_TTL_SECONDS', 7200)
    app.config.setdefault('DEMO_MAX_VISITORS', 500)
    app.config.setdefault('DEMO_RESET_COOLDOWN_SECONDS', 10)
    app.register_blueprint(bp)

    @app.before_request
    def require_visitor():
        if request.endpoint == 'static' or (request.endpoint or '').startswith('public_demo.'):
            return None
        # Public demos cannot register, log in to real accounts, or change account credentials.
        if (request.endpoint or '').startswith('auth.') or request.endpoint in ('main.settings','main.delete_account'):
            abort(404)
        row = visitor()
        if not row or row.expires_at <= now() or not current_user.is_authenticated or current_user.id != row.user_id:
            logout_user()
            session.clear()
            return redirect(url_for('public_demo.landing'))

    @app.after_request
    def private_responses(response):
        if request.endpoint != 'static':
            response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Robots-Tag'] = 'noindex, nofollow'
        return response

    @app.cli.command('demo-init')
    def initialize():
        """Initialize a NEW, EMPTY demo database; never migrate an existing database."""
        from sqlalchemy import inspect
        if inspect(db.engine).get_table_names():
            raise click.ClickException('Database is not empty. Use a separate empty database for this demo.')
        db.create_all()
        click.echo('Created empty visitor-demo schema. Visitors are seeded on entry.')

    @app.cli.command('demo-cleanup')
    def clean():
        """Remove expired visitor accounts and their dependent data."""
        click.echo(f'Removed {cleanup()} expired visitor sandboxes.')
