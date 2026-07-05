"""
AquaSentinel AI — Temel Agent Sınıfı (Abstract Base)

Sprint 2'de geliştirilecek AI Agent mimarisinin temel yapısını
tanımlayan abstract sınıf. Bu sınıf, tüm AquaSentinel agent'larının
uyması gereken arayüzü ve ortak işlevleri sağlar.

Mimari Kararlar:
    - Abstract Base Class (ABC) pattern: Tüm agent'lar aynı arayüzü uygular.
    - Hafıza (memory) desteği: Sprint 2'de conversation/action memory eklenecek.
    - Tool entegrasyonu: Agent'lar veri boru hattı araçlarını kullanabilir.
    - Loglama: Her agent aksiyonu otomatik loglanır.

Sprint 2 Planı:
    - MucilageRiskAgent: Risk endeksi hesaplayan agent
    - DataAnalysisAgent: Veri analizi ve anomali tespiti yapan agent
    - ReportingAgent: Risk raporları üreten agent

Kullanım (Sprint 2'de):
    >>> class MucilageRiskAgent(BaseAquaSentinelAgent):
    ...     @property
    ...     def name(self): return "MucilageRiskAgent"
    ...     def run(self, input_data): ...
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional

from src.utils import setup_logger

logger = setup_logger(__name__, log_file="logs/agents.log")


class BaseAquaSentinelAgent(ABC):
    """Tüm AquaSentinel AI agent'larının temel abstract sınıfı.

    Bu sınıf, her agent'ın uygulaması gereken arayüzü (name, description,
    run) ve ortak işlevleri (loglama, hafıza, araç yönetimi) tanımlar.

    Attributes:
        _memory: Agent'ın geçmiş aksiyonlarını tutan liste (Sprint 2).
        _tools: Agent'ın kullanabileceği araçlar sözlüğü.
        _created_at: Agent'ın oluşturulma zamanı.
    """

    def __init__(self) -> None:
        """BaseAquaSentinelAgent'ı başlatır."""
        self._memory: list[dict[str, Any]] = []
        self._tools: dict[str, callable] = {}
        self._created_at: datetime = datetime.now()

        logger.info(
            "Agent başlatıldı: %s — %s",
            self.name, self.description,
        )

    @property
    @abstractmethod
    def name(self) -> str:
        """Agent'ın benzersiz adı.

        Returns:
            str: Agent adı (ör. 'MucilageRiskAgent').
        """
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Agent'ın ne yaptığını açıklayan kısa tanım.

        Returns:
            str: Agent açıklaması.
        """
        ...

    @property
    def tools(self) -> dict[str, callable]:
        """Agent'ın erişebildiği araçlar sözlüğü.

        Returns:
            dict: Araç adı → callable eşlemesi.
        """
        return self._tools

    @abstractmethod
    def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Agent'ın ana çalışma metodu.

        Alt sınıflar bu metodu uygulayarak kendi iş mantığını tanımlar.

        Args:
            input_data: Agent'a verilen girdi verisi.

        Returns:
            dict: Agent'ın ürettiği çıktı.
        """
        ...

    def register_tool(self, tool_name: str, tool_func: callable) -> None:
        """Agent'a yeni bir araç kaydeder.

        Args:
            tool_name: Aracın adı.
            tool_func: Aracın çağrılabilir fonksiyonu.
        """
        self._tools[tool_name] = tool_func
        logger.info("Araç kaydedildi: %s → %s", self.name, tool_name)

    def log_action(
        self,
        action: str,
        result: Any,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Agent aksiyonunu hafızaya ve loga kaydeder.

        Args:
            action: Gerçekleştirilen aksiyonun açıklaması.
            result: Aksiyonun sonucu.
            metadata: Ek bilgiler (opsiyonel).
        """
        memory_entry = {
            "timestamp": datetime.now().isoformat(),
            "agent": self.name,
            "action": action,
            "result": str(result)[:500],  # Hafıza tasarrufu
            "metadata": metadata or {},
        }

        self._memory.append(memory_entry)

        logger.info(
            "[%s] Aksiyon: %s → Sonuç: %s",
            self.name, action, str(result)[:200],
        )

    def get_memory(self, last_n: Optional[int] = None) -> list[dict[str, Any]]:
        """Agent'ın hafızasındaki geçmiş aksiyonları döndürür.

        Args:
            last_n: Döndürülecek son N aksiyon. None ise tümünü döndürür.

        Returns:
            list[dict]: Geçmiş aksiyon kayıtları.
        """
        if last_n is not None:
            return self._memory[-last_n:]
        return self._memory.copy()

    def clear_memory(self) -> None:
        """Agent hafızasını temizler."""
        count = len(self._memory)
        self._memory.clear()
        logger.info("[%s] Hafıza temizlendi (%d kayıt silindi).", self.name, count)

    def __repr__(self) -> str:
        """Agent'ın string temsilini döndürür."""
        return (
            f"<{self.__class__.__name__}("
            f"name='{self.name}', "
            f"tools={len(self._tools)}, "
            f"memory={len(self._memory)}"
            f")>"
        )
