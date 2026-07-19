"""
AquaSentinel AI — Toplu Gerçek Veri İndirme Betiği

İzmit Körfezi için 4 yaz döneminde (2021-2024, Mayıs-Eylül) haftada 1
Sentinel-3 klorofil-a ve SST ürünü indirip işler.

Kullanım:
    python download_real_data.py              # Tahmini boyut göster ve onayla
    python download_real_data.py --start      # Doğrudan indirmeyi başlat
    python download_real_data.py --resume     # Kaldığı yerden devam et
"""

import os
import sys
import time
import zipfile
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

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

from dotenv import load_dotenv
load_dotenv()

from src.data.sentinel_downloader import SentinelDataDownloader
from src.data.preprocessor import MarmaraDataPreprocessor
from src.utils import ensure_directory, format_file_size


# ─── Yapılandırma ───────────────────────────────────────────────────────

SUMMERS = [
    ("2021-05-01", "2021-09-30"),  # Büyük müsilaj krizi
    ("2022-05-01", "2022-09-30"),  # Kriz sonrası
]

WEEK_INTERVAL_DAYS = 7  # Her hafta 1 veri noktası
RAW_DIR = Path("data/raw")
PROGRESS_FILE = Path("data/raw/.download_progress.txt")

# Tahmini boyutlar (Sentinel-3 ürünleri)
EST_CHL_SIZE_MB = 500   # OLCI WFR ZIP boyutu
EST_SST_SIZE_MB = 30     # SLSTR WST ZIP boyutu (LST'den çok daha küçük)
EST_DOWNLOAD_SPEED_MBPS = 10  # MB/s (ortalama)


def generate_weekly_dates() -> list[tuple[str, str]]:
    """4 yaz dönemi için haftalık tarih çiftleri üretir."""
    weeks = []
    for start_str, end_str in SUMMERS:
        start = datetime.strptime(start_str, "%Y-%m-%d")
        end = datetime.strptime(end_str, "%Y-%m-%d")
        current = start
        while current <= end:
            week_end = min(current + timedelta(days=6), end)
            weeks.append((
                current.strftime("%Y-%m-%d"),
                week_end.strftime("%Y-%m-%d"),
            ))
            current += timedelta(days=WEEK_INTERVAL_DAYS)
    return weeks


def extract_date_from_name(name: str) -> str:
    """Ürün adından YYYYMMDD çıkarır."""
    match = re.search(r"(\d{4})(\d{2})(\d{2})", name)
    if match:
        return f"{match.group(1)}{match.group(2)}{match.group(3)}"
    return "unknown"


def extract_single_nc(zip_path: Path, output_dir: Path, original_name: str, pattern: str) -> Optional[Path]:
    """ZIP'ten sadece hedef .nc dosyasını çıkarır (kısa ad ile)."""
    date_str = extract_date_from_name(original_name)
    output_filename = f"{pattern}_{date_str}.nc"
    output_path = output_dir / output_filename

    if output_path.exists():
        return output_path

    try:
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            for member in zip_ref.namelist():
                if pattern.lower() in member.lower() and member.endswith(".nc"):
                    with zip_ref.open(member) as source, open(output_path, "wb") as target:
                        target.write(source.read())
                    return output_path
    except Exception as exc:
        print(f"    [HATA] ZIP açma hatası: {exc}")
    return None


def load_progress() -> set[str]:
    """İndirme ilerlemesini diskten oku."""
    if PROGRESS_FILE.exists():
        return set(PROGRESS_FILE.read_text(encoding="utf-8").strip().split("\n"))
    return set()


def save_progress(completed: set[str]):
    """İndirme ilerlemesini diske yaz."""
    ensure_directory(PROGRESS_FILE.parent)
    PROGRESS_FILE.write_text("\n".join(sorted(completed)), encoding="utf-8")


def show_estimate():
    """İndirme öncesi tahmini boyut ve süre göster."""
    weeks = generate_weekly_dates()
    completed = load_progress()
    remaining = [w for w in weeks if f"{w[0]}_chl" not in completed]

    total_weeks = len(weeks)
    remaining_weeks = len(remaining)
    already_done = total_weeks - remaining_weeks

    # Her hafta: 1 CHL (500 MB) + 1 SST (30 MB) indiriliyor, sonra silinecek
    total_download_mb = remaining_weeks * (EST_CHL_SIZE_MB + EST_SST_SIZE_MB)
    total_download_gb = total_download_mb / 1024
    est_time_seconds = total_download_mb / EST_DOWNLOAD_SPEED_MBPS
    est_time_minutes = est_time_seconds / 60
    est_time_hours = est_time_minutes / 60

    # Disk kullanımı: sadece .nc dosyaları kalacak (~5 MB CHL + ~1 MB SST per week)
    disk_usage_mb = total_weeks * 6

    print("\n" + "=" * 60)
    print("📊 İNDİRME TAHMİNİ")
    print("=" * 60)
    print(f"\n🗺️  Bölge        : İzmit Körfezi")
    print(f"📅 Dönem        : 4 yaz (2021-2024, Mayıs-Eylül)")
    print(f"📦 Toplam Hafta  : {total_weeks}")
    print(f"✅ Tamamlanan    : {already_done}")
    print(f"📥 Kalan         : {remaining_weeks}")
    print(f"\n{'─' * 60}")
    print(f"💾 Tahmini İndirme : ~{total_download_gb:.1f} GB")
    print(f"   (Her hafta {EST_CHL_SIZE_MB} MB CHL + {EST_SST_SIZE_MB} MB SST, ZIP sonra siliniyor)")
    print(f"💿 Disk Kullanımı  : ~{disk_usage_mb} MB (sadece .nc dosyaları kalır)")
    print(f"⏱️  Tahmini Süre    : ~{est_time_hours:.1f} saat ({est_time_minutes:.0f} dakika)")
    print(f"   ({EST_DOWNLOAD_SPEED_MBPS} MB/s ortalama hız varsayımıyla)")
    print(f"{'─' * 60}")

    print(f"\n📋 Dönem Detayları:")
    for i, (s, e) in enumerate(SUMMERS):
        year = s[:4]
        year_weeks = [w for w in weeks if w[0].startswith(year)]
        year_remaining = [w for w in year_weeks if f"{w[0]}_chl" not in completed]
        status = "✅" if len(year_remaining) == 0 else "📥"
        label = " (MÜSİLAJ KRİZİ)" if year == "2021" else ""
        print(f"   {status} {year} Yazı{label}: {len(year_weeks)} hafta ({len(year_remaining)} kalan)")

    print(f"\n{'=' * 60}\n")
    return remaining_weeks > 0


def download_all():
    """Tüm haftalık verileri indir ve işle."""
    weeks = generate_weekly_dates()
    completed = load_progress()
    
    downloader = SentinelDataDownloader()
    if downloader._mock_mode:
        print("[HATA] CDSE kimlik bilgileri bulunamadı! .env dosyasını kontrol edin.")
        return

    preprocessor = MarmaraDataPreprocessor()
    ensure_directory(RAW_DIR)

    total = len(weeks)
    success_count = 0
    fail_count = 0
    skipped_count = 0

    start_time = time.time()

    for i, (week_start, week_end) in enumerate(weeks, 1):
        chl_key = f"{week_start}_chl"
        sst_key = f"{week_start}_sst"

        # Zaten tamamlanmış mı?
        if chl_key in completed and sst_key in completed:
            skipped_count += 1
            continue

        elapsed = time.time() - start_time
        remaining_count = total - i
        if success_count > 0:
            avg_per_item = elapsed / (success_count + fail_count) if (success_count + fail_count) > 0 else 0
            eta_seconds = remaining_count * avg_per_item
            eta_str = f" (ETA: {eta_seconds/60:.0f} dk)"
        else:
            eta_str = ""

        print(f"\n{'━' * 60}")
        print(f"📅 [{i}/{total}] Hafta: {week_start} → {week_end}{eta_str}")
        print(f"{'━' * 60}")

        # A. Klorofil-a
        if chl_key not in completed:
            try:
                print(f"   🟢 Klorofil-a indiriliyor...")
                chl_products = downloader.get_available_products(week_start, week_end, "chlorophyll")
                
                if chl_products:
                    selected = chl_products[0]
                    chl_zip = downloader.download_marmara_data(week_start, week_end, RAW_DIR, "chlorophyll")
                    
                    if chl_zip and chl_zip.suffix == ".zip":
                        nc_file = extract_single_nc(chl_zip, RAW_DIR, selected["name"], "CHL_OC4ME")
                        if nc_file:
                            res = preprocessor.process_netcdf(nc_file)
                            if res:
                                print(f"   ✅ CHL: {res['mean_value']:.4f} mg/m³ (kalite: %{res['quality_ratio']*100:.0f})")
                                completed.add(chl_key)
                            else:
                                print(f"   ⚠️ CHL: Geçerli piksel bulunamadı")
                                completed.add(chl_key)  # Tekrar denemesin
                        # ZIP temizle
                        try:
                            chl_zip.unlink()
                        except Exception:
                            pass
                    else:
                        print(f"   ⚠️ CHL: İndirme başarısız")
                else:
                    print(f"   ⚠️ CHL: Bu hafta ürün bulunamadı")
                    completed.add(chl_key)
            except Exception as exc:
                print(f"   ❌ CHL Hata: {exc}")
                fail_count += 1

        # B. SST (Water Surface Temperature)
        if sst_key not in completed:
            try:
                print(f"   🔵 SST indiriliyor...")
                sst_products = downloader.get_available_products(week_start, week_end, "sst")
                
                if sst_products:
                    selected = sst_products[0]
                    sst_zip = downloader.download_marmara_data(week_start, week_end, RAW_DIR, "sst")
                    
                    if sst_zip and sst_zip.suffix == ".zip":
                        # WST ürünlerinde değişken adı "sea_surface_temperature" olabilir
                        nc_file = extract_single_nc(sst_zip, RAW_DIR, selected["name"], "sea_surface_temperature")
                        if not nc_file:
                            # Fallback: bazı ürünlerde farklı ad olabilir
                            nc_file = extract_single_nc(sst_zip, RAW_DIR, selected["name"], "SST")
                        if not nc_file:
                            nc_file = extract_single_nc(sst_zip, RAW_DIR, selected["name"], "LST_in")
                        
                        if nc_file:
                            res = preprocessor.process_netcdf(nc_file)
                            if res:
                                print(f"   ✅ SST: {res['mean_value']:.2f} °C (kalite: %{res['quality_ratio']*100:.0f})")
                                completed.add(sst_key)
                            else:
                                print(f"   ⚠️ SST: Geçerli piksel bulunamadı")
                                completed.add(sst_key)
                        # ZIP temizle
                        try:
                            sst_zip.unlink()
                        except Exception:
                            pass
                    else:
                        print(f"   ⚠️ SST: İndirme başarısız")
                else:
                    print(f"   ⚠️ SST: Bu hafta ürün bulunamadı")
                    completed.add(sst_key)
            except Exception as exc:
                print(f"   ❌ SST Hata: {exc}")
                fail_count += 1

        success_count += 1
        save_progress(completed)

    # Özet
    elapsed_total = time.time() - start_time
    print(f"\n{'=' * 60}")
    print(f"🏁 İNDİRME TAMAMLANDI!")
    print(f"{'=' * 60}")
    print(f"   Toplam Hafta  : {total}")
    print(f"   Başarılı      : {success_count}")
    print(f"   Atlanan       : {skipped_count}")
    print(f"   Başarısız     : {fail_count}")
    print(f"   Toplam Süre   : {elapsed_total/60:.1f} dakika")

    # CSV durumu
    csv_path = Path("data/processed/marmara_time_series.csv")
    if csv_path.exists():
        import pandas as pd
        df = pd.read_csv(csv_path)
        chl_count = len(df[df["parameter_type"] == "chlorophyll_a"])
        sst_count = len(df[df["parameter_type"] == "sst"])
        print(f"\n📊 Veri Seti Durumu:")
        print(f"   Toplam Kayıt  : {len(df)}")
        print(f"   Klorofil-a    : {chl_count} veri noktası")
        print(f"   SST           : {sst_count} veri noktası")
    print(f"{'=' * 60}\n")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="AquaSentinel AI — Toplu Gerçek Veri İndirme")
    parser.add_argument("--start", action="store_true", help="İndirmeyi doğrudan başlat")
    parser.add_argument("--resume", action="store_true", help="Kaldığı yerden devam et")
    args = parser.parse_args()

    if args.start or args.resume:
        download_all()
    else:
        has_remaining = show_estimate()
        if has_remaining:
            print("İndirmeyi başlatmak için şu komutu çalıştırın:")
            print("  python download_real_data.py --start")
            print("\nKaldığı yerden devam etmek için:")
            print("  python download_real_data.py --resume")


if __name__ == "__main__":
    main()
