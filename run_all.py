import subprocess
import sys
import time

print("="*50)
print("🏎️  F1 2022 Telemetry Suite Başlatılıyor...")
print("="*50)

try:
    # 3 ayrı Python scriptini aynı anda başlatıyoruz
    print("[1/3] Mock Telemetry Sender devre dışı (Gerçek oyuna bağlanıyor)...")
    sender = None
    time.sleep(1) # Portların çakışmaması için ufak bir bekleme
    
    print("[2/3] Telemetry Listener (Arka plan işleyicisi) başlatılıyor...")
    listener = subprocess.Popen([sys.executable, "telemetry_listener.py"])
    time.sleep(1)
    
    print("[3/3] Live Dashboard (Arayüz) başlatılıyor...")
    dashboard = subprocess.Popen([sys.executable, "dashboard.py"])
    
    print("\n✅ Bütün sistemler başarıyla aktif edildi!")
    print("🌍 Tarayıcınızda http://127.0.0.1:8050 adresine giderek canlı verileri izleyebilirsiniz.")
    print("\n🛑 Sistemi kapatmak için bu terminalde CTRL+C tuşlarına basmanız yeterlidir.\n")
    
    # Ana programın kapanmasını engellemek için sonsuz döngü
    while True:
        time.sleep(1)

except KeyboardInterrupt:
    print("\n🛑 Kapatma sinyali (CTRL+C) alındı. Ana şebeke durduruluyor...")
    if sender:
        sender.terminate()
    listener.terminate()
    dashboard.terminate()
    print("👋 Tüm servisler başarıyla kapatıldı.")
