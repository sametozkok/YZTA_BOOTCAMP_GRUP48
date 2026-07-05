"""
AquaSentinel AI — Yardımcı Fonksiyonlar (Utilities)

Proje genelinde kullanılan loglama altyapısı, dosya/dizin kontrol
fonksiyonları ve yapılandırma yardımcıları bu modülde tanımlanır.
"""

import logging
import os
from pathlib import Path
from typing import Optional


def get_project_root() -> Path:
    """Proje kök dizinini dinamik olarak döndürür.

    Bu fonksiyon, mevcut dosyanın konumundan iki seviye yukarı çıkarak
    proje kök dizinini bulur (src/utils.py -> src/ -> aquasentinel-ai/).

    Returns:
        Path: Proje kök dizininin mutlak yolu.
    """
    return Path(__file__).resolve().parent.parent


def ensure_directory(path: str | Path) -> Path:
    """Verilen dizin yolunun var olduğunu doğrular, yoksa oluşturur.

    Args:
        path: Oluşturulacak veya doğrulanacak dizin yolu.

    Returns:
        Path: Oluşturulan veya doğrulanan dizinin Path nesnesi.

    Example:
        >>> ensure_directory("data/raw")
        PosixPath('data/raw')
    """
    dir_path = Path(path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def setup_logger(
    name: str,
    log_file: Optional[str] = None,
    level: Optional[str] = None,
) -> logging.Logger:
    """Proje genelinde tutarlı bir loglama yapılandırması oluşturur.

    Hem konsola (StreamHandler) hem de opsiyonel olarak dosyaya
    (FileHandler) log yazan bir logger döndürür. Her iki handler
    için de aynı format kullanılır.

    Args:
        name: Logger'ın adı (genellikle modül adı: __name__).
        log_file: Log dosyasının yolu. None ise yalnızca konsola yazılır.
        level: Log seviyesi ('DEBUG', 'INFO', 'WARNING', 'ERROR').
               None ise LOG_LEVEL ortam değişkeninden okunur,
               o da yoksa 'INFO' kullanılır.

    Returns:
        logging.Logger: Yapılandırılmış logger nesnesi.

    Example:
        >>> logger = setup_logger(__name__, log_file="logs/app.log")
        >>> logger.info("Sistem başlatıldı.")
    """
    if level is None:
        level = os.getenv("LOG_LEVEL", "INFO")

    numeric_level = getattr(logging, level.upper(), logging.INFO)

    logger = logging.getLogger(name)
    logger.setLevel(numeric_level)

    # Aynı logger'a birden fazla handler eklenmesini engelle
    if logger.handlers:
        return logger

    # Log formatı: [2026-07-05 10:30:00] [INFO] [modül_adı] Mesaj
    formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)-8s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Konsol handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Dosya handler (opsiyonel)
    if log_file:
        log_dir = Path(log_file).parent
        ensure_directory(log_dir)

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def validate_date_format(date_string: str) -> bool:
    """Tarih stringinin YYYY-MM-DD formatında olduğunu doğrular.

    Args:
        date_string: Kontrol edilecek tarih stringi.

    Returns:
        bool: Format geçerliyse True, değilse False.
    """
    from datetime import datetime

    try:
        datetime.strptime(date_string, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def format_file_size(size_bytes: int) -> str:
    """Byte cinsinden dosya boyutunu okunabilir formata çevirir.

    Args:
        size_bytes: Dosya boyutu (byte).

    Returns:
        str: İnsan tarafından okunabilir dosya boyutu (ör. '15.3 MB').
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"
