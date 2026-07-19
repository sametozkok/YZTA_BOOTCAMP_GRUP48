"""
AquaSentinel AI — Çoklu Model Karşılaştırma Betiği

Bu betik, müsilaj risk tahmin modeli için birden fazla ML algoritmasını eğitir,
test eder ve performans metriklerini yan yana karşılaştırır.

Karşılaştırılan Modeller:
    1. Random Forest (Baseline)
    2. Gradient Boosting
    3. Logistic Regression
    4. SVM (RBF Kernel)

Metrikler: Accuracy, Precision, Recall, F1-Score, Feature Importances
"""

import sys
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix,
)
from sklearn.preprocessing import StandardScaler

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

warnings.filterwarnings("ignore")


def prepare_dataset(csv_path: str) -> tuple:
    """Zaman serisi CSV'yi model eğitimi için hazırlar.

    Returns:
        (X, y, merged_df): Özellikler, etiketler ve tam birleştirilmiş DataFrame
    """
    df = pd.read_csv(csv_path)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    # Parametre ayırma
    df_chl = df[df["parameter_type"] == "chlorophyll_a"].copy()
    df_sst = df[df["parameter_type"] == "sst"].copy()

    # Tarih bazında birleştir
    merged = pd.merge(
        df_sst[["date", "mean_value"]].rename(columns={"mean_value": "sst"}),
        df_chl[["date", "mean_value"]].rename(columns={"mean_value": "chlorophyll_a"}),
        on="date",
        how="inner",
    )

    if len(merged) < 5:
        raise ValueError(f"Yeterli veri noktası yok: {len(merged)} < 5")

    # Gradyan/Trend hesaplama
    merged["days_diff"] = merged["date"].diff().dt.days.fillna(3.0)
    merged["sst_diff"] = merged["sst"].diff().fillna(0.0)
    merged["sst_trend"] = merged["sst_diff"] / merged["days_diff"]
    merged["chl_diff"] = merged["chlorophyll_a"].diff().fillna(0.0)
    merged["chl_trend"] = merged["chl_diff"] / merged["days_diff"]

    # Gürültü temizleme: 3-gözlemlik hareketli ortalama
    merged["sst_trend"] = merged["sst_trend"].rolling(window=3, min_periods=1).mean()
    merged["chl_trend"] = merged["chl_trend"].rolling(window=3, min_periods=1).mean()

    # Etiketleme — biyolojik eşikler
    merged["risk_label"] = (
        (merged["sst"] > 22.0)
        & (merged["sst_trend"] > 0)
        & (merged["chlorophyll_a"] > 5.0)
        & (merged["chl_trend"] > 0)
    ).astype(int)

    features = ["sst", "sst_trend", "chlorophyll_a", "chl_trend"]
    X = merged[features].copy()
    y = merged["risk_label"].copy()

    return X, y, merged


def run_comparison(csv_path: str = "data/processed/marmara_time_series.csv"):
    """Tüm modelleri eğitir ve karşılaştırır."""

    print("\n" + "=" * 70)
    print("🔬 AquaSentinel AI — Çoklu Model Karşılaştırma Raporu")
    print("=" * 70)

    # 1. Veri Hazırlığı
    X, y, merged = prepare_dataset(csv_path)

    unique_classes = np.unique(y)
    if len(unique_classes) < 2:
        print("\n" + "=" * 70)
        print("⚠️ HATA: Veri kümesinde sadece tek bir sınıf (risk_label=0) bulundu.")
        print("Modelleri karşılaştırmak için en az iki farklı sınıf (0 ve 1) gereklidir.")
        print("Lütfen veri kümesine müsilaj dönemlerine ait (örneğin sıcaklık > 22°C ve klorofil > 5.0 mg/m³)")
        print("veri noktaları ekleyin veya test amaçlı mock veri üretmek için data/processed/marmara_time_series.csv")
        print("dosyasını silerek 'python run_sprint2.py' betiğini çalıştırın.")
        print("=" * 70 + "\n")
        return

    print(f"\n📊 Veri Seti Bilgileri:")
    print(f"   Toplam Veri Noktası : {len(X)}")
    print(f"   Özellik Sayısı     : {X.shape[1]}")
    print(f"   Pozitif Sınıf (1)  : {y.sum()} ({y.sum()/len(y)*100:.1f}%)")
    print(f"   Negatif Sınıf (0)  : {(y == 0).sum()} ({(y==0).sum()/len(y)*100:.1f}%)")

    # Özellik istatistikleri
    print(f"\n📈 Özellik İstatistikleri:")
    print(X.describe().round(4).to_string())

    # 2. Train/Test Split
    # Sınıf dengesini kontrol et
    unique_classes = np.unique(y)
    can_stratify = len(unique_classes) > 1 and all(np.sum(y == c) >= 2 for c in unique_classes)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42,
        stratify=y if can_stratify else None
    )

    print(f"\n🔀 Train/Test Bölünmesi:")
    print(f"   Eğitim Seti : {len(X_train)} ({y_train.sum()} pozitif)")
    print(f"   Test Seti   : {len(X_test)} ({y_test.sum()} pozitif)")

    # 3. Ölçeklendirme (Logistic Regression ve SVM için gerekli)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # 4. Model Tanımları
    models = {
        "Random Forest": {
            "model": RandomForestClassifier(
                n_estimators=100, max_depth=5,
                random_state=42, class_weight="balanced"
            ),
            "needs_scaling": False,
        },
        "Gradient Boosting": {
            "model": GradientBoostingClassifier(
                n_estimators=100, max_depth=3,
                learning_rate=0.1, random_state=42
            ),
            "needs_scaling": False,
        },
        "Logistic Regression": {
            "model": LogisticRegression(
                max_iter=1000, class_weight="balanced",
                random_state=42
            ),
            "needs_scaling": True,
        },
        "SVM (RBF)": {
            "model": SVC(
                kernel="rbf", probability=True,
                class_weight="balanced", random_state=42
            ),
            "needs_scaling": True,
        },
    }

    # 5. Eğitim ve Değerlendirme
    results = []

    for name, config in models.items():
        print(f"\n{'─' * 60}")
        print(f"🤖 Model: {name}")
        print(f"{'─' * 60}")

        clf = config["model"]
        use_scaled = config["needs_scaling"]

        X_tr = X_train_scaled if use_scaled else X_train
        X_te = X_test_scaled if use_scaled else X_test

        # Eğitim
        clf.fit(X_tr, y_train)

        # Test tahmini
        y_pred = clf.predict(X_te)
        if hasattr(clf, "predict_proba"):
            proba = clf.predict_proba(X_te)
            y_prob = proba[:, 1] if proba.shape[1] > 1 else np.zeros(len(X_te))
        else:
            y_prob = None

        # Metrikler
        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, zero_division=0)
        rec = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)

        # Cross-Validation (5-fold)
        cv_folds = min(5, min(np.bincount(y)))
        if cv_folds >= 2 and can_stratify:
            skf = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=42)
            X_cv = scaler.fit_transform(X) if use_scaled else X
            cv_scores = cross_val_score(clf, X_cv, y, cv=skf, scoring="accuracy")
            cv_mean = cv_scores.mean()
            cv_std = cv_scores.std()
        else:
            cv_mean = acc
            cv_std = 0.0

        # Confusion Matrix
        cm = confusion_matrix(y_test, y_pred)

        print(f"   Accuracy  : {acc*100:.2f}%")
        print(f"   Precision : {prec*100:.2f}%")
        print(f"   Recall    : {rec*100:.2f}%")
        print(f"   F1-Score  : {f1*100:.2f}%")
        print(f"   CV Acc    : {cv_mean*100:.2f}% (+/- {cv_std*100:.2f}%)")
        print(f"   Confusion Matrix:")
        print(f"     TN={cm[0][0]:3d}  FP={cm[0][1] if cm.shape[1] > 1 else 0:3d}")
        if cm.shape[0] > 1:
            print(f"     FN={cm[1][0]:3d}  TP={cm[1][1] if cm.shape[1] > 1 else 0:3d}")

        # Feature Importances (varsa)
        if hasattr(clf, "feature_importances_"):
            fi = dict(zip(X.columns.tolist(), clf.feature_importances_.tolist()))
            print(f"   Feature Importances:")
            for feat, imp in sorted(fi.items(), key=lambda x: x[1], reverse=True):
                bar = "█" * int(imp * 40)
                print(f"     {feat:<15} {imp:.4f} {bar}")
        elif hasattr(clf, "coef_"):
            coefs = dict(zip(X.columns.tolist(), np.abs(clf.coef_[0]).tolist()))
            print(f"   Feature Coefficients (abs):")
            for feat, imp in sorted(coefs.items(), key=lambda x: x[1], reverse=True):
                bar = "█" * int(imp / max(coefs.values()) * 20)
                print(f"     {feat:<15} {imp:.4f} {bar}")
            fi = coefs
        else:
            fi = {}

        results.append({
            "model_name": name,
            "accuracy": acc,
            "precision": prec,
            "recall": rec,
            "f1_score": f1,
            "cv_accuracy_mean": cv_mean,
            "cv_accuracy_std": cv_std,
            "confusion_matrix": cm.tolist(),
            "feature_importances": fi,
            "trained_model": clf,
            "needs_scaling": use_scaled,
        })

    # 6. Karşılaştırma Tablosu
    print("\n\n" + "=" * 70)
    print("📋 MODEL KARŞILAŞTIRMA TABLOSU")
    print("=" * 70)

    header = f"{'Model':<25} {'Acc':>7} {'Prec':>7} {'Recall':>7} {'F1':>7} {'CV Acc':>10}"
    print(header)
    print("─" * 70)

    best_f1 = -1
    best_model_name = ""
    best_model_obj = None
    best_needs_scaling = False

    for r in results:
        line = (
            f"{r['model_name']:<25} "
            f"{r['accuracy']*100:>6.2f}% "
            f"{r['precision']*100:>6.2f}% "
            f"{r['recall']*100:>6.2f}% "
            f"{r['f1_score']*100:>6.2f}% "
            f"{r['cv_accuracy_mean']*100:>6.2f}%+/-{r['cv_accuracy_std']*100:.1f}%"
        )
        print(line)

        # En iyi modeli F1 score ile seç (çünkü dengesiz veri seti)
        if r["f1_score"] > best_f1:
            best_f1 = r["f1_score"]
            best_model_name = r["model_name"]
            best_model_obj = r["trained_model"]
            best_needs_scaling = r["needs_scaling"]

    print("─" * 70)
    print(f"\n🏆 En İyi Model: {best_model_name} (F1: {best_f1*100:.2f}%)")

    # 7. En iyi modeli kaydet
    model_save_path = Path("models/mucilage_risk_model.joblib")
    model_save_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(best_model_obj, model_save_path)
    print(f"   Kaydedildi: {model_save_path}")

    if best_needs_scaling:
        scaler_path = Path("models/feature_scaler.joblib")
        joblib.dump(scaler, scaler_path)
        print(f"   Scaler kaydedildi: {scaler_path}")

    # 8. Tüm sonuçları CSV olarak da kaydet
    summary_df = pd.DataFrame([{
        "Model": r["model_name"],
        "Accuracy": round(r["accuracy"] * 100, 2),
        "Precision": round(r["precision"] * 100, 2),
        "Recall": round(r["recall"] * 100, 2),
        "F1_Score": round(r["f1_score"] * 100, 2),
        "CV_Accuracy": round(r["cv_accuracy_mean"] * 100, 2),
    } for r in results])

    summary_path = Path("data/processed/model_comparison_results.csv")
    summary_df.to_csv(summary_path, index=False, encoding="utf-8")
    print(f"   Karşılaştırma tablosu: {summary_path}")

    print("\n" + "=" * 70)
    print("✅ Çoklu Model Karşılaştırması Tamamlandı!")
    print("=" * 70 + "\n")

    return results


if __name__ == "__main__":
    run_comparison()
