from dash import Input, Output, html, dcc
import pandas as pd
import numpy as np
import json
from pathlib import Path

from ui.layout import create_live_hud, create_analysis_tab, create_strategy_tab
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

    @app.callback(
        [Output('live-speed-graph', 'figure'),
         Output('live-pedal-graph', 'figure'),
         Output('live-track-map', 'figure'),
         Output('live-speed-value', 'children'),
         Output('live-fuel-value', 'children'),
         Output('fuel-prediction', 'children'),
         Output('live-delta-value', 'children'),
         Output('live-delta-value', 'style'),
         Output('live-delta-bar-inner', 'style')],
        [Input('update-interval', 'n_intervals')]
    )
    def update_live_data(n):
        if not Path("live_data.json").exists():
            return [{}, {}, {}, "0", "0.0", "No data", "0.00", {}, {}]
        
        try:
            df = pd.read_json("live_data.json")
            if df.empty:
                return [{}, {}, {}, "0", "0.0", "No data", "0.00", {}, {}]
            
            # --- TELEMETRY PLOTS ---
            plots = TelemetryPlots()
            speed_fig = plots.create_speed_plot(df)
            pedal_fig = plots.create_pedal_plot(df)
            track_fig = plots.create_track_map(df)
            
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
            
            return [speed_fig, pedal_fig, track_fig, speed_val, fuel_val, fuel_msg, delta_str, delta_style, bar_style]
            
        except Exception as e:
            return [{}, {}, {}, "ERR", "0.0", f"Error: {str(e)}", "0.00", {}, {}]

    @app.callback(
        [Output('analysis-gforce-map', 'figure'),
         Output('analysis-tire-wear', 'figure')],
        [Input('update-interval', 'n_intervals')],
        [Input('main-tabs', 'value')]
    )
    def update_analysis_tab(n, active_tab):
        if active_tab != 'analysis' or not Path("live_data.json").exists():
            return [{}, {}]
        
        try:
            df = pd.read_json("live_data.json")
            plots = TelemetryPlots()
            g_fig = plots.create_g_force_plot(df)
            t_fig = plots.create_tire_wear_plot(df)
            return [g_fig, t_fig]
        except Exception:
            return [{}, {}]

    @app.callback(
        [Output('engineer-feedback-list', 'children'),
         Output('strategy-recommendations', 'children')],
        [Input('update-interval', 'n_intervals')],
        [Input('main-tabs', 'value')]
    )
    def update_strategy_tab(n, active_tab):
        if active_tab != 'strategy':
            return [[], []]
            
        feedback_items = []
        if Path("engineer_feedback.json").exists():
            with open("engineer_feedback.json", "r", encoding="utf-8") as f:
                report = json.load(f)
                for msg in report.get("all_feedback", []):
                    feedback_items.append(html.Div(f"📻 {msg}", style={'padding': '5px', 'borderBottom': '1px solid #2c2d33'}))
        
        if not feedback_items:
            feedback_items = [html.Div("No feedback available for this lap.", style={'color': '#8e8e93'})]
            
        # Mock strategy advice for now
        strategy = [
            html.Div("⛽ Plan: Standard fuel mixture. Pit on Lap 18 recommended.", style={'color': '#00d2be'})
        ]
        
        return [feedback_items, strategy]
