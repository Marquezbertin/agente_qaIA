"""
QA Agent Tools - Ferramentas para execucao real
================================================

Ferramentas que permitem ao agente executar acoes reais:
- Executar comandos no terminal
- Ler arquivos
- Escrever arquivos
- Rodar testes pytest
- Listar diretorios
"""

import subprocess
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
import json
import requests
from urllib.parse import quote_plus

# Diretorio base do projeto de testes
# Configuravel via variavel de ambiente TEST_PROJECT_DIR
# Se nao definido, usa a pasta sample_project/ inclusa no agente
BASE_DIR = Path(os.getenv("TEST_PROJECT_DIR", str(Path(__file__).parent.parent / "sample_project")))

# Configuracoes de ambiente de teste
# Cada ambiente aponta para uma API e um diretorio de testes
# Personalize com as URLs e diretorios do seu projeto
ENVIRONMENTS = {
    "Desenvolvimento": {
        "name": "Desenvolvimento",
        "api_base_url": "https://jsonplaceholder.typicode.com",
        "web_base_url": "https://jsonplaceholder.typicode.com",
        "test_dir": BASE_DIR / "tests",
        "env_file": BASE_DIR / ".env"
    },
    "Staging": {
        "name": "Staging",
        "api_base_url": "https://reqres.in/api",
        "web_base_url": "https://reqres.in",
        "test_dir": BASE_DIR / "tests",
        "env_file": BASE_DIR / ".env"
    }
}

# Ambiente atual (pode ser alterado pelo agente)
CURRENT_ENVIRONMENT = "Desenvolvimento"

# Pasta de auditoria - todo retorno de API/teste fica salvo aqui
AUDIT_DIR = BASE_DIR / "reports" / "json_retorno"
AUDIT_API_DIR = AUDIT_DIR / "api"
AUDIT_PYTEST_DIR = AUDIT_DIR / "pytest"
AUDIT_SCRIPTS_DIR = AUDIT_DIR / "scripts"

# Garantir que pastas existem
for _d in [AUDIT_API_DIR, AUDIT_PYTEST_DIR, AUDIT_SCRIPTS_DIR]:
    _d.mkdir(parents=True, exist_ok=True)


def _save_audit(subfolder: str, filename: str, data: dict) -> str:
    """
    Salva dados de auditoria em JSON.
    Retorna o caminho do arquivo salvo.
    """
    from datetime import datetime
    folder = AUDIT_DIR / subfolder
    folder.mkdir(parents=True, exist_ok=True)

    # Sanitizar filename
    safe_name = "".join(c if c.isalnum() or c in "-_." else "_" for c in filename)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = folder / f"{timestamp}_{safe_name}.json"

    try:
        # Remover token dos dados antes de salvar (seguranca)
        save_data = json.loads(json.dumps(data, ensure_ascii=False, default=str))
        if "request_data" in save_data and isinstance(save_data["request_data"], dict):
            if "token" in save_data["request_data"]:
                save_data["request_data"]["token"] = "***REDACTED***"

        with open(str(filepath), 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2, default=str)
        return str(filepath)
    except Exception as e:
        return f"Erro ao salvar auditoria: {e}"


def set_environment(env_name: str) -> Dict[str, Any]:
    """Define o ambiente atual de trabalho"""
    global CURRENT_ENVIRONMENT

    if env_name not in ENVIRONMENTS:
        return {
            "success": False,
            "error": f"Ambiente invalido: {env_name}. Disponiveis: {', '.join(ENVIRONMENTS.keys())}"
        }

    CURRENT_ENVIRONMENT = env_name
    env_config = ENVIRONMENTS[env_name]

    return {
        "success": True,
        "environment": env_name,
        "api_url": env_config["api_base_url"],
        "web_url": env_config["web_base_url"],
        "test_dir": str(env_config["test_dir"])
    }


def get_current_environment() -> Dict[str, Any]:
    """Retorna configuracao do ambiente atual"""
    env_config = ENVIRONMENTS[CURRENT_ENVIRONMENT]
    return {
        "name": CURRENT_ENVIRONMENT,
        "api_base_url": env_config["api_base_url"],
        "web_base_url": env_config["web_base_url"],
        "test_dir": str(env_config["test_dir"])
    }


def execute_command(command: str, timeout: int = 120) -> Dict[str, Any]:
    """
    Executa um comando no terminal.

    Args:
        command: Comando a executar
        timeout: Timeout em segundos (padrao 120)

    Returns:
        Dict com stdout, stderr, exit_code
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(BASE_DIR),
            encoding='utf-8',
            errors='replace'
        )

        return {
            "success": result.returncode == 0,
            "stdout": result.stdout[:10000] if result.stdout else "",
            "stderr": result.stderr[:5000] if result.stderr else "",
            "exit_code": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Comando excedeu o timeout de {timeout} segundos",
            "exit_code": -1
        }
    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": str(e),
            "exit_code": -1
        }


def read_file(file_path: str) -> Dict[str, Any]:
    """
    Le conteudo de um arquivo.

    Args:
        file_path: Caminho do arquivo (relativo ao BASE_DIR ou absoluto)

    Returns:
        Dict com conteudo do arquivo
    """
    try:
        # Resolver caminho
        path = Path(file_path)
        if not path.is_absolute():
            path = BASE_DIR / path

        if not path.exists():
            return {
                "success": False,
                "content": "",
                "error": f"Arquivo nao encontrado: {path}"
            }

        if not path.is_file():
            return {
                "success": False,
                "content": "",
                "error": f"Caminho nao e um arquivo: {path}"
            }

        # Limitar tamanho
        if path.stat().st_size > 100000:  # 100KB
            return {
                "success": False,
                "content": "",
                "error": "Arquivo muito grande (>100KB)"
            }

        content = path.read_text(encoding='utf-8', errors='replace')

        return {
            "success": True,
            "content": content,
            "path": str(path),
            "size": len(content)
        }
    except Exception as e:
        return {
            "success": False,
            "content": "",
            "error": str(e)
        }


def write_file(file_path: str, content: str) -> Dict[str, Any]:
    """
    Escreve conteudo em um arquivo.

    Args:
        file_path: Caminho do arquivo
        content: Conteudo a escrever

    Returns:
        Dict com resultado da operacao
    """
    try:
        path = Path(file_path)
        if not path.is_absolute():
            path = BASE_DIR / path

        # Criar diretorio se nao existir
        path.parent.mkdir(parents=True, exist_ok=True)

        path.write_text(content, encoding='utf-8')

        return {
            "success": True,
            "path": str(path),
            "size": len(content),
            "message": f"Arquivo salvo: {path}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def list_directory(directory: str = ".", pattern: str = "*") -> Dict[str, Any]:
    """
    Lista arquivos em um diretorio.

    Args:
        directory: Diretorio a listar
        pattern: Padrao glob (ex: "*.py", "test_*.py")

    Returns:
        Dict com lista de arquivos
    """
    try:
        path = Path(directory)
        if not path.is_absolute():
            path = BASE_DIR / path

        if not path.exists():
            return {
                "success": False,
                "files": [],
                "error": f"Diretorio nao encontrado: {path}"
            }

        files = []
        for item in path.glob(pattern):
            files.append({
                "name": item.name,
                "path": str(item.relative_to(BASE_DIR)) if str(item).startswith(str(BASE_DIR)) else str(item),
                "is_dir": item.is_dir(),
                "size": item.stat().st_size if item.is_file() else 0
            })

        # Ordenar: diretorios primeiro, depois por nome
        files.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))

        return {
            "success": True,
            "directory": str(path),
            "files": files[:100],  # Limitar a 100 itens
            "total": len(files)
        }
    except Exception as e:
        return {
            "success": False,
            "files": [],
            "error": str(e)
        }


def is_standalone_script(file_path: Path) -> bool:
    """
    Detecta se um arquivo Python e um script standalone (nao pytest).

    Criterios para script standalone:
    - Tem if __name__ == "__main__" com chamada de funcao
    - NAO tem funcoes test_* no padrao pytest
    - Tem classe com __init__ que começa com Test (pytest nao aceita)
    """
    if not file_path.exists() or not file_path.suffix == '.py':
        return False

    try:
        content = file_path.read_text(encoding='utf-8', errors='ignore')

        # Verifica se tem main
        has_main = 'if __name__' in content and '__main__' in content

        # Verifica se tem funcoes pytest (def test_)
        has_pytest_functions = 'def test_' in content

        # Verifica se tem classe Test com __init__ (pytest nao aceita)
        import re
        has_test_class_with_init = bool(re.search(r'class\s+Test\w+.*?def\s+__init__', content, re.DOTALL))

        # E standalone se:
        # 1. Tem main E nao tem funcoes pytest
        # 2. OU tem classe Test com __init__ (pytest vai falhar)
        if has_main and not has_pytest_functions:
            return True
        if has_test_class_with_init and not has_pytest_functions:
            return True

        return False
    except Exception:
        return False


def run_python_script(script_path: str, args: str = "", timeout: int = 300) -> Dict[str, Any]:
    """
    Executa um script Python diretamente (nao como teste pytest).

    Util para scripts standalone que tem if __name__ == "__main__".

    Args:
        script_path: Caminho do script Python
        args: Argumentos para passar ao script
        timeout: Timeout em segundos

    Returns:
        Dict com resultado da execucao
    """
    # Encontrar o script
    path = Path(script_path)
    if not path.is_absolute():
        path = BASE_DIR / script_path

    if not path.exists():
        # Fallback: buscar recursivamente - ambiente atual primeiro
        found = None
        search_name = script_path if script_path.endswith(".py") else f"{script_path}.py"
        skip_dirs = {"venv", ".venv", "node_modules", "__pycache__", ".git"}

        def _safe_rglob(base_dir, name):
            """rglob que ignora venv/node_modules"""
            return [m for m in base_dir.rglob(name)
                    if not any(d in m.parts for d in skip_dirs)]

        # 1. Ambiente atual primeiro
        current_env_cfg = ENVIRONMENTS.get(CURRENT_ENVIRONMENT)
        if current_env_cfg:
            matches = _safe_rglob(current_env_cfg["test_dir"], search_name)
            if matches:
                found = matches[0]

        # 2. Outros ambientes
        if not found:
            for env_name, env_cfg in ENVIRONMENTS.items():
                if env_name == CURRENT_ENVIRONMENT:
                    continue
                matches = _safe_rglob(env_cfg["test_dir"], search_name)
                if matches:
                    found = matches[0]
                    break

        if found:
            path = found
        else:
            return {
                "success": False,
                "error": f"Script nao encontrado: {path}",
                "script_path": str(path)
            }

    # Usar o mesmo Python que esta executando o agente
    python_cmd = f'"{sys.executable}"'

    # Montar comando
    command = f'{python_cmd} "{path}"'
    if args:
        command += f" {args}"

    result = execute_command(command, timeout=timeout)

    script_result = {
        "success": result["success"],
        "script_path": str(path),
        "command": command,
        "output": result["stdout"],
        "stderr": result["stderr"],
        "exit_code": result["exit_code"],
        "execution_type": "standalone_script"
    }

    # Salvar auditoria
    audit_filename = f"{CURRENT_ENVIRONMENT}_{path.stem}"
    audit_path = _save_audit("scripts", audit_filename, script_result)
    script_result["audit_file"] = audit_path

    return script_result


def run_pytest(test_path: str = "", markers: str = "", verbose: bool = True, max_failures: int = 0, environment: str = "") -> Dict[str, Any]:
    """
    Executa testes pytest.

    Detecta automaticamente se o arquivo e um script standalone e usa
    python direto em vez de pytest quando apropriado.

    Args:
        test_path: Caminho do teste ou diretorio (relativo ao BASE_DIR ou absoluto)
                   Exemplos: "security_tests", "bruno_pentest", "api_tests/tests/test_api.py"
        markers: Markers pytest (ex: "security", "smoke", "api", "regression")
        verbose: Modo verbose
        max_failures: Parar apos N falhas
        environment: Ambiente especifico (UAT ou Producao). Se vazio, usa o ambiente atual.

    Returns:
        Dict com resultado dos testes
    """
    # Determinar ambiente para variaveis de ambiente
    env_name = environment if environment else CURRENT_ENVIRONMENT
    env_config = ENVIRONMENTS.get(env_name, ENVIRONMENTS["UAT"])

    # Normalizar "." para vazio (usar diretorio padrao do ambiente)
    if test_path in (".", "./", ".\\"):
        test_path = ""

    # Resolver caminho do teste primeiro
    resolved_path = None
    if test_path:
        possible_paths = [
            Path(test_path),  # Caminho absoluto
            BASE_DIR / test_path,  # Relativo ao projeto
            env_config["test_dir"] / test_path,  # Relativo ao ambiente
        ]

        for p in possible_paths:
            if p.exists():
                resolved_path = p
                break

        # Fallback: busca recursiva no test_dir do ambiente (exclui venv/node_modules)
        if not resolved_path and not Path(test_path).is_absolute():
            skip_dirs = {"venv", ".venv", "node_modules", "__pycache__", ".git"}

            def _safe_rglob(base_dir, name):
                return [m for m in base_dir.rglob(name)
                        if not any(d in m.parts for d in skip_dirs)]

            matches = _safe_rglob(env_config["test_dir"], test_path)
            if not matches and not test_path.endswith(".py"):
                matches = _safe_rglob(env_config["test_dir"], f"{test_path}.py")
            if not matches:
                # Tentar outros ambientes
                for other_env, other_cfg in ENVIRONMENTS.items():
                    if other_cfg["test_dir"] == env_config["test_dir"]:
                        continue
                    matches = _safe_rglob(other_cfg["test_dir"], test_path)
                    if not matches and not test_path.endswith(".py"):
                        matches = _safe_rglob(other_cfg["test_dir"], f"{test_path}.py")
                    if matches:
                        break
            if matches:
                resolved_path = matches[0]

    # Se e um arquivo Python unico, verificar se e script standalone
    if resolved_path and resolved_path.is_file() and resolved_path.suffix == '.py':
        if is_standalone_script(resolved_path):
            # Executar como script Python direto
            result = run_python_script(str(resolved_path))
            result["detection"] = "Detectado como script standalone (nao pytest)"
            result["environment"] = env_name
            return result

    # Estrategia para encontrar pytest:
    # 1. Tentar pytest do ambiente especifico (UAT ou Producao tem seus proprios venvs)
    # 2. Tentar Python do sistema com pytest
    # 3. Fallback para pytest global

    # Estrategia: usar venv do projeto se existir, senao Python atual
    env_venv_python = env_config["test_dir"] / "venv" / "Scripts" / "python.exe"

    if env_venv_python.exists():
        cmd_parts = [f'"{env_venv_python}" -m pytest']
    else:
        # Usar o mesmo Python que esta executando o agente
        cmd_parts = [f'"{sys.executable}" -m pytest']

    # Adicionar caminho do teste
    if resolved_path:
        cmd_parts.append(f'"{resolved_path}"')
    elif test_path:
        # Usar o caminho como passado (pode ser um padrao)
        cmd_parts.append(f'"{test_path}"')
    else:
        # Se nenhum caminho especificado, usar o diretorio do ambiente ou raiz
        if env_config["test_dir"].exists():
            cmd_parts.append(f'"{env_config["test_dir"]}"')
        else:
            # Rodar na raiz do projeto (usa pytest.ini)
            cmd_parts.append(f'"{BASE_DIR}"')

    if markers:
        cmd_parts.append(f"-m \"{markers}\"")

    if verbose:
        cmd_parts.append("-v")

    if max_failures > 0:
        cmd_parts.append(f"--maxfail={max_failures}")
    cmd_parts.append("--tb=short")
    cmd_parts.append("--no-header")

    command = " ".join(cmd_parts)

    # Executar subprocess diretamente (nao usar execute_command)
    # para capturar output COMPLETO e parsear stats corretamente
    import re
    from datetime import datetime as _dt

    # Registrar timestamp ANTES da execucao para encontrar arquivos novos depois
    _run_start = _dt.now()

    # Determinar cwd: usar diretorio do ambiente se o teste esta dentro dele
    run_cwd = str(BASE_DIR)
    if resolved_path:
        for _env_key, _env_cfg in ENVIRONMENTS.items():
            try:
                resolved_path.relative_to(_env_cfg["test_dir"])
                run_cwd = str(_env_cfg["test_dir"])
                break
            except ValueError:
                continue

    try:
        proc_result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=1800,
            cwd=run_cwd,
            encoding='utf-8',
            errors='replace'
        )
        full_stdout = proc_result.stdout or ""
        full_stderr = proc_result.stderr or ""
        exit_code = proc_result.returncode
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "test_status": "timeout",
            "command": command,
            "output": f"Testes excederam o timeout de 1800 segundos (30 min)",
            "stderr": "",
            "stats": {"passed": 0, "failed": 0, "skipped": 0, "errors": 0},
            "total_tests": 0,
            "pass_rate": "N/A",
            "exit_code": -1,
            "environment": env_name,
            "api_url": env_config["api_base_url"]
        }
    except Exception as e:
        return {
            "success": False,
            "test_status": "error",
            "command": command,
            "output": "",
            "stderr": str(e),
            "stats": {"passed": 0, "failed": 0, "skipped": 0, "errors": 0},
            "total_tests": 0,
            "pass_rate": "N/A",
            "exit_code": -1,
            "environment": env_name,
            "api_url": env_config["api_base_url"]
        }

    # Extrair estatisticas do output COMPLETO (stdout + stderr como fallback)
    combined_output = full_stdout + "\n" + full_stderr
    stats = {
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "errors": 0
    }

    # Metodo 1: buscar na summary line do pytest (ex: "27 passed, 1 failed in 10.5s")
    match = re.search(r"(\d+) passed", combined_output)
    if match:
        stats["passed"] = int(match.group(1))

    match = re.search(r"(\d+) failed", combined_output)
    if match:
        stats["failed"] = int(match.group(1))

    match = re.search(r"(\d+) skipped", combined_output)
    if match:
        stats["skipped"] = int(match.group(1))

    match = re.search(r"(\d+) error", combined_output)
    if match:
        stats["errors"] = int(match.group(1))

    # Metodo 2 (fallback): se summary nao tem numeros, contar linhas individuais
    # Cobre caso onde pytest morre antes de imprimir summary (ex: timeout)
    if stats["passed"] + stats["failed"] + stats["skipped"] + stats["errors"] == 0:
        stats["passed"] = len(re.findall(r" PASSED", combined_output))
        stats["failed"] = len(re.findall(r" FAILED", combined_output))
        stats["skipped"] = len(re.findall(r" SKIPPED", combined_output))
        stats["errors"] = len(re.findall(r" ERROR", combined_output))
        # Contar timeouts do pytest-timeout como errors
        timeout_count = len(re.findall(r"\+* Timeout \+*", combined_output))
        if timeout_count > 0:
            stats["errors"] += timeout_count

    # Usar stdout, ou stderr como fallback se stdout vazio
    raw_output = full_stdout if full_stdout.strip() else full_stderr

    # Truncar output de forma inteligente: inicio + final (summary sempre visivel)
    if len(raw_output) > 10000:
        output = raw_output[:7000] + "\n\n... [output truncado] ...\n\n" + raw_output[-3000:]
    else:
        output = raw_output

    # Determinar status da execucao:
    # exit_code 0 = todos passaram
    # exit_code 1 = testes rodaram mas alguns falharam (NAO e erro de sistema)
    # exit_code 2+ = erro de coleta/sistema
    tests_ran = stats["passed"] + stats["failed"] + stats["skipped"] > 0

    if exit_code == 0:
        test_status = "all_passed"
        success = True
    elif exit_code == 1 and tests_ran:
        test_status = "tests_failed"
        success = True  # Testes RODARAM com sucesso, alguns falharam
    elif exit_code == 2:
        test_status = "collection_error"
        success = False
    elif exit_code == 5:
        test_status = "no_tests_found"
        success = False
    else:
        test_status = "error" if not tests_ran else "tests_failed"
        success = tests_ran

    total = stats["passed"] + stats["failed"] + stats["skipped"]
    pass_rate = f"{(stats['passed'] / total * 100):.1f}%" if total > 0 else "N/A"

    result = {
        "success": success,
        "test_status": test_status,
        "command": command,
        "output": output,
        "stderr": full_stderr[:3000],
        "stats": stats,
        "total_tests": total,
        "pass_rate": pass_rate,
        "exit_code": exit_code,
        "environment": env_name,
        "api_url": env_config["api_base_url"],
        "INSTRUCAO": f"DADOS REAIS: passed={stats['passed']}, failed={stats['failed']}, skipped={stats['skipped']}, total={total}, pass_rate={pass_rate}. Mostre EXATAMENTE estes numeros ao usuario. NUNCA invente outros valores."
    }

    # Salvar auditoria
    test_label = "all"
    if resolved_path:
        test_label = resolved_path.stem
    elif test_path:
        test_label = Path(test_path).stem
    audit_filename = f"{env_name}_{test_label}"
    audit_path = _save_audit("pytest", audit_filename, result)
    result["audit_file"] = audit_path

    # Escanear reports/respostas/ para arquivos gerados DURANTE esta execucao
    # O conftest.py ResponseSaver salva JSONs individuais por teste aqui
    respostas_dir = BASE_DIR / "reports" / "respostas"
    response_files = []
    try:
        if respostas_dir.exists():
            for f in sorted(respostas_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
                if f.is_file() and f.suffix == ".json":
                    mtime = _dt.fromtimestamp(f.stat().st_mtime)
                    if mtime >= _run_start:
                        response_files.append(str(f.relative_to(BASE_DIR)))
                    else:
                        break  # Arquivos mais antigos que o inicio da run
    except Exception:
        pass

    if response_files:
        result["response_files"] = response_files
        result["response_files_dir"] = str(respostas_dir.relative_to(BASE_DIR))
        result["INSTRUCAO_JSON"] = (
            f"Os JSONs individuais de cada teste estao salvos em {len(response_files)} arquivos na pasta "
            f"reports/respostas/. Use read_file para ler qualquer um deles e mostrar ao usuario. "
            f"NUNCA invente o conteudo - leia o arquivo real."
        )

    return result


def search_in_files(pattern: str, directory: str = ".", file_pattern: str = "*.py") -> Dict[str, Any]:
    """
    Busca padrao em arquivos.

    Args:
        pattern: Padrao de texto a buscar
        directory: Diretorio onde buscar
        file_pattern: Padrao de arquivos (ex: "*.py")

    Returns:
        Dict com resultados da busca
    """
    try:
        path = Path(directory)
        if not path.is_absolute():
            path = BASE_DIR / path

        results = []

        for file_path in path.rglob(file_pattern):
            if file_path.is_file():
                try:
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                    lines = content.split('\n')

                    for i, line in enumerate(lines, 1):
                        if pattern.lower() in line.lower():
                            results.append({
                                "file": str(file_path.relative_to(BASE_DIR)) if str(file_path).startswith(str(BASE_DIR)) else str(file_path),
                                "line": i,
                                "content": line.strip()[:200]
                            })

                            if len(results) >= 50:
                                break
                except:
                    pass

            if len(results) >= 50:
                break

        return {
            "success": True,
            "pattern": pattern,
            "results": results,
            "total": len(results)
        }
    except Exception as e:
        return {
            "success": False,
            "results": [],
            "error": str(e)
        }


# ============================================================================
# NOVAS FERRAMENTAS: BUSCA WEB E REPOSITORIOS LOCAIS
# ============================================================================

def web_search(query: str, num_results: int = 5) -> Dict[str, Any]:
    """
    Realiza busca na web usando DuckDuckGo (sem necessidade de API key).

    Args:
        query: Termo de busca
        num_results: Numero de resultados (padrao 5)

    Returns:
        Dict com resultados da busca
    """
    try:
        # Usar DuckDuckGo HTML para busca (nao requer API)
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        # Parsear resultados simples
        from html.parser import HTMLParser
        import re

        results = []
        html_content = response.text

        # Extrair links e titulos usando regex simples
        # Buscar padrao de resultados do DuckDuckGo
        pattern = r'<a rel="nofollow" class="result__a" href="([^"]+)"[^>]*>([^<]+)</a>'
        matches = re.findall(pattern, html_content)

        for i, (link, title) in enumerate(matches[:num_results]):
            # Decodificar URL do DuckDuckGo
            if "uddg=" in link:
                actual_url = link.split("uddg=")[-1].split("&")[0]
                from urllib.parse import unquote
                actual_url = unquote(actual_url)
            else:
                actual_url = link

            results.append({
                "title": title.strip(),
                "url": actual_url,
                "position": i + 1
            })

        return {
            "success": True,
            "query": query,
            "results": results,
            "total": len(results)
        }

    except Exception as e:
        return {
            "success": False,
            "query": query,
            "results": [],
            "error": str(e)
        }


def fetch_url(url: str, extract_text: bool = True, use_javascript: bool = False) -> Dict[str, Any]:
    """
    Busca conteudo de uma URL.

    Args:
        url: URL para buscar
        extract_text: Se True, extrai apenas texto (remove HTML)
        use_javascript: Se True, usa Selenium para renderizar JavaScript (para paginas dinamicas)

    Returns:
        Dict com conteudo da pagina
    """
    # Se precisa de JavaScript, usar funcao especializada
    if use_javascript:
        return fetch_url_with_js(url, extract_text=extract_text)

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        content = response.text

        if extract_text:
            # Remover tags HTML de forma simples
            import re
            # Remover scripts e styles
            content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
            content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL)
            # Remover tags HTML
            content = re.sub(r'<[^>]+>', ' ', content)
            # Limpar espacos
            content = re.sub(r'\s+', ' ', content).strip()
            # Limitar tamanho
            content = content[:10000]

        return {
            "success": True,
            "url": url,
            "status_code": response.status_code,
            "content": content,
            "content_length": len(content),
            "javascript_rendered": False
        }

    except Exception as e:
        return {
            "success": False,
            "url": url,
            "error": str(e)
        }


def fetch_url_with_js(url: str, extract_text: bool = True, wait_seconds: int = 5,
                      scroll_to_bottom: bool = True, max_content_length: int = 50000) -> Dict[str, Any]:
    """
    Busca conteudo de uma URL usando Selenium para renderizar JavaScript.
    Ideal para paginas dinamicas como documentacoes SPA, React, Vue, etc.

    Args:
        url: URL para buscar
        extract_text: Se True, extrai apenas texto (remove HTML)
        wait_seconds: Segundos para aguardar carregamento do JavaScript
        scroll_to_bottom: Se True, rola a pagina para carregar conteudo lazy-loaded
        max_content_length: Tamanho maximo do conteudo retornado (padrao 50KB)

    Returns:
        Dict com conteudo da pagina renderizada
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        import time
        import re
    except ImportError:
        return {
            "success": False,
            "url": url,
            "error": "Selenium nao instalado. Execute: pip install selenium"
        }

    driver = None
    try:
        # Configurar Chrome em modo headless
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-web-security")
        options.add_argument("--allow-running-insecure-content")
        # User agent para evitar bloqueios
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(30)
        driver.implicitly_wait(10)

        # Navegar para a URL
        driver.get(url)

        # Aguardar carregamento inicial
        time.sleep(wait_seconds)

        # Rolar pagina para carregar conteudo lazy-loaded
        if scroll_to_bottom:
            # Scroll gradual para carregar todo conteudo
            last_height = driver.execute_script("return document.body.scrollHeight")
            scroll_attempts = 0
            max_scroll_attempts = 10

            while scroll_attempts < max_scroll_attempts:
                # Scroll para baixo
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)

                # Verificar se chegou ao final
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
                scroll_attempts += 1

            # Voltar ao topo
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(0.5)

        # Extrair conteudo
        page_title = driver.title
        current_url = driver.current_url

        if extract_text:
            # Extrair texto do body
            try:
                body = driver.find_element(By.TAG_NAME, "body")
                content = body.text
            except:
                content = ""

            # Se o texto estiver vazio, tentar extrair do HTML renderizado
            if not content or len(content) < 100:
                html_source = driver.page_source
                # Remover scripts e styles
                content = re.sub(r'<script[^>]*>.*?</script>', '', html_source, flags=re.DOTALL | re.IGNORECASE)
                content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL | re.IGNORECASE)
                content = re.sub(r'<noscript[^>]*>.*?</noscript>', '', content, flags=re.DOTALL | re.IGNORECASE)
                # Remover tags HTML
                content = re.sub(r'<[^>]+>', ' ', content)
                # Decodificar entidades HTML comuns
                content = content.replace('&nbsp;', ' ')
                content = content.replace('&amp;', '&')
                content = content.replace('&lt;', '<')
                content = content.replace('&gt;', '>')
                content = content.replace('&quot;', '"')
                # Limpar espacos
                content = re.sub(r'\s+', ' ', content).strip()
        else:
            # Retornar HTML completo renderizado
            content = driver.page_source

        # Limitar tamanho
        content = content[:max_content_length]

        # Extrair links da pagina (util para navegacao em documentacao)
        links = []
        try:
            link_elements = driver.find_elements(By.TAG_NAME, "a")
            for link in link_elements[:100]:  # Limitar a 100 links
                href = link.get_attribute("href")
                text = link.text.strip()
                if href and text:
                    links.append({"text": text[:100], "url": href})
        except:
            pass

        # Extrair headings (estrutura da pagina)
        headings = []
        try:
            for tag in ["h1", "h2", "h3"]:
                elements = driver.find_elements(By.TAG_NAME, tag)
                for el in elements[:20]:
                    text = el.text.strip()
                    if text:
                        headings.append({"level": tag, "text": text[:200]})
        except:
            pass

        return {
            "success": True,
            "url": url,
            "current_url": current_url,
            "title": page_title,
            "content": content,
            "content_length": len(content),
            "javascript_rendered": True,
            "links_count": len(links),
            "links": links[:50],  # Retornar ate 50 links
            "headings": headings,
            "scroll_attempts": scroll_attempts if scroll_to_bottom else 0
        }

    except Exception as e:
        return {
            "success": False,
            "url": url,
            "error": str(e),
            "javascript_rendered": True
        }

    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass


def search_local_repositories(query: str, file_extensions: List[str] = None, max_results: int = 30) -> Dict[str, Any]:
    """
    Busca texto em arquivos do projeto de testes.

    Args:
        query: Texto a buscar
        file_extensions: Lista de extensoes (ex: [".py", ".json"]). Se None, busca em todas.
        max_results: Numero maximo de resultados

    Returns:
        Dict com resultados encontrados
    """
    try:
        all_results = []

        if file_extensions is None:
            file_extensions = [".py", ".js", ".ts", ".json", ".yaml", ".yml", ".md", ".txt"]

        if not BASE_DIR.exists():
            return {"success": False, "query": query, "results": [], "error": f"Diretorio nao encontrado: {BASE_DIR}"}

        for ext in file_extensions:
            for file_path in BASE_DIR.rglob(f"*{ext}"):
                if file_path.is_file():
                    try:
                        if file_path.stat().st_size > 500000:
                            continue
                        content = file_path.read_text(encoding='utf-8', errors='ignore')
                        lines = content.split('\n')
                        for i, line in enumerate(lines, 1):
                            if query.lower() in line.lower():
                                relative_path = str(file_path.relative_to(BASE_DIR))
                                all_results.append({
                                    "file": relative_path,
                                    "line": i,
                                    "content": line.strip()[:300],
                                    "full_path": str(file_path)
                                })
                                if len(all_results) >= max_results:
                                    break
                    except Exception:
                        pass
                if len(all_results) >= max_results:
                    break
            if len(all_results) >= max_results:
                break

        return {
            "success": True,
            "query": query,
            "results": all_results,
            "total": len(all_results),
            "search_directory": str(BASE_DIR)
        }

    except Exception as e:
        return {
            "success": False,
            "query": query,
            "results": [],
            "error": str(e)
        }


def get_repository_structure(repository: str = "all", max_depth: int = 3) -> Dict[str, Any]:
    """
    Retorna estrutura de pastas do projeto de testes.

    Args:
        repository: Ignorado (mantido para compatibilidade)
        max_depth: Profundidade maxima de subpastas

    Returns:
        Dict com estrutura de pastas
    """
    def get_tree(path: Path, current_depth: int = 0) -> Dict:
        if current_depth >= max_depth:
            return {"name": path.name, "type": "dir", "truncated": True}

        items = []
        try:
            for item in sorted(path.iterdir()):
                if item.name.startswith('.') or item.name == '__pycache__' or item.name == 'node_modules':
                    continue

                if item.is_dir():
                    items.append(get_tree(item, current_depth + 1))
                else:
                    items.append({
                        "name": item.name,
                        "type": "file",
                        "size": item.stat().st_size
                    })
        except PermissionError:
            pass

        return {
            "name": path.name,
            "type": "dir",
            "children": items[:50]
        }

    try:
        if not BASE_DIR.exists():
            return {"success": False, "error": f"Diretorio nao encontrado: {BASE_DIR}"}

        structure = get_tree(BASE_DIR)

        return {
            "success": True,
            "structures": {BASE_DIR.name: structure},
            "repositories": [BASE_DIR.name]
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# =============================================================================
# CATALOGO DE ENDPOINTS PARA TESTE DIRETO
# =============================================================================

KNOWN_ENDPOINTS = {
    # JSONPlaceholder - API REST fake para testes (https://jsonplaceholder.typicode.com)
    "posts": {"path": "/posts", "method": "GET", "required": [], "description": "Listar todos os posts"},
    "post_by_id": {"path": "/posts/1", "method": "GET", "required": [], "description": "Obter post por ID"},
    "create_post": {"path": "/posts", "method": "POST", "required": ["title", "body", "userId"], "description": "Criar novo post"},
    "users": {"path": "/users", "method": "GET", "required": [], "description": "Listar todos os usuarios"},
    "comments": {"path": "/comments", "method": "GET", "required": [], "description": "Listar todos os comentarios"},
    "todos": {"path": "/todos", "method": "GET", "required": [], "description": "Listar todas as tarefas"},
    # ReqRes.in - API que simula autenticacao (https://reqres.in)
    "reqres_users": {"path": "/users", "method": "GET", "required": [], "description": "Listar usuarios (ReqRes)"},
    "reqres_register": {"path": "/register", "method": "POST", "required": ["email", "password"], "description": "Registrar usuario (ReqRes)"},
    "reqres_login": {"path": "/login", "method": "POST", "required": ["email", "password"], "description": "Login (ReqRes)"},
    # HTTPBin - API para teste de requisicoes HTTP (https://httpbin.org)
    "httpbin_get": {"path": "/get", "method": "GET", "required": [], "description": "Testar GET (HTTPBin)"},
    "httpbin_post": {"path": "/post", "method": "POST", "required": [], "description": "Testar POST (HTTPBin)"},
}


def _load_env_config(env_name: str = "") -> Dict[str, str]:
    """Carrega token e base_url do ambiente especificado (ou atual)"""
    env = env_name or CURRENT_ENVIRONMENT
    if env not in ENVIRONMENTS:
        env = CURRENT_ENVIRONMENT

    env_config = ENVIRONMENTS[env]
    env_file = env_config["env_file"]

    # Defaults dos .env
    api_base_url = str(env_config["api_base_url"])
    api_token = ""

    # Ler token do .env do ambiente
    if env_file.exists():
        try:
            with open(str(env_file), 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        if key == "API_TOKEN":
                            api_token = value
                        elif key == "API_BASE_URL":
                            api_base_url = value
        except Exception:
            pass

    return {
        "api_base_url": api_base_url,
        "api_token": api_token,
        "environment": env
    }


def run_api_test(endpoint_name: str = "", endpoint_path: str = "", method: str = "POST",
                 data: Dict[str, Any] = None, environment: str = "",
                 expected_status: List[int] = None) -> Dict[str, Any]:
    """
    Testa um endpoint da API diretamente sem precisar escrever codigo Python.

    Args:
        endpoint_name: Nome do endpoint conhecido (cpf, cnpj, sintegra_unificada, etc)
        endpoint_path: Caminho customizado (ex: /receita-federal/cpf)
        method: Metodo HTTP (GET, POST, PUT, DELETE)
        data: Dados para enviar (body JSON para POST, query params para GET)
        environment: Ambiente (UAT ou Producao). Usa o atual se nao especificado.
        expected_status: Lista de status HTTP esperados para validacao

    Returns:
        Dict com resultado do teste
    """
    import time

    try:
        # Resolver endpoint
        if endpoint_name and endpoint_name in KNOWN_ENDPOINTS:
            ep = KNOWN_ENDPOINTS[endpoint_name]
            path = ep["path"]
            method = ep["method"]
            required = ep["required"]
            description = ep["description"]

            # Validar parametros obrigatorios
            if data is None:
                data = {}
            missing = [p for p in required if p not in data]
            if missing:
                return {
                    "success": False,
                    "error": f"Parametros obrigatorios faltando: {', '.join(missing)}",
                    "required_params": required,
                    "provided_params": list(data.keys()),
                    "endpoint": endpoint_name
                }
        elif endpoint_path:
            path = endpoint_path
            description = f"Custom: {endpoint_path}"
        else:
            return {
                "success": False,
                "error": "Informe endpoint_name ou endpoint_path. Use list_api_endpoints para ver disponiveis."
            }

        # Carregar configuracao do ambiente
        env_cfg = _load_env_config(environment)
        if not env_cfg["api_token"]:
            return {
                "success": False,
                "error": f"Token nao encontrado no .env do ambiente {env_cfg['environment']}"
            }

        # Montar URL e headers
        url = f"{env_cfg['api_base_url']}{path}"
        api_token = env_cfg['api_token']
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        # Executar request
        start_time = time.time()
        try:
            req_timeout = 120  # 2 min - SINTEGRA pode levar 40-60s
            if method.upper() == "GET":
                response = requests.get(url, params=data, headers=headers, timeout=req_timeout)
            elif method.upper() == "POST":
                response = requests.post(url, json=data, headers=headers, timeout=req_timeout)
            elif method.upper() == "PUT":
                response = requests.put(url, json=data, headers=headers, timeout=req_timeout)
            elif method.upper() == "DELETE":
                response = requests.delete(url, params=data, headers=headers, timeout=req_timeout)
            else:
                return {"success": False, "error": f"Metodo HTTP invalido: {method}"}
        except requests.exceptions.Timeout:
            elapsed_timeout = round(time.time() - start_time, 2)
            timeout_result = {
                "success": True,
                "test_passed": False,
                "endpoint": endpoint_name or path,
                "description": description,
                "environment": env_cfg["environment"],
                "url": url,
                "method": method.upper(),
                "request_data": data,
                "status_code": 0,
                "expected_status": expected_status or [200, 201, 400, 402],
                "status_ok": False,
                "response_time_seconds": elapsed_timeout,
                "response_body": {"error": f"Timeout: API nao respondeu em {req_timeout}s"},
                "INSTRUCAO": "A API excedeu o tempo limite. Isso pode acontecer com endpoints lentos como SINTEGRA. Tente novamente ou aumente o timeout."
            }
            ep_label = endpoint_name or path.replace("/", "_").strip("_")
            extra = ""
            if data:
                if "uf" in data:
                    extra = f"_{data['uf']}"
                elif "cpf" in data:
                    extra = f"_cpf{data['cpf'][-4:]}"
                elif "cnpj" in data:
                    extra = f"_cnpj{data['cnpj'][-4:]}"
            _save_audit("api", f"{env_cfg['environment']}_{ep_label}{extra}_TIMEOUT", timeout_result)
            return timeout_result
        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "error": f"Erro de conexao com {url}",
                "url": url, "method": method.upper()
            }

        elapsed = round(time.time() - start_time, 2)

        # Processar resposta
        status_code = response.status_code

        # Tentar parsear JSON
        response_body = None
        try:
            response_body = response.json()
        except Exception:
            response_body = response.text[:3000] if response.text else ""

        # Validar status
        if expected_status is None:
            expected_status = [200, 201, 400, 402]
        status_ok = status_code in expected_status

        # Truncar resposta se muito grande (manter mais dados para evitar alucinacao)
        response_str = json.dumps(response_body, ensure_ascii=False, default=str) if isinstance(response_body, (dict, list)) else str(response_body)
        if len(response_str) > 15000:
            response_str = response_str[:15000] + "... [RESPOSTA TRUNCADA - dados acima sao REAIS]"
            response_body = response_str

        result = {
            "success": True,
            "test_passed": status_ok,
            "endpoint": endpoint_name or path,
            "description": description,
            "environment": env_cfg["environment"],
            "url": url,
            "method": method.upper(),
            "request_data": data,
            "status_code": status_code,
            "expected_status": expected_status,
            "status_ok": status_ok,
            "response_time_seconds": elapsed,
            "response_body": response_body,
            "INSTRUCAO": "O campo response_body acima contem os DADOS REAIS da API. Quando o usuario pedir para ver o JSON ou resultado, copie EXATAMENTE este response_body. NUNCA invente ou modifique os dados."
        }

        # Salvar auditoria
        ep_label = endpoint_name or path.replace("/", "_").strip("_")
        extra = ""
        if data:
            if "uf" in data:
                extra = f"_{data['uf']}"
            elif "cpf" in data:
                extra = f"_cpf{data['cpf'][-4:]}"
            elif "cnpj" in data:
                extra = f"_cnpj{data['cnpj'][-4:]}"
        audit_filename = f"{env_cfg['environment']}_{ep_label}{extra}"
        audit_path = _save_audit("api", audit_filename, result)
        result["audit_file"] = audit_path

        return result

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "endpoint": endpoint_name or endpoint_path
        }


def list_api_endpoints(category: str = "") -> Dict[str, Any]:
    """
    Lista todos os endpoints disponiveis para teste com run_api_test.

    Args:
        category: Filtrar por categoria (receita, sintegra, exato, cnj, cgu, sancoes, tcu, account)

    Returns:
        Dict com lista de endpoints
    """
    endpoints = []
    for name, ep in KNOWN_ENDPOINTS.items():
        if category:
            # Filtro simples por categoria
            cat_lower = category.lower()
            path_lower = ep["path"].lower()
            name_lower = name.lower()
            if cat_lower not in path_lower and cat_lower not in name_lower:
                continue

        endpoints.append({
            "name": name,
            "path": ep["path"],
            "method": ep["method"],
            "required_params": ep["required"],
            "description": ep["description"]
        })

    return {
        "success": True,
        "endpoints": endpoints,
        "total": len(endpoints),
        "usage": "Use run_api_test(endpoint_name='posts') ou run_api_test(endpoint_name='reqres_login', data={'email': 'eve.holt@reqres.in', 'password': 'cityslicka'})"
    }


def get_test_response(pattern: str = "", latest: int = 1) -> Dict[str, Any]:
    """
    Le JSONs de resposta salvos pelo ResponseSaver durante execucao de testes.
    Pasta: reports/respostas/

    SEMPRE use esta ferramenta quando o usuario pedir para ver JSON/resultado/resposta de um teste.

    Args:
        pattern: Filtro para buscar no nome do arquivo (ex: "DF", "AP", "sintegra_SP").
                 Se vazio, lista os arquivos disponiveis.
        latest: Quantos arquivos retornar (mais recente primeiro). Padrao 1.

    Returns:
        Dict com conteudo JSON real dos arquivos encontrados
    """
    respostas_dir = BASE_DIR / "reports" / "respostas"

    if not respostas_dir.exists():
        return {
            "success": False,
            "error": f"Pasta de respostas nao encontrada: {respostas_dir}"
        }

    # Listar todos os JSONs, mais recentes primeiro
    try:
        all_files = sorted(
            [f for f in respostas_dir.iterdir() if f.is_file() and f.suffix == ".json"],
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
    except Exception as e:
        return {"success": False, "error": str(e)}

    if not all_files:
        return {
            "success": False,
            "error": "Nenhum arquivo de resposta encontrado em reports/respostas/"
        }

    # Filtrar por padrao
    if pattern:
        pattern_lower = pattern.lower().strip().replace(" ", "_")
        matched = [f for f in all_files if pattern_lower in f.name.lower()]
    else:
        matched = all_files

    if not matched:
        available = [f.name for f in all_files[:30]]
        return {
            "success": False,
            "error": f"Nenhum arquivo encontrado com padrao '{pattern}'",
            "available_files": available,
            "INSTRUCAO": "Arquivos disponiveis listados acima. Tente com outro padrao."
        }

    # Ler os N mais recentes
    results = []
    for f in matched[:latest]:
        try:
            content = json.loads(f.read_text(encoding='utf-8'))
            results.append({
                "file": f.name,
                "path": str(f.relative_to(BASE_DIR)),
                "content": content
            })
        except Exception as e:
            results.append({
                "file": f.name,
                "error": str(e)
            })

    return {
        "success": True,
        "pattern": pattern,
        "total_found": len(matched),
        "results": results,
        "INSTRUCAO": "O campo 'content' contem o JSON REAL salvo durante o teste. Mostre EXATAMENTE este conteudo ao usuario em bloco ```json. NUNCA invente dados."
    }


# Definicao das ferramentas COMPACTA (economiza tokens)
TOOLS_DEFINITION = [
    {"name": "execute_command", "description": "Executa comando no terminal", "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}},
    {"name": "read_file", "description": "Le arquivo", "input_schema": {"type": "object", "properties": {"file_path": {"type": "string"}}, "required": ["file_path"]}},
    {"name": "write_file", "description": "Escreve arquivo", "input_schema": {"type": "object", "properties": {"file_path": {"type": "string"}, "content": {"type": "string"}}, "required": ["file_path", "content"]}},
    {"name": "list_directory", "description": "Lista pasta", "input_schema": {"type": "object", "properties": {"directory": {"type": "string", "default": "."}, "pattern": {"type": "string", "default": "*"}}, "required": []}},
    {"name": "run_pytest", "description": "Executa testes pytest ou scripts de teste. USE ESTA TOOL para qualquer arquivo test_*.py ou *_prod.py ou qualquer arquivo com testes. Busca recursivamente se nao achar no caminho direto. Detecta scripts standalone automaticamente.", "input_schema": {"type": "object", "properties": {"test_path": {"type": "string", "default": ""}, "markers": {"type": "string", "default": ""}, "environment": {"type": "string", "default": "", "description": "Ambiente: UAT ou Producao"}}, "required": []}},
    {"name": "run_python_script", "description": "Executa script Python standalone (SOMENTE para scripts utilitarios com if __name__==main, NAO para arquivos de teste). Para arquivos de teste use run_pytest.", "input_schema": {"type": "object", "properties": {"script_path": {"type": "string"}, "args": {"type": "string", "default": ""}}, "required": ["script_path"]}},
    {"name": "search_in_files", "description": "Busca texto em arquivos", "input_schema": {"type": "object", "properties": {"pattern": {"type": "string"}, "directory": {"type": "string", "default": "."}}, "required": ["pattern"]}},
    {"name": "web_search", "description": "Pesquisa na web", "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "fetch_url", "description": "Acessa URL (use_javascript=true para paginas dinamicas)", "input_schema": {"type": "object", "properties": {"url": {"type": "string"}, "use_javascript": {"type": "boolean", "default": False, "description": "Use true para paginas que requerem JavaScript (React, Vue, SPAs, documentacoes)"}}, "required": ["url"]}},
    {"name": "fetch_url_with_js", "description": "Acessa URL com JavaScript (Selenium) - ideal para documentacoes, SPAs e paginas dinamicas", "input_schema": {"type": "object", "properties": {"url": {"type": "string"}, "wait_seconds": {"type": "integer", "default": 5, "description": "Segundos para aguardar carregamento"}, "scroll_to_bottom": {"type": "boolean", "default": True, "description": "Rolar pagina para carregar conteudo lazy-loaded"}, "max_content_length": {"type": "integer", "default": 50000}}, "required": ["url"]}},
    {"name": "search_local_repositories", "description": "Busca texto em arquivos do projeto de testes", "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "set_environment", "description": "Define ambiente de trabalho", "input_schema": {"type": "object", "properties": {"env_name": {"type": "string", "description": "Nome do ambiente (ex: Desenvolvimento, Staging)"}}, "required": ["env_name"]}},
    {"name": "run_api_test", "description": "Testa endpoint da API diretamente (sem escrever codigo). Use endpoint_name para conhecidos (posts, users, reqres_login, etc) ou endpoint_path para custom.", "input_schema": {"type": "object", "properties": {"endpoint_name": {"type": "string", "description": "Nome do endpoint (posts, users, reqres_login, httpbin_get, etc)"}, "endpoint_path": {"type": "string", "description": "Caminho customizado (ex: /posts)"}, "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE"], "default": "POST"}, "data": {"type": "object", "description": "Dados da requisicao (JSON body para POST, query params para GET)"}, "environment": {"type": "string", "description": "Ambiente (usa o atual se vazio)"}, "expected_status": {"type": "array", "items": {"type": "integer"}, "description": "Status HTTP esperados (padrao: [200,201,400,402])"}}, "required": []}},
    {"name": "list_api_endpoints", "description": "Lista todos os endpoints disponiveis para teste com run_api_test. Pode filtrar por categoria.", "input_schema": {"type": "object", "properties": {"category": {"type": "string", "description": "Filtrar por categoria (jsonplaceholder, reqres, httpbin)"}}, "required": []}},
    {"name": "get_test_response", "description": "Le JSON de resposta REAL salvo dos testes (reports/respostas). OBRIGATORIO usar quando o usuario pedir para ver JSON, resultado, retorno ou resposta de qualquer teste. Busca por padrao no nome do arquivo (ex: 'DF', 'AP', 'sintegra_SP', 'cpf'). NUNCA invente JSON - use esta ferramenta.", "input_schema": {"type": "object", "properties": {"pattern": {"type": "string", "description": "Filtro para buscar (ex: 'DF', 'AP', 'sintegra_SP', 'cpf')"}, "latest": {"type": "integer", "default": 1, "description": "Quantos resultados retornar (mais recentes primeiro)"}}, "required": ["pattern"]}}
]


def execute_tool(tool_name: str, tool_input: Dict[str, Any]) -> str:
    """
    Executa uma ferramenta pelo nome.

    Args:
        tool_name: Nome da ferramenta
        tool_input: Parametros da ferramenta

    Returns:
        Resultado em formato string
    """
    try:
        if tool_name == "set_environment":
            result = set_environment(tool_input.get("env_name", "UAT"))
        elif tool_name == "execute_command":
            result = execute_command(tool_input.get("command", ""), tool_input.get("timeout", 120))
        elif tool_name == "read_file":
            result = read_file(tool_input.get("file_path", ""))
        elif tool_name == "write_file":
            result = write_file(tool_input.get("file_path", ""), tool_input.get("content", ""))
        elif tool_name == "list_directory":
            result = list_directory(tool_input.get("directory", "."), tool_input.get("pattern", "*"))
        elif tool_name == "run_pytest":
            result = run_pytest(
                test_path=tool_input.get("test_path", ""),
                markers=tool_input.get("markers", ""),
                verbose=tool_input.get("verbose", True),
                max_failures=tool_input.get("max_failures", 0),
                environment=tool_input.get("environment", "")
            )
        elif tool_name == "run_python_script":
            result = run_python_script(
                script_path=tool_input.get("script_path", ""),
                args=tool_input.get("args", ""),
                timeout=tool_input.get("timeout", 300)
            )
        elif tool_name == "search_in_files":
            result = search_in_files(
                pattern=tool_input.get("pattern", ""),
                directory=tool_input.get("directory", "."),
                file_pattern=tool_input.get("file_pattern", "*.py")
            )
        elif tool_name == "web_search":
            result = web_search(tool_input.get("query", ""), tool_input.get("num_results", 5))
        elif tool_name == "fetch_url":
            result = fetch_url(
                url=tool_input.get("url", ""),
                extract_text=tool_input.get("extract_text", True),
                use_javascript=tool_input.get("use_javascript", False)
            )
        elif tool_name == "fetch_url_with_js":
            result = fetch_url_with_js(
                url=tool_input.get("url", ""),
                extract_text=tool_input.get("extract_text", True),
                wait_seconds=tool_input.get("wait_seconds", 5),
                scroll_to_bottom=tool_input.get("scroll_to_bottom", True),
                max_content_length=tool_input.get("max_content_length", 50000)
            )
        elif tool_name == "search_local_repositories":
            result = search_local_repositories(
                query=tool_input.get("query", ""),
                file_extensions=tool_input.get("file_extensions") or None,
                max_results=tool_input.get("max_results", 30)
            )
        elif tool_name == "get_repository_structure":
            result = get_repository_structure(
                repository=tool_input.get("repository", "all"),
                max_depth=tool_input.get("max_depth", 3)
            )
        elif tool_name == "get_environment":
            result = get_current_environment()
        elif tool_name == "run_api_test":
            result = run_api_test(
                endpoint_name=tool_input.get("endpoint_name", ""),
                endpoint_path=tool_input.get("endpoint_path", ""),
                method=tool_input.get("method", "POST"),
                data=tool_input.get("data"),
                environment=tool_input.get("environment", ""),
                expected_status=tool_input.get("expected_status")
            )
        elif tool_name == "list_api_endpoints":
            result = list_api_endpoints(
                category=tool_input.get("category", "")
            )
        elif tool_name == "get_test_response":
            result = get_test_response(
                pattern=tool_input.get("pattern", ""),
                latest=tool_input.get("latest", 1)
            )
        else:
            result = {"error": f"Ferramenta desconhecida: {tool_name}"}

        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})
