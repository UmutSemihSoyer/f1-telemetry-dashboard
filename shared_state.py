import threading

# Thread lock for safe read/write across Dash (Flask) threads and UDP Listener thread
state_lock = threading.Lock()

# The latest full telemetry chunk (list of dicts)
latest_telemetry_chunk = []

# Store full lap path (list of [PosX, PosZ, Speed, Brake, Throttle])
current_lap_path = []

# To track when the lap changes so we can reset the path
current_lap_num = 0

latest_leaderboard = []

def update_telemetry(chunk_df):
    global latest_telemetry_chunk, current_lap_path, current_lap_num
    with state_lock:
        if chunk_df.empty: return
        
        # Keep only last 100 rows to prevent memory leak
        latest_telemetry_chunk = chunk_df.tail(100).to_dict('records')
        
        latest = latest_telemetry_chunk[-1]
        lap = latest.get('LapNum', 0)
        
        if lap != current_lap_num and current_lap_num > 0:
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

