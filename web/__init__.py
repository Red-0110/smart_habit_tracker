# smart_habit_tracker/web/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf import CSRFProtect
from flask_wtf.csrf import generate_csrf
import os

# ---- Extensions (module-level singletons) ----
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
csrf = CSRFProtect()  # NEW

def create_app(config=None):
    app = Flask(__name__)

    # ---- Config ----
    basedir = os.path.abspath(os.path.dirname(__file__))            # .../smart_habit_tracker/web
    db_path = os.path.abspath(os.path.join(basedir, "..", "instance", "habits.db"))
    os.makedirs(os.path.dirname(db_path), exist_ok=True)            # ensure instance dir exists

    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"  # absolute file path
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.secret_key = os.environ.get("SECRET_KEY", "dev")

    if config:
        app.config.update(config)

    # ---- Init extensions ----
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db, directory=os.path.join(basedir, "..", "migrations"))

    # ---- CSRF wiring (must be inside create_app) ----
    csrf.init_app(app)

    @app.context_processor
    def inject_csrf_token():
        # makes csrf_token() available in Jinja templates
        return dict(csrf_token=generate_csrf)

    # ---- Import models AFTER init_app to avoid circular imports ----
    from . import models  # noqa: F401

    # ---- Blueprints ----
    from .routes import main as main_bp
    from .auth import auth as auth_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)

    # ---- Flask-Login user loader ----
    @login_manager.user_loader
    def load_user(user_id: str):
        from .models import User
        return User.query.get(int(user_id))

    from public_demo import init_public_demo
    init_public_demo(app)

    return app

