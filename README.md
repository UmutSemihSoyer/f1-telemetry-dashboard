# F1 2022 UDP Telemetry Dashboard & Race Engineer

A comprehensive, real-time telemetry analysis and race engineering system built specifically for **F1 2022**. This project captures live UDP telemetry data, performs advanced physics and machine learning analysis, and presents the insights through an interactive dashboard and automated reports.

> **Note on Compatibility:** The UDP packet structure (`struct` unpacking logic) in this project is specifically designed for the **F1 2022** telemetry format. Newer games (such as F1 23 or F1 24) have different packet sizes and structures. To use this application with newer games, the UDP packet unpacking logic in `telemetry_listener.py` must be updated according to the official EA/Codemasters telemetry specifications for those years.

## Features

- **Real-Time Telemetry Listener:** Captures high-frequency UDP packets from F1 2022 without dropping critical data.
- **Interactive Dashboards (Dash/Plotly):** Live visualization of speed, RPM, gear shifts, brake/throttle inputs, and track position.
- **Physics & ML Analytics:**
  - Calculates slipstream advantages and braking points (`analytics_physics.py`).
  - Analyzes braking patterns and driving style using Machine Learning (`ml_analysis.py`).
- **Race Engineer & Voice Alerts:** Automated audio cues for optimal braking points and tactical feedback (`voice_alerts.py`, `race_engineer.py`).
- **Ergast API Integration:** Fetches historical and comparative F1 data to benchmark against real-world laps (`ergast_api.py`).
- **Automated Reporting:** Generates PDF and Word (`.docx`) session reports post-race (`exporter.py`).

## Architecture Overview

1. **`telemetry_listener.py`**: The core UDP server. Binds to `127.0.0.1:20777`, unpacks F1 2022 binary data into Pandas DataFrames, and persists to a local SQLite database (`telemetry.db`).
2. **`dashboard.py`**: A Plotly Dash web application that reads the live database to render real-time telemetry graphs.
3. **`mock_telemetry_sender.py`**: A testing utility that broadcasts mock F1 2022 telemetry data (sine waves simulating speed/RPM) over UDP if the game is not running.
4. **Analytics Modules**: Scripts that run asynchronously to crunch data and provide feedback.

## Setup & Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/UmutSemihSoyer/f1-telemetry-dashboard.git
   cd f1-telemetry-dashboard
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

**To use with the F1 2022 Game:**
- Go to In-Game Settings -> Telemetry Settings.
- Enable UDP Telemetry.
- Set IP to `127.0.0.1` and Port to `20777`.
- Set UDP Format to **2022**.
- Start the listener and dashboard.

## License
MIT License
