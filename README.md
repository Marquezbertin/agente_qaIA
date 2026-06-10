# QA Agent - Assistente de Testes com IA (Gratuito)

Agente de IA que atua como **QA Engineer Senior** - analisa codigo, executa testes, testa APIs, gerencia bugs e gera relatorios.

**100% gratuito** usando OpenCode com modelos free embutidos.

## Destaques

- **Gratuito** - Usa OpenCode com modelos free (sem chave de API)
- **Multi-provedor** - Claude, GPT ou Gemini (opcional, se tiver chave)
- **Executa testes reais** - Roda pytest, testa APIs, gera relatorios
- **Gestao de QA** - Bugs, features, casos de teste, planos (SQLite)
- **Memoria persistente** - Aprendizados entre sessoes
- **Integracao GitHub** - Issues, PRs, branches
- **Dashboard** - Graficos e metricas (Streamlit)
- **Relatorios PDF** - Exportacao profissional
- **OpenCode MCP** - Ferramentas disponiveis no OpenCode

## Instalacao

```bash
# 1. Clone
git clone https://github.com/Marquezbertin/agente_qaIA
cd agente_qaIA

# 2. Ambiente virtual
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Linux/Mac

# 3. Dependencias
pip install -r requirements.txt

# 4. Banco de dados demo
python scripts/create_sample_db.py

# 5. Instale o OpenCode (CLI gratuita)
winget install -e --id SST.OpenCodeDesktop
```

## Como Usar (Gratis - Recomendado)

```bash
# Entre na pasta e execute:
cd agente_qaIA
opencode

# OU clique duas vezes em:
usar_opencode.bat
```

### Comandos dentro do OpenCode:

| Comando | O que faz |
|---------|-----------|
| `Rode os testes de API` | Executa pytest no projeto exemplo |
| `Teste o endpoint posts` | Testa API JSONPlaceholder |
| `Crie um bug: erro no login` | Registra bug no banco SQLite |
| `Liste os bugs abertos` | Mostra bugs registrados |
| `Gere um relatorio de QA` | Relatorio consolidado |
| `Busque por SQL injection` | Busca no codigo fonte |
| `Crie um PR para a branch fix` | Cria Pull Request no GitHub |

### Comandos customizados (via opencode.json):

```
>test:run tests/api/        # Executa pytest
>test:api posts             # Testa endpoint
>test:coverage              # Cobertura de testes
>qa:bugs                    # Lista bugs
>qa:report                  # Relatorio QA
>app:start                  # Streamlit UI
```

## Como Funciona

```
OpenCode (Gratis) → MCP Server → QA Agent Tools
                                     ├── run_pytest
                                     ├── run_api_test
                                     ├── create_bug / list_bugs
                                     ├── create_pull_request
                                     ├── search_code
                                     └── generate_qa_report
```

O OpenCode usa modelos free e o MCP server expoe todas as ferramentas do QA Agent.

## Interfaces Alternativas

### Streamlit (precisa de chave API)

```bash
streamlit run app.py
```

Suporte a: **Claude** (ANTHROPIC_API_KEY), **GPT** (OPENAI_API_KEY) ou **Gemini** (GEMINI_API_KEY).

Selecione o provedor na sidebar.

### CLI (precisa de chave API)

```bash
python main.py
```

## Configuracao

Copie `.env.example` para `.env` e configure:

```env
# PARA USAR GRATIS: nao precisa configurar nada!
# Basta usar: opencode

# Opcional - provedores pagos:
# ANTHROPIC_API_KEY=sk-...
# OPENAI_API_KEY=sk-...
# GEMINI_API_KEY=...

# Opcional - GitHub:
# GIT_TOKEN=ghp_...
# GIT_REPO=seu-usuario/seu-repo
```

Por padrao usa `sample_project/` com APIs publicas (JSONPlaceholder, ReqRes).
Para usar seu projeto, defina `TEST_PROJECT_DIR` no `.env`.

## Estrutura

```
agente_qaIA/
├── app.py                    # Streamlit UI
├── main.py                   # CLI
├── opencode_mcp_server.py    # MCP server (integracao OpenCode)
├── opencode.json             # Config OpenCode
├── AGENTS.md                 # Instrucoes OpenCode
├── usar_opencode.bat         # Launcher Windows
├── core/
│   ├── tools.py              # Ferramentas (pytest, API, arquivos)
│   ├── browser.py            # Selenium
│   ├── memory.py             # Memoria SQLite
│   ├── qa_tools.py           # Bugs, features, test cases
│   ├── providers.py          # Multi-provedores IA
│   ├── github_tools.py       # GitHub/GitLab
│   ├── report_pdf.py         # Relatorios PDF
│   ├── auth.py               # Autenticacao
│   ├── test_data_db.py       # Dados de teste CPF/CNPJ
│   ├── agent.py              # Agente CLI
│   ├── test_analyzer.py      # Analise de testes
│   ├── test_generator.py     # Geracao de testes
│   ├── test_executor.py      # Execucao de testes
│   └── report_generator.py   # Relatorios HTML/MD
├── sample_project/           # Projeto exemplo
├── tests/                    # 35 self-tests
├── scripts/                  # Utilitarios
├── Dockerfile                # Container
└── docker-compose.yml        # Orquestracao
```

## Testes

```bash
# Testes do projeto exemplo
python -m pytest sample_project/tests/

# Self-tests do QA Agent
python -m pytest tests/
```

## Integracao OpenCode

O QA Agent expoe suas ferramentas via **MCP (Model Context Protocol)**:

```json
{
  "mcp": {
    "qa-agent": {
      "type": "local",
      "command": ["python", "opencode_mcp_server.py"],
      "enabled": true
    }
  }
}
```

O OpenCode detecta automaticamente o `opencode.json` na raiz do projeto.

## Licenca

MIT
