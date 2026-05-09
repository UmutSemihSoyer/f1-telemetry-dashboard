import pandas as pd
import numpy as np
from pathlib import Path

class TelemetryService:
    def __init__(self):
        self.best_lap_df = None
        self.current_lap_data = []

    def load_best_lap(self, lap_times_df):
        """
        Loads the best lap telemetry from a previously saved state or DB.
        """
        # For simplicity, we'll look for a 'best_lap_telemetry.json'
        if Path("best_lap_telemetry.json").exists():
            self.best_lap_df = pd.read_json("best_lap_telemetry.json")
            return True
        return False

    def calculate_delta(self, current_df):
        """
        Calculates the time delta between the current lap and the best lap.
        Uses Distance-based interpolation.
        """
        if self.best_lap_df is None or current_df.empty:
            return 0.0
            
        if "LapDistance" not in current_df.columns or "LapDistance" not in self.best_lap_df.columns:
            return 0.0
            
        # Get current distance and time
        curr_dist = current_df["LapDistance"].iloc[-1]
        curr_time = current_df["LapTime"].iloc[-1]
        
        # Find the time in the best lap at the same distance
        # We interpolate the 'LapTime' column of the best lap using 'LapDistance' as index
        best_lap_time_at_dist = np.interp(
            curr_dist, 
            self.best_lap_df["LapDistance"], 
            self.best_lap_df["LapTime"]
        )
        
        delta = curr_time - best_lap_time_at_dist
        return delta

    def update_best_lap(self, lap_df):
        """
        Saves the provided lap as the new best lap.
        """
        self.best_lap_df = lap_df.copy()
        lap_df.to_json("best_lap_telemetry.json", orient="records")
