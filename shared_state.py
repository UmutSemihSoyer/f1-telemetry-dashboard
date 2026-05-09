import threading

from core.ml_engine import TyreDegradationModel

# Thread lock for safe read/write across Dash (Flask) threads and UDP Listener thread
state_lock = threading.Lock()

from core.ml_engine import TyreDegradationModel, BrakingCoach
from core.physics_engine import AeroAnalyzer

# ML & Physics Models
tyre_model = TyreDegradationModel()
braking_coach = BrakingCoach()
aero_analyzer = AeroAnalyzer()

# Best Lap Tracking
best_lap_time = 9999999.0  # ms
best_lap_data = []

# Weather Forecasts
latest_forecasts = []

# The latest full telemetry chunk (list of dicts)
latest_telemetry_chunk = []

# Store full lap path (list of [PosX, PosZ, Speed, Brake, Throttle])
current_lap_path = []

# To track when the lap changes so we can reset the path
current_lap_num = 0

latest_leaderboard = []
completed_laps_data = {}

def update_telemetry(chunk_df):
    global latest_telemetry_chunk, current_lap_path, current_lap_num, completed_laps_data
    with state_lock:
        if chunk_df.empty: return
        
        # Keep only last 100 rows to prevent memory leak
        latest_telemetry_chunk = chunk_df.tail(100).to_dict('records')
        
        latest = latest_telemetry_chunk[-1]
        lap = latest.get('LapNum', 0)
        
        if lap != current_lap_num and current_lap_num > 0:
            if len(current_lap_path) > 10:
                completed_laps_data[current_lap_num] = list(current_lap_path)
            current_lap_path.clear()
            current_lap_num = lap
        elif current_lap_num == 0:
            current_lap_num = lap
            
        pos_x = latest.get('PosX')
        pos_z = latest.get('PosZ')
        if pos_x is not None and pos_z is not None:
            # We append the latest point to the full lap path
            current_lap_path.append({
                'PosX': pos_x,
                'PosY': latest.get('PosY', 0),
                'PosZ': pos_z,
                'Speed': latest.get('Speed', 0),
                'Brake': latest.get('Brake', 0.0),
                'Throttle': latest.get('Throttle', 0.0),
                'LapDistance': latest.get('LapDistance', 0.0)
            })

def get_telemetry():
    with state_lock:
        return list(latest_telemetry_chunk), list(current_lap_path)

def update_leaderboard(lb):
    global latest_leaderboard
    with state_lock:
        latest_leaderboard = lb

def get_leaderboard():
    with state_lock:
        return list(latest_leaderboard)

def get_completed_lap_numbers():
    with state_lock:
        return sorted(list(completed_laps_data.keys()))

def get_completed_lap_data(lap_num):
    with state_lock:
        lap_data = completed_laps_data.get(int(lap_num))
        return list(lap_data) if lap_data else []

def set_lap_completed(lap_num, lap_time_ms):
    global best_lap_time, best_lap_data
    with state_lock:
        lap_data = completed_laps_data.get(int(lap_num))
        if lap_data and lap_time_ms > 0 and lap_time_ms < best_lap_time:
            best_lap_time = lap_time_ms
            best_lap_data = list(lap_data)
            braking_coach.load_best_lap(best_lap_data)
            aero_analyzer.update_baseline(best_lap_data)

def get_best_lap_data():
    with state_lock:
        return list(best_lap_data)

