# 🏎️ F1 2022 Pit Wall & Sanal Yarış Mühendisi - Kullanım Kılavuzu

Bu platform, F1 2022 oyunundan (veya uyumlu diğer F1 oyunlarından) canlı telemetri verisi çekerek profesyonel e-spor takımlarının kullandığı seviyede **canlı analiz**, **fizik simülasyonları** ve **yapay zeka destekli yarış mühendisliği** sunar.

---

## ⚙️ 1. Oyunu Ayarlama (F1 2022)

Sistemin oyundan veri alabilmesi için oyun içi UDP Telemetri ayarlarının açık olması gerekir.

1. F1 2022 oyununu başlatın.
2. **Game Options (Seçenekler)** > **Settings (Ayarlar)** > **Telemetry Settings (Telemetri Ayarları)** menüsüne gidin.
3. Aşağıdaki ayarları aynen uygulayın:
   - **UDP Telemetry:** `On` (Açık)
   - **UDP Broadcast Mode:** `Off` (Kapalı)
   - **UDP IP Address:** `127.0.0.1`
   - **UDP Port:** `20777`
   - **UDP Send Rate:** `20Hz` (veya sistem performansınıza göre `30Hz`/`60Hz`)
   - **UDP Format:** `2022`

---

## 🚀 2. Sistemi Başlatma

Oyun açıkken ve siz sürüşe hazır durumdayken (garajda veya piste çıkmışken):

1. Ana proje klasöründe ( `udp_telemetry` ) bir komut satırı (Terminal / PowerShell / CMD) açın.
2. Tüm servisleri (Telemetri Dinleyicisi ve Canlı Dashboard) tek bir komutla başlatın:
   ```bash
   python run_all.py
   ```
3. Terminalde `✅ Bütün sistemler başarıyla aktif edildi!` yazısını gördüğünüzde sistem arka planda oyunu dinlemeye başlamıştır.

> **Sistemi Kapatmak İçin:** Terminal ekranına tıklayıp klavyenizden **`CTRL + C`** tuşlarına basmanız yeterlidir.

---

## 📊 3. Dashboard'u Kullanma (Gösterge Paneli)

Sistem çalıştığında favori web tarayıcınızı (Chrome, Edge vb.) açın ve şu adrese gidin:  
👉 **http://127.0.0.1:8050**

Dashboard 4 ana sekmeden (Tab) oluşur:

### 🔴 CANLI (Live) Sekmesi
O an araçtayken gerçekleşen her şeyi salisesi salisesine buradan takip edebilirsiniz:
- **Gaz & Fren, Hız, RPM:** Anlık tepkileriniz.
- **Sektör Delta Barları:** En iyi turunuza (PB) göre Sektör 1 ve Sektör 2'de mor (daha hızlı), yeşil (kendi en iyiniz) veya kırmızı (daha yavaş) olduğunuzu canlı gösterir.
- **Lastik Aşınması & Sıcaklığı:** 4 lastiğin anlık aşınma yüzdeleri ve iç/dış sıcaklık değerleri.
- **G-Force Radarı & 2D Pist Haritası:** Aracın yatay/dikey G kuvvetleri ile pist üzerindeki anlık konumu ve fren noktaları.

### ⚙️ FİZİK & STRATEJİ Sekmesi
Gelişmiş mühendislik hesaplamaları burada yapılır:
- **3D Pist Haritası:** Pisti kuşbakışı değil, **hızınıza göre** dağ gibi yükselen 3 boyutlu bir grafikte görürsünüz (düzlükler tepe, yavaş virajlar çukurdur).
- **ERS Hasat / Deploy Haritası:** Pistin neresinde bataryayı harcadığınızı (Mavi) ve neresinde şarj ettiğinizi (Yeşil) harita üzerinde gösterir.
- **Termal Simülasyon:** Gerçek paket sıcaklığı ile fiziksel ısınma modelini karşılaştırır.
- **Hesaplayıcılar:** Pit stop stratejiniz için "Yakıt Yükü Hesaplayıcısı" ve "Erken/Geç Fren Mesafe Hesaplayıcısı" (slider'lar ile interaktif).

### 🧠 SANAL MÜHENDİS Sekmesi (V10)
Siz pistte turlarken, yapay zeka arka planda sürüş stilinizi çıkartır:
- **Sürücü Profili Radarı:** Pürüzsüz trail-braking yapıyor musunuz? İki pedala basmadan çok fazla süzülüyor musunuz? Vites atma zamanlamanız ne kadar iyi? Bu üç kategori 100 üzerinden puanlanır.
- **Tavsiye Listesi:** Her turu attığınızda (çizgiyi geçtiğinizde) sistem en iyi turunuzla (PB) o turu karşılaştırır. "*Turn 4'te 15 metre erken frene bastın*", "*Vitesleri çok erken atıp redline öncesi güç kaybediyorsun*" gibi doğrudan sürenizi geliştirecek eyleme dönüştürülebilir tavsiyeler verir.

### 📈 TARİHSEL & F1 KARŞILAŞTIRMA Sekmesi
Geçmiş seansları ve gerçek dünyayı incelemek içindir:
- **Ergast F1 Veri Çekimi:** Seçtiğiniz bir pistte (Örn: Monza 2024), **gerçek F1 pilotlarının** (Verstappen, Hamilton vb.) o yarışta attığı en iyi tur verilerini çekerek **sizin** Dashboard'daki en iyi turunuz ile aynı grafikte kıyaslar.
- **Seans Isı Haritası:** Attığınız onca turun zamanlarını yan yana sıralayarak, performansınızın lastik aşındıkça nasıl düştüğünü "Isı Haritası" (Heatmap) formatında gösterir.

---

## 🎧 4. Sesli Asistan ve Radyo (Voice Alerts)

Sistem `pyttsx3` üzerinden arka planda tıpkı gerçek bir yarış mühendisi gibi sizinle İngilizce konuşur. Aşağıdaki durumlarda kulaklığınızdan uyarı alırsınız:

- **Lastik Aşınması:** Lastiğiniz ayarladığınız eşiği (Örn: %70) geçtiğinde.
- **Yakıt Durumu:** Finiş çizgisine kalan yakıt limitlerdeyse ("Lift and coast" uyarısı).
- **Best Lap / Purple Sector:** O seanstaki en iyi derecenizi veya mor sektör yaptığınızda sürüş esnasında haberdar olursunuz ("Purple Sector 1").
- **Mühendis Tavsiyesi V10:** Tur bittikten hemen sonra, eğer büyük ve bariz bir hata yaptıysanız sistem bunu sesli okur. (Örn: *"Engineer: You are braking early into Turn 4"*).

*(Uyarı eşik değerlerini Dashboard'un en altındaki **Ayarlar** panelinden değiştirebilirsiniz).*

İyi yarışlar! 🏎️💨
