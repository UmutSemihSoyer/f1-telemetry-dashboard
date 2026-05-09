"""
voice_alerts.py — F1 2022 Voice Pit Wall Alerts
Uses pyttsx3 for system TTS, runs in a background thread.
Configure via config.json -> voice section.
"""
import threading
import time
import json
import sys

try:
    import pyttsx3
    HAS_TTS = True
except ImportError:
    HAS_TTS = False
    print("[voice] pyttsx3 not found. Voice alerts disabled.")

# Load config
try:
    with open("config.json") as f:
        _cfg = json.load(f)["voice"]
    TTS_ENABLED  = _cfg.get("ENABLED", True) and HAS_TTS
    TTS_RATE     = _cfg.get("RATE", 180)
    TTS_VOLUME   = _cfg.get("VOLUME", 0.9)
    COOLDOWN_SEC = _cfg.get("COOLDOWN_SEC", 15)
except Exception:
    TTS_ENABLED  = HAS_TTS
    TTS_RATE     = 180
    TTS_VOLUME   = 0.9
    COOLDOWN_SEC = 15

# State
_last_spoken: dict[str, float] = {}   # key -> timestamp
_speech_queue: list[str] = []
_lock = threading.Lock()
_engine = None


def _init_engine():
    global _engine
    if not TTS_ENABLED:
        return
    try:
        _engine = pyttsx3.init()
        _engine.setProperty("rate",   TTS_RATE)
        _engine.setProperty("volume", TTS_VOLUME)
    except Exception as e:
        print(f"[voice] TTS engine failed to start: {e}")
        globals()["TTS_ENABLED"] = False


def speak(message: str, key: str = None):
    """Queue a speech message. If key is provided, enforces COOLDOWN_SEC per key."""
    if not TTS_ENABLED:
        return
    now = time.time()
    effective_key = key or message
    with _lock:
        last = _last_spoken.get(effective_key, 0)
        if now - last < COOLDOWN_SEC:
            return
        _last_spoken[effective_key] = now
        _speech_queue.append(message)


def _speech_worker():
    """Daemon thread — drains the speech queue."""
    _init_engine()
    if not _engine:
        return
    while True:
        with _lock:
            msgs = list(_speech_queue)
            _speech_queue.clear()
        for msg in msgs:
            try:
                _engine.say(msg)
                _engine.runAndWait()
            except Exception:
                pass
        time.sleep(0.2)


def start_voice_thread():
    """Start the background TTS worker thread."""
    if not TTS_ENABLED:
        return
    t = threading.Thread(target=_speech_worker, daemon=True)
    t.start()
    print("[voice] Voice alert system active.")


# ---- Standard pit wall alerts ----

def alert_tyre_critical(wear: float):
    speak(f"Warning! Tyre wear critical at {int(wear)} percent. Recommend pit stop.", "tyre_crit")

def alert_tyre_warn(wear: float):
    speak(f"Tyre wear at {int(wear)} percent. Monitor closely.", "tyre_warn")

def alert_ers_critical(pct: float):
    speak(f"ERS battery critical at {int(pct)} percent.", "ers_crit")

def alert_fuel_critical(laps: float):
    speak(f"Fuel critical. {laps:.1f} laps remaining.", "fuel_crit")

def alert_fuel_warn(laps: float):
    speak(f"Fuel warning. {laps:.1f} laps of fuel remaining.", "fuel_warn")

def alert_engine(pct: int):
    speak(f"Engine damage at {pct} percent! Check condition.", "engine_dmg")

def alert_safety_car(status: int):
    msgs = {1: "Safety car deployed!", 2: "Virtual safety car!", 3: "Formation lap!"}
    if status in msgs:
        speak(msgs[status], "safety_car")

def alert_weather_change(weather: int):
    names = {0: "Clear", 1: "Light cloud", 2: "Overcast",
             3: "Light rain", 4: "Heavy rain", 5: "Storm"}
    if weather in names:
        speak(f"Weather update: {names[weather]}!", "weather_change")


# ---- Radio commands ----

def radio_box_box(pit_lap: int = 0):
    msg = "Box box! Come in this lap!" if pit_lap <= 0 else f"Box box on lap {pit_lap}!"
    speak(msg, "box_box")

def radio_push_now():
    speak("Push now! Everything you have got!", "push_now")

def radio_save_tyres():
    speak("Tyre management mode. Back off two tenths.", "save_tyres")

def radio_save_fuel():
    speak("Lift and coast. We need to save fuel.", "save_fuel")

def radio_engineer_feedback(msg: str):
    """Speak the most critical feedback from race_engineer."""
    speak(f"Engineer: {msg}", "engineer_eval")

def radio_ers_overtake():
    speak("Deploy overtake mode! ERS full deploy!", "ers_overtake")

def radio_sector_purple(sector: int):
    speak(f"Sector {sector} purple! New best time!", f"purple_s{sector}")

def radio_fastest_lap():
    speak("Fastest lap! Purple sector across the board!", "fastest_lap")

def radio_yellow_flag():
    speak("Yellow flag ahead. Back off and maintain position.", "yellow_flag")

def radio_compound_advice(compound: str, reason: str = ""):
    msg = f"Tyre strategy update: {compound} recommended."
    if reason:
        msg += f" {reason}"
    speak(msg, "compound_advice")

def radio_pit_window_open(laps_remaining: int):
    speak(f"Pit window is open. {laps_remaining} laps to run.", "pit_window")


if __name__ == "__main__":
    start_voice_thread()
    speak("F1 2022 Pit Wall voice system online. All systems nominal.", "startup")
    time.sleep(5)
