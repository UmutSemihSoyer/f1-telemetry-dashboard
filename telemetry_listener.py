import threading
import queue
import time
import pandas as pd
import json
import logging
from core.listener import TelemetryListener
from core.ml_engine import run_ml_analysis_pass
from services.data_service import DataService
from services.race_engineer import generate_lap_feedback
from voice_alerts import (start_voice_thread, radio_engineer_feedback)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MainListener")

class TelemetryManager:
    def __init__(self):
        self.listener = TelemetryListener()
        self.data_service = DataService()
        self.telemetry_buffer = []
        self._last_lap_num = 0
        self.full_lap_buffer = []
        self._latest_lap_info = {}

    def run(self):
        # Start UDP listener in separate thread
        logger.info("Starting UDP listener thread...")
        listener_thread = threading.Thread(target=self.listener.listen, daemon=True)
        listener_thread.start()
        
        # Start voice thread
        start_voice_thread()
        
        # Main processing loop
        logger.info("Main processing loop active.")
        while True:
            try:
                # Get item from listener queue
                item = self.listener.data_queue.get(timeout=1.0)
                p_type = item.get('Type')
                
                # Buffer telemetry data for chunked processing
                if p_type == 'Telemetry':
                    self.telemetry_buffer.append(item)
                    if len(self.telemetry_buffer) >= 100:
                        self.process_telemetry_chunk()
                
                # Handle lap completion
                elif p_type == 'LapData':
                    self._latest_lap_info = item
                    lap_num = item.get('CurrentLapNum', 0)
                    if lap_num != self._last_lap_num and self._last_lap_num > 0:
                        self.handle_lap_completion(item)
                    self._last_lap_num = lap_num

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in manager loop: {e}")

    def process_telemetry_chunk(self):
        df = pd.DataFrame(self.telemetry_buffer)
        
        # Merge latest lap info for Delta/Map
        if self._latest_lap_info:
            df['LapDistance'] = self._latest_lap_info.get('LapDistance', 0)
            df['LapTime'] = self._latest_lap_info.get('CurrentLapTimeMS', 0) / 1000.0
            df['LapNum'] = self._latest_lap_info.get('CurrentLapNum', 0)
            
        self.full_lap_buffer.append(df.copy())
        
        # Save for live dashboard
        try:
            df.to_json("live_data.json", orient="records")
        except Exception as e:
            logger.error(f"Failed to save live_data.json: {e}")
            
        self.telemetry_buffer.clear()

    def handle_lap_completion(self, lap_item):
        lap_num = self._last_lap_num
        s1 = lap_item.get('Sector1MS', 0)
        s2 = lap_item.get('Sector2MS', 0)
        total = lap_item.get('LastLapTimeMS', 0)
        ts = lap_item.get('Timestamp', 0)
        
        logger.info(f"Lap {lap_num} completed. Time: {total}ms")
        
        # Save to DB
        self.data_service.save_lap(lap_num, s1, s2, total, ts)
        
        # Trigger ML analysis
        threading.Thread(target=run_ml_analysis_pass, daemon=True).start()
        
        # Race Engineer Feedback
        if self.full_lap_buffer:
            full_df = pd.concat(self.full_lap_buffer, ignore_index=True)
            self.full_lap_buffer.clear()
            
            feedback = generate_lap_feedback(full_df)
            with open("engineer_feedback.json", "w", encoding="utf-8") as f:
                json.dump(feedback, f)
            
            if feedback.get("priority_alert"):
                radio_engineer_feedback(feedback["priority_alert"])

if __name__ == "__main__":
    manager = TelemetryManager()
    manager.run()
