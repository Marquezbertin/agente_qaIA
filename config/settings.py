"""
Configuracoes do QA Agent
"""
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from enum import Enum

# Diretorio raiz do agente
AGENT_ROOT = Path(__file__).parent.parent
PROJECT_ROOT = AGENT_ROOT.parent

# Repositorios base de conhecimento
# Adicione aqui os caminhos dos seus repositorios para indexacao
KNOWLEDGE_REPOS = {
    "projeto-testes": PROJECT_ROOT,
}


class Environment(Enum):
    """Ambientes disponiveis"""
    UAT = "uat"
    PRODUCTION = "production"


@dataclass
class EnvironmentConfig:
    """Configuracao de ambiente"""
    name: str
    api_base_url: str
    api_token: str
    web_base_url: str
    backend_url: str
    timeout: int = 60
    max_retries: int = 3
    headless: bool = True

    @classmethod
    def from_env_file(cls, env_path: Path) -> "EnvironmentConfig":
        """Carrega configuracao de arquivo .env"""
        config = {}
        if env_path.exists():
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        config[key.strip()] = value.strip()

        return cls(
            name=config.get('ENVIRONMENT', 'unknown'),
            api_base_url=config.get('API_BASE_URL', ''),
            api_token=config.get('API_TOKEN', ''),
            web_base_url=config.get('WEB_BASE_URL', ''),
            backend_url=config.get('BACKEND_URL', ''),
            timeout=int(config.get('API_TIMEOUT', '60')),
            max_retries=int(config.get('MAX_RETRIES', '3')),
            headless=config.get('SELENIUM_HEADLESS', 'true').lower() == 'true'
        )


@dataclass
class AgentConfig:
    """Configuracao principal do agente"""
    # Anthropic API
    anthropic_api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 8192

    # Diretorios
    reports_dir: Path = field(default_factory=lambda: AGENT_ROOT / "reports")
    templates_dir: Path = field(default_factory=lambda: AGENT_ROOT / "templates")
    knowledge_dir: Path = field(default_factory=lambda: AGENT_ROOT / "knowledge_base")

    # Ambientes
    uat_config: Optional[EnvironmentConfig] = None
    prod_config: Optional[EnvironmentConfig] = None

    # Execucao
    parallel_workers: int = 4
    verbose: bool = True
    debug: bool = False

    def __post_init__(self):
        # Carregar configs de ambiente a partir de .env no diretorio de testes
        test_project_dir = Path(os.getenv("TEST_PROJECT_DIR", str(AGENT_ROOT / "sample_project")))
        env_file = test_project_dir / ".env"

        if env_file.exists():
            self.uat_config = EnvironmentConfig.from_env_file(env_file)
            self.prod_config = EnvironmentConfig.from_env_file(env_file)

        # Criar diretorios
        for dir_path in [self.reports_dir, self.templates_dir, self.knowledge_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

    def get_env_config(self, env: Environment) -> Optional[EnvironmentConfig]:
        """Retorna configuracao do ambiente especificado"""
        if env == Environment.UAT:
            return self.uat_config
        return self.prod_config


# Marcadores pytest suportados
PYTEST_MARKERS = [
    "unit", "integration", "e2e", "negative", "security",
    "performance", "schema", "slow", "smoke", "regression",
    "critical", "compliance", "auth", "biometric"
]

# Tipos de teste
TEST_TYPES = {
    "api": ["test_api*.py", "test_*_api.py"],
    "e2e": ["test_e2e*.py", "test_*_e2e.py"],
    "security": ["test_security*.py", "test_*_vulnerability.py", "test_*_injection.py"],
    "integration": ["test_integration*.py", "test_*_integration.py"],
    "smoke": ["test_smoke*.py"],
    "regression": ["test_regression*.py", "test_*_regressao.py"]
}

# Extensoes de arquivo para analise
ANALYZABLE_EXTENSIONS = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".cs": "csharp",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml"
}
