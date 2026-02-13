"""
Test Generator - Gerador de Testes
==================================

Gera casos de teste em formato Gherkin e scripts pytest
baseados na analise de codigo e sugestoes da IA.
"""

import re
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from string import Template

from config.settings import AgentConfig, Environment, AGENT_ROOT


class TestGenerator:
    """
    Gerador de testes automatizados.

    Responsabilidades:
    - Gerar casos de teste em formato Gherkin (BDD)
    - Criar scripts pytest
    - Manter consistencia com padroes do projeto
    - Salvar arquivos nos locais corretos
    """

    # Template para teste de API
    API_TEST_TEMPLATE = '''"""
Testes automatizados: ${feature_name}
Gerado por QA Agent em ${timestamp}

Ambiente: ${environment}
Categoria: ${category}
"""

import pytest
import requests
from typing import Dict, Any

# Fixtures e configuracoes
from conftest import (
    api_base_url,
    api_token,
    robust_api_client,
    ${fixtures}
)


class Test${class_name}:
    """Testes para ${feature_description}"""

    @pytest.mark.${environment}
    @pytest.mark.smoke
    def test_${feature_slug}_success(self, robust_api_client):
        """
        Cenario: ${feature_name} com dados validos

        Given um usuario autenticado
        When faz requisicao para ${endpoint}
        Then recebe resposta 200 OK
        And dados estao no formato esperado
        """
        response = robust_api_client.${method}("${endpoint}"${params})

        assert response.status_code == 200, f"Esperado 200, recebido {response.status_code}"
        data = response.json()
        ${assertions}

    @pytest.mark.${environment}
    @pytest.mark.negative
    def test_${feature_slug}_invalid_input(self, robust_api_client):
        """
        Cenario: ${feature_name} com dados invalidos

        Given um usuario autenticado
        When faz requisicao com dados invalidos
        Then recebe resposta de erro apropriada
        """
        ${negative_test}

    @pytest.mark.${environment}
    @pytest.mark.security
    def test_${feature_slug}_unauthorized(self, api_base_url):
        """
        Cenario: ${feature_name} sem autenticacao

        Given um usuario NAO autenticado
        When tenta acessar ${endpoint}
        Then recebe resposta 401 Unauthorized
        """
        response = requests.${method}(
            f"{api_base_url}${endpoint}",
            timeout=30
        )

        assert response.status_code in [401, 403], \\
            f"Endpoint deveria requerer autenticacao, recebido {response.status_code}"
'''

    # Template para teste E2E
    E2E_TEST_TEMPLATE = '''"""
Testes E2E: ${feature_name}
Gerado por QA Agent em ${timestamp}

Ambiente: ${environment}
"""

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class Test${class_name}E2E:
    """Testes E2E para ${feature_description}"""

    @pytest.fixture(autouse=True)
    def setup(self, driver):
        """Setup do teste"""
        self.driver = driver
        self.wait = WebDriverWait(driver, 30)

    @pytest.mark.${environment}
    @pytest.mark.e2e
    def test_${feature_slug}_flow(self):
        """
        Cenario: Fluxo completo de ${feature_name}

        Given usuario na pagina inicial
        When navega para ${page}
        And preenche formulario
        Then operacao e concluida com sucesso
        """
        # Navegar para pagina
        self.driver.get("${url}")

        # Aguardar carregamento
        self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "${main_selector}"))
        )

        ${e2e_steps}

        # Verificar resultado
        ${e2e_assertions}
'''

    # Template Gherkin
    GHERKIN_TEMPLATE = '''Feature: ${feature_name}
  ${feature_description}

  Background:
    Given usuario esta autenticado no sistema
    And ambiente "${environment}" esta configurado

  @${environment} @smoke
  Scenario: ${feature_name} com sucesso
    Given ${given_success}
    When ${when_success}
    Then ${then_success}

  @${environment} @negative
  Scenario: ${feature_name} com dados invalidos
    Given ${given_negative}
    When ${when_negative}
    Then ${then_negative}

  @${environment} @security
  Scenario: ${feature_name} sem autorizacao
    Given usuario NAO esta autenticado
    When tenta executar ${feature_name}
    Then recebe erro de autorizacao
    And operacao e bloqueada
'''

    def __init__(self, knowledge):
        self.knowledge = knowledge
        self.output_dir = AGENT_ROOT / "generated_tests"
        self.output_dir.mkdir(exist_ok=True)

    def generate_api_test(
        self,
        feature_name: str,
        endpoint: str,
        method: str = "get",
        environment: Environment = Environment.UAT,
        params: Optional[Dict] = None,
        expected_fields: Optional[List[str]] = None
    ) -> str:
        """Gera teste de API"""
        # Preparar variaveis
        feature_slug = self._slugify(feature_name)
        class_name = self._to_class_name(feature_name)

        # Preparar assertions
        assertions = []
        if expected_fields:
            for field in expected_fields:
                assertions.append(f'assert "{field}" in data, "Campo {field} ausente na resposta"')
        else:
            assertions.append('assert data is not None, "Resposta vazia"')

        # Preparar params
        params_str = ""
        if params:
            if method == "get":
                params_str = f", params={params}"
            else:
                params_str = f", json_data={params}"

        # Preparar teste negativo
        negative_test = self._generate_negative_test(endpoint, method)

        # Gerar codigo
        template = Template(self.API_TEST_TEMPLATE)
        code = template.substitute(
            feature_name=feature_name,
            feature_slug=feature_slug,
            feature_description=f"Testes para {feature_name}",
            class_name=class_name,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            environment=environment.value,
            category="api",
            endpoint=endpoint,
            method=method,
            params=params_str,
            fixtures="api_session, base_url",
            assertions="\n        ".join(assertions),
            negative_test=negative_test
        )

        return code

    def generate_e2e_test(
        self,
        feature_name: str,
        url: str,
        environment: Environment = Environment.UAT,
        steps: Optional[List[str]] = None
    ) -> str:
        """Gera teste E2E"""
        feature_slug = self._slugify(feature_name)
        class_name = self._to_class_name(feature_name)

        # Preparar steps
        e2e_steps = []
        if steps:
            for step in steps:
                e2e_steps.append(f"# {step}")
                e2e_steps.append("pass  # TODO: Implementar")
        else:
            e2e_steps.append("# TODO: Implementar passos do teste")
            e2e_steps.append("pass")

        template = Template(self.E2E_TEST_TEMPLATE)
        code = template.substitute(
            feature_name=feature_name,
            feature_slug=feature_slug,
            feature_description=f"Testes E2E para {feature_name}",
            class_name=class_name,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            environment=environment.value,
            page=feature_name,
            url=url,
            main_selector="body",
            e2e_steps="\n        ".join(e2e_steps),
            e2e_assertions="assert True  # TODO: Adicionar verificacoes"
        )

        return code

    def generate_gherkin(
        self,
        feature_name: str,
        feature_description: str,
        environment: Environment = Environment.UAT,
        scenarios: Optional[List[Dict]] = None
    ) -> str:
        """Gera casos de teste em formato Gherkin"""
        template = Template(self.GHERKIN_TEMPLATE)

        # Cenarios padrao
        given_success = "dados validos estao disponiveis"
        when_success = f"usuario executa {feature_name}"
        then_success = "operacao e realizada com sucesso"

        given_negative = "dados invalidos sao fornecidos"
        when_negative = f"usuario tenta executar {feature_name}"
        then_negative = "sistema retorna mensagem de erro apropriada"

        if scenarios:
            for scenario in scenarios:
                if scenario.get("type") == "success":
                    given_success = scenario.get("given", given_success)
                    when_success = scenario.get("when", when_success)
                    then_success = scenario.get("then", then_success)
                elif scenario.get("type") == "negative":
                    given_negative = scenario.get("given", given_negative)
                    when_negative = scenario.get("when", when_negative)
                    then_negative = scenario.get("then", then_negative)

        gherkin = template.substitute(
            feature_name=feature_name,
            feature_description=feature_description,
            environment=environment.value,
            given_success=given_success,
            when_success=when_success,
            then_success=then_success,
            given_negative=given_negative,
            when_negative=when_negative,
            then_negative=then_negative
        )

        return gherkin

    def _generate_negative_test(self, endpoint: str, method: str) -> str:
        """Gera codigo para teste negativo"""
        if "cpf" in endpoint.lower():
            return '''invalid_data = {"cpf": "00000000000"}
        response = robust_api_client.{method}("{endpoint}", json_data=invalid_data)
        assert response.status_code in [400, 422], f"Esperado erro de validacao, recebido {{response.status_code}}"'''.format(
                method=method, endpoint=endpoint
            )
        elif "cnpj" in endpoint.lower():
            return '''invalid_data = {"cnpj": "00000000000000"}
        response = robust_api_client.{method}("{endpoint}", json_data=invalid_data)
        assert response.status_code in [400, 422], f"Esperado erro de validacao, recebido {{response.status_code}}"'''.format(
                method=method, endpoint=endpoint
            )
        else:
            return '''# Teste com dados invalidos/vazios
        response = robust_api_client.{method}("{endpoint}", json_data={{}})
        assert response.status_code >= 400, f"Esperado erro, recebido {{response.status_code}}"'''.format(
                method=method, endpoint=endpoint
            )

    def _slugify(self, text: str) -> str:
        """Converte texto para slug"""
        slug = text.lower()
        slug = re.sub(r'[^a-z0-9]+', '_', slug)
        slug = slug.strip('_')
        return slug

    def _to_class_name(self, text: str) -> str:
        """Converte texto para nome de classe"""
        words = re.split(r'[^a-zA-Z0-9]+', text)
        return ''.join(word.capitalize() for word in words if word)

    def extract_and_save_script(
        self,
        response: str,
        feature_name: str,
        environment: Environment
    ) -> Optional[Path]:
        """Extrai script Python da resposta e salva"""
        # Buscar bloco de codigo Python
        match = re.search(r'```python\n(.*?)```', response, re.DOTALL)
        if not match:
            return None

        code = match.group(1)

        # Determinar diretorio de destino
        if environment == Environment.UAT:
            dest_dir = AGENT_ROOT.parent / "Ambiente de UAT" / "generated"
        else:
            dest_dir = AGENT_ROOT.parent / "Producao" / "generated"

        dest_dir.mkdir(parents=True, exist_ok=True)

        # Salvar arquivo
        filename = f"test_{self._slugify(feature_name)}.py"
        filepath = dest_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(code)

        return filepath

    def save_test(
        self,
        code: str,
        feature_name: str,
        test_type: str,
        environment: Environment
    ) -> Path:
        """Salva teste gerado no local apropriado"""
        # Determinar diretorio
        if environment == Environment.UAT:
            base_dir = AGENT_ROOT.parent / "Ambiente de UAT"
        else:
            base_dir = AGENT_ROOT.parent / "Producao"

        # Subdiretorio por tipo
        type_dirs = {
            "api": "api_tests",
            "e2e": "e2e_tests",
            "security": "security_tests",
            "integration": "integration_tests"
        }

        dest_dir = base_dir / type_dirs.get(test_type, "generated_tests")
        dest_dir.mkdir(parents=True, exist_ok=True)

        # Salvar
        filename = f"test_{self._slugify(feature_name)}.py"
        filepath = dest_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(code)

        return filepath

    def save_gherkin(
        self,
        gherkin: str,
        feature_name: str,
        environment: Environment
    ) -> Path:
        """Salva feature Gherkin"""
        if environment == Environment.UAT:
            base_dir = AGENT_ROOT.parent / "Ambiente de UAT"
        else:
            base_dir = AGENT_ROOT.parent / "Producao"

        dest_dir = base_dir / "features"
        dest_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{self._slugify(feature_name)}.feature"
        filepath = dest_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(gherkin)

        return filepath
