# 🏎️ F1 2022 Pit Wall — Real-Time Telemetry Dashboard

[![CI](https://github.com/UmutSemihSoyer/f1-telemetry-dashboard/actions/workflows/ci.yml/badge.svg)](https://github.com/UmutSemihSoyer/f1-telemetry-dashboard/actions)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A professional, real-time telemetry analysis and race engineering system built for **F1 2022**.
Captures live UDP telemetry, performs physics and ML analysis, and presents insights through
an interactive multi-tab dashboard with voice alerts.

> **Compatibility Note:** The UDP packet structure is specifically designed for the **F1 2022**
> telemetry format. For F1 23/24, the packet unpacking logic in `core/listener.py` must be
> updated per the official EA/Codemasters specification.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🔴 **Live Telemetry** | Speed, RPM, gear shifts, throttle/brake inputs at 10 Hz |
| ⏱️ **Live Delta** | iRacing-style Δ vs Personal Best with animated color bar |
| 🗺️ **Track Map** | Real-time 2D car position from Motion UDP packets |
| 🧠 **ML Braking Zones** | K-Means clustering of braking points across laps |
| 🔧 **Race Engineer** | Corner-by-corner feedback vs Personal Best |
| ⛽ **Fuel Analysis** | Deficit analysis, lift-and-coast savings, pit window |
| 🏎️ **Tyre Thermals** | Physics-based tyre temperature model with status alerts |
| 📡 **Voice Alerts** | Pit wall radio via TTS: fuel, tyres, ERS, safety car |
| 🌐 **Ergast API** | Compare your laps against real F1 drivers (2023–2024) |
| 🔁 **Session Replay** | Replay any saved session through the live dashboard |
| 📄 **PDF Reports** | Auto-generated post-session PDF/CSV exports |

---

## 🏗️ Architecture

```
udp_telemetry/
├── dashboard.py            # Entry point — Dash web app
├── telemetry_listener.py   # Main coordinator — queues UDP data & triggers services
├── run_all.py              # One-command launcher (listener + dashboard)
│
├── core/                   # Pure computation — no I/O side effects
│   ├── listener.py         # UDP socket, packet parser, data queue
│   ├── physics_engine.py   # G-forces, braking distance, tyre thermal model
│   └── ml_engine.py        # K-Means braking zones, lap consistency
│
├── services/               # Business logic — reads/writes to disk & DB
│   ├── data_service.py     # SQLite persistence (lap times, braking zones)
│   ├── race_engineer.py    # Corner analysis & driving feedback
│   ├── telemetry_service.py# Delta timing vs Personal Best
│   └── exporter.py         # PDF & CSV session report generation
│
├── ui/                     # Dash components
│   ├── layout.py           # Page structure, tabs, cards
│   └── callbacks.py        # Live update callbacks
│
├── plotting/
│   └── telemetry_plots.py  # Plotly figure builders (speed, pedals, G-force, track)
│
├── assets/
│   └── style.css           # Dark theme CSS design system
│
├── mock_telemetry_sender.py# Testing tool — broadcasts mock F1 data without a game
├── replay.py               # Replay past sessions through the live dashboard
├── ergast_api.py           # Fetch real F1 lap data from Ergast API
├── analytics_physics.py    # Standalone physics functions (fuel, braking, overtake)
└── voice_alerts.py         # TTS voice alert system
```

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/UmutSemihSoyer/f1-telemetry-dashboard.git
cd f1-telemetry-dashboard
pip install -r requirements.txt
```

### 2. Configure

```bash
cp config.example.json config.json
# Edit config.json if you want to change the UDP port or disable voice alerts
```

### 3. Run

**Full system (with live game):**
```bash
python run_all.py
```
Then open **http://127.0.0.1:8050** in your browser.

Press `CTRL+C` to stop all services.

---

## 🎮 Mock Mode (Test Without the Game)

You can test the full system without F1 2022 running:

```bash
# Terminal 1 — Start the listener and dashboard
python run_all.py

# Terminal 2 — Broadcast simulated telemetry
python mock_telemetry_sender.py
```

The mock sender simulates a full race at Monza: speed, braking, tyre temps, fuel burn, ERS, weather changes.

---

## 🕹️ In-Game Setup (F1 2022)

1. Open **Settings → Telemetry Settings**
2. Enable **UDP Telemetry**
3. Set **IP Address** → `127.0.0.1`
4. Set **Port** → `20777`
5. Set **UDP Format** → `2022`
6. Start `python run_all.py` and begin a session

---

## 🔁 Session Replay

Replay any previously recorded session through the live dashboard:

```bash
# List all saved sessions
python replay.py

# Replay the latest session at 2× speed
python replay.py --speed 2.0

# Replay a specific session
python replay.py --session 20260316_012724 --speed 1.5

# Replay from a CSV file
python replay.py --csv session_telemetry_20260316_012724.csv
```

---

## 🌐 Ergast API — Compare vs Real F1 Drivers

```python
from ergast_api import fetch_race_laps, build_comparison_df, CIRCUIT_MAP

# Download Monza 2024 lap times
df = fetch_race_laps(2024, 16)

# Compare your best lap against the field
comparison = build_comparison_df(our_best_ms=95_000, real_df=df)
print(comparison.head(10))
```

Results are cached in `.ergast_cache/` to avoid repeated downloads.

---

## 🧪 Running Tests

```bash
pytest tests/ -v
```

The test suite covers:
- Fuel load calculation (7 tests)
- Braking distance physics (7 tests)
- Tyre thermal model (9 tests)
- Overtake opportunity window (5 tests)
- Fuel deficit analysis (6 tests)
- Lap consistency metrics (6 tests)

---

## 🛠️ Configuration Reference (`config.json`)

| Key | Default | Description |
|---|---|---|
| `network.UDP_IP` | `0.0.0.0` | Listen on all interfaces |
| `network.UDP_PORT` | `20777` | Must match in-game setting |
| `voice.ENABLED` | `true` | Enable/disable TTS voice alerts |
| `voice.RATE` | `180` | TTS speech rate (words per minute) |
| `voice.COOLDOWN_SEC` | `15` | Minimum seconds between repeated alerts |
| `alerts.TYRE_CRIT_PCT` | `85` | Tyre wear % that triggers critical voice alert |
| `alerts.FUEL_CRIT_LAPS` | `2` | Remaining fuel laps for critical alert |

---

## 📦 Dependencies

```
dash, plotly         — Dashboard and visualization
pandas, numpy        — Data processing
scikit-learn         — ML braking zone clustering
requests             — Ergast API calls
fpdf2                — PDF report generation
pyttsx3              — Voice alerts (TTS)
python-docx          — Word document export
```

Install all with: `pip install -r requirements.txt`

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

© 2026 Umut Semih Soyer
