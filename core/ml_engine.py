import json
import numpy as np
from pathlib import Path

try:
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler
    from sklearn.ensemble import RandomForestRegressor
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

class MLEngine:
    @staticmethod
    def find_optimal_braking_zones(braking_points: list, n_clusters: int = 6) -> list:
        """
        Clusters braking points collected from multiple laps using K-Means.
        Each cluster's centroid = ideal braking point.
        Returns: list of {'x': float, 'z': float, 'size': int}
        """
        if not HAS_SKLEARN or len(braking_points) < n_clusters * 2:
            return []
        try:
            pts = np.array([[p['PosX'], p['PosZ']] for p in braking_points])
            scaler = StandardScaler()
            pts_scaled = scaler.fit_transform(pts)
            km = KMeans(n_clusters=min(n_clusters, len(pts)), random_state=42, n_init=10)
            km.fit(pts_scaled)
            centers = scaler.inverse_transform(km.cluster_centers_)
            labels = km.labels_
            result = []
            for i, center in enumerate(centers):
                size = int(np.sum(labels == i))
                result.append({'x': float(center[0]), 'z': float(center[1]), 'size': size})
            return result
        except Exception as e:
            # We would log this in a real system
            return []

    @staticmethod
    def calculate_lap_consistency(lap_times_ms: list) -> dict:
        """
        Lap time consistency metric.
        Returns: {'mean': ms, 'std': ms, 'consistency_pct': float, 'best': ms}
        """
        if len(lap_times_ms) < 2:
            return {}
        arr = np.array(lap_times_ms, dtype=float)
        arr = arr[arr > 30000]  # Filter laps under 30s (invalid laps)
        if len(arr) < 2:
            return {}
        mean = float(np.mean(arr))
        std = float(np.std(arr))
        best = float(np.min(arr))
        # Consistency: the lower the deviation, the better (100% = perfect)
        consistency = max(0.0, 100.0 - (std / mean * 100))
        return {'mean': mean, 'std': std, 'consistency_pct': consistency, 'best': best}

class TyreDegradationModel:
    def __init__(self):
        self.model = RandomForestRegressor(n_estimators=100, random_state=42) if HAS_SKLEARN else None
        self.is_trained = False
        
        # We will train on dummy synthetic data so the model has "experience" out of the box.
        if self.model:
            # Features: [CurrentWearPct, TrackTemp, WheelSlipAvg, SuspStressAvg]
            # Target: Laps remaining until wear > 75%
            X_train = np.array([
                [10.0, 30.0, 0.05, 1.5],
                [20.0, 35.0, 0.10, 1.8],
                [40.0, 40.0, 0.20, 2.0],
                [60.0, 45.0, 0.30, 2.5],
                [70.0, 50.0, 0.40, 3.0]
            ])
            # Remaining laps to cliff (assuming cliff is 75%)
            y_train = np.array([25, 18, 10, 4, 1])
            self.model.fit(X_train, y_train)
            self.is_trained = True
            
    def predict_cliff_laps(self, current_wear, track_temp, wheel_slip, susp_stress):
        if not self.is_trained or not self.model:
            return -1
        # Predict remaining laps until cliff
        X_test = np.array([[current_wear, track_temp, wheel_slip, susp_stress]])
        pred = self.model.predict(X_test)[0]
        return max(0, int(pred))

class BrakingCoach:
    def __init__(self):
        self.best_braking_points = [] # List of LapDistance markers

    def load_best_lap(self, lap_data):
        """Identify braking points (start of braking) in the best lap."""
        self.best_braking_points = []
        if not lap_data: return
        
        # Simple heuristic: Find where Brake goes from < 10 to > 50
        for i in range(1, len(lap_data)):
            prev = lap_data[i-1].get('Brake', 0)
            curr = lap_data[i].get('Brake', 0)
            if curr > 50 and prev < 10:
                self.best_braking_points.append(lap_data[i].get('LapDistance', 0))

    def check_brake_timing(self, current_dist):
        """Compare current distance with the nearest best-lap braking point."""
        if not self.best_braking_points: return None
        
        # Find nearest point within 100m
        nearest = min(self.best_braking_points, key=lambda x: abs(x - current_dist))
        diff = current_dist - nearest # positive means we are LATER than best lap
        
        if abs(diff) < 100:
            if diff < -8.0: return "EARLY"   # Braked 8m+ too early
            if diff > 8.0:  return "LATE"    # Braked 8m+ too late
            return "GOOD"
        return None

def run_ml_analysis_pass(input_file="braking_points.json", output_file="optimal_braking.json"):
    """
    Utility function to run the ML analysis on a stored JSON file.
    """
    if not Path(input_file).exists():
        return
    try:
        with open(input_file) as f:
            pts = json.load(f)
        clusters = MLEngine.find_optimal_braking_zones(pts)
        with open(output_file, "w") as f:
            json.dump(clusters, f)
    except Exception:
        pass
