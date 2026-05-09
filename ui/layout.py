from dash import html, dcc
import os

def create_header():
    stream_url = ""
    if os.path.exists('stream_url.txt'):
        with open('stream_url.txt', 'r') as f:
            stream_url = f.read().strip()

    return html.Div(className='header-bar', children=[
        html.Div(className='header', children=[
            html.Div(children=[
                html.H1("F1 2022 PIT WALL PRO", style={'margin': '0', 'letterSpacing': '2px'}),
                html.Div("GOD-TIER TELEMETRY SUITE", style={'fontSize': '12px', 'color': '#8e8e93', 'letterSpacing': '1px'})
            ]),
            html.Div(id='live-stream-link', children=[
                html.A("Watch Stream", href=stream_url, target="_blank") if stream_url else ""
            ], style={'color': '#9b00ef', 'fontWeight': 'bold', 'fontSize': '14px'})
        ]),
        html.Div(id='connection-status', children=[
            html.Span("● LIVE", className='critical-alert', style={'fontSize': '0.8rem', 'fontWeight': 'bold'})
        ])
    ])

def create_live_hud():
    return html.Div(className='main-container', children=[
        html.Div(className='row', style={'display': 'flex', 'gap': '20px'}, children=[
            # Left Panel: Main Telemetry
            html.Div(style={'flex': '2'}, children=[
                html.Div(className='card', children=[
                    html.Div("Real-Time Telemetry", className='card-title'),
                    dcc.Graph(id='live-speed-graph', config={'displayModeBar': False})
                ]),
                html.Div(className='card', children=[
                    html.Div("Pedal Inputs", className='card-title'),
                    dcc.Graph(id='live-pedal-graph', config={'displayModeBar': False})
                ])
            ]),
            # Right Panel: Indicators
            html.Div(style={'flex': '1'}, children=[
                html.Div(className='card', children=[
                    html.Div("Current Speed", className='card-title'),
                    html.Div(className='indicator-value', children=[
                        html.Span(id='live-speed-value', children="0"),
                        html.Span("km/h", className='indicator-unit')
                    ])
                ]),
                html.Div(className='card', children=[
                    html.Div("Fuel Status", className='card-title'),
                    html.Div(className='indicator-value', children=[
                        html.Span(id='live-fuel-value', children="0.0"),
                        html.Span("kg", className='indicator-unit')
                    ]),
                    html.Div(id='fuel-prediction', style={'marginTop': '10px', 'fontSize': '0.9rem'})
                ]),
                html.Div(className='card', children=[
                    html.Div("ERS Battery", className='card-title'),
                    html.Div(className='indicator-value', children=[
                        html.Span(id='live-ers-value', children="0"),
                        html.Span("%", className='indicator-unit')
                    ]),
                    html.Div(id='live-ers-bar-wrap', style={
                        'height': '8px', 'width': '100%', 'backgroundColor': '#2c2d33',
                        'borderRadius': '4px', 'marginTop': '10px', 'overflow': 'hidden'
                    }, children=[
                        html.Div(id='live-ers-bar', style={
                            'height': '100%', 'width': '0%',
                            'backgroundColor': '#9b00ef', 'transition': 'width 0.3s'
                        })
                    ])
                ]),
                html.Div(className='card', children=[
                    html.Div("Gap to Car Ahead", className='card-title'),
                    html.Div(className='indicator-value', children=[
                        html.Span(id='live-gap-ahead', children="--"),
                        html.Span("s", className='indicator-unit')
                    ])
                ]),
                html.Div(className='card', children=[
                    html.Div("Gap to Car Behind", className='card-title'),
                    html.Div(className='indicator-value', children=[
                        html.Span(id='live-gap-behind', children="--"),
                        html.Span("s", className='indicator-unit')
                    ])
                ]),
                html.Div(className='card', children=[
                    html.Div("Live Delta", className='card-title'),
                    html.Div(id='live-delta-container', style={'textAlign': 'center'}, children=[
                        html.Div(id='live-delta-value', className='indicator-value', children="0.00"),
                        html.Div(id='live-delta-bar', style={
                            'height': '10px', 'width': '100%', 'backgroundColor': '#2c2d33',
                            'borderRadius': '5px', 'marginTop': '10px', 'overflow': 'hidden'
                        }, children=[
                            html.Div(id='live-delta-bar-inner', style={'height': '100%', 'width': '50%', 'transition': 'all 0.2s'})
                        ])
                    ])
                ]),
                html.Div(className='card', children=[
                    html.Div("Track Map", className='card-title'),
                    dcc.Graph(id='live-track-map', config={'displayModeBar': False})
                ])
            ])
        ])
    ])

def create_analysis_tab():
    return html.Div(className='main-container', children=[
        html.Div(className='row', style={'display': 'flex', 'gap': '20px', 'marginBottom': '20px'}, children=[
            html.Div(className='card', style={'flex': '1'}, children=[
                html.Div("G-Force Distribution", className='card-title'),
                dcc.Graph(id='analysis-gforce-map')
            ]),
            html.Div(className='card', style={'flex': '1'}, children=[
                html.Div("Tyre Thermal State", className='card-title'),
                dcc.Graph(id='analysis-tire-wear')
            ])
        ]),
        html.Div(className='card', style={'marginBottom': '20px'}, children=[
            html.Div("Lap History", className='card-title'),
            html.Div(id='lap-history-table')
        ]),
        html.Div(className='card', children=[
            html.Div("Multi-Lap Comparison Overlay", className='card-title'),
            html.Div(style={'display': 'flex', 'gap': '20px', 'marginBottom': '10px'}, children=[
                dcc.Dropdown(id='compare-lap-1', placeholder="Select Lap A", style={'flex': '1', 'color': '#000'}),
                dcc.Dropdown(id='compare-lap-2', placeholder="Select Lap B", style={'flex': '1', 'color': '#000'})
            ]),
            dcc.Graph(id='compare-graph')
        ]),
        html.Div(className='card', style={'marginTop': '20px'}, children=[
            html.Div("Export Analysis", className='card-title'),
            html.Button("Export Current Session to MoTeC (CSV)", id='btn-export-motec', className='btn-primary'),
            html.Div(id='export-motec-status', style={'marginTop': '10px', 'color': '#00d2be'})
        ])
    ])

def create_strategy_tab():
    return html.Div(className='main-container', children=[
        html.Div(className='card', children=[
            html.Div("Race Engineer Feedback", className='card-title'),
            html.Div(id='engineer-feedback-list')
        ]),
        html.Div(className='card', children=[
            html.Div("Strategy Recommendations", className='card-title'),
            html.Div(id='strategy-recommendations')
        ]),
        html.Div(className='row', style={'display': 'flex', 'gap': '20px'}, children=[
            html.Div(className='card', style={'flex': '1'}, children=[
                html.Div("Interactive Strategy Planner", className='card-title'),
                html.Div(style={'display': 'flex', 'alignItems': 'center', 'gap': '10px', 'marginBottom': '10px'}, children=[
                    html.Label("Pit 1 Lap:", style={'color': '#8e8e93'}),
                    dcc.Input(id='strat-pit-1', type='number', value=15, style={'width': '60px', 'backgroundColor': '#1a1b1e', 'color': '#fff', 'border': '1px solid #2c2d33'}),
                    html.Label("Pit 2 Lap:", style={'color': '#8e8e93'}),
                    dcc.Input(id='strat-pit-2', type='number', value=35, style={'width': '60px', 'backgroundColor': '#1a1b1e', 'color': '#fff', 'border': '1px solid #2c2d33'}),
                ]),
                html.Div(id='strat-planner-output', style={'color': '#00d2be', 'fontWeight': 'bold', 'marginBottom': '10px'})
            ]),
            html.Div(className='card', style={'flex': '1'}, children=[
                html.Div("Rain Radar (30m Forecast)", className='card-title'),
                dcc.Graph(id='weather-radar-graph', config={'displayModeBar': False}, style={'height': '150px'})
            ])
        ])
    ])

def create_setup_tab():
    return html.Div(className='main-container', children=[
        html.Div(className='row', style={'display': 'flex', 'gap': '20px', 'marginBottom': '20px'}, children=[
            html.Div(className='card', style={'flex': '1'}, children=[
                html.Div("Suspension Travel (Bottoming Out)", className='card-title'),
                dcc.Graph(id='setup-suspension-graph')
            ]),
            html.Div(className='card', style={'flex': '1'}, children=[
                html.Div("Wheel Slip (Traction/Lockup)", className='card-title'),
                dcc.Graph(id='setup-slip-graph')
            ])
        ])
    ])

def create_race_control_tab():
    return html.Div(className='main-container', children=[
        html.Div(className='card', children=[
            html.Div("Live Timing Tower", className='card-title'),
            html.Div(id='race-control-table')
        ])
    ])

def get_layout():
    return html.Div([
        create_header(),
        dcc.Tabs(id='main-tabs', value='live', className='custom-tabs-container', children=[
            dcc.Tab(label='Live HUD', value='live', className='custom-tab', selected_className='custom-tab--selected'),
            dcc.Tab(label='Data Analysis', value='analysis', className='custom-tab', selected_className='custom-tab--selected'),
            dcc.Tab(label='Strategy', value='strategy', className='custom-tab', selected_className='custom-tab--selected'),
            dcc.Tab(label='Setup Tuning', value='setup', className='custom-tab', selected_className='custom-tab--selected'),
            dcc.Tab(label='Race Control', value='race_control', className='custom-tab', selected_className='custom-tab--selected'),
        ]),
        html.Div(id='tabs-content'),
        dcc.Interval(id='update-interval', interval=500, n_intervals=0),
        dcc.Store(id='best-lap-store')
    ])
