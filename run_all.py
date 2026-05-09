import subprocess
import sys
import time

print("=" * 50)
print("F1 2022 Telemetry Suite Starting...")
print("=" * 50)

try:
    print("[1/3] Mock Telemetry Sender disabled (connecting to live game)...")
    sender = None
    time.sleep(1)

    print("[2/3] Starting Telemetry Listener (background processor)...")
    listener = subprocess.Popen([sys.executable, "telemetry_listener.py"])
    time.sleep(1)

    print("[3/3] Starting Live Dashboard (web interface)...")
    dashboard = subprocess.Popen([sys.executable, "dashboard.py"])

    print("\nAll systems active!")
    print("Open http://127.0.0.1:8050 in your browser to view live data.")
    print("\nPress CTRL+C in this terminal to shut down all services.\n")

    while True:
        time.sleep(1)

except KeyboardInterrupt:
    print("\nShutdown signal received (CTRL+C). Stopping services...")
    if sender:
        sender.terminate()
    listener.terminate()
    dashboard.terminate()
    print("All services stopped successfully.")
