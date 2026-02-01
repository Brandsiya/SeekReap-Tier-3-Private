#!/bin/bash
# Tier 3 API Auto Start Script

BASE_DIR="$HOME/SeekReap-Tier-3-Private"
LOG_FILE="$BASE_DIR/tier3_server.log"
PID_FILE="$BASE_DIR/tier3_server.pid"
APP_MODULE="tier3_api_app:app"

echo "Stopping old Tier 3 servers..."
pkill -f "uvicorn $APP_MODULE" 2>/dev/null
pkill -f "python3 -m uvicorn $APP_MODULE" 2>/dev/null

echo "Clearing Python cache..."
find "$BASE_DIR" -name "__pycache__" -type d -exec rm -rf {} +

export PYTHONPATH="$BASE_DIR:$PYTHONPATH"

PORT=$(python3 -c "import socket; s=socket.socket(); s.bind(('',0)); print(s.getsockname()[1]); s.close()")
echo "Starting server on port $PORT..."

nohup uvicorn "$APP_MODULE" --host 127.0.0.1 --port $PORT > "$LOG_FILE" 2>&1 &
SERVER_PID=$!
echo $SERVER_PID > "$PID_FILE"

echo "Tier 3 API started!"
echo "PID: $SERVER_PID"
echo "Log file: $LOG_FILE"
echo "URL: http://127.0.0.1:$PORT"
