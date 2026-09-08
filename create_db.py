from web import create_app, db

with create_app().app_context():
    db.create_all()
