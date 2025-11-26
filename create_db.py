from smart_habit_tracker.web import create_app, db

app = create_app()

with app.app_context():
    db.create_all()
    print("Database created succesfully.")