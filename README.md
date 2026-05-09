# 🏎️ F1 2022 Telemetry Suite v7.0 — Simulation Master

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![Architecture](https://img.shields.io/badge/Architecture-In--Memory-red)](shared_state.py)
[![God-Tier](https://img.shields.io/badge/Edition-God--Tier-purple)](app.py)
[![Simulation](https://img.shields.io/badge/Level-Simulation--Master-gold)](core/physics_engine.py)

A high-performance, cloud-connected **Desktop Telemetry Suite** built for **F1 2022**. 
v7.0 introduces **Simulation Master** features: Dirty Air Aero Analysis and 3D Elevation Tracking.

---

## 📸 Masterpiece Preview

![Desktop App & Track Map](assets/dashboard_demo.webp)

---

## ✨ Master Features (v7.0)

| Feature | Description |
|---|---|
| 📐 **3D Track Replay** | Visualize the track in 3D with full elevation data (PosY). See the slopes of Spa/Monaco. |
| 🌪️ **Dirty Air Analysis** | Real-time estimation of downforce loss when following another car (<0.7s gap). |
| 🌐 **Live Multiplayer Stream** | Expose your local dashboard to a public URL via **Ngrok**. |
| 🎓 **AI Braking Coach** | Real-time voice coaching comparing your braking points to your personal best. |
| 💬 **Discord Automation** | Automated posting of New Best Laps and PDF session reports to Discord. |
| 🤖 **AI Tyre Prediction** | RandomForest ML model predicting the tyre degradation "cliff". |
| 📊 **MoTeC i2 Export** | Export sessions to MoTeC-compatible CSVs for professional engineering. |
| 👻 **Live Ghost Car** | Visual "Personal Best" ghost on the track map. |

---

## 🚀 Getting Started

### 1. Installation

```bash
git clone https://github.com/UmutSemihSoyer/f1-telemetry-dashboard.git
cd f1-telemetry-dashboard
pip install -r requirements.txt
```

### 2. Configure
Edit `config.json` for Ngrok and Discord settings.

### 3. Run the Suite
```bash
python app.py
```

---

## 🌪️ Aero & Dirty Air Analysis
The system tracks your "Clean Air" G-force baseline. When you follow a car within 0.7s, the **Aero Analyzer** calculates the percentage of lateral grip lost due to dirty air. Your engineer will alert you: *"Warning! Significant dirty air detected. Downforce down by 18%."*

## 📐 3D Elevation Replay
In the **Analysis** tab, the new 3D Track visualization uses high-resolution motion data (PosX, PosY, PosZ) to render the track with its real vertical profile. The line is colored by your speed, allowing for detailed topographical driving analysis.

---

## 🏗️ Technical Architecture

```
udp_telemetry/
├── app.py                  # ENTRY POINT — GUI + Ngrok Tunnel + Dash Server
├── shared_state.py         # SHARED MEMORY — Zero-latency state pool (with PosY)
├── core/                   # Logic — Aero Analyzer, Braking Coach, ML Models
├── ui/                     # UI — 3D Replay & Live Strategy Planner
└── services/               # Infrastructure — Discord Service, MoTeC Exporter
```

---

## 🕹️ In-Game Setup (F1 2022)

1. **Telemetry Settings:** Enable UDP Telemetry.
2. **IP/Port:** `127.0.0.1` / `20777`.
3. **Format:** `2022`.

---

## 📄 License

MIT License — © 2026 Umut Semih Soyer
