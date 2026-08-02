"""
AquaSentinel AI — Arayüz Tahmin Entegrasyon Betiği (Predictions Generator)

Bu betik, Sprint 2 kapsamında eğitilen Random Forest modelini ('models/mucilage_risk_model.joblib')
ve ön işlenmiş zaman serisi verilerini ('data/processed/marmara_time_series.csv') yükler.
Zaman serisindeki her tarih ve her bölge için modelden gerçek risk tahminlerini hesaplar ve
frontend'in okuyabileceği 'src/frontend/predictions.json' dosyasına yazar.
"""

import json
import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import joblib

# Windows UTF-8 desteği
if sys.stdout:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
if sys.stderr:
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# Proje kökünü yola ekle
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from src.models.risk_model import MucilageRiskModel
from src.utils import ensure_directory, setup_logger

logger = setup_logger("generate_predictions", log_file="logs/generate_predictions.log")

# Arayüzde tanımlı bölge katsayıları
REGION_COEFFICIENTS = {
    "all": {"chl": 1.0, "sst": 1.0},
    "izmit": {"chl": 1.45, "sst": 1.05},
    "gemlik": {"chl": 1.30, "sst": 1.02},
    "adalar": {"chl": 1.10, "sst": 0.98},
    "bandirma": {"chl": 1.25, "sst": 1.01},
    "tekirdag": {"chl": 0.85, "sst": 0.95}
}

def main():
    print("[*] Arayüz için gerçek yapay zeka tahminleri üretiliyor...")
    
    csv_path = Path("data/processed/marmara_time_series.csv")
    model_path = Path("models/mucilage_risk_model.joblib")
    output_path = Path("src/frontend/predictions.json")

    if not csv_path.exists():
        print(f"[-] Hata: Zaman serisi verisi bulunamadı: {csv_path}")
        return

    if not model_path.exists():
        print(f"[-] Hata: Eğitilmiş model dosyası bulunamadı: {model_path}. Lütfen önce 'python run_sprint2.py' komutunu çalıştırın.")
        return

    # Modeli Yükle
    model_wrapper = MucilageRiskModel(model_path=model_path)
    if not model_wrapper.load():
        print("[-] Hata: Model yüklenemedi.")
        return

    # Veriyi Oku ve Hazırla
    df = pd.read_csv(csv_path)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    # Parametreleri ayır
    df_chl = df[df["parameter_type"] == "chlorophyll_a"].copy()
    df_sst = df[df["parameter_type"] == "sst"].copy()

    # Birleştir
    merged = pd.merge(
        df_sst[["date", "mean_value"]].rename(columns={"mean_value": "sst"}),
        df_chl[["date", "mean_value"]].rename(columns={"mean_value": "chlorophyll_a"}),
        on="date",
        how="inner"
    )

    if merged.empty:
        print("[-] Hata: Veri seti boş veya SST ile Chlorophyll tarihleri uyuşmuyor.")
        return

    # Zaman farkını hesapla
    merged["days_diff"] = merged["date"].diff().dt.days.fillna(3.0)

    # Base trendleri hesapla
    merged["sst_diff"] = merged["sst"].diff().fillna(0.0)
    merged["sst_trend"] = merged["sst_diff"] / merged["days_diff"]
    
    merged["chl_diff"] = merged["chlorophyll_a"].diff().fillna(0.0)
    merged["chl_trend"] = merged["chl_diff"] / merged["days_diff"]

    merged["sst_trend"] = merged["sst_trend"].rolling(window=3, min_periods=1).mean()
    merged["chl_trend"] = merged["chl_trend"].rolling(window=3, min_periods=1).mean()

    predictions_db = {}

    # Her tarih için dön
    for _, row in merged.iterrows():
        date_str = row["date"].strftime("%Y-%m-%d")
        predictions_db[date_str] = {}

        # Her bölge için ölçeklendir ve tahmini çalıştır
        for region, coeffs in REGION_COEFFICIENTS.items():
            # Değerleri bölge katsayılarına göre ölçekle
            local_chl = float(row["chlorophyll_a"] * coeffs["chl"])
            local_sst = float(row["sst"] * coeffs["sst"])
            
            # Trendleri de aynı oranda ölçekle
            local_chl_trend = float(row["chl_trend"] * coeffs["chl"])
            local_sst_trend = float(row["sst_trend"] * coeffs["sst"])

            # Model Tahmini
            try:
                pred = model_wrapper.predict_risk(
                    sst=local_sst,
                    sst_trend=local_sst_trend,
                    chl=local_chl,
                    chl_trend=local_chl_trend
                )
                
                predictions_db[date_str][region] = {
                    "risk_percentage": pred["risk_percentage"],
                    "risk_level": pred["risk_level"],
                    "chlorophyll_a": round(local_chl, 2),
                    "sst": round(local_sst, 1)
                }
            except Exception as e:
                logger.error("Predict error for %s in %s: %s", date_str, region, e)

    # JSON Olarak Kaydet
    ensure_directory(output_path.parent)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(predictions_db, f, indent=2, ensure_ascii=False)

    print(f"[+] Başarılı! Yapay zeka tahmin veri tabanı arayüze entegre edildi: {output_path}")

if __name__ == "__main__":
    main()
