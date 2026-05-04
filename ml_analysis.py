"""
ml_analysis.py — F1 2022 Machine Learning Analysis Module
- Optimal braking point clustering using K-Means
- Racing line deviation score
"""
import json
import numpy as np
from pathlib import Path

try:
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    print("[ml] scikit-learn not found. ML analysis disabled.")


def find_optimal_braking_zones(braking_points: list, n_clusters: int = 6) -> list:
    """
    Cluster braking points collected from multiple laps using K-Means.
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
        labels  = km.labels_
        result  = []
        for i, center in enumerate(centers):
            size = int(np.sum(labels == i))
            result.append({'x': float(center[0]), 'z': float(center[1]), 'size': size})
        return result
    except Exception as e:
        print(f"[ml] K-Means error: {e}")
        return []


def calculate_lap_consistency(lap_times_ms: list) -> dict:
    """
    Lap time consistency metric.
    Returns: {'mean': ms, 'std': ms, 'consistency_pct': float, 'best': ms}
    """
    if len(lap_times_ms) < 2:
        return {}
    arr  = np.array(lap_times_ms, dtype=float)
    arr  = arr[arr > 30000]  # Filter laps under 30s (invalid laps)
    if len(arr) < 2:
        return {}
    mean = float(np.mean(arr))
    std  = float(np.std(arr))
    best = float(np.min(arr))
    # Consistency: the lower the deviation, the better (100% = perfect)
    consistency = max(0.0, 100.0 - (std / mean * 100))
    return {'mean': mean, 'std': std, 'consistency_pct': consistency, 'best': best}


def run_braking_analysis_and_save():
    """
    Read braking_points.json and run K-Means,
    write result to optimal_braking.json.
    """
    if not Path("braking_points.json").exists():
        return
    try:
        with open("braking_points.json") as f:
            pts = json.load(f)
        clusters = find_optimal_braking_zones(pts)
        with open("optimal_braking.json", "w") as f:
            json.dump(clusters, f)
        print(f"[ml] {len(clusters)} optimal braking zones calculated.")
    except Exception as e:
        print(f"[ml] Analysis error: {e}")


if __name__ == "__main__":
    run_braking_analysis_and_save()
    if Path("optimal_braking.json").exists():
        import json
        with open("optimal_braking.json") as f:
            result = json.load(f)
        print("Optimal braking points:")
        for r in result:
            print(f"  X:{r['x']:.1f} Z:{r['z']:.1f} ({r['size']} data points)")
