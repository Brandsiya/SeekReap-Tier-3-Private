#!/bin/bash

# Configuration
API_URL="https://seekreap-tier-3-private.onrender.com/health" # We'll add this endpoint below
LOG_FILE="watchdog_history.log"
THRESHOLD_MS=2000 # Alert if response takes > 2 seconds

check_health() {
    TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")
    
    # Perform the request and capture HTTP status code and response time
    RESPONSE=$(curl -s -w "%{http_code} %{time_total}" -o /dev/null "$API_URL")
    STATUS=$(echo $RESPONSE | cut -d' ' -f1)
    LATENCY=$(echo $RESPONSE | cut -d' ' -f2)
    
    # Convert latency to milliseconds for comparison
    LATENCY_MS=$(echo "$LATENCY * 1000 / 1" | bc)

    if [ "$STATUS" -eq 200 ]; then
        if [ "$LATENCY_MS" -gt "$THRESHOLD_MS" ]; then
            echo "[$TIMESTAMP] ⚠️ WARNING: Slow Response (${LATENCY_MS}ms)" >> "$LOG_FILE"
        else
            echo "[$TIMESTAMP] ✅ Healthy (${LATENCY_MS}ms)" >> "$LOG_FILE"
        fi
    else
        echo "[$TIMESTAMP] 🚨 CRITICAL: Tier-3 is DOWN (Status: $STATUS)" >> "$LOG_FILE"
        # Optional: Add a command here to send an email or Slack alert
    fi
}

# Run the check
check_health
