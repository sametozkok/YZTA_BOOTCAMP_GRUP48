# 🌊 AquaSentinel AI — Sprint 1 Proje Yönetimi ve Scrum Raporu

> **Takım:** Takım 48  
> **Sprint Dönemi:** 19 Haziran — 5 Temmuz 2026 (Sprint 1)  
> **Sprint Hedefi:** Copernicus Sentinel-3 uydu verisi alma boru hattı (pipeline), veri ön işleme altyapısı ve projenin mimari iskeletinin oluşturulması.

---

## 📌 Backlog Dağıtma Mantığı ve Story Seçimleri

Bootcamp Bursiyer Kılavuzu kriterleri doğrultusunda **Sprint 1 Backlog** düzenimiz aşağıdaki prensiplere göre oluşturulmuştur:

1. **Önceliklendirme (Prioritization):** Yapay zeka modellerinin eğitilebilmesi ve ajanların beslenebilmesi için öncelikle güvenilir, temiz ve kesintisiz bir veri akışına ihtiyaç vardır. Bu nedenle Sprint 1'de tamamen veri altyapısına (Sentinel-3 CDSE OData API entegrasyonu, bulut/kara maskeleme ve zaman serisi üretimi) odaklanılmıştır.
2. **Puanlama (Story Points):** Sprint başına tahmin edilen puan sayısını geçmeyecek şekilde efor tahminleri yapılmıştır. Story başına çıkan tahmin puanı, toplam puanın yarısından az tutularak işler küçük, yönetilebilir alt görevlere (task'lere) bölünmüştür (1, 2, 3 ve 5 puanlık Fibonacci ölçeği kullanılmıştır).
3. **Görev Dağılımı:** Ekip içinde hiyerarşi olmadan, çapraz fonksiyonel (cross-functional) çalışma prensibiyle her üye hem kod geliştirmeye hem de dokümantasyon ve test süreçlerine aktif katkı sağlamıştır.

---

## 🎯 Sprint Review (Sprint Değerlendirmesi)

* **Toplantı Tarihi:** 4 Temmuz 2026
* **Katılımcılar:** Tüm Takım 48 Üyeleri (PO, SM, Developers)
* **Sunulan Çıktılar:**
  1. Copernicus Sentinel-3 uydu verilerini canlı olarak çekebilen ve mock modda çalışabilen modüler altyapı.
  2. Klorofil-a ve SST verilerinden bulut/kara maskelemesi yaparak temiz zaman serisi (CSV) üreten boru hattı.
  3. 39 adet başarıyla geçen birim testi ve tam entegre çalışır kod tabanı.
* **Karar:** Sprint 1 hedefi **%100 başarıyla** tamamlanmıştır. Ürün, Sprint 2'de yapay zeka modellerinin (Müsilaj Risk Endeksi) ve erken uyarı ajanlarının (AI Agents) entegre edilmesine tamamen hazırdır.

---

## 🔄 Sprint Retrospective (Retrospektif & Gelişim Alanları)

### 🚀 Sprint 2 İçin Aksiyon Kararları (Action Items)
1. **[Aksiyon 1 - Scrum]** Sprint 2'de haftada en az 2 veya 3 kez kısa (10-15 dk) Daily Scrum toplantısı organize etmek.
2. **[Aksiyon 2 - Teknik]** Sprint 2 başlar başlamaz Müsilaj Risk Endeksi'ni hesaplayacak makine öğrenmesi modelinin veri setini `data/processed/` üzerinden beslemek.
3. **[Aksiyon 3 - Teknik]** LangGraph / LangChain tabanlı erken uyarı ajanının projenin LLM entegrasyonunu tamamlamak.
