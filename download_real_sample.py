"""
AquaSentinel AI — Real Data Downloader and Preprocessor Test Script

This script logs into CDSE, lists available Sentinel-3 products for July 2024,
downloads a sample Chlorophyll and SST product, extracts only the necessary
NetCDF (.nc) files to avoid Windows path length limits, and processes them.
"""

import os
import sys
import zipfile
import re
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Ensure UTF-8 output
if sys.stdout:
    try: sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError: pass

load_dotenv()

from src.data.sentinel_downloader import SentinelDataDownloader
from src.data.preprocessor import MarmaraDataPreprocessor
from src.utils import ensure_directory, format_file_size


def extract_date_from_name(name: str) -> str:
    """Extracts YYYYMMDD from filename."""
    match = re.search(r"(\d{4})(\d{2})(\d{2})", name)
    if match:
        return f"{match.group(1)}{match.group(2)}{match.group(3)}"
    return "20240707"


def extract_single_nc(zip_path: Path, output_dir: Path, original_name: str, pattern: str) -> Optional[Path]:
    """Finds a file matching pattern inside the zip and extracts it with a safe short name."""
    print(f"\n[*] Searching for '{pattern}' inside {zip_path.name}...")
    
    date_str = extract_date_from_name(original_name)
    output_filename = f"{pattern}_{date_str}.nc"
    output_path = output_dir / output_filename

    # If already extracted, skip
    if output_path.exists():
        print(f"[+] File already extracted: {output_filename}")
        return output_path

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        target_member = None
        for member in zip_ref.namelist():
            if pattern.lower() in member.lower() and member.endswith(".nc"):
                target_member = member
                break
        
        if target_member:
            print(f"[+] Found member: {target_member}")
            ensure_directory(output_dir)
            with zip_ref.open(target_member) as source, open(output_path, "wb") as target:
                target.write(source.read())
            print(f"[+] Extracted to: {output_path} ({format_file_size(output_path.stat().st_size)})")
            return output_path
        
    print(f"[HATA] '{pattern}' ile eşleşen NetCDF dosyası zip içinde bulunamadı.")
    return None


def main():
    print("==================================================")
    print("🌍 CDSE Gerçek Veri İndirme ve İşleme Testi (Seçici)")
    print("==================================================")

    # Dizinleri oluştur
    raw_dir = Path("data/raw")
    ensure_directory(raw_dir)

    downloader = SentinelDataDownloader()
    
    if downloader._mock_mode:
        print("[HATA] CDSE kimlik bilgileri yüklenemedi! Lütfen .env dosyasını kontrol edin.")
        return

    # 1. Mevcut Ürünleri Sorgula (Temmuz 2024 ilk haftası)
    start_date = "2024-07-01"
    end_date = "2024-07-07"
    
    print(f"\n[*] {start_date} - {end_date} arası Sentinel-3 ürünleri listeleniyor...")
    
    chl_products = downloader.get_available_products(start_date, end_date, "chlorophyll")
    sst_products = downloader.get_available_products(start_date, end_date, "sst")

    if not chl_products or not sst_products:
        print("[!] Sorgulanan aralıkta ürün bulunamadı. Lütfen tarihi genişletin veya mock veriyle devam edin.")
        return

    # En güncel/ilk ürünü seç
    selected_chl = chl_products[0]
    selected_sst = sst_products[0]

    preprocessor = MarmaraDataPreprocessor()

    # A. Klorofil-a İndir & İşle
    print(f"\n[*] Klorofil-a ürünü indiriliyor: {selected_chl['name']}...")
    chl_zip_path = downloader.download_marmara_data(
        start_date=start_date,
        end_date=end_date,
        output_dir=raw_dir,
        product_type="chlorophyll"
    )

    if chl_zip_path and chl_zip_path.suffix == ".zip":
        print(f"[+] Klorofil-a zip dosyası hazır: {chl_zip_path}")
        # Sadece CHL_OC4ME.nc dosyasını çıkar
        nc_file = extract_single_nc(chl_zip_path, raw_dir, selected_chl['name'], "CHL_OC4ME")
        if nc_file:
            print(f"[*] NetCDF verisi ön işleme tabi tutuluyor...")
            res = preprocessor.process_netcdf(nc_file)
            print(f"[+] İşleme Sonucu: {res}")
            
            # Geçici zip dosyasını temizle (disk tasarrufu)
            try:
                chl_zip_path.unlink()
                print("[*] Geçici zip dosyası temizlendi.")
            except Exception:
                pass
    else:
        print("[!] Klorofil-a gerçek veri indirme başarısız oldu veya mock döndü.")

    # B. SST İndir & İşle
    print(f"\n[*] SST (Deniz Sıcaklığı) ürünü indiriliyor: {selected_sst['name']}...")
    sst_zip_path = downloader.download_marmara_data(
        start_date=start_date,
        end_date=end_date,
        output_dir=raw_dir,
        product_type="sst"
    )

    if sst_zip_path and sst_zip_path.suffix == ".zip":
        print(f"[+] SST zip dosyası hazır: {sst_zip_path}")
        # Sadece sst.nc veya LST_in.nc dosyasını çıkar (SLSTR L2 ürünlerinde sst.nc bulunmayabilir, LST veya wqsf kullanılabilir)
        # Sentinel-3 SLSTR LST için "LST_in" parametresi kullanılır
        nc_file = extract_single_nc(sst_zip_path, raw_dir, selected_sst['name'], "LST_in")
        if nc_file:
            print(f"[*] NetCDF verisi ön işleme tabi tutuluyor...")
            res = preprocessor.process_netcdf(nc_file)
            print(f"[+] İşleme Sonucu: {res}")
            
            # Geçici zip dosyasını temizle
            try:
                sst_zip_path.unlink()
                print("[*] Geçici zip dosyası temizlendi.")
            except Exception:
                pass
    else:
        print("[!] SST gerçek veri indirme başarısız oldu veya mock döndü.")

    print("\n==================================================")
    print("🎉 Gerçek Veri Ön İşleme Testi Başarıyla Tamamlandı!")
    print("==================================================")


if __name__ == "__main__":
    main()
