"""
Configuracao compartilhada dos testes (conftest.py)
====================================================

Este arquivo e carregado automaticamente pelo pytest antes de executar
qualquer teste. Aqui definimos fixtures reutilizaveis.

Fixtures sao funcoes que fornecem dados ou recursos para os testes.
Aprenda mais: https://docs.pytest.org/en/stable/how-to/fixtures.html
"""

import pytest
import requests
import json
import os
from pathlib import Path
from datetime import datetime


# Diretorio para salvar respostas de API (auditoria)
REPORTS_DIR = Path(__file__).parent.parent / "reports" / "respostas"


@pytest.fixture(scope="session")
def base_url():
    """URL base para testes de API. Usa JSONPlaceholder como padrao."""
    return os.getenv("API_BASE_URL", "https://jsonplaceholder.typicode.com")


@pytest.fixture(scope="session")
def reqres_url():
    """URL base para testes com ReqRes.in."""
    return "https://reqres.in/api"


@pytest.fixture
def api_session():
    """Sessao HTTP reutilizavel com headers padrao."""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Accept": "application/json",
    })
    yield session
    session.close()


class ResponseSaver:
    """
    Salva respostas de API em arquivos JSON para auditoria.

    Principio: os dados reais NUNCA passam pelo LLM.
    Os JSONs salvos sao exibidos diretamente pelo app.py.
    """

    def __init__(self):
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    def save(self, test_name: str, response: requests.Response) -> Path:
        """Salva a resposta de uma chamada de API."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{test_name}_{timestamp}.json"
        filepath = REPORTS_DIR / filename

        data = {
            "test_name": test_name,
            "timestamp": timestamp,
            "request": {
                "method": response.request.method,
                "url": response.request.url,
            },
            "response": {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text[:1000],
            }
        }

        filepath.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return filepath


@pytest.fixture
def response_saver():
    """Fixture que fornece o ResponseSaver para salvar respostas de API."""
    return ResponseSaver()
