import numpy as np
from typing import Dict, Tuple, Optional

class PhysicsEngine:
    """Core physics calculations for F1 telemetry analysis."""

    @staticmethod
    def calculate_g_forces(last_velocity: float, current_velocity: float, dt: float) -> float:
        """
        Calculates longitudinal G-force based on velocity change.

        Args:
            last_velocity: Previous velocity in m/s.
            current_velocity: Current velocity in m/s.
            dt: Time delta in seconds.

        Returns:
            Calculated G-force.
        """
        if dt <= 0: return 0.0
        accel = (current_velocity - last_velocity) / dt
        g_force = accel / 9.81
        return g_force

    @staticmethod
    def estimate_braking_distance(v_entry_kmh: float, v_target_kmh: float, avg_decel_g: float = 4.5) -> float:
        """
        Estimates the distance required to slow down.

        Args:
            v_entry_kmh: Entry speed in km/h.
            v_target_kmh: Target speed in km/h.
            avg_decel_g: Average deceleration in Gs.

        Returns:
            Estimated distance in meters.
        """
        v_i = v_entry_kmh / 3.6
        v_f = v_target_kmh / 3.6
        a = avg_decel_g * -9.81
        if a == 0: return 0.0
        dist = (v_f**2 - v_i**2) / (2 * a)
        return max(0.0, dist)

    @staticmethod
    def calculate_slipstream_advantage(base_top_speed: float, current_top_speed: float) -> Dict[str, float]:
        """
        Calculates potential time gain from slipstream/DRS.

        Args:
            base_top_speed: Normal top speed without DRS.
            current_top_speed: Current top speed with DRS/Slipstream.

        Returns:
            Dictionary containing 'time_gained_sec' and 'speed_delta_kmh'.
        """
        delta_v = current_top_speed - base_top_speed
        if delta_v <= 0: return {"time_gained_sec": 0.0, "speed_delta_kmh": 0.0}
        
        time_base = 1000 / (base_top_speed / 3.6)
        time_curr = 1000 / (current_top_speed / 3.6)
        return {
            "time_gained_sec": float(time_base - time_curr),
            "speed_delta_kmh": float(delta_v)
        }

class TyreThermalModel:
    """Physics-based model to estimate tyre temperatures and status."""

    def __init__(self, baseline_temp: float = 90.0):
        self.T = baseline_temp
        self.k_ambient = 0.02
        self.k_friction = 0.05
        self.k_brake = 0.1

    def update(self, speed: float, brake_press: float, ambient_temp: float, dt: float = 0.1) -> float:
        """Update the temperature based on current inputs."""
        self.T -= self.k_ambient * (self.T - ambient_temp) * (1 + speed/300) * dt
        self.T += self.k_friction * (speed/300)**2 * dt
        self.T += self.k_brake * brake_press * dt
        return self.T

    def get_status(self) -> str:
        """Returns the thermal status of the tyre."""
        if self.T < 70:  return "Cold"
        if self.T < 80:  return "Warming up"
        if self.T < 110: return "Optimal"
        if self.T < 140: return "Hot"
        return "OVERHEATING"

def fuel_deficit_analysis(fuel_kg: float, fuel_laps: float, current_lap: int, total_laps: int) -> Dict[str, any]:
    """Analyzes fuel sufficiency for the remainder of the race."""
    laps_rem = max(0, total_laps - current_lap)
    rate = fuel_kg / fuel_laps if fuel_laps > 0 else 0
    fuel_needed = laps_rem * rate
    is_ok = fuel_kg >= fuel_needed
    deficit = fuel_needed - fuel_kg if not is_ok else 0
    save_pct = (deficit / fuel_needed * 100) if not is_ok and fuel_needed > 0 else 0
    
    return {
        "is_sufficient": is_ok,
        "surplus_laps": float(fuel_laps - laps_rem) if is_ok else 0.0,
        "deficit_kg": float(deficit),
        "save_pct_needed": float(save_pct)
    }

def calculate_lift_and_coast_gain(coast_time_sec: float, fuel_rate_kg_per_sec: float = 0.035) -> float:
    """Estimates fuel saved in grams during coasting."""
    return coast_time_sec * fuel_rate_kg_per_sec * 1000.0

class AeroAnalyzer:
    """Analyzes aerodynamic efficiency and dirty air impact."""

    def __init__(self):
        self.clean_air_baseline = {}

    def update_baseline(self, lap_data: list):
        """Builds the Clean Air baseline from best lap data."""
        if not lap_data: return
        for row in lap_data:
            dist = row.get('LapDistance', 0)
            glat = abs(row.get('GLat', 0))
            bin_id = int(dist // 10)
            self.clean_air_baseline[bin_id] = max(self.clean_air_baseline.get(bin_id, 0), glat)

    def analyze_dirty_air(self, dist: float, current_glat: float, gap_ahead: float) -> float:
        """Estimates downforce loss percentage when following another car."""
        if gap_ahead <= 0 or gap_ahead > 0.7: return 0.0
        bin_id = int(dist // 10)
        baseline = self.clean_air_baseline.get(bin_id, 0)
        if baseline < 1.2: return 0.0
        current_val = abs(current_glat)
        if current_val < baseline * 0.95:
            loss = (1.0 - (current_val / baseline)) * 100
            return round(min(loss, 35.0), 1)
        return 0.0
