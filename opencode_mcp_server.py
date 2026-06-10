#!/usr/bin/env python3
"""
OpenCode MCP Server para o QA Agent
=====================================
Expoe as ferramentas do QA Agent como um servidor MCP
para ser usado pelo OpenCode.

Configuracao no opencode.json:
{
  "mcp": {
    "qa-agent": {
      "type": "local",
      "command": ["python", "opencode_mcp_server.py"],
      "enabled": true
    }
  }
}
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

TOOL_REGISTRY = {}


def register_tool(name: str, description: str, parameters: dict):
    """Decorator para registrar ferramentas MCP"""
    def decorator(func):
        TOOL_REGISTRY[name] = {
            "description": description,
            "parameters": parameters,
            "function": func,
        }
        return func
    return decorator


# =============================================================================
# FERRAMENTAS QA AGENT
# =============================================================================

@register_tool(
    "run_pytest",
    "Executa testes pytest no projeto",
    {
        "type": "object",
        "properties": {
            "test_path": {"type": "string", "description": "Caminho do teste"},
            "markers": {"type": "string", "description": "Markers para filtrar"},
        },
    },
)
def tool_run_pytest(test_path: str = "", markers: str = ""):
    from core.tools import run_pytest as _run_pytest
    return _run_pytest(test_path=test_path, markers=markers)


@register_tool(
    "run_api_test",
    "Testa um endpoint de API diretamente",
    {
        "type": "object",
        "properties": {
            "endpoint_name": {"type": "string", "description": "Nome do endpoint"},
            "method": {"type": "string", "description": "Metodo HTTP"},
            "data": {"type": "object", "description": "Dados da requisicao"},
        },
    },
)
def tool_run_api_test(endpoint_name: str = "", method: str = "GET", data: dict = None):
    from core.tools import run_api_test as _run_api_test
    return _run_api_test(endpoint_name=endpoint_name, method=method, data=data or {})


@register_tool(
    "read_file",
    "Le o conteudo de um arquivo",
    {
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Caminho do arquivo"}
        },
        "required": ["file_path"],
    },
)
def tool_read_file(file_path: str):
    from core.tools import read_file as _read_file
    return _read_file(file_path)


@register_tool(
    "write_file",
    "Escreve conteudo em um arquivo",
    {
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Caminho do arquivo"},
            "content": {"type": "string", "description": "Conteudo do arquivo"},
        },
        "required": ["file_path", "content"],
    },
)
def tool_write_file(file_path: str, content: str):
    from core.tools import write_file as _write_file
    return _write_file(file_path, content)


@register_tool(
    "search_code",
    "Busca texto em arquivos do projeto",
    {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Texto a buscar"},
        },
        "required": ["pattern"],
    },
)
def tool_search_code(pattern: str):
    from core.tools import search_in_files as _search_in_files
    return _search_in_files(pattern)


@register_tool(
    "create_bug",
    "Registra um bug no banco de dados do QA Agent",
    {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Titulo do bug"},
            "description": {"type": "string", "description": "Descricao do bug"},
            "severity": {
                "type": "string",
                "enum": ["low", "medium", "high", "critical"],
                "description": "Severidade",
            },
        },
        "required": ["title", "description"],
    },
)
def tool_create_bug(title: str, description: str, severity: str = "medium"):
    from core.qa_tools import create_bug as _create_bug
    return _create_bug(title=title, description=description, severity=severity)


@register_tool(
    "list_bugs",
    "Lista bugs registrados",
    {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "enum": ["open", "in_progress", "resolved", "closed"],
                "description": "Filtrar por status",
            },
        },
    },
)
def tool_list_bugs(status: str = "open"):
    from core.qa_tools import list_bugs as _list_bugs
    return _list_bugs(status=status)


@register_tool(
    "generate_qa_report",
    "Gera relatorio consolidado de QA",
    {
        "type": "object",
        "properties": {},
    },
)
def tool_generate_qa_report():
    from core.qa_tools import generate_test_summary_report as _report
    return _report()


@register_tool(
    "get_repository_structure",
    "Retorna estrutura de pastas do projeto",
    {
        "type": "object",
        "properties": {
            "max_depth": {
                "type": "integer",
                "description": "Profundidade maxima (padrao: 3)",
            },
        },
    },
)
def tool_get_structure(max_depth: int = 3):
    from core.tools import get_repository_structure as _struct
    return _struct(max_depth=max_depth)


@register_tool(
    "execute_command",
    "Executa comando no terminal (cuidado!)",
    {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Comando a executar"},
            "timeout": {"type": "integer", "description": "Timeout em segundos"},
        },
        "required": ["command"],
    },
)
def tool_execute_command(command: str, timeout: int = 120):
    from core.tools import execute_command as _exec
    return _exec(command, timeout=timeout)


# =============================================================================
# PROTOCOLO MCP (STDIO)
# =============================================================================

def send_message(msg: dict):
    """Envia mensagem JSON para o cliente MCP via stdout"""
    sys.stdout.write(json.dumps(msg, ensure_ascii=False, default=str) + "\n")
    sys.stdout.flush()


def handle_request(request: dict) -> dict:
    """Processa uma requisicao MCP"""
    method = request.get("method", "")
    params = request.get("params", {})

    if method == "initialize":
        return {
            "protocolVersion": "1.0",
            "capabilities": {
                "tools": {
                    "listChanged": False,
                }
            },
            "serverInfo": {
                "name": "qa-agent-mcp",
                "version": "1.0.0",
            },
        }

    elif method == "tools/list":
        tools = []
        for name, info in TOOL_REGISTRY.items():
            tools.append({
                "name": name,
                "description": info["description"],
                "inputSchema": info["parameters"],
            })
        return {"tools": tools}

    elif method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        if tool_name not in TOOL_REGISTRY:
            return {
                "isError": True,
                "content": [{
                    "type": "text",
                    "text": json.dumps({"error": f"Ferramenta nao encontrada: {tool_name}"}),
                }],
            }

        try:
            func = TOOL_REGISTRY[tool_name]["function"]
            result = func(**arguments)

            if isinstance(result, dict):
                text = json.dumps(result, ensure_ascii=False, default=str)
            else:
                text = str(result)

            return {
                "content": [{"type": "text", "text": text}],
            }
        except Exception as e:
            return {
                "isError": True,
                "content": [{"type": "text", "text": json.dumps({"error": str(e)})}],
            }

    elif method == "notifications/initialized":
        return None

    return {
        "isError": True,
        "content": [{"type": "text", "text": json.dumps({"error": f"Metodo desconhecido: {method}"})}],
    }


def main():
    """Loop principal: le JSON do stdin, processa, envia resposta pro stdout"""
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue

            request = json.loads(line)
            request_id = request.get("id")

            result = handle_request(request)

            if result is not None:
                send_message({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": result,
                })
        except json.JSONDecodeError as e:
            send_message({
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {e}"},
            })
        except Exception as e:
            send_message({
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32603, "message": str(e)},
            })


if __name__ == "__main__":
    main()
