FROM python:3.11-slim

# Install system dependencies for PostgreSQL
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt uvicorn

# Copy the rest of the application
COPY . .

# Run with uvicorn (FastAPI)
CMD exec uvicorn main:app --host 0.0.0.0 --port $PORT
