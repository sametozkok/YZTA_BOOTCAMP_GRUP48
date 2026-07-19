"""
AquaSentinel AI — Agent Modülleri Birim Testleri
"""

import os
from pathlib import Path
import pytest
import numpy as np
import pandas as pd

from src.agents.analyst_agent import DataAnalysisAgent
from src.agents.risk_agent import MucilageRiskAgent
from src.agents.reporting_agent import ReportingAgent
from src.models.risk_model import MucilageRiskModel
from src.data.preprocessor import MarmaraDataPreprocessor


@pytest.fixture
def mock_csv_file(tmp_path):
    """Testler için küçük ölçekli sahte zaman serisi CSV dosyası üretir."""
    processed_dir = tmp_path / "processed"
    processor = MarmaraDataPreprocessor(processed_dir=processed_dir)
    csv_file = processor.generate_mock_data("2024-06-01", "2024-06-15", interval_days=3)
    return csv_file


@pytest.fixture
def trained_model_file(mock_csv_file, tmp_path):
    """Testler için geçici bir eğitilmiş model dosyası hazırlar."""
    model_path = tmp_path / "mucilage_risk_model.joblib"
    model = MucilageRiskModel(model_path=model_path)
    model.train(mock_csv_file)
    return model_path


class TestDataAnalysisAgent:
    """DataAnalysisAgent sınıfını test eder."""

    def test_agent_properties(self):
        """Agent adı ve açıklaması doğru tanımlanmış olmalı."""
        agent = DataAnalysisAgent()
        assert agent.name == "DataAnalysisAgent"
        assert "Zaman serisi" in agent.description
        assert "calculate_trends" in agent.tools
        assert "detect_anomalies" in agent.tools

    def test_run_analysis_produces_results(self, mock_csv_file):
        """Agent'ın çalıştırılması analiz çıktısı üretmeli."""
        agent = DataAnalysisAgent()
        result = agent.run({"csv_path": mock_csv_file})
        
        assert result["status"] == "success"
        assert "latest_metrics" in result
        assert "anomalies_summary" in result
        
        metrics = result["latest_metrics"]
        assert "sst" in metrics
        assert "chlorophyll_a" in metrics
        assert "sst_trend" in metrics
        assert "chl_trend" in metrics
        
        # Hafıza (memory) kaydı kontrolü
        memory = agent.get_memory()
        assert len(memory) > 0
        assert memory[0]["agent"] == "DataAnalysisAgent"


class TestMucilageRiskAgent:
    """MucilageRiskAgent sınıfını test eder."""

    def test_agent_properties(self, trained_model_file):
        """Agent özellikleri ve modeli doğru yüklenmeli."""
        agent = MucilageRiskAgent(model_path=trained_model_file)
        assert agent.name == "MucilageRiskAgent"
        assert "predict_risk" in agent.tools

    def test_run_risk_agent_predicts(self, trained_model_file):
        """Agent girdi parametreleri için risk tahmini yapabilmeli."""
        agent = MucilageRiskAgent(model_path=trained_model_file)
        
        input_data = {
            "sst": 23.5,
            "sst_trend": 0.2,
            "chlorophyll_a": 6.8,
            "chl_trend": 0.15
        }
        
        result = agent.run(input_data)
        assert result["status"] == "success"
        assert "prediction" in result
        assert "risk_percentage" in result["prediction"]
        assert "risk_level" in result["prediction"]


class TestReportingAgent:
    """ReportingAgent sınıfını test eder."""

    def test_agent_properties(self):
        """Agent adı ve aracı doğru tanımlanmış olmalı."""
        agent = ReportingAgent()
        assert agent.name == "ReportingAgent"
        assert "generate_report" in agent.tools

    def test_generate_report_writes_file(self, tmp_path):
        """Rapor üretimi dosya olarak diske yazılmalı (çevrimdışı modda)."""
        agent = ReportingAgent()
        
        analysis_data = {
            "latest_metrics": {
                "date": "2024-06-15",
                "sst": 24.1,
                "sst_trend": 0.15,
                "chlorophyll_a": 5.4,
                "chl_trend": 0.08
            },
            "anomalies_summary": {
                "anomalies": []
            }
        }
        
        risk_data = {
            "prediction": {
                "risk_percentage": 68.5,
                "risk_level": "High"
            }
        }
        
        output_file = tmp_path / "reports" / "mucilage_risk_report.md"
        
        report_text = agent.generate_report(
            analysis_data=analysis_data,
            risk_data=risk_data,
            output_path=output_file
        )
        
        assert output_file.exists()
        assert "# 🌊 Marmara Denizi Müsilaj Risk Raporu" in report_text
        assert "68.5" in report_text
        assert "High" in report_text
