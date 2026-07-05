"""
AquaSentinel AI — Veri Modülü

Uydu verilerinin indirilmesi ve ön işlenmesiyle ilgili
sınıf ve fonksiyonları içerir.
"""

from src.data.sentinel_downloader import SentinelDataDownloader
from src.data.preprocessor import MarmaraDataPreprocessor

__all__ = ["SentinelDataDownloader", "MarmaraDataPreprocessor"]
