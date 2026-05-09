"""
analytics_physics.py — F1 2022 Physics & Strategy Engine
Fuel load calculation, braking distance, tyre thermal model,
overtake opportunity window, and fuel deficit analysis.
"""
import math
import numpy as np

CAR_MASS_KG   = 798.0   # F1 2022 minimum weight (kg)
GRAVITY       = 9.81    # m/s²
FUEL_DENSITY  = 0.725   # kg/L (F1 fuel density)


# ══════════════════════════════════════════════
# 1. FUEL LOAD CALCULATOR
# ══════════════════════════════════════════════
def calculate_fuel_load(
    total_laps:        int,
    fuel_per_lap_kg:   float = 2.2,
    safety_car_laps:   int   = 3,
    safety_car_prob:   float = 0.4,
    formation_lap:     bool  = True
) -> dict:
    """
    Calculate the required fuel load for a race.
    Returns: {base_fuel_kg, sc_buffer_kg, formation_kg, total_fuel_kg, fuel_liters}
    """
    base_fuel     = total_laps * fuel_per_lap_kg
    sc_buffer     = safety_car_laps * fuel_per_lap_kg * safety_car_prob
    formation_kg  = fuel_per_lap_kg * 0.5 if formation_lap else 0.0
    total         = base_fuel + sc_buffer + formation_kg

    return {
        "base_fuel_kg":    round(base_fuel, 2),
        "sc_buffer_kg":    round(sc_buffer, 2),
        "formation_kg":    round(formation_kg, 2),
        "total_fuel_kg":   round(total, 2),
        "fuel_liters":     round(total / FUEL_DENSITY, 1),
        "fuel_per_lap_kg": fuel_per_lap_kg,
    }


# ══════════════════════════════════════════════
# 2. BRAKING DISTANCE CALCULATOR
# ══════════════════════════════════════════════
def calculate_braking_distance(
    v_entry_kmh:    float,
    v_corner_kmh:   float,
    deceleration_g: float = 4.5
) -> dict:
    """
    Calculate braking distance using kinetic energy formula.
    d = (v_entry² - v_corner²) / (2 * a)
    """
    if v_entry_kmh <= v_corner_kmh:
        return {"distance_m": 0.0, "time_s": 0.0,
                "decel_g": deceleration_g,
                "v_entry_kmh": v_entry_kmh, "v_corner_kmh": v_corner_kmh}

    v_in  = v_entry_kmh  / 3.6
    v_out = v_corner_kmh / 3.6
    a     = deceleration_g * GRAVITY

    dist  = (v_in**2 - v_out**2) / (2 * a)
    t     = (v_in - v_out) / a

    return {
        "distance_m":       round(dist, 1),
        "time_s":           round(t, 3),
        "decel_g":          deceleration_g,
        "v_entry_kmh":      v_entry_kmh,
        "v_corner_kmh":     v_corner_kmh,
        "braking_force_kn": round(CAR_MASS_KG * a / 1000, 1),
    }


def braking_distance_sweep(v_entry_range, v_corner_kmh=80, decel_g=4.5):
    """Build a braking distance table for a range of entry speeds."""
    return [
        {"v_entry": v, **calculate_braking_distance(v, v_corner_kmh, decel_g)}
        for v in v_entry_range
    ]


# ══════════════════════════════════════════════
# 3. TYRE THERMAL MODEL
# ══════════════════════════════════════════════
class TyreThermalModel:
    """
    Physics-based tyre temperature model.
    Heat input: braking force + lateral G + road friction.
    Cooling: airflow (speed-dependent).
    """
    def __init__(self,
                 base_temp:    float = 80.0,
                 ambient_temp: float = 22.0,
                 mass_kg:      float = CAR_MASS_KG):
        self.T         = float(base_temp)
        self.T_ambient = float(ambient_temp)
        self.mass      = float(mass_kg)

        # Calibration coefficients
        self.ALPHA_BRAKE = 1.2e-5   # J -> °C (braking)
        self.ALPHA_LAT   = 0.06     # G -> °C (cornering)
        self.BETA_COOL   = 0.0014   # Cooling coefficient

    def step(self, speed_kmh: float, brake: float,
             lat_g: float, dt: float = 0.1) -> float:
        """
        Advance the model by dt seconds, return new temperature.
        """
        v = speed_kmh / 3.6

        # Braking energy (J)
        brake_energy = 0.5 * self.mass * (v ** 2) * abs(brake) * dt

        # Lateral G heat (cornering friction)
        lat_heat = abs(lat_g) * self.mass * v * self.ALPHA_LAT * dt

        # Airflow cooling (increases with speed)
        cooling = self.BETA_COOL * (self.T - self.T_ambient) * (1 + speed_kmh / 180.0) * dt

        self.T += self.ALPHA_BRAKE * brake_energy + lat_heat - cooling
        self.T = max(self.T_ambient + 5.0, min(320.0, self.T))
        return round(self.T, 1)

    def reset(self, temp: float = None):
        self.T = temp if temp is not None else 80.0

    @property
    def in_optimal_window(self) -> bool:
        return 80.0 <= self.T <= 110.0

    @property
    def status(self) -> str:
        if self.T < 70:  return "Cold"
        if self.T < 80:  return "Warming up"
        if self.T < 110: return "Optimal"
        if self.T < 140: return "Hot"
        return "OVERHEATING"


def simulate_lap_thermal(speed_arr, brake_arr, latg_arr, ambient=22.0, dt=0.1):
    """
    Run thermal simulation for a full lap.
    Returns list of temperatures per timestep.
    """
    model = TyreThermalModel(base_temp=80.0, ambient_temp=ambient)
    temps = []
    for spd, brk, lat in zip(speed_arr, brake_arr, latg_arr):
        t = model.step(float(spd), float(brk), float(lat), dt)
        temps.append(t)
    return temps


# ══════════════════════════════════════════════
# 4. OVERTAKE OPPORTUNITY WINDOW
# ══════════════════════════════════════════════
def calculate_overtake_window(
    player_wear_pct:  float,
    target_wear_pct:  float,
    gap_s:            float,
    player_ers_pct:   float,
    speed_delta_kmh:  float = 0.0
) -> dict:
    """
    Calculate an overtake opportunity score.
    Factors: tyre wear delta, ERS deployment advantage, speed delta.
    Returns: {'opportunity': 'High'|'Medium'|'Low', ...}
    """
    wear_diff     = max(0, target_wear_pct - player_wear_pct)  # + = target more worn
    ers_boost_s   = (player_ers_pct / 100.0) * 0.65            # ERS -> time advantage (s)
    wear_adv_s    = wear_diff * 0.028                           # 0.028s per % wear diff
    speed_adv_s   = speed_delta_kmh * 0.004                     # speed delta -> time

    total_adv_s   = wear_adv_s + ers_boost_s + speed_adv_s
    laps_to_catch = gap_s / total_adv_s if total_adv_s > 0.0001 else 999.0

    if laps_to_catch < 5:    opportunity = "High"
    elif laps_to_catch < 15: opportunity = "Medium"
    else:                    opportunity = "Low"

    return {
        "wear_diff_pct":     round(wear_diff, 1),
        "ers_boost_s":       round(ers_boost_s, 3),
        "wear_advantage_s":  round(wear_adv_s, 3),
        "total_advantage_s": round(total_adv_s, 3),
        "laps_to_catch":     round(laps_to_catch, 1) if laps_to_catch < 999 else ">20",
        "opportunity":       opportunity,
        "gap_s":             round(gap_s, 3),
    }


# ══════════════════════════════════════════════
# 5. FUEL DEFICIT ANALYSIS
# ══════════════════════════════════════════════
def fuel_deficit_analysis(
    fuel_kg:     float,
    fuel_laps:   float,
    total_laps:  int,
    current_lap: int
) -> dict:
    """
    Determine whether remaining fuel is sufficient to finish the race.
    Returns: {is_sufficient, surplus_laps, deficit_kg, save_pct_needed}
    """
    laps_rem     = max(0, total_laps - current_lap)
    rate         = fuel_kg / max(1, fuel_laps)   # kg/lap (instantaneous)
    fuel_needed  = laps_rem * rate

    is_ok        = fuel_kg >= fuel_needed
    deficit_kg   = max(0.0, fuel_needed - fuel_kg)
    surplus_laps = round(fuel_laps - laps_rem, 1)

    if not is_ok and laps_rem > 0:
        save_pct = (deficit_kg / laps_rem) / rate * 100
    else:
        save_pct = 0.0

    return {
        "fuel_kg":         round(fuel_kg, 2),
        "laps_remaining":  laps_rem,
        "fuel_needed_kg":  round(fuel_needed, 2),
        "rate_kg_per_lap": round(rate, 3),
        "is_sufficient":   is_ok,
        "deficit_kg":      round(deficit_kg, 3),
        "deficit_per_lap": round(deficit_kg / max(1, laps_rem), 4),
        "save_pct_needed": round(save_pct, 1),
        "surplus_laps":    surplus_laps if is_ok else 0,
    }


# ══════════════════════════════════════════════
# 6. DYNAMIC PIT LOSS
# ══════════════════════════════════════════════

def dynamic_pit_loss(
    sc_status: int = 0,
    weather:   int = 0,
    base_loss: float = 22.0
) -> dict:
    """
    Calculate dynamic pit stop time loss accounting for SC/VSC and weather.
    Normal conditions: ~22.0 s.
    Under VSC/SC: cars run slower (delta time), so pit loss is reduced.
    """
    loss = base_loss

    # 1 = Safety Car, 2 = Virtual Safety Car
    if sc_status == 1:
        loss = base_loss * 0.55  # ~12 s loss
    elif sc_status == 2:
        loss = base_loss * 0.65  # ~14 s loss

    # Weather: 3=Light rain, 4=Heavy Rain, 5=Storm
    if weather >= 3:
        # Wet conditions slow the field; pit loss decreases relatively
        loss -= (weather - 2) * 0.8

    return {
        "dynamic_loss_sec":  round(loss, 2),
        "is_window_optimal": sc_status in [1, 2],
        "sc_status":         sc_status
    }


def calculate_slipstream_advantage(
    clean_air_speed_kmh:  float,
    slipstream_speed_kmh: float,
    straight_length_m:    float = 800.0
) -> dict:
    """
    Given clean-air vs slipstream/DRS speeds, calculate time and speed gained
    by the end of a straight.
    """
    speed_delta = slipstream_speed_kmh - clean_air_speed_kmh
    if speed_delta <= 0:
        return {"speed_delta_kmh": 0.0, "time_gained_sec": 0.0}

    v_clean_ms = clean_air_speed_kmh / 3.6
    v_slip_ms  = slipstream_speed_kmh / 3.6

    time_clean  = straight_length_m / v_clean_ms if v_clean_ms > 0 else 0
    time_slip   = straight_length_m / v_slip_ms  if v_slip_ms  > 0 else 0
    time_gained = max(0, time_clean - time_slip)

    return {
        "speed_delta_kmh": round(speed_delta, 1),
        "time_gained_sec": round(time_gained, 3),
        "efficient":       speed_delta > 5.0
    }


def lift_and_coast_savings(
    coast_time_sec:       float,
    fuel_rate_kg_per_sec: float = 0.035   # Approximate F1 fuel flow at max throttle
) -> dict:
    """
    Fuel saved when lifting off the throttle (Lift and Coast) vs full throttle.
    Returns fuel saved in kg and grams.
    """
    kg_saved     = coast_time_sec * fuel_rate_kg_per_sec
    grams_saved  = kg_saved * 1000.0

    return {
        "coast_time_sec":    round(coast_time_sec, 2),
        "fuel_saved_kg":     round(kg_saved, 3),
        "fuel_saved_grams":  round(grams_saved, 1)
    }


# ══════════════════════════════════════════════
# CLI DEMO
# ══════════════════════════════════════════════
if __name__ == "__main__":
    import json

    print("=== Fuel Load (57 laps, 2.2 kg/lap) ===")
    print(json.dumps(calculate_fuel_load(57, 2.2), indent=2))

    print("\n=== Braking Distance (300 → 80 km/h, 4.5g) ===")
    print(json.dumps(calculate_braking_distance(300, 80, 4.5), indent=2))

    print("\n=== Tyre Thermal (3 steps) ===")
    m = TyreThermalModel(80, 22)
    for spd, brk, lat in [(300, 0, 1), (100, 1, 0), (300, 0, 2)]:
        t = m.step(spd, brk, lat)
        print(f"  Spd:{spd}  Brk:{brk}  Lat:{lat}  -> {t}°C  [{m.status}]")

    print("\n=== Overtake Window ===")
    print(json.dumps(calculate_overtake_window(25, 65, 1.2, 80), indent=2))

    print("\n=== Fuel Deficit ===")
    print(json.dumps(fuel_deficit_analysis(40, 18, 57, 40), indent=2))
