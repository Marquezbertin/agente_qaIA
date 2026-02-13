"""
Testes de API - ReqRes.in
==========================

Testes usando a API publica ReqRes (https://reqres.in).
Simula autenticacao e CRUD de usuarios - ideal para testes mais realistas.

Endpoints testados:
- GET /users - Listar usuarios (paginado)
- POST /register - Registrar usuario
- POST /login - Login
- GET /users/{id} - Obter usuario
- DELETE /users/{id} - Deletar usuario
"""

import pytest
import requests


class TestListUsers:
    """Testes para o endpoint GET /users (paginacao)"""

    def test_listar_usuarios_pagina_1(self, reqres_url, api_session):
        """Verifica que a primeira pagina retorna dados."""
        response = api_session.get(f"{reqres_url}/users", params={"page": 1})
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert len(data["data"]) > 0

    def test_paginacao_tem_metadados(self, reqres_url, api_session):
        """Verifica que a resposta inclui metadados de paginacao."""
        response = api_session.get(f"{reqres_url}/users")
        data = response.json()
        assert "total" in data
        assert "total_pages" in data
        assert "per_page" in data


class TestRegister:
    """Testes para o endpoint POST /register"""

    def test_registro_com_sucesso(self, reqres_url, api_session, response_saver):
        """Testa registro com credenciais validas."""
        payload = {
            "email": "eve.holt@reqres.in",
            "password": "pistol"
        }
        response = api_session.post(f"{reqres_url}/register", json=payload)
        response_saver.save("register_success", response)
        assert response.status_code == 200
        assert "token" in response.json()

    def test_registro_sem_senha_falha(self, reqres_url, api_session, response_saver):
        """Testa que registro sem senha retorna erro 400."""
        payload = {"email": "eve.holt@reqres.in"}
        response = api_session.post(f"{reqres_url}/register", json=payload)
        response_saver.save("register_fail", response)
        assert response.status_code == 400
        assert "error" in response.json()


class TestLogin:
    """Testes para o endpoint POST /login"""

    def test_login_com_sucesso(self, reqres_url, api_session, response_saver):
        """Testa login com credenciais validas."""
        payload = {
            "email": "eve.holt@reqres.in",
            "password": "cityslicka"
        }
        response = api_session.post(f"{reqres_url}/login", json=payload)
        response_saver.save("login_success", response)
        assert response.status_code == 200
        assert "token" in response.json()

    def test_login_sem_senha_falha(self, reqres_url, api_session):
        """Testa que login sem senha retorna erro 400."""
        payload = {"email": "peter@klaven"}
        response = api_session.post(f"{reqres_url}/login", json=payload)
        assert response.status_code == 400

    def test_login_email_invalido(self, reqres_url, api_session):
        """Testa login com email nao cadastrado."""
        payload = {
            "email": "usuario_inexistente@teste.com",
            "password": "qualquersenha"
        }
        response = api_session.post(f"{reqres_url}/login", json=payload)
        assert response.status_code == 400


class TestDeleteUser:
    """Testes para o endpoint DELETE /users/{id}"""

    def test_deletar_usuario_retorna_204(self, reqres_url, api_session):
        """Verifica que deletar um usuario retorna 204 No Content."""
        response = api_session.delete(f"{reqres_url}/users/2")
        assert response.status_code == 204
