import socket
import struct
import logging
import json
import threading
import queue
import time
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TelemetryCore")

class TelemetryListener:
    def __init__(self, config_path="config.json"):
        with open(config_path) as f:
            self.config = json.load(f)
        
        self.udp_ip = self.config["network"]["UDP_IP"]
        self.udp_port = self.config["network"]["UDP_PORT"]
        self.pkt_cfg = self.config["packet_sizes"]
        self.structs = self.config["structs"]
        
        self.header_fmt = self.structs["HEADER_FORMAT"]
        self.header_size = struct.calcsize(self.header_fmt)
        
        self.data_queue = queue.Queue()
        self.is_running = False
        self._prev_weather = -1

    def _parse_header(self, data):
        return struct.unpack(self.header_fmt, data[:self.header_size])

    def listen(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.bind((self.udp_ip, self.udp_port))
            logger.info(f"UDP Listener bound to {self.udp_ip}:{self.udp_port}")
        except Exception as e:
            logger.error(f"Failed to bind socket: {e}")
            return

        self.is_running = True
        while self.is_running:
            try:
                data, _ = sock.recvfrom(4096)
                if len(data) < self.header_size:
                    continue
                
                header = self._parse_header(data)
                packet_id = header[4]
                session_time = header[6]
                player_idx = header[8]

                self._process_packet(packet_id, session_time, player_idx, data)

            except Exception as e:
                logger.error(f"Listener error: {e}")
                time.sleep(0.1)

    def _process_packet(self, packet_id, session_time, player_idx, data):
        # 1. Telemetry Packet
        if packet_id == self.pkt_cfg["TELEMETRY_ID"] and len(data) == self.pkt_cfg["TELEMETRY_SIZE"]:
            fmt = self.structs["CAR_TELEMETRY_FULL_FORMAT"]
            start = 24 + (player_idx * 60)
            u = struct.unpack(fmt, data[start:start+60])
            self.data_queue.put({
                'Type': 'Telemetry', 'Timestamp': session_time,
                'Speed': u[0], 'Throttle': u[1], 'Brake': u[3], 'Gear': u[5], 'RPM': u[6],
                'DRS': u[7],
                'BrakeTempRL': u[10], 'BrakeTempRR': u[11], 'BrakeTempFL': u[12], 'BrakeTempFR': u[13],
                'TyreSurfRL': u[14], 'TyreSurfRR': u[15], 'TyreSurfFL': u[16], 'TyreSurfFR': u[17],
                'TyreInnerRL': u[18], 'TyreInnerRR': u[19], 'TyreInnerFL': u[20], 'TyreInnerFR': u[21],
                'EngineTemp': u[22],
            })

        # 2. Lap Data Packet
        elif packet_id == self.pkt_cfg["LAP_DATA_ID"] and len(data) == self.pkt_cfg["LAP_DATA_SIZE"]:
            fmt = self.structs["LAP_DATA_FORMAT"]
            start = 24 + (player_idx * 43)
            u = struct.unpack(fmt, data[start:start+43])
            
            # Basic lap info
            self.data_queue.put({
                'Type': 'LapData', 'Timestamp': session_time,
                'LastLapTimeMS': u[0], 'CurrentLapTimeMS': u[1],
                'Sector1MS': u[2], 'Sector2MS': u[3],
                'LapDistance': u[4],
                'CurrentLapNum': u[8], 'Penalties': u[13]
            })

            # Leaderboard & Gaps
            leaderboard = []
            for i in range(22):
                cs = 24 + (i * 43)
                try:
                    cu = struct.unpack(fmt, data[cs:cs+43])
                    leaderboard.append({
                        'car': i, 'lap': cu[8], 'lapTimeMS': cu[1], 'pos': cu[9]
                    })
                except struct.error: break
            
            leaderboard.sort(key=lambda x: x.get('pos', 99))
            
            # Simple gap calculation logic (to be moved to services eventually)
            player_lap_ms = u[1]
            gap_ahead = 0.0
            gap_behind = 0.0
            for entry in leaderboard:
                if entry['car'] == player_idx: continue
                diff = (player_lap_ms - entry['lapTimeMS']) / 1000.0
                if diff > 0 and gap_ahead == 0.0: gap_ahead = diff
                elif diff < 0:
                    gap_behind = abs(diff)
                    break
            
            self.data_queue.put({
                'Type': 'Competitors', 'Timestamp': session_time,
                'CarPosition': u[9], 'GapAhead': gap_ahead, 'GapBehind': gap_behind,
                'Leaderboard': leaderboard
            })

        # 3. Damage Packet
        elif packet_id == self.pkt_cfg["DAMAGE_ID"] and len(data) == self.pkt_cfg["DAMAGE_SIZE"]:
            fmt = self.structs["DAMAGE_DATA_FORMAT"]
            start = 24 + (player_idx * 42)
            u = struct.unpack(fmt, data[start:start+42])
            self.data_queue.put({
                'Type': 'Damage', 'Timestamp': session_time,
                'TyreWearRL': u[0], 'TyreWearRR': u[1], 'TyreWearFL': u[2], 'TyreWearFR': u[3],
                'EngineDamage': u[21]
            })

        # 4. Motion Packet
        elif packet_id == self.pkt_cfg["MOTION_ID"] and len(data) == self.pkt_cfg["MOTION_SIZE"]:
            fmt = self.structs["CAR_MOTION_FORMAT"]
            start = 24 + (player_idx * 60)
            u = struct.unpack(fmt, data[start:start+60])
            self.data_queue.put({
                'Type': 'Motion', 'Timestamp': session_time,
                'PosX': u[0], 'PosZ': u[2], 'GLat': u[12], 'GLon': u[13]
            })

        # 5. Status Packet
        elif packet_id == self.pkt_cfg["STATUS_ID"] and len(data) == self.pkt_cfg["STATUS_SIZE"]:
            fmt = self.structs["CAR_STATUS_FORMAT"]
            start = 24 + (player_idx * 47)
            u = struct.unpack(fmt, data[start:start+47])
            self.data_queue.put({
                'Type': 'Status', 'Timestamp': session_time,
                'Fuel': u[5], 'FuelLaps': u[7], 'ERS': u[17], 'ERSMode': u[18], 'TyreAge': u[15]
            })

        # 6. Session Packet
        elif packet_id == self.pkt_cfg["SESSION_ID"] and len(data) == self.pkt_cfg["SESSION_SIZE"]:
            fmt = self.structs["SESSION_PREFIX_FORMAT"]
            prefix_size = struct.calcsize(fmt)
            u = struct.unpack(fmt, data[24:24+prefix_size])
            
            # Safety car status is deep in the packet
            safety_offset = 24 + prefix_size + (21 * 5)
            safety = struct.unpack_from('<B', data, safety_offset)[0]
            
            self.data_queue.put({
                'Type': 'Session', 'Timestamp': session_time,
                'Weather': u[0], 'TrackTemp': u[1], 'AirTemp': u[2],
                'TotalLaps': u[3], 'SessionType': u[5], 'SessionTimeLeft': u[8],
                'SafetyCarStatus': safety
            })

    def stop(self):
        self.is_running = False

if __name__ == "__main__":
    listener = TelemetryListener()
    t = threading.Thread(target=listener.listen, daemon=True)
    t.start()
    
    while True:
        try:
            item = listener.data_queue.get(timeout=1)
            print(f"Captured: {item['Type']}")
        except queue.Empty:
            pass
