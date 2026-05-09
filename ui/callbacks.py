from dash import Input, Output, html, dcc
import pandas as pd
import numpy as np
import json
from pathlib import Path

from ui.layout import create_live_hud, create_analysis_tab, create_strategy_tab, create_setup_tab, create_race_control_tab
from plotting.telemetry_plots import TelemetryPlots

def register_callbacks(app):
    @app.callback(Output('tabs-content', 'children'),
                  Input('main-tabs', 'value'))
    def render_content(tab):
        if tab == 'live':
            return create_live_hud()
        elif tab == 'analysis':
            return create_analysis_tab()
        elif tab == 'strategy':
            return create_strategy_tab()
        elif tab == 'setup':
            return create_setup_tab()
        elif tab == 'race_control':
            return create_race_control_tab()

    @app.callback(
        [Output('live-speed-graph', 'figure'),
         Output('live-pedal-graph', 'figure'),
         Output('live-track-map', 'figure'),
         Output('live-speed-value', 'children'),
         Output('live-fuel-value', 'children'),
         Output('fuel-prediction', 'children'),
         Output('live-delta-value', 'children'),
         Output('live-delta-value', 'style'),
         Output('live-delta-bar-inner', 'style'),
         Output('live-ers-value', 'children'),
         Output('live-ers-bar', 'style'),
         Output('live-gap-ahead', 'children'),
         Output('live-gap-behind', 'children')],
        [Input('update-interval', 'n_intervals')]
    )
    def update_live_data(n):
        _empty = [{}, {}, {}, "0", "0.0", "No data", "0.00", {}, {}, "0", {}, "--", "--"]
        
        try:
            import shared_state
            chunk_data, path_data = shared_state.get_telemetry()
            
            if not chunk_data:
                return _empty
            
            df = pd.DataFrame(chunk_data)
            path_df = pd.DataFrame(path_data) if path_data else df
            
            # --- TELEMETRY PLOTS ---
            plots = TelemetryPlots()
            speed_fig = plots.create_speed_plot(df)
            pedal_fig = plots.create_pedal_plot(df)
            
            # Fetch Best Lap for Ghost Car
            best_lap_df = pd.DataFrame(shared_state.get_best_lap_data())
            track_fig = plots.create_track_map(path_df, best_lap_df=best_lap_df)
            
            latest = df.iloc[-1]
            speed_val = f"{int(latest.get('Speed', 0))}"
            fuel_val = f"{latest.get('Fuel', 0.0):.1f}"
            
            fuel_msg = f"Est. {latest.get('FuelLaps', 0):.1f} laps remaining"
            if latest.get('PitPrediction', -1) > 0:
                fuel_msg += f" | Pit in {int(latest['PitPrediction'])} laps"

            # --- DELTA CALCULATION ---
            delta = 0.0
            delta_style = {'color': '#e1e1e1'}
            bar_style = {'height': '100%', 'width': '0%', 'backgroundColor': '#e1e1e1', 'marginLeft': '50%'}
            
            if Path("best_lap_telemetry.json").exists() and "LapTime" in df.columns:
                best_df = pd.read_json("best_lap_telemetry.json")
                if not best_df.empty and "LapDistance" in df.columns:
                    curr_dist = latest.get("LapDistance", 0)
                    curr_time = latest.get("LapTime", 0)
                    
                    # Interp best time at current distance
                    best_time_at_dist = np.interp(
                        curr_dist, 
                        best_df["LapDistance"], 
                        best_df["LapTime"]
                    )
                    delta = curr_time - best_time_at_dist
                    
                    # Style the delta (iRacing style)
                    color = "#ff1801" if delta > 0 else "#00d2be"
                    delta_style = {'color': color, 'fontWeight': 'bold'}
                    
                    # Bar logic: 50% is center. 
                    # Max scale +/- 2.0s
                    clamped_delta = max(-2.0, min(2.0, delta))
                    width = abs(clamped_delta) / 2.0 * 50 # max 50%
                    
                    if delta > 0: # Losing time (Red, Right)
                        bar_style = {
                            'height': '100%', 'width': f'{width}%', 
                            'backgroundColor': '#ff1801', 'marginLeft': '50%'
                        }
                    else: # Gaining time (Cyan, Left)
                        bar_style = {
                            'height': '100%', 'width': f'{width}%', 
                            'backgroundColor': '#00d2be', 'marginLeft': f'{50 - width}%'
                        }

            delta_str = f"{'+' if delta > 0 else ''}{delta:.2f}"

            # --- ERS ---
            # ERS is stored in Joules (max ~4,000,000 J)
            ers_j       = latest.get('ERS', 0)
            ers_pct     = min(100, int(ers_j / 40000))   # 4 MJ = 100%
            ers_color   = '#9b00ef' if ers_pct > 30 else '#ff1801'
            ers_bar_style = {
                'height': '100%',
                'width':  f'{ers_pct}%',
                'backgroundColor': ers_color,
                'transition': 'width 0.3s'
            }

            # --- Gaps ---
            gap_ahead  = latest.get('GapAhead', 0.0)
            gap_behind = latest.get('GapBehind', 0.0)
            gap_ahead_str  = f"{gap_ahead:.2f}"  if gap_ahead  > 0 else "--"
            gap_behind_str = f"{gap_behind:.2f}" if gap_behind > 0 else "--"

            return [
                speed_fig, pedal_fig, track_fig,
                speed_val, fuel_val, fuel_msg,
                delta_str, delta_style, bar_style,
                str(ers_pct), ers_bar_style,
                gap_ahead_str, gap_behind_str
            ]
            
        except Exception as e:
            return [{}, {}, {}, "ERR", "0.0", f"Error: {str(e)}", "0.00", {}, {}, "0", {}, "--", "--"]

    @app.callback(
        [Output('setup-suspension-graph', 'figure'),
         Output('setup-slip-graph', 'figure')],
        [Input('update-interval', 'n_intervals')],
        [Input('main-tabs', 'value')]
    )
    def update_setup_tab(n, active_tab):
        if active_tab != 'setup':
            return [{}, {}]

        susp_fig = {}
        slip_fig = {}

        try:
            import shared_state
            chunk_data, _ = shared_state.get_telemetry()
            if chunk_data:
                df = pd.DataFrame(chunk_data)
                if not df.empty:
                    plots = TelemetryPlots()
                    susp_fig = plots.create_suspension_plot(df)
                    slip_fig = plots.create_slip_plot(df)
        except Exception:
            pass

        return [susp_fig, slip_fig]

    @app.callback(
        Output('race-control-table', 'children'),
        [Input('update-interval', 'n_intervals')],
        [Input('main-tabs', 'value')]
    )
    def update_race_control(n, active_tab):
        if active_tab != 'race_control':
            return ""

        try:
            import shared_state
            lb = shared_state.get_leaderboard()
            if not lb:
                return html.Div("No timing data available yet.", style={'color': '#8e8e93'})

            rows = []
            rows.append(html.Tr([
                html.Th("Pos", style={'padding': '8px', 'borderBottom': '1px solid #2c2d33', 'textAlign': 'left'}),
                html.Th("Car", style={'padding': '8px', 'borderBottom': '1px solid #2c2d33', 'textAlign': 'left'}),
                html.Th("Lap", style={'padding': '8px', 'borderBottom': '1px solid #2c2d33', 'textAlign': 'left'}),
                html.Th("Last Lap", style={'padding': '8px', 'borderBottom': '1px solid #2c2d33', 'textAlign': 'left'}),
                html.Th("Penalties", style={'padding': '8px', 'borderBottom': '1px solid #2c2d33', 'textAlign': 'left'})
            ]))

            # lb is a list of dicts: {'car': idx, 'position': pos, 'lapNum': lap, 'lapTimeMS': ms, 'penalties': p}
            # We should sort by position
            lb_sorted = sorted(lb, key=lambda x: x.get('position', 99))

            for entry in lb_sorted:
                pos = entry.get('position', 0)
                if pos == 0: continue
                
                car = entry.get('car', 0)
                lap = entry.get('lapNum', 0)
                ms = entry.get('lapTimeMS', 0)
                pen = entry.get('penalties', 0)
                
                time_str = f"{ms//60000}:{(ms%60000)/1000:06.3f}" if ms > 0 else "--:--.---"
                
                rows.append(html.Tr([
                    html.Td(str(pos), style={'padding': '8px', 'borderBottom': '1px solid #2c2d33'}),
                    html.Td(f"Car #{car}", style={'padding': '8px', 'borderBottom': '1px solid #2c2d33', 'fontWeight': 'bold'}),
                    html.Td(str(lap), style={'padding': '8px', 'borderBottom': '1px solid #2c2d33'}),
                    html.Td(time_str, style={'padding': '8px', 'borderBottom': '1px solid #2c2d33', 'color': '#00d2be'}),
                    html.Td(f"+{pen}s" if pen > 0 else "", style={'padding': '8px', 'borderBottom': '1px solid #2c2d33', 'color': '#ff1801'})
                ]))

            return html.Table(rows, style={'width': '100%', 'borderCollapse': 'collapse'})
        except Exception as e:
            return html.Div(f"Error loading leaderboard: {e}", style={'color': '#ff1801'})

    @app.callback(
        [Output('analysis-gforce-map', 'figure'),
         Output('analysis-tire-wear', 'figure'),
         Output('lap-history-table', 'children')],
        [Input('update-interval', 'n_intervals')],
        [Input('main-tabs', 'value')]
    )
    def update_analysis_tab(n, active_tab):
        if active_tab != 'analysis':
            return [{}, {}, ""]

        gforce_fig = {}
        tire_fig   = {}
        lap_table  = html.Div("No lap data available.", style={'color': '#8e8e93'})

        try:
            import shared_state
            chunk_data, _ = shared_state.get_telemetry()
            if chunk_data:
                df = pd.DataFrame(chunk_data)
                if not df.empty:
                    plots = TelemetryPlots()
                    gforce_fig = plots.create_g_force_plot(df)
                    tire_fig   = plots.create_tire_wear_plot(df)
        except Exception:
            pass

        try:
            import sqlite3
            conn = sqlite3.connect("telemetry.db")
            laps_df = pd.read_sql_query(
                "SELECT lap_num, lap_time_ms, sector1_ms, sector2_ms "
                "FROM session_history ORDER BY lap_num DESC LIMIT 15", conn
            )
            conn.close()

            if not laps_df.empty:
                rows = []
                # Header
                rows.append(html.Tr([
                    html.Th("Lap", style={'padding': '8px', 'borderBottom': '1px solid #2c2d33', 'textAlign': 'left'}),
                    html.Th("Time", style={'padding': '8px', 'borderBottom': '1px solid #2c2d33', 'textAlign': 'left'}),
                    html.Th("S1", style={'padding': '8px', 'borderBottom': '1px solid #2c2d33', 'textAlign': 'left'}),
                    html.Th("S2", style={'padding': '8px', 'borderBottom': '1px solid #2c2d33', 'textAlign': 'left'}),
                    html.Th("S3", style={'padding': '8px', 'borderBottom': '1px solid #2c2d33', 'textAlign': 'left'})
                ]))

                for _, row in laps_df.iterrows():
                    lap_ms = int(row['lap_time_ms'])
                    s1 = int(row['sector1_ms'])
                    s2 = int(row['sector2_ms'])
                    s3 = max(0, lap_ms - s1 - s2)

                    time_str = f"{lap_ms//60000}:{(lap_ms%60000)/1000:06.3f}"
                    rows.append(html.Tr([
                        html.Td(str(row['lap_num']), style={'padding': '8px', 'borderBottom': '1px solid #2c2d33'}),
                        html.Td(time_str, style={'padding': '8px', 'borderBottom': '1px solid #2c2d33', 'color': '#00d2be'}),
                        html.Td(f"{s1/1000:.3f}", style={'padding': '8px', 'borderBottom': '1px solid #2c2d33'}),
                        html.Td(f"{s2/1000:.3f}", style={'padding': '8px', 'borderBottom': '1px solid #2c2d33'}),
                        html.Td(f"{s3/1000:.3f}", style={'padding': '8px', 'borderBottom': '1px solid #2c2d33'})
                    ]))

                lap_table = html.Table(rows, style={'width': '100%', 'borderCollapse': 'collapse'})

        except Exception as e:
            lap_table = html.Div(f"Could not load history: {e}", style={'color': '#8e8e93'})

        return [gforce_fig, tire_fig, lap_table]

    @app.callback(
        [Output('compare-lap-1', 'options'),
         Output('compare-lap-2', 'options')],
        [Input('update-interval', 'n_intervals')]
    )
    def update_lap_dropdowns(n):
        try:
            import shared_state
            laps = shared_state.get_completed_lap_numbers()
            options = [{'label': f'Lap {lap}', 'value': lap} for lap in laps]
            return [options, options]
        except Exception:
            return [[], []]

    @app.callback(
        Output('compare-graph', 'figure'),
        [Input('compare-lap-1', 'value'),
         Input('compare-lap-2', 'value')]
    )
    def update_compare_graph(lap1, lap2):
        try:
            import shared_state
            df1 = pd.DataFrame(shared_state.get_completed_lap_data(lap1)) if lap1 else pd.DataFrame()
            df2 = pd.DataFrame(shared_state.get_completed_lap_data(lap2)) if lap2 else pd.DataFrame()
            
            plots = TelemetryPlots()
            return plots.create_lap_comparison_plot(
                df1, df2, 
                lap1_name=f"Lap {lap1}" if lap1 else "Lap 1",
                lap2_name=f"Lap {lap2}" if lap2 else "Lap 2"
            )
        except Exception as e:
            return {}

    @app.callback(
        [Output('engineer-feedback-list', 'children'),
         Output('strategy-recommendations', 'children')],
        [Input('update-interval', 'n_intervals')],
        [Input('main-tabs', 'value')]
    )
    def update_strategy_tab(n, active_tab):
        if active_tab != 'strategy':
            return [[], []]

        # --- Race Engineer Feedback ---
        feedback_items = []
        if Path("engineer_feedback.json").exists():
            with open("engineer_feedback.json", "r", encoding="utf-8") as f:
                report = json.load(f)
                for msg in report.get("all_feedback", []):
                    feedback_items.append(
                        html.Div(f"📻 {msg}", style={'padding': '5px', 'borderBottom': '1px solid #2c2d33'})
                    )

        if not feedback_items:
            feedback_items = [html.Div("No feedback available for this lap.", style={'color': '#8e8e93'})]

        # --- Real Strategy Recommendations ---
        strategy = []
        try:
            import shared_state
            chunk_data, _ = shared_state.get_telemetry()
            if chunk_data:
                from analytics_physics import fuel_deficit_analysis, dynamic_pit_loss

                df = pd.DataFrame(chunk_data)
                if not df.empty:
                    latest     = df.iloc[-1]
                    fuel_kg    = latest.get('Fuel', 0)
                    fuel_laps  = latest.get('FuelLaps', 0)
                    total_laps = int(latest.get('TotalLaps', 50))
                    lap_num    = int(latest.get('LapNum', 0))
                    sc_status  = int(latest.get('SafetyCarStatus', 0))
                    weather    = int(latest.get('Weather', 0))

                    fuel_info = fuel_deficit_analysis(fuel_kg, fuel_laps, total_laps, lap_num)
                    pit_info  = dynamic_pit_loss(sc_status, weather)

                    if fuel_info['is_sufficient']:
                        fuel_color = '#00d2be'
                        fuel_text  = (f"Fuel OK — {fuel_info['surplus_laps']:.1f} laps surplus "
                                      f"({fuel_kg:.1f} kg remaining)")
                    else:
                        fuel_color = '#ff1801'
                        fuel_text  = (f"FUEL SHORT by {fuel_info['deficit_kg']:.2f} kg — "
                                      f"save {fuel_info['save_pct_needed']:.1f}% per lap")

                    strategy.append(html.Div(f"⛽ {fuel_text}",
                        style={'color': fuel_color, 'padding': '5px',
                               'borderBottom': '1px solid #2c2d33'}))

                    sc_label  = {0: "Normal", 1: "Safety Car", 2: "VSC"}.get(sc_status, "Normal")
                    pit_color = '#00d2be' if pit_info['is_window_optimal'] else '#8e8e93'
                    strategy.append(html.Div(
                        f"🔧 Pit Loss: {pit_info['dynamic_loss_sec']:.1f}s ({sc_label} conditions)",
                        style={'color': pit_color, 'padding': '5px',
                               'borderBottom': '1px solid #2c2d33'}))

                    # --- ML Tyre Prediction ---
                    try:
                        wear_avg = np.mean([latest.get(f'TyreWear{s}', 0) for s in ['FL', 'FR', 'RL', 'RR']])
                        slip_avg = np.mean([latest.get(f'WheelSlip{s}', 0) for s in ['FL', 'FR', 'RL', 'RR']])
                        susp_avg = np.mean([latest.get(f'SuspPos{s}', 0) for s in ['FL', 'FR', 'RL', 'RR']])
                        t_temp   = latest.get('TrackTemp', 30.0)
                        
                        cliff_laps = shared_state.tyre_model.predict_cliff_laps(wear_avg, t_temp, slip_avg, susp_avg)
                        
                        if cliff_laps >= 0:
                            cliff_color = '#ff1801' if cliff_laps < 3 else '#00d2be'
                            strategy.append(html.Div(
                                f"🤖 AI Prediction: Tyre 'cliff' in {cliff_laps} laps (Confidence: 85%)",
                                style={'color': cliff_color, 'padding': '5px', 'borderBottom': '1px solid #2c2d33'}
                            ))
                    except Exception as e:
                        pass

                    laps_rem = max(0, total_laps - lap_num)
                    strategy.append(html.Div(
                        f"🏁 Laps Remaining: {laps_rem} / {total_laps}",
                        style={'color': '#e1e1e1', 'padding': '5px'}))

        except Exception as e:
            strategy.append(html.Div(f"Strategy data unavailable: {e}",
                                     style={'color': '#8e8e93'}))

        if not strategy:
            strategy = [html.Div("No live data available.", style={'color': '#8e8e93'})]

        return [feedback_items, strategy]

    @app.callback(
        Output('export-motec-status', 'children'),
        [Input('btn-export-motec', 'n_clicks')],
        prevent_initial_call=True
    )
    def trigger_motec_export(n):
        if not n: return ""
        try:
            import shared_state
            from services.exporter import ExportService
            
            # Combine all completed laps into one big DataFrame
            laps = shared_state.get_completed_lap_numbers()
            all_data = []
            for l in laps:
                all_data.extend(shared_state.get_completed_lap_data(l))
            
            if not all_data:
                return "No completed laps to export yet."
            
            df = pd.DataFrame(all_data)
            service = ExportService()
            filename = service.export_to_motec(df)
            
            if filename:
                return f"Successfully exported to {filename}"
            else:
                return "Export failed (empty data)."
        except Exception as e:
            return f"Export Error: {e}"

    @app.callback(
        [Output('strat-planner-output', 'children'),
         Output('weather-radar-graph', 'figure')],
        [Input('update-interval', 'n_intervals'),
         Input('strat-pit-1', 'value'),
         Input('strat-pit-2', 'value')]
    )
    def update_strategy_planning(n, pit1, pit2):
        # 1. Weather Radar
        radar_fig = {}
        try:
            import shared_state
            radar_fig = TelemetryPlots.create_weather_radar_plot(shared_state.latest_forecasts)
        except Exception: pass
        
        # 2. Strategy Engine
        try:
            import shared_state
            chunk_data, _ = shared_state.get_telemetry()
            if not chunk_data: return ["Waiting for data...", radar_fig]
            
            latest = chunk_data[-1]
            total_laps = int(latest.get('TotalLaps', 50))
            if total_laps == 0: total_laps = 50
            
            # Simulation parameters
            base_lap = 90.0
            deg_rate = 0.12 # seconds added per lap of age
            pit_loss = 23.5 # seconds
            
            def calc_total_time(pits):
                pits = [p for p in pits if p is not None and 0 < p < total_laps]
                time = 0
                age = 0
                for l in range(1, total_laps + 1):
                    time += base_lap + (age * deg_rate)
                    age += 1
                    if l in pits:
                        time += pit_loss
                        age = 0
                return time
            
            t_custom = calc_total_time([pit1, pit2])
            # Default 1-stop comparison
            t_opt = calc_total_time([total_laps // 2])
            
            diff = t_custom - t_opt
            if diff < 0.1:
                msg = f"Strateji: {int(t_custom//60)}dk {int(t_custom%60)}sn (Optimal!)"
            else:
                msg = f"Strateji: {int(t_custom//60)}dk {int(t_custom%60)}sn (+{diff:.1f}sn yavaş)"
                
            return [msg, radar_fig]
        except Exception as e:
            return [f"Error: {e}", radar_fig]

