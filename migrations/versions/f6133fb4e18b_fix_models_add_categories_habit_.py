"""Fix models: add categories, habit.category_id; remove log.category_id; clean duplicates

Revision ID: f6133fb4e18b
Revises: adc6facb3cb0
Create Date: 2025-09-09 10:18:53.945637
"""
from alembic import op
import sqlalchemy as sa

revision = "f6133fb4e18b"
down_revision = "adc6facb3cb0"
branch_labels = None
depends_on = None

# <<< ADJUST THIS IF NEEDED >>>
LOGS_TABLE = "habit_logs"  # change to "logs" if that's your real table name

def _drop_all_tmp_tables(bind, base_table_name: str):
    """
    Drop any Alembic SQLite batch temp tables for a given base table:
    e.g., '_alembic_tmp_<base>%' (with or without suffixes Alembic may add).
    """
    # Find all matching stale temp tables
    rows = bind.exec_driver_sql(
        "SELECT name FROM sqlite_master "
        "WHERE type='table' AND name LIKE :pfx",
        {"pfx": f"_alembic_tmp_{base_table_name}%"},
    ).fetchall()
    for (name,) in rows:
        bind.exec_driver_sql(f'DROP TABLE IF EXISTS "{name}"')

def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # 1) Create habit_categories if missing
    if not insp.has_table("habit_categories"):
        op.create_table(
            "habit_categories",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(
                ["user_id"], ["users.id"], name="fk_habit_categories_user_id_users"
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "name", name="uq_category_per_user"),
        )

    # 2) Remove category_id from LOGS_TABLE only if present (SQLite-safe)
    if insp.has_table(LOGS_TABLE):
        log_cols = {c["name"] for c in insp.get_columns(LOGS_TABLE)}
        if "category_id" in log_cols:
            _drop_all_tmp_tables(bind, LOGS_TABLE)
            with op.batch_alter_table(LOGS_TABLE, schema=None) as batch_op:
                batch_op.drop_column("category_id")

    # 3) Add category_id to habits only if missing (SQLite-safe)
    if insp.has_table("habits"):
        habit_cols = {c["name"] for c in insp.get_columns("habits")}
        if "category_id" not in habit_cols:
            _drop_all_tmp_tables(bind, "habits")
            with op.batch_alter_table("habits", schema=None) as batch_op:
                batch_op.add_column(sa.Column("category_id", sa.Integer(), nullable=True))
                batch_op.create_index(
                    batch_op.f("ix_habits_category_id"), ["category_id"], unique=False
                )
                batch_op.create_foreign_key(
                    "fk_habits_category_id_habit_categories",
                    "habit_categories",
                    ["category_id"],
                    ["id"],
                )

def downgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # Reverse habits change
    if insp.has_table("habits"):
        habit_cols = {c["name"] for c in insp.get_columns("habits")}
        if "category_id" in habit_cols:
            # Gather indexes to avoid errors if missing
            idx_names = {i.get("name") for i in insp.get_indexes("habits")}
            _drop_all_tmp_tables(bind, "habits")
            with op.batch_alter_table("habits", schema=None) as batch_op:
                # best-effort: drop FK if it exists
                try:
                    batch_op.drop_constraint(
                        "fk_habits_category_id_habit_categories", type_="foreignkey"
                    )
                except Exception:
                    pass
                ix = batch_op.f("ix_habits_category_id")
                if ix in idx_names:
                    batch_op.drop_index(ix)
                batch_op.drop_column("category_id")

    # Reverse LOGS_TABLE change
    if insp.has_table(LOGS_TABLE):
        log_cols = {c["name"] for c in insp.get_columns(LOGS_TABLE)}
        if "category_id" not in log_cols:
            _drop_all_tmp_tables(bind, LOGS_TABLE)
            with op.batch_alter_table(LOGS_TABLE, schema=None) as batch_op:
                batch_op.add_column(sa.Column("category_id", sa.Integer(), nullable=True))

    # Reverse habit_categories creation
    if insp.has_table("habit_categories"):
        op.drop_table("habit_categories")
