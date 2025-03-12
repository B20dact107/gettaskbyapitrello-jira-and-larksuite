# Dockerfile
FROM python:3.111

WORKDIR /app


# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .


CMD ["python", "app.py"]