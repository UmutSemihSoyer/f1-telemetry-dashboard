import socket, struct, time, math, json, random

with open("config.json") as f:
    CONFIG = json.load(f)

UDP_IP   = "127.0.0.1" if CONFIG["network"]["UDP_IP"] == "0.0.0.0" else CONFIG["network"]["UDP_IP"]
UDP_PORT = CONFIG["network"]["UDP_PORT"]
PKT      = CONFIG["packet_sizes"]

HEADER_FMT    = CONFIG["structs"]["HEADER_FORMAT"]
LAP_FMT       = CONFIG["structs"]["LAP_DATA_FORMAT"]
DAMAGE_FMT    = CONFIG["structs"]["DAMAGE_DATA_FORMAT"]
CAR_STATUS_FMT= CONFIG["structs"]["CAR_STATUS_FORMAT"]
SESSION_FMT   = CONFIG["structs"]["SESSION_PREFIX_FORMAT"]

# Full 60-byte car telemetry
# <HfffBbHBBHHHHHBBBBBBBBHffffBBBB>
CAR_TELEM_FULL = "<HfffBbHBBHHHHHBBBBBBBBHffffBBBB"
MOTION_FMT     = "<ffffffhhhhhhffffff"

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
print(f"F1 2022 V7 Mock Sender --> {UDP_IP}:{UDP_PORT}")

# State
speed=250.0; state_time=0.0; is_accel=True
session_time=0.0; frame_id=0
lap=1; lap_ms=0.0; tyre_wear=0.0; track_angle=0.0
fuel_kg=105.0; fuel_laps=50.0; ers=4_000_000.0
# Session state
weather=0; weather_timer=0.0
# Tire temps (simulated realistic values baseline + heat from braking)
tyre_surf_temp=[90,90,90,90]   # RL,RR,FL,FR (Celsius)
tyre_inner_temp=[95,95,95,95]
brake_temp=[200,200,200,200]
engine_temp=100

ACCEL_DUR=5.0; BRAKE_DUR=1.5; dt=0.1

def hdr(pid):
    return struct.pack(HEADER_FMT, 2022,1,18,1,pid,123456789,session_time,frame_id,0,255)

while True:
    session_time+=dt; frame_id+=1; lap_ms+=dt*1000
    tyre_wear=min(tyre_wear+0.5*dt, 100.0)
    track_angle+=0.05*dt
    fuel_kg=max(0.0,fuel_kg-0.01*dt); fuel_laps=max(0.0,fuel_kg/2.1)
    ers=max(0.0,ers-5000*dt); weather_timer+=dt

    # Weather change every ~2 min
    if weather_timer>120:
        weather=(weather+1)%6; weather_timer=0.0

    if is_accel and state_time>=ACCEL_DUR: is_accel=False; state_time=0.0
    elif not is_accel and state_time>=BRAKE_DUR: is_accel=True; state_time=0.0

    if is_accel:
        brake=0.0; speed=min(speed+20.*dt,340.)
        for i in range(4):
            tyre_surf_temp[i]=max(80,min(120,tyre_surf_temp[i]-0.5))
            brake_temp[i]=max(80,min(900,brake_temp[i]-20))
    else:
        brake=1.0; speed=max(speed-130.*dt,60.)
        for i in range(4):
            tyre_surf_temp[i]=min(150,tyre_surf_temp[i]+3.)
            brake_temp[i]=min(900,brake_temp[i]+60.)
    for i in range(4):
        tyre_inner_temp[i]=tyre_surf_temp[i]+random.uniform(3,8)

    if lap_ms>90000: lap_ms=0.0; lap+=1
    gear=max(1,min(8,int(speed/35.)+1))
    rpm=min(12000,max(5000,5000+(speed%35.)/35.*7000))
    throttle=1.0 if is_accel else 0.0
    g_lon=1.2 if is_accel else -4.0
    g_lat=1.5*math.sin(track_angle*3)
    pos_x=500.*math.cos(track_angle)
    pos_z=500.*math.sin(track_angle)
    drs=1 if speed>250 and is_accel else 0

    # ---- PACKET 0: MOTION ----
    mot_cars=b''
    for i in range(22):
        mot_cars+=struct.pack(MOTION_FMT,
            pos_x,0.,pos_z, 0.,0.,0., 0,0,32767,0,32767,0,
            g_lat,g_lon,0., 0.,0.,0.) if i==0 else bytes(60)
    sock.sendto(hdr(0)+mot_cars+bytes(36*4+4),(UDP_IP,UDP_PORT))

    # ---- PACKET 6: FULL TELEMETRY (60 bytes each car) ----
    # <HfffBbHBBHHHHHBBBBBBBBHffffBBBB>
    tel_cars=b''
    for i in range(22):
        tel_cars+=struct.pack(CAR_TELEM_FULL,
            int(speed),throttle,0.0,brake,0,gear,int(rpm),
            drs,int((rpm/12000)*100),0,
            int(brake_temp[2]),int(brake_temp[3]),int(brake_temp[0]),int(brake_temp[1]),
            int(tyre_surf_temp[2]),int(tyre_surf_temp[3]),int(tyre_surf_temp[0]),int(tyre_surf_temp[1]),
            int(tyre_inner_temp[2]),int(tyre_inner_temp[3]),int(tyre_inner_temp[0]),int(tyre_inner_temp[1]),
            int(engine_temp),
            2.2,2.2,2.2,2.2,
            0,0,0,0
        ) if i==0 else bytes(60)
    sock.sendto(hdr(6)+tel_cars+struct.pack('<BBb',255,255,0),(UDP_IP,UDP_PORT))

    # ---- PACKET 2: LAP DATA (all 22 cars - mock) ----
    s1=int(lap_ms*0.3); s2=int(lap_ms*0.35)
    lap_cars=b''
    for i in range(22):
        car_lap=int(lap)+max(0,i-5)
        car_ms =max(1000, min(89000, int(lap_ms)+random.randint(-2000,2000))) if i!=0 else max(1000,int(lap_ms))
        car_pos=i+1
        lap_cars+=struct.pack(LAP_FMT,
            80000,car_ms,s1,s2, 0.,0.,0., 1,min(car_lap,50),
            car_pos,0,1,0,0, 0,0,0,1,1,2,0,0,0,0)
    sock.sendto(hdr(2)+lap_cars+struct.pack('<BB',255,255),(UDP_IP,UDP_PORT))

    # ---- PACKET 10: DAMAGE ----
    dmg_cars=b''
    for i in range(22):
        dmg_cars+=struct.pack(DAMAGE_FMT,
            tyre_wear,tyre_wear,tyre_wear,tyre_wear,
            0,0,0,0, 0,0,0,0,
            0,0,0, 0,0,0, 0,0,0, 0,0,0, 0,0,0, 0,0,0) if i==0 else bytes(42)
    sock.sendto(hdr(10)+dmg_cars,(UDP_IP,UDP_PORT))

    # ---- PACKET 7: CAR STATUS ----
    status_cars=b''
    for i in range(22):
        status_cars+=struct.pack(CAR_STATUS_FMT,
            0,1,1,50,0, fuel_kg,110.,fuel_laps,
            12000,5000, 8,1,50, 16,16,lap,0,
            ers,1, 500000.,200000.,300000., 0) if i==0 else bytes(47)
    sock.sendto(hdr(7)+status_cars,(UDP_IP,UDP_PORT))

    # ---- PACKET 1: SESSION DATA ----
    # <BbbBHBbBHHBBBBBB> = 18 bytes + marshal zones[21]*5 + safety_car+network
    # Total expected payload: 632 - 24(header) = 608 bytes
    sess_fields = struct.pack(SESSION_FMT,
        weather,     # weather
        30,          # trackTemperature
        22,          # airTemperature
        50,          # totalLaps
        5793,        # trackLength (Monza)
        6,           # sessionType (R=Race)
        10,          # trackId (Monza)
        0,           # formula
        3600,        # sessionTimeLeft
        5400,        # sessionDuration
        80,          # pitSpeedLimit
        0,0,0,0,0    # gamePaused, isSpectating, spectatorIdx, sliPro, numMarshalZones
    )
    marshal_bytes  = bytes(21*5)   # 21 marshal zones * 5 bytes
    safety_car     = 0
    network_game   = 0
    num_forecast   = 0
    weather_padded = bytes(56*8)   # 56 weather forecast samples * 8 bytes (simplified)
    session_payload = sess_fields + marshal_bytes + struct.pack('<BB',safety_car,network_game) + weather_padded
    # Trim/pad to 632-24=608 bytes
    session_payload = session_payload[:608].ljust(608, b'\x00')
    sock.sendto(hdr(1)+session_payload,(UDP_IP,UDP_PORT))

    phase="ACCEL" if is_accel else "BRAKE"
    print(f"[{phase}] Spd:{speed:.0f} Lap:{lap} Fuel:{fuel_kg:.1f}kg ERS:{ers/40000:.0f}% "
          f"Weather:{weather} TyreSurf:{tyre_surf_temp[0]}C Inner:{tyre_inner_temp[0]}C")

    state_time+=dt
    time.sleep(dt)
