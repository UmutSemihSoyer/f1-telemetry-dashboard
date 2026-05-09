import json
import threading
import time
import webview
import logging
from pyngrok import ngrok

# We import the Dash app and the TelemetryManager
from dashboard import app
from telemetry_listener import TelemetryManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AppWindow")

def start_ngrok():
    try:
        with open("config.json") as f:
            cfg = json.load(f)
            if cfg.get("remote", {}).get("STREAMING_ENABLED", False):
                token = cfg["remote"].get("NGROK_AUTH_TOKEN")
                if token: ngrok.set_auth_token(token)
                
                public_url = ngrok.connect(8050).public_url
                logger.info(f"🚀 REMOTE STREAM ACTIVE: {public_url}")
                with open("stream_url.txt", "w") as f:
                    f.write(public_url)
    except Exception as e:
        logger.error(f"Ngrok failed: {e}")

def run_dash():
    # Run Dash server in production mode (waitress/werkzeug without debug to prevent reloading)
    logger.info("Starting Dash server...")
    app.run(debug=False, port=8050, use_reloader=False)

def run_listener():
    logger.info("Starting Telemetry Listener...")
    manager = TelemetryManager()
    manager.run()

if __name__ == '__main__':
    # Start Ngrok if enabled
    start_ngrok()
    
    # Start the backend listener
    listener_thread = threading.Thread(target=run_listener, daemon=True)
    listener_thread.start()

    # Start the frontend dash server
    dash_thread = threading.Thread(target=run_dash, daemon=True)
    dash_thread.start()

    # Give the server a second to start
    time.sleep(1.5)

    logger.info("Launching Desktop UI...")
    
    # Create the native window
    window = webview.create_window(
        "F1 2022 Pit Wall Pro", 
        "http://127.0.0.1:8050",
        width=1600,
        height=900,
        background_color='#0e0e11',
        resizable=True
    )
    
    # Start the desktop window loop
    webview.start()
