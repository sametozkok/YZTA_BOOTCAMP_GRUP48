"""
AquaSentinel AI — Sprint 3 Model Performans Görselleştirme Betiği

Bu betik, Sprint 3 kapsamında eğitilen gelişmiş makine öğrenmesi modelinin
çapraz doğrulama (Cross-Validation) metriklerini, özellik önem derecelerini (Feature Importances)
ve algoritma karşılaştırmalarını yüksek çözünürlüklü grafik olarak 'images/sprint3_model_performance.png'
dosyasına kaydeder.
"""

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

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

def generate_chart():
    # Dark Mode Tema Ayarları
    plt.style.use('dark_background')
    fig, axes = plt.subplots(1, 2, figsize=(14, 6), dpi=300)
    fig.patch.set_facecolor('#0f172a')  # Dark Slate Background

    # 1. GRAFİK: Çoklu Model Karşılaştırması (5-Fold CV Accuracy)
    models = ['Random Forest\n(Seçilen)', 'SVM (RBF)', 'Logistic\nRegression', 'Gradient\nBoosting']
    cv_scores = [93.33, 95.56, 93.33, 84.44]
    colors = ['#06b6d4', '#3b82f6', '#8b5cf6', '#64748b']

    ax1 = axes[0]
    ax1.set_facecolor('#1e293b')
    bars = ax1.bar(models, cv_scores, color=colors, width=0.55, edgecolor='#334155', linewidth=1.5)
    ax1.set_ylim(60, 105)
    ax1.set_title('Modellerin 5-Fold Cross-Validation Başarısı (%)', fontsize=12, fontweight='bold', color='#f8fafc', pad=12)
    ax1.set_ylabel('Çapraz Doğrulama Doğruluğu (%)', fontsize=10, color='#94a3b8')
    ax1.grid(axis='y', linestyle='--', alpha=0.3, color='#475569')

    # Değer etiketleri ekle
    for bar in bars:
        height = bar.get_height()
        ax1.annotate(f'%{height:.2f}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 5),
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=10, fontweight='bold', color='#38bdf8')

    # 2. GRAFİK: Özellik Önem Dereceleri (Feature Importances - 7 Özellik)
    features = [
        'sst_trend (Sıcaklık İvmesi)',
        'sst (Deniz Sıcaklığı)',
        'sst_chl_product (Etkileşim Sinerjisi)',
        'chl_trend (Klorofil İvmesi)',
        'chl_ma3 (Klorofil MA3)',
        'chlorophyll_a (Klorofil Yoğunluğu)',
        'sst_ma3 (Sıcaklık MA3)'
    ]
    importances = [0.2565, 0.2447, 0.1593, 0.1539, 0.0879, 0.0682, 0.0295]

    # Ters sırala (en yüksek üstte dursun)
    features.reverse()
    importances.reverse()

    ax2 = axes[1]
    ax2.set_facecolor('#1e293b')
    bars2 = ax2.barh(features, [imp * 100 for imp in importances], color='#10b981', height=0.6, edgecolor='#059669', linewidth=1.2)
    ax2.set_xlim(0, 32)
    ax2.set_title('Gelişmiş Model Özellik Önem Dereceleri (%)', fontsize=12, fontweight='bold', color='#f8fafc', pad=12)
    ax2.set_xlabel('Önem Oranı (%)', fontsize=10, color='#94a3b8')
    ax2.grid(axis='x', linestyle='--', alpha=0.3, color='#475569')

    for bar in bars2:
        width = bar.get_width()
        ax2.annotate(f'%{width:.2f}',
                    xy=(width, bar.get_y() + bar.get_height() / 2),
                    xytext=(6, 0),
                    textcoords="offset points",
                    ha='left', va='center', fontsize=9, fontweight='bold', color='#6ee7b7')

    plt.suptitle('AquaSentinel AI — Sprint 3 Model Performans & Özellik Analizi', fontsize=15, fontweight='bold', color='#38bdf8', y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.94])

    # İlgili klasöre kaydet
    output_dir = Path("images")
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "sprint3_model_performance.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()

    print(f"[+] Performans grafiği başarıyla oluşturuldu ve kaydedildi: {output_path}")

if __name__ == "__main__":
    generate_chart()
