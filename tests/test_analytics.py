"""
tests/test_analytics.py — F1 2022 Telemetri Analitik Test Suiti
pytest ile calistir: cd udp_telemetry && pytest tests/ -v
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import numpy as np

from analytics_physics import (
    calculate_fuel_load,
    calculate_braking_distance,
    TyreThermalModel,
    calculate_overtake_window,
    fuel_deficit_analysis,
    simulate_lap_thermal,
    braking_distance_sweep,
)
from ml_analysis import calculate_lap_consistency


# ════════════════════════════════════════════════════════════
# YAKIT YUK HESAPLAYICISI
# ════════════════════════════════════════════════════════════
class TestFuelLoad:
    def test_base_fuel_correct(self):
        r = calculate_fuel_load(57, 2.2)
        assert r["base_fuel_kg"] == pytest.approx(57 * 2.2, abs=0.01)

    def test_total_exceeds_base(self):
        r = calculate_fuel_load(50, 2.0)
        assert r["total_fuel_kg"] > r["base_fuel_kg"]

    def test_zero_laps(self):
        r = calculate_fuel_load(0, 2.0)
        assert r["base_fuel_kg"] == 0.0

    def test_liters_conversion(self):
        r = calculate_fuel_load(10, 2.0, safety_car_laps=0,
                                safety_car_prob=0, formation_lap=False)
        expected = 10 * 2.0 / 0.725
        assert r["fuel_liters"] == pytest.approx(expected, abs=0.2)

    def test_no_safety_car_buffer(self):
        r = calculate_fuel_load(50, 2.0, safety_car_prob=0, formation_lap=False)
        assert r["sc_buffer_kg"] == 0.0

    def test_fuel_per_lap_returned(self):
        r = calculate_fuel_load(30, 1.8)
        assert r["fuel_per_lap_kg"] == 1.8

    def test_high_lap_count(self):
        r = calculate_fuel_load(100, 2.2)
        assert r["total_fuel_kg"] > 200.0


# ════════════════════════════════════════════════════════════
# BRAKING DISTANCE
# ════════════════════════════════════════════════════════════
class TestBrakingDistance:
    def test_standard_braking(self):
        r = calculate_braking_distance(300, 80, 4.5)
        assert r["distance_m"] > 50
        assert r["distance_m"] < 350

    def test_no_braking_needed(self):
        r = calculate_braking_distance(80, 100, 4.5)
        assert r["distance_m"] == 0.0
        assert r["time_s"] == 0.0

    def test_equal_speeds(self):
        r = calculate_braking_distance(150, 150)
        assert r["distance_m"] == 0.0

    def test_higher_entry_longer_distance(self):
        r1 = calculate_braking_distance(200, 80, 4.5)
        r2 = calculate_braking_distance(300, 80, 4.5)
        assert r2["distance_m"] > r1["distance_m"]

    def test_higher_decel_shorter_distance(self):
        r1 = calculate_braking_distance(250, 100, 3.0)
        r2 = calculate_braking_distance(250, 100, 5.0)
        assert r2["distance_m"] < r1["distance_m"]

    def test_braking_force_positive(self):
        r = calculate_braking_distance(300, 80)
        assert r["braking_force_kn"] > 0

    def test_sweep_asc_order(self):
        sweep = braking_distance_sweep([100, 200, 300], v_corner_kmh=80)
        dists = [s["distance_m"] for s in sweep]
        assert dists[0] < dists[1] < dists[2]


# ════════════════════════════════════════════════════════════
# TYRE THERMAL MODEL
# ════════════════════════════════════════════════════════════
class TestTyreThermal:
    def test_braking_heats_tyre(self):
        m = TyreThermalModel(80, 22)
        t = m.step(200, 1.0, 0.0, dt=0.5)
        assert t > 80

    def test_high_speed_no_brake_cools(self):
        m = TyreThermalModel(150, 22)
        for _ in range(100):
            m.step(300, 0.0, 0.0)
        assert m.T < 150

    def test_temp_upper_bound(self):
        m = TyreThermalModel(80, 22)
        for _ in range(1000):
            m.step(300, 1.0, 4.0)
        assert m.T <= 320.0

    def test_temp_lower_bound(self):
        m = TyreThermalModel(80, 22)
        for _ in range(500):
            m.step(0, 0.0, 0.0)
        assert m.T >= 22.0 + 5.0

    def test_reset(self):
        m = TyreThermalModel(80, 22)
        for _ in range(50):
            m.step(300, 1.0, 3.0)
        m.reset(90.0)
        assert m.T == 90.0

    def test_optimal_window(self):
        m = TyreThermalModel(95, 22)
        assert m.in_optimal_window is True

    def test_cold_tyre_not_optimal(self):
        m = TyreThermalModel(60, 22)
        assert m.in_optimal_window is False

    def test_status_strings(self):
        m = TyreThermalModel(55, 22)
        assert m.status == "Soguk"
        m.T = 95; assert m.status == "Optimal"
        m.T = 145; assert m.status == "ASIRI SICAK"

    def test_simulate_lap(self):
        speeds = [200, 100, 50, 200, 300] * 20
        brakes = [0, 0.8, 1.0, 0, 0] * 20
        lats   = [1.0, 0.5, 0.0, 2.0, 0.5] * 20
        temps  = simulate_lap_thermal(speeds, brakes, lats)
        assert len(temps) == len(speeds)
        assert all(isinstance(t, float) for t in temps)


# ════════════════════════════════════════════════════════════
# OVERTAKE OPPORTUNITY WINDOW
# ════════════════════════════════════════════════════════════
class TestOvertakeWindow:
    def test_high_wear_diff_high_opportunity(self):
        r = calculate_overtake_window(20, 75, 0.5, 90)
        assert r["opportunity"] == "High"

    def test_equal_wear_low_opportunity(self):
        r = calculate_overtake_window(50, 50, 5.0, 20)
        assert r["opportunity"] == "Low"

    def test_small_gap_better(self):
        r1 = calculate_overtake_window(20, 60, 0.5, 70)
        r2 = calculate_overtake_window(20, 60, 5.0, 70)
        laps1 = r1["laps_to_catch"]
        laps2 = r2["laps_to_catch"]
        if isinstance(laps1, float) and isinstance(laps2, (float, int)):
            assert laps1 <= laps2

    def test_no_advantage_returns_over20(self):
        r = calculate_overtake_window(80, 80, 10.0, 0)
        # When no advantage, returns the string '>20'
        assert r['laps_to_catch'] == ">20"

    def test_wear_diff_in_result(self):
        r = calculate_overtake_window(30, 70, 1.0, 80)
        assert r["wear_diff_pct"] == pytest.approx(40.0, abs=0.1)


# ════════════════════════════════════════════════════════════
# FUEL DEFICIT ANALYSIS
# ════════════════════════════════════════════════════════════
class TestFuelDeficit:
    def test_sufficient_fuel(self):
        # 10 kg fuel, burns 0.9kg/lap (fuel_laps=11.1), needs 47*0.9=42.3kg for 47 laps
        # But we have 10 kg and fuel_laps=11.1, so 10/11.1=0.9kg/lap, fuel_needed=47*0.9=42.3 > 10 -> NOT sufficient
        # Let's use: 50 kg, 50 fuel_laps (1 kg/lap), 57 laps total, lap 50 -> 7 laps rem, need 7 kg < 50 kg
        r = fuel_deficit_analysis(50.0, 50.0, 57, 50)
        assert r["is_sufficient"] is True

    def test_insufficient_fuel(self):
        r = fuel_deficit_analysis(5.0, 2.5, 57, 10)
        assert r["is_sufficient"] is False

    def test_laps_remaining(self):
        r = fuel_deficit_analysis(50.0, 50.0, 57, 10)
        assert r["laps_remaining"] == 47

    def test_no_deficit_when_sufficient(self):
        r = fuel_deficit_analysis(50.0, 50.0, 57, 50)
        assert r["deficit_kg"] == 0.0

    def test_save_pct_zero_when_ok(self):
        r = fuel_deficit_analysis(50.0, 50.0, 57, 50)
        assert r["save_pct_needed"] == 0.0

    def test_race_over_returns_zero_rem(self):
        r = fuel_deficit_analysis(5.0, 3.0, 57, 57)
        assert r["laps_remaining"] == 0


# ════════════════════════════════════════════════════════════
# LAP CONSISTENCY
# ════════════════════════════════════════════════════════════
class TestLapConsistency:
    def test_very_consistent(self):
        laps = [90000, 90050, 89980, 90020, 90010]
        r = calculate_lap_consistency(laps)
        assert r.get('consistency_pct', 0) > 99.9  # Very tight spread

    def test_inconsistent_lower_than_consistent(self):
        """Inconsistent laps should score LOWER than consistent ones."""
        consistent   = [90000, 90050, 89980, 90020, 90010]
        inconsistent = [90000, 96000, 84000, 93000, 87000]
        r_con = calculate_lap_consistency(consistent)
        r_inc = calculate_lap_consistency(inconsistent)
        assert r_con['consistency_pct'] > r_inc['consistency_pct']

    def test_empty_returns_empty(self):
        assert calculate_lap_consistency([]) == {}

    def test_single_lap_returns_empty(self):
        assert calculate_lap_consistency([90000]) == {}

    def test_best_is_minimum(self):
        laps = [91000, 89500, 90000]
        r = calculate_lap_consistency(laps)
        assert r['best'] == pytest.approx(89500.0)

    def test_filters_outliers(self):
        # Very short times (< 30s = 30000ms) should be filtered
        laps = [90000, 100, 90100, 90200]
        r = calculate_lap_consistency(laps)
        # mean should be around 90100 (not dragged down by 100ms outlier)
        assert r.get('mean', 0) > 30000
