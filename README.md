# QA Agent - Agente de IA para Automacao de Testes

Agente inteligente que atua como **QA Engineer Senior**, capaz de analisar codigo, criar casos de teste, executar testes e gerar relatorios automaticamente.

Construido com a API do Claude (Anthropic) usando o padrao **Tool Use** - o agente tem ferramentas reais para executar acoes no seu projeto.

## Destaques

- **Execucao real de testes** - Roda pytest, analisa resultados, salva evidencias
- **Teste de API direto** - Testa endpoints sem escrever codigo
- **Memoria persistente** - Lembra aprendizados entre sessoes (SQLite)
- **Anti-alucinacao** - Dados de API sao exibidos diretamente pelo codigo Python, nunca pelo LLM
- **Gestao de QA completa** - Bugs, features, casos de teste, planos de teste
- **Browser automation** - Selenium para testes E2E e monitoramento
- **Interface web** - Streamlit com sidebar interativa
- **Interface CLI** - Rich terminal para uso via linha de comando

## Requisitos

- Python 3.10+
- Chave de API da Anthropic ([obtenha aqui](https://console.anthropic.com/))
- Chrome/Chromium (opcional, para testes E2E com Selenium)

## Instalacao

```bash
# 1. Clone o repositorio
git clone https://github.com/Marquezbertin/agente_qaIA
cd qa-agent

# 2. Crie e ative um ambiente virtual
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac

# 3. Instale as dependencias
pip install -r requirements.txt

# 4. Configure sua chave de API
cp .env.example .env
# Edite o arquivo .env e cole sua chave ANTHROPIC_API_KEY

# 5. Crie o banco de dados de demonstracao
python scripts/create_sample_db.py
```

## Como Usar

### Interface Web (Recomendado)

```bash
streamlit run app.py
```

Acesse `http://localhost:8501` no navegador. A interface inclui:
- Chat com o agente
- Seletor de ambiente e modelo
- Explorador de testes (sidebar)
- Acoes rapidas (smoke, security, etc.)
- Monitoramento de browser em tempo real

### Interface CLI

```bash
python main.py
```

Comandos disponiveis no modo interativo:

| Comando | Descricao | Exemplo |
|---------|-----------|---------|
| `analisar <path>` | Analisa codigo e sugere testes | `analisar tests/api/` |
| `criar <feature>` | Cria casos de teste | `criar login` |
| `executar <suite>` | Executa testes | `executar smoke` |
| `relatorio [periodo]` | Gera relatorio | `relatorio today` |
| `cobertura` | Analisa cobertura | `cobertura` |
| `sugerir` | Sugere cenarios | `sugerir` |
| `help` | Mostra ajuda | `help` |
| `sair` | Encerra | `sair` |

## Exemplos de Uso (Chat)

```
> Rode os testes de API
> Teste o endpoint de posts do JSONPlaceholder
> Crie um teste de seguranca para SQL injection
> Registre um bug: botao de login nao responde
> Mostre o historico de testes
> O que voce aprendeu sobre testes de API?
```

Veja mais exemplos no arquivo [GUIA_PROMPTS_QA_AGENT.md](GUIA_PROMPTS_QA_AGENT.md).

## Configurando Seu Projeto

Por padrao, o agente usa o `sample_project/` com APIs publicas (JSONPlaceholder, ReqRes).

Para usar com **seu proprio projeto de testes**:

1. Defina a variavel de ambiente `TEST_PROJECT_DIR` no `.env`:
   ```
   TEST_PROJECT_DIR=C:\caminho\para\seu\projeto
   ```

2. O agente vai detectar automaticamente os testes dentro dessa pasta.

3. Se sua API precisa de autenticacao, crie um `.env` dentro do seu projeto com `API_TOKEN` e `API_BASE_URL`.

## Arquitetura

```
qa-agent/
├── app.py                   # Interface web (Streamlit)
├── main.py                  # Interface CLI (Click + Rich)
├── .env.example             # Template de configuracao
├── requirements.txt         # Dependencias Python
├── config/
│   └── settings.py          # Configuracoes do agente
├── core/
│   ├── tools.py             # Ferramentas de execucao (Tool Use)
│   ├── browser.py           # Automacao Selenium
│   ├── memory.py            # Memoria persistente (SQLite)
│   ├── qa_tools.py          # Gestao de QA (bugs, features, test cases)
│   ├── test_data_db.py      # Banco de dados de teste (CPF/CNPJ demo)
│   ├── agent.py             # Agente principal (CLI)
│   ├── knowledge_manager.py # Indexacao de repositorios
│   ├── knowledge_base.py    # RAG com TF-IDF
│   ├── test_analyzer.py     # Analise de testes existentes
│   ├── test_generator.py    # Geracao de novos testes
│   ├── test_executor.py     # Execucao de suites pytest
│   └── report_generator.py  # Geracao de relatorios
├── scripts/
│   └── create_sample_db.py  # Cria banco de dados demo
├── sample_project/          # Projeto de testes exemplo
│   ├── tests/
│   │   ├── api/             # Testes de API (JSONPlaceholder, ReqRes)
│   │   ├── security/        # Testes de seguranca
│   │   └── conftest.py      # Fixtures compartilhadas
│   └── pytest.ini           # Configuracao pytest
├── data/                    # Banco SQLite de dados de teste
├── docs/                    # Documentacao adicional
└── LICENSE                  # MIT
```

## Como Funciona (Tool Use)

O agente usa o padrao **Tool Use** da API do Claude:

1. Usuario envia mensagem
2. Claude analisa e decide qual ferramenta usar
3. O codigo Python executa a ferramenta (ex: `run_pytest`, `run_api_test`)
4. O resultado REAL e devolvido ao Claude
5. Claude interpreta e responde ao usuario
6. Dados reais sao exibidos diretamente pelo codigo (nunca pelo LLM)

Este loop pode repetir ate 10 vezes por mensagem, permitindo que o agente execute fluxos complexos automaticamente.

## Licenca

MIT - Veja [LICENSE](LICENSE) para detalhes.
