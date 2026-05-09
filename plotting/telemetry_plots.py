import plotly.graph_objects as go
import plotly.express as px

# Shared Dark Theme for Plotly
PLOTLY_DARK = {
    'layout': {
        'plot_bgcolor': 'rgba(0,0,0,0)',
        'paper_bgcolor': 'rgba(0,0,0,0)',
        'font': {'color': '#e1e1e1', 'family': 'Inter'},
        'margin': {'t': 40, 'b': 40, 'l': 50, 'r': 10},
        'xaxis': {'gridcolor': '#2c2d33', 'zerolinecolor': '#2c2d33'},
        'yaxis': {'gridcolor': '#2c2d33', 'zerolinecolor': '#2c2d33'},
    }
}

class TelemetryPlots:
    @staticmethod
    def create_speed_plot(df):
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df.index, y=df['Speed'],
            mode='lines',
            name='Speed',
            line=dict(color='#00d2be', width=2),
            fill='tozeroy',
            fillcolor='rgba(0, 210, 190, 0.1)'
        ))
        fig.update_layout(title="Speed (km/h)", **PLOTLY_DARK['layout'])
        return fig

    @staticmethod
    def create_pedal_plot(df):
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df.index, y=df['Throttle'] * 100,
            mode='lines',
            name='Throttle',
            line=dict(color='#00ff88', width=2)
        ))
        fig.add_trace(go.Scatter(
            x=df.index, y=df['Brake'] * 100,
            mode='lines',
            name='Brake',
            line=dict(color='#ff1801', width=2)
        ))
        fig.update_layout(title="Pedal Inputs (%)", **PLOTLY_DARK['layout'])
        fig.update_yaxes(range=[0, 105])
        return fig

    @staticmethod
    def create_tire_wear_plot(df):
        latest = df.iloc[-1]
        tires  = ['FL', 'FR', 'RL', 'RR']
        values = [latest.get(f'TyreWear{t}', 0) for t in tires]

        fig = go.Figure(data=[
            go.Bar(x=tires, y=values,
                   marker_color=['#00d2be', '#00d2be', '#9b00ef', '#9b00ef'])
        ])
        fig.update_layout(title="Tyre Wear (%)", **PLOTLY_DARK['layout'])
        fig.update_yaxes(range=[0, 100])
        return fig


    @staticmethod
    def create_g_force_plot(df):
        fig = go.Figure()
        # G-Force bubble plot (longitudinal vs lateral)
        fig.add_trace(go.Scatter(
            x=df['GLat'], y=df['GLon'],
            mode='markers',
            marker=dict(
                size=8,
                color=df.index,
                colorscale='Viridis',
                opacity=0.6
            )
        ))
        # Add center crosshair
        fig.add_shape(type="line", x0=-5, y0=0, x1=5, y1=0, line=dict(color="#2c2d33", width=1))
        fig.add_shape(type="line", x0=0, y0=-5, x1=0, y1=5, line=dict(color="#2c2d33", width=1))
        
        fig.update_layout(
            title="G-Force Map",
            xaxis=dict(title="Lateral G", range=[-5, 5]),
            yaxis=dict(title="Longitudinal G", range=[-5, 5]),
            **PLOTLY_DARK['layout']
        )
        return fig

    @staticmethod
    def create_track_map(df, best_lap_df=None):
        fig = go.Figure()
        
        if df is None or df.empty or 'PosX' not in df.columns or 'PosZ' not in df.columns:
            fig.update_layout(title="Track Position (No Data)", **PLOTLY_DARK['layout'])
            return fig
            
        # 2D track map using PosX and PosZ
        fig.add_trace(go.Scatter(
            x=df['PosX'], y=df['PosZ'],
            mode='lines',
            line=dict(color='#e1e1e1', width=3),
            name='Track'
        ))
        
        # Ghost Car Position (Best Lap)
        if best_lap_df is not None and not best_lap_df.empty:
            current_dist = df['LapDistance'].iloc[-1]
            diffs = (best_lap_df['LapDistance'] - current_dist).abs()
            ghost_idx = diffs.idxmin()
            ghost_pt = best_lap_df.loc[ghost_idx]
            
            fig.add_trace(go.Scatter(
                x=[ghost_pt['PosX']], y=[ghost_pt['PosZ']],
                mode='markers',
                marker=dict(size=12, color='rgba(155, 0, 239, 0.4)', symbol='circle'),
                name='Ghost (Best Lap)'
            ))

        # Current position marker
        if len(df) > 0:
            fig.add_trace(go.Scatter(
                x=[df['PosX'].iloc[-1]], y=[df['PosZ'].iloc[-1]],
                mode='markers',
                marker=dict(size=14, color='#ff1801', symbol='circle'),
                name='Live Car'
            ))
            
        fig.update_layout(
            title="Track Position",
            showlegend=False,
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            **PLOTLY_DARK['layout']
        )
        return fig

    @staticmethod
    def create_suspension_plot(df):
        fig = go.Figure()
        if df is None or df.empty or 'SuspPosFL' not in df.columns:
            fig.update_layout(title="Suspension Travel (No Data)", **PLOTLY_DARK['layout'])
            return fig
            
        fig.add_trace(go.Scatter(y=df['SuspPosFL'], mode='lines', name='FL', line=dict(color='#00d2be')))
        fig.add_trace(go.Scatter(y=df['SuspPosFR'], mode='lines', name='FR', line=dict(color='#ff1801')))
        fig.add_trace(go.Scatter(y=df['SuspPosRL'], mode='lines', name='RL', line=dict(color='#e1e1e1')))
        fig.add_trace(go.Scatter(y=df['SuspPosRR'], mode='lines', name='RR', line=dict(color='#9b00ef')))
        
        fig.update_layout(
            title="Suspension Compression",
            yaxis=dict(title="Position"),
            xaxis=dict(title="Recent History"),
            **PLOTLY_DARK['layout']
        )
        return fig

    @staticmethod
    def create_slip_plot(df):
        fig = go.Figure()
        if df is None or df.empty or 'WheelSlipFL' not in df.columns:
            fig.update_layout(title="Wheel Slip (No Data)", **PLOTLY_DARK['layout'])
            return fig
            
        fig.add_trace(go.Scatter(y=df['WheelSlipRL'], mode='lines', name='RL (Traction)', line=dict(color='#e1e1e1')))
        fig.add_trace(go.Scatter(y=df['WheelSlipRR'], mode='lines', name='RR (Traction)', line=dict(color='#9b00ef')))
        fig.add_trace(go.Scatter(y=df['WheelSlipFL'], mode='lines', name='FL (Lockup)', line=dict(color='#00d2be')))
        fig.add_trace(go.Scatter(y=df['WheelSlipFR'], mode='lines', name='FR (Lockup)', line=dict(color='#ff1801')))
        
        fig.update_layout(
            title="Wheel Slip Ratio",
            yaxis=dict(title="Slip"),
            xaxis=dict(title="Recent History"),
            **PLOTLY_DARK['layout']
        )
        return fig

    @staticmethod
    def create_lap_comparison_plot(df_lap1, df_lap2, lap1_name="Lap 1", lap2_name="Lap 2"):
        from plotly.subplots import make_subplots
        
        if (df_lap1 is None or df_lap1.empty) and (df_lap2 is None or df_lap2.empty):
            fig = go.Figure()
            fig.update_layout(title="Multi-Lap Comparison (No Laps Selected)", **PLOTLY_DARK['layout'])
            return fig

        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, 
                            subplot_titles=("Speed (km/h)", "Throttle & Brake"))

        if df_lap1 is not None and not df_lap1.empty and 'LapDistance' in df_lap1.columns:
            # Lap 1 Speed
            fig.add_trace(go.Scatter(x=df_lap1['LapDistance'], y=df_lap1['Speed'], mode='lines', 
                                     name=f'{lap1_name} Speed', line=dict(color='#00d2be')), row=1, col=1)
            # Lap 1 Throttle/Brake
            fig.add_trace(go.Scatter(x=df_lap1['LapDistance'], y=df_lap1['Throttle'], mode='lines', 
                                     name=f'{lap1_name} Throttle', line=dict(color='#00d2be', dash='dot')), row=2, col=1)
            fig.add_trace(go.Scatter(x=df_lap1['LapDistance'], y=df_lap1['Brake'], mode='lines', 
                                     name=f'{lap1_name} Brake', line=dict(color='#ff1801', dash='dot')), row=2, col=1)

        if df_lap2 is not None and not df_lap2.empty and 'LapDistance' in df_lap2.columns:
            # Lap 2 Speed
            fig.add_trace(go.Scatter(x=df_lap2['LapDistance'], y=df_lap2['Speed'], mode='lines', 
                                     name=f'{lap2_name} Speed', line=dict(color='#e1e1e1')), row=1, col=1)
            # Lap 2 Throttle/Brake
            fig.add_trace(go.Scatter(x=df_lap2['LapDistance'], y=df_lap2['Throttle'], mode='lines', 
                                     name=f'{lap2_name} Throttle', line=dict(color='#e1e1e1', dash='dot')), row=2, col=1)
            fig.add_trace(go.Scatter(x=df_lap2['LapDistance'], y=df_lap2['Brake'], mode='lines', 
                                     name=f'{lap2_name} Brake', line=dict(color='#9b00ef', dash='dot')), row=2, col=1)

        fig.update_layout(
            height=500,
            hovermode='x unified',
            **PLOTLY_DARK['layout']
        )
        # Fix xaxis titles
        fig.update_xaxes(title_text="Lap Distance (m)", row=2, col=1)
        return fig

    @staticmethod
    def create_weather_radar_plot(forecasts):
        fig = go.Figure()
        
        if not forecasts:
            fig.update_layout(title="No Forecast Data", **PLOTLY_DARK['layout'])
            return fig
            
        times = [f['TimeOffset'] for f in forecasts]
        rains = [f['RainPct'] for f in forecasts]
        
        # Color bar based on rain percentage
        colors = ['#00d2be' if r < 20 else '#ff1801' if r > 70 else '#e1e1e1' for r in rains]
        
        fig.add_trace(go.Bar(
            x=times, y=rains,
            marker_color=colors,
            name='Rain %'
        ))
        
        fig.update_layout(
            margin=dict(l=20, r=20, t=30, b=20),
            height=150,
            yaxis=dict(title="Rain %", range=[0, 100]),
            xaxis=dict(title="Minutes Ahead"),
            **PLOTLY_DARK['layout']
        )
        return fig
