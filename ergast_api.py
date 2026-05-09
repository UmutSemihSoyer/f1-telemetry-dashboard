"""
ergast_api.py — Real F1 Data (Jolpi Ergast API)
Fetch and compare: your lap times vs real F1 drivers.

Usage:
  from ergast_api import fetch_race_laps, get_best_laps_per_driver, CIRCUIT_MAP
"""
import json
import time
from pathlib import Path
import pandas as pd

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("[ergast] 'requests' module not found. Run: pip install requests")

BASE_URL  = "https://api.jolpi.ca/ergast/f1"
CACHE_DIR = Path(".ergast_cache")
CACHE_DIR.mkdir(exist_ok=True)

# Popular circuits mapped to (year, round_number)
CIRCUIT_MAP = {
    "Bahrain 2024":       (2024, 1),
    "Saudi Arabia 2024":  (2024, 2),
    "Australia 2024":     (2024, 3),
    "Japan 2024":         (2024, 4),
    "China 2024":         (2024, 5),
    "Miami 2024":         (2024, 6),
    "Monaco 2024":        (2024, 8),
    "Canada 2024":        (2024, 9),
    "Spain 2024":         (2024, 10),
    "Great Britain 2024": (2024, 12),
    "Hungary 2024":       (2024, 13),
    "Belgium 2024":       (2024, 14),
    "Netherlands 2024":   (2024, 15),
    "Italy/Monza 2024":   (2024, 16),
    "Singapore 2024":     (2024, 18),
    "Abu Dhabi 2024":     (2024, 24),
    "Bahrain 2023":       (2023, 1),
    "Monaco 2023":        (2023, 8),
    "Italy/Monza 2023":   (2023, 15),
}


def parse_lap_time(time_str: str) -> int:
    """Convert '1:24.543' to milliseconds."""
    try:
        if ':' in time_str:
            m, s = time_str.split(':')
            return int((int(m) * 60 + float(s)) * 1000)
        return int(float(time_str) * 1000)
    except Exception:
        return 0


def _cache_path(year: int, round_num: int) -> Path:
    return CACHE_DIR / f"laps_{year}_r{round_num:02d}.json"


def fetch_race_laps(year: int, round_num: int) -> pd.DataFrame:
    """
    Fetch lap time data from the Ergast API with local caching.
    Returns: DataFrame[lap, driver, time_ms, position]
    """
    cache = _cache_path(year, round_num)
    if cache.exists():
        print(f"[ergast] Loaded from cache: {cache.name}")
        with open(cache) as f:
            raw = json.load(f)
        return _parse_laps(raw)

    if not HAS_REQUESTS:
        print("[ergast] 'requests' not available — returning empty DataFrame.")
        return pd.DataFrame()

    all_laps, offset, limit, total_recs = [], 0, 100, None
    print(f"[ergast] Downloading: {year} Round {round_num}")
    while True:
        url = f"{BASE_URL}/{year}/{round_num}/laps.json?limit={limit}&offset={offset}"
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            data   = resp.json()
            mrdata = data.get("MRData", {})
            if total_recs is None:
                total_recs = int(mrdata.get("total", 0))
            races = mrdata.get("RaceTable", {}).get("Races", [])
            if not races:
                break
            laps = races[0].get("Laps", [])
            if not laps:
                break
            all_laps.extend(laps)
            offset += limit
            if offset >= total_recs:
                break
            time.sleep(0.25)
        except Exception as e:
            print(f"[ergast] API error (offset={offset}): {e}")
            break

    raw = {"Laps": all_laps}
    with open(cache, "w") as f:
        json.dump(raw, f)
    print(f"[ergast] {len(all_laps)} lap records downloaded and cached.")
    return _parse_laps(raw)


def _parse_laps(raw: dict) -> pd.DataFrame:
    rows = []
    for lap in raw.get("Laps", []):
        lap_num = int(lap.get("number", 0))
        for timing in lap.get("Timings", []):
            ms = parse_lap_time(timing.get("time", ""))
            if ms > 0:
                rows.append({
                    "lap":      lap_num,
                    "driver":   timing.get("driverId", ""),
                    "time_ms":  ms,
                    "position": int(timing.get("position", 0)),
                })
    df = pd.DataFrame(rows)
    if not df.empty:
        for c in ["lap", "time_ms", "position"]:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
    return df


def get_best_laps_per_driver(df: pd.DataFrame) -> pd.DataFrame:
    """Return the best lap time per driver."""
    if df.empty:
        return df
    return (df.groupby("driver")["time_ms"]
              .min().reset_index()
              .rename(columns={"time_ms": "best_ms"})
              .sort_values("best_ms"))


def get_lap_progression(df: pd.DataFrame, driver: str = None) -> pd.DataFrame:
    """Return lap-by-lap time progression, optionally filtered by driver."""
    if df.empty:
        return df
    if driver:
        df = df[df["driver"] == driver]
    return df.sort_values("lap")


def build_comparison_df(our_best_ms: int, real_df: pd.DataFrame) -> pd.DataFrame:
    """Compare your best lap against real F1 drivers."""
    bests = get_best_laps_per_driver(real_df).copy()
    bests["our_best_ms"] = our_best_ms
    bests["delta_ms"]    = bests["best_ms"] - our_best_ms
    bests["delta_pct"]   = (bests["delta_ms"] / bests["best_ms"] * 100).round(2)
    bests["time_str"]    = bests["best_ms"].apply(
        lambda ms: f"{ms//60000}:{(ms%60000)/1000:06.3f}"
    )
    return bests


def clear_cache():
    """Remove all cached API response files."""
    for f in CACHE_DIR.glob("*.json"):
        f.unlink()
    print("[ergast] Cache cleared.")


if __name__ == "__main__":
    print("Ergast API Test")
    print("Available circuits:", list(CIRCUIT_MAP.keys())[:5], "...")
    df = fetch_race_laps(2024, 16)  # Monza 2024
    if not df.empty:
        print(f"Total lap records: {len(df)}")
        print(get_best_laps_per_driver(df).head(10).to_string())
