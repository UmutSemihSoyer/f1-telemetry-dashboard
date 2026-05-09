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
    def create_track_map(df):
        # 2D track map using PosX and PosZ
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['PosX'], y=df['PosZ'],
            mode='lines',
            line=dict(color='#e1e1e1', width=3),
            name='Track'
        ))
        # Current position marker
        fig.add_trace(go.Scatter(
            x=[df['PosX'].iloc[-1]], y=[df['PosZ'].iloc[-1]],
            mode='markers',
            marker=dict(size=12, color='#ff1801', symbol='triangle-up'),
            name='Current Pos'
        ))
        fig.update_layout(
            title="Track Position",
            showlegend=False,
            xaxis=dict(visible=False),
            yaxis=dict(visible=False, scaleanchor="x", scaleratio=1),
            **PLOTLY_DARK['layout']
        )
        return fig
