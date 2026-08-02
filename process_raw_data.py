"""
AquaSentinel AI — Ham Satellite NetCDF Verilerini İşleme Betiği

Bu betik 'data/raw' klasöründeki tüm gerçek Sentinel-3 NetCDF (.nc) dosyalarını
okur, kalite filtrelerini uygular ve 'data/processed/marmara_time_series.csv'
dosyasına kaydeder.
"""

import os
import sys
from pathlib import Path

# Windows UTF-8 desteği
if sys.stdout:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
if sys.stderr:
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

from src.data.preprocessor import MarmaraDataPreprocessor
from src.utils import setup_logger

logger = setup_logger("process_raw_data", log_file="logs/process_raw_data.log")

def main():
    raw_dir = Path("data/raw")
    nc_files = list(raw_dir.glob("*.nc"))
    
    print(f"[*] 'data/raw/' klasöründe {len(nc_files)} adet NetCDF (.nc) dosyası bulundu.")
    if not nc_files:
        print("[-] Hata: 'data/raw/' klasöründe .nc dosyası bulunamadı.")
        return
        
    preprocessor = MarmaraDataPreprocessor()
    success_count = 0
    
    # Dosyaları isme göre sırala
    nc_files.sort()
    
    for i, file_path in enumerate(nc_files, 1):
        print(f"[{i}/{len(nc_files)}] İşleniyor: {file_path.name}...")
        res = preprocessor.process_netcdf(file_path)
        if res:
            success_count += 1
            print(f"   -> Başarılı: Tarih={res['date']} | Param={res['parameter_type']} | Ort={res['mean_value']}")
        else:
            print(f"   -> İşlenemedi / Geçersiz: {file_path.name}")
            
    print(f"\n[+] İşlem Tamamlandı! {len(nc_files)} dosyadan {success_count} tanesi başarıyla işlendi.")
    print(f"[+] Çıktı Dosyası: data/processed/marmara_time_series.csv")

if __name__ == "__main__":
    main()
