"""
Test Executor - Executor de Testes
==================================

Executa suites de teste em diferentes ambientes
e coleta resultados para analise.
"""

import os
import subprocess
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import time

from config.settings import AgentConfig, Environment, AGENT_ROOT


@dataclass
class TestResult:
    """Resultado de um teste"""
    name: str
    status: str  # passed, failed, skipped, error
    duration: float
    message: Optional[str] = None
    traceback: Optional[str] = None


@dataclass
class SuiteResult:
    """Resultado de uma suite de testes"""
    suite_name: str
    environment: str
    start_time: datetime
    end_time: Optional[datetime] = None
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    duration: float = 0.0
    tests: List[TestResult] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return (self.passed / self.total) * 100


class TestExecutor:
    """
    Executor de testes automatizados.

    Responsabilidades:
    - Executar suites pytest
    - Coletar resultados e metricas
    - Gerar evidencias (screenshots, logs)
    - Separar execucoes por ambiente
    """

    # Mapeamento de suites para paths
    # Personalize com as pastas do seu projeto de testes
    SUITE_PATHS = {
        "smoke": ["tests/", "-m", "smoke"],
        "regression": ["tests/", "-m", "regression"],
        "security": ["tests/security/"],
        "api": ["tests/api/"],
        "e2e": ["tests/e2e/"],
        "all": ["."],
    }

    def __init__(self, config: AgentConfig):
        self.config = config
        self.results_dir = AGENT_ROOT / "results"
        self.results_dir.mkdir(exist_ok=True)

    def run_tests(
        self,
        suite: str,
        environment: Environment,
        markers: Optional[List[str]] = None,
        parallel: bool = False,
        collect_only: bool = False
    ) -> SuiteResult:
        """Executa suite de testes"""
        result = SuiteResult(
            suite_name=suite,
            environment=environment.value,
            start_time=datetime.now()
        )

        # Obter configuracao do ambiente
        env_config = self.config.get_env_config(environment)
        if not env_config:
            result.errors = 1
            result.tests.append(TestResult(
                name="setup",
                status="error",
                duration=0,
                message=f"Ambiente {environment.value} nao configurado"
            ))
            return result

        # Construir comando pytest
        cmd = self._build_pytest_command(suite, environment, markers, parallel, collect_only)

        # Configurar variaveis de ambiente
        test_env = self._prepare_environment(env_config)

        # Arquivo de resultado JSON
        result_file = self.results_dir / f"result_{suite}_{environment.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        try:
            # Executar pytest
            process = subprocess.run(
                cmd,
                cwd=str(AGENT_ROOT.parent),
                env=test_env,
                capture_output=True,
                text=True,
                timeout=600  # 10 minutos max
            )

            # Parse resultado
            result = self._parse_pytest_output(
                process.stdout,
                process.stderr,
                process.returncode,
                result
            )

            # Salvar resultado
            self._save_result(result, result_file)

        except subprocess.TimeoutExpired:
            result.errors = 1
            result.tests.append(TestResult(
                name="execution",
                status="error",
                duration=600,
                message="Execucao excedeu timeout de 10 minutos"
            ))
        except Exception as e:
            result.errors = 1
            result.tests.append(TestResult(
                name="execution",
                status="error",
                duration=0,
                message=str(e)
            ))

        result.end_time = datetime.now()
        result.duration = (result.end_time - result.start_time).total_seconds()

        return result

    def _build_pytest_command(
        self,
        suite: str,
        environment: Environment,
        markers: Optional[List[str]] = None,
        parallel: bool = False,
        collect_only: bool = False
    ) -> List[str]:
        """Constroi comando pytest"""
        cmd = ["python", "-m", "pytest"]

        # Adicionar paths da suite
        if suite in self.SUITE_PATHS:
            paths = self.SUITE_PATHS[suite]
            for path in paths:
                if not path.startswith("-"):
                    cmd.append(path)
                else:
                    cmd.extend([path, paths[paths.index(path) + 1]])
                    break
        else:
            # Assumir que suite e um path direto
            cmd.append(suite)

        # Markers
        all_markers = [environment.value]
        if markers:
            all_markers.extend(markers)

        # Adicionar marker do ambiente
        if len(all_markers) > 0:
            marker_expr = " or ".join(all_markers)
            cmd.extend(["-m", marker_expr])

        # Opcoes comuns
        cmd.extend([
            "-v",
            "--tb=short",
            "-ra",
            f"--html={self.results_dir}/report_{suite}_{environment.value}.html",
            "--self-contained-html"
        ])

        # Paralelismo
        if parallel:
            cmd.extend(["-n", str(self.config.parallel_workers)])

        # Apenas coletar
        if collect_only:
            cmd.append("--collect-only")

        return cmd

    def _prepare_environment(self, env_config) -> Dict[str, str]:
        """Prepara variaveis de ambiente para execucao"""
        env = os.environ.copy()

        env.update({
            "API_BASE_URL": env_config.api_base_url,
            "API_TOKEN": env_config.api_token,
            "WEB_BASE_URL": env_config.web_base_url,
            "BACKEND_URL": env_config.backend_url,
            "ENVIRONMENT": env_config.name,
            "TEST_ENV": env_config.name.lower(),
            "API_TIMEOUT": str(env_config.timeout),
            "SELENIUM_HEADLESS": str(env_config.headless).lower()
        })

        return env

    def _parse_pytest_output(
        self,
        stdout: str,
        stderr: str,
        returncode: int,
        result: SuiteResult
    ) -> SuiteResult:
        """Parse output do pytest"""
        # Extrair estatisticas do output
        lines = stdout.split('\n')

        for line in lines:
            # Linha de resumo: "5 passed, 2 failed, 1 skipped in 10.5s"
            if ' passed' in line or ' failed' in line:
                import re
                passed_match = re.search(r'(\d+) passed', line)
                failed_match = re.search(r'(\d+) failed', line)
                skipped_match = re.search(r'(\d+) skipped', line)
                error_match = re.search(r'(\d+) error', line)
                duration_match = re.search(r'in ([\d.]+)s', line)

                if passed_match:
                    result.passed = int(passed_match.group(1))
                if failed_match:
                    result.failed = int(failed_match.group(1))
                if skipped_match:
                    result.skipped = int(skipped_match.group(1))
                if error_match:
                    result.errors = int(error_match.group(1))
                if duration_match:
                    result.duration = float(duration_match.group(1))

            # Detectar testes individuais
            if '::test_' in line:
                status = "passed"
                if "PASSED" in line:
                    status = "passed"
                elif "FAILED" in line:
                    status = "failed"
                elif "SKIPPED" in line:
                    status = "skipped"
                elif "ERROR" in line:
                    status = "error"

                # Extrair nome do teste
                test_name = line.split('::')[-1].split()[0] if '::' in line else line

                result.tests.append(TestResult(
                    name=test_name,
                    status=status,
                    duration=0  # Seria necessario parse mais detalhado
                ))

        result.total = result.passed + result.failed + result.skipped + result.errors

        # Adicionar stderr como informacao de debug
        if stderr and result.failed > 0:
            for test in result.tests:
                if test.status == "failed":
                    test.traceback = stderr[:1000]  # Limitar tamanho

        return result

    def _save_result(self, result: SuiteResult, filepath: Path):
        """Salva resultado em JSON"""
        data = {
            "suite_name": result.suite_name,
            "environment": result.environment,
            "start_time": result.start_time.isoformat(),
            "end_time": result.end_time.isoformat() if result.end_time else None,
            "total": result.total,
            "passed": result.passed,
            "failed": result.failed,
            "skipped": result.skipped,
            "errors": result.errors,
            "duration": result.duration,
            "success_rate": result.success_rate,
            "tests": [
                {
                    "name": t.name,
                    "status": t.status,
                    "duration": t.duration,
                    "message": t.message,
                    "traceback": t.traceback
                }
                for t in result.tests
            ]
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def collect_tests(
        self,
        suite: str,
        environment: Environment
    ) -> List[str]:
        """Coleta lista de testes sem executar"""
        result = self.run_tests(suite, environment, collect_only=True)

        # Parse testes coletados
        tests = []
        for test in result.tests:
            tests.append(test.name)

        return tests

    def run_single_test(
        self,
        test_path: str,
        environment: Environment
    ) -> TestResult:
        """Executa um teste especifico"""
        env_config = self.config.get_env_config(environment)
        if not env_config:
            return TestResult(
                name=test_path,
                status="error",
                duration=0,
                message=f"Ambiente {environment.value} nao configurado"
            )

        cmd = [
            "python", "-m", "pytest",
            test_path,
            "-v",
            "--tb=short"
        ]

        test_env = self._prepare_environment(env_config)
        start_time = time.time()

        try:
            process = subprocess.run(
                cmd,
                cwd=str(AGENT_ROOT.parent),
                env=test_env,
                capture_output=True,
                text=True,
                timeout=300
            )

            duration = time.time() - start_time

            status = "passed" if process.returncode == 0 else "failed"
            message = None
            traceback = None

            if process.returncode != 0:
                message = "Teste falhou"
                traceback = process.stdout + "\n" + process.stderr

            return TestResult(
                name=test_path,
                status=status,
                duration=duration,
                message=message,
                traceback=traceback
            )

        except subprocess.TimeoutExpired:
            return TestResult(
                name=test_path,
                status="error",
                duration=300,
                message="Timeout excedido"
            )
        except Exception as e:
            return TestResult(
                name=test_path,
                status="error",
                duration=0,
                message=str(e)
            )

    def get_execution_history(
        self,
        suite: Optional[str] = None,
        environment: Optional[Environment] = None,
        limit: int = 20
    ) -> List[Dict]:
        """Retorna historico de execucoes"""
        results = []

        for result_file in sorted(self.results_dir.glob("result_*.json"), reverse=True):
            try:
                with open(result_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Filtrar por suite
                if suite and data.get("suite_name") != suite:
                    continue

                # Filtrar por ambiente
                if environment and data.get("environment") != environment.value:
                    continue

                results.append(data)

                if len(results) >= limit:
                    break

            except Exception:
                continue

        return results
