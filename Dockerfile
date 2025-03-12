# Dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Add additional dependencies
RUN pip install \
    flask \
    pymongo \
    python-dotenv \
    requests \
    apscheduler

# Copy application code
COPY . .

# Environment variables (override with docker-compose)
ENV PYTHONUNBUFFERED=1
ENV MONGO_URI=mongodb://mongo:27017
ENV FLASK_ENV=production

CMD ["python", "app.py"]