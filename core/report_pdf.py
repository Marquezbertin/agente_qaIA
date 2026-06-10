"""
QA Agent - Geracao de Relatorios PDF
=====================================
Gera relatorios PDF a partir dos dados de QA (bugs, testes, execucoes).
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

REPORTS_DIR = Path(__file__).parent.parent / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def _strip_emoji(text: str) -> str:
    """Remove emoji characters that are not supported by Helvetica"""
    emoji_pattern = re.compile(
        "[\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "\U0001F900-\U0001F9FF"
        "\U00002600-\U000026FF"
        "\U00002700-\U000027BF"
        "\U0001FA00-\U0001FA6F"
        "\U0001FA70-\U0001FAFF"
        "\U00002600-\U000026FF"
        "\u2705\u274c\u274e"
        "\u2b50\ufe0f]+",
        flags=re.UNICODE
    )
    return emoji_pattern.sub("", text)


def generate_pdf_report(data: Dict[str, Any], output_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Gera um relatorio PDF a partir dos dados fornecidos.
    
    Args:
        data: Dicionario com dados do relatorio
        output_path: Caminho para salvar o PDF (opcional)
    
    Returns:
        Dict com resultado da operacao
    """
    try:
        from fpdf import FPDF

        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = REPORTS_DIR / f"relatorio_qa_{timestamp}.pdf"

        pdf = FPDF()
        pdf.add_page()

        pdf.set_font("Helvetica", "B", 20)
        title = _strip_emoji(data.get("title", "Relatorio de QA"))
        pdf.cell(0, 15, title, new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.ln(5)

        pdf.set_font("Helvetica", "", 10)
        report_date = _strip_emoji(data.get("date", datetime.now().strftime("%Y-%m-%d %H:%M")))
        pdf.cell(0, 8, f"Data: {report_date}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)

        summary = data.get("summary", {})
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, "Resumo Executivo", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 12)

        metrics = [
            ("Total de Testes", summary.get("total_tests", 0)),
            ("Passaram", summary.get("passed", 0)),
            ("Falharam", summary.get("failed", 0)),
            ("Taxa de Sucesso", summary.get("success_rate", "N/A")),
            ("Bugs Abertos", summary.get("open_bugs", 0)),
            ("Cobertura", summary.get("coverage", "N/A")),
        ]
        for label, value in metrics:
            pdf.cell(0, 8, f"{label}: {value}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)

        bugs = data.get("bugs", [])
        if bugs:
            pdf.set_font("Helvetica", "B", 14)
            pdf.cell(0, 10, f"Bugs ({len(bugs)})", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 10)
            for bug in bugs[:20]:
                sev = bug.get("severity", "medium")
                sev_label = {"critical": "[CRIT]", "high": "[HIGH]", "medium": "[MED]", "low": "[LOW]"}.get(sev, "[MED]")
                bug_text = f"{sev_label} #{bug.get('id', '?')} {_strip_emoji(str(bug.get('title', '?')))} [{bug.get('status', 'open')}]"
                pdf.set_font("Helvetica", "B", 10)
                pdf.cell(0, 7, bug_text, new_x="LMARGIN", new_y="NEXT")
                if bug.get("description"):
                    pdf.set_font("Helvetica", "", 9)
                    desc = _strip_emoji(bug["description"][:200])
                    pdf.multi_cell(0, 6, desc)
            pdf.ln(3)

        test_results = data.get("test_results", [])
        if test_results:
            pdf.set_font("Helvetica", "B", 14)
            pdf.cell(0, 10, f"Resultados de Testes ({len(test_results)})", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 10)
            for tr in test_results[:20]:
                status_str = "[OK]" if tr.get("failed", 0) == 0 else "[FAIL]"
                text = f"{status_str} {tr.get('test_path', '?')} - Passed: {tr.get('passed', 0)} Failed: {tr.get('failed', 0)}"
                pdf.cell(0, 7, text, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(3)

        features = data.get("features", [])
        if features:
            pdf.set_font("Helvetica", "B", 14)
            pdf.cell(0, 10, f"Features ({len(features)})", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 10)
            for feat in features[:10]:
                title = _strip_emoji(str(feat.get("title", "?")))
                pdf.cell(0, 7, f"#{feat.get('id', '?')} {title} [{feat.get('status', 'draft')}]",
                         new_x="LMARGIN", new_y="NEXT")

        pdf.ln(10)
        pdf.set_font("Helvetica", "I", 8)
        pdf.cell(0, 5, f"Gerado por QA Agent em {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                 new_x="LMARGIN", new_y="NEXT", align="C")

        pdf.output(str(output_path))

        return {
            "success": True,
            "path": str(output_path),
            "pages": pdf.pages_count,
            "message": f"PDF salvo em: {output_path}"
        }

    except ImportError:
        return {"success": False, "error": "fpdf2 nao instalado. pip install fpdf2"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def generate_pdf_from_qa_data(bugs: List[Dict] = None, test_results: List[Dict] = None,
                                features: List[Dict] = None) -> Dict[str, Any]:
    """Gera PDF automaticamente a partir dos dados do QA Agent"""
    summary = {
        "total_tests": sum(tr.get("passed", 0) + tr.get("failed", 0) for tr in (test_results or [])),
        "passed": sum(tr.get("passed", 0) for tr in (test_results or [])),
        "failed": sum(tr.get("failed", 0) for tr in (test_results or [])),
        "open_bugs": len([b for b in (bugs or []) if b.get("status") == "open"]),
    }
    total = summary["passed"] + summary["failed"]
    summary["success_rate"] = f"{(summary['passed'] / total * 100):.1f}%" if total > 0 else "N/A"

    data = {
        "title": "QA Agent - Relatorio Automatico",
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "summary": summary,
        "bugs": bugs or [],
        "test_results": test_results or [],
        "features": features or [],
    }
    return generate_pdf_report(data)
