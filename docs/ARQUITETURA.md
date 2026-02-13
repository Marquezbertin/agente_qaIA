# Arquitetura do QA Agent

## Visao Geral

O QA Agent e um agente de IA construido sobre a API do Claude (Anthropic) usando o padrao **Tool Use**.
O agente pode executar acoes reais no seu ambiente: rodar testes, ler/escrever arquivos, testar APIs, navegar em paginas web e muito mais.

## Diagrama de Fluxo

```
Usuario (Streamlit/CLI)
     |
     v
  app.py / main.py
     |
     v
  API do Claude (messages.create)
     |
     +-- Tool Use: "run_pytest" -------> core/tools.py::run_pytest()
     |                                        |
     |                                   subprocess (pytest)
     |                                        |
     |                                   Resultado REAL
     |
     +-- Tool Use: "run_api_test" -----> core/tools.py::run_api_test()
     |                                        |
     |                                   requests.post/get
     |                                        |
     |                                   Resposta REAL da API
     |
     +-- Tool Use: "create_bug" -------> core/qa_tools.py::create_bug()
     |                                        |
     |                                   SQLite (qa_data.db)
     |
     +-- Tool Use: "save_learning" ----> core/memory.py::add_learning()
     |                                        |
     |                                   SQLite (agent_memory.db)
     |
     +-- Texto final ------------------> Resposta ao usuario
                                              +
                                         Dados REAIS (auto-exibidos)
```

## Principio Fundamental: Anti-Alucinacao

O LLM (Claude) NUNCA e confiavel para exibir dados de API. Por isso:

1. Toda resposta de API e salva em JSON (auditoria) por `_save_audit()`
2. O app.py extrai dados reais do resultado da ferramenta via **codigo Python**
3. Esses dados sao exibidos em blocos separados ("DADOS REAIS")
4. O LLM pode interpretar e comentar, mas os dados brutos vem do codigo

## Modulos Principais

### app.py - Interface Web (Streamlit)
- Loop de Tool Use: envia mensagem → Claude escolhe ferramenta → executa → repete
- `real_data_blocks`: injeta dados reais na resposta (nao depende do LLM)
- Sidebar: ambiente, modelo, explorador de testes, acoes rapidas, memoria

### core/tools.py - Ferramentas de Execucao
- `execute_command()`: Terminal
- `read_file()` / `write_file()`: Arquivos
- `run_pytest()`: Executa testes, parseia stats, escaneia reports/
- `run_api_test()`: Testa endpoints diretamente (HTTP request)
- `get_test_response()`: Le JSONs de resposta salvos pelos testes
- `web_search()`: Busca DuckDuckGo
- `fetch_url()` / `fetch_url_with_js()`: Navega URLs (com/sem JavaScript)

### core/memory.py - Memoria Persistente
- SQLite para aprendizados, historico de conversas, resultados de testes
- `save_learning()` / `search_learnings()`: Aprendizados do agente
- `save_conversation()`: Historico de chat
- `save_test_result()`: Resultados de execucoes

### core/qa_tools.py - Gestao de QA
- Bugs, features, casos de teste, planos de teste, execucoes
- Tudo em SQLite com CRUD completo
- `generate_qa_report()`: Relatorio consolidado

### core/browser.py - Automacao Selenium
- `selenium_navigate()`: Navega para URLs
- `start_user_monitoring()`: Abre browser visivel para o usuario navegar
- `capture_user_state()`: Captura screenshots e estado da pagina
- `stop_user_monitoring()`: Encerra e retorna dados capturados

### core/test_data_db.py - Banco de Dados de Teste
- SQLite com CPFs/CNPJs ficticios para uso em testes
- `get_test_cpfs()` / `get_test_cnpjs()`: Dados para testes de API
- `query_test_data()`: Consulta flexivel

## Como Funciona o Tool Use

1. `app.py` envia mensagem para Claude com `tools=ALL_TOOLS`
2. Claude responde com `tool_use` block (nome + parametros)
3. `process_tool_call()` executa a ferramenta correspondente
4. Resultado e devolvido como `tool_result`
5. Claude recebe o resultado e pode chamar outra ferramenta ou responder
6. Loop repete ate `stop_reason == "end_turn"` (max 10 iteracoes)

## Persistencia

| Banco | Modulo | Conteudo |
|-------|--------|----------|
| `data/agent_memory.db` | memory.py | Aprendizados, conversas, resultados |
| `data/qa_data.db` | qa_tools.py | Bugs, features, test cases, plans |
| `data/sample_test_data.db` | test_data_db.py | CPFs/CNPJs ficticios |

## Configuracao

| Variavel | Arquivo | Descricao |
|----------|---------|-----------|
| `ANTHROPIC_API_KEY` | .env | Chave da API Anthropic |
| `ANTHROPIC_MODEL` | .env | Modelo do Claude |
| `TEST_PROJECT_DIR` | .env | Diretorio do projeto de testes |
| `API_TIMEOUT` | .env | Timeout para chamadas de API |
