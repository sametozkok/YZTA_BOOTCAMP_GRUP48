"""
AquaSentinel AI — MucilageRiskModel Birim Testleri
"""

import os
from pathlib import Path
import pytest
import pandas as pd
import numpy as np

from src.models.risk_model import MucilageRiskModel
from src.data.preprocessor import MarmaraDataPreprocessor


@pytest.fixture
def mock_csv_path(tmp_path):
    """Testler için küçük ölçekli sahte bir zaman serisi CSV dosyası üretir."""
    processed_dir = tmp_path / "processed"
    processor = MarmaraDataPreprocessor(processed_dir=processed_dir)
    
    # Yeterli pozitif/negatif sınıf örneği için geniş tarih aralığı
    csv_file = processor.generate_mock_data("2024-05-01", "2024-08-31", interval_days=3)
    return csv_file


class TestMucilageRiskModel:
    """Müsilaj Risk Modelinin tüm metotlarını test eder."""

    def test_prepare_dataset_structure(self, mock_csv_path):
        """prepare_dataset X ve y olarak doğru şekil ve sütunları dönmeli."""
        X, y = MucilageRiskModel.prepare_dataset(mock_csv_path)
        
        assert isinstance(X, pd.DataFrame)
        assert isinstance(y, pd.Series)
        assert list(X.columns) == ["sst", "sst_trend", "chlorophyll_a", "chl_trend"]
        assert len(X) == len(y)
        assert set(y.unique()).issubset({0, 1})

    def test_train_model_saves_and_returns_metrics(self, mock_csv_path, tmp_path):
        """Model eğitimi başarılı bir şekilde kaydedilmeli ve metrikleri dönmeli."""
        model_file = tmp_path / "test_model.joblib"
        model_wrapper = MucilageRiskModel(model_path=model_file)
        
        metrics = model_wrapper.train(mock_csv_path)
        
        assert "accuracy" in metrics
        assert "confusion_matrix" in metrics
        assert "feature_importances" in metrics
        assert model_file.exists()
        
        # Özellik önem dereceleri toplamı 1.0 olmalı
        importances = list(metrics["feature_importances"].values())
        assert pytest.approx(sum(importances), abs=0.01) == 1.0

    def test_predict_risk_returns_correct_level_and_keys(self, mock_csv_path, tmp_path):
        """Model risk yüzdesi ve seviyesini doğru formatta dönmeli."""
        model_file = tmp_path / "test_model.joblib"
        model_wrapper = MucilageRiskModel(model_path=model_file)
        model_wrapper.train(mock_csv_path)
        
        # Test tahmini yap
        # 1. Düşük Risk Senaryosu
        low_risk_result = model_wrapper.predict_risk(
            sst=15.0, sst_trend=-0.1, chl=1.2, chl_trend=-0.05
        )
        assert "risk_percentage" in low_risk_result
        assert "risk_level" in low_risk_result
        assert low_risk_result["risk_level"] in ["Low", "Medium", "High", "Extreme"]
        
        # 2. Yüksek/Ekstrem Risk Senaryosu
        high_risk_result = model_wrapper.predict_risk(
            sst=24.5, sst_trend=0.3, chl=8.5, chl_trend=0.4
        )
        assert high_risk_result["risk_percentage"] > low_risk_result["risk_percentage"]

    def test_load_non_existent_model_returns_false(self, tmp_path):
        """Olmayan model dosyası yüklenmeye çalışıldığında False dönmeli."""
        non_existent_file = tmp_path / "ghost.joblib"
        model_wrapper = MucilageRiskModel(model_path=non_existent_file)
        assert not model_wrapper.load()
