"""Local demo launcher. All demo data lives beside this script in demo-data/."""
import argparse
import json
import os
from pathlib import Path
import secrets
import sqlite3
import subprocess
import sys
import threading
import venv
import webbrowser
from datetime import date, datetime, timedelta, timezone

ROOT = Path(__file__).resolve().parent
KIND = 'habits'
PORT = 5051
DATA = ROOT / 'demo-data'
DATABASE = DATA / 'demo.sqlite3'
PASSWORD = 'Demo-Explore-2026!'
EMAILS = ['alex@example.com', 'jordan@example.com']


def make_app(database=DATABASE):
    DATA.mkdir(exist_ok=True)
    secret_file = DATA / '.secret'
    if not secret_file.exists():
        secret_file.write_text(secrets.token_hex(32))
        secret_file.chmod(0o600)
    if KIND == 'habits':
        from web import create_app
    else:
        from app import create_app
    # Explicit override prevents inherited DATABASE_URL from selecting a real database.
    app = create_app({'SQLALCHEMY_DATABASE_URI': 'sqlite:///' + str(database.resolve()),
                      'SECRET_KEY': secret_file.read_text(), 'DEMO_MODE': True,
                      'SESSION_COOKIE_NAME': 'demo_' + KIND,
                      'DEBUG': False})
    return app


def seed(app):
    if KIND == 'habits':
        from web import db
        from web.models import User, HabitCategory, Habit, HabitLog
    else:
        from app.extensions import db
        from app.models import User, Activity, Session
    with app.app_context():
        db.create_all()
        if User.query.first():
            print('Existing demo data preserved. Use reset to restore sample records.')
            return
        for index, email in enumerate(EMAILS):
            user = User(email=email)
            if KIND == 'habits':
                user.username = ['Alex', 'Jordan'][index]
                user.weekly_goal = 15
            user.set_password(PASSWORD)
            db.session.add(user)
            db.session.flush()
            if KIND == 'habits':
                for j, (category_name, name) in enumerate([
                    ('Learning', 'Read 20 minutes'), ('Health', 'Morning walk'),
                    ('Career', 'Practice Python'), ('Wellbeing', 'Evening journal')]):
                    category = HabitCategory(name=category_name, user_id=user.id)
                    db.session.add(category)
                    db.session.flush()
                    habit = Habit(name=name, description='Fictional demo habit', user_id=user.id,
                                  category_id=category.id, created_at=datetime.now(timezone.utc).replace(tzinfo=None)-timedelta(days=42))
                    db.session.add(habit)
                    db.session.flush()
                    for days_ago in range(42):
                        when = datetime.combine(datetime.now(timezone.utc).replace(tzinfo=None).date()-timedelta(days=days_ago), datetime.min.time())
                        db.session.add(HabitLog(habit_id=habit.id, user_id=user.id,
                            timestamp=when+timedelta(hours=8+j), completed=(days_ago+j+index)%5 != 0))
            else:
                activities = []
                for name, category in [('Tennis','Sport'), ('Strength','Gym'), ('Walking','Recovery')]:
                    activity = Activity(name=name, category=category, user_id=user.id)
                    db.session.add(activity)
                    db.session.flush()
                    activities.append(activity)
                for days_ago in range(56):
                    if days_ago % 7 in (2, 5):
                        continue
                    activity = activities[(days_ago+index)%3]
                    db.session.add(Session(user_id=user.id, activity_id=activity.id,
                        session_date=date.today()-timedelta(days=days_ago),
                        duration_min=25+((days_ago+index)%5)*10,
                        rpe=2 if activity.name=='Walking' else 4+(days_ago%4),
                        notes=['Easy technique practice', 'Steady effort; felt recovered', 'Short focused session'][days_ago%3]))
        db.session.commit()
        print('Created fictional sample records for Alex and Jordan.')


def inspect_database():
    if not DATABASE.exists():
        raise SystemExit('Run setup first.')
    with sqlite3.connect(DATABASE.as_uri()+'?mode=ro', uri=True) as con:
        tables = ['users','habit_categories','habits','habit_logs'] if KIND=='habits' else ['user','activity','session']
        counts = {table:con.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0] for table in tables}
    print(json.dumps({'database':str(DATABASE), 'record_counts':counts}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['setup','run','seed','reset','inspect'])
    parser.add_argument('--open', action='store_true', help='Open the browser when starting')
    parser.add_argument('--port', type=int, default=PORT)
    args = parser.parse_args()
    python = ROOT / '.venv' / ('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    if Path(sys.prefix).resolve() != (ROOT/'.venv').resolve():
        if args.command == 'setup':
            if not python.exists():
                venv.EnvBuilder(with_pip=True).create(ROOT/'.venv')
            subprocess.check_call([str(python), '-m', 'pip', 'install', '-r', str(ROOT/'requirements-demo.txt')])
        elif not python.exists():
            raise SystemExit('First run: python3 demo.py setup')
        raise SystemExit(subprocess.call([str(python), str(Path(__file__).resolve()), *sys.argv[1:]]))
    if args.command == 'inspect':
        inspect_database()
        return
    if args.command == 'reset' and DATABASE.exists():
        # Back up before reset; only this fixed demo database can be replaced.
        backup = DATA / ('backup-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.sqlite3')
        with sqlite3.connect(DATABASE) as source, sqlite3.connect(backup) as target:
            source.backup(target)
        DATABASE.unlink()
        print('Previous demo data backed up to', backup)
    app = make_app()
    if args.command in ('setup','seed','reset') or not DATABASE.exists():
        seed(app)
    print('Demo accounts:', ', '.join(EMAILS), '\nPassword:', PASSWORD)
    print('Database:', DATABASE)
    if args.command == 'run':
        from waitress import serve
        url = f'http://127.0.0.1:{args.port}/login'
        print('Open', url, '\nStop with Ctrl+C. Stop before using reset.', flush=True)
        if args.open:
            threading.Timer(1, lambda:webbrowser.open(url)).start()
        serve(app, host='127.0.0.1', port=args.port)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\nDemo stopped. Saved data is preserved.')
