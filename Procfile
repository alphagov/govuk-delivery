web:    ./venv/bin/gunicorn -blocalhost:3042 --workers=2 service:flask_app
worker: ./venv/bin/celery worker -A service
