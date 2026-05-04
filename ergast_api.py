"""
ergast_api.py — Gercek F1 Verisi (Jolpi Ergast API)
Fetch ve karsilastir: Senin turların vs gercek F1 pilotlari.

Kullanim:
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
    print("[ergast] requests modulu yok. pip install requests")

BASE_URL  = "https://api.jolpi.ca/ergast/f1"
CACHE_DIR = Path(".ergast_cache")
CACHE_DIR.mkdir(exist_ok=True)

# Populer pisler icin (yil, tur) eslesmeleri
CIRCUIT_MAP = {
    "Bahrain 2024":           (2024, 1),
    "Saudi Arabia 2024":      (2024, 2),
    "Australia 2024":         (2024, 3),
    "Japan 2024":             (2024, 4),
    "China 2024":             (2024, 5),
    "Miami 2024":             (2024, 6),
    "Monaco 2024":            (2024, 8),
    "Canada 2024":            (2024, 9),
    "Spain 2024":             (2024, 10),
    "Great Britain 2024":     (2024, 12),
    "Hungary 2024":           (2024, 13),
    "Belgium 2024":           (2024, 14),
    "Netherlands 2024":       (2024, 15),
    "Italy/Monza 2024":       (2024, 16),
    "Singapore 2024":         (2024, 18),
    "Abu Dhabi 2024":         (2024, 24),
    # 2023
    "Bahrain 2023":           (2023, 1),
    "Monaco 2023":            (2023, 8),
    "Italy/Monza 2023":       (2023, 15),
}


def parse_lap_time(time_str: str) -> int:
    """'1:24.543' → millisaniye"""
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
    Ergast API'den yaris tur zaman verilerini cek.
    Var olan sonuclar cache'den yuklenir.
    Returns: DataFrame[lap, driver, time_ms, position]
    """
    cache = _cache_path(year, round_num)
    if cache.exists():
        print(f"[ergast] Cache'den yuklendi: {cache.name}")
        with open(cache) as f:
            raw = json.load(f)
        return _parse_laps(raw)

    if not HAS_REQUESTS:
        print("[ergast] requests yok, bos DataFrame donduruluyor.")
        return pd.DataFrame()

    all_laps   = []
    offset     = 0
    limit      = 100
    total_recs = None

    print(f"[ergast] Veri indiriliyor: {year} Round {round_num}")
    while True:
        url = f"{BASE_URL}/{year}/{round_num}/laps.json?limit={limit}&offset={offset}"
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            data     = resp.json()
            mrdata   = data.get("MRData", {})
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
            print(f"[ergast] API hatasi (offset={offset}): {e}")
            break

    raw = {"Laps": all_laps}
    with open(cache, "w") as f:
        json.dump(raw, f)
    print(f"[ergast] {len(all_laps)} tur verisi indirildi ve cache'e yazildi.")
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
        for c in ["lap","time_ms","position"]:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
    return df


def get_best_laps_per_driver(df: pd.DataFrame) -> pd.DataFrame:
    """Her pilot icin en iyi tur suresi."""
    if df.empty:
        return df
    return (df.groupby("driver")["time_ms"]
              .min()
              .reset_index()
              .rename(columns={"time_ms": "best_ms"})
              .sort_values("best_ms"))


def get_lap_progression(df: pd.DataFrame, driver: str = None) -> pd.DataFrame:
    """Bir pilotun tur bazli zaman seyrini getir."""
    if df.empty:
        return df
    if driver:
        df = df[df["driver"] == driver]
    return df.sort_values("lap")


def build_comparison_df(our_best_ms: int, real_df: pd.DataFrame) -> pd.DataFrame:
    """
    Kendi en iyi turunu gercek F1 pilotlariyla karsilastir.
    Returns: DataFrame with delta_ms, delta_pct columns.
    """
    bests = get_best_laps_per_driver(real_df).copy()
    bests["our_best_ms"] = our_best_ms
    bests["delta_ms"]    = bests["best_ms"] - our_best_ms
    bests["delta_pct"]   = (bests["delta_ms"] / bests["best_ms"] * 100).round(2)
    bests["time_str"]    = bests["best_ms"].apply(
        lambda ms: f"{ms//60000}:{(ms%60000)/1000:06.3f}"
    )
    return bests


def clear_cache():
    """Tum cache dosyalarini temizle."""
    for f in CACHE_DIR.glob("*.json"):
        f.unlink()
    print("[ergast] Cache temizlendi.")


if __name__ == "__main__":
    print("Ergast API Testi")
    print("Mevcut pisler:", list(CIRCUIT_MAP.keys())[:5], "...")
    df = fetch_race_laps(2024, 16)  # Monza 2024
    if not df.empty:
        print(f"Toplam tur kaydi: {len(df)}")
        best = get_best_laps_per_driver(df)
        print(best.head(10).to_string())
