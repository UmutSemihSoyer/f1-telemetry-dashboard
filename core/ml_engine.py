import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional

try:
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler
    from sklearn.ensemble import RandomForestRegressor
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

class MLEngine:
    """Machine Learning analysis suite for braking and consistency."""

    @staticmethod
    def find_optimal_braking_zones(braking_points: List[Dict], n_clusters: int = 6) -> List[Dict]:
        """
        Clusters braking points to identify ideal braking zones.

        Args:
            braking_points: List of recorded braking events.
            n_clusters: Number of target clusters (corners).

        Returns:
            List of cluster centroids with metadata.
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
        except Exception:
            return []

    @staticmethod
    def calculate_lap_consistency(lap_times_ms: List[float]) -> Dict[str, float]:
        """Calculates lap time consistency metrics."""
        if len(lap_times_ms) < 2: return {}
        arr = np.array(lap_times_ms, dtype=float)
        arr = arr[arr > 30000]
        if len(arr) < 2: return {}
        mean = float(np.mean(arr))
        std = float(np.std(arr))
        consistency = max(0.0, 100.0 - (std / mean * 100))
        return {'mean': mean, 'std': std, 'consistency_pct': consistency, 'best': float(np.min(arr))}

class TyreDegradationModel:
    """Predictive model for tyre wear degradation."""

    def __init__(self):
        self.model = RandomForestRegressor(n_estimators=100, random_state=42) if HAS_SKLEARN else None
        self.is_trained = False
        if self.model:
            # Initial synthetic training for cold-start performance
            X_train = np.array([[10.0, 30.0, 0.05, 1.5], [20.0, 35.0, 0.10, 1.8], [40.0, 40.0, 0.20, 2.0], [60.0, 45.0, 0.30, 2.5], [70.0, 50.0, 0.40, 3.0]])
            y_train = np.array([25, 18, 10, 4, 1])
            self.model.fit(X_train, y_train)
            self.is_trained = True
            
    def predict_cliff_laps(self, current_wear: float, track_temp: float, wheel_slip: float, susp_stress: float) -> int:
        """Predicts remaining laps until the tyre performance 'cliff'."""
        if not self.is_trained or not self.model: return -1
        X_test = np.array([[current_wear, track_temp, wheel_slip, susp_stress]])
        pred = self.model.predict(X_test)[0]
        return max(0, int(pred))

class BrakingCoach:
    """Real-time coaching engine comparing current braking with best lap."""

    def __init__(self):
        self.best_braking_points: List[float] = []

    def load_best_lap(self, lap_data: List[Dict]):
        """Builds braking point reference from best lap data."""
        self.best_braking_points = []
        if not lap_data: return
        for i in range(1, len(lap_data)):
            prev = lap_data[i-1].get('Brake', 0)
            curr = lap_data[i].get('Brake', 0)
            if curr > 50 and prev < 10:
                self.best_braking_points.append(lap_data[i].get('LapDistance', 0))

    def check_brake_timing(self, current_dist: float) -> Optional[str]:
        """Returns timing status: EARLY, LATE, or GOOD."""
        if not self.best_braking_points: return None
        nearest = min(self.best_braking_points, key=lambda x: abs(x - current_dist))
        diff = current_dist - nearest
        if abs(diff) < 100:
            if diff < -8.0: return "EARLY"
            if diff > 8.0:  return "LATE"
            return "GOOD"
        return None

def run_ml_analysis_pass(input_file: str = "braking_points.json", output_file: str = "optimal_braking.json"):
    """Runs a batch ML analysis pass on stored data."""
    if not Path(input_file).exists(): return
    try:
        with open(input_file) as f: pts = json.load(f)
        clusters = MLEngine.find_optimal_braking_zones(pts)
        with open(output_file, "w") as f: json.dump(clusters, f)
    except Exception: pass
