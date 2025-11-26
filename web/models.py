from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from . import db


class User(db.Model, UserMixin):
    """Users of the habit tracker"""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)

    # Preferences (used by settings page)
    nudge_preference = db.Column(db.Boolean, default=True)
    weekly_goal = db.Column(db.Integer, default=0)
    email_reminders = db.Column(db.Boolean, default=True)

    # Relationships
    habits = db.relationship(
        "Habit",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan",
    )
    habit_logs = db.relationship(
        "HabitLog",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan",
    )
    categories = db.relationship(
        "HabitCategory",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan",
    )

    # Helpers
    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:
        return f"<User {self.username}>"


class HabitCategory(db.Model):
    """User-owned category for grouping habits"""
    __tablename__ = "habit_categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

    # owner
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    # link to habits
    habits = db.relationship("Habit", back_populates="category", lazy=True)

    # enforce unique name per user
    __table_args__ = (
        db.UniqueConstraint("user_id", "name", name="uq_category_per_user"),
    )

    def __repr__(self) -> str:
        return f"<HabitCategory {self.name}>"


class Habit(db.Model):
    """A habit the user wants to track"""
    __tablename__ = "habits"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # owner
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    # optional category
    category_id = db.Column(db.Integer, db.ForeignKey("habit_categories.id"), nullable=True, index=True)
    category = db.relationship("HabitCategory", back_populates="habits")

    # logs
    logs = db.relationship(
        "HabitLog",
        back_populates="habit",
        lazy=True,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Habit {self.name}>"


class HabitLog(db.Model):
    """Track each completion of a habit"""
    __tablename__ = "habit_logs"

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    completed = db.Column(db.Boolean, default=False, nullable=False)

    # foreign keys
    habit_id = db.Column(db.Integer, db.ForeignKey("habits.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    # back to habit
    habit = db.relationship("Habit", back_populates="logs")

    def __repr__(self) -> str:
        return f"<HabitLog habit={self.habit_id} at {self.timestamp}>"