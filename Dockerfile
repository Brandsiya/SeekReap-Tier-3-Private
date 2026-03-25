FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    ffmpeg \
    libchromaprint-tools \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

COPY . .

CMD exec uvicorn main:app --host 0.0.0.0 --port $PORT
# Add cookies file
COPY cookies.txt /app/cookies.txt
