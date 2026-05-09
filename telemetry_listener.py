import threading
import queue
import time
import pandas as pd
import json
import logging
from core.listener import TelemetryListener
from core.ml_engine import run_ml_analysis_pass
from services.data_service import DataService
from services.race_engineer import generate_lap_feedback
from voice_alerts import (start_voice_thread, radio_engineer_feedback, alert_tyre_critical, 
                          alert_tyre_warn, alert_ers_critical, alert_fuel_critical, 
                          alert_fuel_warn, alert_safety_car, speak)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MainListener")

class TelemetryManager:
    def __init__(self):
        self.listener = TelemetryListener()
        self.data_service = DataService()
        self.telemetry_buffer = []
        self._last_lap_num = 0
        self.full_lap_buffer = []
        self._was_braking = False

        # Latest state from each packet type — merged into every chunk
        self._latest_lap_info    = {}
        self._latest_damage      = {}
        self._latest_status      = {}
        self._latest_motion      = {}
        self._latest_session     = {}
        self._latest_competitors = {}

    def run(self):
        logger.info("Starting UDP listener thread...")
        listener_thread = threading.Thread(target=self.listener.listen, daemon=True)
        listener_thread.start()

        start_voice_thread()

        logger.info("Main processing loop active.")
        while True:
            try:
                item = self.listener.data_queue.get(timeout=1.0)
                p_type = item.get('Type')

                if p_type == 'Telemetry':
                    self.telemetry_buffer.append(item)
                    if len(self.telemetry_buffer) >= 100:
                        self.process_telemetry_chunk()

                elif p_type == 'LapData':
                    self._latest_lap_info = item
                    lap_num = item.get('CurrentLapNum', 0)
                    if lap_num != self._last_lap_num and self._last_lap_num > 0:
                        self.handle_lap_completion(item)
                    self._last_lap_num = lap_num

                elif p_type == 'Damage':
                    self._latest_damage = item

                elif p_type == 'Status':
                    self._latest_status = item

                elif p_type == 'Motion':
                    self._latest_motion = item

                elif p_type == 'Session':
                    self._latest_session = item

                elif p_type == 'Competitors':
                    self._latest_competitors = item

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in manager loop: {e}")

    def process_telemetry_chunk(self):
        df = pd.DataFrame(self.telemetry_buffer)

        # ── Lap info (distance, time, lap number) ─────────────────────────────
        if self._latest_lap_info:
            df['LapDistance'] = self._latest_lap_info.get('LapDistance', 0)
            df['LapTime']     = self._latest_lap_info.get('CurrentLapTimeMS', 0) / 1000.0
            df['LapNum']      = self._latest_lap_info.get('CurrentLapNum', 0)
            df['Sector1']     = self._latest_lap_info.get('Sector1MS', 0)
            df['Sector2']     = self._latest_lap_info.get('Sector2MS', 0)
            df['Penalties']   = self._latest_lap_info.get('Penalties', 0)

        # ── Damage / Tyre Wear ─────────────────────────────────────────────────
        if self._latest_damage:
            df['TyreWearFL']   = self._latest_damage.get('TyreWearFL', 0)
            df['TyreWearFR']   = self._latest_damage.get('TyreWearFR', 0)
            df['TyreWearRL']   = self._latest_damage.get('TyreWearRL', 0)
            df['TyreWearRR']   = self._latest_damage.get('TyreWearRR', 0)
            df['EngineDamage'] = self._latest_damage.get('EngineDamage', 0)

        # ── Car Status (fuel, ERS, tyre age) ──────────────────────────────────
        if self._latest_status:
            df['Fuel']         = self._latest_status.get('Fuel', 0)
            df['FuelLaps']     = self._latest_status.get('FuelLaps', 0)
            df['ERS']          = self._latest_status.get('ERS', 0)
            df['ERSMode']      = self._latest_status.get('ERSMode', 0)
            df['TyreAge']      = self._latest_status.get('TyreAge', 0)

            # Pit prediction: estimate laps until fuel runs out
            fuel_laps = self._latest_status.get('FuelLaps', 0)
            df['PitPrediction'] = round(fuel_laps, 1) if fuel_laps > 0 else -1

        # ── Motion (track map, suspension) ────────────────────────────────────────────────
        if self._latest_motion:
            df['PosX'] = self._latest_motion.get('PosX', 0)
            df['PosZ'] = self._latest_motion.get('PosZ', 0)
            df['GLat'] = self._latest_motion.get('GLat', 0)
            df['GLon'] = self._latest_motion.get('GLon', 0)
            df['SuspPosRL'] = self._latest_motion.get('SuspPosRL', 0)
            df['SuspPosRR'] = self._latest_motion.get('SuspPosRR', 0)
            df['SuspPosFL'] = self._latest_motion.get('SuspPosFL', 0)
            df['SuspPosFR'] = self._latest_motion.get('SuspPosFR', 0)
            df['WheelSlipRL'] = self._latest_motion.get('WheelSlipRL', 0)
            df['WheelSlipRR'] = self._latest_motion.get('WheelSlipRR', 0)
            df['WheelSlipFL'] = self._latest_motion.get('WheelSlipFL', 0)
            df['WheelSlipFR'] = self._latest_motion.get('WheelSlipFR', 0)

        # ── Session (weather, temps) ───────────────────────────────────────────
        if self._latest_session:
            df['Weather']      = self._latest_session.get('Weather', 0)
            df['TrackTemp']    = self._latest_session.get('TrackTemp', 0)
            df['AirTemp']      = self._latest_session.get('AirTemp', 0)
            df['TotalLaps']    = self._latest_session.get('TotalLaps', 0)
            df['SafetyCarStatus'] = self._latest_session.get('SafetyCarStatus', 0)
            
            # Store forecasts in shared_state directly for the radar
            if 'Forecasts' in self._latest_session:
                import shared_state
                shared_state.latest_forecasts = self._latest_session['Forecasts']

        # ── Competitors (gaps) ────────────────────────────────────────────────
        if self._latest_competitors:
            df['CarPosition'] = self._latest_competitors.get('CarPosition', 0)
            df['GapAhead']    = self._latest_competitors.get('GapAhead', 0.0)
            df['GapBehind']   = self._latest_competitors.get('GapBehind', 0.0)
            
            try:
                import shared_state
                lb = self._latest_competitors.get('Leaderboard', [])
                shared_state.update_leaderboard(lb)
            except Exception:
                pass

        self.full_lap_buffer.append(df.copy())

        try:
            import shared_state
            shared_state.update_telemetry(df)
        except Exception as e:
            logger.error(f"Failed to update shared_state: {e}")

        self.telemetry_buffer.clear()
        
        # Trigger voice alerts based on latest data
        self.trigger_voice_alerts(df.iloc[-1])

    def trigger_voice_alerts(self, latest):
        """Analyze latest telemetry row and trigger voice cues if necessary."""
        # 1. Tyre Wear (average)
        w_fl, w_fr = latest.get('TyreWearFL', 0), latest.get('TyreWearFR', 0)
        w_rl, w_rr = latest.get('TyreWearRL', 0), latest.get('TyreWearRR', 0)
        avg_wear = (w_fl + w_fr + w_rl + w_rr) / 4.0
        
        if avg_wear > 75:
            alert_tyre_critical(avg_wear)
        elif avg_wear > 45:
            alert_tyre_warn(avg_wear)
            
        # 2. Fuel
        fuel_laps = latest.get('FuelLaps', 0)
        if fuel_laps > 0:
            if fuel_laps < 1.0:
                alert_fuel_critical(fuel_laps)
            elif fuel_laps < 3.0:
                alert_fuel_warn(fuel_laps)
                
        # 3. ERS
        ers_pct = latest.get('ERS', 0)
        if ers_pct < 10:
            alert_ers_critical(ers_pct)
            
        # 4. Gaps / DRS
        gap_ahead = latest.get('GapAhead', 99.0)
        if 0 < gap_ahead < 1.0:
            speak(f"DRS distance! Gap ahead is {gap_ahead:.2f} seconds. Push now!", "drs_warn")
            
        # 5. Safety Car
        sc_status = latest.get('SafetyCarStatus', 0)
        if sc_status > 0:
            alert_safety_car(sc_status)
            
        # 6. Braking Coach
        curr_brake = latest.get('Brake', 0)
        if curr_brake > 50 and not self._was_braking:
            self._was_braking = True
            import shared_state
            status = shared_state.braking_coach.check_brake_timing(latest.get('LapDistance', 0))
            if status == "EARLY":
                speak("Braked too early! Brake later.", "coach_early")
            elif status == "LATE":
                speak("Braked too late! Focus on the exit.", "coach_late")
        elif curr_brake < 10:
            self._was_braking = False

    def handle_lap_completion(self, lap_item):
        lap_num = self._last_lap_num
        s1      = lap_item.get('Sector1MS', 0)
        s2      = lap_item.get('Sector2MS', 0)
        total   = lap_item.get('LastLapTimeMS', 0)
        ts      = lap_item.get('Timestamp', 0)

        logger.info(f"Lap {lap_num} completed. Time: {total}ms")

        self.data_service.save_lap(lap_num, s1, s2, total, ts)

        import shared_state
        from services.exporter import ExportService
        
        is_new_best = (total > 0 and total < shared_state.best_lap_time)
        shared_state.set_lap_completed(lap_num, total)
        
        if is_new_best:
            # Notify Discord of New Personal Best
            ExportService().send_to_discord(None, f"⭐ **Personal Best Shattered!** Lap {lap_num}: `{total/1000:.3f}s` 🏎️💨")

        threading.Thread(target=run_ml_analysis_pass, daemon=True).start()

        if self.full_lap_buffer:
            full_df = pd.concat(self.full_lap_buffer, ignore_index=True)
            self.full_lap_buffer.clear()

            feedback = generate_lap_feedback(full_df)
            with open("engineer_feedback.json", "w", encoding="utf-8") as f:
                json.dump(feedback, f)

            if feedback.get("priority_alert"):
                radio_engineer_feedback(feedback["priority_alert"])

if __name__ == "__main__":
    manager = TelemetryManager()
    manager.run()
