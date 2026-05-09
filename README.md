# 🏎️ F1 2022 Telemetry Suite v6.0 — God-Tier Edition

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Architecture](https://img.shields.io/badge/Architecture-In--Memory-red)](shared_state.py)
[![God-Tier](https://img.shields.io/badge/Edition-God--Tier-purple)](app.py)

A high-performance, cloud-connected **Desktop Telemetry Suite** built for **F1 2022**. 
v6.0 introduces the **God-Tier** update: Multiplayer Live Streaming, AI Braking Coaching, and Discord Automation.

---

## 📸 Masterpiece Preview

![Desktop App & Track Map](assets/dashboard_demo.webp)

---

## ✨ God-Tier Features (v6.0)

| Feature | Description |
|---|---|
| 🌐 **Live Multiplayer Stream** | Expose your local dashboard to a public URL via **Ngrok**. Let your engineer watch live. |
| 🎓 **AI Braking Coach** | Real-time voice coaching comparing your braking points to your personal best. |
| 💬 **Discord Automation** | Automated posting of New Best Laps and PDF session reports to your Discord channel. |
| ⚡ **In-Memory Engine** | Shared Memory architecture with **0ms latency**. No disk I/O bottlenecks. |
| 🖥️ **Native Desktop App** | Independent Windows application window powered by `pywebview`. |
| 👻 **Live Ghost Car** | Visual "Personal Best" ghost on the track map to track live delta. |
| 🤖 **AI Tyre Prediction** | RandomForest ML model predicting the tyre degradation "cliff". |
| 📊 **MoTeC i2 Export** | Export sessions to MoTeC-compatible CSVs for professional engineering. |
| 🌦️ **Rain Radar** | Real-time weather forecasting based on 30-minute game samples. |
| 📡 **Voice Engineer** | Fully active radio alerts for fuel, wear, DRS, and coaching. |

---

## 🚀 Getting Started

### 1. Installation

```bash
git clone https://github.com/UmutSemihSoyer/f1-telemetry-dashboard.git
cd f1-telemetry-dashboard
pip install -r requirements.txt
```

### 2. Configure (v6.0 Specifics)
Edit `config.json` to enable new integrations:
```json
"remote": {
    "STREAMING_ENABLED": true,
    "NGROK_AUTH_TOKEN": "YOUR_TOKEN_HERE"
},
"integrations": {
    "DISCORD_WEBHOOK_URL": "YOUR_WEBHOOK_HERE"
}
```

### 3. Run the Suite
```bash
python app.py
```

---

## 🎓 AI Braking Coach
The coach analyzes your braking performance in real-time. If you brake 8m+ earlier than your personal best, you'll hear: *"Braked too early! Brake later."* If you overshoot, it warns: *"Braked too late! Focus on the exit."*

## 🌐 Remote Engineering (Ngrok)
When `STREAMING_ENABLED` is true, the app generates a public URL. Share this with your teammate so they can monitor your temperatures, ERS, and strategy from their own device, anywhere in the world.

---

## 🏗️ Technical Architecture

```
udp_telemetry/
├── app.py                  # ENTRY POINT — GUI + Ngrok Tunnel + Dash Server
├── shared_state.py         # SHARED MEMORY — Zero-latency state pool
├── core/                   # Logic — AI Braking Coach, ML Models, Packet Parser
├── ui/                     # UI — Layouts and live Callbacks
├── services/               # Infrastructure — Discord Service, MoTeC Exporter
└── build.ps1               # COMPILATION — Standalone .EXE script
```

---

## 🕹️ In-Game Setup (F1 2022)

1. **Telemetry Settings:** Enable UDP Telemetry.
2. **IP/Port:** `127.0.0.1` / `20777`.
3. **Format:** `2022`.

---

## 📄 License

MIT License — © 2026 Umut Semih Soyer
