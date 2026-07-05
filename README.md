# 🌊 AquaSentinel AI

**Uydu Verileri Destekli Yapay Zeka Tabanlı Müsilaj Erken Uyarı Sistemi**

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Sprint](https://img.shields.io/badge/Sprint-1%20Tamamlandı-brightgreen.svg)]()
[![Tests](https://img.shields.io/badge/Tests-39%20Passed-success.svg)]()

---

## 📖 Proje Hakkında

**AquaSentinel AI**, Marmara Denizi'nde müsilaj (deniz salyası) oluşumunu erken aşamada tespit etmek ve risk değerlendirmesi yapmak amacıyla geliştirilen yapay zeka tabanlı bir erken uyarı sistemidir.

Sistem, **Copernicus Sentinel-3** uydu verilerini (Klorofil-a konsantrasyonu ve Deniz Yüzeyi Sıcaklığı - SST) otomatik olarak indirip işleyerek:

- 🛰️ Uydu verisi toplama ve ön işleme boru hattı
- 🧠 Müsilaj risk endeksi hesaplayan AI modeli (Sprint 2)
- 🤖 Risk raporları üreten AI Agent mimarisi (Sprint 2)
- 🗺️ Harita tabanlı web dashboard (Sprint 3)

bileşenlerinden oluşmaktadır.

---

## 🎯 Ürün Bilgileri

| Alan | Detay |
|------|-------|
| **Ürün İsmi** | AquaSentinel AI |
| **Takım İsmi** | Takım 48 |
| **Product Backlog** | [Sprint 1 Raporu](doc/sprint1_review.md) |

### Ürün Açıklaması

AquaSentinel AI, Marmara Denizi'ndeki müsilaj oluşumunu Copernicus Sentinel-3 uydu verileri ve yapay zeka modelleri kullanarak erken aşamada tespit eden bir erken uyarı sistemidir. Sistem, deniz yüzeyi sıcaklığı (SST) ve klorofil-a yoğunluğu verilerini otomatik olarak toplayıp analiz ederek, müsilaj riskini önceden tahmin eder ve karar vericilere harita tabanlı bir dashboard üzerinden uyarılar sunar.

### Ürün Özellikleri

**MVP (Sprint 1-2)**
- Sentinel-3 OLCI/SLSTR uydu verisi otomatik indirme (CDSE OData API)
- Marmara Denizi bölgesi için veri filtreleme ve ön işleme
- Bulut/kara/hatalı piksel maskeleme ve kalite kontrolü
- Klorofil-a ve SST zaman serisi oluşturma
- Müsilaj Risk Endeksi hesaplama (AI model — Sprint 2)
- AI Agent ile risk raporu üretimi (Sprint 2)

**Ek Özellikler (Sprint 3)**
- Harita tabanlı (GIS) web dashboard
- Gerçek zamanlı erken uyarı sistemi
- Tarihsel trend analizi ve görselleştirme
- Canlıya alınabilir ürün

### Hedef Kitle

- Çevre ve Şehircilik Bakanlığı
- Belediyelerin çevre birimleri
- Denizcilik ve su ürünleri sektörü
- Araştırmacılar

---

## 🏗️ Mimari Yapı

```
aquasentinel-ai/
├── data/
│   ├── raw/                         # Ham uydu verileri (NetCDF/TIF)
│   └── processed/                   # İşlenmiş zaman serisi (CSV)
├── src/
│   ├── data/
│   │   ├── sentinel_downloader.py   # CDSE OData API veri indirme
│   │   └── preprocessor.py          # Kalite filtreleme ve istatistik
│   ├── agents/
│   │   └── base_agent.py            # AI Agent temel sınıfı
│   └── utils.py                     # Loglama ve yardımcı fonksiyonlar
├── tests/                           # Birim testleri (pytest)
├── doc/                             # Proje dokümantasyonu
├── .env.example                     # Ortam değişkeni şablonu
├── requirements.txt                 # Python bağımlılıkları
└── README.md                        # Bu dosya
```

---

## 🚀 Kurulum ve Çalıştırma

### Ön Gereksinimler

- Python 3.10 veya üstü
- pip (Python paket yöneticisi)
- Git

### Adım 1: Depoyu Klonlayın

```bash
git clone https://github.com/sametozkok/YZTA_BOOTCAMP_GRUP48.git
cd aquasentinel-ai
```

### Adım 2: Sanal Ortam Oluşturun

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### Adım 3: Bağımlılıkları Yükleyin

```bash
pip install -r requirements.txt
```

### Adım 4: Ortam Değişkenlerini Ayarlayın

```bash
# .env.example dosyasını .env olarak kopyalayın
copy .env.example .env    # Windows
cp .env.example .env      # macOS / Linux

# .env dosyasını açıp CDSE kimlik bilgilerinizi girin
# Hesap oluşturmak için: https://dataspace.copernicus.eu/
```

### Adım 5: Testleri Çalıştırın

```bash
python -m pytest tests/ -v
```

---

## 💻 Kullanım Örnekleri

### Mock Veri ile Hızlı Başlangıç (API Hesabı Gerekmez)

```python
from src.data.sentinel_downloader import SentinelDataDownloader
from src.data.preprocessor import MarmaraDataPreprocessor

# 1. Mock modda veri indir (API hesabı olmadan)
downloader = SentinelDataDownloader()
mock_file = downloader.download_marmara_data(
    start_date="2024-06-01",
    end_date="2024-06-15",
    output_dir="data/raw",
)
print(f"Mock veri oluşturuldu: {mock_file}")

# 2. Gerçekçi simüle zaman serisi üret
processor = MarmaraDataPreprocessor(processed_dir="data/processed")
csv_path = processor.generate_mock_data(
    start_date="2024-01-01",
    end_date="2024-12-31",
    interval_days=3,
)
print(f"Zaman serisi: {csv_path}")
```

### Gerçek Uydu Verisi İndirme (CDSE Hesabı Gerekir)

```python
from src.data.sentinel_downloader import SentinelDataDownloader

# .env dosyasında CDSE_USERNAME ve CDSE_PASSWORD tanımlı olmalı
downloader = SentinelDataDownloader()

# Marmara Denizi için Sentinel-3 OLCI (Klorofil-a) verisi
result = downloader.download_marmara_data(
    start_date="2024-06-01",
    end_date="2024-06-15",
    output_dir="data/raw",
    product_type="chlorophyll",  # veya "sst"
)
```

---

## 📊 Bootcamp Sprint Planı & Durumu

| Sprint / Dönem | Odak Noktası | Yapılacak İşler (Task'ler) & Örnekler | Teslim Edilecekler | Durum |
|---|---|---|---|:---:|
| **Sprint 1**<br>*(19 Haz — 5 Tem)* | **Veri Boru Hattı & Altyapı** | • Sentinel API bağlantılarının kurulması.<br>• Marmara Denizi geçmiş müsilaj dönemlerine ait SST (Deniz Yüzeyi Sıcaklığı) verilerinin çekilmesi.<br>• Veri temizleme ve anomali tespiti altyapısı.<br>• Slack Daily Scrum düzeninin kurulması. | • GitHub Repo Açılışı<br>• README (Takım/Ürün vizyonu)<br>• Miro Backlog Düzeni<br>• [Sprint 1 Raporu](doc/sprint1_review.md) | ✅ **Tamamlandı** |
| **Sprint 2**<br>*(6 Tem — 19 Tem)* | **AI Model & Agent Geliştirme** | • Sıcaklık artış hızı ve klorofil yoğunluğuna göre "Müsilaj Risk Endeksi" hesaplayan modelin eğitilmesi.<br>• Risk raporları hazırlayacak AI Agent mimarisinin (hafıza ve araç entegrasyonu) kurgulanması.<br>• Temiz kod mimarisinin kurulması. | • Model Performans Raporu<br>• Güncellenmiş Sprint Board<br>• Daily Scrum Notları | 🔜 **Planlanıyor** |
| **Sprint 3**<br>*(20 Tem — 2 Ağu)* | **Entegrasyon, Dağıtım & Kapanış** | • AI Agent ile tahmin modelinin orkestre edilmesi.<br>• Harita tabanlı (GIS) basit bir web arayüzünün (dashboard) canlıya alınması.<br>• Kodun refactor edilmesi (Clean Code).<br>• 3 dakikalık YouTube proje videosunun çekilmesi. | • Canlı Ürün Linki<br>• 3 Dk YouTube Videosu<br>• Ürün Teslim Formu | ⏳ **Beklemede** |

### Sprint 1 Teslim Edilenler

- ✅ [Sprint 1 Raporu](doc/sprint1_review.md)
- ✅ Sentinel-3 CDSE OData API bağlantısı (gerçek API doğrulandı)
- ✅ Marmara Denizi SST ve Klorofil-a veri çekme altyapısı
- ✅ Veri temizleme (bulut/kara/hatalı piksel maskeleme)
- ✅ Zaman serisi oluşturma (CSV)
- ✅ AI Agent iskelet yapısı (Sprint 2 hazırlığı)
- ✅ 39 birim testi (hepsi geçiyor)


---

## 🛰️ Veri Kaynakları

| Kaynak | Ürün | Parametre | Çözünürlük |
|--------|------|-----------|------------|
| Sentinel-3 OLCI | OL_2_WFR___ | Klorofil-a (mg/m³) | 300m |
| Sentinel-3 SLSTR | SL_2_LST___ | Deniz Yüzeyi Sıcaklığı (°C) | 1km |

**API:** [Copernicus Dataspace Ecosystem (CDSE)](https://dataspace.copernicus.eu/)

---

## 🧪 Test

```bash
# Tüm testleri çalıştır
python -m pytest tests/ -v

# Sadece downloader testleri
python -m pytest tests/test_downloader.py -v

# Sadece preprocessor testleri
python -m pytest tests/test_preprocessor.py -v
```

---

## 

Bu proje, Yapay Zeka ve Teknoloji Akademisi Bootcamp 2026 kapsamında geliştirilmektedir.

---

## 👥 Takım

| Rol | İsim |
|-----|------|
| **Product Owner** | Samet Özkök |
| **Scrum Master** | Betül Danışmaz |
| **Team Member / Developer** | Selma Bener |
| **Team Member / Developer** | Ahmet Yasir Duman |
| **Team Member / Developer** | Fırat Kaan Çıkar |
