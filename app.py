"""
QA Agent - Interface Web com Tool Use e Memoria
===============================================

Agente de IA completo com:
- Execucao real de comandos e testes
- Memoria persistente (SQLite) para aprendizados
- Historico de conversas e resultados

Executar: streamlit run app.py
"""

import streamlit as st
import os
import sys
from pathlib import Path
import json
import uuid

# Adicionar path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from anthropic import Anthropic
from core.tools import TOOLS_DEFINITION, execute_tool, set_environment, get_current_environment, ENVIRONMENTS
from core.browser import BROWSER_TOOLS_DEFINITION, execute_browser_tool, get_monitoring_status
from core.memory import (
    MEMORY_TOOLS, execute_memory_tool, get_context_for_agent,
    save_conversation, get_conversation_history, add_learning,
    search_learnings, save_test_result
)
from core.qa_tools import QA_TOOLS_DEFINITION, execute_qa_tool
from core.test_data_db import TEST_DATA_DB_TOOLS, execute_test_data_tool

# Configuracao da pagina
st.set_page_config(
    page_title="QA Agent - Assistente de Testes",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Combinar todas as ferramentas
ALL_TOOLS = TOOLS_DEFINITION + MEMORY_TOOLS + BROWSER_TOOLS_DEFINITION + QA_TOOLS_DEFINITION + TEST_DATA_DB_TOOLS

# Ferramentas que NAO devem ser usadas durante monitoramento
EXCLUDED_DURING_MONITORING = ["selenium_navigate", "selenium_interact", "selenium_check_errors"]


def get_available_tools():
    """Retorna ferramentas disponiveis baseado no estado atual"""
    monitoring_status = get_monitoring_status()

    if monitoring_status.get("active"):
        # Durante monitoramento, excluir ferramentas que interferem
        return [tool for tool in ALL_TOOLS if tool.get("name") not in EXCLUDED_DURING_MONITORING]
    return ALL_TOOLS

# Diretorio base do projeto de testes
# Configuravel via variavel de ambiente TEST_PROJECT_DIR
# Se nao definido, usa a pasta sample_project/ inclusa no agente
PROJECT_DIR = Path(os.getenv("TEST_PROJECT_DIR", str(Path(__file__).parent / "sample_project")))

# Estrutura de pastas de testes do projeto
# Personalize com as pastas do seu projeto de testes
TEST_FOLDERS = {
    "🌐 api": {
        "path": "tests/api",
        "description": "Testes de API (JSONPlaceholder, ReqRes)",
        "marker": "api"
    },
    "🛡️ security": {
        "path": "tests/security",
        "description": "Testes de seguranca (headers, injection, XSS)",
        "marker": "security"
    },
    "🧪 all tests": {
        "path": "tests",
        "description": "Todos os testes do projeto",
        "marker": ""
    }
}


def get_folder_contents(folder_path: Path, max_items: int = 50):
    """Retorna conteudo de uma pasta com informacoes uteis"""
    items = {"folders": [], "test_files": [], "docs": [], "configs": []}

    if not folder_path.exists():
        return items

    try:
        for item in sorted(folder_path.iterdir())[:max_items]:
            name = item.name

            # Ignorar pastas especiais
            if name.startswith('.') or name in ['__pycache__', 'venv', '.venv', 'node_modules']:
                continue

            if item.is_dir():
                # Contar arquivos de teste na pasta
                test_count = len(list(item.glob("**/test_*.py"))) + len(list(item.glob("**/*_test.py")))
                items["folders"].append({
                    "name": name,
                    "path": str(item),
                    "test_count": test_count
                })
            elif item.is_file():
                if name.startswith("test_") or name.endswith("_test.py"):
                    items["test_files"].append({"name": name, "path": str(item)})
                elif name.endswith(('.md', '.txt', '.rst')):
                    items["docs"].append({"name": name, "path": str(item)})
                elif name in ['conftest.py', 'pytest.ini', '.env', 'requirements.txt', 'config.py']:
                    items["configs"].append({"name": name, "path": str(item)})
    except Exception:
        pass

    return items


def get_system_prompt():
    """Gera o system prompt com contexto expandido"""
    memory_context = get_context_for_agent()
    # Aumentado limite de memoria
    if len(memory_context) > 2000:
        memory_context = memory_context[:2000] + "..."

    # Incluir tarefa ativa se existir
    active_task_context = ""
    if st.session_state.get("active_task"):
        active_task_context = f"""
TAREFA ATIVA (NAO ESQUECA!):
{st.session_state.active_task}
---
"""

    return f"""Voce e o QA Agent - Engenheiro de QA Senior com acesso completo ao projeto de testes.

{active_task_context}
REGRA CRITICA: SEMPRE lembre da tarefa original que o usuario pediu.

PROJETO BASE: {str(PROJECT_DIR)}

=====================================================================
REGRA #1: COMO TESTAR ENDPOINTS
=====================================================================
Para QUALQUER pedido de teste de endpoint/API, use run_api_test.
run_api_test faz a requisicao HTTP direto, com headers corretos.

EXEMPLO - Testar endpoint:
  run_api_test(endpoint_name="posts")
  run_api_test(endpoint_name="reqres_login", data={{"email": "eve.holt@reqres.in", "password": "cityslicka"}})

Para lista completa: list_api_endpoints()

Para obter dados de teste do banco:
  get_test_cpfs(5) ou get_test_cnpjs(5) → dados ficticios do banco SQLite

=====================================================================
RODAR TESTES EXISTENTES
=====================================================================
Use run_pytest para executar suites de teste:
  run_pytest() → todos os testes
  run_pytest(test_path="tests/api/test_jsonplaceholder.py")
  run_pytest(test_path="tests/security/test_basic_security.py")

=====================================================================
CRIAR SCRIPTS PYTEST (so quando pedido)
=====================================================================
SOMENTE crie scripts Python se o usuario pedir explicitamente.
Para testes simples de endpoint, use run_api_test.

Template basico:
```python
import pytest
import requests

class TestMeuTeste:
    def test_exemplo(self, api_session, base_url, response_saver):
        response = api_session.get(f"{{base_url}}/posts/1")
        response_saver.save("test_exemplo", response)
        assert response.status_code == 200
```

=====================================================================
REGRA MAIS IMPORTANTE: NUNCA ALUCINAR DADOS
=====================================================================
PROIBIDO inventar, fabricar ou resumir dados de resposta da API.
- Copie EXATAMENTE o campo "response_body" do resultado da ferramenta run_api_test
- Mostre o JSON COMPLETO em um bloco ```json ... ```
- NUNCA invente campos, valores ou qualquer outro dado
- Se nao tiver response_body, diga "sem dados de resposta"

Para JSONs de testes executados:
- Use get_test_response(pattern="NOME") para ler o arquivo REAL
- NUNCA invente o conteudo do JSON. O sistema auto-exibe o JSON real na tela.

Para resultados de testes (run_pytest):
- Mostre EXATAMENTE os numeros dos campos "stats" e "pass_rate" do resultado
- NUNCA invente contagens de testes passed/failed

=====================================================================
FERRAMENTAS DISPONIVEIS
=====================================================================
- run_api_test: Testar endpoint direto
- list_api_endpoints: Listar endpoints disponiveis
- get_test_response: Ver JSON REAL de resposta dos testes
- get_test_cpfs/get_test_cnpjs/query_test_data/get_test_data_summary: Dados do banco SQLite de demonstracao
- run_pytest: Executar suites pytest
- read_file/write_file: Ler/editar arquivos
- execute_command: Terminal
- search_in_files: Buscar codigo
- save_learning/search_memory: Memoria persistente
- selenium_navigate/interact: Browser headless
- start_user_monitoring/capture_user_state/stop_user_monitoring: Monitoramento de usuario
- QA: create_bug, list_bugs, create_feature, create_test_case, create_test_plan, generate_qa_report

MEMORIA: {memory_context}

Responda SEMPRE em portugues."""


def init_session_state():
    """Inicializa estado da sessao"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "environment" not in st.session_state:
        st.session_state.environment = "Desenvolvimento"
    if "tool_calls" not in st.session_state:
        st.session_state.tool_calls = []
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())[:8]
    if "active_task" not in st.session_state:
        st.session_state.active_task = None
    if "model_choice" not in st.session_state:
        st.session_state.model_choice = "claude-3-haiku-20240307"
    if "monitoring_active" not in st.session_state:
        st.session_state.monitoring_active = False


def get_client():
    """Retorna cliente Anthropic"""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        return Anthropic(api_key=api_key)
    return None


def process_tool_call(tool_name: str, tool_input: dict) -> str:
    """Processa uma chamada de ferramenta"""

    # PROTECAO: Se monitoramento esta ativo, bloquear ferramentas conflitantes
    monitoring_status = get_monitoring_status()
    if monitoring_status.get("active") and tool_name in EXCLUDED_DURING_MONITORING:
        return json.dumps({
            "success": False,
            "error": f"BLOQUEADO: O monitoramento de usuario esta ATIVO. Voce NAO pode usar '{tool_name}' agora. Use apenas: capture_user_state, stop_user_monitoring, ou get_monitoring_status. Aguarde o usuario navegar e dizer quando capturar ou encerrar.",
            "monitoring_active": True,
            "allowed_tools": ["capture_user_state", "stop_user_monitoring", "get_monitoring_status"]
        })

    # Verificar se e ferramenta de memoria
    if tool_name in ["save_learning", "search_memory", "get_test_history"]:
        return execute_memory_tool(tool_name, tool_input)
    # Verificar se e ferramenta de browser (incluindo novas de monitoramento)
    elif tool_name in ["selenium_navigate", "selenium_interact", "selenium_screenshot", "selenium_check_errors", "selenium_find_element", "run_selenium_test", "run_cypress_test", "run_playwright_test", "start_user_monitoring", "capture_user_state", "stop_user_monitoring", "get_monitoring_status"]:
        return execute_browser_tool(tool_name, tool_input)
    # Verificar se e ferramenta de QA (bugs, features, test cases, plans)
    elif tool_name in ["create_bug", "list_bugs", "get_bug", "update_bug", "create_feature", "list_features", "update_feature", "create_test_case", "list_test_cases", "get_test_case", "create_test_plan", "add_test_case_to_plan", "list_test_plans", "get_test_plan", "update_test_plan_status", "record_test_execution", "get_execution_history", "generate_qa_report"]:
        return execute_qa_tool(tool_name, tool_input)
    # Verificar se e ferramenta de dados de teste (CPF/CNPJ)
    elif tool_name in ["get_test_cpfs", "get_test_cnpjs", "query_test_data", "get_test_data_summary"]:
        return execute_test_data_tool(tool_name, tool_input)
    else:
        result = execute_tool(tool_name, tool_input)

        # Se foi um teste, salvar resultado
        if tool_name == "run_pytest":
            try:
                result_dict = json.loads(result)
                stats = result_dict.get("stats", {})
                save_test_result(
                    test_path=tool_input.get("test_path", "all"),
                    passed=stats.get("passed", 0),
                    failed=stats.get("failed", 0),
                    skipped=stats.get("skipped", 0),
                    duration=0,
                    output=result_dict.get("output", "")[:5000]
                )
            except:
                pass

        return result


def chat_with_agent(client, user_message: str) -> str:
    """
    Envia mensagem para o agente com suporte a Tool Use.
    Versao simplificada sem atualizacoes de DOM durante execucao.
    """
    if not client:
        return "Erro: API key nao configurada. Verifique o arquivo .env"

    # Salvar mensagem do usuario
    save_conversation(st.session_state.session_id, "user", user_message)

    # Preparar historico (aumentado para manter contexto)
    messages = []

    # Se temos uma tarefa ativa, incluir como contexto
    if st.session_state.get("active_task"):
        messages.append({
            "role": "user",
            "content": f"[TAREFA ATIVA - NAO ESQUECER]: {st.session_state.active_task}"
        })
        messages.append({
            "role": "assistant",
            "content": "Entendido, vou manter essa tarefa em mente durante toda nossa conversa."
        })

    # Aumentado de 4 para 20 mensagens para manter contexto
    for msg in st.session_state.messages[-20:]:
        messages.append({
            "role": msg["role"],
            "content": msg["content"]
        })

    messages.append({
        "role": "user",
        "content": user_message
    })

    full_response = ""
    tool_results_list = []  # Lista de ferramentas executadas
    real_data_blocks = []   # Dados reais das APIs/testes (nunca depende do LLM)

    try:
        # Loop de execucao de ferramentas
        iterations = 0
        max_iterations = 10

        while iterations < max_iterations:
            iterations += 1

            # Definir max_tokens baseado no modelo
            model = st.session_state.model_choice
            if "haiku" in model:
                max_tokens = 4096
            elif "sonnet" in model:
                max_tokens = 8192
            else:  # opus
                max_tokens = 8192

            # Usar ferramentas disponiveis baseado no estado de monitoramento
            available_tools = get_available_tools()

            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=get_system_prompt(),
                tools=available_tools,
                messages=messages
            )

            # Processar resposta
            assistant_content = []
            has_tool_use = False

            for block in response.content:
                if block.type == "text":
                    full_response += block.text

                elif block.type == "tool_use":
                    has_tool_use = True
                    tool_name = block.name
                    tool_input = block.input
                    tool_use_id = block.id

                    # Icones das ferramentas
                    tool_icons = {
                        "run_pytest": "🧪",
                        "read_file": "📄",
                        "write_file": "📝",
                        "execute_command": "💻",
                        "list_directory": "📁",
                        "search_in_files": "🔍",
                        "save_learning": "🧠",
                        "search_memory": "💭",
                        "get_test_history": "📊",
                        "fetch_url_with_js": "🌐",
                        "selenium_navigate": "🖥️",
                        "web_search": "🔎",
                        "run_api_test": "🎯",
                        "list_api_endpoints": "📋"
                    }
                    icon = tool_icons.get(tool_name, "⚙️")

                    # Executar ferramenta
                    tool_result = process_tool_call(tool_name, tool_input)

                    # Guardar para exibicao na sidebar
                    st.session_state.tool_calls.append({
                        "tool": tool_name,
                        "input": tool_input,
                        "result": tool_result[:500]
                    })

                    # Determinar status
                    status_icon = "✅"
                    result_json = {}
                    try:
                        result_json = json.loads(tool_result)
                        if tool_name == "run_pytest":
                            test_status = result_json.get("test_status", "")
                            if test_status == "all_passed":
                                status_icon = "✅"
                            elif test_status == "tests_failed":
                                status_icon = "⚠️"
                            else:
                                status_icon = "❌"
                        elif tool_name == "run_api_test":
                            if result_json.get("test_passed"):
                                status_icon = "✅"
                            elif result_json.get("success") and not result_json.get("test_passed"):
                                status_icon = "⚠️"
                            else:
                                status_icon = "❌"
                        elif not result_json.get("success", True):
                            error_msg = result_json.get('error', result_json.get('stderr', ''))
                            if error_msg:
                                status_icon = "❌"
                    except:
                        pass

                    # Info da ferramenta para o resumo
                    tool_info = f"{icon} {tool_name}"
                    if tool_name == "run_pytest":
                        test_path_display = tool_input.get('test_path', 'all')
                        if test_path_display and len(test_path_display) > 30:
                            test_path_display = Path(test_path_display).name or 'all'
                        pass_rate = result_json.get("pass_rate", "")
                        stats = result_json.get("stats", {})
                        tool_info += f"(`{test_path_display}`)"
                        if pass_rate and pass_rate != "N/A":
                            total = result_json.get("total_tests", 0)
                            tool_info += f" {stats.get('passed',0)}/{total} {pass_rate}"
                    elif tool_name == "run_api_test":
                        ep_name = tool_input.get('endpoint_name', '') or tool_input.get('endpoint_path', 'custom')
                        status_code = result_json.get("status_code", "?")
                        resp_time = result_json.get("response_time_seconds", "")
                        env_used = result_json.get("environment", "")
                        tool_info += f"(`{ep_name}`) HTTP {status_code}"
                        if resp_time:
                            tool_info += f" {resp_time}s"
                        if env_used:
                            tool_info += f" [{env_used}]"
                    tool_results_list.append(f"{tool_info} {status_icon}")

                    # =====================================================
                    # AUTO-EXIBICAO DE DADOS REAIS (nao depende do LLM)
                    # =====================================================
                    if result_json:
                        if tool_name == "run_api_test":
                            # Mostrar response_body REAL da API
                            body = result_json.get("response_body")
                            ep = result_json.get("endpoint", "")
                            env = result_json.get("environment", "")
                            status = result_json.get("status_code", "?")
                            elapsed = result_json.get("response_time_seconds", "")
                            if body is not None:
                                if isinstance(body, (dict, list)):
                                    body_str = json.dumps(body, ensure_ascii=False, indent=2)
                                else:
                                    body_str = str(body)
                                audit = result_json.get("audit_file", "")
                                audit_info = f"\n📁 Auditoria: `{Path(audit).name}`" if audit and not audit.startswith("Erro") else ""
                                header = f"📡 **Resposta REAL da API** | `{ep}` | HTTP {status} | {elapsed}s | [{env}]{audit_info}"
                                real_data_blocks.append(f"{header}\n```json\n{body_str}\n```")
                            elif result_json.get("error"):
                                real_data_blocks.append(f"❌ **Erro API** `{ep}`: {result_json['error']}")

                        elif tool_name == "run_pytest":
                            # Mostrar stats REAIS dos testes
                            s = result_json.get("stats", {})
                            total = result_json.get("total_tests", 0)
                            pr = result_json.get("pass_rate", "N/A")
                            env = result_json.get("environment", "")
                            ts = result_json.get("test_status", "")
                            cmd = result_json.get("command", "")
                            audit = result_json.get("audit_file", "")
                            audit_info = f" | 📁 `{Path(audit).name}`" if audit and not audit.startswith("Erro") else ""
                            block = f"🧪 **Resultado REAL dos testes** [{env}]{audit_info}\n"
                            block += f"- **Passed:** {s.get('passed', 0)} | **Failed:** {s.get('failed', 0)} | **Skipped:** {s.get('skipped', 0)} | **Total:** {total}\n"
                            block += f"- **Taxa de sucesso:** {pr}\n"
                            block += f"- **Status:** {ts}"
                            if s.get('failed', 0) > 0:
                                # Extrair linhas FAILED do output real
                                output = result_json.get("output", "")
                                failed_lines = [l for l in output.split('\n') if 'FAILED' in l]
                                if failed_lines:
                                    block += "\n- **Falhas:**\n"
                                    for fl in failed_lines[:20]:
                                        block += f"  - `{fl.strip()}`\n"
                            real_data_blocks.append(block)

                        elif tool_name == "run_python_script":
                            # Mostrar stdout REAL do script
                            output = result_json.get("output", "")
                            script = result_json.get("script_path", "")
                            if output:
                                real_data_blocks.append(f"📜 **Output REAL** `{Path(script).name}`\n```\n{output[:10000]}\n```")

                        elif tool_name in ("get_test_cpfs", "get_test_cnpjs"):
                            # Mostrar lista REAL de CPFs/CNPJs
                            cpf_list = result_json.get("cpf_list") or result_json.get("cnpj_list")
                            if cpf_list:
                                label = "CPFs" if "cpf" in tool_name else "CNPJs"
                                real_data_blocks.append(f"📋 **{label} reais do banco:** `{', '.join(cpf_list)}`")

                        elif tool_name == "query_test_data":
                            # Mostrar registros REAIS do banco
                            records = result_json.get("results") or result_json.get("records")
                            if records:
                                records_str = json.dumps(records, ensure_ascii=False, indent=2)
                                if len(records_str) > 50000:
                                    records_str = records_str[:50000] + "\n... [truncado]"
                                real_data_blocks.append(f"📋 **Dados reais do banco** ({len(records)} registros)\n```json\n{records_str}\n```")

                        elif tool_name == "get_test_response":
                            # Mostrar JSON REAL dos testes - direto do arquivo, sem LLM
                            resp_results = result_json.get("results", [])
                            for r in resp_results:
                                content = r.get("content")
                                fname = r.get("file", "")
                                if content:
                                    content_str = json.dumps(content, ensure_ascii=False, indent=2)
                                    sc = content.get("status_code", "?")
                                    tname = content.get("test_name", "")
                                    ep = content.get("endpoint", "")
                                    ok = content.get("success", False)
                                    si = "✅" if ok else "❌"
                                    elapsed = content.get("elapsed_ms", 0)
                                    elapsed_s = f"{elapsed/1000:.1f}s" if elapsed else ""
                                    real_data_blocks.append(
                                        f"{si} **JSON REAL** `{tname}` | `{ep}` | HTTP {sc} | {elapsed_s} | 📁 `{fname}`\n```json\n{content_str}\n```"
                                    )
                                elif r.get("error"):
                                    real_data_blocks.append(f"❌ Erro ao ler `{fname}`: {r['error']}")
                            if not resp_results and result_json.get("available_files"):
                                avail = result_json["available_files"][:15]
                                real_data_blocks.append(
                                    f"📁 **Arquivos disponíveis** ({len(avail)}):\n" +
                                    "\n".join(f"- `{f}`" for f in avail)
                                )

                    assistant_content.append({
                        "type": "tool_use",
                        "id": tool_use_id,
                        "name": tool_name,
                        "input": tool_input
                    })

                    # Adicionar para proxima iteracao
                    messages.append({"role": "assistant", "content": assistant_content})
                    messages.append({
                        "role": "user",
                        "content": [{
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": tool_result
                        }]
                    })
                    assistant_content = []

            # Se nao houve tool_use ou end_turn, terminamos
            if not has_tool_use or response.stop_reason == "end_turn":
                break

        # Montar resposta final
        # 1. Dados reais (injetados pelo codigo Python, nao pelo LLM)
        real_data_section = ""
        if real_data_blocks:
            real_data_section = "\n\n---\n📊 **DADOS REAIS (gerados pelo codigo, nao pelo LLM):**\n\n"
            real_data_section += "\n\n".join(real_data_blocks)

        # 2. Rodape com ferramentas executadas
        tools_summary = ""
        if tool_results_list:
            tools_summary = "\n\n---\n**Ferramentas executadas:**\n" + " | ".join(tool_results_list)

        final_response = full_response + real_data_section + tools_summary

        # Salvar resposta na memoria
        save_conversation(st.session_state.session_id, "assistant", final_response)

        return final_response

    except Exception as e:
        error_msg = f"Erro: {str(e)}"
        return error_msg


def main():
    # Inicializar
    init_session_state()
    client = get_client()

    # === HEADER ===
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("🤖 QA Agent")
        st.caption("Assistente de QA com execucao real e memoria persistente")
    with col2:
        status = "🟢 Online" if client else "🔴 Offline"
        st.metric("Status", status)
        st.caption(f"Sessao: {st.session_state.session_id}")

    st.divider()

    # === SIDEBAR ===
    with st.sidebar:
        st.header("⚙️ Configuracoes")

        env_options = list(ENVIRONMENTS.keys())
        env = st.selectbox(
            "Ambiente",
            env_options,
            index=env_options.index(st.session_state.environment) if st.session_state.environment in env_options else 0
        )

        # Sincronizar com ferramentas
        if env != st.session_state.environment:
            st.session_state.environment = env
            set_environment(env)  # Atualizar ambiente nas ferramentas

        # Mostrar info do ambiente
        env_info = ENVIRONMENTS.get(env, {})
        st.caption(f"🌐 API: {env_info.get('api_base_url', 'N/A')}")
        st.caption(f"📁 Testes: {env_info.get('test_dir', 'N/A')}")

        st.divider()

        # Selecao de modelo
        st.subheader("🤖 Modelo")
        model_options = {
            "Haiku (Rapido)": "claude-3-haiku-20240307",
            "Sonnet (Equilibrado)": "claude-sonnet-4-20250514",
            "Opus (Poderoso)": "claude-opus-4-20250514"
        }
        selected_model = st.selectbox(
            "Modelo Claude",
            options=list(model_options.keys()),
            index=0 if st.session_state.model_choice == "claude-3-haiku-20240307" else
                  1 if st.session_state.model_choice == "claude-sonnet-4-20250514" else 2
        )
        st.session_state.model_choice = model_options[selected_model]
        st.caption("Sonnet/Opus melhor para tarefas complexas")

        st.divider()

        # Tarefa ativa
        st.subheader("📋 Tarefa Ativa")
        if st.session_state.active_task:
            st.info(st.session_state.active_task[:100] + "..." if len(st.session_state.active_task) > 100 else st.session_state.active_task)
            if st.button("❌ Limpar Tarefa", use_container_width=True):
                st.session_state.active_task = None
                st.rerun()
        else:
            st.caption("Nenhuma tarefa ativa")
            new_task = st.text_area("Definir tarefa:", height=80, placeholder="Ex: Abrir pagina X e monitorar minhas acoes")
            if st.button("✅ Definir Tarefa", use_container_width=True) and new_task:
                st.session_state.active_task = new_task
                st.rerun()

        st.divider()

        # Status de monitoramento
        st.subheader("👁️ Monitoramento")
        monitoring_status = get_monitoring_status()
        if monitoring_status.get("active"):
            st.success("🟢 NAVEGADOR ABERTO")
            st.caption(f"Sessao: {monitoring_status.get('session_name', 'default')}")
            st.caption(f"Capturas: {monitoring_status.get('screenshots_taken', 0)}")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📸 Capturar", use_container_width=True, help="Capturar estado atual"):
                    st.session_state.pending_message = "Capture o estado atual da página (screenshot, URL, elementos)"
            with col2:
                if st.button("🛑 Encerrar", use_container_width=True, help="Encerrar monitoramento"):
                    st.session_state.pending_message = "Encerre o monitoramento e me mostre todos os dados capturados"
        else:
            st.caption("🔴 Nenhum monitoramento ativo")

        st.divider()

        # === EXPLORADOR DE TESTES ===
        st.header("📂 Explorador de Testes")

        # Selecionar pasta principal
        selected_folder = st.selectbox(
            "Selecione uma pasta:",
            options=list(TEST_FOLDERS.keys()),
            format_func=lambda x: x
        )

        if selected_folder:
            folder_info = TEST_FOLDERS[selected_folder]
            folder_path = PROJECT_DIR / folder_info["path"]

            st.caption(f"📝 {folder_info['description']}")

            # Botoes de acao para a pasta
            col1, col2 = st.columns(2)
            with col1:
                if st.button("▶️ Rodar", key=f"run_{selected_folder}", use_container_width=True):
                    marker_cmd = f' com marker {folder_info["marker"]}' if folder_info["marker"] else ''
                    st.session_state.pending_message = f"Execute os testes da pasta {folder_info['path']}{marker_cmd}"
            with col2:
                if st.button("📖 Analisar", key=f"analyze_{selected_folder}", use_container_width=True):
                    st.session_state.pending_message = f"Analise a estrutura e os testes da pasta {folder_info['path']} e me de um resumo"

            # Mostrar conteudo da pasta
            contents = get_folder_contents(folder_path)

            # Subpastas
            if contents["folders"]:
                with st.expander(f"📁 Subpastas ({len(contents['folders'])})", expanded=False):
                    for folder in contents["folders"][:15]:
                        test_badge = f" ({folder['test_count']} testes)" if folder['test_count'] > 0 else ""
                        if st.button(f"📁 {folder['name']}{test_badge}", key=f"folder_{folder['name']}", use_container_width=True):
                            st.session_state.pending_message = f"Liste os arquivos de teste na pasta {folder['path']} e descreva o que cada um testa"

            # Arquivos de teste
            if contents["test_files"]:
                with st.expander(f"🧪 Testes ({len(contents['test_files'])})", expanded=True):
                    for test in contents["test_files"][:20]:
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.text(f"🧪 {test['name']}")
                        with col2:
                            if st.button("▶️", key=f"run_test_{test['name']}", help="Rodar teste"):
                                st.session_state.pending_message = f"Execute o teste {test['path']}"

            # Documentos
            if contents["docs"]:
                with st.expander(f"📄 Docs ({len(contents['docs'])})", expanded=False):
                    for doc in contents["docs"][:10]:
                        if st.button(f"📄 {doc['name']}", key=f"doc_{doc['name']}", use_container_width=True):
                            st.session_state.pending_message = f"Leia e me mostre o conteudo do arquivo {doc['path']}"

            # Configs
            if contents["configs"]:
                with st.expander(f"⚙️ Configs ({len(contents['configs'])})", expanded=False):
                    for cfg in contents["configs"]:
                        if st.button(f"⚙️ {cfg['name']}", key=f"cfg_{cfg['name']}", use_container_width=True):
                            st.session_state.pending_message = f"Leia e analise o arquivo de configuracao {cfg['path']}"

        st.divider()

        # === COMANDOS RAPIDOS ===
        st.header("⚡ Acoes Rapidas")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🧪 Smoke", use_container_width=True, help="Testes de smoke"):
                st.session_state.pending_message = "Execute os testes de smoke do ambiente atual"
        with col2:
            if st.button("🛡️ Security", use_container_width=True, help="Testes de seguranca"):
                st.session_state.pending_message = "Execute os testes de seguranca"

        col1, col2 = st.columns(2)
        with col1:
            if st.button("📊 Historico", use_container_width=True, help="Ver historico"):
                st.session_state.pending_message = "Mostre o historico das ultimas execucoes de teste"
        with col2:
            if st.button("🔍 Buscar", use_container_width=True, help="Buscar nos testes"):
                st.session_state.pending_message = "O que voce gostaria de buscar nos arquivos de teste?"

        st.divider()

        # === MEMORIA ===
        st.header("🧠 Memoria")

        if st.button("Ver Aprendizados", use_container_width=True):
            st.session_state.pending_message = "Mostre todos os aprendizados que voce tem na memoria"

        # Input para ensinar algo novo
        with st.expander("➕ Ensinar algo novo"):
            new_learning = st.text_area("O que quer me ensinar?", height=100)
            if st.button("Salvar Aprendizado") and new_learning:
                st.session_state.pending_message = f"Aprenda e salve na memoria: {new_learning}"

        st.divider()

        # === FERRAMENTAS USADAS ===
        if st.session_state.tool_calls:
            st.header("🔧 Ultimas Ferramentas")
            for tc in st.session_state.tool_calls[-5:]:
                with st.expander(f"{tc['tool']}", expanded=False):
                    st.json(tc['input'])

        st.divider()

        if st.button("🗑️ Limpar Conversa", use_container_width=True):
            st.session_state.messages = []
            st.session_state.tool_calls = []
            st.rerun()

    # === CHAT ===

    # Mensagem de boas-vindas
    if not st.session_state.messages:
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown("""
**Ola! Sou o QA Agent com poderes de execucao e memoria!** 🚀

### O que posso fazer:

| Acao | Exemplo |
|------|---------|
| 🧪 **Rodar testes** | "Execute os testes de seguranca" |
| 📄 **Ler arquivos** | "Mostre o arquivo conftest.py" |
| 📝 **Criar testes** | "Crie um teste para validar CPF" |
| 🔍 **Buscar codigo** | "Busque por SQL injection" |
| 🧠 **Aprender** | "Lembre que X precisa de Y" |
| 💭 **Lembrar** | "O que voce sabe sobre testes de API?" |

### Memoria Persistente:
Tudo que voce me ensinar fica salvo em um banco SQLite.
Na proxima vez que abrir, eu vou lembrar!

**Experimente:** *"Rode os testes de smoke"* ou *"O que voce ja aprendeu?"*
            """)

    # Processar mensagem pendente (dos botoes)
    if "pending_message" in st.session_state and st.session_state.pending_message:
        pending = st.session_state.pending_message
        st.session_state.pending_message = None

        st.session_state.messages.append({"role": "user", "content": pending})

        with st.chat_message("user", avatar="👤"):
            st.markdown(pending)

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("🤔 Processando..."):
                response = chat_with_agent(client, pending)
            st.markdown(response)

        st.session_state.messages.append({"role": "assistant", "content": response})

    # Exibir historico
    for message in st.session_state.messages:
        avatar = "👤" if message["role"] == "user" else "🤖"
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])

    # Input do usuario
    if prompt := st.chat_input("Digite sua pergunta ou comando..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("🤔 Processando..."):
                response = chat_with_agent(client, prompt)
            st.markdown(response)

        st.session_state.messages.append({"role": "assistant", "content": response})


if __name__ == "__main__":
    main()
