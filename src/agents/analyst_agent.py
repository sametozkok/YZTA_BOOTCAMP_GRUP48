"""
AquaSentinel AI — DataAnalysisAgent (Veri Analizi ve Anomali Tespiti)

Bu modül, zaman serisi verilerinden sıcaklık ve klorofil artış hızlarını
hesaplayan, anomali ve pik değerleri tespit eden DataAnalysisAgent'ı tanımlar.
"""

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.agents.base_agent import BaseAquaSentinelAgent
from src.utils import setup_logger

logger = setup_logger(__name__, log_file="logs/analyst_agent.log")


class DataAnalysisAgent(BaseAquaSentinelAgent):
    """Zaman serisi verilerini analiz eden ve anomali tespiti yapan agent."""

    @property
    def name(self) -> str:
        return "DataAnalysisAgent"

    @property
    def description(self) -> str:
        return "Zaman serisi verilerini analiz eden, gradyanları hesaplayan ve anomali tespiti yapan analist agent."

    def __init__(self) -> None:
        super().__init__()
        # Araçları (Tools) kaydet
        self.register_tool("calculate_trends", self.calculate_trends)
        self.register_tool("detect_anomalies", self.detect_anomalies)

    def calculate_trends(self, csv_path: str | Path) -> dict[str, Any]:
        """Zaman serisindeki son verileri okur ve artış hızlarını hesaplar.

        Args:
            csv_path: Zaman serisi CSV dosyası.

        Returns:
            dict: Son tarihe ait parametreler ve trendler.
        """
        csv_path = Path(csv_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"Veri dosyası bulunamadı: {csv_path}")

        df = pd.read_csv(csv_path)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")

        df_chl = df[df["parameter_type"] == "chlorophyll_a"].copy()
        df_sst = df[df["parameter_type"] == "sst"].copy()

        # Birleştirme
        merged = pd.merge(
            df_sst[["date", "mean_value"]].rename(columns={"mean_value": "sst"}),
            df_chl[["date", "mean_value"]].rename(columns={"mean_value": "chlorophyll"}),
            on="date",
            how="inner"
        )

        if merged.empty:
            raise ValueError("CSV dosyasında birleştirilecek veri bulunamadı.")

        # Günlük farkları ve trendleri hesapla
        merged["days_diff"] = merged["date"].diff().dt.days.fillna(3.0)
        
        merged["sst_diff"] = merged["sst"].diff().fillna(0.0)
        merged["sst_trend"] = merged["sst_diff"] / merged["days_diff"]

        merged["chl_diff"] = merged["chlorophyll"].diff().fillna(0.0)
        merged["chl_trend"] = merged["chl_diff"] / merged["days_diff"]

        # Trendleri düzleştir (hareketli ortalama)
        merged["sst_trend"] = merged["sst_trend"].rolling(window=3, min_periods=1).mean()
        merged["chl_trend"] = merged["chl_trend"].rolling(window=3, min_periods=1).mean()

        # Son satırı al
        latest_row = merged.iloc[-1]

        result = {
            "date": latest_row["date"].strftime("%Y-%m-%d"),
            "sst": float(latest_row["sst"]),
            "sst_trend": float(latest_row["sst_trend"]),
            "chlorophyll_a": float(latest_row["chlorophyll"]),
            "chl_trend": float(latest_row["chl_trend"]),
            "data_points_count": len(merged)
        }

        self.log_action("calculate_trends", result, {"csv_path": str(csv_path)})
        return result

    def detect_anomalies(self, csv_path: str | Path, window_size: int = 10) -> dict[str, Any]:
        """Zaman serisinde ortalamadan sapma bazlı anomali tespiti yapar.

        Sapma Formülü: |Değer - Hareketli_Ortalama| > 2 * Hareketli_Standart_Sapma

        Args:
            csv_path: Zaman serisi CSV dosyası.
            window_size: Hareketli pencere boyutu (gözlem sayısı).

        Returns:
            dict: Tespit edilen anomaliler listesi ve istatistikleri.
        """
        csv_path = Path(csv_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"Veri dosyası bulunamadı: {csv_path}")

        df = pd.read_csv(csv_path)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")

        anomalies_list = []

        for p_type in ["sst", "chlorophyll_a"]:
            sub_df = df[df["parameter_type"] == p_type].copy()
            if len(sub_df) < window_size:
                continue

            # Hareketli ortalama ve standart sapma
            sub_df["roll_mean"] = sub_df["mean_value"].rolling(window=window_size, min_periods=3).mean()
            sub_df["roll_std"] = sub_df["mean_value"].rolling(window=window_size, min_periods=3).std()

            # Standart sapma sıfır veya NaN ise küçük bir eşik ata
            sub_df["roll_std"] = sub_df["roll_std"].fillna(0.1).replace(0.0, 0.1)

            # Anomali koşulu: Z-skoru > 2
            sub_df["z_score"] = (sub_df["mean_value"] - sub_df["roll_mean"]) / sub_df["roll_std"]
            anom_df = sub_df[sub_df["z_score"].abs() > 2.0]

            for _, row in anom_df.iterrows():
                anomalies_list.append({
                    "date": row["date"].strftime("%Y-%m-%d"),
                    "parameter": p_type,
                    "value": float(row["mean_value"]),
                    "expected_mean": float(row["roll_mean"]),
                    "z_score": float(row["z_score"]),
                    "severity": "High" if abs(row["z_score"]) > 3.0 else "Medium"
                })

        result = {
            "total_anomalies_count": len(anomalies_list),
            "anomalies": anomalies_list
        }

        self.log_action("detect_anomalies", result, {"csv_path": str(csv_path)})
        return result

    def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Zaman serisi verisini analiz eder.

        Args:
            input_data: {"csv_path": str}

        Returns:
            dict: Trend analiz sonuçları ve anomaliler.
        """
        csv_path = input_data.get("csv_path", "data/processed/marmara_time_series.csv")
        logger.info("Veri analizi başlatıldı, dosya: %s", csv_path)

        trends = self.calculate_trends(csv_path)
        anomalies = self.detect_anomalies(csv_path)

        output = {
            "status": "success",
            "latest_metrics": trends,
            "anomalies_summary": anomalies
        }

        logger.info("Veri analizi tamamlandı.")
        return output
