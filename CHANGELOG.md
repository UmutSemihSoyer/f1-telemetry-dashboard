# Changelog

All notable changes to this project will be documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [v2.0.0] — 2026-05-09

### Added
- **Modular architecture** — codebase restructured into four clean layers:
  - `core/` — UDP listener, physics engine, ML engine
  - `services/` — data persistence, race engineer, telemetry service, exporter
  - `ui/` — Dash layout and callbacks
  - `plotting/` — Plotly figure builders
- **Live delta timing** — iRacing-style ΔT vs personal best with animated color bar
- **Dynamic track map** — real-time 2D car position from Motion packets
- **K-Means braking zone clustering** (ML) — finds optimal braking points across laps
- **Lap consistency metric** — standard deviation analysis of lap time variation
- **Ergast API integration** — compare your lap times vs real F1 drivers (2023-2024 data)
- **Session replay** (`replay.py`) — replay past sessions through the live dashboard
- **G-force scatter map** — longitudinal vs lateral G-force visualization
- **config.example.json** — safe template for first-time setup
- **GitHub Actions CI** — automated pytest on Python 3.10 / 3.11 / 3.12

### Changed
- `dashboard.py` updated to use `app.run()` (replaces deprecated `app.run_server()`)
- All source code and documentation translated fully to English
- `requirements.txt` updated with all runtime dependencies (`pyttsx3`, `fpdf2`)

### Fixed
- Missing `__init__.py` in all package directories

---

## [v1.0.0] — 2026-05-03

### Added
- Initial release: F1 2022 UDP telemetry listener (`telemetry_listener.py`)
- Interactive Dash/Plotly dashboard (`dashboard.py`)
- Physics analytics engine (`analytics_physics.py`)
- ML braking analysis (`ml_analysis.py`)
- Race engineer feedback engine (`race_engineer.py`)
- Voice alert system via pyttsx3 (`voice_alerts.py`)
- PDF/CSV session report exporter (`exporter.py`)
- Mock telemetry sender for testing without the game (`mock_telemetry_sender.py`)
- SQLite session persistence (`telemetry.db`)
