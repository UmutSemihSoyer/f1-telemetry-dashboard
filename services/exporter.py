import json
import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime

try:
    from fpdf import FPDF
    HAS_FPDF = True
except ImportError:
    HAS_FPDF = False

class ExportService:
    def __init__(self, db_path="telemetry.db"):
        self.db_path = db_path

    def load_lap_times(self) -> pd.DataFrame:
        if not Path(self.db_path).exists():
            return pd.DataFrame()
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query("SELECT * FROM lap_times ORDER BY lap_num", conn)
        conn.close()
        for col in ['lap_num', 'sector1_ms', 'sector2_ms', 'lap_time_ms']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        return df

    def export_session(self, live_df, laps_df, braking_df):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # CSV Export
        live_df.to_csv(f"session_telemetry_{ts}.csv", index=False)
        if not laps_df.empty:
            laps_df.to_csv(f"session_laps_{ts}.csv", index=False)
        if not braking_df.empty:
            braking_df.to_csv(f"session_braking_{ts}.csv", index=False)
            
        # PDF Export
        if HAS_FPDF:
            self._generate_pdf(live_df, laps_df, braking_df, ts)
            
        return ts

    def _generate_pdf(self, live_df, laps_df, braking_df, ts):
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        
        # Header
        pdf.set_font("Helvetica", "B", 18)
        pdf.cell(0, 10, "F1 2022 Session Telemetry Report", new_x="LMARGIN", new_y="NEXT", align='C')
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 10, f"Generated: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}", new_x="LMARGIN", new_y="NEXT", align='C')
        pdf.ln(10)
        
        # Lap Times Table
        if not laps_df.empty:
            pdf.set_font("Helvetica", "B", 14)
            pdf.cell(0, 10, "Lap History", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "B", 10)
            
            # Table Header
            col_widths = [20, 40, 40, 40]
            headers = ["Lap", "Lap Time", "Sector 1", "Sector 2"]
            for i, header in enumerate(headers):
                pdf.cell(col_widths[i], 10, header, border=1, align='C')
            pdf.ln()
            
            # Table Rows
            pdf.set_font("Helvetica", "", 10)
            for _, row in laps_df.iterrows():
                lap_ms = int(row.get('lap_time_ms', 0))
                s1 = int(row.get('sector1_ms', 0))
                s2 = int(row.get('sector2_ms', 0))
                
                time_str = f"{lap_ms//60000}:{(lap_ms%60000)/1000:06.3f}" if lap_ms > 0 else "-"
                s1_str = f"{s1/1000:.3f}" if s1 > 0 else "-"
                s2_str = f"{s2/1000:.3f}" if s2 > 0 else "-"
                
                pdf.cell(col_widths[0], 10, str(row.get('lap_num', 0)), border=1, align='C')
                pdf.cell(col_widths[1], 10, time_str, border=1, align='C')
                pdf.cell(col_widths[2], 10, s1_str, border=1, align='C')
                pdf.cell(col_widths[3], 10, s2_str, border=1, align='C')
                pdf.ln()
        
        # Save output
        pdf.output(f"session_report_{ts}.pdf")

    def export_to_motec(self, df):
        if df is None or df.empty:
            return None
        
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"motec_export_{ts}.csv"
        
        # MoTeC i2 compatible headers and units
        mapping = {
            'Timestamp': 'Time',
            'LapDistance': 'Distance',
            'Speed': 'Speed',
            'Throttle': 'Throttle',
            'Brake': 'Brake',
            'Gear': 'Gear',
            'RPM': 'RPM',
            'Steer': 'Steering Angle',
            'PosX': 'PosX',
            'PosZ': 'PosZ',
            'GLat': 'G Force Lat',
            'GLon': 'G Force Lon'
        }
        
        # Rename columns that exist
        export_df = df.rename(columns=mapping)
        cols_to_keep = [v for v in mapping.values() if v in export_df.columns]
        export_df = export_df[cols_to_keep]
        
        # Create the units row
        units = {
            'Time': 's',
            'Distance': 'm',
            'Speed': 'km/h',
            'Throttle': '%',
            'Brake': '%',
            'Gear': '',
            'RPM': 'rpm',
            'Steering Angle': 'deg',
            'PosX': 'm',
            'PosZ': 'm',
            'G Force Lat': 'G',
            'G Force Lon': 'G'
        }
        
        unit_row = pd.DataFrame([units], columns=cols_to_keep)
        
        # Final combine
        final_df = pd.concat([unit_row, export_df], ignore_index=True)
        final_df.to_csv(filename, index=False)
        return filename

    def send_to_discord(self, pdf_path, message=""):
        try:
            import requests
            with open("config.json") as f:
                cfg = json.load(f)
                webhook_url = cfg.get("integrations", {}).get("DISCORD_WEBHOOK_URL")
            
            if not webhook_url:
                return False
            
            payload = {"content": message or "🏎️ **F1 2022 Pit Wall — Session Report Ready**"}
            
            if pdf_path and Path(pdf_path).exists():
                with open(pdf_path, 'rb') as f:
                    files = {'file': (pdf_path, f, 'application/pdf')}
                    r = requests.post(webhook_url, data=payload, files=files)
            else:
                r = requests.post(webhook_url, json=payload)
                
            return r.status_code == 200 or r.status_code == 204
        except Exception:
            return False

def run_export():
    """
    Stand-alone export trigger reading from local sqlite.
    """
    service = ExportService()
    laps_df = service.load_lap_times()
    
    # Try fetching session_history from the DB if load_lap_times returns empty
    if laps_df.empty:
        try:
            conn = sqlite3.connect("telemetry.db")
            laps_df = pd.read_sql_query("SELECT * FROM session_history ORDER BY lap_num", conn)
            conn.close()
        except Exception:
            pass
            
    print("Export triggered. Generating files...")
    service.export_session(pd.DataFrame(), laps_df, pd.DataFrame())
    print("Export complete.")
