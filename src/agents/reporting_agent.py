"""
AquaSentinel AI — ReportingAgent (Müsilaj Risk Raporlama)

Bu modül, DataAnalysisAgent ve MucilageRiskAgent çıktılarını birleştirerek,
Gemini API (veya çevrimdışı şablon) desteğiyle profesyonel bir Müsilaj Risk
Raporu hazırlayan ReportingAgent'ı tanımlar.
"""

import os
from pathlib import Path
from typing import Any, Optional

from src.agents.base_agent import BaseAquaSentinelAgent
from src.utils import setup_logger

logger = setup_logger(__name__, log_file="logs/reporting_agent.log")


class ReportingAgent(BaseAquaSentinelAgent):
    """Bulgu ve tahmin sonuçlarını birleştirerek risk raporları oluşturan agent."""

    @property
    def name(self) -> str:
        return "ReportingAgent"

    @property
    def description(self) -> str:
        return "Diğer agent'ların bulgularını birleştirerek Gemini API veya çevrimdışı şablonlarla risk raporu üreten agent."

    def __init__(self) -> None:
        super().__init__()
        # Araçları (Tools) kaydet
        self.register_tool("generate_report", self.generate_report)

    def generate_report(
        self,
        analysis_data: dict[str, Any],
        risk_data: dict[str, Any],
        output_path: str | Path = "data/processed/mucilage_risk_report.md"
    ) -> str:
        """Girdi verilerini yorumlar ve detaylı Markdown raporu üretir.

        Args:
            analysis_data: DataAnalysisAgent çıktı verisi.
            risk_data: MucilageRiskAgent çıktı verisi.
            output_path: Raporun yazılacağı dosya yolu.

        Returns:
            str: Hazırlanan rapor metni.
        """
        output_path = Path(output_path)
        
        # Değişkenleri ayıkla
        latest_metrics = analysis_data.get("latest_metrics", {})
        anomalies_summary = analysis_data.get("anomalies_summary", {})
        prediction = risk_data.get("prediction", {})

        date_str = latest_metrics.get("date", "Bilinmeyen Tarih")
        sst = latest_metrics.get("sst", 0.0)
        sst_trend = latest_metrics.get("sst_trend", 0.0)
        chl = latest_metrics.get("chlorophyll_a", 0.0)
        chl_trend = latest_metrics.get("chl_trend", 0.0)

        risk_percentage = prediction.get("risk_percentage", 0.0)
        risk_level = prediction.get("risk_level", "Unknown")

        anomalies = anomalies_summary.get("anomalies", [])
        anomalies_str = ""
        if anomalies:
            for idx, a in enumerate(anomalies[-5:]):  # Son 5 anomaliyi göster
                anomalies_str += f"- **{a['date']}**: {a['parameter']} parametresinde anomali tespit edildi. Değer: {a['value']}, Önceki Ortalama: {a['expected_mean']} (Şiddet: {a['severity']})\n"
        else:
            anomalies_str = "- Yakın zamanda herhangi bir anomali tespit edilmemiştir.\n"

        # Gemini API kullanmayı dene
        api_key = os.getenv("GEMINI_API_KEY")
        report_content = ""
        online_success = False

        if api_key:
            try:
                import google.generativeai as genai

                genai.configure(api_key=api_key)
                
                # gemini-2.0-flash modelini kullan
                model = genai.GenerativeModel("gemini-2.0-flash")
                
                prompt = f"""
Sen AquaSentinel AI deniz bilimleri ve çevre koruma uzmanı yapay zeka ajanısın.
Marmara Denizi'nden elde edilen aşağıdaki uydu gözlem verilerini analiz et ve çevre/belediye yetkilileri için profesyonel bir "Müsilaj Risk Raporu" oluştur.

Gözlem Tarihi: {date_str}
Deniz Yüzeyi Sıcaklığı (SST): {sst:.2f}°C (Günlük Eğilim: {sst_trend:+.4f} °C/gün)
Klorofil-a Konsantrasyonu: {chl:.2f} mg/m³ (Günlük Eğilim: {chl_trend:+.4f} mg/m³/gün)
Hesaplanan Müsilaj Risk Oranı: %{risk_percentage}
Risk Seviyesi: {risk_level}

Tespit Edilen Son Anomaliler:
{anomalies_str}

Lütfen raporu şu bölümlerle Türkçe olarak ve oldukça profesyonel bir tonda yaz:
# 🌊 Marmara Denizi Müsilaj Risk Raporu ({date_str})

## Giriş ve Genel Durum
(Kısa özet)

## 1. Uydu Gözlemleri ve Parametrik Analizler
(SST ve Klorofil-a değerlerini, artış hızlarını ve bunların müsilaj oluşumu üzerindeki etkilerini biyolojik olarak yorumla)

## 2. Müsilaj Risk Değerlendirmesi
(Makine öğrenmesi modelinin bulduğu %{risk_percentage} risk oranını ve {risk_level} seviyesini analiz et. Sıcaklık artış hızının tetikleyici gücünü açıkla)

## 3. Anomali ve Sıradışı Durum Analizleri
(Tespit edilen anomalileri değerlendir, ani ısı artışları veya klorofil patlamaları var mı yorumla)

## 4. Yetkililere Yönelik Acil Önlemler ve Eylem Önerileri
(Yerel yönetimler ve Çevre Bakanlığı için somut, uygulanabilir, kısa ve orta vadeli eylemleri maddeler halinde sırala)

Not: Sadece Markdown formatında çıktı ver, başında ve sonunda markdown blokları (```markdown) kullanma.
"""
                logger.info("Gemini API üzerinden rapor üretiliyor...")
                response = model.generate_content(prompt)
                report_content = response.text.strip()
                online_success = True
                logger.info("Gemini API rapor üretimi başarılı.")
            except Exception as exc:
                logger.error("Gemini API hatası oluştu, çevrimdışı şablona geçiliyor: %s", exc)

        # Çevrimdışı şablon (Fallback)
        if not online_success:
            logger.info("Çevrimdışı/Simüle rapor şablonu kullanılıyor...")
            
            # Risk seviyesine göre yorum ve eylemleri belirle
            if risk_level == "Low":
                eval_comment = "Parametreler mevsim normallerindedir. Müsilaj riski düşüktür."
                actions = [
                    "Rutin uydu izleme çalışmalarına devam edilmeli.",
                    "Arıtma tesislerinin standart deşarj kontrolleri sürdürülmeli."
                ]
            elif risk_level == "Medium":
                eval_comment = "Sıcaklık ve klorofil değerlerinde hafif yükseliş eğilimi bulunmaktadır. Orta derecede risk mevcuttur."
                actions = [
                    "Hassas bölgelerde (körfezler vb.) yerinde örnekleme sıklığı artırılmalı.",
                    "Deşarj izleme sıklığı artırılmalı, tesis denetimleri sıkılaştırılmalı."
                ]
            elif risk_level == "High":
                eval_comment = "Sıcaklık 22°C tetikleme eşiğine yakın/üstünde olup, klorofil artış hızı yüksektir. Müsilaj oluşumunu tetikleyebilecek ciddi bir risk mevcuttur."
                actions = [
                    "Çevre, Şehircilik ve İklim Değişikliği Bakanlığı ve ilgili belediyeler acil durum izleme moduna geçmeli.",
                    "Derelere ve deniz alıcı ortamına yapılan deşarjlarda azot-fosfor arıtımı daha sıkı denetlenmeli.",
                    "Erken müdahale gemileri ve bariyer sistemleri hazırlık seviyesine getirilmeli."
                ]
            else:  # Extreme
                eval_comment = "Sıcaklık ve klorofil-a konsantrasyonu kritik sınırları aşmış ve güçlü artış eğilimindedir. Müsilaj patlaması an meselesidir veya başlamıştır."
                actions = [
                    "Müsilaj Acil Eylem Planı derhal devreye sokulmalı.",
                    "Tüm endüstriyel ve evsel deşarjlar geçici olarak kısıtlanmalı / ileri arıtma seviyelerine zorlanmalı.",
                    "Fiziksel temizlik ekipleri riskli koy ve limanlarda konuşlandırılmalıdır."
                ]

            actions_str = "\n".join([f"- **Acil:** {a}" if idx == 0 else f"- {a}" for idx, a in enumerate(actions)])

            report_content = f"""# 🌊 Marmara Denizi Müsilaj Risk Raporu ({date_str})

> **[UYARI: ÇEVRİMDIŞI ŞABLON]** *Gemini API anahtarı ayarlanmadığı için bu rapor otomatik kural motoru tarafından üretilmiştir.*

## Giriş ve Genel Durum
Bu rapor, Marmara Denizi genelindeki Sentinel-3 uydu verilerinden türetilen Deniz Yüzeyi Sıcaklığı (SST) ve Klorofil-a zaman serisi analiz sonuçları doğrultusunda hazırlanmıştır.

## 1. Uydu Gözlemleri ve Parametrik Analizler
* **Gözlem Tarihi:** {date_str}
* **Deniz Yüzeyi Sıcaklığı (SST):** {sst:.2f}°C (Eğilim: {sst_trend:+.4f} °C/gün)
* **Klorofil-a Konsantrasyonu:** {chl:.2f} mg/m³ (Eğilim: {chl_trend:+.4f} mg/m³/gün)

## 2. Müsilaj Risk Değerlendirmesi
AquaSentinel AI tahmin modeline göre Marmara Denizi'nde müsilaj oluşum olasılığı **%{risk_percentage:.1f}** olarak hesaplanmış ve risk seviyesi **{risk_level}** olarak sınıflandırılmıştır.
* **Yorum:** {eval_comment}

## 3. Anomali ve Sıradışı Durum Analizleri
Yakın zamanda tespit edilen zaman serisi anomalileri aşağıda sunulmuştur:
{anomalies_str}

## 4. Yetkililere Yönelik Acil Önlemler ve Eylem Önerileri
{actions_str}
"""

        # Raporu kaydet
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(report_content, encoding="utf-8")
            logger.info("Rapor başarıyla kaydedildi: %s", output_path)
        except Exception as exc:
            logger.error("Rapor kaydetme hatası: %s", exc)

        self.log_action("generate_report", {"output_path": str(output_path), "risk_level": risk_level}, {
            "online_mode": online_success
        })
        return report_content

    def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Raporlama işlemini yürütür.

        Args:
            input_data: {"analysis_data": dict, "risk_data": dict, "output_path": Optional[str]}

        Returns:
            dict: Rapor dosyası yolu ve durum.
        """
        analysis_data = input_data.get("analysis_data")
        risk_data = input_data.get("risk_data")
        output_path = input_data.get("output_path", "data/processed/mucilage_risk_report.md")

        if not analysis_data or not risk_data:
            raise ValueError("Rapor üretmek için 'analysis_data' ve 'risk_data' gereklidir.")

        logger.info("Rapor oluşturuluyor...")
        report_text = self.generate_report(analysis_data, risk_data, output_path)

        output = {
            "status": "success",
            "report_path": str(output_path),
            "report_preview": report_text[:300] + "..."
        }

        logger.info("Raporlama tamamlandı.")
        return output
