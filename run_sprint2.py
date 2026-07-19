"""
AquaSentinel AI — Sprint 2 Ana Yürütme ve Orkestrasyon Betiği

Bu dosya, Sprint 2 hedeflerini gerçekleştirmek üzere:
1. Zaman serisi verilerini doğrular (yoksa sahte veri üretir).
2. Makine öğrenmesi risk modelini eğitir, kaydeder ve performansını ölçer.
3. DataAnalysisAgent, MucilageRiskAgent ve ReportingAgent'ı orkestre ederek
   güncel risk analiz raporunu hazırlar.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Windows konsolunda UTF-8 çıktı desteğini zorla
if sys.stdout:
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass
if sys.stderr:
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# .env dosyasını yükle (varsa)
load_dotenv()

from src.models.risk_model import MucilageRiskModel
from src.data.preprocessor import MarmaraDataPreprocessor
from src.agents.analyst_agent import DataAnalysisAgent
from src.agents.risk_agent import MucilageRiskAgent
from src.agents.reporting_agent import ReportingAgent
from src.utils import setup_logger, format_file_size

logger = setup_logger("run_sprint2", log_file="logs/sprint2_execution.log")


def main():
    print("\n==================================================")
    print("🌊 AquaSentinel AI — Sprint 2 Orkestrasyonu Başlıyor")
    print("==================================================\n")

    csv_path = Path("data/processed/marmara_time_series.csv")
    model_path = Path("models/mucilage_risk_model.joblib")

    # 1. Veri Hazırlığı
    if not csv_path.exists():
        print("[*] Zaman serisi CSV dosyası bulunamadı. Mock veri üretiliyor...")
        preprocessor = MarmaraDataPreprocessor()
        preprocessor.generate_mock_data("2024-01-01", "2024-12-31")
    else:
        print(f"[+] Mevcut veri seti bulundu: {csv_path} ({format_file_size(csv_path.stat().st_size)})")

    # 2. Model Eğitimi
    print("\n[*] Makine Öğrenmesi Modeli Eğitiliyor (Random Forest)...")
    model_wrapper = MucilageRiskModel(model_path=model_path)
    metrics = model_wrapper.train(csv_path)

    print("\n[+] Model Başarıyla Eğitildi ve Kaydedildi!")
    print(f"    - Test Seti Doğruluğu (Accuracy): %{metrics['accuracy']*100:.2f}")
    print("    - Özellik Önem Dereceleri (Feature Importances):")
    for feat, imp in metrics["feature_importances"].items():
        print(f"      * {feat:<15}: {imp:.4f}")

    # 3. Agent Çalışmaları ve Orkestrasyon
    print("\n[*] AI Ajanları Çalıştırılıyor...")

    # A. Veri Analiz Ajanı
    print("   [1/3] DataAnalysisAgent başlatılıyor...")
    analyst = DataAnalysisAgent()
    analysis_result = analyst.run({"csv_path": str(csv_path)})
    latest_metrics = analysis_result["latest_metrics"]
    print(f"         -> Son Gözlem Tarihi: {latest_metrics['date']}")
    print(f"         -> Sıcaklık (SST): {latest_metrics['sst']:.2f}°C (Eğilim: {latest_metrics['sst_trend']:+.4f} °C/gün)")
    print(f"         -> Klorofil-a: {latest_metrics['chlorophyll_a']:.2f} mg/m³ (Eğilim: {latest_metrics['chl_trend']:+.4f} mg/m³/gün)")
    print(f"         -> Anomali Sayısı: {analysis_result['anomalies_summary']['total_anomalies_count']}")

    # B. Müsilaj Risk Hesaplama Ajanı
    print("   [2/3] MucilageRiskAgent başlatılıyor...")
    risk_agent = MucilageRiskAgent(model_path=model_path)
    risk_result = risk_agent.run(analysis_result)
    prediction = risk_result["prediction"]
    print(f"         -> Model Risk Tahmini: %{prediction['risk_percentage']:.2f}")
    print(f"         -> Risk Seviyesi: {prediction['risk_level']}")

    # C. Raporlama ve Öneri Ajanı
    print("   [3/3] ReportingAgent başlatılıyor...")
    reporting_agent = ReportingAgent()
    
    report_output_path = Path("data/processed/mucilage_risk_report.md")
    report_result = reporting_agent.run({
        "analysis_data": analysis_result,
        "risk_data": risk_result,
        "output_path": str(report_output_path)
    })

    print(f"\n[+] Raporlama Tamamlandı! Dosya: {report_output_path}")

    # Agent Hafıza Kontrollerini Göster
    print("\n==================================================")
    print("🧠 Ajan Hafızalarından Özetler:")
    print(f" - {analyst.name} Hafıza Kayıt Sayısı: {len(analyst.get_memory())}")
    print(f" - {risk_agent.name} Hafıza Kayıt Sayısı: {len(risk_agent.get_memory())}")
    print(f" - {reporting_agent.name} Hafıza Kayıt Sayısı: {len(reporting_agent.get_memory())}")
    print("==================================================\n")


if __name__ == "__main__":
    main()
