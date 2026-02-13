"""
QA Agent Browser - Automacao de Navegador com Selenium
======================================================

Ferramentas para interagir com paginas web:
- Navegar para URLs
- Tirar screenshots
- Interagir com elementos (clicar, digitar)
- Verificar elementos
- Executar testes E2E existentes (Selenium, Cypress, Playwright)
"""

import os
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import json

# Diretorios
BASE_DIR = Path(__file__).parent.parent
SCREENSHOTS_DIR = BASE_DIR / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

# Tentar importar Selenium
SELENIUM_AVAILABLE = False
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    SELENIUM_AVAILABLE = True
except ImportError:
    pass

# Driver global para reutilizar
_driver = None


def get_driver(headless: bool = True, enable_logging: bool = False) -> Any:
    """Obtem ou cria instancia do WebDriver"""
    global _driver

    if not SELENIUM_AVAILABLE:
        return None

    if _driver is None:
        try:
            options = Options()
            if headless:
                options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--disable-gpu")

            # Habilitar logging de rede se solicitado
            if enable_logging:
                options.set_capability('goog:loggingPrefs', {'performance': 'ALL', 'browser': 'ALL'})
                options.add_argument("--enable-logging")
                options.add_argument("--v=1")

            _driver = webdriver.Chrome(options=options)
            _driver.implicitly_wait(10)
        except Exception as e:
            return None

    return _driver


# Estado de monitoramento de sessao do usuario
_monitoring_session = {
    "active": False,
    "start_url": None,
    "actions": [],
    "network_requests": [],
    "screenshots": [],
    "start_time": None
}


def close_driver():
    """Fecha o driver"""
    global _driver
    if _driver:
        try:
            _driver.quit()
        except:
            pass
        _driver = None


def selenium_navigate(url: str, take_screenshot: bool = True, wait_seconds: int = 3) -> Dict[str, Any]:
    """
    Navega para uma URL e opcionalmente tira screenshot.
    NOTA: Este e o modo HEADLESS (invisivel). Para navegador visivel, use start_user_monitoring.

    Args:
        url: URL para navegar
        take_screenshot: Se deve tirar screenshot
        wait_seconds: Segundos para aguardar apos carregar

    Returns:
        Dict com resultado
    """
    global _monitoring_session

    if not SELENIUM_AVAILABLE:
        return {
            "success": False,
            "error": "Selenium nao instalado. Execute: pip install selenium"
        }

    # Se tem monitoramento ativo, NAO sobrescrever o driver visivel
    if _monitoring_session.get("active"):
        return {
            "success": False,
            "error": "ATENCAO: Ha uma sessao de monitoramento ativa! Use capture_user_state para capturar o estado atual, ou stop_user_monitoring para encerrar a sessao. NAO use selenium_navigate durante monitoramento pois isso fecharia o navegador visivel do usuario."
        }

    try:
        driver = get_driver(headless=True)
        if not driver:
            return {
                "success": False,
                "error": "Nao foi possivel iniciar o navegador. Verifique se o Chrome e ChromeDriver estao instalados."
            }

        driver.get(url)

        # Aguardar carregamento
        import time
        time.sleep(wait_seconds)

        result = {
            "success": True,
            "url": url,
            "title": driver.title,
            "current_url": driver.current_url
        }

        # Capturar erros visiveis na pagina
        page_source = driver.page_source.lower()
        errors_found = []

        error_indicators = [
            "error", "erro", "404", "500", "503",
            "not found", "nao encontrad", "falha", "failure",
            "exception", "traceback", "undefined"
        ]

        for indicator in error_indicators:
            if indicator in page_source:
                errors_found.append(indicator)

        result["possible_errors"] = errors_found[:5] if errors_found else []

        # Screenshot
        if take_screenshot:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            filepath = SCREENSHOTS_DIR / filename
            driver.save_screenshot(str(filepath))
            result["screenshot"] = str(filepath)

        # Extrair texto principal
        try:
            body = driver.find_element(By.TAG_NAME, "body")
            result["page_text"] = body.text[:2000] if body.text else ""
        except:
            result["page_text"] = ""

        return result

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def selenium_find_element(selector: str, selector_type: str = "css") -> Dict[str, Any]:
    """
    Encontra elemento na pagina atual.

    Args:
        selector: Seletor do elemento
        selector_type: Tipo de seletor (css, xpath, id, name, class)

    Returns:
        Dict com informacoes do elemento
    """
    if not SELENIUM_AVAILABLE:
        return {"success": False, "error": "Selenium nao instalado"}

    try:
        driver = get_driver()
        if not driver:
            return {"success": False, "error": "Navegador nao iniciado. Use selenium_navigate primeiro."}

        by_map = {
            "css": By.CSS_SELECTOR,
            "xpath": By.XPATH,
            "id": By.ID,
            "name": By.NAME,
            "class": By.CLASS_NAME,
            "tag": By.TAG_NAME
        }

        by = by_map.get(selector_type.lower(), By.CSS_SELECTOR)
        element = driver.find_element(by, selector)

        return {
            "success": True,
            "found": True,
            "tag": element.tag_name,
            "text": element.text[:500] if element.text else "",
            "visible": element.is_displayed(),
            "enabled": element.is_enabled()
        }

    except Exception as e:
        return {
            "success": True,
            "found": False,
            "error": str(e)
        }


def selenium_interact(selector: str, action: str, value: str = "", selector_type: str = "css") -> Dict[str, Any]:
    """
    Interage com elemento na pagina.

    Args:
        selector: Seletor do elemento
        action: Acao (click, type, clear, submit)
        value: Valor para digitar (se action=type)
        selector_type: Tipo de seletor

    Returns:
        Dict com resultado
    """
    if not SELENIUM_AVAILABLE:
        return {"success": False, "error": "Selenium nao instalado"}

    try:
        driver = get_driver()
        if not driver:
            return {"success": False, "error": "Navegador nao iniciado"}

        by_map = {
            "css": By.CSS_SELECTOR,
            "xpath": By.XPATH,
            "id": By.ID,
            "name": By.NAME,
            "class": By.CLASS_NAME
        }

        by = by_map.get(selector_type.lower(), By.CSS_SELECTOR)

        # Aguardar elemento
        wait = WebDriverWait(driver, 10)
        element = wait.until(EC.presence_of_element_located((by, selector)))

        if action == "click":
            element.click()
        elif action == "type":
            element.clear()
            element.send_keys(value)
        elif action == "clear":
            element.clear()
        elif action == "submit":
            element.submit()
        elif action == "enter":
            element.send_keys(Keys.ENTER)
        else:
            return {"success": False, "error": f"Acao desconhecida: {action}"}

        return {
            "success": True,
            "action": action,
            "selector": selector,
            "message": f"Acao '{action}' executada com sucesso"
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def selenium_screenshot(filename: str = "") -> Dict[str, Any]:
    """Tira screenshot da pagina atual"""
    if not SELENIUM_AVAILABLE:
        return {"success": False, "error": "Selenium nao instalado"}

    try:
        driver = get_driver()
        if not driver:
            return {"success": False, "error": "Navegador nao iniciado"}

        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"

        if not filename.endswith(".png"):
            filename += ".png"

        filepath = SCREENSHOTS_DIR / filename
        driver.save_screenshot(str(filepath))

        return {
            "success": True,
            "screenshot": str(filepath),
            "url": driver.current_url,
            "title": driver.title
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def selenium_check_page_errors(url: str = "") -> Dict[str, Any]:
    """
    Verifica erros visiveis em uma pagina.

    Args:
        url: URL para verificar (se vazio, usa pagina atual)

    Returns:
        Dict com erros encontrados
    """
    if not SELENIUM_AVAILABLE:
        return {"success": False, "error": "Selenium nao instalado"}

    try:
        driver = get_driver()
        if not driver:
            return {"success": False, "error": "Navegador nao iniciado"}

        if url:
            driver.get(url)
            import time
            time.sleep(2)

        page_source = driver.page_source
        page_text = driver.find_element(By.TAG_NAME, "body").text

        errors = []
        warnings = []

        # Verificar erros comuns
        error_patterns = [
            ("404", "Pagina nao encontrada (404)"),
            ("500", "Erro interno do servidor (500)"),
            ("503", "Servico indisponivel (503)"),
            ("error", "Mensagem de erro detectada"),
            ("erro", "Mensagem de erro detectada (PT)"),
            ("exception", "Excecao detectada"),
            ("traceback", "Traceback detectado"),
            ("undefined", "Variavel undefined detectada"),
            ("null", "Valor null detectado"),
            ("failed", "Falha detectada"),
            ("falhou", "Falha detectada (PT)"),
        ]

        for pattern, message in error_patterns:
            if pattern.lower() in page_text.lower():
                errors.append(message)

        # Verificar console (se possivel)
        try:
            logs = driver.get_log("browser")
            for log in logs:
                if log["level"] == "SEVERE":
                    errors.append(f"Console error: {log['message'][:100]}")
                elif log["level"] == "WARNING":
                    warnings.append(f"Console warning: {log['message'][:100]}")
        except:
            pass

        # Screenshot de evidencia
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = SCREENSHOTS_DIR / f"check_{timestamp}.png"
        driver.save_screenshot(str(screenshot_path))

        return {
            "success": True,
            "url": driver.current_url,
            "title": driver.title,
            "errors": errors[:10],
            "warnings": warnings[:10],
            "has_errors": len(errors) > 0,
            "screenshot": str(screenshot_path)
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def run_selenium_test(test_file: str) -> Dict[str, Any]:
    """
    Executa um arquivo de teste Selenium existente.

    Args:
        test_file: Caminho do arquivo de teste

    Returns:
        Dict com resultado
    """
    try:
        path = Path(test_file)
        if not path.is_absolute():
            path = BASE_DIR / test_file

        if not path.exists():
            return {"success": False, "error": f"Arquivo nao encontrado: {path}"}

        result = subprocess.run(
            ["python", str(path)],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(path.parent)
        )

        return {
            "success": result.returncode == 0,
            "file": str(path),
            "stdout": result.stdout[:5000] if result.stdout else "",
            "stderr": result.stderr[:2000] if result.stderr else "",
            "exit_code": result.returncode
        }

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Teste excedeu timeout de 5 minutos"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def run_cypress_test(spec_file: str = "", project_dir: str = "") -> Dict[str, Any]:
    """
    Executa testes Cypress.

    Args:
        spec_file: Arquivo spec especifico (opcional)
        project_dir: Diretorio do projeto Cypress

    Returns:
        Dict com resultado
    """
    try:
        if not project_dir:
            # Procurar diretorio Cypress no projeto
            possible_dirs = [
                BASE_DIR / "e2e_tests" / "exato_web",
                BASE_DIR / "e2e_tests",
                BASE_DIR / "cypress"
            ]
            for d in possible_dirs:
                if (d / "cypress.config.js").exists() or (d / "cypress.json").exists():
                    project_dir = str(d)
                    break

        if not project_dir:
            return {"success": False, "error": "Diretorio Cypress nao encontrado"}

        cmd = ["npx", "cypress", "run", "--headless"]

        if spec_file:
            cmd.extend(["--spec", spec_file])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
            cwd=project_dir,
            shell=True
        )

        return {
            "success": result.returncode == 0,
            "project": project_dir,
            "stdout": result.stdout[:5000] if result.stdout else "",
            "stderr": result.stderr[:2000] if result.stderr else "",
            "exit_code": result.returncode
        }

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Teste excedeu timeout de 10 minutos"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def run_playwright_test(test_file: str = "", project_dir: str = "") -> Dict[str, Any]:
    """
    Executa testes Playwright.

    Args:
        test_file: Arquivo de teste especifico (opcional)
        project_dir: Diretorio do projeto

    Returns:
        Dict com resultado
    """
    try:
        if not project_dir:
            project_dir = str(BASE_DIR)

        cmd = ["npx", "playwright", "test"]

        if test_file:
            cmd.append(test_file)

        cmd.append("--reporter=list")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
            cwd=project_dir,
            shell=True
        )

        return {
            "success": result.returncode == 0,
            "project": project_dir,
            "stdout": result.stdout[:5000] if result.stdout else "",
            "stderr": result.stderr[:2000] if result.stderr else "",
            "exit_code": result.returncode
        }

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Teste excedeu timeout de 10 minutos"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def start_user_monitoring(url: str, session_name: str = "default") -> Dict[str, Any]:
    """
    Abre navegador VISIVEL para o usuario interagir enquanto monitora acoes.

    Args:
        url: URL inicial para abrir
        session_name: Nome da sessao de monitoramento

    Returns:
        Dict com status da sessao
    """
    global _driver, _monitoring_session

    if not SELENIUM_AVAILABLE:
        return {
            "success": False,
            "error": "Selenium nao instalado. Execute: pip install selenium"
        }

    try:
        # Fechar driver existente se houver
        close_driver()

        # Criar novo driver VISIVEL (headless=False)
        options = Options()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--start-maximized")
        # Habilitar captura de logs de rede
        options.set_capability('goog:loggingPrefs', {'performance': 'ALL', 'browser': 'ALL'})

        _driver = webdriver.Chrome(options=options)
        _driver.implicitly_wait(10)

        # Navegar para URL
        _driver.get(url)

        # Inicializar sessao de monitoramento
        _monitoring_session = {
            "active": True,
            "session_name": session_name,
            "start_url": url,
            "actions": [],
            "network_requests": [],
            "screenshots": [],
            "start_time": datetime.now().isoformat()
        }

        # Screenshot inicial
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = SCREENSHOTS_DIR / f"monitor_{session_name}_{timestamp}.png"
        _driver.save_screenshot(str(screenshot_path))
        _monitoring_session["screenshots"].append(str(screenshot_path))

        return {
            "success": True,
            "browser_visible": True,
            "message": f"NAVEGADOR CHROME ABERTO E VISIVEL! O usuario pode navegar manualmente agora.",
            "session_name": session_name,
            "start_url": url,
            "screenshot_inicial": str(screenshot_path),
            "instructions": """
IMPORTANTE - LEIA COM ATENCAO:
1. O navegador Chrome esta ABERTO e VISIVEL na tela do usuario
2. O usuario pode navegar, clicar, digitar - voce NAO deve fazer nada automaticamente
3. AGUARDE o usuario dizer que pode capturar ou que terminou
4. Quando o usuario pedir, use 'capture_user_state' para capturar o estado atual
5. Quando o usuario disser que terminou, use 'stop_user_monitoring' para encerrar
6. NAO use selenium_navigate ou selenium_interact - isso fecharia o navegador do usuario!
""",
            "aviso": "NAO chame outras ferramentas de navegador. Aguarde comandos do usuario."
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def capture_user_state() -> Dict[str, Any]:
    """
    Captura estado atual da pagina durante monitoramento do usuario.
    Grava screenshot, URL atual, elementos interagidos, requests de rede.
    """
    global _driver, _monitoring_session

    if not _monitoring_session.get("active"):
        return {
            "success": False,
            "error": "Nenhuma sessao de monitoramento ativa. Use start_user_monitoring primeiro."
        }

    if not _driver:
        return {
            "success": False,
            "error": "Navegador nao esta aberto"
        }

    try:
        current_url = _driver.current_url
        page_title = _driver.title

        # Capturar screenshot
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_name = _monitoring_session.get("session_name", "default")
        screenshot_path = SCREENSHOTS_DIR / f"capture_{session_name}_{timestamp}.png"
        _driver.save_screenshot(str(screenshot_path))
        _monitoring_session["screenshots"].append(str(screenshot_path))

        # Registrar acao
        action = {
            "timestamp": timestamp,
            "url": current_url,
            "title": page_title,
            "screenshot": str(screenshot_path)
        }

        # Tentar capturar logs de rede
        try:
            perf_logs = _driver.get_log('performance')
            network_entries = []
            for entry in perf_logs:
                try:
                    msg = json.loads(entry['message'])['message']
                    if 'Network.requestWillBeSent' in msg.get('method', ''):
                        request_url = msg.get('params', {}).get('request', {}).get('url', '')
                        if request_url and not request_url.startswith('data:'):
                            network_entries.append({
                                "url": request_url,
                                "method": msg.get('params', {}).get('request', {}).get('method', 'GET')
                            })
                except:
                    pass
            action["network_requests"] = network_entries[:20]  # Limitar
            _monitoring_session["network_requests"].extend(network_entries[:20])
        except:
            pass

        # Capturar elementos visiveis/interativos
        try:
            interactive_elements = []
            # Botoes
            buttons = _driver.find_elements(By.TAG_NAME, "button")
            for btn in buttons[:10]:
                if btn.is_displayed():
                    interactive_elements.append({
                        "type": "button",
                        "text": btn.text[:50] if btn.text else "",
                        "id": btn.get_attribute("id") or "",
                        "class": btn.get_attribute("class") or ""
                    })
            # Inputs
            inputs = _driver.find_elements(By.TAG_NAME, "input")
            for inp in inputs[:10]:
                if inp.is_displayed():
                    interactive_elements.append({
                        "type": "input",
                        "name": inp.get_attribute("name") or "",
                        "id": inp.get_attribute("id") or "",
                        "placeholder": inp.get_attribute("placeholder") or ""
                    })
            # Links
            links = _driver.find_elements(By.TAG_NAME, "a")
            for link in links[:10]:
                if link.is_displayed() and link.get_attribute("href"):
                    interactive_elements.append({
                        "type": "link",
                        "text": link.text[:50] if link.text else "",
                        "href": link.get_attribute("href")[:100]
                    })
            action["interactive_elements"] = interactive_elements
        except:
            pass

        _monitoring_session["actions"].append(action)

        return {
            "success": True,
            "current_url": current_url,
            "page_title": page_title,
            "screenshot": str(screenshot_path),
            "elements_found": len(action.get("interactive_elements", [])),
            "network_requests_captured": len(action.get("network_requests", [])),
            "total_actions_recorded": len(_monitoring_session["actions"])
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def stop_user_monitoring() -> Dict[str, Any]:
    """
    Encerra sessao de monitoramento e retorna todos os dados capturados.
    """
    global _driver, _monitoring_session

    if not _monitoring_session.get("active"):
        return {
            "success": False,
            "error": "Nenhuma sessao de monitoramento ativa"
        }

    try:
        # Capturar estado final
        final_state = capture_user_state()

        # Compilar dados da sessao
        session_data = {
            "success": True,
            "session_name": _monitoring_session.get("session_name"),
            "start_url": _monitoring_session.get("start_url"),
            "start_time": _monitoring_session.get("start_time"),
            "end_time": datetime.now().isoformat(),
            "total_actions": len(_monitoring_session.get("actions", [])),
            "total_screenshots": len(_monitoring_session.get("screenshots", [])),
            "actions": _monitoring_session.get("actions", []),
            "all_network_requests": _monitoring_session.get("network_requests", []),
            "all_screenshots": _monitoring_session.get("screenshots", [])
        }

        # Extrair URLs unicas visitadas
        urls_visited = list(set([a.get("url") for a in _monitoring_session.get("actions", []) if a.get("url")]))
        session_data["urls_visited"] = urls_visited

        # Extrair endpoints de API unicos
        api_endpoints = list(set([
            r.get("url") for r in _monitoring_session.get("network_requests", [])
            if r.get("url") and ("api" in r.get("url", "").lower() or "/v1/" in r.get("url", ""))
        ]))
        session_data["api_endpoints"] = api_endpoints[:50]

        # Salvar dados em arquivo
        session_name = _monitoring_session.get("session_name", "default")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        data_file = SCREENSHOTS_DIR / f"session_{session_name}_{timestamp}.json"
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)
        session_data["data_file"] = str(data_file)

        # Resetar estado
        _monitoring_session = {
            "active": False,
            "start_url": None,
            "actions": [],
            "network_requests": [],
            "screenshots": [],
            "start_time": None
        }

        # Fechar navegador
        close_driver()

        return session_data

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def get_monitoring_status() -> Dict[str, Any]:
    """Retorna status atual do monitoramento"""
    global _monitoring_session

    if not _monitoring_session.get("active"):
        return {
            "active": False,
            "message": "Nenhuma sessao de monitoramento ativa"
        }

    return {
        "active": True,
        "session_name": _monitoring_session.get("session_name"),
        "start_url": _monitoring_session.get("start_url"),
        "start_time": _monitoring_session.get("start_time"),
        "actions_recorded": len(_monitoring_session.get("actions", [])),
        "screenshots_taken": len(_monitoring_session.get("screenshots", [])),
        "network_requests": len(_monitoring_session.get("network_requests", []))
    }


# Definicoes das ferramentas de browser para a API
BROWSER_TOOLS_DEFINITION = [
    {"name": "selenium_navigate", "description": "Abre URL no navegador HEADLESS e tira screenshot (usuario NAO ve)", "input_schema": {"type": "object", "properties": {"url": {"type": "string"}, "take_screenshot": {"type": "boolean", "default": True}}, "required": ["url"]}},
    {"name": "selenium_interact", "description": "Interage com elemento (click, type, clear)", "input_schema": {"type": "object", "properties": {"selector": {"type": "string"}, "action": {"type": "string", "enum": ["click", "type", "clear", "submit", "enter"]}, "value": {"type": "string", "default": ""}, "selector_type": {"type": "string", "default": "css"}}, "required": ["selector", "action"]}},
    {"name": "selenium_screenshot", "description": "Tira screenshot da pagina atual", "input_schema": {"type": "object", "properties": {"filename": {"type": "string", "default": ""}}, "required": []}},
    {"name": "selenium_check_errors", "description": "Verifica erros visiveis na pagina", "input_schema": {"type": "object", "properties": {"url": {"type": "string", "default": ""}}, "required": []}},
    {"name": "run_cypress_test", "description": "Executa testes Cypress", "input_schema": {"type": "object", "properties": {"spec_file": {"type": "string", "default": ""}}, "required": []}},
    {"name": "run_playwright_test", "description": "Executa testes Playwright", "input_schema": {"type": "object", "properties": {"test_file": {"type": "string", "default": ""}}, "required": []}},
    # NOVAS FERRAMENTAS DE MONITORAMENTO
    {"name": "start_user_monitoring", "description": "Abre navegador VISIVEL para o USUARIO navegar manualmente. O agente apenas observa e grava todas as acoes, cliques, URLs visitadas, endpoints de API. Usa quando o usuario quer testar manualmente enquanto voce monitora.", "input_schema": {"type": "object", "properties": {"url": {"type": "string", "description": "URL inicial para abrir"}, "session_name": {"type": "string", "default": "default", "description": "Nome da sessao para identificacao"}}, "required": ["url"]}},
    {"name": "capture_user_state", "description": "Captura estado atual da pagina durante monitoramento: screenshot, URL, elementos, requests de rede. Chame periodicamente enquanto o usuario navega.", "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "stop_user_monitoring", "description": "Encerra sessao de monitoramento e retorna TODOS os dados capturados: URLs visitadas, endpoints de API, screenshots, acoes. Fecha o navegador.", "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "get_monitoring_status", "description": "Verifica status atual do monitoramento: se esta ativo, quantas acoes gravadas, etc.", "input_schema": {"type": "object", "properties": {}, "required": []}}
]


def execute_browser_tool(tool_name: str, tool_input: Dict[str, Any]) -> str:
    """Executa uma ferramenta de browser"""
    try:
        if tool_name == "selenium_navigate":
            result = selenium_navigate(
                url=tool_input.get("url", ""),
                take_screenshot=tool_input.get("take_screenshot", True),
                wait_seconds=tool_input.get("wait_seconds", 3)
            )
        elif tool_name == "selenium_interact":
            result = selenium_interact(
                selector=tool_input.get("selector", ""),
                action=tool_input.get("action", "click"),
                value=tool_input.get("value", ""),
                selector_type=tool_input.get("selector_type", "css")
            )
        elif tool_name == "selenium_screenshot":
            result = selenium_screenshot(tool_input.get("filename", ""))
        elif tool_name == "selenium_check_errors":
            result = selenium_check_page_errors(tool_input.get("url", ""))
        elif tool_name == "selenium_find_element":
            result = selenium_find_element(
                selector=tool_input.get("selector", ""),
                selector_type=tool_input.get("selector_type", "css")
            )
        elif tool_name == "run_selenium_test":
            result = run_selenium_test(tool_input.get("test_file", ""))
        elif tool_name == "run_cypress_test":
            result = run_cypress_test(
                spec_file=tool_input.get("spec_file", ""),
                project_dir=tool_input.get("project_dir", "")
            )
        elif tool_name == "run_playwright_test":
            result = run_playwright_test(
                test_file=tool_input.get("test_file", ""),
                project_dir=tool_input.get("project_dir", "")
            )
        # NOVAS FERRAMENTAS DE MONITORAMENTO
        elif tool_name == "start_user_monitoring":
            result = start_user_monitoring(
                url=tool_input.get("url", ""),
                session_name=tool_input.get("session_name", "default")
            )
        elif tool_name == "capture_user_state":
            result = capture_user_state()
        elif tool_name == "stop_user_monitoring":
            result = stop_user_monitoring()
        elif tool_name == "get_monitoring_status":
            result = get_monitoring_status()
        else:
            result = {"error": f"Ferramenta desconhecida: {tool_name}"}

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e)})
