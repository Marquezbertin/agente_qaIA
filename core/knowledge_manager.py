"""
Knowledge Manager - Gerenciador de Base de Conhecimento
=======================================================

Responsavel por indexar, buscar e analisar os repositorios
base de conhecimento do QA Agent.
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import subprocess


@dataclass
class FileInfo:
    """Informacoes de um arquivo"""
    path: Path
    name: str
    extension: str
    size: int
    modified: datetime
    content_hash: Optional[str] = None
    is_test: bool = False
    language: Optional[str] = None


@dataclass
class CodeContext:
    """Contexto de codigo para analise"""
    file_path: str
    content: str
    language: str
    imports: List[str] = field(default_factory=list)
    classes: List[str] = field(default_factory=list)
    functions: List[str] = field(default_factory=list)
    endpoints: List[str] = field(default_factory=list)


class KnowledgeManager:
    """
    Gerenciador da base de conhecimento do agente.

    Indexa e busca nos repositorios configurados:
    - Projeto de testes: Scripts de teste existentes
    """

    # Padroes para ignorar
    IGNORE_PATTERNS = [
        r"\.venv", r"node_modules", r"__pycache__", r"\.git",
        r"\.pytest_cache", r"\.mypy_cache", r"dist", r"build",
        r"\.egg-info", r"\.tox", r"\.coverage"
    ]

    # Extensoes de interesse
    EXTENSIONS = {
        ".py": "python",
        ".cs": "csharp",
        ".js": "javascript",
        ".ts": "typescript",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".md": "markdown",
        ".sql": "sql"
    }

    def __init__(self, repositories: Dict[str, Path]):
        self.repositories = repositories
        self.index: Dict[str, List[FileInfo]] = {}
        self.test_files: List[FileInfo] = []
        self.source_files: List[FileInfo] = []

    def scan_repositories(self) -> Dict[str, Dict]:
        """Escaneia todos os repositorios e retorna estatisticas"""
        stats = {}

        for repo_name, repo_path in self.repositories.items():
            repo_stats = self._scan_repository(repo_name, repo_path)
            stats[repo_name] = repo_stats

        return stats

    def _scan_repository(self, name: str, path: Path) -> Dict:
        """Escaneia um repositorio especifico"""
        if not path.exists():
            return {"accessible": False, "error": "Path not found"}

        stats = {
            "accessible": True,
            "python_files": 0,
            "test_files": 0,
            "csharp_files": 0,
            "total_files": 0,
            "directories": 0
        }

        self.index[name] = []

        for root, dirs, files in os.walk(path):
            # Filtrar diretorios ignorados
            dirs[:] = [d for d in dirs if not self._should_ignore(d)]

            stats["directories"] += 1

            for file in files:
                file_path = Path(root) / file
                ext = file_path.suffix.lower()

                if ext not in self.EXTENSIONS:
                    continue

                if self._should_ignore(str(file_path)):
                    continue

                stats["total_files"] += 1

                try:
                    file_info = FileInfo(
                        path=file_path,
                        name=file,
                        extension=ext,
                        size=file_path.stat().st_size,
                        modified=datetime.fromtimestamp(file_path.stat().st_mtime),
                        is_test=self._is_test_file(file),
                        language=self.EXTENSIONS.get(ext)
                    )

                    self.index[name].append(file_info)

                    if ext == ".py":
                        stats["python_files"] += 1
                        if file_info.is_test:
                            stats["test_files"] += 1
                            self.test_files.append(file_info)
                        else:
                            self.source_files.append(file_info)
                    elif ext == ".cs":
                        stats["csharp_files"] += 1
                        self.source_files.append(file_info)

                except Exception:
                    continue

        return stats

    def _should_ignore(self, path: str) -> bool:
        """Verifica se o caminho deve ser ignorado"""
        for pattern in self.IGNORE_PATTERNS:
            if re.search(pattern, path):
                return True
        return False

    def _is_test_file(self, filename: str) -> bool:
        """Verifica se e um arquivo de teste"""
        name = filename.lower()
        return (
            name.startswith("test_") or
            name.endswith("_test.py") or
            name.endswith("_tests.py") or
            "test" in name and name.endswith(".py")
        )

    def search_relevant_code(self, query: str, max_results: int = 10) -> str:
        """Busca codigo relevante para uma query"""
        results = []
        query_lower = query.lower()
        keywords = query_lower.split()

        for repo_name, files in self.index.items():
            for file_info in files:
                # Verificar nome do arquivo
                score = 0
                file_name_lower = file_info.name.lower()

                for keyword in keywords:
                    if keyword in file_name_lower:
                        score += 10
                    if keyword in str(file_info.path).lower():
                        score += 5

                # Buscar no conteudo
                if score > 0 or any(kw in file_name_lower for kw in keywords):
                    try:
                        content = self._read_file(file_info.path)
                        content_lower = content.lower()

                        for keyword in keywords:
                            count = content_lower.count(keyword)
                            score += count * 2

                        if score > 0:
                            results.append((score, file_info, content[:2000]))
                    except Exception:
                        continue

        # Ordenar por score e limitar resultados
        results.sort(key=lambda x: x[0], reverse=True)
        results = results[:max_results]

        # Formatar output
        output = []
        for score, file_info, content in results:
            output.append(f"""
### {file_info.name} (Score: {score})
**Path:** {file_info.path}
**Language:** {file_info.language}

```{file_info.language}
{content}
```
""")

        return "\n".join(output) if output else "Nenhum codigo relevante encontrado."

    def _read_file(self, path: Path, max_size: int = 100000) -> str:
        """Le conteudo de um arquivo"""
        if path.stat().st_size > max_size:
            return f"[Arquivo muito grande: {path.stat().st_size} bytes]"

        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            return f"[Erro ao ler arquivo: {e}]"

    def get_file_content(self, file_path: str) -> Optional[str]:
        """Retorna conteudo de um arquivo especifico"""
        path = Path(file_path)
        if path.exists():
            return self._read_file(path)

        # Buscar nos repositorios
        for repo_path in self.repositories.values():
            full_path = repo_path / file_path
            if full_path.exists():
                return self._read_file(full_path)

        return None

    def get_recent_changes(self, days: int = 7) -> str:
        """Retorna arquivos modificados recentemente"""
        cutoff = datetime.now() - timedelta(days=days)
        recent = []

        for repo_name, files in self.index.items():
            for file_info in files:
                if file_info.modified > cutoff:
                    recent.append(file_info)

        recent.sort(key=lambda x: x.modified, reverse=True)

        output = [f"## Arquivos modificados nos ultimos {days} dias\n"]
        for file_info in recent[:50]:
            output.append(
                f"- **{file_info.name}** ({file_info.path.parent.name}) - "
                f"{file_info.modified.strftime('%Y-%m-%d %H:%M')}"
            )

        return "\n".join(output)

    def discover_testables(self, target_type: str = "api") -> str:
        """Descobre funcionalidades testaveis"""
        discoveries = []

        if target_type == "api":
            discoveries = self._discover_api_endpoints()
        elif target_type == "ui":
            discoveries = self._discover_ui_components()
        elif target_type == "security":
            discoveries = self._discover_security_points()
        else:
            discoveries = self._discover_all()

        return "\n".join(discoveries)

    def _discover_api_endpoints(self) -> List[str]:
        """Descobre endpoints de API"""
        endpoints = []
        patterns = [
            r'@app\.route\(["\']([^"\']+)',  # Flask
            r'@router\.(get|post|put|delete)\(["\']([^"\']+)',  # FastAPI
            r'\[Route\(["\']([^"\']+)',  # ASP.NET
            r'\.MapGet\(["\']([^"\']+)',  # .NET Minimal API
            r'\.MapPost\(["\']([^"\']+)',
            r'"route":\s*["\']([^"\']+)',  # ServiceStack
        ]

        for repo_name, files in self.index.items():
            for file_info in files:
                if file_info.language not in ["python", "csharp"]:
                    continue

                try:
                    content = self._read_file(file_info.path)
                    for pattern in patterns:
                        matches = re.findall(pattern, content)
                        for match in matches:
                            endpoint = match if isinstance(match, str) else match[-1]
                            endpoints.append(f"- `{endpoint}` ({file_info.name})")
                except Exception:
                    continue

        return ["## Endpoints de API descobertos\n"] + list(set(endpoints))[:100]

    def _discover_ui_components(self) -> List[str]:
        """Descobre componentes de UI"""
        components = []
        # Implementar descoberta de componentes UI
        return ["## Componentes de UI descobertos\n"] + components

    def _discover_security_points(self) -> List[str]:
        """Descobre pontos de seguranca"""
        security_points = []
        patterns = [
            (r'password|senha', "Manipulacao de senha"),
            (r'token|jwt|bearer', "Manipulacao de token"),
            (r'encrypt|decrypt|hash', "Criptografia"),
            (r'auth|login|logout', "Autenticacao"),
            (r'permission|role|access', "Controle de acesso"),
            (r'sql.*\+|execute.*query', "Possivel SQL dinamico"),
            (r'innerHTML|eval\(', "Possivel XSS"),
        ]

        for repo_name, files in self.index.items():
            for file_info in files:
                try:
                    content = self._read_file(file_info.path).lower()
                    for pattern, description in patterns:
                        if re.search(pattern, content):
                            security_points.append(
                                f"- **{description}** em `{file_info.name}`"
                            )
                except Exception:
                    continue

        return ["## Pontos de Seguranca descobertos\n"] + list(set(security_points))[:100]

    def _discover_all(self) -> List[str]:
        """Descobre todas as funcionalidades"""
        all_discoveries = []
        all_discoveries.extend(self._discover_api_endpoints())
        all_discoveries.extend(self._discover_security_points())
        return all_discoveries

    def get_test_patterns(self) -> Dict[str, List[str]]:
        """Retorna padroes de teste existentes"""
        patterns = {
            "fixtures": [],
            "markers": [],
            "assertions": [],
            "setup_teardown": []
        }

        for file_info in self.test_files:
            try:
                content = self._read_file(file_info.path)

                # Fixtures
                fixtures = re.findall(r'@pytest\.fixture.*\ndef (\w+)', content)
                patterns["fixtures"].extend(fixtures)

                # Markers
                markers = re.findall(r'@pytest\.mark\.(\w+)', content)
                patterns["markers"].extend(markers)

                # Assertions
                assertions = re.findall(r'(assert\w*|expect\w*)\s*\(', content)
                patterns["assertions"].extend(assertions)

            except Exception:
                continue

        # Remover duplicatas e limitar
        for key in patterns:
            patterns[key] = list(set(patterns[key]))[:50]

        return patterns

    def get_repository_structure(self, repo_name: str) -> str:
        """Retorna estrutura de um repositorio"""
        if repo_name not in self.repositories:
            return f"Repositorio '{repo_name}' nao encontrado."

        repo_path = self.repositories[repo_name]
        structure = [f"## Estrutura: {repo_name}\n"]

        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if not self._should_ignore(d)]

            level = len(Path(root).relative_to(repo_path).parts)
            if level > 3:  # Limitar profundidade
                continue

            indent = "  " * level
            folder_name = Path(root).name
            structure.append(f"{indent}- **{folder_name}/**")

            # Listar alguns arquivos importantes
            important_files = [f for f in files if not f.startswith('.')][:5]
            for file in important_files:
                structure.append(f"{indent}  - {file}")

        return "\n".join(structure[:100])
