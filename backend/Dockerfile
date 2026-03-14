FROM python:3.12-slim

# Install system dependencies for psycopg2 and LDAP
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    libldap2-dev \
    libsasl2-dev \
    ldap-utils \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy project
COPY . .

# Expose port
EXPOSE 8000

# Run server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]