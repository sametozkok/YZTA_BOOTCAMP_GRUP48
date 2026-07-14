"""
AquaSentinel AI — Marmara Denizi Zaman Serisi Görselleştirme Modülü

Bu betik, 'data/processed/marmara_time_series.csv' dosyasını okuyarak
Klorofil-a konsantrasyonu ve Deniz Yüzeyi Sıcaklığı (SST) parametrelerinin
zaman içindeki değişimlerini grafiksel olarak çizer ve kaydeder.

Kullanım:
    python src/visualization.py
"""

import os
from pathlib import Path
import pandas as pd
import numpy as np

# matplotlib'in kurulu olup olmadığını kontrol et, yoksa yükleme uyarısı ver
try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
except ImportError:
    print("HATA: 'matplotlib' kütüphanesi bulunamadı.")
    print("Grafik çizebilmek için lütfen 'pip install matplotlib' komutunu çalıştırın.")
    exit(1)

from src.utils import setup_logger, ensure_directory

logger = setup_logger(__name__, log_file="logs/visualization.log")


def plot_marmara_trends(
    csv_path: str | Path = "data/processed/marmara_time_series.csv",
    output_image_path: str | Path = "data/processed/marmara_trends.png"
) -> bool:
    """Marmara Denizi zaman serisi verilerinden trend grafikleri çizer.

    Args:
        csv_path: Veri kaynağı olan zaman serisi CSV dosyası.
        output_image_path: Grafik çıktısının kaydedileceği resim yolu.

    Returns:
        bool: İşlem başarılıysa True, değilse False.
    """
    csv_path = Path(csv_path)
    output_image_path = Path(output_image_path)

    if not csv_path.exists():
        logger.error("Zaman serisi CSV dosyası bulunamadı: %s", csv_path)
        return False

    try:
        # Veriyi oku
        df = pd.read_csv(csv_path)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values(by='date')

        # Parametreleri ayır
        df_chl = df[df['parameter_type'] == 'chlorophyll_a']
        df_sst = df[df['parameter_type'] == 'sst']

        if df_chl.empty and df_sst.empty:
            logger.warning("Görselleştirilecek veri bulunamadı (Chl veya SST boş).")
            return False

        # Grafik ayarları
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
        fig.suptitle("🌊 Marmara Denizi Müsilaj Parametreleri Trend Analizi (2024)", fontsize=14, fontweight='bold', color='#1A365D')

        # 1. Klorofil-a Grafiği
        if not df_chl.empty:
            ax1.plot(df_chl['date'], df_chl['mean_value'], color='#2D3748', linewidth=2.0, marker='o', markersize=4, label='Ortalama Klorofil-a')
            ax1.fill_between(
                df_chl['date'],
                df_chl['mean_value'] - df_chl['std_value'],
                df_chl['mean_value'] + df_chl['std_value'],
                color='#718096',
                alpha=0.15,
                label='Standart Sapma'
            )
            ax1.set_ylabel("Klorofil-a (mg/m³)", fontsize=11, fontweight='bold', color='#2D3748')
            ax1.grid(True, linestyle='--', alpha=0.5)
            ax1.legend(loc='upper left')
            ax1.set_title("Klorofil-a Konsantrasyonu (Müsilaj Risk Göstergesi)", fontsize=12, fontweight='bold', color='#2B6CB0')
            
            # Risk eşik çizgisi (5 mg/m³ üstü riskli kabul edilir)
            ax1.axhline(y=5.0, color='#E53E3E', linestyle=':', linewidth=1.5, label='Müsilaj Risk Eşiği (>5)')
            ax1.legend(loc='upper left')

        # 2. SST Grafiği
        if not df_sst.empty:
            ax2.plot(df_sst['date'], df_sst['mean_value'], color='#DD6B20', linewidth=2.0, marker='o', markersize=4, label='Ortalama Deniz Yüzeyi Sıcaklığı (SST)')
            ax2.fill_between(
                df_sst['date'],
                df_sst['mean_value'] - df_sst['std_value'],
                df_sst['mean_value'] + df_sst['std_value'],
                color='#ED8936',
                alpha=0.15,
                label='Standart Sapma'
            )
            ax2.set_ylabel("Deniz Yüzeyi Sıcaklığı (°C)", fontsize=11, fontweight='bold', color='#2D3748')
            ax2.grid(True, linestyle='--', alpha=0.5)
            ax2.legend(loc='upper left')
            ax2.set_title("Deniz Yüzeyi Sıcaklığı (SST) Değişimi", fontsize=12, fontweight='bold', color='#C05621')

            # Sıcaklık risk eşik çizgisi (>22°C müsilaj oluşumunu tetikler)
            ax2.axhline(y=22.0, color='#E53E3E', linestyle=':', linewidth=1.5, label='Sıcaklık Tetikleme Eşiği (>22°C)')
            ax2.legend(loc='upper left')

        # X ekseni tarih formatlama
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=30))
        plt.gcf().autofmt_xdate()

        # Kaydet ve Kapat
        ensure_directory(output_image_path.parent)
        plt.tight_layout()
        plt.savefig(output_image_path, dpi=300)
        plt.close()

        logger.info("Grafik basariyla olusturuldu ve kaydedildi: %s", output_image_path)
        print(f"Grafik basariyla olusturuldu: {output_image_path}")
        return True

    except Exception as exc:
        logger.error("Grafik çizilirken beklenmeyen bir hata oluştu: %s", exc, exc_info=True)
        return False


if __name__ == "__main__":
    plot_marmara_trends()
