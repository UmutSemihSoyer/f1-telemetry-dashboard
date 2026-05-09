import json
import numpy as np
from pathlib import Path

try:
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler
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
