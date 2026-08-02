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
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.calibration import CalibratedClassifierCV
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
        self.model: Optional[Any] = None
        self.feature_names = [
            "sst",
            "sst_trend",
            "chlorophyll_a",
            "chl_trend",
            "sst_chl_product",
            "sst_ma3",
            "chl_ma3",
        ]

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
        """Zaman serisi CSV verisini okur, türetilmiş özellikleri hesaplar ve etiketler.

        Özellikler (Features):
            - sst: Sıcaklık ortalaması (°C)
            - sst_trend: Sıcaklık günlük artış hızı (°C/gün)
            - chlorophyll_a: Klorofil-a ortalaması (mg/m³)
            - chl_trend: Klorofil günlük artış hızı (mg/m³/gün)
            - sst_chl_product: Sıcaklık x Klorofil sinerji etkileşimi
            - sst_ma3: 3 gözlemlik sıcaklık hareketli ortalaması
            - chl_ma3: 3 gözlemlik klorofil hareketli ortalaması

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
        merged["days_diff"] = merged["date"].diff().dt.days.fillna(3.0)

        # Gradyan (Trend) Hesaplama: Değişim miktarı / Gün sayısı
        merged["sst_diff"] = merged["sst"].diff().fillna(0.0)
        merged["sst_trend"] = merged["sst_diff"] / merged["days_diff"]

        merged["chl_diff"] = merged["chlorophyll_a"].diff().fillna(0.0)
        merged["chl_trend"] = merged["chl_diff"] / merged["days_diff"]

        # Gelişmiş Özellik Türetimi (Feature Engineering)
        merged["sst_trend"] = merged["sst_trend"].rolling(window=3, min_periods=1).mean()
        merged["chl_trend"] = merged["chl_trend"].rolling(window=3, min_periods=1).mean()

        merged["sst_chl_product"] = merged["sst"] * merged["chlorophyll_a"]
        merged["sst_ma3"] = merged["sst"].rolling(window=3, min_periods=1).mean()
        merged["chl_ma3"] = merged["chlorophyll_a"].rolling(window=3, min_periods=1).mean()

        # Etiketleme Mantığı (Gerçek Uydu Ölçüm Eşikleri)
        merged["risk_label"] = (
            (merged["sst"] > 17.0)
            & (merged["sst_trend"] > 0)
            & (merged["chlorophyll_a"] > 0.50)
            & (merged["chl_trend"] > 0)
        ).astype(int)

        features = [
            "sst",
            "sst_trend",
            "chlorophyll_a",
            "chl_trend",
            "sst_chl_product",
            "sst_ma3",
            "chl_ma3",
        ]
        X = merged[features].copy()
        y = merged["risk_label"].copy()

        logger.info(
            "Veri seti hazırlandı. Satır sayısı: %d, Pozitif Sınıf (Müsilaj): %d (%2.1f%%)",
            len(merged), y.sum(), (y.sum() / len(y)) * 100
        )

        return X, y

    def train(self, csv_path: str | Path) -> dict[str, Any]:
        """Modeli eğitir, GridSearchCV ve CalibratedClassifierCV uygular.

        Args:
            csv_path: Zaman serisi verilerinin yolu.

        Returns:
            dict: Model performans metrikleri.
        """
        X, y = self.prepare_dataset(csv_path)

        if len(X) < 10:
            X_train, X_test = X, X
            y_train, y_test = y, y
        else:
            unique_classes = np.unique(y)
            if len(unique_classes) > 1 and all(np.sum(y == c) >= 2 for c in unique_classes):
                stratify_y = y
            else:
                stratify_y = None

            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=stratify_y
            )

        # 1. Base Classifier
        base_rf = RandomForestClassifier(random_state=42, class_weight="balanced")

        # 2. Hyperparameter Grid Search (GridSearchCV)
        param_grid = {
            "n_estimators": [50, 100, 150],
            "max_depth": [3, 5, 7, None],
            "min_samples_split": [2, 4],
        }

        min_samples_per_class = min(np.bincount(y_train)) if len(np.unique(y_train)) > 1 else 1
        cv_folds = max(2, min(3, min_samples_per_class))

        grid_search = GridSearchCV(
            base_rf, param_grid, cv=cv_folds, scoring="accuracy", n_jobs=-1
        )
        grid_search.fit(X_train, y_train)
        best_estimator = grid_search.best_estimator_

        # 3. Probability Calibration (CalibratedClassifierCV)
        try:
            calibrated_clf = CalibratedClassifierCV(estimator=best_estimator, cv=cv_folds)
            calibrated_clf.fit(X_train, y_train)
            self.model = calibrated_clf
        except Exception:
            self.model = best_estimator

        # Test kümesi tahmini
        y_pred = self.model.predict(X_test)
        proba = self.model.predict_proba(X_test)

        acc = accuracy_score(y_test, y_pred)
        cm = confusion_matrix(y_test, y_pred).tolist()
        report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)

        # Feature Importances (ana kestirimciden)
        if hasattr(best_estimator, "feature_importances_"):
            importances = best_estimator.feature_importances_
            feature_importance_dict = dict(zip(self.feature_names, importances.tolist()))
        else:
            feature_importance_dict = {f: 1.0 / len(self.feature_names) for f in self.feature_names}

        logger.info("Model eğitimi (GridSearch + Kalibrasyon) tamamlandı. Test Doğruluğu: %.4f", acc)

        metrics = {
            "accuracy": acc,
            "confusion_matrix": cm,
            "classification_report": report,
            "feature_importances": feature_importance_dict,
            "best_params": grid_search.best_params_,
            "train_size": len(X_train),
            "test_size": len(X_test)
        }

        self.save()
        return metrics

    def predict_risk(self, sst: float, sst_trend: float, chl: float, chl_trend: float) -> dict[str, Any]:
        """Girdi değerleri için müsilaj risk olasılığı ve seviyesi hesaplar.

        Args:
            sst: Deniz yüzeyi sıcaklığı (°C)
            sst_trend: Sıcaklık artış hızı (°C/gün)
            chl: Klorofil-a konsantrasyonu (mg/m³)
            chl_trend: Klorofil artış hızı (mg/m³/gün)

        Returns:
            dict: Risk oranı (%), Risk seviyesi ve girdiler.
        """
        if self.model is None:
            if not self.load():
                raise ValueError("Eğitilmiş model yüklenemedi. Önce modeli eğitmelisiniz.")

        sst_chl_product = sst * chl
        sst_ma3 = sst
        chl_ma3 = chl

        X_input = pd.DataFrame(
            [[sst, sst_trend, chl, chl_trend, sst_chl_product, sst_ma3, chl_ma3]],
            columns=self.feature_names
        )

        proba = self.model.predict_proba(X_input)
        prob_1 = proba[0, 1] if proba.shape[1] > 1 else 0.0
        risk_percentage = round(float(prob_1) * 100, 2)

        if risk_percentage < 25.0:
            risk_level = "Low"
        elif risk_percentage < 50.0:
            risk_level = "Medium"
        elif risk_percentage < 75.0:
            risk_level = "High"
        else:
            risk_level = "Extreme"

        return {
            "risk_percentage": risk_percentage,
            "risk_level": risk_level,
            "inputs": {
                "sst": sst,
                "sst_trend": sst_trend,
                "chlorophyll_a": chl,
                "chl_trend": chl_trend,
                "sst_chl_product": sst_chl_product,
            }
        }


        logger.info(
            "Risk tahmini yapıldı: %s (%2.1f%%) — Girdiler: SST=%s, Chl=%s",
            risk_level, risk_percentage, sst, chl
        )

        return result
