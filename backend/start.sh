#!/bin/sh
set -e
python manage.py migrate --noinput
python manage.py shell -c "from django.contrib.auth.models import User; import os; u=os.environ.get('DJANGO_SUPERUSER_USERNAME','admin'); e=os.environ.get('DJANGO_SUPERUSER_EMAIL','admin@trustlayer.com'); p=os.environ.get('DJANGO_SUPERUSER_PASSWORD',''); User.objects.filter(username=u).exists() or (p and User.objects.create_superuser(u,e,p))"
exec gunicorn trustlayer.wsgi:application --bind 0.0.0.0:${PORT:-8000}
