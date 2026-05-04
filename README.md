# F1 UDP Telemetry Dashboard & Race Engineer

A comprehensive, real-time telemetry analysis and race engineering system for F1 games. This project captures live UDP telemetry data, performs advanced physics and machine learning analysis, and presents the insights through an interactive dashboard and automated reports.

## Features

- **Real-Time Telemetry Listener:** Captures high-frequency UDP packets (e.g., from F1 2022/2023) without dropping critical data.
- **Interactive Dashboards (Dash/Plotly):** Live visualization of speed, RPM, gear shifts, brake/throttle inputs, and track position.
- **Physics & ML Analytics:**
  - Calculates slipstream advantages and braking points (`analytics_physics.py`).
  - Analyzes braking patterns and driving style using Machine Learning (`ml_analysis.py`).
- **Race Engineer & Voice Alerts:** Automated audio cues for optimal braking points and tactical feedback (`voice_alerts.py`, `race_engineer.py`).
- **Ergast API Integration:** Fetches historical and comparative F1 data to benchmark against real-world laps (`ergast_api.py`).
- **Automated Reporting:** Generates PDF and Word (`.docx`) session reports post-race (`exporter.py`).

## Architecture Overview

1. **`telemetry_listener.py`**: The core UDP server. Binds to `127.0.0.1:20777`, unpacks binary data into Pandas DataFrames, and persists to a local SQLite database (`telemetry.db`).
2. **`dashboard.py`**: A Plotly Dash web application that reads the live database to render real-time telemetry graphs.
3. **`mock_telemetry_sender.py`**: A testing utility that broadcasts mock telemetry data (sine waves simulating speed/RPM) over UDP if the game is not running.
4. **Analytics Modules**: Scripts that run asynchronously to crunch data and provide feedback.

## Setup & Installation

1. Clone this repository:
   ```bash
   git clone <YOUR-REPO-URL>
   cd udp_telemetry
   ```
2. Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

You can run the components separately or use a launcher script.

**To test the system without the game (Mock Mode):**
1. Start the listener: `python telemetry_listener.py`
2. Start the dashboard: `python dashboard.py` (open `http://127.0.0.1:8050` in your browser)
3. Start the mock sender: `python mock_telemetry_sender.py`

**To use with the F1 Game:**
- Set your in-game Telemetry settings to broadcast to `127.0.0.1` on port `20777` (Format: F1 2022 / UDP).
- Start the listener and dashboard.

## License
MIT License
