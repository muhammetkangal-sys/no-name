# AI CNC Inspector

CNC makinesinden çıkan ürünlerin fotoğraflarına bakarak hata tespiti yapan, zamanla öğrenen kalite kontrol uygulaması.

## Özellikler

- Telefon/tablet kamerasıyla çekilen fotoğrafları yükleme
- Hata tipi etiketleme (çizik, çatlak, burr vb.)
- Kayıtlı hatalarla görsel benzerlik karşılaştırması
- Geçmiş kayıtları listeleme ve filtreleme
- Basit istatistik paneli

## Kurulum (Windows)

> **Önemli:** Projeyi başka bilgisayardan kopyaladıysanız `venv` klasörü çalışmaz. Silin ve yeniden oluşturun.

### 1. Python kur

1. https://www.python.org/downloads/ adresine git
2. **Download Python** ile indir
3. Kurulumda **"Add python.exe to PATH"** kutusunu işaretle
4. Kurulum bitince CMD'yi kapatıp yeniden aç

Kontrol:
```cmd
python --version
```

### 2. Otomatik kurulum (kolay yol)

Proje klasöründe `setup.bat` dosyasına çift tıkla. Eski `venv`'i silip paketleri kurar.

### 3. Manuel kurulum

```cmd
cd C:\Users\user\Desktop\AI_CNC_Inspector
rmdir /s /q venv
python -m venv venv
venv\Scripts\activate
pip install -r requirements-min.txt
```

## Çalıştırma

```cmd
start.bat
```

veya:

```cmd
venv\Scripts\activate
streamlit run app.py
```

Tarayıcıda `http://localhost:8501` adresi açılır. Aynı ağdaki telefon/tabletten de erişilebilir.

## Kullanım

1. **Yeni Hata Kaydı** — Hatalı parça fotoğrafı yükle, hata tipini etiketle, kaydet.
2. **Analiz** — Yeni fotoğraf yükle; sistem daha önce kaydedilen benzer hataları önerir.
3. **Geçmiş Kayıtlar** — Tüm etiketlenmiş hataları görüntüle.
4. **İstatistikler** — Hata tipi dağılımını takip et.

## Veri yapısı

```
data/
├── defects/          # Yüklenen fotoğraflar
└── cnc_inspector.db  # SQLite veritabanı
```

## Sonraki adımlar

- [ ] YOLO ile otomatik hata bölgesi tespiti
- [ ] Periyodik model yeniden eğitimi
- [ ] Çoklu kullanıcı desteği
- [ ] Makine parçası aşınma modülü
