import pandas as pd
import tkinter as tk
from tkinter import filedialog
import os

# 1. Tkinter'in gereksiz ana penceresini gizle
root = tk.Tk()
root.withdraw()

# Her zaman en üstte görünmesini sağla
root.attributes('-topmost', True)

print("[SİSTEM] Dosya seçimi bekleniyor... (Açılan pencereden CSV dosyanızı seçin)")

# 2. Kullanıcıya dosya seçtir (Path ve isim derdi bitti)
dosya_yolu = filedialog.askopenfilename(
    title="Analiz Edilecek Telemetri CSV'sini Seçin",
    filetypes=[("CSV Dosyaları", "*.csv"), ("Tüm Dosyalar", "*.*")]
)

# 3. Eğer kullanıcı 'İptal'e basarsa sistemi durdur
if not dosya_yolu:
    print("❌ Dosya seçimi iptal edildi. Sistem kapatılıyor.")
    exit()

# Sadece dosyanın adını ekrana basmak için ayrıştır (Uzun yolları gizle)
dosya_adi = os.path.basename(dosya_yolu)
print(f"\n[İŞLENİYOR] Hedef Kilitlendi: {dosya_adi}")

# 4. Veriyi Oku ve Anatomisini Çıkar
try:
    df = pd.read_csv(dosya_yolu)
    print("\n✅ DOSYA BAŞARIYLA YÜKLENDİ!")
    
    print("\n--- SÜTUN İSİMLERİ (KOLONLAR) ---")
    print(list(df.columns))
    
    print(f"\n--- VERİ BOYUTU ---")
    print(f"Toplam Satır: {len(df)}")
    
    print("\n--- İLK 3 SATIR ÖNİZLEME ---")
    print(df.head(3))

except Exception as e:
    print(f"\n❌ OKUMA HATASI: Veri çekilemedi. Hata detayı:\n{e}")