"""
AquaSentinel AI — SentinelDataDownloader Birim Testleri

Mock modu, sorgu oluşturma, parametre doğrulama ve hata durumlarını test eder.
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# Proje kökünü Python yoluna ekle
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data.sentinel_downloader import SentinelDataDownloader


class TestSentinelDataDownloaderInit:
    """SentinelDataDownloader başlatma testleri."""

    def test_init_without_credentials_enables_mock_mode(self):
        """CDSE kimlik bilgileri yoksa mock mod aktif olmalı."""
        with patch.dict(os.environ, {}, clear=True):
            downloader = SentinelDataDownloader()
            assert downloader._mock_mode is True

    def test_init_with_credentials_disables_mock_mode(self):
        """CDSE kimlik bilgileri varsa mock mod kapalı olmalı."""
        with patch.dict(os.environ, {
            "CDSE_USERNAME": "test@example.com",
            "CDSE_PASSWORD": "test_password",
        }):
            downloader = SentinelDataDownloader()
            assert downloader._mock_mode is False
            assert downloader.username == "test@example.com"


class TestBuildQuery:
    """OData sorgu oluşturma testleri."""

    def setup_method(self):
        """Her test öncesi mock modda downloader oluştur."""
        with patch.dict(os.environ, {
            "CDSE_USERNAME": "test@example.com",
            "CDSE_PASSWORD": "test_password",
        }):
            self.downloader = SentinelDataDownloader()

    def test_build_query_chlorophyll(self):
        """Klorofil-a sorgusu doğru ürün tipini içermeli."""
        query = self.downloader._build_query("2024-06-01", "2024-06-15", "chlorophyll")
        assert "OL_2_WFR___" in query
        assert "SENTINEL-3" in query
        assert "2024-06-01" in query
        assert "2024-06-15" in query

    def test_build_query_sst(self):
        """SST sorgusu doğru ürün tipini içermeli."""
        query = self.downloader._build_query("2024-06-01", "2024-06-15", "sst")
        assert "SL_2_LST___" in query

    def test_build_query_contains_marmara_bbox(self):
        """Sorgu Marmara Denizi bounding box'ını içermeli."""
        query = self.downloader._build_query("2024-06-01", "2024-06-15", "chlorophyll")
        assert "26.5" in query
        assert "40.0" in query
        assert "30.0" in query
        assert "41.5" in query

    def test_build_query_invalid_product_type_raises(self):
        """Geçersiz ürün tipi ValueError fırlatmalı."""
        with pytest.raises(ValueError, match="Geçersiz ürün tipi"):
            self.downloader._build_query("2024-06-01", "2024-06-15", "invalid_type")

    def test_build_query_invalid_date_format_raises(self):
        """Geçersiz tarih formatı ValueError fırlatmalı."""
        with pytest.raises(ValueError, match="YYYY-MM-DD"):
            self.downloader._build_query("01-06-2024", "15/06/2024", "chlorophyll")


class TestMockDownload:
    """Mock indirme testleri."""

    def setup_method(self):
        """Her test öncesi mock modda downloader oluştur."""
        with patch.dict(os.environ, {}, clear=True):
            self.downloader = SentinelDataDownloader()

    def test_mock_download_creates_file(self, tmp_path):
        """Mock indirme bir .npz dosyası oluşturmalı."""
        result_path = self.downloader._mock_download(tmp_path)
        assert result_path.exists()
        assert result_path.suffix == ".npz"

    def test_mock_download_contains_expected_arrays(self, tmp_path):
        """Mock dosya beklenen veri dizilerini içermeli."""
        result_path = self.downloader._mock_download(tmp_path)
        data = np.load(str(result_path))
        expected_keys = {"chlorophyll", "sst", "latitudes", "longitudes",
                         "quality_flags", "land_mask", "cloud_mask"}
        assert expected_keys.issubset(set(data.files))
        data.close()

    def test_mock_download_chlorophyll_range(self, tmp_path):
        """Mock Klorofil-a değerleri fiziksel sınırlarda olmalı."""
        result_path = self.downloader._mock_download(tmp_path)
        data = np.load(str(result_path))
        chl = data["chlorophyll"]
        valid_chl = chl[~np.isnan(chl)]
        assert np.all(valid_chl >= 0)
        assert np.all(valid_chl <= 50)
        data.close()

    def test_mock_download_sst_range(self, tmp_path):
        """Mock SST değerleri fiziksel sınırlarda olmalı."""
        result_path = self.downloader._mock_download(tmp_path)
        data = np.load(str(result_path))
        sst = data["sst"]
        valid_sst = sst[~np.isnan(sst)]
        assert np.all(valid_sst >= 10)
        assert np.all(valid_sst <= 35)
        data.close()


class TestDownloadMarmaraData:
    """download_marmara_data entegrasyon testleri."""

    def test_download_in_mock_mode_returns_path(self, tmp_path):
        """Mock modda indirme bir dosya yolu döndürmeli."""
        with patch.dict(os.environ, {}, clear=True):
            downloader = SentinelDataDownloader()
            result = downloader.download_marmara_data(
                "2024-06-01", "2024-06-15", str(tmp_path)
            )
            assert result is not None
            assert result.exists()

    def test_download_creates_output_directory(self, tmp_path):
        """İndirme hedef dizini otomatik oluşturmalı."""
        output_dir = tmp_path / "nested" / "output"
        with patch.dict(os.environ, {}, clear=True):
            downloader = SentinelDataDownloader()
            downloader.download_marmara_data(
                "2024-06-01", "2024-06-15", str(output_dir)
            )
            assert output_dir.exists()


class TestGetAvailableProducts:
    """Ürün listeleme testleri."""

    def test_mock_mode_returns_mock_products(self):
        """Mock modda ürün listesi mock olarak döndürülmeli."""
        with patch.dict(os.environ, {}, clear=True):
            downloader = SentinelDataDownloader()
            products = downloader.get_available_products("2024-06-01", "2024-06-15")
            assert len(products) == 1
            assert products[0]["mock"] is True
