"""
QA Agent - Ferramentas de Integracao GitHub/GitLab
===================================================

Permite ao agente:
- Criar/Listar/Atualizar Issues
- Criar/Listar/Atualizar Pull Requests / Merge Requests
- Listar branches e repositorios
- Comentar em issues e PRs
"""

import os
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

GIT_TOKEN = os.getenv("GIT_TOKEN", "")
GIT_REPO = os.getenv("GIT_REPO", "")
GIT_PROVIDER = os.getenv("GIT_PROVIDER", "github")  # github ou gitlab


def _get_github_headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {GIT_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "QA-Agent/1.0"
    }


def _get_gitlab_headers() -> Dict[str, str]:
    return {
        "PRIVATE-TOKEN": GIT_TOKEN,
        "User-Agent": "QA-Agent/1.0"
    }


def _get_api_base() -> str:
    if GIT_PROVIDER == "gitlab":
        return os.getenv("GITLAB_URL", "https://gitlab.com/api/v4")
    return "https://api.github.com"


def _get_project_path() -> str:
    if GIT_PROVIDER == "gitlab":
        return GIT_REPO.replace("/", "%2F")
    return f"repos/{GIT_REPO}"


def _api_call(method: str, endpoint: str, data: Dict = None) -> Dict[str, Any]:
    """Faz chamada a API do GitHub/GitLab"""
    import requests

    headers = _get_github_headers() if GIT_PROVIDER == "github" else _get_gitlab_headers()
    url = f"{_get_api_base()}/{endpoint}"

    try:
        if method == "GET":
            resp = requests.get(url, headers=headers, timeout=30)
        elif method == "POST":
            resp = requests.post(url, headers=headers, json=data, timeout=30)
        elif method == "PATCH":
            resp = requests.patch(url, headers=headers, json=data, timeout=30)
        else:
            return {"success": False, "error": f"Metodo invalido: {method}"}

        if resp.status_code in (200, 201):
            return {"success": True, "data": resp.json()}
        else:
            return {
                "success": False,
                "error": f"API {GIT_PROVIDER} retornou {resp.status_code}: {resp.text[:500]}",
                "status_code": resp.status_code
            }
    except Exception as e:
        return {"success": False, "error": str(e)}


def _check_config() -> Optional[Dict[str, Any]]:
    """Verifica se a configuracao basica existe"""
    if not GIT_TOKEN:
        return {"success": False, "error": "GIT_TOKEN nao configurado no .env"}
    if not GIT_REPO:
        return {"success": False, "error": "GIT_REPO nao configurado no .env (formato: usuario/repo)"}
    return None


# =============================================================================
# TOOL DEFINITIONS
# =============================================================================

GIT_TOOLS_DEFINITION = [
    {
        "name": "list_issues",
        "description": "Lista issues do repositorio com filtros opcionais",
        "input_schema": {
            "type": "object",
            "properties": {
                "state": {
                    "type": "string",
                    "enum": ["open", "closed", "all"],
                    "description": "Estado das issues (padrao: open)"
                },
                "label": {
                    "type": "string",
                    "description": "Filtrar por label (ex: bug, enhancement)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Numero maximo de issues (padrao: 20)"
                }
            }
        }
    },
    {
        "name": "create_issue",
        "description": "Cria uma nova issue no repositorio",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Titulo da issue"},
                "body": {"type": "string", "description": "Corpo/descricao da issue"},
                "labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Labels para a issue (ex: [bug, critical])"
                },
                "assignee": {
                    "type": "string",
                    "description": "Usuario para atribuir (GitHub username)"
                }
            },
            "required": ["title", "body"]
        }
    },
    {
        "name": "get_issue",
        "description": "Obtem detalhes de uma issue pelo numero",
        "input_schema": {
            "type": "object",
            "properties": {
                "issue_number": {
                    "type": "integer",
                    "description": "Numero da issue"
                }
            },
            "required": ["issue_number"]
        }
    },
    {
        "name": "update_issue",
        "description": "Atualiza uma issue existente (status, labels, assignee)",
        "input_schema": {
            "type": "object",
            "properties": {
                "issue_number": {"type": "integer", "description": "Numero da issue"},
                "state": {
                    "type": "string",
                    "enum": ["open", "closed"],
                    "description": "Novo estado"
                },
                "title": {"type": "string", "description": "Novo titulo"},
                "body": {"type": "string", "description": "Novo corpo"},
                "labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Novas labels"
                }
            },
            "required": ["issue_number"]
        }
    },
    {
        "name": "list_pull_requests",
        "description": "Lista pull requests do repositorio",
        "input_schema": {
            "type": "object",
            "properties": {
                "state": {
                    "type": "string",
                    "enum": ["open", "closed", "all"],
                    "description": "Estado dos PRs (padrao: open)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Numero maximo (padrao: 20)"
                }
            }
        }
    },
    {
        "name": "create_pull_request",
        "description": "Cria um pull request",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Titulo do PR"},
                "body": {"type": "string", "description": "Descricao do PR"},
                "head": {"type": "string", "description": "Branch de origem (feature)"},
                "base": {"type": "string", "description": "Branch de destino (ex: main)"},
                "draft": {
                    "type": "boolean",
                    "description": "Criar como draft PR"
                }
            },
            "required": ["title", "head", "base"]
        }
    },
    {
        "name": "add_issue_comment",
        "description": "Adiciona comentario em uma issue ou PR",
        "input_schema": {
            "type": "object",
            "properties": {
                "issue_number": {"type": "integer", "description": "Numero da issue/PR"},
                "comment": {"type": "string", "description": "Texto do comentario"}
            },
            "required": ["issue_number", "comment"]
        }
    },
    {
        "name": "list_branches",
        "description": "Lista branches do repositorio",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Numero maximo (padrao: 30)"
                }
            }
        }
    },
    {
        "name": "create_branch",
        "description": "Cria uma nova branch a partir de outra",
        "input_schema": {
            "type": "object",
            "properties": {
                "branch_name": {"type": "string", "description": "Nome da nova branch"},
                "source_branch": {
                    "type": "string",
                    "description": "Branch de origem (padrao: main)"
                }
            },
            "required": ["branch_name"]
        }
    },
]


# =============================================================================
# TOOL FUNCTIONS
# =============================================================================

def execute_git_tool(tool_name: str, tool_input: Dict[str, Any]) -> str:
    """Executa ferramenta git e retorna JSON string"""
    try:
        config_error = _check_config()
        if config_error:
            if tool_name == "list_branches":
                pass
            else:
                return json.dumps(config_error, ensure_ascii=False)

        tool_map = {
            "list_issues": _list_issues,
            "create_issue": _create_issue,
            "get_issue": _get_issue,
            "update_issue": _update_issue,
            "list_pull_requests": _list_pull_requests,
            "create_pull_request": _create_pull_request,
            "add_issue_comment": _add_issue_comment,
            "list_branches": _list_branches,
            "create_branch": _create_branch,
        }

        func = tool_map.get(tool_name)
        if not func:
            return json.dumps({"success": False, "error": f"Ferramenta git desconhecida: {tool_name}"})

        result = func(**tool_input)
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


# =============================================================================
# IMPLEMENTACOES
# =============================================================================

def _list_issues(state: str = "open", label: str = "", limit: int = 20) -> Dict:
    if GIT_PROVIDER == "gitlab":
        endpoint = f"projects/{_get_project_path()}/issues?state={state}&per_page={limit}"
        if label:
            endpoint += f"&labels={label}"
    else:
        endpoint = f"{_get_project_path()}/issues?state={state}&per_page={limit}"
        if label:
            endpoint += f"&labels={label}"
    result = _api_call("GET", endpoint)
    if result["success"]:
        issues = []
        for item in result["data"][:limit]:
            issue = {
                "number": item.get("number") or item.get("iid"),
                "title": item["title"],
                "state": item["state"],
                "created_at": item.get("created_at", ""),
                "labels": [l.get("name", l) if isinstance(l, dict) else l for l in item.get("labels", [])],
                "url": item.get("html_url", ""),
            }
            if GIT_PROVIDER == "gitlab":
                issue["url"] = item.get("web_url", "")
            issues.append(issue)
        return {"success": True, "issues": issues, "total": len(issues)}
    return result


def _create_issue(title: str, body: str, labels: List[str] = None,
                  assignee: str = "") -> Dict:
    data = {"title": title, "body": body}
    if labels:
        data["labels"] = labels
    if assignee:
        if GIT_PROVIDER == "gitlab":
            data["assignee_ids"] = [assignee]
        else:
            data["assignees"] = [assignee]

    if GIT_PROVIDER == "gitlab":
        endpoint = f"projects/{_get_project_path()}/issues"
    else:
        endpoint = f"{_get_project_path()}/issues"

    result = _api_call("POST", endpoint, data)
    if result["success"]:
        item = result["data"]
        return {
            "success": True,
            "issue": {
                "number": item.get("number") or item.get("iid"),
                "title": item["title"],
                "state": item["state"],
                "url": item.get("html_url") or item.get("web_url", ""),
            },
            "message": f"Issue #{item.get('number') or item.get('iid')} criada com sucesso!"
        }
    return result


def _get_issue(issue_number: int) -> Dict:
    if GIT_PROVIDER == "gitlab":
        endpoint = f"projects/{_get_project_path()}/issues/{issue_number}"
    else:
        endpoint = f"{_get_project_path()}/issues/{issue_number}"
    result = _api_call("GET", endpoint)
    if result["success"]:
        item = result["data"]
        return {
            "success": True,
            "issue": {
                "number": item.get("number") or item.get("iid"),
                "title": item["title"],
                "body": item.get("body", item.get("description", "")),
                "state": item["state"],
                "labels": [l.get("name", l) if isinstance(l, dict) else l for l in item.get("labels", [])],
                "created_at": item.get("created_at", ""),
                "updated_at": item.get("updated_at", ""),
                "url": item.get("html_url") or item.get("web_url", ""),
            }
        }
    return result


def _update_issue(issue_number: int, state: str = "", title: str = "",
                  body: str = "", labels: List[str] = None) -> Dict:
    data = {}
    if state:
        data["state"] = state
    if title:
        data["title"] = title
    if body:
        data["body"] = body
    if labels is not None:
        data["labels"] = labels

    if not data:
        return {"success": False, "error": "Nenhum campo para atualizar"}

    if GIT_PROVIDER == "gitlab":
        endpoint = f"projects/{_get_project_path()}/issues/{issue_number}"
    else:
        endpoint = f"{_get_project_path()}/issues/{issue_number}"

    result = _api_call("PATCH", endpoint, data)
    if result["success"]:
        return {
            "success": True,
            "message": f"Issue #{issue_number} atualizada com sucesso!",
            "issue": {
                "number": result["data"].get("number") or result["data"].get("iid"),
                "state": result["data"]["state"],
                "title": result["data"]["title"],
            }
        }
    return result


def _list_pull_requests(state: str = "open", limit: int = 20) -> Dict:
    if GIT_PROVIDER == "gitlab":
        endpoint = f"projects/{_get_project_path()}/merge_requests?state={state}&per_page={limit}"
    else:
        endpoint = f"{_get_project_path()}/pulls?state={state}&per_page={limit}"

    result = _api_call("GET", endpoint)
    if result["success"]:
        prs = []
        for item in result["data"][:limit]:
            pr = {
                "number": item.get("number") or item.get("iid"),
                "title": item["title"],
                "state": item["state"],
                "branch": item.get("head", {}).get("ref", item.get("source_branch", "")),
                "target_branch": item.get("base", {}).get("ref", item.get("target_branch", "")),
                "created_at": item.get("created_at", ""),
                "url": item.get("html_url") or item.get("web_url", ""),
            }
            prs.append(pr)
        return {"success": True, "pull_requests": prs, "total": len(prs)}
    return result


def _create_pull_request(title: str, head: str, base: str = "main",
                         body: str = "", draft: bool = False) -> Dict:
    data = {
        "title": title,
        "head": head,
        "base": base,
    }
    if body:
        data["body"] = body
    if draft:
        data["draft"] = True

    if GIT_PROVIDER == "gitlab":
        data["source_branch"] = data.pop("head")
        data["target_branch"] = data.pop("base")
        endpoint = f"projects/{_get_project_path()}/merge_requests"
    else:
        endpoint = f"{_get_project_path()}/pulls"

    result = _api_call("POST", endpoint, data)
    if result["success"]:
        item = result["data"]
        return {
            "success": True,
            "pull_request": {
                "number": item.get("number") or item.get("iid"),
                "title": item["title"],
                "state": item["state"],
                "url": item.get("html_url") or item.get("web_url", ""),
            },
            "message": f"PR #{item.get('number') or item.get('iid')} criado com sucesso!"
        }
    return result


def _add_issue_comment(issue_number: int, comment: str) -> Dict:
    if GIT_PROVIDER == "gitlab":
        endpoint = f"projects/{_get_project_path()}/issues/{issue_number}/notes"
    else:
        endpoint = f"{_get_project_path()}/issues/{issue_number}/comments"

    result = _api_call("POST", endpoint, {"body": comment})
    if result["success"]:
        return {
            "success": True,
            "message": f"Comentario adicionado na issue #{issue_number} com sucesso!"
        }
    return result


def _list_branches(limit: int = 30) -> Dict:
    if GIT_PROVIDER == "gitlab":
        endpoint = f"projects/{_get_project_path()}/repository/branches?per_page={limit}"
    else:
        endpoint = f"{_get_project_path()}/branches?per_page={limit}"

    result = _api_call("GET", endpoint)
    if result["success"]:
        branches = []
        for item in result["data"][:limit]:
            branch = {
                "name": item["name"],
                "commit_sha": item.get("commit", {}).get("sha", "")[:8],
            }
            branches.append(branch)
        return {"success": True, "branches": branches, "total": len(branches)}
    return result


def _create_branch(branch_name: str, source_branch: str = "main") -> Dict:
    if GIT_PROVIDER == "gitlab":
        endpoint = f"projects/{_get_project_path()}/repository/branches"
        data = {"branch": branch_name, "ref": source_branch}
    else:
        sha_result = _api_call("GET", f"{_get_project_path()}/git/refs/heads/{source_branch}")
        if not sha_result["success"]:
            return {"success": False, "error": f"Nao foi possivel obter SHA da branch {source_branch}"}
        sha = sha_result["data"]["object"]["sha"]
        data = {"ref": f"refs/heads/{branch_name}", "sha": sha}
        endpoint = f"{_get_project_path()}/git/refs"

    result = _api_call("POST", endpoint, data)
    if result["success"]:
        return {
            "success": True,
            "message": f"Branch '{branch_name}' criada com sucesso a partir de '{source_branch}'!",
        }
    return result
