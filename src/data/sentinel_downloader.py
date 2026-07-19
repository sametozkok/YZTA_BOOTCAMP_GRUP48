"""
AquaSentinel AI — Sentinel Uydu Verisi İndirme Modülü

Copernicus Dataspace Ecosystem (CDSE) OData API üzerinden
Sentinel-3 OLCI ve SLSTR uydu verilerini sorgulayan ve
indiren sınıfı içerir.

Dual-mode tasarım:
    - Gerçek mod: CDSE API'ye bağlanıp veri indirir.
    - Mock mod: API erişimi yoksa simüle edilmiş NetCDF dosyası üretir.

Kullanım:
    >>> from src.data.sentinel_downloader import SentinelDataDownloader
    >>> downloader = SentinelDataDownloader()
    >>> downloader.download_marmara_data("2024-06-01", "2024-06-15", "data/raw")
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import numpy as np
import requests
from dotenv import load_dotenv

from src.utils import ensure_directory, format_file_size, setup_logger, validate_date_format

logger = setup_logger(__name__, log_file="logs/downloader.log")


class SentinelDataDownloader:
    """Copernicus Dataspace Ecosystem (CDSE) üzerinden Sentinel-3 verisi indirir.

    Bu sınıf, Marmara Denizi bölgesi için Sentinel-3 OLCI (Klorofil-a)
    ve SLSTR (Deniz Yüzeyi Sıcaklığı - SST) ürünlerini sorgular ve indirir.
    API erişimi başarısız olursa otomatik olarak mock moduna geçer.

    Attributes:
        MARMARA_BBOX: Marmara Denizi coğrafi sınır kutusu (WKT formatı).
        CATALOGUE_URL: CDSE OData API temel URL'si.
        TOKEN_URL: CDSE OAuth2 token endpoint'i.
        PRODUCT_TYPES: Desteklenen Sentinel-3 ürün tipleri.
    """

    # İzmit Körfezi Bounding Box (WKT) — 2021 müsilaj krizinde en çok etkilenen bölge
    MARMARA_BBOX: str = (
        "POLYGON((29.20 40.65, 29.95 40.65, 29.95 40.78, 29.20 40.78, 29.20 40.65))"
    )

    # CDSE API Endpoint'leri
    CATALOGUE_URL: str = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
    TOKEN_URL: str = (
        "https://identity.dataspace.copernicus.eu/auth/realms/"
        "CDSE/protocol/openid-connect/token"
    )

    # Desteklenen ürün tipleri
    PRODUCT_TYPES: dict[str, str] = {
        "chlorophyll": "OL_2_WFR___",
        "sst": "SL_2_WST___",
    }

    def __init__(self) -> None:
        """SentinelDataDownloader'ı başlatır ve kimlik bilgilerini yükler.

        .env dosyasından CDSE kullanıcı adı ve şifresini okur.
        Kimlik bilgileri bulunamazsa uyarı verir ve mock moda geçer.
        """
        load_dotenv()

        self.username: Optional[str] = os.getenv("CDSE_USERNAME")
        self.password: Optional[str] = os.getenv("CDSE_PASSWORD")
        self._access_token: Optional[str] = None
        self._mock_mode: bool = False

        if not self.username or not self.password:
            logger.warning(
                "CDSE kimlik bilgileri .env dosyasında bulunamadı. "
                "Mock mod etkinleştirilecek. Gerçek veri indirmek için "
                ".env.example dosyasını .env olarak kopyalayıp bilgilerinizi girin."
            )
            self._mock_mode = True
        else:
            logger.info(
                "CDSE kimlik bilgileri yüklendi. Kullanıcı: %s", self.username
            )

    def _authenticate(self) -> bool:
        """CDSE OAuth2 ile kimlik doğrulaması yapar ve erişim token'ı alır.

        Returns:
            bool: Kimlik doğrulama başarılıysa True, değilse False.
        """
        if self._mock_mode:
            logger.info("Mock mod aktif — kimlik doğrulama atlanıyor.")
            return False

        try:
            response = requests.post(
                self.TOKEN_URL,
                data={
                    "client_id": "cdse-public",
                    "username": self.username,
                    "password": self.password,
                    "grant_type": "password",
                },
                timeout=30,
            )
            response.raise_for_status()

            token_data = response.json()
            self._access_token = token_data.get("access_token")

            if self._access_token:
                logger.info("CDSE OAuth2 kimlik doğrulama başarılı.")
                return True
            else:
                logger.error("Token yanıtında 'access_token' bulunamadı.")
                return False

        except requests.exceptions.ConnectionError:
            logger.error(
                "CDSE sunucusuna bağlanılamadı. İnternet bağlantınızı kontrol edin."
            )
            return False
        except requests.exceptions.HTTPError as exc:
            logger.error("Kimlik doğrulama hatası (HTTP %s): %s", exc.response.status_code, exc)
            return False
        except requests.exceptions.Timeout:
            logger.error("Kimlik doğrulama zaman aşımına uğradı (30s).")
            return False
        except requests.exceptions.RequestException as exc:
            logger.error("Beklenmeyen kimlik doğrulama hatası: %s", exc)
            return False

    def _build_query(
        self,
        start_date: str,
        end_date: str,
        product_type: str = "chlorophyll",
    ) -> str:
        """CDSE OData API sorgu URL'si oluşturur.

        Args:
            start_date: Başlangıç tarihi (YYYY-MM-DD formatında).
            end_date: Bitiş tarihi (YYYY-MM-DD formatında).
            product_type: Ürün tipi anahtarı ('chlorophyll' veya 'sst').

        Returns:
            str: OData $filter parametreleriyle oluşturulmuş sorgu URL'si.

        Raises:
            ValueError: Geçersiz product_type veya tarih formatı verildiğinde.
        """
        if product_type not in self.PRODUCT_TYPES:
            raise ValueError(
                f"Geçersiz ürün tipi: '{product_type}'. "
                f"Desteklenen tipler: {list(self.PRODUCT_TYPES.keys())}"
            )

        if not validate_date_format(start_date) or not validate_date_format(end_date):
            raise ValueError(
                f"Tarih formatı YYYY-MM-DD olmalıdır. "
                f"Verilen: start='{start_date}', end='{end_date}'"
            )

        sentinel_product = self.PRODUCT_TYPES[product_type]

        odata_filter = (
            f"Collection/Name eq 'SENTINEL-3' "
            f"and Attributes/OData.CSC.StringAttribute/any("
            f"att:att/Name eq 'productType' and att/OData.CSC.StringAttribute/Value eq '{sentinel_product}') "
            f"and OData.CSC.Intersects(area=geography'SRID=4326;{self.MARMARA_BBOX}') "
            f"and ContentDate/Start gt {start_date}T00:00:00.000Z "
            f"and ContentDate/Start lt {end_date}T23:59:59.999Z"
        )

        query_url = (
            f"{self.CATALOGUE_URL}?$filter={odata_filter}"
            f"&$orderby=ContentDate/Start desc"
            f"&$top=5"
        )

        logger.debug("OData sorgu URL'si oluşturuldu: %s", query_url)
        return query_url

    def _download_product(
        self,
        product_id: str,
        product_name: str,
        output_dir: str | Path,
    ) -> Optional[Path]:
        """Tekil bir ürünü CDSE API'den indirir.

        Args:
            product_id: CDSE ürün UUID'si.
            product_name: Ürün dosya adı.
            output_dir: İndirilecek dizin yolu.

        Returns:
            Optional[Path]: İndirilen dosyanın yolu, başarısızsa None.
        """
        output_path = Path(output_dir) / f"{product_name}.zip"

        if output_path.exists():
            logger.info("Ürün zaten mevcut, atlanıyor: %s", output_path.name)
            return output_path

        download_url = f"{self.CATALOGUE_URL}({product_id})/$value"
        headers = {"Authorization": f"Bearer {self._access_token}"}

        try:
            logger.info("İndirme başlıyor: %s", product_name)

            # CDSE redirects across subdomains strip the Authorization header in python requests.
            # We handle the redirect manually to preserve the header.
            response = requests.get(
                download_url, headers=headers, stream=True, timeout=300, allow_redirects=False
            )
            
            if response.status_code in (301, 302, 303, 307, 308):
                redirect_url = response.headers.get("Location")
                logger.info("Yönlendirme tespit edildi, kimlik bilgileri taşınıyor -> %s", redirect_url)
                response.close()
                response = requests.get(
                    redirect_url, headers=headers, stream=True, timeout=300, allow_redirects=True
                )
            
            with response:
                response.raise_for_status()

                total_size = int(response.headers.get("content-length", 0))
                downloaded = 0

                with open(output_path, "wb") as file:
                    for chunk in response.iter_content(chunk_size=8192):
                        file.write(chunk)
                        downloaded += len(chunk)

                        # Her 10 MB'da ilerleme logu
                        if downloaded % (10 * 1024 * 1024) < 8192:
                            progress = (
                                f"{format_file_size(downloaded)}/{format_file_size(total_size)}"
                                if total_size > 0
                                else format_file_size(downloaded)
                            )
                            logger.info("İndirme ilerlemesi: %s", progress)

            logger.info(
                "İndirme tamamlandı: %s (%s)",
                output_path.name,
                format_file_size(output_path.stat().st_size),
            )
            return output_path

        except requests.exceptions.HTTPError as exc:
            logger.error("İndirme hatası (HTTP %s): %s", exc.response.status_code, exc)
            if output_path.exists():
                output_path.unlink()
            return None
        except requests.exceptions.RequestException as exc:
            logger.error("İndirme sırasında bağlantı hatası: %s", exc)
            if output_path.exists():
                output_path.unlink()
            return None

    def _mock_download(self, output_dir: str | Path) -> Path:
        """Gerçek API erişimi olmadığında simüle edilmiş bir NetCDF dosyası üretir.

        Marmara Denizi boyutlarına uygun, gerçekçi Klorofil-a ve SST
        değerleri içeren bir NumPy dosyası oluşturur. Bu dosya, preprocessor
        modülünün test edilmesi için kullanılabilir.

        Args:
            output_dir: Dosyanın kaydedileceği dizin.

        Returns:
            Path: Oluşturulan mock dosyasının yolu.
        """
        output_path = Path(output_dir)
        ensure_directory(output_path)

        mock_filename = f"mock_sentinel3_marmara_{datetime.now().strftime('%Y%m%d')}.npz"
        mock_filepath = output_path / mock_filename

        # Marmara Denizi grid boyutları (yaklaşık 300m çözünürlükte)
        lat_points = 50   # ~1.5 derece / 0.03
        lon_points = 117  # ~3.5 derece / 0.03

        # Koordinat gridleri
        latitudes = np.linspace(40.0, 41.5, lat_points)
        longitudes = np.linspace(26.5, 30.0, lon_points)

        # Simüle Klorofil-a verisi (mg/m³)
        # Marmara'da normal: 0.5-3.0, müsilaj döneminde: 5.0-20.0+
        chlorophyll = np.random.uniform(0.5, 5.0, (lat_points, lon_points))

        # Kara maskesi (basit dikdörtgen yaklaşımı)
        land_mask = np.zeros((lat_points, lon_points), dtype=bool)
        land_mask[:10, :30] = True    # Kuzey-batı (Trakya kıyısı)
        land_mask[:8, 80:] = True     # Kuzey-doğu (İstanbul kıyısı)
        land_mask[40:, 50:80] = True  # Güney (Bursa/Yalova kıyısı)

        # Bulut maskesi (%15 rastgele bulut)
        cloud_mask = np.random.random((lat_points, lon_points)) < 0.15

        # Kalite flag'leri birleştir
        quality_flags = np.zeros((lat_points, lon_points), dtype=np.uint8)
        quality_flags[land_mask] = 1   # 1 = kara
        quality_flags[cloud_mask] = 2  # 2 = bulut

        # Kara ve bulutlu piksellere NaN ata
        chlorophyll[land_mask | cloud_mask] = np.nan

        # Simüle SST verisi (°C)
        # Marmara yazın: 20-28°C, müsilaj riskli dönem: >22°C
        sst = np.random.uniform(20.0, 28.0, (lat_points, lon_points))
        sst[land_mask | cloud_mask] = np.nan

        # Tüm verileri kaydet
        np.savez(
            mock_filepath,
            chlorophyll=chlorophyll,
            sst=sst,
            latitudes=latitudes,
            longitudes=longitudes,
            quality_flags=quality_flags,
            land_mask=land_mask,
            cloud_mask=cloud_mask,
        )

        logger.info(
            "Mock uydu verisi oluşturuldu: %s (Grid: %dx%d, Boyut: %s)",
            mock_filepath.name,
            lat_points,
            lon_points,
            format_file_size(mock_filepath.stat().st_size),
        )

        return mock_filepath

    def download_marmara_data(
        self,
        start_date: str,
        end_date: str,
        output_dir: str | Path = "data/raw",
        product_type: str = "chlorophyll",
    ) -> Optional[Path]:
        """Marmara Denizi için Sentinel-3 uydu verisi indirir.

        CDSE OData API üzerinden belirtilen tarih aralığı ve ürün tipi
        için sorgu yapar. En güncel uygun ürünü seçip indirir.
        API erişimi başarısız olursa mock moduna geçer.

        Args:
            start_date: Başlangıç tarihi (YYYY-MM-DD).
            end_date: Bitiş tarihi (YYYY-MM-DD).
            output_dir: İndirilecek dizin (varsayılan: 'data/raw').
            product_type: 'chlorophyll' veya 'sst' (varsayılan: 'chlorophyll').

        Returns:
            Optional[Path]: İndirilen/üretilen dosyanın yolu.

        Example:
            >>> downloader = SentinelDataDownloader()
            >>> path = downloader.download_marmara_data(
            ...     "2024-06-01", "2024-06-15", "data/raw", "chlorophyll"
            ... )
        """
        logger.info(
            "Marmara verisi indirme başlatılıyor — "
            "Tarih: %s → %s, Ürün: %s, Dizin: %s",
            start_date, end_date, product_type, output_dir,
        )

        ensure_directory(output_dir)

        # Mock moda düşme kontrolü
        if self._mock_mode:
            logger.info(
                "Mock mod aktif — simüle edilmiş veri üretiliyor."
            )
            return self._mock_download(output_dir)

        # Kimlik doğrulama
        if not self._authenticate():
            logger.warning(
                "Kimlik doğrulama başarısız — mock moda geçiliyor."
            )
            self._mock_mode = True
            return self._mock_download(output_dir)

        # Sorgu oluştur ve çalıştır
        try:
            query_url = self._build_query(start_date, end_date, product_type)

            headers = {"Authorization": f"Bearer {self._access_token}"}
            response = requests.get(query_url, headers=headers, timeout=60)
            response.raise_for_status()

            results = response.json()
            products = results.get("value", [])

            if not products:
                logger.warning(
                    "Belirtilen tarih aralığında ürün bulunamadı "
                    "(%s → %s). Mock veri üretiliyor.",
                    start_date, end_date,
                )
                return self._mock_download(output_dir)

            # En güncel ürünü seç (ilk sonuç — sıralama desc)
            best_product = products[0]
            product_id = best_product["Id"]
            product_name = best_product["Name"]

            logger.info(
                "En uygun ürün seçildi: %s (ID: %s)",
                product_name, product_id,
            )

            return self._download_product(product_id, product_name, output_dir)

        except ValueError as exc:
            logger.error("Parametre hatası: %s", exc)
            return None
        except requests.exceptions.RequestException as exc:
            logger.error(
                "API sorgu hatası: %s — mock moda geçiliyor.", exc
            )
            return self._mock_download(output_dir)
        except (json.JSONDecodeError, KeyError) as exc:
            logger.error(
                "API yanıt ayrıştırma hatası: %s — mock moda geçiliyor.", exc
            )
            return self._mock_download(output_dir)

    def get_available_products(
        self,
        start_date: str,
        end_date: str,
        product_type: str = "chlorophyll",
    ) -> list[dict[str, Any]]:
        """Belirtilen tarih aralığındaki uygun ürünleri listeler (indirmeden).

        Args:
            start_date: Başlangıç tarihi (YYYY-MM-DD).
            end_date: Bitiş tarihi (YYYY-MM-DD).
            product_type: 'chlorophyll' veya 'sst'.

        Returns:
            list[dict]: Ürün bilgileri listesi (id, name, date, size).
        """
        if self._mock_mode:
            logger.info("Mock mod aktif — örnek ürün listesi döndürülüyor.")
            return [
                {
                    "id": "mock-uuid-001",
                    "name": f"S3A_OL_2_WFR___{start_date.replace('-', '')}",
                    "date": start_date,
                    "size": "250 MB",
                    "mock": True,
                }
            ]

        try:
            if not self._access_token and not self._authenticate():
                return []

            query_url = self._build_query(start_date, end_date, product_type)
            headers = {"Authorization": f"Bearer {self._access_token}"}
            response = requests.get(query_url, headers=headers, timeout=60)
            response.raise_for_status()

            products = response.json().get("value", [])
            return [
                {
                    "id": p["Id"],
                    "name": p["Name"],
                    "date": p.get("ContentDate", {}).get("Start", "N/A"),
                    "size": format_file_size(p.get("ContentLength", 0)),
                    "mock": False,
                }
                for p in products
            ]

        except requests.exceptions.RequestException as exc:
            logger.error("Ürün listeleme hatası: %s", exc)
            return []
