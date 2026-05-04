"""
exporter.py - F1 2022 Session Report Generator
Usage: python exporter.py
Output: session_telemetry_TIMESTAMP.csv, session_laps_TIMESTAMP.csv, session_report_TIMESTAMP.pdf
"""

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
    print("[WARNING] fpdf2 not found. Only CSV will be generated. (pip install fpdf2)")


def load_live_data() -> pd.DataFrame:
    if not Path("live_data.json").exists():
        return pd.DataFrame()
    return pd.read_json("live_data.json")


def load_lap_times() -> pd.DataFrame:
    if not Path("telemetry.db").exists():
        return pd.DataFrame()
    conn = sqlite3.connect("telemetry.db")
    df = pd.read_sql_query("SELECT * FROM lap_times ORDER BY lap_num", conn)
    conn.close()
    # ensure numeric types
    for col in ['lap_num', 'sector1_ms', 'sector2_ms', 'lap_time_ms']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
    return df


def load_braking_zones() -> pd.DataFrame:
    if not Path("telemetry.db").exists():
        return pd.DataFrame()
    conn = sqlite3.connect("telemetry.db")
    df = pd.read_sql_query("SELECT * FROM braking_zones ORDER BY session_time", conn)
    conn.close()
    for col in ['entry_speed', 'exit_speed', 'duration', 'max_pressure']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
    return df


def export_csv(live_df, laps_df, braking_df):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    live_df.to_csv(f"session_telemetry_{ts}.csv", index=False)
    if not laps_df.empty:
        laps_df.to_csv(f"session_laps_{ts}.csv", index=False)
    if not braking_df.empty:
        braking_df.to_csv(f"session_braking_{ts}.csv", index=False)
    print(f"[OK] CSV files created (timestamp: {ts})")
    return ts


def export_pdf(live_df, laps_df, braking_df, ts):
    if not HAS_FPDF:
        return

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    def row(h, text, bold=False, color=(0, 0, 0), size=10, align='L'):
        pdf.set_font("Helvetica", "B" if bold else "", size)
        pdf.set_text_color(*color)
        pdf.cell(0, h, str(text), new_x="LMARGIN", new_y="NEXT", align=align)

    def hline():
        pdf.ln(2)
        pdf.set_draw_color(200, 200, 200)
        pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
        pdf.ln(2)

    # ---- Title ----
    row(12, "F1 2022 Session Telemetry Report", bold=True, color=(220, 30, 30), size=18, align='C')
    row(6,  f"Generated: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}", color=(100, 100, 100), size=9, align='C')
    pdf.ln(4)

    # ---- Telemetry Summary ----
    if not live_df.empty:
        row(8, "Telemetry Summary", bold=True, size=13)
        hline()
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(0, 0, 0)

        spd_col = next((c for c in live_df.columns if c.lower().startswith('h') and 'z' in c.lower()), None)
        summary_rows = [("Total Data Points", str(len(live_df)))]
        if spd_col:
            summary_rows += [
                ("Max Speed",  f"{float(live_df[spd_col].max()):.1f} km/h"),
                ("Avg Speed",  f"{float(live_df[spd_col].mean()):.1f} km/h"),
            ]
        summary_rows.append(("Max RPM", f"{float(live_df['RPM'].max()):.0f}"))
        if 'WearFL' in live_df.columns:
            summary_rows.append(("Max Tyre Wear (FL)", f"{float(live_df['WearFL'].max()):.1f}%"))
        if 'Fuel' in live_df.columns:
            summary_rows.append(("Min Fuel",  f"{float(live_df['Fuel'].min()):.2f} kg"))
        if 'ERS' in live_df.columns:
            ers_pct = (float(live_df['ERS'].min()) / 4_000_000) * 100
            summary_rows.append(("Min ERS",   f"{ers_pct:.1f}%"))

        for label, val in summary_rows:
            pdf.set_fill_color(245, 245, 245)
            pdf.cell(85, 7, label, border=0, fill=True)
            pdf.cell(0, 7, val, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

    # ---- Lap Times ----
    if not laps_df.empty:
        row(8, "Lap Times", bold=True, size=13)
        hline()

        headers = ["Lap", "Sector 1 (ms)", "Sector 2 (ms)", "Total (ms)"]
        col_w   = [20, 50, 50, 55]

        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(30, 30, 30)
        pdf.set_text_color(255, 255, 255)
        for h, w in zip(headers, col_w):
            pdf.cell(w, 7, h, border=1, fill=True, align="C")
        pdf.ln()

        pdf.set_font("Helvetica", "", 9)
        best_lap_ms = int(laps_df['lap_time_ms'].min())
        for _, r in laps_df.iterrows():
            is_best = int(r['lap_time_ms']) == best_lap_ms
            pdf.set_fill_color(180, 255, 180) if is_best else pdf.set_fill_color(255, 255, 255)
            pdf.set_text_color(0, 0, 0)
            vals = [str(int(r['lap_num'])), str(int(r['sector1_ms'])),
                    str(int(r['sector2_ms'])), str(int(r['lap_time_ms']))]
            for v, w in zip(vals, col_w):
                pdf.cell(w, 6, v, border=1, fill=True, align="C")
            pdf.ln()

        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(60, 60, 60)
        pdf.cell(0, 7, f"  * Fastest Lap: {best_lap_ms}ms  ({best_lap_ms/1000:.3f}s)",
                 new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

    # ---- Braking Zones ----
    if not braking_df.empty:
        row(8, "Braking Zones", bold=True, size=13)
        hline()

        bh     = ["#", "Entry (km/h)", "Exit (km/h)", "Duration (s)", "Max Press (%)"]
        bcol_w = [15, 42, 42, 35, 41]

        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(30, 30, 30)
        pdf.set_text_color(255, 255, 255)
        for h, w in zip(bh, bcol_w):
            pdf.cell(w, 7, h, border=1, fill=True, align="C")
        pdf.ln()

        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(0, 0, 0)
        for n, (_, r) in enumerate(braking_df.iterrows(), 1):
            pdf.set_fill_color(255, 245, 245) if n % 2 == 0 else pdf.set_fill_color(255, 255, 255)
            bvals = [str(n),
                     f"{float(r['entry_speed']):.1f}",
                     f"{float(r['exit_speed']):.1f}",
                     f"{float(r['duration']):.2f}",
                     f"{float(r['max_pressure']):.1f}"]
            for v, w in zip(bvals, bcol_w):
                pdf.cell(w, 6, v, border=1, fill=True, align="C")
            pdf.ln()

    fname = f"session_report_{ts}.pdf"
    pdf.output(fname)
    print(f"[OK] PDF report created: {fname}")


if __name__ == "__main__":
    print("[INFO] Generating session report...")
    live_df    = load_live_data()
    laps_df    = load_lap_times()
    braking_df = load_braking_zones()

    if live_df.empty and laps_df.empty:
        print("[ERROR] No data found. Run 'python run_all.py' first.")
    else:
        ts = export_csv(live_df, laps_df, braking_df)
        export_pdf(live_df, laps_df, braking_df, ts)
        print("[DONE] Export complete!")
