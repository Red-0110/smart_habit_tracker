"""Hosting-neutral WSGI entry point; configuration is explicit and separate from local demos."""
import os
from web import create_app

secret = os.environ.get('SECRET_KEY', '')
database = os.environ.get('DEMO_DATABASE_URL', '')
if len(secret) < 32 or not database:
    raise RuntimeError('Set SECRET_KEY (at least 32 characters) and DEMO_DATABASE_URL for a dedicated demo database.')

app = create_app({
    'PUBLIC_DEMO': True,
    'DEMO_MODE': False,
    'SECRET_KEY': secret,
    'SQLALCHEMY_DATABASE_URI': database,
    'SESSION_COOKIE_NAME': 'public_demo_habits',
    'SESSION_COOKIE_HTTPONLY': True,
    'SESSION_COOKIE_SAMESITE': 'Lax',
    'SESSION_COOKIE_SECURE': os.environ.get('DEMO_LOCAL_HTTP') != '1',
    'MAX_CONTENT_LENGTH': 64 * 1024,
    'DEBUG': False,
})
