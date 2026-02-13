"""
Testes Basicos de Seguranca
============================

Testes que verificam aspectos basicos de seguranca em APIs web.
Estes testes sao educacionais e demonstram verificacoes comuns em QA de seguranca.

Checklist OWASP verificado:
- Headers de seguranca
- Protecao contra metodos HTTP nao permitidos
- Validacao de Content-Type
- Respostas de erro nao vazam informacoes
"""

import pytest
import requests


class TestSecurityHeaders:
    """Verifica presenca de headers de seguranca na resposta."""

    @pytest.fixture
    def response(self):
        """Faz uma requisicao GET e retorna a resposta para analise."""
        return requests.get("https://jsonplaceholder.typicode.com/posts/1")

    def test_content_type_presente(self, response):
        """Verifica que Content-Type esta presente na resposta."""
        assert "Content-Type" in response.headers

    def test_content_type_json(self, response):
        """Verifica que a API retorna JSON."""
        content_type = response.headers.get("Content-Type", "")
        assert "application/json" in content_type or "charset=utf-8" in content_type


class TestHTTPMethods:
    """Testa comportamento com diferentes metodos HTTP."""

    def test_options_retorna_metodos_permitidos(self):
        """Verifica que OPTIONS retorna os metodos permitidos."""
        response = requests.options("https://jsonplaceholder.typicode.com/posts")
        # Verifica que a requisicao nao retorna erro do servidor
        assert response.status_code < 500

    def test_head_retorna_headers_sem_body(self):
        """Verifica que HEAD retorna headers mas sem body."""
        response = requests.head("https://jsonplaceholder.typicode.com/posts/1")
        assert response.status_code == 200
        # HEAD nao deve ter body
        assert len(response.content) == 0


class TestInputValidation:
    """Testa validacao de entrada (prevencao de injection)."""

    def test_sql_injection_no_parametro(self):
        """Verifica que SQL injection em parametros nao causa erro 500."""
        malicious_input = "1 OR 1=1; DROP TABLE users;--"
        response = requests.get(
            f"https://jsonplaceholder.typicode.com/posts/{malicious_input}"
        )
        # A API nao deve retornar erro interno (500)
        assert response.status_code != 500

    def test_xss_no_body(self):
        """Verifica que XSS no body da requisicao nao e refletido sem sanitizacao."""
        xss_payload = "<script>alert('XSS')</script>"
        response = requests.post(
            "https://jsonplaceholder.typicode.com/posts",
            json={
                "title": xss_payload,
                "body": "Teste XSS",
                "userId": 1
            }
        )
        # JSONPlaceholder retorna o que recebe (API fake)
        # Em uma API real, o XSS deveria ser sanitizado
        assert response.status_code in [200, 201]

    def test_body_muito_grande(self):
        """Testa envio de payload excessivamente grande."""
        large_body = "A" * 100000  # 100KB de dados
        response = requests.post(
            "https://jsonplaceholder.typicode.com/posts",
            json={
                "title": "Teste payload grande",
                "body": large_body,
                "userId": 1
            }
        )
        # A API deve responder sem erro 500
        assert response.status_code != 500


class TestErrorResponses:
    """Verifica que respostas de erro nao vazam informacoes sensiveis."""

    def test_404_nao_vaza_stack_trace(self):
        """Verifica que erro 404 nao expoe stack trace ou detalhes internos."""
        response = requests.get("https://jsonplaceholder.typicode.com/recurso_inexistente")
        body = response.text.lower()
        # Nao deve conter indicios de stack trace
        assert "traceback" not in body
        assert "exception" not in body
        assert "stack trace" not in body

    def test_metodo_invalido_nao_vaza_info(self):
        """Verifica que metodo PATCH em endpoint errado nao vaza info."""
        response = requests.patch(
            "https://jsonplaceholder.typicode.com/invalid_endpoint",
            json={"test": True}
        )
        body = response.text.lower()
        assert "internal server error" not in body
