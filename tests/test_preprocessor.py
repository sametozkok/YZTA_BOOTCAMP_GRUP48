"""
AquaSentinel AI — MarmaraDataPreprocessor Birim Testleri

Mock veri üretimi, kalite maskeleme, istatistik hesaplama ve
CSV çıktı formatı testleri.
"""

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# Proje kökünü Python yoluna ekle
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data.preprocessor import MarmaraDataPreprocessor


class TestMarmaraDataPreprocessorInit:
    """Preprocessor başlatma testleri."""

    def test_init_creates_output_directory(self, tmp_path):
        """Başlatma sırasında çıktı dizini oluşturulmalı."""
        output_dir = tmp_path / "processed"
        processor = MarmaraDataPreprocessor(processed_dir=output_dir)
        assert output_dir.exists()

    def test_init_sets_timeseries_path(self, tmp_path):
        """Zaman serisi dosya yolu doğru ayarlanmalı."""
        processor = MarmaraDataPreprocessor(processed_dir=tmp_path)
        assert processor._timeseries_path.name == "marmara_time_series.csv"


class TestApplyQualityMask:
    """Kalite maskeleme testleri."""

    def setup_method(self, tmp_path=None):
        """Her test öncesi preprocessor oluştur."""
        self.processor = MarmaraDataPreprocessor(processed_dir="data/processed")

    def test_mask_with_flags_removes_land_pixels(self):
        """Kara flag'li pikseller NaN olmalı."""
        data = np.array([[1.0, 2.0], [3.0, 4.0]])
        flags = np.array([[1, 0], [0, 0]], dtype=np.uint8)  # Sol üst = kara

        result = self.processor._apply_quality_mask(data, flags)
        assert np.isnan(result[0, 0])
        assert not np.isnan(result[0, 1])

    def test_mask_with_flags_removes_cloud_pixels(self):
        """Bulut flag'li pikseller NaN olmalı."""
        data = np.array([[1.0, 2.0], [3.0, 4.0]])
        flags = np.array([[0, 2], [0, 0]], dtype=np.uint8)  # Sağ üst = bulut

        result = self.processor._apply_quality_mask(data, flags)
        assert np.isnan(result[0, 1])
        assert not np.isnan(result[1, 0])

    def test_mask_removes_out_of_range_values(self):
        """Fiziksel sınır dışı değerler NaN olmalı."""
        data = np.array([[1.0, -10.0], [150.0, 5.0]])

        result = self.processor._apply_quality_mask(data, flags=None)
        assert np.isnan(result[0, 1])   # -10 < -2 → NaN
        assert np.isnan(result[1, 0])   # 150 > 100 → NaN
        assert not np.isnan(result[0, 0])
        assert not np.isnan(result[1, 1])

    def test_mask_without_flags_keeps_valid_data(self):
        """Flag yoksa sadece fiziksel sınır dışı temizlenmeli."""
        data = np.array([[1.0, 2.0], [3.0, 4.0]])

        result = self.processor._apply_quality_mask(data, flags=None)
        assert np.sum(np.isnan(result)) == 0


class TestComputeStatistics:
    """İstatistik hesaplama testleri."""

    def setup_method(self):
        """Her test öncesi preprocessor oluştur."""
        self.processor = MarmaraDataPreprocessor(processed_dir="data/processed")

    def test_compute_statistics_returns_correct_mean(self):
        """Ortalama değer doğru hesaplanmalı."""
        data = np.array([1.0, 2.0, 3.0, np.nan, 4.0])
        result = self.processor._compute_statistics(data, "2024-06-01", "chlorophyll_a")

        assert result is not None
        assert result["mean_value"] == pytest.approx(2.5, abs=0.01)

    def test_compute_statistics_returns_correct_keys(self):
        """Sonuç sözlüğü beklenen anahtarları içermeli."""
        data = np.array([1.0, 2.0, 3.0])
        result = self.processor._compute_statistics(data, "2024-06-01", "sst")

        expected_keys = {
            "date", "parameter_type", "mean_value", "std_value",
            "min_value", "max_value", "valid_pixel_count",
            "total_pixel_count", "quality_ratio",
        }
        assert set(result.keys()) == expected_keys

    def test_compute_statistics_all_nan_returns_none(self):
        """Tüm pikseller NaN ise None dönmeli."""
        data = np.array([np.nan, np.nan, np.nan])
        result = self.processor._compute_statistics(data, "2024-06-01", "sst")
        assert result is None

    def test_compute_statistics_quality_ratio(self):
        """Kalite oranı doğru hesaplanmalı."""
        data = np.array([1.0, np.nan, 3.0, np.nan])
        result = self.processor._compute_statistics(data, "2024-06-01", "chlorophyll_a")

        assert result["quality_ratio"] == pytest.approx(0.5, abs=0.01)
        assert result["valid_pixel_count"] == 2
        assert result["total_pixel_count"] == 4


class TestAppendToTimeseries:
    """CSV zaman serisi yazma testleri."""

    def test_append_creates_csv_file(self, tmp_path):
        """İlk ekleme CSV dosyası oluşturmalı."""
        processor = MarmaraDataPreprocessor(processed_dir=tmp_path)
        processor._append_to_timeseries(
            date="2024-06-01",
            parameter_type="chlorophyll_a",
            mean_value=3.5,
            std_value=0.8,
            min_value=1.2,
            max_value=7.1,
            valid_pixel_count=4000,
            total_pixel_count=5850,
            quality_ratio=0.68,
        )

        csv_path = tmp_path / "marmara_time_series.csv"
        assert csv_path.exists()

        df = pd.read_csv(csv_path)
        assert len(df) == 1
        assert df.iloc[0]["date"] == "2024-06-01"
        assert df.iloc[0]["parameter_type"] == "chlorophyll_a"

    def test_append_updates_existing_record(self, tmp_path):
        """Aynı tarih/parametre için mevcut kayıt güncellenmeli."""
        processor = MarmaraDataPreprocessor(processed_dir=tmp_path)

        # İlk kayıt
        processor._append_to_timeseries(
            date="2024-06-01", parameter_type="sst",
            mean_value=22.0, std_value=1.0,
            min_value=20.0, max_value=24.0,
            valid_pixel_count=4500, total_pixel_count=5850,
            quality_ratio=0.77,
        )

        # Aynı tarih/tip ile güncelle
        processor._append_to_timeseries(
            date="2024-06-01", parameter_type="sst",
            mean_value=23.5, std_value=1.2,
            min_value=21.0, max_value=25.0,
            valid_pixel_count=4600, total_pixel_count=5850,
            quality_ratio=0.79,
        )

        df = pd.read_csv(tmp_path / "marmara_time_series.csv")
        assert len(df) == 1  # Ek satır olmamalı
        assert df.iloc[0]["mean_value"] == pytest.approx(23.5)

    def test_append_multiple_dates(self, tmp_path):
        """Farklı tarihler ayrı satırlar olarak eklenmeli."""
        processor = MarmaraDataPreprocessor(processed_dir=tmp_path)

        for day in range(1, 4):
            processor._append_to_timeseries(
                date=f"2024-06-{day:02d}", parameter_type="chlorophyll_a",
                mean_value=2.0 + day, std_value=0.5,
                min_value=1.0, max_value=5.0,
                valid_pixel_count=4000, total_pixel_count=5850,
                quality_ratio=0.68,
            )

        df = pd.read_csv(tmp_path / "marmara_time_series.csv")
        assert len(df) == 3


class TestGenerateMockData:
    """Mock veri üretimi testleri."""

    def test_generate_mock_data_creates_csv(self, tmp_path):
        """Mock veri üretimi CSV dosyası oluşturmalı."""
        processor = MarmaraDataPreprocessor(processed_dir=tmp_path)
        result_path = processor.generate_mock_data("2024-06-01", "2024-06-30")

        assert result_path.exists()
        assert result_path.suffix == ".csv"

    def test_generate_mock_data_contains_both_parameters(self, tmp_path):
        """Mock veri hem Klorofil-a hem SST içermeli."""
        processor = MarmaraDataPreprocessor(processed_dir=tmp_path)
        processor.generate_mock_data("2024-06-01", "2024-06-10")

        df = pd.read_csv(tmp_path / "marmara_time_series.csv")
        param_types = df["parameter_type"].unique()
        assert "chlorophyll_a" in param_types
        assert "sst" in param_types

    def test_generate_mock_data_correct_columns(self, tmp_path):
        """Mock CSV doğru sütun başlıklarına sahip olmalı."""
        processor = MarmaraDataPreprocessor(processed_dir=tmp_path)
        processor.generate_mock_data("2024-06-01", "2024-06-05")

        df = pd.read_csv(tmp_path / "marmara_time_series.csv")
        expected_cols = set(MarmaraDataPreprocessor.CSV_COLUMNS)
        assert set(df.columns) == expected_cols

    def test_generate_mock_data_chlorophyll_realistic_range(self, tmp_path):
        """Mock Klorofil-a değerleri gerçekçi aralıkta olmalı (0.1-25 mg/m³)."""
        processor = MarmaraDataPreprocessor(processed_dir=tmp_path)
        processor.generate_mock_data("2024-01-01", "2024-12-31")

        df = pd.read_csv(tmp_path / "marmara_time_series.csv")
        chl_data = df[df["parameter_type"] == "chlorophyll_a"]
        assert chl_data["mean_value"].min() >= 0.0
        assert chl_data["mean_value"].max() <= 30.0

    def test_generate_mock_data_sst_realistic_range(self, tmp_path):
        """Mock SST değerleri gerçekçi aralıkta olmalı (5-32 °C)."""
        processor = MarmaraDataPreprocessor(processed_dir=tmp_path)
        processor.generate_mock_data("2024-01-01", "2024-12-31")

        df = pd.read_csv(tmp_path / "marmara_time_series.csv")
        sst_data = df[df["parameter_type"] == "sst"]
        assert sst_data["mean_value"].min() >= 5.0
        assert sst_data["mean_value"].max() <= 32.0

    def test_generate_mock_data_interval(self, tmp_path):
        """Veri noktaları doğru aralıkla üretilmeli."""
        processor = MarmaraDataPreprocessor(processed_dir=tmp_path)
        processor.generate_mock_data("2024-06-01", "2024-06-10", interval_days=3)

        df = pd.read_csv(tmp_path / "marmara_time_series.csv")
        # 1, 4, 7, 10 Haziran = 4 tarih x 2 parametre = 8 kayıt
        assert len(df) == 8


class TestExtractDateFromFilename:
    """Dosya adından tarih çıkarma testleri."""

    def test_sentinel_filename(self):
        """Sentinel-3 dosya adı formatından tarih çıkarmalı."""
        result = MarmaraDataPreprocessor._extract_date_from_filename(
            "S3A_OL_2_WFR___20240601T093000_..."
        )
        assert result == "2024-06-01"

    def test_mock_filename(self):
        """Mock dosya adından tarih çıkarmalı."""
        result = MarmaraDataPreprocessor._extract_date_from_filename(
            "mock_sentinel3_marmara_20240601.npz"
        )
        assert result == "2024-06-01"

    def test_no_date_returns_today(self):
        """Tarih bulunamazsa bugünün tarihini döndürmeli."""
        result = MarmaraDataPreprocessor._extract_date_from_filename("no_date_here.nc")
        # Bugünün tarihi format kontrolü
        assert len(result) == 10
        assert result[4] == "-"


class TestDetectParameterType:
    """Parametre tipi algılama testleri."""

    def test_detect_chlorophyll(self):
        """Klorofil dosya adı doğru algılanmalı."""
        assert MarmaraDataPreprocessor._detect_parameter_type("CHL_data.tif") == "chlorophyll_a"
        assert MarmaraDataPreprocessor._detect_parameter_type("OL_2_WFR_file.nc") == "chlorophyll_a"

    def test_detect_sst(self):
        """SST dosya adı doğru algılanmalı."""
        assert MarmaraDataPreprocessor._detect_parameter_type("SST_marmara.tif") == "sst"
        assert MarmaraDataPreprocessor._detect_parameter_type("SL_2_LST_file.nc") == "sst"

    def test_detect_unknown(self):
        """Bilinmeyen dosya adı 'unknown' döndürmeli."""
        assert MarmaraDataPreprocessor._detect_parameter_type("random_file.nc") == "unknown"
