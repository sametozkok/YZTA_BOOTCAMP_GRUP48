"""
AquaSentinel AI — Müsilaj Risk Endeksi Tahmin Modeli

Bu modül, deniz yüzeyi sıcaklığı (SST), klorofil-a konsantrasyonu ve bunların
artış hızlarını (gradyanlarını) kullanarak müsilaj riskini tahmin eden bir
makine öğrenmesi modeli tanımlar, eğitir ve kaydeder.

Kullanılan Algoritma: Random Forest Classifier (Rastgele Orman Sınıflandırıcısı)
Açıklama: Karar ağaçları topluluğu kullanarak doğrusal olmayan ilişkileri ve
          değişken etkileşimlerini yüksek doğrulukla modeller.
"""

import os
from pathlib import Path
from typing import Any, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

from src.utils import ensure_directory, setup_logger

logger = setup_logger(__name__, log_file="logs/risk_model.log")


class MucilageRiskModel:
    """Müsilaj riskini tahmin eden Random Forest tabanlı makine öğrenmesi modeli."""

    def __init__(self, model_path: Optional[str | Path] = None) -> None:
        """MucilageRiskModel sınıfını başlatır.

        Args:
            model_path: Eğitilmiş modelin (.joblib) dosya yolu.
        """
        self.model_path = Path(model_path) if model_path else Path("models/mucilage_risk_model.joblib")
        self.model: Optional[RandomForestClassifier] = None
        self.feature_names = ["sst", "sst_trend", "chlorophyll_a", "chl_trend"]

    def load(self) -> bool:
        """Eğitilmiş model dosyasını diskten yükler.

        Returns:
            bool: Yükleme başarılıysa True, değilse False.
        """
        if not self.model_path.exists():
            logger.warning("Model dosyası bulunamadı: %s", self.model_path)
            return False

        try:
            self.model = joblib.load(self.model_path)
            logger.info("Model başarıyla yüklendi: %s", self.model_path)
            return True
        except Exception as exc:
            logger.error("Model yükleme hatası: %s", exc, exc_info=True)
            return False

    def save(self) -> None:
        """Mevcut modeli diske kaydeder."""
        if self.model is None:
            raise ValueError("Kaydedilecek eğitilmiş bir model yok.")

        ensure_directory(self.model_path.parent)
        try:
            joblib.dump(self.model, self.model_path)
            logger.info("Model başarıyla kaydedildi: %s", self.model_path)
        except Exception as exc:
            logger.error("Model kaydetme hatası: %s", exc, exc_info=True)
            raise

    @staticmethod
    def prepare_dataset(csv_path: str | Path) -> Tuple[pd.DataFrame, pd.Series]:
        """Zaman serisi CSV verisini okur, gradyanları hesaplar ve etiketler.

        Özellikler (Features):
            - sst: Sıcaklık ortalaması (°C)
            - sst_trend: Sıcaklık günlük artış hızı (°C/gün)
            - chlorophyll_a: Klorofil-a ortalaması (mg/m³)
            - chl_trend: Klorofil günlük artış hızı (mg/m³/gün)

        Etiketleme Mantığı (Biyolojik Eşikler):
            Eğer bir günde:
            - Sıcaklık > 22°C AND Sıcaklık eğilimi (sst_trend) > 0 AND
            - Klorofil-a > 5.0 mg/m³ AND Klorofil eğilimi (chl_trend) > 0 ise
            müsilaj riski YÜKSEK (1) olarak etiketlenir. Aksi halde DÜŞÜK (0).

        Args:
            csv_path: Zaman serisi CSV dosya yolu.

        Returns:
            Tuple[pd.DataFrame, pd.Series]: Özellikler (X) ve Etiketler (y).
        """
        csv_path = Path(csv_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"Veri dosyası bulunamadı: {csv_path}")

        # Veriyi oku ve tarihe göre sırala
        df = pd.read_csv(csv_path)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")

        # Parametreleri ayır
        df_chl = df[df["parameter_type"] == "chlorophyll_a"].copy()
        df_sst = df[df["parameter_type"] == "sst"].copy()

        # Tarih bazında birleştir (merge)
        merged = pd.merge(
            df_sst[["date", "mean_value"]].rename(columns={"mean_value": "sst"}),
            df_chl[["date", "mean_value"]].rename(columns={"mean_value": "chlorophyll_a"}),
            on="date",
            how="inner"
        )

        if len(merged) < 5:
            raise ValueError("Model eğitimi için yeterli ortak tarihli veri noktası bulunamadı.")

        # Zaman farkını gün cinsinden hesapla
        merged["days_diff"] = merged["date"].diff().dt.days.fillna(3.0)  # ilk satır için varsayılan 3 gün

        # Gradyan (Trend) Hesaplama: Değişim miktarı / Gün sayısı
        merged["sst_diff"] = merged["sst"].diff().fillna(0.0)
        merged["sst_trend"] = merged["sst_diff"] / merged["days_diff"]
        
        merged["chl_diff"] = merged["chlorophyll_a"].diff().fillna(0.0)
        merged["chl_trend"] = merged["chl_diff"] / merged["days_diff"]

        # Trendleri gürültüden arındırmak için 3 gözlemlik (yaklaşık 9 gün) hareketli ortalama
        merged["sst_trend"] = merged["sst_trend"].rolling(window=3, min_periods=1).mean()
        merged["chl_trend"] = merged["chl_trend"].rolling(window=3, min_periods=1).mean()

        # Biyolojik Kurallara Göre Etiketleme (Supervised Learning Labels)
        # SST > 22 C, Chl > 5.0 ve her ikisinin eğilimi pozitifse risk=1, aksi halde 0
        merged["risk_label"] = (
            (merged["sst"] > 22.0) & 
            (merged["sst_trend"] > 0) & 
            (merged["chlorophyll_a"] > 5.0) & 
            (merged["chl_trend"] > 0)
        ).astype(int)

        # X ve y ayrımı
        features = ["sst", "sst_trend", "chlorophyll_a", "chl_trend"]
        X = merged[features].copy()
        y = merged["risk_label"].copy()

        logger.info(
            "Veri seti hazırlandı. Satır sayısı: %d, Pozitif Sınıf (Müsilaj): %d (%2.1f%%)",
            len(merged), y.sum(), (y.sum() / len(y)) * 100
        )

        return X, y

    def train(self, csv_path: str | Path) -> dict[str, Any]:
        """Modeli eğitir ve performans raporu metriklerini döndürür.

        Args:
            csv_path: Zaman serisi verilerinin yolu.

        Returns:
            dict: Model performans metrikleri (Doğruluk, hata matrisi vb.).
        """
        X, y = self.prepare_dataset(csv_path)

        # Küçük veri setlerinde (örn. testlerde) train/test split yapma, tüm veriyi kullan
        if len(X) < 10:
            X_train, X_test = X, X
            y_train, y_test = y, y
        else:
            # Sınıf bazlı minimum örnek sayısını kontrol et
            unique_classes = np.unique(y)
            if len(unique_classes) > 1 and all(np.sum(y == c) >= 2 for c in unique_classes):
                stratify_y = y
            else:
                stratify_y = None

            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=stratify_y
            )

        # Sınıflandırıcının oluşturulması
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=5,
            random_state=42,
            class_weight="balanced"
        )
        
        # Eğitim
        self.model.fit(X_train, y_train)

        # Test seti üzerinde tahminler ve değerlendirme
        y_pred = self.model.predict(X_test)
        proba = self.model.predict_proba(X_test)
        y_prob = proba[:, 1] if proba.shape[1] > 1 else np.zeros(len(X_test))

        acc = accuracy_score(y_test, y_pred)
        cm = confusion_matrix(y_test, y_pred).tolist()
        report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)

        # Özellik Önem Dereceleri (Feature Importances)
        importances = self.model.feature_importances_
        feature_importance_dict = dict(zip(self.feature_names, importances.tolist()))

        logger.info("Model eğitimi tamamlandı. Test Doğruluğu: %.4f", acc)

        metrics = {
            "accuracy": acc,
            "confusion_matrix": cm,
            "classification_report": report,
            "feature_importances": feature_importance_dict,
            "train_size": len(X_train),
            "test_size": len(X_test)
        }

        # Modeli kaydet
        self.save()

        return metrics

    def predict_risk(self, sst: float, sst_trend: float, chl: float, chl_trend: float) -> dict[str, Any]:
        """Belirli girdi değerleri için müsilaj risk olasılığı ve seviyesi hesaplar.

        Args:
            sst: Deniz yüzeyi sıcaklığı (°C)
            sst_trend: Sıcaklık artış hızı (°C/gün)
            chl: Klorofil-a konsantrasyonu (mg/m³)
            chl_trend: Klorofil artış hızı (mg/m³/gün)

        Returns:
            dict: Risk oranı (%), Risk seviyesi (Düşük, Orta, Yüksek, Ekstrem) ve girdiler.
        """
        if self.model is None:
            # Model yüklenmemişse yüklemeyi dene
            if not self.load():
                raise ValueError("Eğitilmiş model yüklenemedi. Önce modeli eğitmelisiniz.")

        # Modeli tahmin için hazırla
        X_input = pd.DataFrame(
            [[sst, sst_trend, chl, chl_trend]],
            columns=self.feature_names
        )

        # Olasılık tahmini ([p_0, p_1])
        proba = self.model.predict_proba(X_input)
        prob_1 = proba[0, 1] if proba.shape[1] > 1 else 0.0
        risk_percentage = round(float(prob_1) * 100, 2)

        # Risk Seviyesi Belirleme
        if risk_percentage < 25.0:
            risk_level = "Low"
        elif risk_percentage < 50.0:
            risk_level = "Medium"
        elif risk_percentage < 75.0:
            risk_level = "High"
        else:
            risk_level = "Extreme"

        result = {
            "risk_percentage": risk_percentage,
            "risk_level": risk_level,
            "inputs": {
                "sst": sst,
                "sst_trend": sst_trend,
                "chlorophyll_a": chl,
                "chl_trend": chl_trend
            }
        }

        logger.info(
            "Risk tahmini yapıldı: %s (%2.1f%%) — Girdiler: SST=%s, Chl=%s",
            risk_level, risk_percentage, sst, chl
        )

        return result
