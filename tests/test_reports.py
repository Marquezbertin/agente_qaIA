"""
Testes para geracao de relatorios
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()


class TestPDFReport:
    def test_generate_pdf_report(self, tmp_path):
        from core.report_pdf import generate_pdf_report
        data = {
            "title": "Test Report",
            "date": "2024-01-01",
            "summary": {
                "total_tests": 10,
                "passed": 8,
                "failed": 2,
                "success_rate": "80.0%",
                "open_bugs": 3,
            },
            "bugs": [
                {"id": 1, "title": "Bug 1", "severity": "high", "status": "open", "description": "Test bug"},
                {"id": 2, "title": "Bug 2", "severity": "low", "status": "closed"},
            ],
            "test_results": [
                {"test_path": "tests/api/test_a.py", "passed": 5, "failed": 0},
                {"test_path": "tests/api/test_b.py", "passed": 3, "failed": 2},
            ],
        }
        output = tmp_path / "test_report.pdf"
        result = generate_pdf_report(data, output_path=output)
        if not result.get("success"):
            error = result.get("error", "")
            if "fpdf2" in error:
                return
        assert result.get("success"), f"PDF generation failed: {result.get('error', 'unknown')}"
        assert output.exists()

    def test_generate_pdf_from_qa_data(self):
        from core.report_pdf import generate_pdf_from_qa_data
        result = generate_pdf_from_qa_data(
            bugs=[{"id": 1, "title": "Bug", "severity": "medium", "status": "open"}],
            test_results=[{"test_path": "test_x.py", "passed": 5, "failed": 1}],
        )
        if not result.get("success"):
            error = result.get("error", "")
            if "fpdf2" in error:
                return
        assert result.get("success"), f"PDF generation failed: {result.get('error', 'unknown')}"


class TestHTMLReport:
    def test_report_generator_imports(self):
        from core.report_generator import ReportGenerator
        from config.settings import AgentConfig
        config = AgentConfig()
        gen = ReportGenerator(config)
        assert gen is not None
