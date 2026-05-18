FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput || true

EXPOSE 8000

# migrate + create superuser from env vars + start gunicorn
CMD python manage.py migrate --noinput && \
    python manage.py shell -c "
from django.contrib.auth.models import User
import os
u = os.environ.get('DJANGO_SUPERUSER_USERNAME','admin')
e = os.environ.get('DJANGO_SUPERUSER_EMAIL','admin@trustlayer.com')
p = os.environ.get('DJANGO_SUPERUSER_PASSWORD','')
if p and not User.objects.filter(username=u).exists():
    User.objects.create_superuser(u, e, p)
    print('Superuser created')
" && \
    gunicorn trustlayer.wsgi:application --bind 0.0.0.0:${PORT:-8000}
