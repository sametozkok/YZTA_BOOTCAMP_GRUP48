# 🌊 AquaSentinel AI — Sprint 1 Proje Yönetimi ve Scrum Raporu

> **Takım:** Takım 48  
> **Sprint Dönemi:** 19 Haziran — 5 Temmuz 2026 (Sprint 1)  
> **Sprint Hedefi:** Copernicus Sentinel-3 uydu verisi alma boru hattı (pipeline), veri ön işleme altyapısı ve projenin mimari iskeletinin oluşturulması.

---

## 📌 1. Backlog Dağıtma Mantığı ve Story Seçimleri

Bootcamp Bursiyer Kılavuzu kriterleri doğrultusunda **Sprint 1 Backlog** düzenimiz aşağıdaki prensiplere göre oluşturulmuştur:

1. **Önceliklendirme (Prioritization):** Yapay zeka modellerinin eğitilebilmesi ve AI agent'ların beslenebilmesi için öncelikle güvenilir, temiz ve kesintisiz bir veri akışına (data pipeline) ihtiyaç vardır. Bu nedenle Sprint 1'de tamamen veri altyapısına (Sentinel-3 CDSE OData API entegrasyonu, cloud/land masking ve time-series generation) odaklanılmıştır.
2. **Puanlama (Story Points):** Sprint başına tahmin edilen eforu yönetebilmek adına işler küçük, yönetilebilir alt görevlere (task'lere) bölünmüştür (1, 2, 3 ve 5 puanlık Fibonacci ölçeği kullanılmıştır).
3. **Görev Dağılımı:** Ekip içinde hiyerarşi olmadan, cross-functional çalışma prensibiyle her üye hem development hem de documentation ve unit testing süreçlerine aktif katkı sağlamıştır.

---

## 💬 2. Daily Scrum Notları 

> **📌 Takım üyelerimizin sprintin ilk haftalarında **üniversite mezuniyet bitirme projeleri/ödevleri** ve **yaz stajı başvuru/mesai yoğunlukları** sebebiyle senkron (canlı) toplantı düzenlenememiştir. İlerlememiz sprintin ilk bölümünde daha yavaş seyretmiş; asıl development eforu ve pipeline entegrasyonu **sprintin son günlerinde yoğun bir odaklanma (sprint crunch) ve WhatsApp Grubu üzerinden başarıyla tamamlanmıştır.


## 📋 3. Sprint Board Updates (Board Güncellemeleri)

Sprint boyunca görevlerin **Miro / Trello Sprint Board** üzerindeki ilerleyişi aşağıdaki Kanban tablosunda özetlenmiştir. 

> *(Not: Yoğun staj ve mezuniyet takvimleri nedeniyle task'lerin geliştirme ve test onay süreçleri sprintin son haftasında konsolide edilerek Done sütununa alınmıştır.)*

| Story ID | User Story / Görev Tanımı | Sorumlu Üyeler | Puan | Başlangıç Durumu | Güncel Durum (Sprint Kapanış) |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **US-101** | **Proje Mimarisinin ve Kurulum Altyapısının Hazırlanması**<br>• Repo açılışı, `.gitignore`, `.env.example`, `requirements.txt`<br>• Clean Code ve modüler klasör yapısının (`src/`, `tests/`, `doc/`) kurulması | Samet Özkök & Betül Danışmaz | 3 | To Do | ✅ **Done** |
| **US-102** | **Copernicus CDSE OData API Entegrasyonu (`sentinel_downloader.py`)**<br>• Sentinel-3 OLCI (Klorofil-a) ve SLSTR (SST) veri indirme modülü<br>• Otomatik oturum açma, token yönetimi ve sorgu filtreleme | Selma Bener & Fırat Kaan Çıkar | 5 | To Do | ✅ **Done** |
| **US-103** | **Veri Ön İşleme ve Temizleme Boru Hattı (`preprocessor.py`)**<br>• Bulut, kara ve hatalı piksellerin maskelenmesi (Quality Control)<br>• Marmara Denizi bounding box filtrelemesi ve zaman serisi (CSV) üretimi | Ahmet Yasir Duman & Selma Bener | 5 | To Do | ✅ **Done** |
| **US-104** | **AI Agent İskelet Mimarisi (`base_agent.py`)**<br>• Sprint 2'de geliştirilecek LLM tabanlı erken uyarı ajanları için soyut temel sınıf (BaseAgent) tasarımının yapılması | Fırat Kaan Çıkar & Samet Özkök | 3 | To Do | ✅ **Done** |
| **US-105** | **Birim Testleri (Unit Testing) ve Kalite Güvencesi**<br>• `pytest` ile veri indirme ve ön işleme fonksiyonları için 39 adet birim testinin yazılması ve doğrulanması | Betül Danışmaz & Ahmet Yasir Duman | 3 | To Do | ✅ **Done** |

---

## 💻 4. Ürün Durumu (Product Status & Çıktı Kanıtları)

Sprint 1 sonunda ortaya konan çalışır teknik ürünün ve altyapının mevcut durumu aşağıdakilerle doğrulanmıştır:

1. **Modüler ve Clean Code Altyapısı (`src/`):**
   * `sentinel_downloader.py`: Copernicus CDSE API'sine bağlanarak Marmara Denizi bounding box koordinatlarında otomatik OLCI/SLSTR uydu verisi indirebilmektedir (iletişim hatalarına karşı retry logic ve exception handling mevcuttur).
   * `preprocessor.py`: İndirilen ham raster verelerden quality flag'ler kullanılarak cloud/land masking (bulut/kara maskeleme) yapılmakta ve time-series analizi için `.csv` formatında temiz veri üretilmektedir.
   * `base_agent.py`: Object-Oriented Programming (OOP) prensimleriyle AI agent'larının türetileceği abstract base class (interface) başarıyla kurulmuştur.
2. **Otomatik Unit Test Kanıtı (`tests/`):**
   * CI/CD uyumlu `pytest` test suite'i koşturan terminal çıktısı başarımızı kanıtlamaktadır:
   ```text
   ============================= test session starts =============================
   platform win32 -- Python 3.12.x, pytest-8.3.x, pluggy-1.5.x
   rootdir: c:\Users\kaan\OneDrive\Desktop\final_bootcamp\test1
   collected 39 items

   tests\test_downloader.py ................................                [ 82%]
   tests\test_preprocessor.py .......                                       [100%]

   ============================== 39 passed in 0.45s ==============================
   ```

---

## 🎯 5. Sprint Review (Sprint Değerlendirmesi)

* **Toplantı Tarihi:** 4 Temmuz 2026
* **Katılımcılar:** Tüm Takım 48 Üyeleri (PO, SM, Developers)
* **Sunulan Çıktılar:**
  1. Copernicus Sentinel-3 uydu verilerini canlı olarak çekebilen ve mock modda çalışabilen modüler altyapı.
  2. Klorofil-a ve SST verilerinden cloud/land masking yaparak temiz time-series (CSV) üreten data pipeline.
  3. 39 adet başarıyla geçen unit test ve tam entegre çalışır codebase.
* **Karar:** Sprint 1 hedefi **%100 başarıyla** tamamlanmıştır. Ürün, Sprint 2'de machine learning modellerinin (Müsilaj Risk Endeksi) ve LLM-based early warning agent'larının entegre edilmesine tamamen hazırdır.

---

## 🔄 6. Sprint Retrospective (Retrospektif & Gelişim Alanları)

### 🟢 Neyi İyi Yaptık? (What went well?)
* **Kriz Yönetimi & Son Gün Odaklanması:** Sprint başında staj ve mezuniyet bitirme projeleri nedeniyle ilerlememiz yavaş olsa da panik yapmadan doğru önceliklendirme yaptık. Son günlerdeki yoğun odaklanma (sprint crunch) ile tüm MVP hedeflerini zamanında yetiştirdik.
* **Asenkron İmece & Cross-Functional Çalışma:** Toplantı yapamasak bile WhatsApp grubumuz üzerinden net, teknik ve çözüm odaklı anlık mesajlaşarak blocker'ları giderdik. PO ve SM dahi kod yazarak (development & testing) ekibin yükünü paylaştı.
* **Mock Mode & Test Odaklılık:** Gerçek uydu verisini indirmek vakit aldığı için `mock_mode` geliştirip `pytest` ile testleri paralel yürütmemiz, son gün entegrasyonunda bize büyük zaman kazandırdı.

### 🟡 Neyi Geliştirebiliriz? (What could be improved?)
* **Dengesiz İş Yükü Dağılımı (Velocity):** Okul/staj teslimleri nedeniyle eforun büyük kısmı sprintin son 3-4 gününe yığıldı. Sprint 2'de görevleri zaman çizelgesine daha dengeli yaymaya çalışmalıyız.
* **Canlı Sync İhtiyacı:** Asenkron iletişim işi bitirmemizi sağladı ancak kod entegrasyonu sırasında zaman zaman zorlaştı. Sprint 2'de haftada en az 1-2 kez 15 dakikalık canlı Google Meet check-in'i yapmalıyız.
* **API Request Limits & Caching:** Copernicus CDSE sunucuları saatlik isteklerde limit uygulayabiliyor. Sprint 2'de verileri diske önbellekleyen daha güçlü bir caching mechanism kurmalıyız.

### 🚀 Sprint 2 İçin Aksiyon Kararları (Action Items)
1. **[Aksiyon 1 - Scrum]** Sprint 2'de haftada en az 1-2 kez Discord veya Google Meet üzerinden 15 dakikalık kısa canlı check-in (sync) toplantısı organize etmek.
2. **[Aksiyon 2 - Teknik]** Sprint 2 başlar başlamaz Müsilaj Risk Endeksi'ni hesaplayacak machine learning modelinin veri setini `data/processed/` üzerinden beslemek.
3. **[Aksiyon 3 - Teknik]** LangGraph / LangChain tabanlı erken uyarı ajanının projenin LLM entegrasyonunu tamamlamak.
