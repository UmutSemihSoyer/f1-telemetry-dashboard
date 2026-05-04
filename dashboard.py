"""
dashboard.py — F1 2022 V10 Pit Wall  
Sekmeler: Live | Fizik & Strateji | Sanal Mühendis | Tarihsel & F1 Karsilastirma
"""
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import sqlite3
import json
import os
import math
import flask

from analytics_physics import (
    calculate_fuel_load, calculate_braking_distance,
    TyreThermalModel, calculate_overtake_window,
    fuel_deficit_analysis, simulate_lap_thermal, braking_distance_sweep,
    dynamic_pit_loss, lift_and_coast_savings
)
from ergast_api import fetch_race_laps, build_comparison_df, CIRCUIT_MAP

# ─────────────────────────────────────────────────────────
server = flask.Flask(__name__)
app    = dash.Dash(__name__, server=server, title="F1 2022 Pit Wall V9")

DARK = dict(plot_bgcolor='#111', paper_bgcolor='#0d0d0d',
            font_color='#ddd', margin=dict(l=35,r=15,t=38,b=25))
COMPOUND_COLORS = {"Soft":"#ff3366","Medium":"#ffcc00","Hard":"#e0e0e0",
                   "Intermediate":"#00cc44","Wet":"#0088ff"}
WEATHER_NAMES   = {0:"☀ Clear",1:"Light Cloud",2:"Overcast",
                   3:"Light Rain",4:"Heavy Rain",5:"Storm"}
SAFETY_NAMES    = {0:"",1:"Safety Car",2:"Virtual SC",3:"Formation Lap"}

# ─────────────────────────────────────────────────────────
# REST API
# ─────────────────────────────────────────────────────────
@server.route("/api/live")
def api_live():
    if not os.path.exists("live_data.json"): return flask.jsonify({"error":"no data"})
    with open("live_data.json") as f: return flask.Response(f.read(), mimetype="application/json")

@server.route("/api/alerts")
def api_alerts():
    if not os.path.exists("alerts.json"): return flask.jsonify([])
    with open("alerts.json") as f: return flask.Response(f.read(), mimetype="application/json")

@server.route("/api/laps")
def api_laps():
    if not os.path.exists("telemetry.db"): return flask.jsonify([])
    conn=sqlite3.connect("telemetry.db"); df=pd.read_sql_query("SELECT * FROM lap_times ORDER BY lap_num",conn); conn.close()
    return flask.Response(df.to_json(orient="records"), mimetype="application/json")

@server.route("/api/braking")
def api_braking():
    if not os.path.exists("braking_points.json"): return flask.jsonify([])
    with open("braking_points.json") as f: return flask.Response(f.read(), mimetype="application/json")

@server.route("/api/optimal_braking")
def api_optimal():
    if not os.path.exists("optimal_braking.json"): return flask.jsonify([])
    with open("optimal_braking.json") as f: return flask.Response(f.read(), mimetype="application/json")

# ─────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────
def rj(path, default=None):
    try:
        if not os.path.exists(path): return default or []
        with open(path) as f: return json.load(f)
    except: return default or []

def load_laps():
    if not os.path.exists("telemetry.db"): return pd.DataFrame()
    try:
        conn=sqlite3.connect("telemetry.db")
        df=pd.read_sql_query("SELECT session_id,lap_num,sector1_ms,sector2_ms,lap_time_ms FROM lap_times ORDER BY lap_num",conn); conn.close()
        for c in ['lap_num','sector1_ms','sector2_ms','lap_time_ms']:
            df[c]=pd.to_numeric(df[c],errors='coerce').fillna(0).astype(int)
        return df
    except: return pd.DataFrame()

def load_all_sessions():
    if not os.path.exists("telemetry.db"): return pd.DataFrame()
    try:
        conn=sqlite3.connect("telemetry.db")
        df=pd.read_sql_query("SELECT session_id,lap_num,lap_time_ms FROM session_history ORDER BY session_id,lap_num",conn); conn.close()
        for c in ['lap_num','lap_time_ms']:
            df[c]=pd.to_numeric(df[c],errors='coerce').fillna(0).astype(int)
        return df
    except: return pd.DataFrame()

def card(title, value, color="#fff", bg="#1a1a1a", icon="", sub=""):
    return html.Div(style={
        'background':bg,'borderRadius':'10px','padding':'10px 14px',
        'minWidth':'120px','flex':'1','border':f'1px solid {color}33','boxShadow':f'0 0 8px {color}18'},
        children=[
            html.Div(f"{icon} {title}", style={'fontSize':'10px','color':'#666','marginBottom':'2px'}),
            html.Div(value, style={'fontSize':'20px','fontWeight':'bold','color':color}),
            html.Div(sub,   style={'fontSize':'10px','color':'#555'}) if sub else None
        ])

def ef(title=""): f=go.Figure(); f.update_layout(title=title,**DARK); return f

TAB_STYLE        = {'backgroundColor':'#1a1a1a','color':'#888','border':'none','padding':'8px 16px','fontSize':'13px'}
TAB_SELECTED     = {'backgroundColor':'#ff1e00','color':'#fff','border':'none','padding':'8px 16px','fontSize':'13px','fontWeight':'bold'}

# ─────────────────────────────────────────────────────────
# LAYOUT
# ─────────────────────────────────────────────────────────
app.layout = html.Div(
    style={'backgroundColor':'#0d0d0d','color':'#fff','fontFamily':'"Segoe UI",Helvetica,sans-serif',
           'padding':'10px','maxWidth':'1800px','margin':'0 auto'},
    children=[
        html.H1("🏎 F1 2022 Pit Wall V9",
                style={'textAlign':'center','color':'#ff1e00','margin':'0 0 4px 0','fontSize':'22px'}),
        html.Div(id='live-status',
                 style={'textAlign':'center','fontSize':'12px','color':'#666','marginBottom':'8px'}),

        html.Div(id='alert-banner', style={'marginBottom':'8px'}),
        html.Div(id='info-cards',
                 style={'display':'flex','gap':'8px','marginBottom':'10px','flexWrap':'wrap'}),
        html.Div(id='weather-row',
                 style={'display':'flex','gap':'8px','marginBottom':'8px','flexWrap':'wrap'}),
        html.Div(id='delta-bar', style={'marginBottom':'8px'}),

        # ════ TABS ════
        dcc.Tabs(id='tabs', value='live',
                 style={'marginBottom':'10px'},
                 children=[
            # ─── TAB 1: CANLI ───────────────────────────────────────
            dcc.Tab(label='🔴 CANLI', value='live',
                    style=TAB_STYLE, selected_style=TAB_SELECTED,
                    children=[
                        html.Div(style={'display':'flex','flexWrap':'wrap','gap':'8px','marginBottom':'8px'},children=[
                            html.Div(dcc.Graph(id='speed-graph'), style={'flex':'60 1 400px','minWidth':'0'}),
                            html.Div(dcc.Graph(id='inputs-graph'), style={'flex':'40 1 260px','minWidth':'0'}),
                        ]),
                        html.Div(style={'display':'flex','flexWrap':'wrap','gap':'8px','marginBottom':'8px'},children=[
                            html.Div(dcc.Graph(id='tyre-graph'),    style={'flex':'50 1 300px','minWidth':'0'}),
                            html.Div(dcc.Graph(id='tyretemp-graph'),style={'flex':'50 1 300px','minWidth':'0'}),
                        ]),
                        html.Div(style={'display':'flex','flexWrap':'wrap','gap':'8px','marginBottom':'8px'},children=[
                            html.Div(dcc.Graph(id='track-graph'),  style={'flex':'60 1 380px','minWidth':'0'}),
                            html.Div(dcc.Graph(id='gforce-graph'), style={'flex':'40 1 250px','minWidth':'0'}),
                        ]),
                        html.Div(style={'display':'flex','flexWrap':'wrap','gap':'8px','marginBottom':'8px'},children=[
                            html.Div(dcc.Graph(id='sector-graph'), style={'flex':'50 1 300px','minWidth':'0'}),
                            html.Div(dcc.Graph(id='gap-graph'),    style={'flex':'50 1 300px','minWidth':'0'}),
                        ]),
                        html.Div(dcc.Graph(id='rpm-graph')),
                    ]),

            # ─── TAB 2: FİZİK & STRATEJİ ────────────────────────────
            dcc.Tab(label='⚙ Fizik & Strateji', value='physics',
                    style=TAB_STYLE, selected_style=TAB_SELECTED,
                    children=[
                        # Row: 3D Track + ERS Enerji Haritasi
                        html.Div(style={'display':'flex','flexWrap':'wrap','gap':'8px','marginBottom':'8px'},children=[
                            html.Div(dcc.Graph(id='track3d-graph'),   style={'flex':'55 1 350px','minWidth':'0'}),
                            html.Div(dcc.Graph(id='ers-harvest-graph'),style={'flex':'45 1 300px','minWidth':'0'}),
                        ]),
                        # Tire Thermal Simulation
                        html.Div(dcc.Graph(id='thermal-graph'), style={'marginBottom':'8px'}),

                        # Interactive Calculators Row
                        html.Div(style={'display':'flex','flexWrap':'wrap','gap':'12px','marginBottom':'12px'},children=[
                            # ── Yakit Yuk Hesaplayicisi
                            html.Div(style={'flex':'1','minWidth':'280px','background':'#141414',
                                            'borderRadius':'10px','padding':'14px','border':'1px solid #222'},children=[
                                html.H4("⛽ Yakit Yuk Hesaplayicisi",
                                        style={'color':'#ffbb00','margin':'0 0 10px 0','fontSize':'14px'}),
                                html.Div(style={'display':'grid','gridTemplateColumns':'1fr 1fr','gap':'8px'},children=[
                                    html.Div([html.Label("Tur Sayisi", style={'fontSize':'11px','color':'#888'}),
                                              dcc.Input(id='inp-laps',type='number',value=57,min=1,max=100,
                                                        style={'width':'100%','background':'#222','color':'#fff',
                                                               'border':'1px solid #444','borderRadius':'4px','padding':'4px'})]),
                                    html.Div([html.Label("Yakit/tur (kg)", style={'fontSize':'11px','color':'#888'}),
                                              dcc.Input(id='inp-fuelrate',type='number',value=2.2,min=1.0,max=4.0,step=0.1,
                                                        style={'width':'100%','background':'#222','color':'#fff',
                                                               'border':'1px solid #444','borderRadius':'4px','padding':'4px'})]),
                                    html.Div([html.Label("SC Olasiligi %", style={'fontSize':'11px','color':'#888'}),
                                              dcc.Slider(id='sl-sc-prob',min=0,max=100,step=10,value=40,
                                                         marks={0:'0',50:'50',100:'100'})]),
                                    html.Div([html.Label("SC Turu Sayisi", style={'fontSize':'11px','color':'#888'}),
                                              dcc.Slider(id='sl-sc-laps',min=0,max=10,step=1,value=3,
                                                         marks={0:'0',5:'5',10:'10'})]),
                                ]),
                                html.Div(id='fuel-calc-result', style={'marginTop':'10px'}),
                            ]),

                            # ── Fren Mesafesi Hesaplayicisi
                            html.Div(style={'flex':'1','minWidth':'280px','background':'#141414',
                                            'borderRadius':'10px','padding':'14px','border':'1px solid #222'},children=[
                                html.H4("🛑 Fren Mesafesi Hesaplayicisi",
                                        style={'color':'#ff4444','margin':'0 0 10px 0','fontSize':'14px'}),
                                html.Div(style={'display':'grid','gridTemplateColumns':'1fr 1fr','gap':'8px'},children=[
                                    html.Div([html.Label("Giris Hizi (km/h)", style={'fontSize':'11px','color':'#888'}),
                                              dcc.Slider(id='sl-ventry',min=100,max=380,step=10,value=300,
                                                         marks={100:'100',200:'200',300:'300',380:'380'})]),
                                    html.Div([html.Label("Viraj Hizi (km/h)", style={'fontSize':'11px','color':'#888'}),
                                              dcc.Slider(id='sl-vcorner',min=40,max=200,step=10,value=80,
                                                         marks={40:'40',100:'100',200:'200'})]),
                                    html.Div([html.Label("Yavastama (G)", style={'fontSize':'11px','color':'#888'}),
                                              dcc.Slider(id='sl-decel',min=2.0,max=6.0,step=0.5,value=4.5,
                                                         marks={2:'2g',4:'4g',6:'6g'})]),
                                    html.Div(id='brake-dist-result'),
                                ]),
                                html.Div(dcc.Graph(id='brake-sweep-graph'), style={'marginTop':'8px'}),
                            ]),
                        ]),

                        # Overtake Window + Fuel Deficit cards (live)
                        html.Div(id='overtake-card', style={'marginBottom':'8px'}),
                    ]),

            # ─── TAB 3: SANAL MÜHENDİS (V10) ────────────────────────
            dcc.Tab(label='🧠 Sanal Mühendis', value='engineer',
                    style=TAB_STYLE, selected_style=TAB_SELECTED,
                    children=[
                        html.Div(style={'display':'flex','flexWrap':'wrap','gap':'12px','marginBottom':'12px'},children=[
                            # Sol panel: Radar Grafiği (Driver Profiling)
                            html.Div(style={'flex':'1','minWidth':'300px','background':'#141414',
                                            'borderRadius':'10px','padding':'14px','border':'1px solid #222'},children=[
                                html.H4("🧑‍🚀 Sürücü Profili (Fingerprint)",
                                        style={'color':'#00d4ff','margin':'0 0 10px 0','fontSize':'14px'}),
                                dcc.Graph(id='engineer-radar-graph')
                            ]),
                            
                            # Sağ panel: Actionable Feedback
                            html.Div(style={'flex':'2','minWidth':'400px','background':'#141414',
                                            'borderRadius':'10px','padding':'14px','border':'1px solid #222'},children=[
                                html.H4("📻 Yarış Mühendisi Tavsiyeleri",
                                        style={'color':'#ffbb00','margin':'0 0 10px 0','fontSize':'14px'}),
                                html.Div(id='engineer-feedback-list', style={'display':'flex','flexDirection':'column','gap':'8px'})
                            ]),
                        ])
                    ]),

            # ─── TAB 4: TARİHSEL & F1 KARSILASTIRMA ─────────────────
            dcc.Tab(label='📈 Tarihsel & F1', value='historical',
                    style=TAB_STYLE, selected_style=TAB_SELECTED,
                    children=[
                        # Calendar Heatmap
                        html.Div(dcc.Graph(id='calendar-heatmap'), style={'marginBottom':'8px'}),
                        # Session Compare
                        html.Div(dcc.Graph(id='session-compare-graph'), style={'marginBottom':'8px'}),
                        # Ergast F1 Karsilastirma
                        html.Div(style={'background':'#141414','borderRadius':'10px','padding':'14px',
                                        'border':'1px solid #222','marginBottom':'8px'},children=[
                            html.H4("🏁 Gercek F1 Karsilastirmasi (Ergast API)",
                                    style={'color':'#00d4ff','margin':'0 0 10px 0','fontSize':'14px'}),
                            html.Div(style={'display':'flex','gap':'12px','alignItems':'center','flexWrap':'wrap',
                                            'marginBottom':'10px'},children=[
                                html.Div([
                                    html.Label("Pist / Yil Sec:", style={'fontSize':'11px','color':'#888'}),
                                    dcc.Dropdown(id='dd-circuit',
                                                 options=[{"label":k,"value":k} for k in CIRCUIT_MAP.keys()],
                                                 value="Italy/Monza 2024",
                                                 style={'width':'280px','backgroundColor':'#222','color':'#000'}),
                                ]),
                                html.Button("🔄 Veri Cek", id='btn-fetch-ergast',
                                            style={'backgroundColor':'#00d4ff','color':'#000','border':'none',
                                                   'borderRadius':'6px','padding':'8px 16px','cursor':'pointer',
                                                   'fontWeight':'bold','alignSelf':'flex-end'}),
                                html.Span(id='ergast-status', style={'color':'#888','fontSize':'12px','alignSelf':'flex-end'}),
                            ]),
                            dcc.Graph(id='ergast-compare-graph'),
                        ]),
                    ]),
        ]),

        # ════ ALWAYS VISIBLE: PIT SIMULATOR + SETTINGS ════
        html.Div(style={'background':'#141414','border':'1px solid #333','borderRadius':'12px',
                        'padding':'16px','marginBottom':'10px'},children=[
            html.H3("🔧 Pit Stop Simulatoru",style={'color':'#ff8800','margin':'0 0 10px 0','fontSize':'16px'}),
            html.Div(style={'display':'flex','gap':'20px','alignItems':'center','flexWrap':'wrap'},children=[
                html.Div(style={'flex':'1','minWidth':'200px'},children=[
                    html.Label("Pit Lap Sec:", style={'fontSize':'12px','color':'#aaa'}),
                    dcc.Slider(id='pit-lap-slider',min=1,max=50,step=1,value=10,
                               marks={i:str(i) for i in range(5,51,5)},
                               tooltip={"placement":"bottom","always_visible":True}),
                ]),
                html.Div(id='pit-sim-result',style={'flex':'1','minWidth':'200px','fontSize':'14px'}),
            ]),
        ]),

        html.Div(style={'background':'#141414','border':'1px solid #222','borderRadius':'12px',
                        'padding':'14px','marginBottom':'10px'},children=[
            html.Details(children=[
                html.Summary("⚙ Uyari Eslikleri (Ayarlar)",
                             style={'cursor':'pointer','color':'#aaa','fontSize':'14px','fontWeight':'bold','marginBottom':'8px'}),
                html.Div(style={'display':'flex','gap':'20px','flexWrap':'wrap','paddingTop':'12px'},children=[
                    html.Div(style={'flex':'1','minWidth':'180px'},children=[
                        html.Label("Lastik Uyari %",style={'fontSize':'11px','color':'#888'}),
                        dcc.Slider(id='sl-tyre-warn',min=50,max=90,step=5,value=70,
                                   marks={50:'50',70:'70',90:'90'},
                                   tooltip={"placement":"bottom","always_visible":True}),
                    ]),
                    html.Div(style={'flex':'1','minWidth':'180px'},children=[
                        html.Label("Lastik Kritik %",style={'fontSize':'11px','color':'#888'}),
                        dcc.Slider(id='sl-tyre-crit',min=70,max=99,step=5,value=85,
                                   marks={70:'70',85:'85',99:'99'},
                                   tooltip={"placement":"bottom","always_visible":True}),
                    ]),
                    html.Div(style={'flex':'1','minWidth':'180px'},children=[
                        html.Label("ERS Uyari (J)",style={'fontSize':'11px','color':'#888'}),
                        dcc.Slider(id='sl-ers-warn',min=200000,max=1500000,step=100000,value=800000,
                                   marks={200000:'200k',800000:'800k',1500000:'1.5M'},
                                   tooltip={"placement":"bottom","always_visible":True}),
                    ]),
                    html.Div(style={'flex':'1','minWidth':'180px'},children=[
                        html.Label("Yakit Uyari (tur)",style={'fontSize':'11px','color':'#888'}),
                        dcc.Slider(id='sl-fuel-warn',min=2,max=10,step=1,value=4,
                                   marks={2:'2',4:'4',10:'10'},
                                   tooltip={"placement":"bottom","always_visible":True}),
                    ]),
                    html.Div(style={'marginTop':'8px'},children=[
                        html.Button("💾 Kaydet",id='btn-save-settings',
                                    style={'backgroundColor':'#ff8800','color':'#000','border':'none',
                                           'borderRadius':'6px','padding':'8px 18px','cursor':'pointer',
                                           'fontSize':'13px','fontWeight':'bold'}),
                        html.Span(id='settings-saved',style={'marginLeft':'10px','color':'#00ff88','fontSize':'12px'}),
                    ]),
                ]),
            ]),
        ]),

        dcc.Interval(id='interval',interval=600,n_intervals=0),
        dcc.Store(id='ergast-store', data={}),
    ]
)

# ─────────────────────────────────────────────────────────
# SETTINGS SAVE
# ─────────────────────────────────────────────────────────
@app.callback(Output('settings-saved','children'),
              Input('btn-save-settings','n_clicks'),
              State('sl-tyre-warn','value'),State('sl-tyre-crit','value'),
              State('sl-ers-warn','value'),State('sl-fuel-warn','value'),
              prevent_initial_call=True)
def save_settings(n,tw,tc,ew,fw):
    try:
        with open("config.json") as f: cfg=json.load(f)
        cfg["alerts"]["TYRE_WARN_PCT"]=tw; cfg["alerts"]["TYRE_CRIT_PCT"]=tc
        cfg["alerts"]["ERS_WARN_J"]=ew;   cfg["alerts"]["FUEL_WARN_LAPS"]=fw
        with open("config.json","w") as f: json.dump(cfg,f,indent=4)
        return "✓ Kaydedildi"
    except Exception as e: return f"Hata: {e}"

# ─────────────────────────────────────────────────────────
# ERGAST FETCH
# ─────────────────────────────────────────────────────────
@app.callback(Output('ergast-store','data'),
              Output('ergast-status','children'),
              Input('btn-fetch-ergast','n_clicks'),
              State('dd-circuit','value'),
              prevent_initial_call=True)
def fetch_ergast(n, circuit_key):
    if not circuit_key: return {}, "Pist secmediniz."
    try:
        year, rnd = CIRCUIT_MAP[circuit_key]
        df = fetch_race_laps(year, rnd)
        if df.empty:
            return {}, f"Veri gelmedi ({circuit_key})"
        bests = df.groupby("driver")["time_ms"].min().reset_index()
        return {"circuit":circuit_key,"data":bests.to_dict("records")}, f"✓ {len(bests)} pilot | {circuit_key}"
    except Exception as e:
        return {}, f"Hata: {e}"

# ─────────────────────────────────────────────────────────
# PHYSICS CALCULATORS
# ─────────────────────────────────────────────────────────
@app.callback(Output('fuel-calc-result','children'),
              Input('inp-laps','value'), Input('inp-fuelrate','value'),
              Input('sl-sc-prob','value'), Input('sl-sc-laps','value'))
def update_fuel_calc(laps, rate, sc_prob, sc_laps):
    try:
        r = calculate_fuel_load(int(laps or 57), float(rate or 2.2),
                                int(sc_laps or 3), (sc_prob or 40)/100)
        rows = [
            ("Temel Yakit",    f"{r['base_fuel_kg']} kg",  '#ffbb00'),
            ("SC Buffer",      f"{r['sc_buffer_kg']} kg",  '#ff8800'),
            ("Formation Lap",  f"{r['formation_kg']} kg",  '#aaa'),
            ("TOPLAM",         f"{r['total_fuel_kg']} kg", '#00ff88'),
            ("Hacim",          f"{r['fuel_liters']} L",    '#00d4ff'),
        ]
        return html.Div([
            html.Div(style={'display':'flex','justifyContent':'space-between','padding':'3px 0',
                            'borderBottom':'1px solid #222'},children=[
                html.Span(label, style={'color':'#888','fontSize':'12px'}),
                html.Span(val,   style={'color':col,'fontWeight':'bold','fontSize':'13px'})
            ]) for label,val,col in rows
        ])
    except: return html.Div("Gecersiz giris", style={'color':'#ff4444'})

@app.callback(Output('brake-dist-result','children'),
              Output('brake-sweep-graph','figure'),
              Input('sl-ventry','value'), Input('sl-vcorner','value'), Input('sl-decel','value'))
def update_brake_calc(v_in, v_out, decel):
    try:
        r = calculate_braking_distance(float(v_in), float(v_out), float(decel))
        result = html.Div([
            html.Div(f"Mesafe: {r['distance_m']} m", style={'color':'#ff4444','fontSize':'16px','fontWeight':'bold'}),
            html.Div(f"Sure:   {r['time_s']} s",     style={'color':'#ff8800','fontSize':'13px'}),
            html.Div(f"Kuvvet: {r['braking_force_kn']} kN", style={'color':'#aaa','fontSize':'12px'}),
        ])
        sweep_data = braking_distance_sweep(range(100, 381, 20), float(v_out), float(decel))
        f = go.Figure(go.Scatter(x=[s['v_entry'] for s in sweep_data],
                                  y=[s['distance_m'] for s in sweep_data],
                                  mode='lines+markers', line=dict(color='#ff4444',width=2),
                                  marker=dict(size=5)))
        f.add_vline(x=float(v_in), line_dash='dash', line_color='#ffbb00',
                    annotation_text=f"{v_in}km/h")
        f.update_layout(title="Fren Mesafesi vs Giris Hizi", xaxis_title="km/h",
                         yaxis_title="Mesafe (m)", **DARK)
        return result, f
    except Exception as e:
        return html.Div(f"Hata:{e}",style={'color':'#ff4444'}), ef()

# ─────────────────────────────────────────────────────────
# PIT SIMULATOR
# ─────────────────────────────────────────────────────────
@app.callback(Output('pit-sim-result','children'),
              Input('pit-lap-slider','value'), Input('interval','n_intervals'))
def pit_sim(pit_lap, _):
    if not os.path.exists("live_data.json"): return ""
    try:
        df=pd.read_json("live_data.json")
        if df.empty: return ""
        wear=float(df['WearFL'].iloc[-1]) if 'WearFL' in df.columns else 50.
        fuel=float(df['Fuel'].iloc[-1])   if 'Fuel'  in df.columns else 50.
        flaps=float(df['FuelLaps'].iloc[-1]) if 'FuelLaps' in df.columns else 20.
        lap_n=int(df['LapNum'].iloc[-1])  if 'LapNum' in df.columns else 1
        laps_rem=max(0,pit_lap-lap_n)
        proj_w=min(100,wear+laps_rem*2.5); proj_f=max(0,fuel-laps_rem*2.1)
        
        # V11: Dynamic Pit Loss
        sc_s = int(df['SafetyCar'].iloc[-1]) if 'SafetyCar' in df.columns else 0
        wx   = int(df['Weather'].iloc[-1])   if 'Weather' in df.columns else 0
        pit_calc = dynamic_pit_loss(sc_s, wx)
        pit_time = pit_calc["dynamic_loss_sec"]
        pt_color = '#00d4ff' if pit_calc["is_window_optimal"] else '#aaa'
        
        return html.Div(style={'display':'flex','gap':'10px','flexWrap':'wrap'},children=[
            html.Div(style={'background':'#1c1c1c','borderRadius':'8px','padding':'10px','flex':'1','minWidth':'130px'},children=[
                html.Div("Projeksiyon",style={'fontSize':'10px','color':'#666'}),
                html.Div(f"Tur {pit_lap}",style={'fontWeight':'bold','color':'#ff8800','fontSize':'14px'}),
                html.Div(f"Wear:{proj_w:.0f}%",style={'color':wc,'fontSize':'13px'}),
                html.Div(f"Yakit:{proj_f:.1f}kg",style={'color':'#00ff88' if proj_f>5 else '#ff2200','fontSize':'13px'}),
                html.Div(f"~{pit_time}s kayip" + (" (SC!)" if sc_s else ""),style={'color':pt_color,'fontSize':'11px','fontWeight':'bold' if sc_s else 'normal'}),
            ]),
            html.Div(style={'background':'#1c1c1c','borderRadius':'8px','padding':'10px','flex':'1','minWidth':'130px'},children=[
                html.Div("Tavsiye",style={'fontSize':'10px','color':'#666'}),
                html.Div(
                    "✅ Uygun" if proj_w<85 and proj_f>5 else "⚠ Risk" if proj_w<95 else "🔴 PIT SIMDI!",
                    style={'fontWeight':'bold','fontSize':'14px',
                           'color':'#00ff88' if proj_w<85 and proj_f>5 else '#ff8800' if proj_w<95 else '#ff2200'}),
            ]),
        ])
    except: return ""

# ─────────────────────────────────────────────────────────
# MAIN LIVE CALLBACK
# ─────────────────────────────────────────────────────────
@app.callback(
    [Output('speed-graph','figure'),  Output('inputs-graph','figure'),
     Output('tyre-graph','figure'),   Output('tyretemp-graph','figure'),
     Output('track-graph','figure'),  Output('gforce-graph','figure'),
     Output('sector-graph','figure'), Output('gap-graph','figure'),
     Output('rpm-graph','figure'),
     Output('info-cards','children'), Output('weather-row','children'),
     Output('delta-bar','children'),  Output('alert-banner','children'),
     Output('live-status','children'),
     # Physics tab
     Output('track3d-graph','figure'),     Output('ers-harvest-graph','figure'),
     Output('thermal-graph','figure'),     Output('overtake-card','children'),
     # Historical tab
     Output('calendar-heatmap','figure'),  Output('session-compare-graph','figure'),
     Output('ergast-compare-graph','figure'),
    ],
    [Input('interval','n_intervals'), Input('ergast-store','data')]
)
def update(n, ergast_data):
    blanks = [ef()]*21
    if not os.path.exists("live_data.json"):
        cards=[]; wx=[]; delta=html.Div(); banner=[]; status="Telemetri bekleniyor..."
        return *blanks[:9],cards,wx,delta,banner,status,*blanks[9:]

    try:
        df = pd.read_json("live_data.json")
        if df.empty: raise ValueError("empty")

        # ── 1. Speed + DRS
        f_spd=px.line(df,x='Timestamp',y='Hız',title="Speed km/h",color_discrete_sequence=['#00d4ff'])
        f_spd.update_layout(**DARK)
        if 'DRS' in df.columns:
            drs=df[df['DRS']==1]
            if not drs.empty:
                f_spd.add_trace(go.Scatter(x=drs['Timestamp'],y=drs['Hız'],mode='markers',
                    marker=dict(color='lime',size=4,symbol='diamond'),name='DRS'))

        # ── 2. Inputs
        f_inp=px.line(df,x='Timestamp',y=['Fren','Gaz'],title="Fren & Gaz",
                      color_discrete_map={'Fren':'#ff2200','Gaz':'#00ff88'})
        f_inp.update_layout(**DARK)

        # ── 3. Tyre Wear
        wc=[c for c in['WearFL','WearFR','WearRL','WearRR'] if c in df.columns]
        f_tyr=px.line(df,x='Timestamp',y=wc,title="Lastik Asinmasi %",
                       color_discrete_map={'WearFL':'#ff00ff','WearFR':'#00ffff',
                                           'WearRL':'#ffff00','WearRR':'#ff8800'}) if wc else ef("Wear")
        f_tyr.update_layout(**DARK)

        # ── 4. Tyre Temps
        tc=[c for c in['TyreInnerFL','TyreInnerFR','TyreInnerRL','TyreInnerRR'] if c in df.columns]
        if tc:
            f_tt=px.line(df,x='Timestamp',y=tc,title="Lastik Ic Sicakligi C",
                         color_discrete_map={'TyreInnerFL':'#ff5500','TyreInnerFR':'#ffaa00',
                                             'TyreInnerRL':'#00ccff','TyreInnerRR':'#aa00ff'})
            f_tt.add_hrect(y0=80,y1=110,fillcolor='rgba(0,200,0,0.07)',line_width=0,annotation_text="Optimal")
        else: f_tt=ef("Lastik Sicakligi")
        f_tt.update_layout(**DARK)

        # ── 5. Track 2D
        has_pos='PosX' in df.columns and df['PosX'].abs().max()>1
        if has_pos:
            f_trk=px.scatter(df,x='PosX',y='PosZ',color='Hız',color_continuous_scale='plasma',title="2D Pist")
            f_trk.update_traces(marker_size=3)
            bp=rj("braking_points.json")
            if bp: f_trk.add_trace(go.Scatter(x=[p['PosX'] for p in bp],y=[p['PosZ'] for p in bp],
                mode='markers',marker=dict(color='red',size=6,symbol='circle-open'),name='Fren'))
            opt=rj("optimal_braking.json")
            if opt: f_trk.add_trace(go.Scatter(x=[o['x'] for o in opt],y=[o['z'] for o in opt],
                mode='markers+text',marker=dict(color='gold',size=13,symbol='star',line_width=2,line_color='white'),
                text=[f"#{i+1}" for i in range(len(opt))],textposition="top center",name='ML Optimal'))
        else: f_trk=ef("2D Pist")
        f_trk.update_layout(**DARK)

        # ── 6. G-Force
        if 'GLat' in df.columns:
            f_gf=px.scatter(df,x='GLat',y='GLon',title="G-Force",color_discrete_sequence=['#ff5500'])
            theta=list(range(0,361,5))
            for r in[1,2,3,4]:
                f_gf.add_trace(go.Scatter(x=[r*math.cos(math.radians(t)) for t in theta],
                    y=[r*math.sin(math.radians(t)) for t in theta],
                    mode='lines',line=dict(color='#333',dash='dot'),showlegend=False))
            f_gf.add_vline(x=0,line_color='#444'); f_gf.add_hline(y=0,line_color='#444')
        else: f_gf=ef("G-Force")
        f_gf.update_layout(**DARK)

        # ── 7. Sector Analysis
        laps=load_laps()
        if not laps.empty:
            f_sec=go.Figure()
            f_sec.add_bar(x=laps['lap_num'],y=laps['sector1_ms'],name='S1',marker_color='#4488ff')
            f_sec.add_bar(x=laps['lap_num'],y=laps['sector2_ms'],name='S2',marker_color='#ff8800')
            s3=(laps['lap_time_ms']-laps['sector1_ms']-laps['sector2_ms']).clip(lower=0)
            f_sec.add_bar(x=laps['lap_num'],y=s3,name='S3',marker_color='#44ff88')
            best=laps.loc[laps['lap_time_ms'].idxmin(),'lap_num']
            f_sec.add_vline(x=best,line_dash='dash',line_color='gold',annotation_text="Best")
            f_sec.update_layout(barmode='stack',title="Sektor Analizi (ms)",**DARK)
        else: f_sec=ef("Sektor Analizi")

        # ── 8. Competitor Leaderboard
        comp=rj("competitors.json",[])
        if comp:
            ids=[f"P{e.get('pos',i+1)}:Car{e.get('car',i)}" for i,e in enumerate(comp[:10])]
            times=[e.get('lapTimeMS',0)/1000. for e in comp[:10]]
            colors=['gold' if c.get('car')==0 else '#4488ff' for c in comp[:10]]
            f_gap=go.Figure(go.Bar(x=times,y=ids,orientation='h',marker_color=colors))
            f_gap.update_layout(title="Siralama",xaxis_title="Anlık Tur (s)",**DARK)
        else: f_gap=ef("Siralama")

        # ── 9. RPM
        f_rpm=px.line(df,x='Timestamp',y='RPM',title="Motor RPM",color_discrete_sequence=['#ffbb00'])
        f_rpm.update_layout(**DARK)

        # ── 3D TRACK MAP (Physics tab) ─────────────────────────────
        if has_pos and 'Hız' in df.columns:
            # Z = Speed (height), creates "mountain" on fast straights
            f_3d = go.Figure(go.Scatter3d(
                x=df['PosX'], y=df['PosZ'],
                z=df['Hız'],
                mode='lines',
                line=dict(color=df['Hız'], colorscale='plasma', width=4),
                name='Racing Line 3D'
            ))
            # Add braking points as red spikes
            if bp:
                f_3d.add_trace(go.Scatter3d(
                    x=[p['PosX'] for p in bp], y=[p['PosZ'] for p in bp],
                    z=[0]*len(bp), mode='markers',
                    marker=dict(color='red',size=4,symbol='circle'),name='Fren'))
            f_3d.update_layout(
                title="3D Pist Haritasi (Yukseklik = Hiz)",
                scene=dict(
                    xaxis_title="X (m)", yaxis_title="Z (m)", zaxis_title="Hiz (km/h)",
                    bgcolor='#111',
                    xaxis=dict(gridcolor='#333',zerolinecolor='#555'),
                    yaxis=dict(gridcolor='#333',zerolinecolor='#555'),
                    zaxis=dict(gridcolor='#333',zerolinecolor='#555'),
                ),
                **{k:v for k,v in DARK.items() if k != 'plot_bgcolor'}
            )
        else: f_3d=ef("3D Pist (Veri bekleniyor)")

        # ── ERS HASAT HARİTASI ─────────────────────────────────────
        if has_pos and 'ERS' in df.columns:
            # Calculate ERS delta: positive = harvesting, negative = deploying
            df2 = df.copy()
            df2['ERS_delta'] = df2['ERS'].diff().fillna(0)
            df2['ERS_action'] = df2['ERS_delta'].apply(
                lambda x: 'Hasat' if x > 2000 else ('Deploy' if x < -2000 else 'Neutral'))
            f_ers = px.scatter(df2, x='PosX', y='PosZ',
                               color='ERS_action',
                               color_discrete_map={'Hasat':'#00ff88','Deploy':'#00aaff','Neutral':'#333'},
                               title="ERS Hasat / Deploy Haritasi",
                               size_max=6)
            f_ers.update_traces(marker_size=4)
        else: f_ers=ef("ERS Hasat Haritasi")
        f_ers.update_layout(**DARK)

        # ── TİRE THERMAL SİMÜLASYON ───────────────────────────────
        if not df.empty and 'Hız' in df.columns and 'Fren' in df.columns:
            sample = df.tail(200)
            spd = sample['Hız'].values.astype(float)
            brk = sample['Fren'].values.astype(float)
            lat = sample['GLat'].values.astype(float) if 'GLat' in sample.columns else [0]*len(spd)
            sim_temps = simulate_lap_thermal(spd, brk, lat, ambient=22.0)
            actual_fl = sample['TyreInnerFL'].values if 'TyreInnerFL' in sample.columns else [0]*len(spd)
            idx = list(range(len(sim_temps)))
            f_therm = go.Figure()
            f_therm.add_trace(go.Scatter(x=idx, y=sim_temps, mode='lines',
                                          name='Simule (Fizik Model)', line=dict(color='#ff8800', width=2)))
            f_therm.add_trace(go.Scatter(x=idx, y=actual_fl, mode='lines',
                                          name='Gercek (Paket)', line=dict(color='#00d4ff', width=2, dash='dot')))
            f_therm.add_hrect(y0=80, y1=110, fillcolor='rgba(0,200,0,0.08)',
                               line_width=0, annotation_text="Optimal 80-110°C")
            f_therm.update_layout(title="Lastik Termal Model: Simule vs Gercek", **DARK)
        else: f_therm=ef("Lastik Termal Modeli")

        # ── OVERTAKE CARD ─────────────────────────────────────────
        ovt_card = []
        if 'WearFL' in df.columns and 'GapAhead' in df.columns and 'ERS' in df.columns:
            p_wear = float(df['WearFL'].iloc[-1])
            gap    = float(df['GapAhead'].iloc[-1])
            ers_p  = (float(df['ERS'].iloc[-1]) / 4_000_000) * 100
            # Mock target wear (usually higher)
            t_wear = min(100, p_wear + 15)
            ov = calculate_overtake_window(p_wear, t_wear, gap, ers_p)
            fdp = fuel_deficit_analysis(
                float(df['Fuel'].iloc[-1]) if 'Fuel' in df.columns else 50,
                float(df['FuelLaps'].iloc[-1]) if 'FuelLaps' in df.columns else 20,
                57, int(df['LapNum'].iloc[-1]) if 'LapNum' in df.columns else 1
            )
            op_col = '#00ff88' if ov['opportunity']=='High' else '#ff8800' if ov['opportunity']=='Medium' else '#666'
            ovt_card = html.Div(style={'display':'flex','gap':'10px','flexWrap':'wrap'},children=[
                card("Gecis Firsati", ov['opportunity'], op_col, icon="🏎",
                     sub=f"ERS boost: +{ov['ers_boost_s']:.2f}s"),
                card("Lastik Avantaji", f"+{ov['wear_advantage_s']:.2f}s/tur", '#ffbb00', icon="🛞",
                     sub=f"Wear fark: {ov['wear_diff_pct']}%"),
                card("Yakit Durumu",
                     "✅ Yeterli" if fdp['is_sufficient'] else f"⚠ {fdp['deficit_per_lap']:.3f}kg/tur az",
                     '#00ff88' if fdp['is_sufficient'] else '#ff8800', icon="⛽",
                     sub=f"{fdp['laps_remaining']} tur kaldi"),
            ])

        # ── CALENDAR HEATMAP ──────────────────────────────────────
        ash = load_all_sessions()
        if not ash.empty:
            # Pivot: session_id as rows, lap_num as columns, value = lap_time_ms
            try:
                pivot = ash.pivot_table(index='session_id', columns='lap_num',
                                        values='lap_time_ms', aggfunc='min')
                f_cal = go.Figure(go.Heatmap(
                    z=pivot.values,
                    x=[f"Tur {c}" for c in pivot.columns],
                    y=[str(s)[-8:] for s in pivot.index],
                    colorscale='RdYlGn_r',
                    colorbar=dict(title="ms"),
                    text=[[f"{int(v/1000)}.{int(v%1000):03d}"
                           if not pd.isna(v) else "" for v in row]
                          for row in pivot.values],
                    texttemplate="%{text}",
                ))
                f_cal.update_layout(title="Seans Isı Haritası (Tur Süreleri)", **DARK)
            except Exception:
                f_cal = ef("Seans Isı Haritası (veri az)")
        else: f_cal=ef("Seans Isı Haritası")

        # ── SESSION COMPARE ───────────────────────────────────────
        if not ash.empty and ash['session_id'].nunique()>0:
            f_cmp=px.line(ash,x='lap_num',y='lap_time_ms',color='session_id',
                          title="Seans Karsilastirmasi")
        else: f_cmp=ef("Seans Karsilastirmasi")
        f_cmp.update_layout(**DARK)

        # ── ERGAST COMPARE ────────────────────────────────────────
        if ergast_data and ergast_data.get('data'):
            bests_df = pd.DataFrame(ergast_data['data'])
            our_best = int(laps['lap_time_ms'].min()) if not laps.empty and 'lap_time_ms' in laps.columns else 0
            circuit  = ergast_data.get('circuit','')
            colors   = ['gold' if row['time_ms'] > our_best else '#4488ff'
                        for _,row in bests_df.iterrows()]
            f_erg = go.Figure()
            f_erg.add_bar(x=bests_df['driver'],
                           y=bests_df['time_ms'],
                           marker_color='#4488ff', name='F1 Pilotu')
            if our_best > 0:
                f_erg.add_hline(y=our_best, line_dash='dash', line_color='gold',
                                annotation_text=f"Senin En Iyin: {our_best/1000:.3f}s",
                                annotation_font_color='gold')
            f_erg.update_layout(title=f"F1 Karsilastirma — {circuit}",
                                  yaxis_title="En Iyi Tur (ms)", **DARK)
        else: f_erg=ef("F1 Karsilastirma (Pist sec ve 'Veri Cek' tikla)")

        # ── INFO CARDS ────────────────────────────────────────────
        lap_n   = int(df['LapNum'].iloc[-1])   if 'LapNum'        in df.columns else 0
        lap_t   = float(df['LapTime'].iloc[-1])if 'LapTime'       in df.columns else 0
        pit_p   = int(df['PitPrediction'].iloc[-1]) if 'PitPrediction' in df.columns else -1
        pit_c   = '#ff2200' if pit_p<3 else '#ff8800' if pit_p<8 else '#00ff88'
        best_ms = int(df['BestLapMs'].iloc[-1]) if 'BestLapMs' in df.columns and df['BestLapMs'].iloc[-1]>0 else 0
        compound= df['CompoundAdvisor'].iloc[-1] if 'CompoundAdvisor' in df.columns else "—"
        cmp_col = COMPOUND_COLORS.get(compound,'#fff')

        cards=[
            card("Lap",f"#{lap_n}",'#00d4ff',icon="🏁"),
            card("Tur Suresi",f"{lap_t:.2f}s",'#fff',icon="⏱"),
            card("En Iyi",f"{best_ms/1000:.3f}s" if best_ms else "—",'#cc44ff',icon="★"),
            card("Pit Pred",f"{pit_p}L" if pit_p>=0 else "—",pit_c,icon="🔧"),
        ]
        if 'Fuel' in df.columns:
            cards.append(card("Yakit",f"{df['Fuel'].iloc[-1]:.1f}kg",'#ffbb00',icon="⛽",sub=f"{df['FuelLaps'].iloc[-1]:.1f}L"))
        if 'ERS' in df.columns:
            ep=(df['ERS'].iloc[-1]/4_000_000)*100
            cards.append(card("ERS",f"%{ep:.0f}",'#ff2200' if ep<10 else '#ff8800' if ep<30 else '#00ff88',icon="🔋"))
        if 'TyreAge' in df.columns:
            cards.append(card("Lastik Yasi",f"{int(df['TyreAge'].iloc[-1])}L",'#aaa',icon="🛞"))
        cards.append(card("Compound",compound,cmp_col,icon="⚪"))
        if 'CarPosition' in df.columns:
            cards.append(card("Pozisyon",f"P{int(df['CarPosition'].iloc[-1])}",'gold',icon="🏆"))

        # ── WEATHER ROW ───────────────────────────────────────────
        wx=[]
        if 'Weather' in df.columns:
            w=int(df['Weather'].iloc[-1]); tt=int(df['TrackTemp'].iloc[-1]) if 'TrackTemp' in df.columns else 0
            at=int(df['AirTemp'].iloc[-1]) if 'AirTemp' in df.columns else 0
            sc=int(df['SafetyCar'].iloc[-1]) if 'SafetyCar' in df.columns else 0
            wx=[card("Hava",WEATHER_NAMES.get(w,"—"),'#87ceeb',bg='#0d1a27',icon="🌍"),
                card("Pist","{}°C".format(tt),'#ff8c00',icon="🌡"),
                card("Hava","{}°C".format(at),'#87ceeb',icon="💨")]
            if sc>0: wx.append(card("Durum",SAFETY_NAMES.get(sc,""),'#ffff00',icon="🚨"))

        # ── DELTA BAR ─────────────────────────────────────────────
        def dchip(lbl,delta,ck):
            CM={'purple':'#cc44ff','green':'#00cc44','red':'#ff2200','yellow':'#ffcc00'}
            col=CM.get(ck,'#888'); sign='+' if delta>=0 else ''
            return html.Div(f"{lbl}:{sign}{int(delta)}ms",
                style={'background':col+'22','border':f'1px solid {col}','borderRadius':'8px',
                       'padding':'5px 12px','fontSize':'13px','color':col,'fontWeight':'bold'})
        delta_bar=[]
        if 'DeltaS1' in df.columns and best_ms>0:
            delta_bar=[html.Div("Δ Best:",style={'fontSize':'12px','color':'#666','alignSelf':'center','marginRight':'6px'}),
                       dchip("S1",df['DeltaS1'].iloc[-1],df['ColorS1'].iloc[-1]),
                       dchip("S2",df['DeltaS2'].iloc[-1],df['ColorS2'].iloc[-1]),
                       dchip("Total",df['DeltaTotal'].iloc[-1],'green' if df['DeltaTotal'].iloc[-1]<0 else 'red')]
        delta_container=html.Div(delta_bar,style={'display':'flex','gap':'8px','alignItems':'center','flexWrap':'wrap'}) if delta_bar else html.Div()

        # ── ALERTS ────────────────────────────────────────────────
        alerts=rj("alerts.json",[])
        banner=[]
        for a in alerts:
            col='#ff2200' if a.get('level')=='critical' else '#ff8800'
            banner.append(html.Div(f"{a.get('icon','')} {a.get('msg','')}",
                style={'background':col+'22','border':f'1px solid {col}','borderRadius':'8px',
                       'padding':'6px 12px','marginBottom':'4px','fontSize':'13px','color':col}))

        status=f"Live | {len(df)} pkt | Lap:{lap_n} | T:{lap_t:.2f}s | REST:/api/live /api/laps"

        return (f_spd,f_inp,f_tyr,f_tt,f_trk,f_gf,f_sec,f_gap,f_rpm,
                cards,wx,delta_container,banner,status,
                f_3d,f_ers,f_therm,ovt_card,
                f_cal,f_cmp,f_erg)

    except Exception as e:
        cards=[]; wx=[]; delta=html.Div(); banner=[]; status=f"Hata: {e}"
        return *([ef(f"Hata: {e}")]*21)[:9],cards,wx,delta,banner,status,*([ef()]*21)[9:]

# ─────────────────────────────────────────────────────────
# VIRTUAL ENGINEER CALLBACK
# ─────────────────────────────────────────────────────────
@app.callback(
    Output('engineer-radar-graph', 'figure'),
    Output('engineer-feedback-list', 'children'),
    Input('interval', 'n_intervals')
)
def update_engineer(n):
    if not os.path.exists("engineer_feedback.json"):
        return ef("Sürücü Profili Bekleniyor..."), [html.Div("Henüz tam bir tur atılmadı veya veri bekleniyor.", style={'color':'#888'})]
        
    try:
        report = rj("engineer_feedback.json", {})
        if not report: raise ValueError("Empty")
        
        # 1. Radar Chart (Score 0-100)
        tb_score = report.get("trail_braking_score", 0)
        
        # Convert Coast Time to a 0-100 score (0s = 100, >3.0s = 0)
        coast_s = report.get("coast_time_sec", 0)
        pedal_score = max(0, min(100, 100 - (coast_s / 3.0) * 100))
        
        # Convert Average Shift RPM to 0-100 score (11500-12300 is good)
        rpm = report.get("avg_shift_rpm", 0)
        if 11500 <= rpm <= 12300: shift_score = 100
        elif rpm < 11500: shift_score = max(0, 100 - ((11500 - rpm) / 1000) * 100)
        else: shift_score = max(0, 100 - ((rpm - 12300) / 1000) * 100)
            
        categories = ['Trail Braking (Pürüzsüzlük)', 'Pedal Geçiş Hızı (Coast)', 'İdeal Vites (RPM)']
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=[tb_score, pedal_score, shift_score],
            theta=categories,
            fill='toself',
            name='Son Tur Profili',
            line_color='#00d4ff', fillcolor='rgba(0, 212, 255, 0.4)'
        ))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100], color='#444')),
            showlegend=False,
            margin=dict(l=30, r=30, t=20, b=20),
            paper_bgcolor='#141414', plot_bgcolor='#141414',
            font_color='#ddd'
        )
        
        # V11: Lift-and-Coast Savings
        l_c = lift_and_coast_savings(coast_s)
        g_saved = l_c["fuel_saved_grams"]
        
        feedback_items = []
        # Add Fuel Efficiency Tracker as first item
        feedback_items.append(html.Div(f"🍃 Lift-and-Coast Yakıt Tasarrufu (Son Tur): +{g_saved} gr ({coast_s}s süzülme)", style={
            'padding':'10px', 'background':'rgba(0,255,136,0.1)', 'border':f'1px solid #00ff8855',
            'borderRadius':'6px', 'color':'#00ff88', 'fontSize':'13px', 'fontWeight':'bold'
        }))
        alerts = report.get("all_feedback", [])
        if not alerts:
            feedback_items.append(html.Div("Sürüş mükemmel, hata bulunamadı!", style={'color':'#00ff88','padding':'10px','background':'rgba(0,255,136,0.1)','borderRadius':'6px'}))
        else:
            for idx, msg in enumerate(alerts):
                # Priortize first item with red color
                bg = 'rgba(255,34,0,0.1)' if idx == 0 else 'rgba(255,136,0,0.1)'
                color = '#ff2200' if idx == 0 else '#ff8800'
                icon = "🚨" if idx == 0 else "🔧"
                feedback_items.append(html.Div(f"{icon} {msg}", style={
                    'padding':'10px', 'background':bg, 'border':f'1px solid {color}55',
                    'borderRadius':'6px', 'color':color, 'fontSize':'14px', 'fontWeight':'bold' if idx == 0 else 'normal'
                }))
                
        return fig, feedback_items
        
    except Exception as e:
        return ef("Hata"), [html.Div(f"Mühendis modülü yüklenemedi: {e}", style={'color':'#ff2200'})]


if __name__=='__main__':
    print("F1 2022 V10 Dashboard --> http://127.0.0.1:8050")
    print("Sekmeler: CANLI | Fizik & Strateji | Sanal Mühendis | Tarihsel & F1")
    app.run(debug=True, port=8050)

