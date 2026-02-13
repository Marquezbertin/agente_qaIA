# Projeto de Testes Exemplo

Este diretorio contem testes de exemplo que funcionam sem nenhuma configuracao adicional.

## APIs Utilizadas

- **JSONPlaceholder** (https://jsonplaceholder.typicode.com) - API REST fake para testes
- **ReqRes.in** (https://reqres.in) - API que simula autenticacao e CRUD

Ambas sao gratuitas e nao requerem cadastro ou API key.

## Como Executar

```bash
# Todos os testes
pytest

# Apenas testes de API
pytest tests/api/

# Apenas testes de seguranca
pytest tests/security/

# Com saida detalhada
pytest -v -s
```

## Estrutura

```
sample_project/
  tests/
    api/
      test_jsonplaceholder.py   # GET, POST, PUT, DELETE em posts e users
      test_reqres.py            # Login, registro, paginacao
    security/
      test_basic_security.py    # Headers, injection, error leaking
    conftest.py                 # Fixtures compartilhadas
  pytest.ini                    # Configuracao do pytest
```
