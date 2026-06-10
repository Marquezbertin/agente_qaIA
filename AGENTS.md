# QA Agent - Instrucoes para OpenCode

## Projeto
Agente de IA para Automacao de QA (Quality Assurance). Executa testes, analisa codigo, gerencia bugs e gera relatorios.

## Estrutura Principal
- `app.py` - Interface web Streamlit
- `main.py` - CLI com Click
- `core/` - Modulos principais (tools, browser, memory, qa_tools, providers, github_tools)
- `config/` - Configuracoes e settings
- `sample_project/` - Projeto de testes exemplo
- `scripts/` - Utilitarios

## Comandos Rapidos
- `python main.py` - CLI interativa
- `streamlit run app.py` - Web UI
- `python scripts/create_sample_db.py` - Criar banco de dados demo
- `python -m pytest sample_project/tests/` - Rodar testes

## Padroes de Codigo
- Python 3.10+
- f-strings para formatacao
- Docstrings para modulos
- Type hints em funcoes
- Nomes em ingles para codigo, portugues para UI/mensagens

## MCP Server
O arquivo `opencode_mcp_server.py` expoe ferramentas do QA Agent via MCP:
- run_pytest, run_api_test, read_file, write_file, search_code
- create_bug, list_bugs, generate_qa_report
- get_repository_structure, execute_command

## Variaveis de Ambiente Necessarias
- `ANTHROPIC_API_KEY` (ou OPENAI_API_KEY / GEMINI_API_KEY)
- `GIT_TOKEN` e `GIT_REPO` para integracao GitHub
