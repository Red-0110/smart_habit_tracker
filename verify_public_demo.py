"""Visitor-demo integration tests; all data is temporary."""
from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import timedelta
import re
from demo import make_app, KIND
from public_demo import DemoVisitor, User, db, now
if KIND=='habits':
    from web import create_app
    from web.models import Habit, HabitLog
else:
    from app import create_app
    from app.models import Session

def token(response):
    match=re.search(r'name="csrf_token"[^>]*value="([^"]+)"',response.get_data(as_text=True))
    assert match, response.get_data(as_text=True)[:300]
    return match.group(1)

def post(client,path,source='/demo',**data):
    return client.post(path,data={'csrf_token':token(client.get(source)),**data})

with TemporaryDirectory() as folder:
    app=create_app({'TESTING':True,'PUBLIC_DEMO':True,'SECRET_KEY':'testing-only-long-secret-key-0123456789',
                    'SQLALCHEMY_DATABASE_URI':'sqlite:///'+str(Path(folder)/'visitors.sqlite3')})
    runner=app.test_cli_runner()
    assert runner.invoke(args=['demo-init']).exit_code==0
    assert runner.invoke(args=['demo-init']).exit_code!=0
    a,b=app.test_client(),app.test_client()
    assert a.get('/').location.endswith('/demo')
    assert a.get('/login').status_code==404
    assert a.get('/register').status_code==404
    assert a.post('/demo/start').status_code==400
    assert b'Demo-Explore' not in a.get('/demo').data
    # Browsers request missing icons after rendering a form. Neither those
    # requests nor anonymous protected-page redirects may rotate its CSRF token.
    form_token = token(a.get('/demo'))
    for missing in ['/favicon.ico', '/apple-touch-icon.png', '/missing-page']:
        assert a.get(missing).status_code == 404
    assert a.get('/dashboard', follow_redirects=True).status_code == 200
    assert a.post('/demo/start', data={'csrf_token': form_token}).status_code == 302
    with a.session_transaction() as state: akey=state['demo_visitor']
    assert post(a,'/demo/start').status_code==302
    with app.app_context(): assert DemoVisitor.query.count()==1
    assert post(b,'/demo/start').status_code==302
    with b.session_transaction() as state: bkey=state['demo_visitor']
    with app.app_context():
        ar=db.session.get(DemoVisitor,akey);br=db.session.get(DemoVisitor,bkey)
        aid,bid=ar.user_id,br.user_id
        assert aid!=bid
        baseline=HabitLog.query.filter_by(user_id=bid).count() if KIND=='habits' else Session.query.filter_by(user_id=bid).count()
        assert baseline==(168 if KIND=='habits' else 40)
    assert a.get('/dashboard').status_code==200
    assert b'Reset my demo' in a.get('/dashboard').data
    assert a.get('/dashboard').headers['Cache-Control']=='no-store'
    if KIND=='habits':
        assert a.get('/settings').status_code==404
        assert post(a,'/habits/new',source='/dashboard',habit_name='Only visitor A sees this').status_code==302
        with app.app_context(): foreign=Habit.query.filter_by(user_id=bid).first().id
        assert post(a,'/log',source='/dashboard',habit_id=foreign,completed='on').status_code==404
        assert b'Only visitor A sees this' in a.get('/dashboard').data
        assert b'Only visitor A sees this' not in b.get('/dashboard').data
    else:
        with app.app_context():
            s=Session.query.filter_by(user_id=aid).first();s.notes='Only visitor A sees this';db.session.commit()
            foreign=Session.query.filter_by(user_id=bid).first().id
        assert a.get(f'/sessions/{foreign}/edit').status_code==403
        assert b'Only visitor A sees this' in a.get('/sessions/export.csv').data
        assert b'Only visitor A sees this' not in b.get('/sessions/export.csv').data
    # Saved data can be read by a newly constructed app using the same signed cookie.
    new_app=create_app(dict(app.config))
    new_client=new_app.test_client()
    cookie=a.get_cookie(app.config['SESSION_COOKIE_NAME'])
    new_client.set_cookie(app.config['SESSION_COOKIE_NAME'],cookie.value)
    assert new_client.get('/dashboard').status_code==200
    assert post(a,'/demo/reset').status_code==429
    with app.app_context():
        db.session.get(DemoVisitor,akey).created_at=now()-timedelta(seconds=20);db.session.commit()
    assert post(a,'/demo/reset').status_code==302
    with app.app_context():
        assert db.session.get(DemoVisitor,akey) is None
        assert db.session.get(DemoVisitor,bkey) is not None
        assert (HabitLog.query.filter_by(user_id=bid).count() if KIND=='habits' else Session.query.filter_by(user_id=bid).count())==baseline
        assert User.query.count()==2
    with a.session_transaction() as state: newkey=state['demo_visitor']
    # Expired signed cookies cannot access data; cleanup removes only expired demo owners.
    with app.app_context():
        db.session.get(DemoVisitor,newkey).expires_at=now()-timedelta(seconds=1)
        real=User(email='ordinary@example.com');real.set_password('ordinary-password')
        if KIND=='habits':real.username='Ordinary account'
        db.session.add(real);db.session.commit();real_id=real.id
    assert a.get('/dashboard').location.endswith('/demo')
    assert runner.invoke(args=['demo-cleanup']).exit_code==0
    with app.app_context():
        assert db.session.get(DemoVisitor,newkey) is None
        assert db.session.get(User,real_id) is not None
    app.config['DEMO_MAX_VISITORS']=1
    c=app.test_client()
    assert post(c,'/demo/start').status_code==503
    assert post(b,'/demo/end').status_code==302
    with app.app_context():
        assert DemoVisitor.query.count()==0
        assert User.query.count()==1
    assert b.get('/dashboard').location.endswith('/demo')
print('PASS: visitor entry, CSRF, repeated entry, isolation, restart cookie, reset isolation, expiry, cleanup, capacity, end demo, disabled accounts.')
