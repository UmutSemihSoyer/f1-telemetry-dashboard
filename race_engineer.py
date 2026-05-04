"""
race_engineer.py — F1 2022 Virtual Race Engineer
Analyzes telemetry to provide actionable feedback on:
- Corner by corner micro-sectors
- Trail braking smoothness
- Ideal shifting
- Coasting (dead time)
- Setup suggestions
"""
import numpy as np
import pandas as pd

from analytics_physics import calculate_slipstream_advantage

def split_into_micro_sectors(df, min_speed_dip=15):
    """
    Identifies corners by finding local minimums in speed.
    Returns a list of corner dictionaries containing entry, apex, and exit indices.
    """
    corners = []
    # Smooth the speed a bit to avoid micro-fluctuations
    if "Speed" not in df.columns or len(df) < 50:
        return corners
        
    speed = df["Speed"].rolling(window=5, center=True).mean().fillna(df["Speed"])
    
    # Simple algorithm: find troughs (minimums) surrounded by higher speeds
    troughs = []
    for i in range(10, len(speed) - 10):
        if speed.iloc[i] < speed.iloc[i-5] and speed.iloc[i] < speed.iloc[i+5]:
            # Check if this is a significant dip (a real corner)
            local_max_before = speed.iloc[max(0, i-50):i].max()
            if local_max_before - speed.iloc[i] > min_speed_dip:
                # To avoid duplicate troughs for the same corner, check distance to last
                if not troughs or i - troughs[-1] > 30:
                    troughs.append(i)
                    
    # Build complete corner structures (entry, apex, exit)
    for apex_idx in troughs:
        # Trace back to find where braking started
        entry_idx = apex_idx
        while entry_idx > 0 and df["Brake"].iloc[entry_idx-1] > 0.05:
            entry_idx -= 1
            
        # Trace forward to find where throttle reached 95%+
        exit_idx = apex_idx
        while exit_idx < len(df) - 1 and df["Throttle"].iloc[exit_idx] < 0.95:
            exit_idx += 1
            
        corners.append({
            "entry_idx": entry_idx,
            "apex_idx": apex_idx,
            "exit_idx": exit_idx,
            "dist_entry": df["LapDistance"].iloc[entry_idx] if "LapDistance" in df else 0,
            "dist_apex": df["LapDistance"].iloc[apex_idx] if "LapDistance" in df else 0,
            "v_min": df["Speed"].iloc[apex_idx]
        })
        
    return corners

def analyze_corners(current_df, pb_df):
    """
    Compares current lap corners vs PB lap corners.
    Returns a list of feedback strings.
    """
    if current_df is None or pb_df is None or current_df.empty or pb_df.empty:
        return []
        
    current_corners = split_into_micro_sectors(current_df)
    pb_corners = split_into_micro_sectors(pb_df)
    
    feedback = []
    
    # Match corners by distance
    for i, c_curr in enumerate(current_corners):
        # Find matching corner in PB
        matching_pb = None
        for c_pb in pb_corners:
            if abs(c_curr["dist_apex"] - c_pb["dist_apex"]) < 100:  # Within 100m
                matching_pb = c_pb
                break
                
        if matching_pb:
            turn_name = f"Turn {i+1}"
            
            # 1. Brake Point Analysis
            brake_diff = matching_pb["dist_entry"] - c_curr["dist_entry"]
            if brake_diff > 15: # Braked 15m earlier than PB
                feedback.append(f"{turn_name}: Frene {brake_diff:.0f} metre daha ERKEN bastin. Daha geç frenlemeyi dene.")
            elif brake_diff < -15:
                feedback.append(f"{turn_name}: Frene {abs(brake_diff):.0f} metre GEÇ bastin, apex'i kaçirmiş olabilirsin.")
                
            # 2. Minimum Speed Analysis
            speed_diff = matching_pb["v_min"] - c_curr["v_min"]
            if speed_diff > 5: # 5 km/h slower at apex
                feedback.append(f"{turn_name}: Apex hizin {speed_diff:.0f} km/h DÜŞÜK. Viraj içine daha fazla hiz taşimaya çaliş.")
                
            # 3. Throttle Application Analysis
            # Compare time/distance from apex to full throttle
            dist_to_throttle_curr = current_df["LapDistance"].iloc[c_curr["exit_idx"]] - c_curr["dist_apex"]
            dist_to_throttle_pb = pb_df["LapDistance"].iloc[matching_pb["exit_idx"]] - matching_pb["dist_apex"]
            if dist_to_throttle_curr > dist_to_throttle_pb + 15:
                feedback.append(f"{turn_name}: Çikişta gaza {dist_to_throttle_curr - dist_to_throttle_pb:.0f} metre daha GEÇ oturdun. Traksiyon kaybettin.")

    return feedback

def calculate_trail_braking_score(df):
    """
    Analyzes how smoothly the brake is released.
    Score 0-100.
    """
    if "Brake" not in df.columns:
        return 100
        
    # Find all braking zones
    braking = df["Brake"] > 0.05
    # Detect transitions from braking to not braking
    releases = []
    in_zone = False
    zone_start = 0
    
    for i in range(len(braking)):
        if braking.iloc[i] and not in_zone:
            in_zone = True
            zone_start = i
        elif not braking.iloc[i] and in_zone:
            in_zone = False
            releases.append(df["Brake"].iloc[zone_start:i+1].values)
            
    if not releases:
        return 100
        
    penalties = 0
    total_zones = len(releases)
    
    for release_curve in releases:
        if len(release_curve) < 3:
            continue
            
        # Check if the drop from max brake to 0 is instantaneous (bad trail braking)
        max_brake = np.max(release_curve)
        max_idx = np.argmax(release_curve)
        
        # If max brake is held until the very end and drops sharply
        trailing_portion = release_curve[max_idx:]
        if len(trailing_portion) > 0:
            # Calculate gradient
            gradient = np.abs(np.diff(trailing_portion))
            if len(gradient) > 0 and np.max(gradient) > 0.5: # Dropping more than 50% brake in one tick
                penalties += 1
                
    score = max(0, 100 - (penalties / total_zones * 100))
    
    feedback = []
    if score < 60:
        feedback.append("Frenleri çok sert/aniden birakiyorsun. ABS'ye yüklenmek yerine Trail-Braking (Yavaşça birakma) yapmaya çaliş.")
    elif score > 85:
        feedback.append("Trail-Braking mükemmel, aracin dengesini viraj içine çok iyi taşiyorsun.")
        
    return {
        "score": score,
        "feedback": feedback
    }

def analyze_coast_time(df):
    """
    Calculates time spent neither baking nor accelerating.
    """
    if "Brake" not in df.columns or "Throttle" not in df.columns:
        return {"coast_time_sec": 0, "feedback": []}
        
    # Coasting = Brake < 0.05 AND Throttle < 0.05
    is_coasting = (df["Brake"] < 0.05) & (df["Throttle"] < 0.05)
    
    # Assuming ~20Hz telemetry, each tick is ~0.05s
    # A more precise way would be using SessionTime differences, but counting ticks is robust
    coast_ticks = is_coasting.sum()
    coast_time_sec = coast_ticks * 0.05
    
    feedback = []
    if coast_time_sec > 1.5:
        feedback.append(f"Bu tur toplam {coast_time_sec:.1f} saniye 'Süzüldün' (İki pedala da basmadin). Pedallar arasi geçişte çok saniye kaybediyorsun!")
        
    return {
        "coast_time_sec": coast_time_sec,
        "feedback": feedback
    }

def analyze_shifting(df):
    """
    Analyzes RPM at the exact moment of upshifts.
    """
    if "Gear" not in df.columns or "EngineRPM" not in df.columns:
        return {"feedback": []}
        
    shifts = []
    for i in range(1, len(df)):
        if df["Gear"].iloc[i] > df["Gear"].iloc[i-1] and df["Gear"].iloc[i] > 1:
            shifts.append(df["EngineRPM"].iloc[i-1]) # RPM just before shift
            
    if not shifts:
        return {"feedback": []}
        
    avg_shift_rpm = np.mean(shifts)
    
    feedback = []
    # F1 2022 cars shift optimally around 11500 - 12200 RPM depending on gear
    if avg_shift_rpm > 12300:
        feedback.append("Vitesleri çok GEÇ atiyorsun (Redline'a vuruyorsun). Motor devri kesiciye girip zaman kaybettiriyor.")
    elif avg_shift_rpm < 11000:
        feedback.append("Vitesleri çok ERKEN atiyorsun (Short-shifting). Ciddi güç kaybediyorsun, devri biraz daha yükselt.")
        
    return {
        "avg_shift_rpm": avg_shift_rpm,
        "feedback": feedback
    }
    
def setup_advisor(df):
    """
    Analyzes telemetry to suggest setup changes.
    """
    feedback = []
    if "Speed" not in df.columns or "Throttle" not in df.columns:
        return feedback
        
    # 1. Top Speed Analysis (Straight line speed)
    max_speed = df["Speed"].max()
    if max_speed < 310:
        feedback.append("Düzlük hizim çok düşük. Arka kanadi (Rear Wing) 2-3 tik kısmayi/düşürmeyi düşünebilirsin.")
        
    # 2. Traction Analysis (Wheel slip on corner exit)
    # Simple heuristic: If RPM spikes while speed is low and throttle is high (wheelspin)
    if "EngineRPM" in df.columns:
        low_gear_high_rpm = ((df["Gear"] <= 4) & 
                             (df["Throttle"] > 0.8) & 
                             (df["Speed"] < 150) & 
                             (df["EngineRPM"] > 11500)).sum()
                             
        if low_gear_high_rpm > 20: # Arbitrary threshold for wheelspin ticks
            feedback.append("Düşük hizli viraj çikişlarinda çok patinajda kaliyorsun. Diferansiyeli (On-Throttle Diff) daha açik (Low) ayarlamayi dene.")
            
    return feedback

def analyze_race_start(df):
    """
    V11: Analyzes the 0-100 km/h launch at the start of the race.
    Only valid for Lap 1 where initial speed is 0.
    """
    if "LapNum" not in df.columns or "Speed" not in df.columns or df.empty:
        return {"feedback": []}
        
    # Strictly for Lap 1
    if df["LapNum"].iloc[-1] != 1:
        return {"feedback": []}
        
    start_idx = -1
    for i in range(min(500, len(df))):
        if df["Speed"].iloc[i] < 2.0 and df["Throttle"].iloc[i] > 0.5:
            start_idx = i
            break
            
    if start_idx == -1:
        # No launch detected
        return {"feedback": []}
        
    # Find when speed crosses 100 km/h
    hundred_idx = -1
    for i in range(start_idx, len(df)):
        if df["Speed"].iloc[i] >= 100:
            hundred_idx = i
            break
            
    if hundred_idx == -1:
        return {"feedback": []}
        
    # Roughly 20Hz -> 0.05s per tick
    time_0_100_s = (hundred_idx - start_idx) * 0.05
    
    # Calculate Wheelspin during this phase
    wheelspin_ticks = 0
    if "EngineRPM" in df.columns and "Gear" in df.columns:
        launch_phase = df.iloc[start_idx:hundred_idx]
        wheelspin_ticks = ((launch_phase["Gear"] <= 3) & (launch_phase["EngineRPM"] > 11500) & (launch_phase["Speed"] < 80)).sum()
        
    score = max(0, 100 - (time_0_100_s - 2.5) * 20 - wheelspin_ticks * 2)
    score = min(100, score)
    
    feedback = []
    if time_0_100_s < 2.8:
        feedback.append(f"🚦 Mükemmel Kalkiş! 0-100 km/h: {time_0_100_s:.2f}s | Kalkiş Puanin: {score:.0f}/100")
    else:
        feedback.append(f"🚦 Yavaş Kalkiş! 0-100 km/h: {time_0_100_s:.2f}s (Patinaj: {wheelspin_ticks} birim). Debriyaj noktasini daha iyi ayarla.")
        
    return {"feedback": feedback}

def analyze_slipstream(current_df, pb_df):
    """
    V11: Computes top speed delta on the longest straight to quantify slipstream/DRS.
    """
    if pb_df is None or "Speed" not in current_df.columns:
        return {"feedback": []}
        
    # Top speed of PB (clean air assumed) vs Current Lap
    pb_max_speed = pb_df["Speed"].max()
    curr_max_speed = current_df["Speed"].max()
    
    # Find where max speed occurred in current lap
    curr_max_idx = current_df["Speed"].idxmax()
    
    # Use DRS state as proxy for being close to a car ahead (Slipstream)
    is_drs = False
    if "DRS" in current_df.columns:
        is_drs = current_df["DRS"].iloc[curr_max_idx] > 0
    
    feedback = []
    if is_drs and (curr_max_speed > pb_max_speed + 3):
        res = calculate_slipstream_advantage(pb_max_speed, curr_max_speed)
        time_gained = res["time_gained_sec"]
        spd_delta = res["speed_delta_kmh"]
        feedback.append(f"💨 Slipstream/DRS Etkisi: Düzlükte +{spd_delta:.1f} km/h hiz avantajin vardi. (Tahmini {time_gained:.3f} sn kazandin)")
        
    return {"feedback": feedback}

def generate_lap_feedback(current_df, pb_df=None):
    """
    Synthesizes all modules into a combined feedback report.
    """
    report = {
        "trail_braking_score": 100,
        "coast_time_sec": 0,
        "avg_shift_rpm": 0,
        "priority_alert": "",
        "all_feedback": []
    }
    
    if current_df is None or current_df.empty:
        return report

    # 1. Corners
    if pb_df is not None and not pb_df.empty:
        corner_feedback = analyze_corners(current_df, pb_df)
        report["all_feedback"].extend(corner_feedback)
        
    # 2. Trail Braking
    tb_res = calculate_trail_braking_score(current_df)
    report["trail_braking_score"] = int(tb_res["score"])
    report["all_feedback"].extend(tb_res["feedback"])
    
    # 3. Coast Time
    coast_res = analyze_coast_time(current_df)
    report["coast_time_sec"] = float(coast_res["coast_time_sec"])
    report["all_feedback"].extend(coast_res["feedback"])
    
    # 4. Shifting
    shift_res = analyze_shifting(current_df)
    report["avg_shift_rpm"] = float(shift_res.get("avg_shift_rpm", 0))
    report["all_feedback"].extend(shift_res["feedback"])
    
    # 5. Setup Advisor
    setup_feedback = setup_advisor(current_df)
    report["all_feedback"].extend(setup_feedback)
    
    # 6. Race Start (V11)
    start_res = analyze_race_start(current_df)
    report["all_feedback"].extend(start_res["feedback"])
    
    # 7. Slipstream (V11)
    if pb_df is not None and not pb_df.empty:
        slip_res = analyze_slipstream(current_df, pb_df)
        report["all_feedback"].extend(slip_res["feedback"])
    
    # Priority Alert (for voice)
    if report["all_feedback"]:
        # Pick the most critical one. For now, just the first corner alert or first generic alert
        report["priority_alert"] = report["all_feedback"][0]
        
    return report

if __name__ == "__main__":
    # Simple test
    print("Testing race_engineer logic...")
    df = pd.DataFrame({
        "LapDistance": np.linspace(0, 5000, 1000),
        "Speed": np.abs(np.sin(np.linspace(0, 10, 1000))) * 300 + 50,
        "Brake": (np.cos(np.linspace(0, 10, 1000)) > 0).astype(float),
        "Throttle": (np.sin(np.linspace(0, 10, 1000)) > 0).astype(float),
        "Gear": (np.linspace(1, 8, 1000)).astype(int),
        "EngineRPM": np.random.uniform(10000, 12500, 1000)
    })
    res = generate_lap_feedback(df, df)
    print("TB Score:", res["trail_braking_score"])
    print("Coast Time:", res["coast_time_sec"])
    print("Alerts:")
    for f in res["all_feedback"]:
        print(" -", f)
