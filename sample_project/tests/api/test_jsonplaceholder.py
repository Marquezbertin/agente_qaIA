"""
Testes de API - JSONPlaceholder
================================

Testes usando a API publica JSONPlaceholder (https://jsonplaceholder.typicode.com).
Esta API e gratuita e nao requer autenticacao - perfeita para aprender.

Endpoints testados:
- GET /posts - Listar posts
- GET /posts/{id} - Obter post especifico
- POST /posts - Criar post
- PUT /posts/{id} - Atualizar post
- DELETE /posts/{id} - Deletar post
- GET /users - Listar usuarios
"""

import pytest
import requests


class TestGetPosts:
    """Testes para o endpoint GET /posts"""

    def test_listar_posts_retorna_200(self, base_url, api_session):
        """Verifica que a listagem de posts retorna status 200."""
        response = api_session.get(f"{base_url}/posts")
        assert response.status_code == 200

    def test_listar_posts_retorna_lista(self, base_url, api_session):
        """Verifica que a resposta e uma lista com 100 posts."""
        response = api_session.get(f"{base_url}/posts")
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 100

    def test_post_tem_campos_obrigatorios(self, base_url, api_session):
        """Verifica que cada post tem os campos esperados."""
        response = api_session.get(f"{base_url}/posts/1")
        data = response.json()
        assert "userId" in data
        assert "id" in data
        assert "title" in data
        assert "body" in data

    def test_filtrar_posts_por_usuario(self, base_url, api_session):
        """Testa filtragem de posts por userId via query parameter."""
        response = api_session.get(f"{base_url}/posts", params={"userId": 1})
        data = response.json()
        assert len(data) == 10
        assert all(post["userId"] == 1 for post in data)


class TestGetPostById:
    """Testes para o endpoint GET /posts/{id}"""

    def test_obter_post_existente(self, base_url, api_session):
        """Verifica que um post existente retorna 200."""
        response = api_session.get(f"{base_url}/posts/1")
        assert response.status_code == 200
        assert response.json()["id"] == 1

    def test_obter_post_inexistente_retorna_404(self, base_url, api_session):
        """Verifica que um post inexistente retorna 404."""
        response = api_session.get(f"{base_url}/posts/999999")
        assert response.status_code == 404


class TestCreatePost:
    """Testes para o endpoint POST /posts"""

    def test_criar_post_retorna_201(self, base_url, api_session, response_saver):
        """Verifica que a criacao de um post retorna 201."""
        payload = {
            "title": "Teste QA Agent",
            "body": "Este post foi criado pelo QA Agent como teste.",
            "userId": 1
        }
        response = api_session.post(f"{base_url}/posts", json=payload)

        # Salvar resposta para auditoria
        response_saver.save("create_post", response)

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == payload["title"]
        assert "id" in data

    def test_criar_post_sem_titulo(self, base_url, api_session):
        """Testa criacao de post sem campo obrigatorio (titulo)."""
        payload = {
            "body": "Post sem titulo",
            "userId": 1
        }
        response = api_session.post(f"{base_url}/posts", json=payload)
        # JSONPlaceholder aceita mesmo sem titulo (API fake)
        # Em uma API real, esperariamos 400 Bad Request
        assert response.status_code == 201


class TestUpdatePost:
    """Testes para o endpoint PUT /posts/{id}"""

    def test_atualizar_post_retorna_200(self, base_url, api_session):
        """Verifica que a atualizacao de um post retorna 200."""
        payload = {
            "id": 1,
            "title": "Titulo Atualizado",
            "body": "Corpo atualizado pelo teste.",
            "userId": 1
        }
        response = api_session.put(f"{base_url}/posts/1", json=payload)
        assert response.status_code == 200
        assert response.json()["title"] == "Titulo Atualizado"


class TestDeletePost:
    """Testes para o endpoint DELETE /posts/{id}"""

    def test_deletar_post_retorna_200(self, base_url, api_session):
        """Verifica que a delecao de um post retorna 200."""
        response = api_session.delete(f"{base_url}/posts/1")
        assert response.status_code == 200


class TestGetUsers:
    """Testes para o endpoint GET /users"""

    def test_listar_usuarios_retorna_200(self, base_url, api_session):
        """Verifica que a listagem de usuarios retorna 200."""
        response = api_session.get(f"{base_url}/users")
        assert response.status_code == 200

    def test_usuario_tem_campos_completos(self, base_url, api_session):
        """Verifica que um usuario tem todos os campos esperados."""
        response = api_session.get(f"{base_url}/users/1")
        data = response.json()
        assert "name" in data
        assert "email" in data
        assert "address" in data
        assert "company" in data
