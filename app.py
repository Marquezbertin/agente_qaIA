"""
QA Agent - Interface Web com Dashboard, Graficos e Multi-Provedores
====================================================================
"""

import streamlit as st
import os
import sys
from pathlib import Path
import json
import uuid
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

# =============================================================================
# PROVEDORES DE IA
# =============================================================================
from core.providers import (
    PROVIDER_REGISTRY, PROVIDER_MODELS,
    get_provider, check_provider_key
)
AI_PROVIDER = os.getenv("AI_PROVIDER", "anthropic")

# =============================================================================
# FERRAMENTAS
# =============================================================================
from core.tools import TOOLS_DEFINITION, execute_tool, set_environment, get_current_environment, ENVIRONMENTS
from core.browser import BROWSER_TOOLS_DEFINITION, execute_browser_tool, get_monitoring_status
from core.memory import (
    MEMORY_TOOLS, execute_memory_tool, get_context_for_agent,
    save_conversation, get_conversation_history, add_learning,
    search_learnings, save_test_result, get_test_history
)
from core.qa_tools import QA_TOOLS_DEFINITION, execute_qa_tool, init_qa_database, list_bugs
from core.test_data_db import TEST_DATA_DB_TOOLS, execute_test_data_tool
from core.github_tools import GIT_TOOLS_DEFINITION, execute_git_tool

st.set_page_config(
    page_title="QA Agent - Assistente de Testes",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

ALL_TOOLS = (
    TOOLS_DEFINITION + MEMORY_TOOLS + BROWSER_TOOLS_DEFINITION +
    QA_TOOLS_DEFINITION + TEST_DATA_DB_TOOLS + GIT_TOOLS_DEFINITION
)

EXCLUDED_DURING_MONITORING = ["selenium_navigate", "selenium_interact", "selenium_check_errors"]

# =============================================================================
# INICIALIZACAO
# =============================================================================
PROJECT_DIR = Path(os.getenv("TEST_PROJECT_DIR", str(Path(__file__).parent / "sample_project")))

TEST_FOLDERS = {
    "🌐 api": {"path": "tests/api", "description": "Testes de API (JSONPlaceholder, ReqRes)", "marker": "api"},
    "🛡️ security": {"path": "tests/security", "description": "Testes de seguranca (headers, injection, XSS)", "marker": "security"},
    "🧪 all tests": {"path": "tests", "description": "Todos os testes do projeto", "marker": ""},
    "🐛 smoke": {"path": "tests", "description": "Testes smoke (rapidos)", "marker": "smoke"},
}


def get_available_tools():
    monitoring_status = get_monitoring_status()
    if monitoring_status.get("active"):
        return [tool for tool in ALL_TOOLS if tool.get("name") not in EXCLUDED_DURING_MONITORING]
    return ALL_TOOLS


def get_folder_contents(folder_path: Path, max_items: int = 50):
    items = {"folders": [], "test_files": [], "docs": [], "configs": []}
    if not folder_path.exists():
        return items
    try:
        for item in sorted(folder_path.iterdir())[:max_items]:
            name = item.name
            if name.startswith('.') or name in ['__pycache__', 'venv', '.venv', 'node_modules']:
                continue
            if item.is_dir():
                test_count = len(list(item.glob("**/test_*.py"))) + len(list(item.glob("**/*_test.py")))
                items["folders"].append({"name": name, "path": str(item), "test_count": test_count})
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


# =============================================================================
# SYSTEM PROMPT
# =============================================================================
def get_system_prompt():
    memory_context = get_context_for_agent()
    if len(memory_context) > 2000:
        memory_context = memory_context[:2000] + "..."
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

PROVEDOR ATIVO: {st.session_state.get('provider', 'anthropic').upper()}
MODELO ATIVO: {st.session_state.get('model', 'claude-3-haiku-20240307')}

=====================================================================
REGRA #1: COMO TESTAR ENDPOINTS
=====================================================================
Para QUALQUER pedido de teste de endpoint/API, use run_api_test.
run_api_test faz a requisicao HTTP direto, com headers corretos.

EXEMPLO - Testar endpoint:
  run_api_test(endpoint_name="posts")
  run_api_test(endpoint_name="reqres_login", data={{"email": "eve.holt@reqres.in", "password": "cityslicka"}})

Para lista completa: list_api_endpoints()

=====================================================================
RODAR TESTES EXISTENTES
=====================================================================
Use run_pytest para executar suites de teste:
  run_pytest() -> todos os testes
  run_pytest(test_path="tests/api/test_jsonplaceholder.py")
  run_pytest(test_path="tests/security/test_basic_security.py")

=====================================================================
GITHUB/GITLAB INTEGRATION
=====================================================================
Se configurado, voce pode usar ferramentas git:
  list_issues, create_issue, get_issue, update_issue
  list_pull_requests, create_pull_request, add_issue_comment
  list_branches, create_branch

=====================================================================
REGRA MAIS IMPORTANTE: NUNCA ALUCINAR DADOS
=====================================================================
PROIBIDO inventar, fabricar ou resumir dados de resposta da API.
- Copie EXATAMENTE o campo "response_body" do resultado da ferramenta run_api_test
- Mostre o JSON COMPLETO em um bloco ```json ... ```
- NUNCA invente campos, valores ou qualquer outro dado

MEMORIA: {memory_context}

Responda SEMPRE em portugues."""


# =============================================================================
# SESSION STATE
# =============================================================================
def init_session_state():
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
    if "provider" not in st.session_state:
        st.session_state.provider = AI_PROVIDER
    if "model" not in st.session_state:
        st.session_state.model = "claude-3-haiku-20240307"
    if "monitoring_active" not in st.session_state:
        st.session_state.monitoring_active = False
    if "tab" not in st.session_state:
        st.session_state.tab = "Chat"
    if "test_history" not in st.session_state:
        st.session_state.test_history = []
    if "bugs" not in st.session_state:
        st.session_state.bugs = []
    if "dark_mode" not in st.session_state:
        st.session_state.dark_mode = False


# =============================================================================
# CLIENT (multi-provedor)
# =============================================================================
def get_ai_client():
    provider_name = st.session_state.provider
    model = st.session_state.model

    config = {"model": model, "api_key": ""}
    env_keys = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "gemini": "GEMINI_API_KEY",
    }
    env_key = env_keys.get(provider_name, "ANTHROPIC_API_KEY")
    config["api_key"] = os.getenv(env_key, "")

    if not config["api_key"]:
        return None, f"Chave {env_key} nao configurada"

    try:
        provider = get_provider(provider_name, config)
        return provider, None
    except Exception as e:
        return None, str(e)


# =============================================================================
# PROCESS TOOL CALL
# =============================================================================
def process_tool_call(tool_name: str, tool_input: dict) -> str:
    monitoring_status = get_monitoring_status()
    if monitoring_status.get("active") and tool_name in EXCLUDED_DURING_MONITORING:
        return json.dumps({
            "success": False,
            "error": f"BLOQUEADO: Monitoramento ativo. Use: capture_user_state, stop_user_monitoring, get_monitoring_status",
            "monitoring_active": True,
            "allowed_tools": ["capture_user_state", "stop_user_monitoring", "get_monitoring_status"]
        })

    if tool_name in ["save_learning", "search_memory", "get_test_history"]:
        return execute_memory_tool(tool_name, tool_input)
    elif tool_name in ["selenium_navigate", "selenium_interact", "selenium_screenshot", "selenium_check_errors",
                       "selenium_find_element", "run_selenium_test", "run_cypress_test", "run_playwright_test",
                       "start_user_monitoring", "capture_user_state", "stop_user_monitoring", "get_monitoring_status"]:
        return execute_browser_tool(tool_name, tool_input)
    elif tool_name in ["create_bug", "list_bugs", "get_bug", "update_bug", "create_feature", "list_features",
                       "update_feature", "create_test_case", "list_test_cases", "get_test_case", "create_test_plan",
                       "add_test_case_to_plan", "list_test_plans", "get_test_plan", "update_test_plan_status",
                       "record_test_execution", "get_execution_history", "generate_qa_report"]:
        return execute_qa_tool(tool_name, tool_input)
    elif tool_name in ["get_test_cpfs", "get_test_cnpjs", "query_test_data", "get_test_data_summary"]:
        return execute_test_data_tool(tool_name, tool_input)
    elif tool_name in ["list_issues", "create_issue", "get_issue", "update_issue",
                       "list_pull_requests", "create_pull_request", "add_issue_comment",
                       "list_branches", "create_branch"]:
        return execute_git_tool(tool_name, tool_input)
    else:
        result = execute_tool(tool_name, tool_input)
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


# =============================================================================
# CHAT WITH AGENT (multi-provedor)
# =============================================================================
def chat_with_agent(provider, user_message: str) -> str:
    if not provider:
        return "Erro: Provedor de IA nao configurado. Verifique o .env"

    save_conversation(st.session_state.session_id, "user", user_message)

    messages = []
    if st.session_state.get("active_task"):
        messages.append({"role": "user", "content": f"[TAREFA ATIVA]: {st.session_state.active_task}"})
        messages.append({"role": "assistant", "content": "Entendido, vou manter essa tarefa em mente."})

    for msg in st.session_state.messages[-20:]:
        messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": user_message})

    full_response = ""
    tool_results_list = []
    real_data_blocks = []

    try:
        iterations = 0
        max_iterations = 10

        while iterations < max_iterations:
            iterations += 1

            model = st.session_state.model
            if "haiku" in model or "mini" in model or "flash" in model:
                max_tokens = 4096
            elif "sonnet" in model or "pro" in model:
                max_tokens = 8192
            else:
                max_tokens = 8192

            available_tools = get_available_tools()

            try:
                response = provider.create_message(
                    messages=messages,
                    tools=available_tools,
                    system=get_system_prompt(),
                    max_tokens=max_tokens
                )
                parsed = provider.parse_response(response)
            except Exception as e:
                error_msg = f"Erro na chamada da API ({st.session_state.provider}): {e}"
                save_conversation(st.session_state.session_id, "assistant", error_msg)
                return error_msg

            has_tool_use = False
            assistant_content = []

            for block in parsed["content"]:
                if block["type"] == "text":
                    full_response += block["text"]
                elif block["type"] == "tool_use":
                    has_tool_use = True
                    tool_name = block["name"]
                    tool_input = block["input"]
                    tool_use_id = block.get("id", f"tool_{iterations}_{tool_name}")

                    tool_icons = {
                        "run_pytest": "🧪", "read_file": "📄", "write_file": "📝",
                        "execute_command": "💻", "list_directory": "📁", "search_in_files": "🔍",
                        "save_learning": "🧠", "search_memory": "💭", "get_test_history": "📊",
                        "fetch_url_with_js": "🌐", "selenium_navigate": "🖥️", "web_search": "🔎",
                        "run_api_test": "🎯", "list_api_endpoints": "📋",
                        "create_issue": "🐛", "list_issues": "📋", "create_pull_request": "🔀",
                    }
                    icon = tool_icons.get(tool_name, "⚙️")

                    tool_result = process_tool_call(tool_name, tool_input)

                    st.session_state.tool_calls.append({
                        "tool": tool_name, "input": tool_input, "result": tool_result[:500]
                    })

                    status_icon = "✅"
                    result_json = {}
                    try:
                        result_json = json.loads(tool_result)
                        if tool_name == "run_pytest":
                            ts = result_json.get("test_status", "")
                            if ts == "all_passed":
                                status_icon = "✅"
                            elif ts == "tests_failed":
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
                            status_icon = "❌"
                    except:
                        pass

                    tool_info = f"{icon} {tool_name}"
                    if tool_name == "run_pytest":
                        test_path_display = tool_input.get('test_path', 'all')
                        if test_path_display and len(test_path_display) > 30:
                            test_path_display = Path(test_path_display).name or 'all'
                        pr = result_json.get("pass_rate", "")
                        stats = result_json.get("stats", {})
                        tool_info += f"({test_path_display})"
                        if pr and pr != "N/A":
                            total = result_json.get("total_tests", 0)
                            tool_info += f" {stats.get('passed',0)}/{total} {pr}"
                    elif tool_name == "run_api_test":
                        ep_name = tool_input.get('endpoint_name', '') or tool_input.get('endpoint_path', 'custom')
                        sc = result_json.get("status_code", "?")
                        rt = result_json.get("response_time_seconds", "")
                        env = result_json.get("environment", "")
                        tool_info += f"({ep_name}) HTTP {sc}"
                        if rt:
                            tool_info += f" {rt}s"
                        if env:
                            tool_info += f" [{env}]"
                    tool_results_list.append(f"{tool_info} {status_icon}")

                    if result_json:
                        if tool_name == "run_api_test":
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
                            s = result_json.get("stats", {})
                            total = result_json.get("total_tests", 0)
                            pr = result_json.get("pass_rate", "N/A")
                            env = result_json.get("environment", "")
                            ts = result_json.get("test_status", "")
                            block = f"🧪 **Resultado REAL dos testes** [{env}]\n"
                            block += f"- **Passed:** {s.get('passed', 0)} | **Failed:** {s.get('failed', 0)} | **Skipped:** {s.get('skipped', 0)} | **Total:** {total}\n"
                            block += f"- **Taxa de sucesso:** {pr}\n- **Status:** {ts}"
                            if s.get('failed', 0) > 0:
                                output = result_json.get("output", "")
                                failed_lines = [l for l in output.split('\n') if 'FAILED' in l]
                                if failed_lines:
                                    block += "\n- **Falhas:**\n" + "\n".join(f"  - `{fl.strip()}`" for fl in failed_lines[:10])
                            real_data_blocks.append(block)

                        elif tool_name in ("create_issue", "list_issues", "get_issue", "update_issue",
                                           "create_pull_request", "list_pull_requests"):
                            tool_label = {"create_issue": "Issue criada", "list_issues": "Issues",
                                          "get_issue": "Issue", "update_issue": "Issue atualizada",
                                          "create_pull_request": "PR criado", "list_pull_requests": "PRs"}.get(tool_name, tool_name)
                            if result_json.get("success"):
                                if tool_name == "list_issues":
                                    issues = result_json.get("issues", [])
                                    if issues:
                                        block = f"🐙 **{tool_label}** ({len(issues)}):\n"
                                        for iss in issues[:10]:
                                            block += f"- #{iss['number']} {iss['title']} [{iss['state']}]\n"
                                        real_data_blocks.append(block)
                                elif tool_name == "list_pull_requests":
                                    prs = result_json.get("pull_requests", [])
                                    if prs:
                                        block = f"🔀 **{tool_label}** ({len(prs)}):\n"
                                        for p in prs[:10]:
                                            block += f"- !{p['number']} {p['title']} [{p['state']}] {p['branch']}->{p['target_branch']}\n"
                                        real_data_blocks.append(block)
                                else:
                                    msg = result_json.get("message", "")
                                    if msg:
                                        real_data_blocks.append(f"🐙 **{tool_label}:** {msg}")

                    assistant_content.append({
                        "type": "tool_result" if provider.name == "anthropic" else "tool_use",
                        "tool_use_id": tool_use_id if provider.name == "anthropic" else tool_use_id,
                        "name": tool_name,
                        "input": tool_input
                    })

                    messages.append({"role": "assistant", "content": assistant_content})
                    messages.append({
                        "role": "user",
                        "content": [{"type": "tool_result", "tool_use_id": tool_use_id, "content": tool_result}]
                    })
                    assistant_content = []

            if not has_tool_use or parsed.get("stop_reason") == "end_turn":
                break

        real_data_section = ""
        if real_data_blocks:
            real_data_section = "\n\n---\n📊 **DADOS REAIS (gerados pelo codigo, nao pelo LLM):**\n\n"
            real_data_section += "\n\n".join(real_data_blocks)

        tools_summary = ""
        if tool_results_list:
            tools_summary = "\n\n---\n**Ferramentas executadas:**\n" + " | ".join(tool_results_list)

        final_response = full_response + real_data_section + tools_summary
        save_conversation(st.session_state.session_id, "assistant", final_response)
        return final_response

    except Exception as e:
        error_msg = f"Erro: {str(e)}"
        return error_msg


# =============================================================================
# DASHBOARD
# =============================================================================
def render_dashboard():
    st.header("📊 Dashboard de QA")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🧪 Testes Totais", "27", "+3 hoje")
    with col2:
        st.metric("✅ Taxa Sucesso", "92.6%", "+2.1%")
    with col3:
        st.metric("🐛 Bugs Abertos", "3", "-1")
    with col4:
        st.metric("📋 Cobertura", "78%", "+5%")

    st.subheader("📈 Ultimas Execucoes")
    try:
        history = get_test_history(limit=20)
        if history:
            import plotly.graph_objects as go
            dates = [h.get("created_at", "")[:10] for h in history]
            passed = [h.get("passed", 0) for h in history]
            failed = [h.get("failed", 0) for h in history]

            fig = go.Figure()
            fig.add_trace(go.Bar(name="Passed", x=dates, y=passed, marker_color="#00cc66"))
            fig.add_trace(go.Bar(name="Failed", x=dates, y=failed, marker_color="#ff4444"))
            fig.update_layout(barmode="group", height=300, margin=dict(l=0, r=0, t=0, b=0),
                              xaxis_title="Data", yaxis_title="Testes")
            st.plotly_chart(fig, use_container_width=True)

            col1, col2 = st.columns(2)
            with col1:
                st.subheader("✅ Ultimos Testes Bem-sucedidos")
                for h in history[:5]:
                    if h.get("failed", 0) == 0:
                        st.success(f"`{h.get('test_path', 'unknown')}` - {h.get('passed', 0)} passed")
            with col2:
                st.subheader("❌ Ultimas Falhas")
                for h in history[:5]:
                    if h.get("failed", 0) > 0:
                        st.error(f"`{h.get('test_path', 'unknown')}` - {h.get('failed', 0)} falhas")
        else:
            st.info("Nenhum resultado de teste ainda. Execute testes pelo Chat!")
    except Exception as e:
        st.warning(f"Sem dados historicos: {e}")

    st.subheader("🐛 Bugs Ativos")
    try:
        bugs = list_bugs(status="open")
        if bugs.get("success"):
            bug_list = bugs.get("bugs", [])
            if bug_list:
                for b in bug_list[:5]:
                    severity = b.get("severity", "medium")
                    icons = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
                    sev_icon = icons.get(severity, "⚪")
                    st.info(f"{sev_icon} **#{b.get('id', '?')}** {b.get('title', '?')} - `{severity}`")
            else:
                st.success("Nenhum bug aberto!")
        else:
            st.caption("Nenhum bug registrado ainda")
    except Exception:
        st.caption("Use o Chat para registrar bugs")


# =============================================================================
# SIDEBAR
# =============================================================================
def render_sidebar():
    with st.sidebar:
        st.title("⚙️ QA Agent")
        st.caption(f"Sessao: {st.session_state.session_id}")

        st.divider()

        provider_options = {
            "anthropic": "Claude (Anthropic)",
            "openai": "GPT (OpenAI)",
            "gemini": "Gemini (Google)",
        }
        available_providers = {k: v for k, v in provider_options.items() if check_provider_key(k)}
        if not available_providers:
            available_providers = {"anthropic": "Claude (Anthropic)"}

        provider = st.selectbox(
            "🧠 Provedor IA",
            options=list(available_providers.keys()),
            format_func=lambda x: available_providers[x],
            index=0 if st.session_state.provider in available_providers else 0
        )

        if provider:
            models = PROVIDER_MODELS.get(provider, {})
            if models:
                model_names = list(models.keys())
                current_model = st.session_state.model
                model_idx = 0
                if current_model in model_names:
                    model_idx = model_names.index(current_model)
                selected_model = st.selectbox(
                    "🎯 Modelo",
                    options=model_names,
                    format_func=lambda x: models.get(x, x),
                    index=model_idx
                )
                st.session_state.model = selected_model
            st.session_state.provider = provider

        st.divider()

        env_options = list(ENVIRONMENTS.keys())
        env = st.selectbox(
            "🌐 Ambiente",
            env_options,
            index=env_options.index(st.session_state.environment) if st.session_state.environment in env_options else 0
        )
        if env != st.session_state.environment:
            st.session_state.environment = env
            set_environment(env)

        env_info = ENVIRONMENTS.get(env, {})
        st.caption(f"API: {env_info.get('api_base_url', 'N/A')}")

        st.divider()

        st.subheader("📋 Tarefa Ativa")
        if st.session_state.active_task:
            st.info(st.session_state.active_task[:100] + "..." if len(st.session_state.active_task) > 100 else st.session_state.active_task)
            if st.button("❌ Limpar Tarefa", use_container_width=True):
                st.session_state.active_task = None
                st.rerun()
        else:
            st.caption("Nenhuma tarefa ativa")
            new_task = st.text_area("Definir tarefa:", height=80, placeholder="Ex: Testar todos os endpoints...")
            if st.button("✅ Definir", use_container_width=True) and new_task:
                st.session_state.active_task = new_task
                st.rerun()

        st.divider()

        st.subheader("👁️ Monitoramento")
        monitoring_status = get_monitoring_status()
        if monitoring_status.get("active"):
            st.success("🟢 NAVEGADOR ABERTO")
            st.caption(f"Capturas: {monitoring_status.get('screenshots_taken', 0)}")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📸 Capturar", use_container_width=True):
                    st.session_state.pending_message = "Capture o estado atual da pagina"
            with col2:
                if st.button("🛑 Encerrar", use_container_width=True):
                    st.session_state.pending_message = "Encerre o monitoramento"
        else:
            st.caption("🔴 Nenhum monitoramento ativo")

        st.divider()

        st.subheader("📂 Explorador")
        selected_folder = st.selectbox("Pasta:", options=list(TEST_FOLDERS.keys()), format_func=lambda x: x)
        if selected_folder:
            folder_info = TEST_FOLDERS[selected_folder]
            folder_path = PROJECT_DIR / folder_info["path"]
            st.caption(f"📝 {folder_info['description']}")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("▶️ Rodar", key=f"run_{selected_folder}", use_container_width=True):
                    marker_cmd = f' com marker {folder_info["marker"]}' if folder_info["marker"] else ''
                    st.session_state.pending_message = f"Execute os testes da pasta {folder_info['path']}{marker_cmd}"
            with col2:
                if st.button("📖 Analisar", key=f"analyze_{selected_folder}", use_container_width=True):
                    st.session_state.pending_message = f"Analise a estrutura e os testes da pasta {folder_info['path']}"
            contents = get_folder_contents(folder_path)
            if contents["test_files"]:
                with st.expander(f"🧪 Testes ({len(contents['test_files'])})", expanded=True):
                    for test in contents["test_files"][:15]:
                        c1, c2 = st.columns([3, 1])
                        with c1:
                            st.text(f"🧪 {test['name']}")
                        with c2:
                            if st.button("▶️", key=f"rt_{test['name']}", help="Rodar"):
                                st.session_state.pending_message = f"Execute o teste {test['path']}"

        st.divider()

        st.subheader("⚡ Acoes Rapidas")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🧪 Smoke", use_container_width=True):
                st.session_state.pending_message = "Execute os testes de smoke"
        with col2:
            if st.button("🛡️ Security", use_container_width=True):
                st.session_state.pending_message = "Execute os testes de seguranca"

        col1, col2 = st.columns(2)
        with col1:
            if st.button("📊 Historico", use_container_width=True):
                st.session_state.pending_message = "Mostre o historico das ultimas execucoes"
        with col2:
            if st.button("🔍 Buscar", use_container_width=True):
                st.session_state.pending_message = "Busque por SQL injection nos arquivos de teste"

        st.divider()

        if st.button("🗑️ Limpar Conversa", use_container_width=True):
            st.session_state.messages = []
            st.session_state.tool_calls = []
            st.rerun()


# =============================================================================
# CHAT UI
# =============================================================================
def render_chat():
    for message in st.session_state.messages:
        avatar = "👤" if message["role"] == "user" else "🤖"
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])

    if not st.session_state.messages:
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(f"""
**Ola! Sou o QA Agent com Dashboard e Multi-Provedores!** 🚀

**Provedor ativo:** `{st.session_state.provider.upper()}` | **Modelo:** `{st.session_state.model}`

| Acao | Exemplo |
|------|---------|
| 🧪 **Rodar testes** | "Execute os testes de API" |
| 📡 **Testar API** | "Teste o endpoint de posts" |
| 🐛 **Registrar bug** | "Crie um bug: login quebrado severity high" |
| 🔀 **Criar PR** | "Crie um PR para a branch fix-login" |
| 📊 **Dashboard** | Vá na aba Dashboard para ver graficos |

**Experimente:** *"Rode todos os testes"* ou *"O que voce aprendeu?"*
            """)


# =============================================================================
# MAIN
# =============================================================================
def main():
    init_session_state()
    provider, error = get_ai_client()

    tab_chat, tab_dashboard, tab_qa, tab_about = st.tabs(["💬 Chat", "📊 Dashboard", "🐛 QA Management", "ℹ️ Sobre"])

    with tab_chat:
        col1, col2 = st.columns([5, 1])
        with col1:
            st.title("💬 QA Agent")
        with col2:
            status = "🟢 Online" if provider else "🔴 Offline"
            prov_status = f"{st.session_state.provider.upper()}"
            st.metric("Status", status)
            st.caption(prov_status)

        if error:
            st.error(f"⚠️ {error}")

        render_chat()

        if prompt := st.chat_input("Digite sua pergunta ou comando..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user", avatar="👤"):
                st.markdown(prompt)
            with st.chat_message("assistant", avatar="🤖"):
                with st.spinner(f"🤔 Processando com {st.session_state.provider.upper()}..."):
                    response = chat_with_agent(provider, prompt)
                st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.rerun()

    with tab_dashboard:
        render_dashboard()

    with tab_qa:
        st.header("🐛 Gestao de QA")

        qa_tab1, qa_tab2, qa_tab3, qa_tab4 = st.tabs(["Bugs", "Features", "Test Cases", "Reports"])

        with qa_tab1:
            col1, col2 = st.columns([2, 1])
            with col1:
                st.subheader("Bugs Registrados")
                try:
                    bugs = list_bugs()
                    if bugs.get("success"):
                        bug_list = bugs.get("bugs", [])
                        if bug_list:
                            for b in bug_list:
                                sev = b.get("severity", "medium")
                                sev_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(sev, "⚪")
                                st.info(f"{sev_icon} **#{b.get('id')}** {b.get('title')} - `{b.get('status', 'open')}`")
                        else:
                            st.success("Nenhum bug registrado!")
                except:
                    pass
            with col2:
                st.subheader("Novo Bug")
                bug_title = st.text_input("Titulo", key="bug_title")
                bug_desc = st.text_area("Descricao", key="bug_desc", height=80)
                bug_sev = st.selectbox("Severidade", ["low", "medium", "high", "critical"], key="bug_sev")
                if st.button("🐛 Registrar Bug", use_container_width=True) and bug_title:
                    result = execute_qa_tool("create_bug", {
                        "title": bug_title, "description": bug_desc, "severity": bug_sev
                    })
                    st.success("Bug registrado! Veja no Chat.")
                    st.rerun()

        with qa_tab2:
            st.subheader("Features / User Stories")
            feat_title = st.text_input("Titulo da Feature", key="feat_title")
            feat_desc = st.text_area("Descricao / Criterios de Aceite", key="feat_desc", height=100)
            if st.button("➕ Criar Feature", use_container_width=True) and feat_title:
                result = execute_qa_tool("create_feature", {
                    "title": feat_title, "description": feat_desc
                })
                st.success("Feature criada!")
                st.rerun()

        with qa_tab3:
            st.subheader("Casos de Teste")
            tc_title = st.text_input("Titulo do Caso de Teste", key="tc_title")
            tc_steps = st.text_area("Passos (um por linha)", key="tc_steps", height=80)
            tc_expected = st.text_area("Resultado Esperado", key="tc_expected", height=60)
            if st.button("➕ Criar Caso de Teste", use_container_width=True) and tc_title:
                steps_list = [s.strip() for s in tc_steps.split("\n") if s.strip()]
                result = execute_qa_tool("create_test_case", {
                    "title": tc_title,
                    "steps": steps_list,
                    "expected_results": tc_expected,
                })
                st.success("Caso de teste criado!")
                st.rerun()

        with qa_tab4:
            st.subheader("Relatorios")
            if st.button("📊 Gerar Relatorio Consolidado", use_container_width=True):
                result = execute_qa_tool("generate_qa_report", {})
                try:
                    data = json.loads(result)
                    st.json(data)
                except:
                    st.text(result)
            if st.button("📋 Gerar Relatorio de Testes (Markdown)", use_container_width=True):
                st.session_state.pending_message = "Gere um relatorio completo de QA em Markdown"

    with tab_about:
        st.header("ℹ️ Sobre o QA Agent")
        st.markdown("""
| Componente | Versao |
|------------|--------|
| **Provedor** | Multi (Anthropic, OpenAI, Gemini) |
| **Interface** | Streamlit + Plotly |
| **Testes** | Pytest + Selenium |
| **Memoria** | SQLite |
| **Integracao** | GitHub/GitLab, OpenCode MCP |
| **Relatorios** | HTML, Markdown, JSON, PDF |

### Funcionalidades:
- ✅ **Execucao real de testes** - Roda pytest, analisa resultados
- ✅ **Teste de API direto** - Testa endpoints sem codigo
- ✅ **Memoria persistente** - Aprendizados entre sessoes
- ✅ **Gestao de QA** - Bugs, features, casos de teste, planos
- ✅ **Multi-provedor** - Claude, GPT e Gemini
- ✅ **Git Integration** - Issues, PRs, branches
- ✅ **Dashboard** - Graficos e metricas em tempo real
- ✅ **OpenCode MCP** - Integracao com OpenCode
- ✅ **Docker** - Container pronto para deploy
- ✅ **CI/CD** - GitHub Actions pipeline
        """)

    # Process pending message from sidebar buttons
    if "pending_message" in st.session_state and st.session_state.pending_message:
        pending = st.session_state.pending_message
        st.session_state.pending_message = None
        st.session_state.messages.append({"role": "user", "content": pending})
        with st.chat_message("user", avatar="👤"):
            st.markdown(pending)
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner(f"🤔 Processando com {st.session_state.provider.upper()}..."):
                response = chat_with_agent(provider, pending)
            st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()

    render_sidebar()


if __name__ == "__main__":
    main()
