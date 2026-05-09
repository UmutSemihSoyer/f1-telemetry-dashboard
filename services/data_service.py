import sqlite3
import time
import logging

logger = logging.getLogger("DataService")

class DataService:
    def __init__(self, db_path="telemetry.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        # Braking Zones
        c.execute('''CREATE TABLE IF NOT EXISTS braking_zones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_time REAL, entry_speed REAL, exit_speed REAL,
            duration REAL, max_pressure REAL)''')
        # Lap Times
        c.execute('''CREATE TABLE IF NOT EXISTS lap_times (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT DEFAULT 'default',
            lap_num INTEGER, sector1_ms INTEGER, sector2_ms INTEGER,
            lap_time_ms INTEGER, timestamp REAL)''')
        # Session History
        c.execute('''CREATE TABLE IF NOT EXISTS session_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT, lap_num INTEGER, lap_time_ms INTEGER,
            sector1_ms INTEGER, sector2_ms INTEGER, timestamp REAL)''')
        
        # Migrations
        try:
            c.execute("ALTER TABLE lap_times ADD COLUMN session_id TEXT DEFAULT 'default'")
        except Exception: pass
        
        conn.commit()
        conn.close()

    def save_lap(self, lap_num, s1, s2, total, ts):
        try:
            session_id = time.strftime("%Y%m%d_%H%M00")
            conn = sqlite3.connect(self.db_path)
            conn.execute('''INSERT INTO lap_times 
                (session_id, lap_num, sector1_ms, sector2_ms, lap_time_ms, timestamp) 
                VALUES (?,?,?,?,?,?)''', (session_id, lap_num, s1, s2, total, ts))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error saving lap: {e}")

    def save_braking_zone(self, ts, entry, exit_, dur, mp):
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute('''INSERT INTO braking_zones 
                (session_time, entry_speed, exit_speed, duration, max_pressure) 
                VALUES (?,?,?,?,?)''', (ts, entry, exit_, dur, mp))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error saving braking zone: {e}")
