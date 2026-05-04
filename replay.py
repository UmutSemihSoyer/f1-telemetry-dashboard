"""
replay.py — F1 2022 Seans Tekrar Oynatma
SQLite'daki session_history veya CSV'den bir seansı geri oynatır.
Kullanim: python replay.py [--session SESSION_ID] [--speed 2.0]
"""
import sqlite3
import json
import time
import argparse
import pandas as pd
from pathlib import Path

REPLAY_FILE = "live_data.json"


def list_sessions() -> list:
    if not Path("telemetry.db").exists():
        return []
    conn = sqlite3.connect("telemetry.db")
    rows = conn.execute(
        "SELECT DISTINCT session_id, COUNT(*) as laps, MIN(lap_time_ms) as best "
        "FROM session_history GROUP BY session_id ORDER BY session_id DESC"
    ).fetchall()
    conn.close()
    return rows


def load_session(session_id: str) -> pd.DataFrame:
    conn = sqlite3.connect("telemetry.db")
    df = pd.read_sql_query(
        "SELECT * FROM session_history WHERE session_id=? ORDER BY lap_num",
        conn, params=(session_id,)
    )
    conn.close()
    for col in ["lap_num", "lap_time_ms", "sector1_ms", "sector2_ms"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    return df


def load_telemetry_csv(csv_path: str) -> pd.DataFrame:
    return pd.read_csv(csv_path)


def replay_session(df: pd.DataFrame, speed: float = 1.0):
    """
    Replays lap rows to live_data.json, simulating real-time pace.
    Each lap row is written as a snapshot with a delay.
    """
    print(f"[REPLAY] {len(df)} tur, hiz x{speed}")
    best_lap_ms = int(df['lap_time_ms'].min()) if not df.empty else 0

    for i, (_, row) in enumerate(df.iterrows(), 1):
        lap_ms = int(row.get('lap_time_ms', 0))
        s1     = int(row.get('sector1_ms', 0))
        s2     = int(row.get('sector2_ms', 0))
        s3     = max(0, lap_ms - s1 - s2)

        # Delta vs best
        delta_s1 = s1 - best_lap_ms * 0.33
        delta_s2 = s2 - best_lap_ms * 0.35
        delta_s3 = s3 - best_lap_ms * 0.32
        total_delta = lap_ms - best_lap_ms

        def sector_color(delta):
            if delta < -50:   return "purple"
            elif delta < 0:   return "green"
            else:             return "red"

        snapshot = [{
            "Speed":       200,
            "RPM":       8000,
            "Throttle":       0.8,
            "Brake":      0.0,
            "LapNum":    int(row.get('lap_num', i)),
            "LapTime":   lap_ms / 1000.0,
            "Sector1":   s1,
            "Sector2":   s2,
            "Sector3":   s3,
            "DeltaS1":   round(delta_s1, 0),
            "DeltaS2":   round(delta_s2, 0),
            "DeltaS3":   round(delta_s3, 0),
            "DeltaTotal":round(total_delta, 0),
            "ColorS1":   sector_color(delta_s1),
            "ColorS2":   sector_color(delta_s2),
            "ColorS3":   sector_color(delta_s3),
            "Timestamp": time.time(),
            "REPLAY":    True,
        }]

        with open(REPLAY_FILE, "w") as f:
            json.dump(snapshot, f)

        lap_t_s = lap_ms / 1000.0
        print(f"  Tur {int(row.get('lap_num',i)):3d} | {lap_t_s:.3f}s | "
              f"S1:{s1}ms S2:{s2}ms S3:{s3}ms | Delta:{total_delta:+d}ms")

        # Simulate time between laps (scaled by speed)
        sleep_s = min(2.0, lap_t_s / 45.0) / speed
        time.sleep(sleep_s)

    print("[REPLAY] Tamamlandi.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="F1 2022 Session Replay")
    parser.add_argument("--session", default=None, help="Session ID (default: latest)")
    parser.add_argument("--speed",   type=float, default=2.0, help="Replay speed multiplier")
    parser.add_argument("--csv",     default=None, help="Optional: replay from a CSV file")
    args = parser.parse_args()

    if args.csv:
        df = load_telemetry_csv(args.csv)
        replay_session(df, speed=args.speed)
    else:
        sessions = list_sessions()
        if not sessions:
            print("[REPLAY] Veritabaninda seans yok. Once 'python run_all.py' calistirin.")
        else:
            print("\nMevcut Seanslar:")
            print(f"{'ID':<25} {'Turlar':>6} {'En Hizli (ms)':>14}")
            print("-" * 50)
            for sid, laps, best in sessions:
                print(f"{sid:<25} {laps:>6} {best:>14}")

            target = args.session or sessions[0][0]
            print(f"\n[REPLAY] Seans oynatuluyor: {target} (x{args.speed})")
            df = load_session(target)
            if df.empty:
                print(f"[REPLAY] Seans bulunamadi: {target}")
            else:
                replay_session(df, speed=args.speed)
