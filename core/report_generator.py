"""
Report Generator - Gerador de Relatorios
=========================================

Gera relatorios detalhados de execucao de testes
em diversos formatos (HTML, PDF, Markdown).
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from string import Template

from config.settings import AgentConfig, AGENT_ROOT


class ReportGenerator:
    """
    Gerador de relatorios de testes.

    Responsabilidades:
    - Gerar relatorios de execucao
    - Calcular metricas e tendencias
    - Exportar em multiplos formatos
    - Criar dashboards de status
    """

    HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QA Agent - Relatorio de Testes</title>
    <style>
        :root {
            --primary: #2563eb;
            --success: #22c55e;
            --danger: #ef4444;
            --warning: #f59e0b;
            --bg: #f8fafc;
            --text: #1e293b;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
            padding: 2rem;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { color: var(--primary); margin-bottom: 0.5rem; }
        .subtitle { color: #64748b; margin-bottom: 2rem; }
        .card {
            background: white;
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }
        .stat {
            text-align: center;
            padding: 1.5rem;
        }
        .stat-value {
            font-size: 2.5rem;
            font-weight: 700;
        }
        .stat-label {
            color: #64748b;
            font-size: 0.875rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .passed { color: var(--success); }
        .failed { color: var(--danger); }
        .skipped { color: var(--warning); }
        .progress-bar {
            height: 8px;
            background: #e2e8f0;
            border-radius: 4px;
            overflow: hidden;
            margin-top: 1rem;
        }
        .progress-fill {
            height: 100%;
            background: var(--success);
            transition: width 0.3s;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 0.75rem 1rem;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
        }
        th {
            background: #f1f5f9;
            font-weight: 600;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .badge {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
        }
        .badge-passed { background: #dcfce7; color: #166534; }
        .badge-failed { background: #fee2e2; color: #991b1b; }
        .badge-skipped { background: #fef3c7; color: #92400e; }
        .badge-error { background: #fee2e2; color: #991b1b; }
        .section-title {
            font-size: 1.25rem;
            font-weight: 600;
            margin-bottom: 1rem;
            color: var(--text);
        }
        .footer {
            text-align: center;
            color: #64748b;
            font-size: 0.875rem;
            margin-top: 2rem;
            padding-top: 2rem;
            border-top: 1px solid #e2e8f0;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>QA Agent - Relatorio de Testes</h1>
        <p class="subtitle">Gerado em ${timestamp} | Ambiente: ${environment}</p>

        <div class="stats-grid">
            <div class="card stat">
                <div class="stat-value">${total}</div>
                <div class="stat-label">Total de Testes</div>
            </div>
            <div class="card stat">
                <div class="stat-value passed">${passed}</div>
                <div class="stat-label">Passou</div>
            </div>
            <div class="card stat">
                <div class="stat-value failed">${failed}</div>
                <div class="stat-label">Falhou</div>
            </div>
            <div class="card stat">
                <div class="stat-value skipped">${skipped}</div>
                <div class="stat-label">Pulado</div>
            </div>
        </div>

        <div class="card">
            <h2 class="section-title">Taxa de Sucesso: ${success_rate}%</h2>
            <div class="progress-bar">
                <div class="progress-fill" style="width: ${success_rate}%"></div>
            </div>
        </div>

        <div class="card">
            <h2 class="section-title">Detalhes dos Testes</h2>
            <table>
                <thead>
                    <tr>
                        <th>Teste</th>
                        <th>Status</th>
                        <th>Duracao</th>
                        <th>Mensagem</th>
                    </tr>
                </thead>
                <tbody>
                    ${test_rows}
                </tbody>
            </table>
        </div>

        ${failed_details}

        <div class="footer">
            <p>Gerado por QA Agent | ${period}</p>
        </div>
    </div>
</body>
</html>'''

    MARKDOWN_TEMPLATE = '''# QA Agent - Relatorio de Testes

**Gerado em:** ${timestamp}
**Ambiente:** ${environment}
**Periodo:** ${period}

## Resumo

| Metrica | Valor |
|---------|-------|
| Total de Testes | ${total} |
| Passou | ${passed} |
| Falhou | ${failed} |
| Pulado | ${skipped} |
| Taxa de Sucesso | ${success_rate}% |
| Duracao Total | ${duration}s |

## Testes por Categoria

${category_table}

## Detalhes dos Testes

${test_details}

## Testes que Falharam

${failed_details}

## Recomendacoes

${recommendations}

---
*Gerado automaticamente por QA Agent*
'''

    def __init__(self, config: AgentConfig):
        self.config = config
        self.reports_dir = config.reports_dir
        self.reports_dir.mkdir(exist_ok=True)

    def generate_report(
        self,
        period: str = "today",
        environment: Optional[str] = None
    ) -> Dict[str, Any]:
        """Gera dados do relatorio"""
        # Determinar periodo
        start_date, end_date = self._parse_period(period)

        # Coletar resultados do periodo
        results = self._collect_results(start_date, end_date, environment)

        # Agregar estatisticas
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "period": period,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "environment": environment or "all",
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": 0,
            "success_rate": 0.0,
            "duration": 0.0,
            "by_category": {},
            "by_suite": {},
            "tests": [],
            "failed_tests": [],
            "recommendations": []
        }

        for result in results:
            report_data["total_tests"] += result.get("total", 0)
            report_data["passed"] += result.get("passed", 0)
            report_data["failed"] += result.get("failed", 0)
            report_data["skipped"] += result.get("skipped", 0)
            report_data["errors"] += result.get("errors", 0)
            report_data["duration"] += result.get("duration", 0)

            # Por suite
            suite = result.get("suite_name", "unknown")
            if suite not in report_data["by_suite"]:
                report_data["by_suite"][suite] = {"total": 0, "passed": 0, "failed": 0}
            report_data["by_suite"][suite]["total"] += result.get("total", 0)
            report_data["by_suite"][suite]["passed"] += result.get("passed", 0)
            report_data["by_suite"][suite]["failed"] += result.get("failed", 0)

            # Testes individuais
            for test in result.get("tests", []):
                report_data["tests"].append(test)
                if test.get("status") == "failed":
                    report_data["failed_tests"].append(test)

        # Calcular taxa de sucesso
        if report_data["total_tests"] > 0:
            report_data["success_rate"] = round(
                (report_data["passed"] / report_data["total_tests"]) * 100, 2
            )

        # Gerar recomendacoes
        report_data["recommendations"] = self._generate_recommendations(report_data)

        return report_data

    def _parse_period(self, period: str) -> tuple:
        """Parse periodo para datas"""
        now = datetime.now()

        if period == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now
        elif period == "yesterday":
            start = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            end = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "week":
            start = now - timedelta(days=7)
            end = now
        elif period == "month":
            start = now - timedelta(days=30)
            end = now
        else:
            # Tentar parse como data
            try:
                start = datetime.fromisoformat(period)
                end = now
            except ValueError:
                start = now - timedelta(days=1)
                end = now

        return start, end

    def _collect_results(
        self,
        start_date: datetime,
        end_date: datetime,
        environment: Optional[str] = None
    ) -> List[Dict]:
        """Coleta resultados do periodo"""
        results = []
        results_dir = AGENT_ROOT / "results"

        if not results_dir.exists():
            return results

        for result_file in results_dir.glob("result_*.json"):
            try:
                with open(result_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Verificar data
                result_time = datetime.fromisoformat(data.get("start_time", ""))
                if not (start_date <= result_time <= end_date):
                    continue

                # Verificar ambiente
                if environment and data.get("environment") != environment:
                    continue

                results.append(data)

            except Exception:
                continue

        return results

    def _generate_recommendations(self, report_data: Dict) -> List[str]:
        """Gera recomendacoes baseadas nos dados"""
        recommendations = []

        # Taxa de sucesso baixa
        if report_data["success_rate"] < 80:
            recommendations.append(
                "Taxa de sucesso abaixo de 80%. Priorize a correcao dos testes falhando."
            )

        # Muitos erros
        if report_data["errors"] > 0:
            recommendations.append(
                f"{report_data['errors']} teste(s) com erro. Verifique configuracao do ambiente."
            )

        # Testes pulados
        if report_data["skipped"] > report_data["total_tests"] * 0.1:
            recommendations.append(
                "Mais de 10% dos testes foram pulados. Revise as condicoes de skip."
            )

        # Duracao alta
        if report_data["duration"] > 600:
            recommendations.append(
                "Execucao demorou mais de 10 minutos. Considere paralelizar os testes."
            )

        # Testes falhando repetidamente
        failed_names = [t.get("name") for t in report_data["failed_tests"]]
        if failed_names:
            recommendations.append(
                f"Testes falhando: {', '.join(failed_names[:5])}. Investigue as causas."
            )

        if not recommendations:
            recommendations.append("Otimo trabalho! Todos os indicadores estao saudaveis.")

        return recommendations

    def save_report(
        self,
        report_data: Dict,
        format: str = "html"
    ) -> Path:
        """Salva relatorio em arquivo"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"report_{report_data['period']}_{timestamp}.{format}"
        filepath = self.reports_dir / filename

        if format == "html":
            content = self._render_html(report_data)
        elif format == "md":
            content = self._render_markdown(report_data)
        elif format == "json":
            content = json.dumps(report_data, indent=2, ensure_ascii=False)
        else:
            content = self._render_markdown(report_data)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        return filepath

    def _render_html(self, data: Dict) -> str:
        """Renderiza relatorio HTML"""
        # Gerar linhas da tabela
        test_rows = []
        for test in data.get("tests", [])[:50]:  # Limitar a 50
            status = test.get("status", "unknown")
            badge_class = f"badge-{status}"
            test_rows.append(f'''
                <tr>
                    <td>{test.get("name", "N/A")}</td>
                    <td><span class="badge {badge_class}">{status.upper()}</span></td>
                    <td>{test.get("duration", 0):.2f}s</td>
                    <td>{test.get("message", "-") or "-"}</td>
                </tr>
            ''')

        # Detalhes de falhas
        failed_details = ""
        if data.get("failed_tests"):
            failed_details = '<div class="card"><h2 class="section-title">Detalhes das Falhas</h2>'
            for test in data["failed_tests"][:10]:
                failed_details += f'''
                    <div style="margin-bottom: 1rem; padding: 1rem; background: #fef2f2; border-radius: 8px;">
                        <strong>{test.get("name", "N/A")}</strong>
                        <pre style="margin-top: 0.5rem; font-size: 0.75rem; overflow-x: auto;">
{test.get("traceback", "Sem traceback disponivel")[:500]}
                        </pre>
                    </div>
                '''
            failed_details += '</div>'

        template = Template(self.HTML_TEMPLATE)
        return template.substitute(
            timestamp=datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            environment=data.get("environment", "N/A"),
            period=data.get("period", "N/A"),
            total=data.get("total_tests", 0),
            passed=data.get("passed", 0),
            failed=data.get("failed", 0),
            skipped=data.get("skipped", 0),
            success_rate=data.get("success_rate", 0),
            test_rows="\n".join(test_rows),
            failed_details=failed_details
        )

    def _render_markdown(self, data: Dict) -> str:
        """Renderiza relatorio Markdown"""
        # Tabela de categorias
        category_rows = []
        for suite, stats in data.get("by_suite", {}).items():
            rate = (stats["passed"] / stats["total"] * 100) if stats["total"] > 0 else 0
            category_rows.append(f"| {suite} | {stats['total']} | {stats['passed']} | {stats['failed']} | {rate:.1f}% |")

        category_table = "| Suite | Total | Passou | Falhou | Taxa |\n|-------|-------|--------|--------|------|\n"
        category_table += "\n".join(category_rows) if category_rows else "| - | - | - | - | - |"

        # Detalhes dos testes
        test_details = ""
        for test in data.get("tests", [])[:30]:
            status_emoji = {"passed": "pass", "failed": "fail", "skipped": "skip"}.get(test.get("status"), "?")
            test_details += f"- [{status_emoji}] `{test.get('name', 'N/A')}` ({test.get('duration', 0):.2f}s)\n"

        # Falhas detalhadas
        failed_details = ""
        for test in data.get("failed_tests", [])[:10]:
            failed_details += f"### {test.get('name', 'N/A')}\n"
            failed_details += f"**Mensagem:** {test.get('message', 'N/A')}\n"
            if test.get("traceback"):
                failed_details += f"```\n{test['traceback'][:500]}\n```\n\n"

        # Recomendacoes
        recommendations = "\n".join(f"- {r}" for r in data.get("recommendations", []))

        template = Template(self.MARKDOWN_TEMPLATE)
        return template.substitute(
            timestamp=datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            environment=data.get("environment", "N/A"),
            period=data.get("period", "N/A"),
            total=data.get("total_tests", 0),
            passed=data.get("passed", 0),
            failed=data.get("failed", 0),
            skipped=data.get("skipped", 0),
            success_rate=data.get("success_rate", 0),
            duration=data.get("duration", 0),
            category_table=category_table,
            test_details=test_details or "Nenhum teste executado no periodo.",
            failed_details=failed_details or "Nenhuma falha no periodo.",
            recommendations=recommendations or "Nenhuma recomendacao."
        )
