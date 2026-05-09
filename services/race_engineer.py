import numpy as np
import pandas as pd
from core.physics_engine import PhysicsEngine

class RaceEngineerService:
    def __init__(self):
        self.physics = PhysicsEngine()

    def split_into_micro_sectors(self, df, min_speed_dip=15):
        """
        Identifies corners by finding local minimums in speed.
        """
        corners = []
        if "Speed" not in df.columns or len(df) < 50:
            return corners
            
        speed = df["Speed"].rolling(window=5, center=True).mean().fillna(df["Speed"])
        
        troughs = []
        for i in range(10, len(speed) - 10):
            if speed.iloc[i] < speed.iloc[i-5] and speed.iloc[i] < speed.iloc[i+5]:
                local_max_before = speed.iloc[max(0, i-50):i].max()
                if local_max_before - speed.iloc[i] > min_speed_dip:
                    if not troughs or i - troughs[-1] > 30:
                        troughs.append(i)
                        
        for apex_idx in troughs:
            entry_idx = apex_idx
            while entry_idx > 0 and df["Brake"].iloc[entry_idx-1] > 0.05:
                entry_idx -= 1
                
            exit_idx = apex_idx
            while exit_idx < len(df) - 1 and df["Throttle"].iloc[exit_idx] < 0.95:
                exit_idx += 1
                
            corners.append({
                "entry_idx": entry_idx,
                "apex_idx": apex_idx,
                "exit_idx": exit_idx,
                "dist_entry": df["LapDistance"].iloc[entry_idx] if "LapDistance" in df else 0,
                "dist_apex": df["LapDistance"].iloc[apex_idx] if "LapDistance" in df else 0,
                "v_min": df["Speed"].iloc[apex_idx]
            })
            
        return corners

    def analyze_lap_performance(self, current_df, pb_df):
        """
        Compares current lap performance against Personal Best.
        """
        if current_df is None or pb_df is None or current_df.empty or pb_df.empty:
            return []
            
        curr_corners = self.split_into_micro_sectors(current_df)
        pb_corners = self.split_into_micro_sectors(pb_df)
        
        feedback = []
        for i, c_curr in enumerate(curr_corners):
            matching_pb = None
            for c_pb in pb_corners:
                if abs(c_curr["dist_apex"] - c_pb["dist_apex"]) < 100:
                    matching_pb = c_pb
                    break
                    
            if matching_pb:
                turn_name = f"Turn {i+1}"
                
                # Brake Point
                brake_diff = matching_pb["dist_entry"] - c_curr["dist_entry"]
                if brake_diff > 15:
                    feedback.append(f"{turn_name}: You braked {brake_diff:.0f} meters EARLIER. Try braking later.")
                elif brake_diff < -15:
                    feedback.append(f"{turn_name}: You braked {abs(brake_diff):.0f} meters LATE, you might have missed the apex.")
                    
                # Apex Speed
                speed_diff = matching_pb["v_min"] - c_curr["v_min"]
                if speed_diff > 5:
                    feedback.append(f"{turn_name}: Apex speed is {speed_diff:.0f} km/h SLOWER. Try carrying more speed into the corner.")
                    
                # Exit Throttle
                dist_to_throttle_curr = current_df["LapDistance"].iloc[c_curr["exit_idx"]] - c_curr["dist_apex"]
                dist_to_throttle_pb = pb_df["LapDistance"].iloc[matching_pb["exit_idx"]] - matching_pb["dist_apex"]
                if dist_to_throttle_curr > dist_to_throttle_pb + 15:
                    feedback.append(f"{turn_name}: You applied throttle {dist_to_throttle_curr - dist_to_throttle_pb:.0f} meters LATER on exit. Traction lost.")

        return feedback

    def get_setup_advice(self, df):
        """
        Provides suggestions for car setup changes.
        """
        feedback = []
        if "Speed" not in df.columns or "Throttle" not in df.columns:
            return feedback
            
        # Top Speed
        if df["Speed"].max() < 310:
            feedback.append("Top speed is very low. Consider reducing the Rear Wing by 2-3 clicks.")
            
        # Traction
        if "EngineRPM" in df.columns and "Gear" in df.columns:
            wheelspin = ((df["Gear"] <= 4) & (df["Throttle"] > 0.8) & (df["Speed"] < 150) & (df["EngineRPM"] > 11500)).sum()
            if wheelspin > 20:
                feedback.append("Experiencing heavy wheelspin on slow corner exits. Try opening the On-Throttle Diff (Lower setting).")
                
        return feedback

def generate_lap_feedback(current_df, pb_df=None):
    """
    Compatibility wrapper for the new service-oriented architecture.
    """
    service = RaceEngineerService()
    feedback = service.analyze_lap_performance(current_df, pb_df)
    setup = service.get_setup_advice(current_df)
    
    return {
        "all_feedback": feedback + setup,
        "priority_alert": feedback[0] if feedback else (setup[0] if setup else "")
    }
