"""
AquaSentinel AI — MucilageRiskAgent (Müsilaj Risk Hesaplama)

Bu modül, eğitilmiş makine öğrenmesi modelini yükleyerek anlık/güncel veriler için
müsilaj risk olasılığı ve seviyesi hesaplayan MucilageRiskAgent'ı tanımlar.
"""

from pathlib import Path
from typing import Any, Optional

from src.agents.base_agent import BaseAquaSentinelAgent
from src.models.risk_model import MucilageRiskModel
from src.utils import setup_logger

logger = setup_logger(__name__, log_file="logs/risk_agent.log")


class MucilageRiskAgent(BaseAquaSentinelAgent):
    """Müsilaj riskini tahmin eden makine öğrenmesi entegreli agent sınıfı."""

    @property
    def name(self) -> str:
        return "MucilageRiskAgent"

    @property
    def description(self) -> str:
        return "Eğitilen makine öğrenmesi modelini kullanarak güncel uydu verileri bazında müsilaj risk endeksi üreten agent."

    def __init__(self, model_path: Optional[str | Path] = None) -> None:
        """MucilageRiskAgent'ı başlatır.

        Args:
            model_path: Model dosya yolu (.joblib).
        """
        super().__init__()
        self.model_path = model_path or "models/mucilage_risk_model.joblib"
        self.model = MucilageRiskModel(model_path=self.model_path)
        
        # Model dosyasını yüklemeyi dene, yoksa uyarı ver
        if not self.model.load():
            logger.warning("Eğitilmiş model dosyası yüklenemedi. Tahmin yapmadan önce model eğitilmelidir.")

        # Araçları (Tools) kaydet
        self.register_tool("predict_risk", self.predict_risk)

    def predict_risk(self, sst: float, sst_trend: float, chl: float, chl_trend: float) -> dict[str, Any]:
        """Eğitilmiş ML modelini çağırarak risk hesaplar.

        Args:
            sst: Deniz yüzeyi sıcaklığı (°C)
            sst_trend: Sıcaklık artış hızı (°C/gün)
            chl: Klorofil-a konsantrasyonu (mg/m³)
            chl_trend: Klorofil artış hızı (mg/m³/gün)

        Returns:
            dict: Risk yüzdesi ve seviyesi.
        """
        try:
            # Model diskte yoksa veya yüklenemediyse, otomatik yüklemeyi/eğitmeyi denemek için kontrol et
            if self.model.model is None:
                if not self.model.load():
                    raise RuntimeError("Eğitilmiş model yüklenemedi. Lütfen önce modeli eğitin.")

            risk_result = self.model.predict_risk(sst, sst_trend, chl, chl_trend)
            self.log_action("predict_risk", risk_result, {
                "sst": sst, "sst_trend": sst_trend, "chl": chl, "chl_trend": chl_trend
            })
            return risk_result
        except Exception as exc:
            logger.error("Risk tahmini sırasında hata oluştu: %s", exc, exc_info=True)
            return {
                "risk_percentage": 0.0,
                "risk_level": "Unknown",
                "error": str(exc)
            }

    def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Girdi verilerine göre risk tahminini yürütür.

        Args:
            input_data: {"sst": float, "sst_trend": float, "chlorophyll_a": float, "chl_trend": float}
                        veya {"latest_metrics": dict}

        Returns:
            dict: Risk analizi sonucu.
        """
        metrics = input_data.get("latest_metrics", input_data)
        logger.info("Müsilaj risk hesaplaması başlatıldı. Girdiler: %s", metrics)

        # Girdileri kontrol et ve ayıkla
        sst = metrics.get("sst")
        sst_trend = metrics.get("sst_trend", 0.0)
        chl = metrics.get("chlorophyll_a", metrics.get("chlorophyll"))
        chl_trend = metrics.get("chl_trend", 0.0)

        if sst is None or chl is None:
            raise ValueError("Risk tahmini için 'sst' ve 'chlorophyll_a' parametreleri zorunludur.")

        risk_prediction = self.predict_risk(float(sst), float(sst_trend), float(chl), float(chl_trend))

        output = {
            "status": "success",
            "prediction": risk_prediction
        }

        logger.info("Risk hesaplaması tamamlandı: %s (%s%%)", 
                    risk_prediction.get("risk_level"), risk_prediction.get("risk_percentage"))
        return output
