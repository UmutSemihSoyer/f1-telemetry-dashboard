import numpy as np

class PhysicsEngine:
    @staticmethod
    def calculate_g_forces(last_velocity, current_velocity, dt):
        """
        Calculates longitudinal and lateral G-forces.
        Note: The F1 UDP packet already provides these, but this can be used for verification 
        or if using raw motion data.
        """
        if dt <= 0: return 0.0, 0.0
        accel = (current_velocity - last_velocity) / dt
        g_force = accel / 9.81
        return g_force

    @staticmethod
    def estimate_braking_distance(v_entry_kmh, v_target_kmh, avg_decel_g=4.5):
        """
        Estimates the distance required to slow down.
        Formula: d = (v_f^2 - v_i^2) / (2 * a)
        """
        v_i = v_entry_kmh / 3.6
        v_f = v_target_kmh / 3.6
        a = avg_decel_g * -9.81
        if a == 0: return 0.0
        dist = (v_f**2 - v_i**2) / (2 * a)
        return max(0.0, dist)

    @staticmethod
    def calculate_slipstream_advantage(base_top_speed, current_top_speed):
        """
        Calculates the time gained due to slipstream/DRS on a straight.
        """
        delta_v = current_top_speed - base_top_speed
        if delta_v <= 0: return {"time_gained_sec": 0, "speed_delta_kmh": 0}
        
        # Simplified: Gain over a 1000m straight
        time_base = 1000 / (base_top_speed / 3.6)
        time_curr = 1000 / (current_top_speed / 3.6)
        return {
            "time_gained_sec": time_base - time_curr,
            "speed_delta_kmh": delta_v
        }

class TyreThermalModel:
    def __init__(self, baseline_temp=90.0):
        self.T = baseline_temp
        self.k_ambient = 0.02  # Cooling rate
        self.k_friction = 0.05 # Heating from friction
        self.k_brake = 0.1    # Heating from brake soak

    def update(self, speed, brake_press, ambient_temp, dt=0.1):
        # Cooling
        self.T -= self.k_ambient * (self.T - ambient_temp) * (1 + speed/300) * dt
        # Heating
        self.T += self.k_friction * (speed/300)**2 * dt
        self.T += self.k_brake * brake_press * dt
        return self.T

    def get_status(self):
        if self.T < 70:  return "Cold"
        if self.T < 80:  return "Warming up"
        if self.T < 110: return "Optimal"
        if self.T < 140: return "Hot"
        return "OVERHEATING"

def fuel_deficit_analysis(fuel_kg, fuel_laps, current_lap, total_laps):
    """
    Analyzes if the current fuel is sufficient to finish the race.
    """
    laps_rem = max(0, total_laps - current_lap)
    if fuel_laps <= 0:
        rate = 0
    else:
        rate = fuel_kg / fuel_laps # kg/lap
    
    fuel_needed = laps_rem * rate
    is_ok = fuel_kg >= fuel_needed
    deficit = fuel_needed - fuel_kg if not is_ok else 0
    
    save_pct = 0
    if not is_ok and fuel_needed > 0:
        save_pct = (deficit / fuel_needed) * 100
        
    return {
        "is_sufficient": is_ok,
        "surplus_laps": fuel_laps - laps_rem if is_ok else 0,
        "deficit_kg": deficit,
        "save_pct_needed": save_pct
    }

def calculate_lift_and_coast_gain(coast_time_sec, fuel_rate_kg_per_sec=0.035):
    """
    Calculates fuel saved in grams during coasting.
    """
    kg_saved = coast_time_sec * fuel_rate_kg_per_sec
    return kg_saved * 1000.0
