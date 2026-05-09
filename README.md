# 🏎️ F1 2022 Telemetry Suite v5.0 — Ultra-Premium

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Architecture](https://img.shields.io/badge/Architecture-In--Memory-red)](shared_state.py)

A professional-grade, high-performance **Desktop Telemetry Suite** built for **F1 2022**. 
Transitioning from a web-based dashboard to a native, zero-latency desktop application, this suite provides industry-standard analysis tools comparable to MoTeC and VRS.

---

## 📸 Masterpiece Preview

![Desktop App & Track Map](assets/dashboard_demo.webp)

---

## ✨ Ultra-Premium Features (v5.0)

| Feature | Description |
|---|---|
| ⚡ **In-Memory Engine** | Shared Memory architecture with **0ms latency**. No disk I/O bottlenecks. |
| 🖥️ **Native Desktop App** | Independent Windows application window powered by `pywebview`. |
| 📊 **MoTeC i2 Export** | Export sessions to MoTeC-compatible CSVs for professional engineering. |
| 👻 **Live Ghost Car** | Visual "Personal Best" ghost on the track map to track live delta. |
| 🤖 **AI Tyre Prediction** | RandomForest ML model predicting the tyre degradation "cliff". |
| 🗺️ **Full Track Trace** | Dynamic pathing that draws the entire lap trace, not just a slice. |
| ⚖️ **Setup Tuning** | Dedicated tab for Suspension Compression & Wheel Slip analysis. |
| 🏰 **Race Control** | 22-car live Timing Tower with positions, gaps, and penalties. |
| 📡 **Advanced Voice** | Fully active Voice Engineer radio for fuel, wear, and DRS alerts. |
| 🌦️ **Rain Radar** | Real-time weather forecasting based on 30-minute game samples. |

---

## 🏗️ Technical Architecture

The suite has been re-engineered for performance using a unified process model:

```
udp_telemetry/
├── app.py                  # MAIN ENTRY POINT — Desktop GUI + Listener + Server
├── shared_state.py         # SHARED MEMORY — Thread-safe RAM storage (0ms I/O)
│
├── core/                   # Processing Layer
│   ├── listener.py         # High-speed UDP packet binary unpacking
│   ├── physics_engine.py   # G-force and thermal models
│   └── ml_engine.py        # RandomForest Tyre Prediction & K-Means clusters
│
├── ui/                     # Presentation Layer
│   ├── layout.py           # Dashboard design with interactive strategy planner
│   └── callbacks.py        # Real-time state fetching from RAM
│
├── services/               # Infrastructure Layer
│   ├── exporter.py         # PDF Reporting & MoTeC CSV Engine
│   └── data_service.py     # SQLite persistence for lap history
│
└── build.ps1               # COMPILATION — One-click .EXE creation script
```

---

## 🚀 Getting Started

### 1. Installation

```bash
git clone https://github.com/UmutSemihSoyer/f1-telemetry-dashboard.git
cd f1-telemetry-dashboard
pip install -r requirements.txt
```

### 2. Run the Desktop App

```bash
python app.py
```
*Note: This starts the UDP Listener, the Dash background server, and the Desktop Window in one command.*

### 3. Create a Standalone .EXE

If you want to run the suite without Python:
1. Open PowerShell.
2. Run `./build.ps1`.
3. Find your app in `dist/F1_PitWall.exe`.

---

## 🏎️ Analysis Tools

### Multi-Lap Overlay
In the **Analysis** tab, select two completed laps from the dropdowns. The system will overlay their speed, throttle, and brake traces on a single graph with a unified X-axis (Distance), allowing you to pinpoint exactly where you lost time.

### MoTeC Integration
Use the **Export to MoTeC** button to generate a CSV formatted for MoTeC i2 Pro. It includes high-resolution channels for:
- Steering Angle
- Suspension Velocity
- Wheel Slip (Traction/Lockup)
- G-Forces (Lateral/Longitudinal)

### Strategy Planner
An interactive simulator where you can input pit stop laps. The engine uses our ML model to estimate the **Total Race Time**, comparing different strategies (e.g., 1-stop vs 2-stop) against the optimal path.

---

## 🎮 In-Game Setup (F1 2022)

1. **Telemetry Settings:** Enable UDP Telemetry.
2. **IP/Port:** `127.0.0.1` / `20777`.
3. **Format:** `2022`.
4. **Action:** Start `app.py` before heading out of the pit lane.

---

## 📄 License

MIT License — © 2026 Umut Semih Soyer
