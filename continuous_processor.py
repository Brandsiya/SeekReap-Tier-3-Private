import subprocess
import time
import datetime
import requests
import traceback
import os
from run_real_content_db import fetch_unverified_snapshots, update_snapshot

# ==============================
# Config
# ==============================

TIER3_HOST = "127.0.0.1"
TIER3_PORT = 10001
TIER3_CMD = ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", str(TIER3_PORT)]
TIER4_URL = os.environ.get("TIER4_URL")

LOG_DIR = "./logs"
LOG_PREFIX = "tier3_processing"
MAX_LOG_SIZE_MB = 10
BATCHES_PER_LOG = 5
SLEEP_BETWEEN_BATCHES = 10
RETRY_DB = 3
RETRY_TIER3 = 3

# ==============================
# Logging
# ==============================

def new_log_file():
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(LOG_DIR, f"{LOG_PREFIX}_{timestamp}.log")


def check_rotate():
    global log_file
    if not log_file or (
        os.path.exists(log_file)
        and os.path.getsize(log_file) > MAX_LOG_SIZE_MB * 1024 * 1024
    ):
        log_file = new_log_file()
        print(f"📝 Rotated log file: {log_file}")


# ==============================
# Tier-3 Management
# ==============================

def start_tier3():
    subprocess.run(["pkill", "-f", "uvicorn main:app"],
                   stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL)

    subprocess.Popen(TIER3_CMD,
                     stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL)

    while True:
        try:
            r = requests.get(
                f"http://{TIER3_HOST}:{TIER3_PORT}/",
                timeout=5
            )
            if r.json().get("status") == "Tier-3 is running":
                print("✅ Tier-3 is up!")
                return
        except requests.RequestException:
            time.sleep(1)


# ==============================
# Main Processing Loop
# ==============================

log_file = ""
batch_counter = 0

os.makedirs(LOG_DIR, exist_ok=True)

check_rotate()
start_tier3()

while True:
    try:
        check_rotate()
        timestamp = datetime.datetime.now().isoformat()

        # ----------------------
        # Fetch snapshots
        # ----------------------
        snapshots = []
        for attempt in range(RETRY_DB):
            try:
                snapshots = fetch_unverified_snapshots(limit=50)
                break
            except Exception as e:
                print(f"[WARN] DB fetch attempt {attempt+1} failed: {e}")
                time.sleep(2)

        if not snapshots:
            print(f"[INFO] No snapshots fetched at {timestamp}. Sleeping {SLEEP_BETWEEN_BATCHES}s...")
            time.sleep(SLEEP_BETWEEN_BATCHES)
            continue

        # ----------------------
        # Process snapshots
        # ----------------------
        for snap in snapshots:
            snapshot_id = snap.get("id")

            payload = {
                "task_id": snapshot_id,
                "task_type": "moderation",
                "inputs": snap,
                "context": {}
            }

            # Retry Tier-3
            tier3_response = None
            for attempt in range(RETRY_TIER3):
                try:
                    tier3_response = requests.post(
                        f"http://{TIER3_HOST}:{TIER3_PORT}/verify",
                        json=payload,
                        timeout=30
                    ).json()
                    break
                except requests.RequestException as e:
                    print(f"[WARN] Tier-3 request failed for {snapshot_id}: {e}")
                    start_tier3()
                    time.sleep(2)

            if not tier3_response:
                with open("tier3_failures.log", "a") as f:
                    f.write(f"[{datetime.datetime.now()}] Failed Tier-3: {snapshot_id}\n")
                continue

            # Tier-4
            try:
                tier4_response = requests.post(
                    TIER4_URL,
                    json=payload,
                    timeout=30
                ).json()
            except Exception as e:
                tier4_response = {"status": "failed", "reason": str(e)}
                print(f"[WARN] Tier-4 failed for {snapshot_id}: {e}")

            # Update DB
            for attempt in range(RETRY_DB):
                try:
                    update_snapshot(
                        snapshot_id,
                        tier3_response.get("tier3_score"),
                        tier4_response
                    )
                    break
                except Exception as e:
                    print(f"[WARN] DB update attempt {attempt+1} failed for {snapshot_id}: {e}")
                    time.sleep(2)

        # ----------------------
        # Batch Complete
        # ----------------------
        batch_counter += 1

        with open(log_file, "a") as f:
            f.write(
                f"\n===== Batch {batch_counter} completed at {datetime.datetime.now()} =====\n"
            )

        if batch_counter >= BATCHES_PER_LOG:
            batch_counter = 0
            check_rotate()

        time.sleep(SLEEP_BETWEEN_BATCHES)

    except Exception:
        with open(log_file, "a") as f:
            f.write(
                f"[ERROR] Exception at {datetime.datetime.now()}:\n{traceback.format_exc()}\n"
            )

        print(f"[ERROR] Exception occurred. See log: {log_file}")
        time.sleep(10)
