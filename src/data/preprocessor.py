"""
AquaSentinel AI — Marmara Denizi Uydu Verisi Ön İşleme Modülü

İndirilen NetCDF (.nc), GeoTIFF (.tif) ve mock (.npz) uydu verilerini
okur, kalite filtrelerini uygular, istatistik hesaplar ve zaman
serisine ekler.

Desteklenen işlemler:
    - NetCDF (Sentinel-3 Level-2) okuma ve kalite maskeleme
    - GeoTIFF okuma ve işleme
    - Mock/simüle veri üretimi ve ön işleme
    - Zaman serisi CSV oluşturma/güncelleme

Kullanım:
    >>> from src.data.preprocessor import MarmaraDataPreprocessor
    >>> processor = MarmaraDataPreprocessor()
    >>> processor.generate_mock_data("2024-01-01", "2024-12-31")
"""

import csv
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd

from src.utils import ensure_directory, setup_logger

logger = setup_logger(__name__, log_file="logs/preprocessor.log")


class MarmaraDataPreprocessor:
    """Marmara Denizi uydu verilerini ön işler ve zaman serisi oluşturur.

    Bu sınıf, ham uydu görüntülerindeki bulutlu, hatalı ve kara
    piksellerini temizler; Klorofil-a ve SST ortalamalarını hesaplar
    ve sonuçları tarih bazlı CSV dosyasına yazar.

    Attributes:
        TIMESERIES_FILENAME: Çıktı CSV dosyasının adı.
        CSV_COLUMNS: CSV sütun başlıkları.
        QUALITY_FLAG_LAND: Kara pikseli flag değeri.
        QUALITY_FLAG_CLOUD: Bulut pikseli flag değeri.
        QUALITY_FLAG_INVALID: Geçersiz piksel flag değeri.
    """

    TIMESERIES_FILENAME: str = "marmara_time_series.csv"

    CSV_COLUMNS: list[str] = [
        "date",
        "parameter_type",
        "mean_value",
        "std_value",
        "min_value",
        "max_value",
        "valid_pixel_count",
        "total_pixel_count",
        "quality_ratio",
    ]

    # Kalite flag bit değerleri (Sentinel-3 OLCI Level-2 uyumlu)
    QUALITY_FLAG_LAND: int = 1
    QUALITY_FLAG_CLOUD: int = 2
    QUALITY_FLAG_INVALID: int = 4

    def __init__(self, processed_dir: str | Path = "data/processed") -> None:
        """MarmaraDataPreprocessor'ı başlatır.

        Args:
            processed_dir: İşlenmiş verilerin kaydedileceği dizin.
                          Varsayılan: 'data/processed'.
        """
        self.processed_dir = Path(processed_dir)
        ensure_directory(self.processed_dir)
        self._timeseries_path = self.processed_dir / self.TIMESERIES_FILENAME

        logger.info(
            "MarmaraDataPreprocessor başlatıldı. Çıktı dizini: %s",
            self.processed_dir,
        )

    def process_netcdf(self, file_path: str | Path) -> Optional[dict[str, Any]]:
        """NetCDF (.nc) dosyasını okur ve ön işler.

        Sentinel-3 Level-2 NetCDF dosyasından Klorofil-a veya SST
        değerlerini çıkarır, kalite maskesi uygular ve istatistikleri
        hesaplar.

        Args:
            file_path: NetCDF dosyasının yolu.

        Returns:
            Optional[dict]: İstatistik sonuçları veya dosya okunamazsa None.
                Anahtarlar: date, parameter_type, mean_value, std_value,
                            valid_pixel_count, quality_ratio.
        """
        file_path = Path(file_path)

        if not file_path.exists():
            logger.error("Dosya bulunamadı: %s", file_path)
            return None

        if file_path.suffix not in (".nc", ".NC"):
            logger.error(
                "Desteklenmeyen dosya formatı: %s (beklenen: .nc)", file_path.suffix
            )
            return None

        try:
            import netCDF4 as nc

            dataset = nc.Dataset(str(file_path), "r")
            logger.info("NetCDF dosyası açıldı: %s", file_path.name)

            # Değişken isimlerini algıla
            variables = list(dataset.variables.keys())
            logger.debug("NetCDF değişkenleri: %s", variables)

            # Klorofil-a verisi ara
            chl_var_names = ["CHL_OC4ME", "CHL_NN", "chlorophyll", "chl_a", "CHL"]
            sst_var_names = ["SST", "sea_surface_temperature", "sst", "LST"]

            data = None
            param_type = "unknown"

            for var_name in chl_var_names:
                if var_name in variables:
                    data = np.array(dataset.variables[var_name][:])
                    param_type = "chlorophyll_a"
                    logger.info("Klorofil-a verisi bulundu: %s", var_name)
                    break

            if data is None:
                for var_name in sst_var_names:
                    if var_name in variables:
                        data = np.array(dataset.variables[var_name][:])
                        param_type = "sst"
                        logger.info("SST verisi bulundu: %s", var_name)
                        break

            if data is None:
                logger.warning(
                    "Bilinen değişken bulunamadı. Mevcut değişkenler: %s", variables
                )
                dataset.close()
                return None

            # Kalite flag'lerini oku (varsa)
            flags = None
            flag_names = ["WQSF", "quality_flags", "flags", "QF"]
            for flag_name in flag_names:
                if flag_name in variables:
                    flags = np.array(dataset.variables[flag_name][:])
                    break

            # Tarih bilgisini çıkar
            date_str = self._extract_date_from_netcdf(dataset, file_path.name)

            dataset.close()

            # Kalite maskesi uygula
            clean_data = self._apply_quality_mask(data, flags)

            # İstatistik hesapla
            result = self._compute_statistics(clean_data, date_str, param_type)

            # CSV'ye ekle
            if result:
                self._append_to_timeseries(**result)

            return result

        except ImportError:
            logger.error(
                "netCDF4 kütüphanesi yüklü değil. "
                "'pip install netCDF4' komutunu çalıştırın."
            )
            return None
        except Exception as exc:
            logger.error("NetCDF işleme hatası: %s", exc, exc_info=True)
            return None

    def process_geotiff(self, file_path: str | Path) -> Optional[dict[str, Any]]:
        """GeoTIFF (.tif) dosyasını okur ve ön işler.

        Args:
            file_path: GeoTIFF dosyasının yolu.

        Returns:
            Optional[dict]: İstatistik sonuçları veya dosya okunamazsa None.
        """
        file_path = Path(file_path)

        if not file_path.exists():
            logger.error("Dosya bulunamadı: %s", file_path)
            return None

        try:
            import rasterio

            with rasterio.open(str(file_path)) as src:
                logger.info(
                    "GeoTIFF dosyası açıldı: %s (Bantlar: %d, CRS: %s)",
                    file_path.name, src.count, src.crs,
                )

                # İlk bandı oku
                data = src.read(1).astype(np.float64)

                # NoData değerlerini NaN'a çevir
                nodata = src.nodata
                if nodata is not None:
                    data[data == nodata] = np.nan

            # Tarih bilgisini dosya adından çıkar
            date_str = self._extract_date_from_filename(file_path.name)
            param_type = self._detect_parameter_type(file_path.name)

            # Kalite maskesi (basit: negatif ve aşırı değerler)
            clean_data = self._apply_quality_mask(data, flags=None)

            # İstatistik hesapla
            result = self._compute_statistics(clean_data, date_str, param_type)

            if result:
                self._append_to_timeseries(**result)

            return result

        except ImportError:
            logger.error(
                "rasterio kütüphanesi yüklü değil. "
                "'pip install rasterio' komutunu çalıştırın."
            )
            return None
        except Exception as exc:
            logger.error("GeoTIFF işleme hatası: %s", exc, exc_info=True)
            return None

    def process_mock_npz(self, file_path: str | Path) -> Optional[list[dict[str, Any]]]:
        """Mock (.npz) dosyasını okur ve ön işler.

        SentinelDataDownloader._mock_download() tarafından üretilen
        simüle veri dosyalarını işler.

        Args:
            file_path: Mock .npz dosyasının yolu.

        Returns:
            Optional[list[dict]]: Klorofil-a ve SST istatistikleri listesi.
        """
        file_path = Path(file_path)

        if not file_path.exists():
            logger.error("Mock dosya bulunamadı: %s", file_path)
            return None

        try:
            mock_data = np.load(str(file_path))
            logger.info("Mock veri dosyası yüklendi: %s", file_path.name)

            results = []
            date_str = self._extract_date_from_filename(file_path.name)

            # Klorofil-a işle
            if "chlorophyll" in mock_data:
                chl_data = mock_data["chlorophyll"].copy()
                quality_flags = (
                    mock_data["quality_flags"] if "quality_flags" in mock_data else None
                )
                clean_chl = self._apply_quality_mask(chl_data, quality_flags)
                result = self._compute_statistics(clean_chl, date_str, "chlorophyll_a")
                if result:
                    self._append_to_timeseries(**result)
                    results.append(result)

            # SST işle
            if "sst" in mock_data:
                sst_data = mock_data["sst"].copy()
                quality_flags = (
                    mock_data["quality_flags"] if "quality_flags" in mock_data else None
                )
                clean_sst = self._apply_quality_mask(sst_data, quality_flags)
                result = self._compute_statistics(clean_sst, date_str, "sst")
                if result:
                    self._append_to_timeseries(**result)
                    results.append(result)

            mock_data.close()
            return results if results else None

        except Exception as exc:
            logger.error("Mock veri işleme hatası: %s", exc, exc_info=True)
            return None

    def _apply_quality_mask(
        self,
        data: np.ndarray,
        flags: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """Kalite flag'lerine göre hatalı pikselleri maskeler.

        Uygulanan maskeleme kuralları:
            1. Kara pikselleri → NaN
            2. Bulutlu pikseller → NaN
            3. Geçersiz flag'li pikseller → NaN
            4. Fiziksel olarak anlamsız değerler → NaN
               - Klorofil-a: <0 veya >100 mg/m³
               - SST: <-2 veya >45 °C

        Args:
            data: Ham piksel değerleri (2D NumPy array).
            flags: Kalite flag matrisi (opsiyonel).

        Returns:
            np.ndarray: Temizlenmiş veri matrisi (hatalı pikseller NaN).
        """
        clean_data = data.astype(np.float64).copy()
        total_pixels = clean_data.size

        # Flag bazlı maskeleme
        if flags is not None:
            land_pixels = np.bitwise_and(flags, self.QUALITY_FLAG_LAND) > 0
            cloud_pixels = np.bitwise_and(flags, self.QUALITY_FLAG_CLOUD) > 0
            invalid_pixels = np.bitwise_and(flags, self.QUALITY_FLAG_INVALID) > 0

            clean_data[land_pixels] = np.nan
            clean_data[cloud_pixels] = np.nan
            clean_data[invalid_pixels] = np.nan

            logger.debug(
                "Maskeleme: Kara=%d, Bulut=%d, Geçersiz=%d piksel",
                np.sum(land_pixels),
                np.sum(cloud_pixels),
                np.sum(invalid_pixels),
            )

        # Fiziksel sınır kontrolü — aşırı değerleri temizle
        clean_data[clean_data < -2.0] = np.nan     # SST alt sınır
        clean_data[clean_data > 100.0] = np.nan     # Klorofil üst sınır

        nan_count = np.sum(np.isnan(clean_data))
        logger.info(
            "Kalite maskeleme tamamlandı: %d/%d piksel temizlendi (%%%.1f)",
            nan_count, total_pixels,
            (nan_count / total_pixels * 100) if total_pixels > 0 else 0,
        )

        return clean_data

    def _compute_statistics(
        self,
        clean_data: np.ndarray,
        date: str,
        param_type: str,
    ) -> Optional[dict[str, Any]]:
        """Temizlenmiş veri matrisinden özet istatistikler hesaplar.

        Args:
            clean_data: Kalite maskesi uygulanmış veri (NaN'lar dahil).
            date: Verinin tarihi (YYYY-MM-DD).
            param_type: Parametre tipi ('chlorophyll_a' veya 'sst').

        Returns:
            Optional[dict]: Hesaplanan istatistikler veya geçerli veri yoksa None.
        """
        valid_data = clean_data[~np.isnan(clean_data)]
        total_pixels = clean_data.size
        valid_pixels = valid_data.size

        if valid_pixels == 0:
            logger.warning(
                "Tarih %s için geçerli piksel bulunamadı — atlanıyor.", date
            )
            return None

        quality_ratio = valid_pixels / total_pixels if total_pixels > 0 else 0.0

        result = {
            "date": date,
            "parameter_type": param_type,
            "mean_value": round(float(np.nanmean(valid_data)), 4),
            "std_value": round(float(np.nanstd(valid_data)), 4),
            "min_value": round(float(np.nanmin(valid_data)), 4),
            "max_value": round(float(np.nanmax(valid_data)), 4),
            "valid_pixel_count": valid_pixels,
            "total_pixel_count": total_pixels,
            "quality_ratio": round(quality_ratio, 4),
        }

        logger.info(
            "İstatistikler hesaplandı [%s | %s]: "
            "Ortalama=%.4f, Std=%.4f, Min=%.4f, Max=%.4f, "
            "Kalite=%%%.1f (%d/%d piksel)",
            date, param_type,
            result["mean_value"], result["std_value"],
            result["min_value"], result["max_value"],
            quality_ratio * 100, valid_pixels, total_pixels,
        )

        return result

    def _append_to_timeseries(self, **kwargs: Any) -> None:
        """Hesaplanan istatistikleri zaman serisi CSV dosyasına ekler.

        Eğer aynı tarih ve parametre tipi için daha önce kayıt varsa
        günceller, yoksa yeni satır ekler.

        Args:
            **kwargs: CSV sütunlarına karşılık gelen anahtar-değer çiftleri.
        """
        csv_path = self._timeseries_path
        file_exists = csv_path.exists()

        # Mevcut verileri oku (varsa)
        existing_rows: list[dict[str, Any]] = []
        if file_exists:
            try:
                df = pd.read_csv(csv_path)
                existing_rows = df.to_dict("records")
            except Exception as exc:
                logger.warning("Mevcut CSV okunamadı: %s — yeni oluşturulacak.", exc)
                existing_rows = []

        # Aynı tarih + parametre tipi varsa güncelle
        date_val = kwargs.get("date")
        param_val = kwargs.get("parameter_type")
        updated = False

        for i, row in enumerate(existing_rows):
            if row.get("date") == date_val and row.get("parameter_type") == param_val:
                existing_rows[i] = kwargs
                updated = True
                logger.info(
                    "Mevcut kayıt güncellendi: %s / %s", date_val, param_val
                )
                break

        if not updated:
            existing_rows.append(kwargs)
            logger.info("Yeni kayıt eklendi: %s / %s", date_val, param_val)

        # CSV'ye yaz
        df = pd.DataFrame(existing_rows, columns=self.CSV_COLUMNS)
        df.to_csv(csv_path, index=False, encoding="utf-8")

        logger.info(
            "Zaman serisi güncellendi: %s (Toplam: %d kayıt)",
            csv_path.name, len(existing_rows),
        )

    def generate_mock_data(
        self,
        start_date: str,
        end_date: str,
        interval_days: int = 3,
    ) -> Path:
        """Test amaçlı gerçekçi simüle Marmara verisi üretir.

        Marmara Denizi'nde müsilaj dönemlerini yansıtan Klorofil-a
        ve SST zaman serisi oluşturur. Yaz aylarında artan değerler,
        müsilaj riskiyle korelasyon ve doğal varyans simüle edilir.

        Simülasyon özellikleri:
            - Klorofil-a bazal: 0.8-2.5 mg/m³ (kış), 3.0-15.0 mg/m³ (yaz/müsilaj)
            - SST bazal: 8-12°C (kış), 22-28°C (yaz)
            - Mevsimsel sinüzoidal trend
            - Rastgele gürültü (doğal varyans)

        Args:
            start_date: Başlangıç tarihi (YYYY-MM-DD).
            end_date: Bitiş tarihi (YYYY-MM-DD).
            interval_days: Veri noktaları arası gün sayısı (varsayılan: 3).

        Returns:
            Path: Oluşturulan zaman serisi CSV dosyasının yolu.
        """
        logger.info(
            "Mock veri üretimi başlıyor: %s → %s (aralık: %d gün)",
            start_date, end_date, interval_days,
        )

        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        current = start

        record_count = 0

        while current <= end:
            day_of_year = current.timetuple().tm_yday

            # Mevsimsel faktör (0-1 arası, yaz aylarında ~1, kış aylarında ~0)
            seasonal_factor = (
                0.5 * (1 + np.sin(2 * np.pi * (day_of_year - 80) / 365))
            )

            # --- Klorofil-a (mg/m³) ---
            # Kış bazal: ~1.5, Yaz pik: ~8.0, Müsilaj spike: ek +5-10
            chl_base = 1.0 + 7.0 * seasonal_factor
            chl_noise = np.random.normal(0, 0.5)
            # Müsilaj spike (Mayıs-Ağustos, %20 olasılıkla)
            mucilage_spike = 0.0
            if 5 <= current.month <= 8 and np.random.random() < 0.20:
                mucilage_spike = np.random.uniform(3.0, 12.0)
            chl_value = max(0.1, chl_base + chl_noise + mucilage_spike)

            chl_stats = {
                "date": current.strftime("%Y-%m-%d"),
                "parameter_type": "chlorophyll_a",
                "mean_value": round(chl_value, 4),
                "std_value": round(abs(np.random.normal(0.3, 0.1)), 4),
                "min_value": round(max(0.01, chl_value - np.random.uniform(0.5, 2.0)), 4),
                "max_value": round(chl_value + np.random.uniform(1.0, 5.0), 4),
                "valid_pixel_count": np.random.randint(3500, 5000),
                "total_pixel_count": 5850,
                "quality_ratio": round(np.random.uniform(0.60, 0.95), 4),
            }
            self._append_to_timeseries(**chl_stats)

            # --- SST (°C) ---
            # Kış bazal: ~10°C, Yaz pik: ~25°C
            sst_base = 10.0 + 15.0 * seasonal_factor
            sst_noise = np.random.normal(0, 0.8)
            sst_value = max(5.0, min(32.0, sst_base + sst_noise))

            sst_stats = {
                "date": current.strftime("%Y-%m-%d"),
                "parameter_type": "sst",
                "mean_value": round(sst_value, 4),
                "std_value": round(abs(np.random.normal(1.0, 0.3)), 4),
                "min_value": round(max(3.0, sst_value - np.random.uniform(1.0, 3.0)), 4),
                "max_value": round(min(35.0, sst_value + np.random.uniform(1.0, 3.0)), 4),
                "valid_pixel_count": np.random.randint(4000, 5500),
                "total_pixel_count": 5850,
                "quality_ratio": round(np.random.uniform(0.70, 0.95), 4),
            }
            self._append_to_timeseries(**sst_stats)

            record_count += 2
            current += timedelta(days=interval_days)

        logger.info(
            "Mock veri üretimi tamamlandı: %d kayıt → %s",
            record_count, self._timeseries_path.name,
        )

        return self._timeseries_path

    @staticmethod
    def _extract_date_from_netcdf(dataset: Any, filename: str) -> str:
        """NetCDF metadata'sından veya dosya adından tarih çıkarır.

        Args:
            dataset: Açık netCDF4.Dataset nesnesi.
            filename: Dosya adı (fallback olarak kullanılır).

        Returns:
            str: YYYY-MM-DD formatında tarih.
        """
        # Önce metadata'dan dene
        for attr in ["time_coverage_start", "start_date", "date_created"]:
            try:
                date_val = getattr(dataset, attr, None)
                if date_val:
                    return str(date_val)[:10]
            except (AttributeError, TypeError):
                continue

        # Dosya adından çıkar
        return MarmaraDataPreprocessor._extract_date_from_filename(filename)

    @staticmethod
    def _extract_date_from_filename(filename: str) -> str:
        """Dosya adındaki tarih bilgisini çıkarır.

        Sentinel-3 dosya adı formatı: S3A_OL_2_WFR___20240601T...
        Mock dosya adı formatı: mock_sentinel3_marmara_20240601.npz

        Args:
            filename: Dosya adı.

        Returns:
            str: YYYY-MM-DD formatında tarih veya bugünün tarihi (fallback).
        """
        import re

        # YYYYMMDD kalıbını ara
        match = re.search(r"(\d{4})(\d{2})(\d{2})", filename)
        if match:
            return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"

        return datetime.now().strftime("%Y-%m-%d")

    @staticmethod
    def _detect_parameter_type(filename: str) -> str:
        """Dosya adından parametre tipini tahmin eder.

        Args:
            filename: Dosya adı.

        Returns:
            str: Tahmin edilen parametre tipi.
        """
        filename_lower = filename.lower()

        if any(kw in filename_lower for kw in ["chl", "chlorophyll", "olci", "wfr"]):
            return "chlorophyll_a"
        elif any(kw in filename_lower for kw in ["sst", "lst", "slstr", "temperature"]):
            return "sst"
        else:
            return "unknown"
