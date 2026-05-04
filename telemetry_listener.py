import socket
import struct
import logging
import json
import numpy as np
import pandas as pd
import threading
import queue
import sqlite3
import time

# ====================================================
# V7 CONFIG
# ====================================================
with open("config.json") as f:
    CONFIG = json.load(f)

UDP_IP   = CONFIG["network"]["UDP_IP"]
UDP_PORT = CONFIG["network"]["UDP_PORT"]
BUFFER_LIMIT = CONFIG["listener"]["BUFFER_LIMIT"]

HEADER_FORMAT       = CONFIG["structs"]["HEADER_FORMAT"]
HEADER_SIZE         = struct.calcsize(HEADER_FORMAT)

# Paket formatları
CAR_DATA_SHORT      = CONFIG["structs"]["CAR_TELEMETRY_FORMAT"]   # 18-byte quick parse
CAR_DATA_FULL       = CONFIG["structs"]["CAR_TELEMETRY_FULL_FORMAT"]  # 60-byte full
LAP_DATA_FORMAT     = CONFIG["structs"]["LAP_DATA_FORMAT"]
DAMAGE_DATA_FORMAT  = CONFIG["structs"]["DAMAGE_DATA_FORMAT"]
CAR_MOTION_FORMAT   = CONFIG["structs"]["CAR_MOTION_FORMAT"]
CAR_STATUS_FORMAT   = CONFIG["structs"]["CAR_STATUS_FORMAT"]
SESSION_PREFIX_FMT  = CONFIG["structs"]["SESSION_PREFIX_FORMAT"]  # first ~18 bytes of session

PKT         = CONFIG["packet_sizes"]
ALERT_CFG   = CONFIG["alerts"]

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TelemetryListener")

# Voice uyarı modülü
from voice_alerts import (start_voice_thread,
                          alert_tyre_critical, alert_tyre_warn,
                          alert_ers_critical, alert_fuel_critical, alert_fuel_warn,
                          alert_engine, alert_safety_car, alert_weather_change,
                          radio_sector_purple, radio_fastest_lap, radio_box_box,
                          radio_pit_window_open, radio_save_fuel, radio_save_tyres,
                          radio_compound_advice, radio_engineer_feedback)
from ml_analysis import run_braking_analysis_and_save
from race_engineer import generate_lap_feedback

telemetry_queue = queue.Queue()

# State için globaller
_last_lap_num    = 0
_prev_weather    = -1

# ====================================================
# VERİTABANI
# ====================================================
def init_db():
    conn = sqlite3.connect('telemetry.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS braking_zones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_time REAL, entry_speed REAL, exit_speed REAL,
        duration REAL, max_pressure REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS lap_times (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT DEFAULT 'default',
        lap_num INTEGER, sector1_ms INTEGER, sector2_ms INTEGER,
        lap_time_ms INTEGER, timestamp REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS session_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT, lap_num INTEGER, lap_time_ms INTEGER,
        sector1_ms INTEGER, sector2_ms INTEGER, timestamp REAL)''')
    conn.commit()
    # Migration: add session_id column to old DBs that don't have it
    try:
        c.execute("ALTER TABLE lap_times ADD COLUMN session_id TEXT DEFAULT 'default'")
        conn.commit()
    except Exception:
        pass  # Column already exists
    conn.close()


def save_braking_zone(session_time, entry_speed, exit_speed, duration, max_pressure):
    try:
        conn = sqlite3.connect('telemetry.db')
        conn.execute('INSERT INTO braking_zones (session_time,entry_speed,exit_speed,duration,max_pressure) VALUES(?,?,?,?,?)',
                     (session_time, entry_speed, exit_speed, duration, max_pressure))
        conn.commit(); conn.close()
    except Exception as e:
        logger.error(f"DB braking_zones: {e}")


def save_lap_time(lap_num, s1, s2, total, ts):
    try:
        session_id = time.strftime("%Y%m%d_%H%M00")  # hourly session ID
        conn = sqlite3.connect('telemetry.db')
        conn.execute('INSERT INTO lap_times (session_id,lap_num,sector1_ms,sector2_ms,lap_time_ms,timestamp) VALUES(?,?,?,?,?,?)',
                     (session_id, lap_num, s1, s2, total, ts))
        # Session history için de kaydet
        conn.execute('INSERT INTO session_history (session_id,lap_num,lap_time_ms,sector1_ms,sector2_ms,timestamp) VALUES(?,?,?,?,?,?)',
                     (session_id, lap_num, total, s1, s2, ts))
        conn.commit(); conn.close()
        logger.info(f"[LAP] Lap {lap_num} | S1:{s1}ms S2:{s2}ms Total:{total}ms")
    except Exception as e:
        logger.error(f"DB lap_times: {e}")

# ====================================================
# ANALİZ FONKSİYONLARI
# ====================================================
def analyze_braking_zones(df):
    if df.empty or 'Brake' not in df.columns:
        return []
    is_braking = df['Brake'] > 0.05
    groups     = (is_braking != is_braking.shift()).cumsum()
    events     = df[is_braking].groupby(groups)
    leftover   = []
    last_idx   = df.index[-1]
    for _, ev in events:
        if ev.index[-1] == last_idx:
            leftover = df.loc[ev.index[0]:].to_dict('records'); continue
        entry = ev['Speed'].iloc[0]; exit_ = ev['Speed'].iloc[-1]
        mp    = ev['Brake'].max() * 100
        dur   = ev['Timestamp'].iloc[-1] - ev['Timestamp'].iloc[0]
        save_braking_zone(ev['Timestamp'].iloc[0], entry, exit_, dur, mp)
    return leftover


def predict_pit_stop(wear_history, fuel_laps):
    try:
        if len(wear_history) < 5:
            return None
        x = np.arange(len(wear_history))
        slope, intercept = np.polyfit(x, np.array(wear_history), 1)
        if slope <= 0: return 99
        laps_to_crit = int((ALERT_CFG["TYRE_CRIT_PCT"] - wear_history[-1]) / (slope * BUFFER_LIMIT / 10))
        return max(0, min(laps_to_crit, int(fuel_laps) if fuel_laps else 99))
    except Exception:
        return None


def check_alerts(df, latest_status, latest_damage):
    global _prev_weather
    alerts = []
    if latest_damage:
        wear_max = max(latest_damage.get('TyreWearFL', 0), latest_damage.get('TyreWearFR', 0),
                       latest_damage.get('TyreWearRL', 0), latest_damage.get('TyreWearRR', 0))
        if wear_max > ALERT_CFG["TYRE_CRIT_PCT"]:
            alerts.append({"level":"critical","icon":"⚠️","msg":f"Tyre Critical! %{wear_max:.1f}"})
            alert_tyre_critical(wear_max)
        elif wear_max > ALERT_CFG["TYRE_WARN_PCT"]:
            alerts.append({"level":"warning","icon":"🟡","msg":f"Tyre Wear %{wear_max:.1f}"})
            alert_tyre_warn(wear_max)
        eng = latest_damage.get('EngineDamage', 0)
        if eng > ALERT_CFG["ENGINE_CRIT_PCT"]:
            alerts.append({"level":"critical","icon":"🚨","msg":f"Engine Damage: %{eng}"})
            alert_engine(eng)

    if latest_status:
        ers = latest_status.get('ERS', 0)
        ers_pct = (ers / 4_000_000) * 100
        if ers < ALERT_CFG["ERS_CRIT_J"]:
            alerts.append({"level":"critical","icon":"🔋","msg":f"ERS Critical: %{ers_pct:.1f}"})
            alert_ers_critical(ers_pct)
        elif ers < ALERT_CFG["ERS_WARN_J"]:
            alerts.append({"level":"warning","icon":"🔋","msg":f"ERS Low: %{ers_pct:.1f}"})
        fuel_laps = latest_status.get('FuelLaps', 99)
        if fuel_laps < ALERT_CFG["FUEL_CRIT_LAPS"]:
            alerts.append({"level":"critical","icon":"⛽","msg":f"Fuel Critical! {fuel_laps:.1f} laps"})
            alert_fuel_critical(fuel_laps)
        elif fuel_laps < ALERT_CFG["FUEL_WARN_LAPS"]:
            alerts.append({"level":"warning","icon":"⛽","msg":f"Fuel Warning {fuel_laps:.1f} laps"})
            alert_fuel_warn(fuel_laps)

    try:
        with open("alerts.json", "w") as f:
            json.dump(alerts, f)
    except Exception:
        pass

# ====================================================
# ANALİTİK İŞÇİ
# ====================================================
def compound_advisor(wear_pct: float, tyre_age: int, weather: int, fuel_laps: float) -> str:
    """
    Lastik compound tavsiyesi:
    - Yagmurda: Wet/Inter
    - Yuksek asınma: Hard
    - Orta: Medium
    - Dusuk: Soft (hiz icin)
    """
    if weather >= 3:
        return "Intermediate" if weather == 3 else "Wet"
    if wear_pct > 60 or tyre_age > 25:
        return "Hard"
    elif wear_pct > 30 or tyre_age > 15:
        return "Medium"
    else:
        return "Soft"


def analytics_worker():
    global _last_lap_num
    logger.info("Analytics thread started.")

    telemetry_buffer = []
    lap_buffer       = []
    damage_buffer    = []
    motion_buffer    = []
    status_buffer    = []
    session_buffer   = []
    competitor_buffer= []
    wear_history     = []
    ml_counter       = 0

    # Delta time state: track best sectors across entire session
    best_s1 = float('inf')
    best_s2 = float('inf')
    best_lap_ms = float('inf')
    prev_compound = None
    
    # V10: Virtual Race Engineer Lap State
    full_lap_df_buffer = []
    pb_df_cache = None

    while True:
        try:
            item   = telemetry_queue.get(timeout=1.0)
            p_type = item.get('Type', 'Telemetry')

            if p_type == 'Telemetry':
                telemetry_buffer.append(item)
            elif p_type == 'LapData':
                lap_buffer.append(item)
                lap_num = item.get('CurrentLapNum', 0)
                if lap_num != _last_lap_num and _last_lap_num > 0:
                    last_lap_ms = item.get('LastLapTimeMS', 0)
                    save_lap_time(_last_lap_num,
                                  item.get('Sector1MS', 0),
                                  item.get('Sector2MS', 0),
                                  last_lap_ms,
                                  item.get('Timestamp', 0))
                    
                    # V10: Trigger Race Engineer Analysis on Lap Completion
                    if full_lap_df_buffer:
                        # Concatenate all 100-row chunks captured during this lap
                        current_lap_df = pd.concat(full_lap_df_buffer, ignore_index=True)
                        full_lap_df_buffer.clear()
                        
                        if not current_lap_df.empty:
                            # Feed the lap to the Virtual Engineer
                            feedback_report = generate_lap_feedback(current_lap_df, pb_df_cache)
                            
                            # Write to file for the Dashboard
                            try:
                                with open("engineer_feedback.json", "w", encoding="utf-8") as f:
                                    json.dump(feedback_report, f)
                            except Exception as e:
                                logger.error(f"Failed to save engineer feedback: {e}")
                                
                            # Voice the most critical feedback if any exists
                            if feedback_report.get("priority_alert"):
                                radio_engineer_feedback(feedback_report["priority_alert"])
                                
                            # If this was a valid Personal Best lap (or the very first valid lap)
                            if last_lap_ms > 0 and (pb_df_cache is None or last_lap_ms <= best_lap_ms):
                                pb_df_cache = current_lap_df.copy()
                                
                _last_lap_num = lap_num
            elif p_type == 'Damage':
                damage_buffer.append(item)
            elif p_type == 'Motion':
                motion_buffer.append(item)
            elif p_type == 'Status':
                status_buffer.append(item)
            elif p_type == 'Session':
                session_buffer.append(item)
            elif p_type == 'Competitors':
                competitor_buffer.append(item)

            if len(telemetry_buffer) >= BUFFER_LIMIT:
                df = pd.DataFrame(telemetry_buffer)
                
                # V10: Store DF block into full lap buffer
                full_lap_df_buffer.append(df.copy())

                latest_lap    = lap_buffer[-1]    if lap_buffer    else None
                latest_dmg    = damage_buffer[-1] if damage_buffer else None
                latest_mot    = motion_buffer[-1] if motion_buffer else None
                latest_status = status_buffer[-1] if status_buffer else None
                latest_sess   = session_buffer[-1] if session_buffer else None
                latest_comp   = competitor_buffer[-1] if competitor_buffer else None

                # Tur verisi
                df['LapNum']  = latest_lap['CurrentLapNum']      if latest_lap else 0
                df['LapTime'] = latest_lap['CurrentLapTimeMS'] / 1000.0 if latest_lap else 0.0
                df['Sector1'] = latest_lap['Sector1MS']           if latest_lap else 0
                df['Sector2'] = latest_lap['Sector2MS']           if latest_lap else 0

                # Hasar (Wear ve Engine damage) - from Damage packet
                for field in ['WearFL','WearFR','WearRL','WearRR','EngineDamage']:
                    df[field] = latest_dmg.get(field, 0) if latest_dmg else 0

                # Tire temps, DRS, EngineTemp are already columns in df (from Telemetry rows)
                # Just fill NaN/missing with 0 in case older buffered rows lack them
                for field in ['BrakeTempFL','BrakeTempFR','BrakeTempRL','BrakeTempRR',
                               'TyreSurfFL','TyreSurfFR','TyreSurfRL','TyreSurfRR',
                               'TyreInnerFL','TyreInnerFR','TyreInnerRL','TyreInnerRR',
                               'DRS','EngineTemp']:
                    if field not in df.columns:
                        df[field] = 0

                # Motion
                df['PosX'] = latest_mot['PosX'] if latest_mot else 0.0
                df['PosZ'] = latest_mot['PosZ'] if latest_mot else 0.0
                df['GLat'] = latest_mot['GLat'] if latest_mot else 0.0
                df['GLon'] = latest_mot['GLon'] if latest_mot else 0.0

                # Status
                df['Fuel']     = latest_status['Fuel']     if latest_status else 0.0
                df['FuelLaps'] = latest_status['FuelLaps'] if latest_status else 0.0
                df['ERS']      = latest_status['ERS']      if latest_status else 0.0
                df['TyreAge']  = latest_status['TyreAge']  if latest_status else 0

                # Session (Hava, Bayrak, Sıcaklık)
                if latest_sess:
                    df['Weather']      = latest_sess.get('Weather', 0)
                    df['TrackTemp']    = latest_sess.get('TrackTemp', 0)
                    df['AirTemp']      = latest_sess.get('AirTemp', 0)
                    df['SafetyCar']    = latest_sess.get('SafetyCarStatus', 0)
                    df['SessionTime']  = latest_sess.get('SessionTimeLeft', 0)
                else:
                    df['Weather'] = df['TrackTemp'] = df['AirTemp'] = df['SafetyCar'] = df['SessionTime'] = 0

                # Rakip Boşlukları
                df['GapAhead']  = latest_comp.get('GapAhead', 0.0)  if latest_comp else 0.0
                df['GapBehind'] = latest_comp.get('GapBehind', 0.0) if latest_comp else 0.0
                df['CarPosition'] = latest_comp.get('CarPosition', 0) if latest_comp else 0

                # ── Pit Tahmini
                if latest_dmg:
                    wear_now = max(latest_dmg.get('TyreWearFL', 0), latest_dmg.get('TyreWearFR', 0))
                    wear_history.append(wear_now)
                    if len(wear_history) > 20:
                        wear_history.pop(0)
                pit_pred = predict_pit_stop(wear_history, df['FuelLaps'].iloc[-1])
                df['PitPrediction'] = pit_pred if pit_pred is not None else -1

                # ── Delta Time (Purple / Green / Red Sektor)
                s1  = int(df['Sector1'].iloc[-1]) if 'Sector1' in df.columns else 0
                s2  = int(df['Sector2'].iloc[-1]) if 'Sector2' in df.columns else 0
                lap_t_ms = int(df['LapTime'].iloc[-1] * 1000) if 'LapTime' in df.columns else 0
                s3  = max(0, lap_t_ms - s1 - s2)

                def _sector_color(val, best):
                    if best == float('inf') or best == 0: return 'yellow'
                    d = val - best
                    if d < -50:  return 'purple'
                    if d < 0:    return 'green'
                    return 'red'

                if s1 > 100:
                    if s1 < best_s1:
                        if best_s1 != float('inf'): radio_sector_purple(1)
                        best_s1 = s1
                    if s2 < best_s2:
                        if best_s2 != float('inf'): radio_sector_purple(2)
                        best_s2 = s2
                    if lap_t_ms > 0 and lap_t_ms < best_lap_ms:
                        if best_lap_ms != float('inf'): radio_fastest_lap()
                        best_lap_ms = lap_t_ms

                df['DeltaS1']    = s1 - best_s1 if best_s1 != float('inf') else 0
                df['DeltaS2']    = s2 - best_s2 if best_s2 != float('inf') else 0
                df['DeltaTotal'] = lap_t_ms - best_lap_ms if best_lap_ms != float('inf') else 0
                df['ColorS1']   = _sector_color(s1, best_s1)
                df['ColorS2']   = _sector_color(s2, best_s2)
                df['BestLapMs'] = int(best_lap_ms) if best_lap_ms != float('inf') else 0

                # ── Compound Tavsiyesi
                wear_avg   = sum(wear_history) / len(wear_history) if wear_history else 0
                tyre_age   = int(df['TyreAge'].iloc[-1]) if 'TyreAge' in df.columns else 0
                weather_v  = int(df['Weather'].iloc[-1]) if 'Weather' in df.columns else 0
                fuel_laps_v= float(df['FuelLaps'].iloc[-1]) if 'FuelLaps' in df.columns else 99
                compound   = compound_advisor(wear_avg, tyre_age, weather_v, fuel_laps_v)
                df['CompoundAdvisor'] = compound

                if compound != prev_compound and prev_compound is not None:
                    reason = "Rain detected." if weather_v >= 3 else f"Wear {wear_avg:.0f}%, Age {tyre_age}L."
                    radio_compound_advice(compound, reason)
                prev_compound = compound

                # ── Radio: Pit window + Fuel save
                if pit_pred is not None and 1 <= pit_pred <= 3:
                    radio_box_box()
                if fuel_laps_v < 5:
                    radio_save_fuel()

                # ── Fren Noktaları Overlay
                brake_pts = df[df['Brake'] > 0.8][['PosX','PosZ','Speed']].to_dict('records')
                if brake_pts:
                    try:
                        import os
                        existing = []
                        if os.path.exists("braking_points.json"):
                            with open("braking_points.json") as f:
                                existing = json.load(f)
                        combined = (existing + brake_pts)[-2000:]
                        with open("braking_points.json", "w") as f:
                            json.dump(combined, f)
                        ml_counter += 1
                        if ml_counter % 10 == 0:
                            threading.Thread(target=run_braking_analysis_and_save, daemon=True).start()
                    except Exception as e:
                        logger.error(f"braking_points: {e}")

                # ── Uyarı Sistemi
                check_alerts(df, latest_status, latest_dmg)

                # Competitor gap JSON
                if latest_comp:
                    try:
                        with open("competitors.json", "w") as f:
                            json.dump(latest_comp.get('Leaderboard', []), f)
                    except Exception:
                        pass

                # IPC JSON
                try:
                    df.to_json("live_data.json", orient="records")
                except Exception as e:
                    logger.error(f"live_data.json: {e}")

                print(f"[SYS] Lap:{df['LapNum'].iloc[-1]} | Spd:{df['Speed'].mean():.0f}km/h | "
                      f"Pit:{pit_pred} | Weather:{df['Weather'].iloc[-1]} | "
                      f"Pos:{df['CarPosition'].iloc[-1]}")

                telemetry_buffer = analyze_braking_zones(df)
                if not telemetry_buffer: telemetry_buffer.clear()
                lap_buffer.clear(); damage_buffer.clear()
                motion_buffer.clear(); status_buffer.clear()
                session_buffer.clear(); competitor_buffer.clear()

            telemetry_queue.task_done()
        except queue.Empty:
            continue
        except Exception as e:
            logger.error(f"Analytics worker error: {e}")

# ====================================================
# UDP DİNLEYİCİ
# ====================================================
def udp_listener():
    global _prev_weather
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind((UDP_IP, UDP_PORT))
    except Exception as e:
        logger.error(f"Socket connection error: {e}"); return

    print(f"Connected to F1 2022 V7 Main Grid. Port:{UDP_PORT}")

    while True:
        try:
            data, _ = sock.recvfrom(4096)
            if len(data) < HEADER_SIZE: continue
            header = struct.unpack(HEADER_FORMAT, data[:HEADER_SIZE])
            packet_id    = header[4]
            session_time = header[6]
            player_idx   = header[8]

            # ---- PAKET 6: TAM TELEMETRİ (60 byte) ----
            if packet_id == PKT["TELEMETRY_ID"] and len(data) == PKT["TELEMETRY_SIZE"]:
                start = 24 + (player_idx * 60)
                u = struct.unpack(CAR_DATA_FULL, data[start:start+60])
                # Sıcaklık array indeksleri: u[10-13]=brakesTemp, u[14-17]=tyresSurf, u[18-21]=tyresInner
                # u[22]=engineTemp, u[23-26]=tyresPressure
                # FL=0, FR=1, RL=2, RR=3 (F1 2022 array order: RL,RR,FL,FR → check spec carefully)
                # Spec: [rear_left, rear_right, front_left, front_right]
                telemetry_queue.put({
                    'Type':'Telemetry', 'Timestamp':session_time,
                    'Speed':u[0], 'Throttle':u[1], 'Brake':u[3], 'Gear':u[5], 'RPM':u[6],
                    'DRS': u[7],
                    'BrakeTempRL':u[10], 'BrakeTempRR':u[11], 'BrakeTempFL':u[12], 'BrakeTempFR':u[13],
                    'TyreSurfRL':u[14], 'TyreSurfRR':u[15], 'TyreSurfFL':u[16], 'TyreSurfFR':u[17],
                    'TyreInnerRL':u[18], 'TyreInnerRR':u[19], 'TyreInnerFL':u[20], 'TyreInnerFR':u[21],
                    'EngineTemp':u[22],
                })

            # ---- PAKET 2: TUR VERİSİ + RAKİP GAPLER ----
            elif packet_id == PKT["LAP_DATA_ID"] and len(data) == PKT["LAP_DATA_SIZE"]:
                # Oyuncu
                start = 24 + (player_idx * 43)
                u = struct.unpack(LAP_DATA_FORMAT, data[start:start+43])
                telemetry_queue.put({
                    'Type':'LapData', 'Timestamp':session_time,
                    'LastLapTimeMS':u[0], 'CurrentLapTimeMS':u[1],
                    'Sector1MS':u[2], 'Sector2MS':u[3],
                    'CurrentLapNum':u[8], 'Penalties':u[13]
                })
                # Tüm 22 araç için liderboard
                leaderboard = []
                player_pos  = 0
                player_lap_ms = u[1]
                for i in range(22):
                    cs = 24 + (i * 43)
                    try:
                        cu = struct.unpack(LAP_DATA_FORMAT, data[cs:cs+43])
                        lap_n = cu[8]; lap_ms = cu[1]; pos = cu[9]  # carPosition at index ~9
                        if i == player_idx:
                            player_pos = pos
                        leaderboard.append({'car': i, 'lap': lap_n, 'lapTimeMS': lap_ms, 'pos': pos})
                    except struct.error:
                        break
                leaderboard.sort(key=lambda x: x.get('pos', 99))
                # Gap hesabı: oyuncunun önündekileri bul
                gap_ahead  = 0.0
                gap_behind = 0.0
                for entry in leaderboard:
                    if entry['car'] == player_idx: continue
                    diff = (player_lap_ms - entry['lapTimeMS']) / 1000.0
                    if diff > 0 and gap_ahead == 0.0:
                        gap_ahead = diff  # oyuncudan kısa tur zamanı = önde
                    elif diff < 0:
                        gap_behind = abs(diff)
                        break
                telemetry_queue.put({
                    'Type':'Competitors', 'Timestamp':session_time,
                    'CarPosition':player_pos,
                    'GapAhead': gap_ahead,
                    'GapBehind': gap_behind,
                    'Leaderboard': leaderboard
                })

            # ---- PAKET 10: ARAÇ HASARI ----
            elif packet_id == PKT["DAMAGE_ID"] and len(data) == PKT["DAMAGE_SIZE"]:
                start = 24 + (player_idx * 42)
                u = struct.unpack(DAMAGE_DATA_FORMAT, data[start:start+42])
                telemetry_queue.put({
                    'Type':'Damage', 'Timestamp':session_time,
                    'TyreWearRL':u[0],'TyreWearRR':u[1],'TyreWearFL':u[2],'TyreWearFR':u[3],
                    'EngineDamage':u[21]
                })

            # ---- PAKET 0: HAREKET VERİSİ ----
            elif packet_id == PKT["MOTION_ID"] and len(data) == PKT["MOTION_SIZE"]:
                start = 24 + (player_idx * 60)
                u = struct.unpack(CAR_MOTION_FORMAT, data[start:start+60])
                telemetry_queue.put({'Type':'Motion','Timestamp':session_time,
                    'PosX':u[0],'PosZ':u[2],'GLat':u[12],'GLon':u[13]})

            # ---- PAKET 7: ARAÇ DURUMU ----
            elif packet_id == PKT["STATUS_ID"] and len(data) == PKT["STATUS_SIZE"]:
                start = 24 + (player_idx * 47)
                u = struct.unpack(CAR_STATUS_FORMAT, data[start:start+47])
                telemetry_queue.put({'Type':'Status','Timestamp':session_time,
                    'Fuel':u[5],'FuelLaps':u[7],'ERS':u[17],'ERSMode':u[18],'TyreAge':u[15]})

            elif packet_id == PKT["SESSION_ID"] and len(data) == PKT["SESSION_SIZE"]:
                sess_prefix_size = struct.calcsize(SESSION_PREFIX_FMT)
                u = struct.unpack(SESSION_PREFIX_FMT, data[24:24+sess_prefix_size])
                # safetyCarStatus at offset: header(24) + prefix + marshal zones(21*5)
                safety_offset = 24 + sess_prefix_size + (21 * 5)
                safety = struct.unpack_from('<B', data, safety_offset)[0]
                weather = u[0]
                if weather != _prev_weather and _prev_weather >= 0:
                    alert_weather_change(weather)
                _prev_weather = weather
                if safety > 0:
                    alert_safety_car(safety)
                telemetry_queue.put({
                    'Type':'Session', 'Timestamp':session_time,
                    'Weather':weather, 'TrackTemp':u[1],
                    'AirTemp':u[2], 'TotalLaps':u[3],
                    'SessionType':u[5], 'SessionTimeLeft':u[8],
                    'SafetyCarStatus':safety
                })

        except struct.error as e:
            logger.warning(f"Packet error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")


if __name__ == "__main__":
    init_db()
    start_voice_thread()
    threading.Thread(target=analytics_worker, daemon=True).start()
    udp_listener()
