"""
Test Analyzer - Analisador de Testes
====================================

Analisa codigo-fonte e testes existentes para identificar
gaps de cobertura e sugerir novos cenarios.
"""

import re
import ast
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from collections import defaultdict

from core.knowledge_manager import KnowledgeManager


@dataclass
class TestCase:
    """Representa um caso de teste"""
    name: str
    file_path: str
    markers: List[str] = field(default_factory=list)
    docstring: Optional[str] = None
    assertions: int = 0
    complexity: str = "low"  # low, medium, high


@dataclass
class AnalysisResult:
    """Resultado de uma analise"""
    target: str
    file_count: int
    test_count: int
    coverage_estimate: float
    gaps: List[str]
    suggestions: List[str]
    existing_tests: List[TestCase]


class TestAnalyzer:
    """
    Analisador de testes existentes e codigo-fonte.

    Responsabilidades:
    - Mapear testes existentes
    - Identificar gaps de cobertura
    - Analisar complexidade de codigo
    - Sugerir novos cenarios de teste
    """

    def __init__(self, knowledge: KnowledgeManager):
        self.knowledge = knowledge
        self.tests_by_category: Dict[str, List[TestCase]] = defaultdict(list)
        self.total_tests = 0

    def scan_existing_tests(self) -> Dict:
        """Escaneia todos os testes existentes"""
        stats = {
            "total": 0,
            "by_category": defaultdict(int),
            "by_marker": defaultdict(int),
            "coverage": {}
        }

        for file_info in self.knowledge.test_files:
            try:
                content = self.knowledge._read_file(file_info.path)
                tests = self._extract_tests(content, str(file_info.path))

                for test in tests:
                    stats["total"] += 1
                    self.total_tests += 1

                    # Categorizar
                    category = self._categorize_test(test, str(file_info.path))
                    stats["by_category"][category] += 1
                    self.tests_by_category[category].append(test)

                    # Markers
                    for marker in test.markers:
                        stats["by_marker"][marker] += 1

            except Exception:
                continue

        # Calcular cobertura estimada por categoria
        total_possible = {
            "api": 100,
            "e2e": 50,
            "security": 80,
            "integration": 60,
            "unit": 200,
            "smoke": 20,
            "regression": 40
        }

        for category, possible in total_possible.items():
            actual = stats["by_category"].get(category, 0)
            stats["coverage"][category] = min(100, (actual / possible) * 100)

        return stats

    def _extract_tests(self, content: str, file_path: str) -> List[TestCase]:
        """Extrai casos de teste de um arquivo"""
        tests = []

        # Regex para encontrar funcoes de teste
        test_pattern = re.compile(
            r'(@pytest\.mark\.(\w+)\s*\n)*'
            r'def (test_\w+)\s*\([^)]*\):\s*'
            r'(?:"""([^"]*?)""")?',
            re.MULTILINE | re.DOTALL
        )

        for match in test_pattern.finditer(content):
            markers_text = match.group(0)
            test_name = match.group(3)
            docstring = match.group(4)

            # Extrair markers
            markers = re.findall(r'@pytest\.mark\.(\w+)', markers_text)

            # Contar assertions
            test_start = match.end()
            test_end = content.find('\ndef ', test_start)
            if test_end == -1:
                test_end = len(content)
            test_body = content[test_start:test_end]
            assertions = len(re.findall(r'\bassert\b', test_body))

            # Determinar complexidade
            complexity = "low"
            if assertions > 5 or len(test_body) > 500:
                complexity = "high"
            elif assertions > 2 or len(test_body) > 200:
                complexity = "medium"

            tests.append(TestCase(
                name=test_name,
                file_path=file_path,
                markers=markers,
                docstring=docstring,
                assertions=assertions,
                complexity=complexity
            ))

        return tests

    def _categorize_test(self, test: TestCase, file_path: str) -> str:
        """Categoriza um teste baseado em markers e path"""
        path_lower = file_path.lower()
        name_lower = test.name.lower()

        # Prioridade por markers
        if "security" in test.markers or "security" in path_lower:
            return "security"
        if "e2e" in test.markers or "e2e" in path_lower:
            return "e2e"
        if "integration" in test.markers or "integration" in path_lower:
            return "integration"
        if "smoke" in test.markers:
            return "smoke"
        if "regression" in test.markers or "regressao" in path_lower:
            return "regression"
        if "api" in path_lower or "_api" in name_lower:
            return "api"
        if "unit" in test.markers:
            return "unit"

        return "other"

    def analyze(self, target: str) -> str:
        """Analisa um alvo (arquivo ou diretorio)"""
        target_path = Path(target)

        # Verificar se e caminho absoluto ou relativo
        if not target_path.is_absolute():
            for repo_path in self.knowledge.repositories.values():
                possible_path = repo_path / target
                if possible_path.exists():
                    target_path = possible_path
                    break

        if not target_path.exists():
            return f"Alvo nao encontrado: {target}"

        if target_path.is_file():
            return self._analyze_file(target_path)
        else:
            return self._analyze_directory(target_path)

    def _analyze_file(self, file_path: Path) -> str:
        """Analisa um arquivo especifico"""
        try:
            content = self.knowledge._read_file(file_path)
        except Exception as e:
            return f"Erro ao ler arquivo: {e}"

        analysis = [f"## Analise: {file_path.name}\n"]

        # Informacoes basicas
        analysis.append(f"**Tamanho:** {len(content)} caracteres")
        analysis.append(f"**Linhas:** {content.count(chr(10))}")

        # Analise especifica por tipo
        if file_path.suffix == ".py":
            analysis.extend(self._analyze_python(content))
        elif file_path.suffix == ".cs":
            analysis.extend(self._analyze_csharp(content))
        elif file_path.suffix in [".json", ".yaml", ".yml"]:
            analysis.extend(self._analyze_config(content))

        # Identificar cenarios de teste
        analysis.append("\n### Cenarios de Teste Sugeridos\n")
        scenarios = self._suggest_scenarios(content, file_path)
        for i, scenario in enumerate(scenarios, 1):
            analysis.append(f"{i}. {scenario}")

        return "\n".join(analysis)

    def _analyze_python(self, content: str) -> List[str]:
        """Analisa codigo Python"""
        analysis = []

        # Classes
        classes = re.findall(r'class (\w+)', content)
        if classes:
            analysis.append(f"\n**Classes:** {', '.join(classes)}")

        # Funcoes
        functions = re.findall(r'def (\w+)\s*\(', content)
        if functions:
            analysis.append(f"**Funcoes:** {len(functions)} encontradas")
            public_funcs = [f for f in functions if not f.startswith('_')]
            analysis.append(f"**Funcoes publicas:** {', '.join(public_funcs[:10])}")

        # Imports
        imports = re.findall(r'^(?:from|import)\s+(\S+)', content, re.MULTILINE)
        if imports:
            analysis.append(f"**Dependencias:** {', '.join(set(imports)[:10])}")

        # Decorators
        decorators = re.findall(r'@(\w+)', content)
        if decorators:
            analysis.append(f"**Decorators:** {', '.join(set(decorators))}")

        # Complexidade ciclomatica estimada
        complexity = self._estimate_complexity(content)
        analysis.append(f"\n**Complexidade estimada:** {complexity}")

        return analysis

    def _analyze_csharp(self, content: str) -> List[str]:
        """Analisa codigo C#"""
        analysis = []

        # Classes
        classes = re.findall(r'class (\w+)', content)
        if classes:
            analysis.append(f"\n**Classes:** {', '.join(classes)}")

        # Metodos
        methods = re.findall(r'(?:public|private|protected)\s+\w+\s+(\w+)\s*\(', content)
        if methods:
            analysis.append(f"**Metodos:** {len(methods)} encontrados")

        # Endpoints (ServiceStack/ASP.NET)
        routes = re.findall(r'\[Route\(["\']([^"\']+)', content)
        if routes:
            analysis.append(f"\n**Endpoints:** {', '.join(routes)}")

        return analysis

    def _analyze_config(self, content: str) -> List[str]:
        """Analisa arquivos de configuracao"""
        analysis = []

        # Contar chaves
        keys = re.findall(r'"(\w+)":', content)
        if keys:
            analysis.append(f"\n**Configuracoes:** {len(set(keys))} chaves")

        return analysis

    def _estimate_complexity(self, content: str) -> str:
        """Estima complexidade do codigo"""
        # Contadores simples
        ifs = len(re.findall(r'\bif\b', content))
        loops = len(re.findall(r'\b(for|while)\b', content))
        trys = len(re.findall(r'\btry\b', content))

        score = ifs + (loops * 2) + trys

        if score > 50:
            return "Alta (score: {})".format(score)
        elif score > 20:
            return "Media (score: {})".format(score)
        else:
            return "Baixa (score: {})".format(score)

    def _analyze_directory(self, dir_path: Path) -> str:
        """Analisa um diretorio"""
        analysis = [f"## Analise: {dir_path.name}/\n"]

        # Contar arquivos
        py_files = list(dir_path.rglob("*.py"))
        test_files = [f for f in py_files if f.name.startswith("test_")]

        analysis.append(f"**Arquivos Python:** {len(py_files)}")
        analysis.append(f"**Arquivos de teste:** {len(test_files)}")

        # Listar subdiretorios
        subdirs = [d.name for d in dir_path.iterdir() if d.is_dir() and not d.name.startswith('.')]
        if subdirs:
            analysis.append(f"**Subdiretorios:** {', '.join(subdirs[:10])}")

        # Analisar testes existentes
        analysis.append("\n### Testes Existentes\n")
        for test_file in test_files[:10]:
            content = self.knowledge._read_file(test_file)
            tests = self._extract_tests(content, str(test_file))
            analysis.append(f"- **{test_file.name}:** {len(tests)} testes")

        # Gaps identificados
        analysis.append("\n### Gaps de Cobertura\n")
        gaps = self._identify_gaps(dir_path)
        for gap in gaps[:10]:
            analysis.append(f"- {gap}")

        return "\n".join(analysis)

    def _suggest_scenarios(self, content: str, file_path: Path) -> List[str]:
        """Sugere cenarios de teste baseado no codigo"""
        scenarios = []
        name = file_path.stem

        # Cenarios baseados em funcoes
        functions = re.findall(r'def (\w+)\s*\(([^)]*)\)', content)
        for func_name, params in functions:
            if func_name.startswith('_'):
                continue

            # Cenario positivo
            scenarios.append(f"Testar `{func_name}` com parametros validos")

            # Cenarios negativos
            if params:
                scenarios.append(f"Testar `{func_name}` com parametros invalidos/nulos")

            # Cenarios de boundary
            if any(t in params.lower() for t in ['int', 'float', 'number', 'id']):
                scenarios.append(f"Testar `{func_name}` com valores limite (0, -1, max)")

        # Cenarios baseados em patterns
        if re.search(r'api|request|response|endpoint', content, re.I):
            scenarios.append("Testar resposta para requisicao valida (200 OK)")
            scenarios.append("Testar resposta para requisicao sem autenticacao (401)")
            scenarios.append("Testar resposta para recurso inexistente (404)")
            scenarios.append("Testar resposta para dados invalidos (400)")

        if re.search(r'login|auth|password|token', content, re.I):
            scenarios.append("Testar login com credenciais validas")
            scenarios.append("Testar login com credenciais invalidas")
            scenarios.append("Testar expiracao de token/sessao")
            scenarios.append("Testar brute force protection")

        if re.search(r'cpf|cnpj|document', content, re.I):
            scenarios.append("Testar com CPF/CNPJ valido")
            scenarios.append("Testar com CPF/CNPJ invalido")
            scenarios.append("Testar com CPF/CNPJ formatado vs nao formatado")

        return scenarios[:15]

    def _identify_gaps(self, dir_path: Path) -> List[str]:
        """Identifica gaps de cobertura"""
        gaps = []

        # Arquivos sem testes correspondentes
        source_files = list(dir_path.rglob("*.py"))
        test_files = {f.name.replace("test_", "").replace("_test", "")
                      for f in source_files if "test" in f.name.lower()}

        for source in source_files:
            if "test" in source.name.lower():
                continue
            if source.stem not in test_files and not source.name.startswith("__"):
                gaps.append(f"Arquivo `{source.name}` sem teste correspondente")

        # Categorias sem cobertura
        categories = ["smoke", "regression", "security", "performance"]
        existing_markers = set()

        for file_info in self.knowledge.test_files:
            if str(dir_path) in str(file_info.path):
                content = self.knowledge._read_file(file_info.path)
                markers = re.findall(r'@pytest\.mark\.(\w+)', content)
                existing_markers.update(markers)

        for category in categories:
            if category not in existing_markers:
                gaps.append(f"Sem testes de `{category}`")

        return gaps

    def analyze_coverage(self) -> str:
        """Analisa cobertura geral de testes"""
        analysis = ["# Analise de Cobertura de Testes\n"]

        # Por categoria
        analysis.append("## Por Categoria\n")
        for category, tests in self.tests_by_category.items():
            analysis.append(f"- **{category.capitalize()}:** {len(tests)} testes")

        # Por repositorio
        analysis.append("\n## Por Repositorio\n")
        for repo_name, files in self.knowledge.index.items():
            test_count = sum(1 for f in files if f.is_test)
            source_count = sum(1 for f in files if not f.is_test and f.extension == ".py")
            ratio = (test_count / source_count * 100) if source_count > 0 else 0
            analysis.append(f"- **{repo_name}:** {test_count} testes / {source_count} fontes ({ratio:.1f}%)")

        # Gaps criticos
        analysis.append("\n## Gaps Criticos\n")
        gaps = self.find_test_gaps()
        for gap in gaps.split('\n')[:20]:
            if gap.strip():
                analysis.append(gap)

        return "\n".join(analysis)

    def find_test_gaps(self) -> str:
        """Encontra gaps de teste prioritarios"""
        gaps = []

        # Arquivos de seguranca sem testes
        for repo_name, files in self.knowledge.index.items():
            for file_info in files:
                if file_info.is_test:
                    continue

                content = self.knowledge._read_file(file_info.path)
                if not content:
                    continue

                # Detectar codigo critico
                if re.search(r'password|token|secret|auth', content, re.I):
                    # Verificar se tem teste
                    test_name = f"test_{file_info.path.stem}"
                    has_test = any(
                        test_name in t.name
                        for tests in self.tests_by_category.values()
                        for t in tests
                    )
                    if not has_test:
                        gaps.append(f"- [CRITICO] `{file_info.name}` manipula dados sensiveis sem teste")

                # Detectar endpoints sem teste
                if re.search(r'@app\.route|Route\(|MapGet|MapPost', content):
                    gaps.append(f"- [ALTO] `{file_info.name}` contem endpoints que precisam de teste de API")

        return "\n".join(gaps[:30])
