"""Exercise demo workflows against a temporary database; leaves the demo intact."""
from pathlib import Path
import re
import tempfile
from datetime import date
from demo import make_app, seed, KIND, PASSWORD

def token(response):
    text = response.get_data(as_text=True)
    match=re.search(r'name="csrf_token"[^>]*value="([^"]+)"',text)
    assert match, 'Missing CSRF field'
    return match.group(1)

def login(client,email):
    r=client.post('/login',data={'email':email,'password':PASSWORD,'csrf_token':token(client.get('/login'))},follow_redirects=True)
    assert r.status_code==200 and b'Logout' in r.data or r.status_code==200 and b'logout' in r.data
    return r

with tempfile.TemporaryDirectory() as folder:
    database=Path(folder)/'test.sqlite3'
    app=make_app(database)
    app.config['TESTING']=True
    seed(app)
    if KIND=='habits':
        from web import db
        from web.models import User,Habit,HabitLog
    else:
        from app.extensions import db
        from app.models import User,Activity,Session
    with app.app_context():
        assert User.query.count()==2
        initial = HabitLog.query.count() if KIND=='habits' else Session.query.count()
    seed(app)
    with app.app_context():
        assert (HabitLog.query.count() if KIND=='habits' else Session.query.count())==initial
    c=app.test_client()
    assert c.get('/dashboard').status_code==302
    assert c.post('/login',data={'email':'alex@example.com','password':PASSWORD}).status_code==400
    login(c,'alex@example.com')
    if KIND=='habits':
        with app.app_context():
            alex=User.query.filter_by(email='alex@example.com').one()
            jordan=User.query.filter_by(email='jordan@example.com').one()
            other=Habit.query.filter_by(user_id=jordan.id).first().id
        r=c.post('/habits/new',data={'csrf_token':token(c.get('/dashboard')),'habit_name':'Interview persistence proof'},follow_redirects=True)
        assert r.status_code==200 and b'Interview persistence proof' in r.data
        with app.app_context(): own=Habit.query.filter_by(name='Interview persistence proof').one().id
        for route in ['/log','/dashboard']:
            assert c.post(route,data={'csrf_token':token(c.get('/dashboard')),'habit_id':other,'completed':'on'}).status_code==404
        assert c.post('/log',data={'csrf_token':token(c.get('/dashboard')),'habit_id':own,'completed':'on'},follow_redirects=True).status_code==200
        r=c.post('/settings',data={'csrf_token':token(c.get('/settings')),'current_password':PASSWORD,'username':'Alex','email':'alex@example.com','weekly_goal':'21','nudge_preference':'on'},follow_redirects=True)
        assert r.status_code==200 and b'Settings saved' in r.data
        with app.app_context(): assert db.session.get(User,alex.id).weekly_goal==21
        # Restart app against the same database, then log in as each user.
        c2=make_app(database).test_client()
        assert b'Interview persistence proof' in login(c2,'alex@example.com').data
        c3=make_app(database).test_client()
        assert b'Interview persistence proof' not in login(c3,'jordan@example.com').data
        assert c3.post(f'/habits/{own}/delete',data={'csrf_token':token(c3.get('/dashboard'))}).status_code==404
    else:
        with app.app_context():
            alex=User.query.filter_by(email='alex@example.com').one()
            jordan=User.query.filter_by(email='jordan@example.com').one()
            own=Activity.query.filter_by(user_id=alex.id).first().id
            other_session=Session.query.filter_by(user_id=jordan.id).first().id
            other_activity=Activity.query.filter_by(user_id=jordan.id).first().id
        r=c.post('/sessions/',data={'csrf_token':token(c.get('/sessions/')),'activity_id':own,'session_date':date.today().isoformat(),'duration_min':37,'rpe':5,'notes':'Interview persistence proof'},follow_redirects=True)
        assert r.status_code==200 and b'Interview persistence proof' in r.data
        with app.app_context():
            record=Session.query.filter_by(notes='Interview persistence proof').one()
            assert record.load==185
        assert c.get(f'/sessions/{other_session}/edit').status_code==403
        before=c.get('/sessions/export.csv').data
        assert b'Interview persistence proof' in before
        c.post('/sessions/',data={'csrf_token':token(c.get('/sessions/')),'activity_id':other_activity,'session_date':date.today().isoformat(),'duration_min':30,'rpe':5,'notes':'Forbidden record'})
        assert b'Forbidden record' not in c.get('/sessions/export.csv').data
        c2=make_app(database).test_client();login(c2,'alex@example.com')
        assert b'Interview persistence proof' in c2.get('/sessions/').data
        c3=make_app(database).test_client();login(c3,'jordan@example.com')
        assert b'Interview persistence proof' not in c3.get('/sessions/export.csv').data
    assert c.get('/static/vendor/chart.umd.js').status_code==200
    assert b'https://cdn.' not in c.get('/dashboard').data
print('PASS: seeding, idempotence, CSRF, login, record creation, restart persistence, user isolation, local chart asset.' )
