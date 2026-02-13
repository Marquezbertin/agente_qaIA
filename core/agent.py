"""
QA Agent - Agente de IA para Automacao de Testes
================================================

Agente inteligente que atua como QA Engineer Senior,
capaz de analisar, criar, executar e reportar testes.
"""

import os
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

# Adicionar path do projeto
sys.path.insert(0, str(Path(__file__).parent.parent))

from anthropic import Anthropic
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.markdown import Markdown

from config.settings import AgentConfig, Environment, KNOWLEDGE_REPOS
from core.knowledge_manager import KnowledgeManager
from core.test_analyzer import TestAnalyzer
from core.test_generator import TestGenerator
from core.test_executor import TestExecutor
from core.report_generator import ReportGenerator


console = Console()


class AgentCommand(Enum):
    """Comandos disponiveis do agente"""
    ANALISAR = "analisar"
    CRIAR_TESTE = "criar"
    EXECUTAR = "executar"
    RELATORIO = "relatorio"
    COBERTURA = "cobertura"
    SUGERIR = "sugerir"
    DESCOBRIR = "descobrir"
    HELP = "help"
    SAIR = "sair"


class QAAgent:
    """
    Agente de QA Inteligente

    Responsabilidades:
    - Analisar codigo e identificar cenarios de teste
    - Criar casos de teste e scripts automatizados
    - Executar testes em ambientes UAT/Producao
    - Gerar relatorios detalhados
    - Sugerir melhorias e novos cenarios
    """

    SYSTEM_PROMPT = """Voce e um Engenheiro de QA Senior especializado em automacao de testes.
Seu nome e QA Agent. Voce possui expertise em:

- Testes funcionais, de integracao, E2E, API e performance
- Frameworks: Pytest, Selenium, Playwright, Requests
- Analise de codigo e identificacao de cenarios de teste
- Boas praticas de QA e metodologias ageis

CONTEXTO DO PROJETO:
Voce tem acesso ao repositorio de testes do projeto, que inclui:
- Scripts de teste existentes (API, seguranca, E2E)
- Configuracoes e fixtures (conftest.py, pytest.ini)
- Banco de dados de demonstracao com dados ficticios (CPFs, CNPJs)

APIs DE TESTE DISPONIVEIS:
- JSONPlaceholder (https://jsonplaceholder.typicode.com) - API REST fake
- ReqRes.in (https://reqres.in) - API com autenticacao simulada
- HTTPBin (https://httpbin.org) - API para teste de requisicoes HTTP

DIRETRIZES:
1. Sempre analise o codigo existente ANTES de criar novos testes
2. Mantenha consistencia com padroes ja estabelecidos
3. Maximize cobertura sem criar testes redundantes
4. Documente suas decisoes e sugestoes
5. NUNCA invente dados de resposta - sempre use os dados reais

FORMATO DE RESPOSTA:
- Use markdown para formatacao
- Inclua exemplos de codigo quando relevante
- Seja conciso mas completo
- Indique claramente acoes que serao executadas"""

    def __init__(self, config: Optional[AgentConfig] = None):
        self.config = config or AgentConfig()
        self.client = Anthropic(api_key=self.config.anthropic_api_key)
        self.conversation_history: List[Dict[str, str]] = []

        # Inicializar componentes
        self.knowledge = KnowledgeManager(KNOWLEDGE_REPOS)
        self.analyzer = TestAnalyzer(self.knowledge)
        self.generator = TestGenerator(self.knowledge)
        self.executor = TestExecutor(self.config)
        self.reporter = ReportGenerator(self.config)

        # Estado
        self.current_env: Environment = Environment.UAT
        self.session_start = datetime.now()

    def initialize(self) -> Dict[str, Any]:
        """Inicializa o agente e mapeia os repositorios"""
        console.print(Panel.fit(
            "[bold cyan]QA Agent[/bold cyan] - Iniciando...",
            border_style="cyan"
        ))

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            # Mapear repositorios
            task = progress.add_task("Mapeando repositorios...", total=None)
            repo_stats = self.knowledge.scan_repositories()
            progress.update(task, description="Repositorios mapeados!")

            # Identificar testes existentes
            progress.update(task, description="Identificando testes existentes...")
            test_stats = self.analyzer.scan_existing_tests()
            progress.update(task, description="Testes identificados!")

            # Carregar configs de ambiente
            progress.update(task, description="Carregando configuracoes...")
            env_status = {
                "UAT": self.config.uat_config is not None,
                "Producao": self.config.prod_config is not None
            }
            progress.update(task, description="Pronto!")

        # Exibir resumo
        self._display_initialization_summary(repo_stats, test_stats, env_status)

        return {
            "repositories": repo_stats,
            "tests": test_stats,
            "environments": env_status
        }

    def _display_initialization_summary(
        self,
        repo_stats: Dict,
        test_stats: Dict,
        env_status: Dict
    ):
        """Exibe resumo da inicializacao"""
        # Tabela de repositorios
        repo_table = Table(title="Repositorios Base de Conhecimento")
        repo_table.add_column("Repositorio", style="cyan")
        repo_table.add_column("Arquivos Python", justify="right")
        repo_table.add_column("Arquivos de Teste", justify="right")
        repo_table.add_column("Status", justify="center")

        for repo_name, stats in repo_stats.items():
            repo_table.add_row(
                repo_name,
                str(stats.get("python_files", 0)),
                str(stats.get("test_files", 0)),
                "[green]OK[/green]" if stats.get("accessible") else "[red]ERRO[/red]"
            )
        console.print(repo_table)

        # Tabela de testes
        test_table = Table(title="Testes Existentes por Categoria")
        test_table.add_column("Categoria", style="yellow")
        test_table.add_column("Quantidade", justify="right")
        test_table.add_column("Cobertura", justify="right")

        for category, count in test_stats.get("by_category", {}).items():
            test_table.add_row(
                category,
                str(count),
                f"{test_stats.get('coverage', {}).get(category, 0):.1f}%"
            )
        console.print(test_table)

        # Status dos ambientes
        env_table = Table(title="Ambientes Configurados")
        env_table.add_column("Ambiente", style="magenta")
        env_table.add_column("URL", style="dim")
        env_table.add_column("Status", justify="center")

        for env_name, is_configured in env_status.items():
            config = self.config.uat_config if env_name == "UAT" else self.config.prod_config
            url = config.api_base_url if config else "N/A"
            status = "[green]Configurado[/green]" if is_configured else "[red]Nao configurado[/red]"
            env_table.add_row(env_name, url, status)
        console.print(env_table)

    def chat(self, user_message: str) -> str:
        """Processa mensagem do usuario e retorna resposta"""
        # Adicionar contexto atual
        context = self._build_context()
        enhanced_message = f"{context}\n\nUsuario: {user_message}"

        self.conversation_history.append({
            "role": "user",
            "content": enhanced_message
        })

        # Chamar API do Claude
        response = self.client.messages.create(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            system=self.SYSTEM_PROMPT,
            messages=self.conversation_history
        )

        assistant_message = response.content[0].text
        self.conversation_history.append({
            "role": "assistant",
            "content": assistant_message
        })

        return assistant_message

    def _build_context(self) -> str:
        """Constroi contexto para a conversa"""
        return f"""[Contexto Atual]
- Ambiente ativo: {self.current_env.value}
- Sessao iniciada: {self.session_start.strftime('%Y-%m-%d %H:%M:%S')}
- Testes mapeados: {self.analyzer.total_tests}
- Ultimo comando: {self.conversation_history[-1]['content'][:50] if self.conversation_history else 'N/A'}"""

    def execute_command(self, command: str, args: List[str] = None) -> str:
        """Executa um comando especifico"""
        args = args or []
        cmd = command.lower().strip()

        if cmd == "analisar":
            return self._cmd_analyze(args)
        elif cmd == "criar":
            return self._cmd_create_test(args)
        elif cmd == "executar":
            return self._cmd_execute(args)
        elif cmd == "relatorio":
            return self._cmd_report(args)
        elif cmd == "cobertura":
            return self._cmd_coverage(args)
        elif cmd == "sugerir":
            return self._cmd_suggest(args)
        elif cmd == "descobrir":
            return self._cmd_discover(args)
        elif cmd == "env":
            return self._cmd_set_env(args)
        elif cmd == "help":
            return self._cmd_help()
        else:
            return self.chat(f"{command} {' '.join(args)}")

    def _cmd_analyze(self, args: List[str]) -> str:
        """Analisa codigo e sugere testes"""
        if not args:
            return "Uso: analisar <caminho/arquivo>\nExemplo: analisar security_tests/"

        target = args[0]
        console.print(f"[cyan]Analisando:[/cyan] {target}")

        analysis = self.analyzer.analyze(target)

        # Usar IA para enriquecer analise
        prompt = f"""Analise o seguinte codigo/diretorio e sugira casos de teste:

Alvo: {target}
Analise tecnica:
{analysis}

Forneca:
1. Cenarios de teste identificados
2. Gaps de cobertura
3. Sugestoes de casos de teste em formato Gherkin
4. Prioridade de cada teste (Alta/Media/Baixa)"""

        return self.chat(prompt)

    def _cmd_create_test(self, args: List[str]) -> str:
        """Cria casos de teste"""
        if not args:
            return "Uso: criar <funcionalidade> [--env uat|prod]\nExemplo: criar validacao_cpf --env uat"

        feature = args[0]
        env = Environment.UAT

        if "--env" in args:
            env_idx = args.index("--env")
            if env_idx + 1 < len(args):
                env = Environment(args[env_idx + 1].lower())

        console.print(f"[cyan]Criando teste para:[/cyan] {feature} [cyan]em[/cyan] {env.value}")

        # Buscar contexto relevante
        context = self.knowledge.search_relevant_code(feature)

        prompt = f"""Crie casos de teste para a funcionalidade: {feature}

Ambiente alvo: {env.value}
Contexto do codigo existente:
{context}

Gere:
1. Casos de teste em formato Gherkin (BDD)
2. Script pytest correspondente
3. Dados de teste necessarios
4. Marcadores pytest apropriados (@pytest.mark.{env.value}, @pytest.mark.smoke, etc)

Use os padroes existentes no repositorio de testes."""

        response = self.chat(prompt)

        # Extrair e salvar script gerado
        if "```python" in response:
            script = self.generator.extract_and_save_script(response, feature, env)
            if script:
                response += f"\n\n[Script salvo em: {script}]"

        return response

    def _cmd_execute(self, args: List[str]) -> str:
        """Executa testes"""
        suite = args[0] if args else "smoke"
        env = self.current_env

        if "--env" in args:
            env_idx = args.index("--env")
            if env_idx + 1 < len(args):
                env = Environment(args[env_idx + 1].lower())

        console.print(f"[cyan]Executando suite:[/cyan] {suite} [cyan]em[/cyan] {env.value}")

        # Executar testes
        results = self.executor.run_tests(suite, env)

        # Gerar resposta
        prompt = f"""Analise os resultados da execucao de testes:

Suite: {suite}
Ambiente: {env.value}
Resultados:
{results}

Forneca:
1. Resumo executivo
2. Testes que falharam e possiveis causas
3. Recomendacoes de acao
4. Proximos passos sugeridos"""

        return self.chat(prompt)

    def _cmd_report(self, args: List[str]) -> str:
        """Gera relatorio"""
        period = args[0] if args else "today"

        console.print(f"[cyan]Gerando relatorio:[/cyan] {period}")

        report_data = self.reporter.generate_report(period)
        report_path = self.reporter.save_report(report_data)

        return f"""Relatorio gerado com sucesso!

**Arquivo:** {report_path}

**Resumo:**
- Total de testes: {report_data.get('total_tests', 0)}
- Passou: {report_data.get('passed', 0)}
- Falhou: {report_data.get('failed', 0)}
- Taxa de sucesso: {report_data.get('success_rate', 0):.1f}%

Abra o arquivo para ver detalhes completos."""

    def _cmd_coverage(self, args: List[str]) -> str:
        """Analisa cobertura de testes"""
        console.print("[cyan]Analisando cobertura...[/cyan]")

        coverage = self.analyzer.analyze_coverage()

        prompt = f"""Analise a cobertura de testes atual:

{coverage}

Identifique:
1. Areas com baixa cobertura
2. Funcionalidades criticas sem testes
3. Sugestoes para aumentar cobertura
4. Prioridades de implementacao"""

        return self.chat(prompt)

    def _cmd_suggest(self, args: List[str]) -> str:
        """Sugere novos cenarios de teste"""
        console.print("[cyan]Gerando sugestoes...[/cyan]")

        # Analisar gaps
        gaps = self.analyzer.find_test_gaps()
        recent_changes = self.knowledge.get_recent_changes()

        prompt = f"""Com base na analise dos repositorios, sugira novos cenarios de teste:

Gaps identificados:
{gaps}

Mudancas recentes no codigo:
{recent_changes}

Forneca:
1. Top 10 cenarios prioritarios
2. Justificativa para cada cenario
3. Complexidade estimada (Baixa/Media/Alta)
4. Tipo de teste recomendado (API, E2E, Security, etc)"""

        return self.chat(prompt)

    def _cmd_discover(self, args: List[str]) -> str:
        """Descobre endpoints e funcionalidades para testar"""
        target = args[0] if args else "api"

        console.print(f"[cyan]Descobrindo:[/cyan] {target}")

        discoveries = self.knowledge.discover_testables(target)

        prompt = f"""Analise as funcionalidades descobertas e sugira estrategia de testes:

Descobertas:
{discoveries}

Para cada item, indique:
1. Tipo de teste mais apropriado
2. Cenarios principais a cobrir
3. Dados de teste necessarios
4. Riscos se nao testado"""

        return self.chat(prompt)

    def _cmd_set_env(self, args: List[str]) -> str:
        """Define ambiente ativo"""
        if not args:
            return f"Ambiente atual: {self.current_env.value}\nUso: env <uat|prod>"

        env_name = args[0].lower()
        if env_name in ["uat", "homologacao"]:
            self.current_env = Environment.UAT
        elif env_name in ["prod", "production", "producao"]:
            self.current_env = Environment.PRODUCTION
        else:
            return f"Ambiente invalido: {env_name}. Use 'uat' ou 'prod'."

        return f"Ambiente alterado para: {self.current_env.value}"

    def _cmd_help(self) -> str:
        """Exibe ajuda"""
        return """
# QA Agent - Comandos Disponiveis

| Comando | Descricao | Exemplo |
|---------|-----------|---------|
| `analisar <path>` | Analisa codigo e sugere testes | `analisar security_tests/` |
| `criar <feature>` | Cria casos de teste | `criar validacao_cpf --env uat` |
| `executar <suite>` | Executa testes | `executar smoke --env prod` |
| `relatorio [periodo]` | Gera relatorio | `relatorio today` |
| `cobertura` | Analisa cobertura atual | `cobertura` |
| `sugerir` | Sugere novos cenarios | `sugerir` |
| `descobrir [tipo]` | Descobre funcionalidades | `descobrir api` |
| `env <uat or prod>` | Define ambiente | `env uat` |
| `help` | Mostra esta ajuda | `help` |
| `sair` | Encerra o agente | `sair` |

Voce tambem pode conversar naturalmente comigo sobre qualquer topico de QA!
"""

    def run_interactive(self):
        """Executa o agente em modo interativo"""
        self.initialize()

        console.print("\n[bold green]QA Agent pronto![/bold green]")
        console.print("Digite um comando ou converse comigo. Use 'help' para ver comandos.\n")

        while True:
            try:
                user_input = console.input("[bold cyan]QA>[/bold cyan] ").strip()

                if not user_input:
                    continue

                if user_input.lower() in ["sair", "exit", "quit"]:
                    console.print("[yellow]Ate logo![/yellow]")
                    break

                # Verificar se e um comando
                parts = user_input.split()
                command = parts[0].lower()
                args = parts[1:] if len(parts) > 1 else []

                if command in [c.value for c in AgentCommand]:
                    response = self.execute_command(command, args)
                else:
                    response = self.chat(user_input)

                # Exibir resposta
                console.print(Markdown(response))
                console.print()

            except KeyboardInterrupt:
                console.print("\n[yellow]Interrompido. Digite 'sair' para encerrar.[/yellow]")
            except Exception as e:
                console.print(f"[red]Erro: {e}[/red]")


def main():
    """Ponto de entrada principal"""
    from dotenv import load_dotenv
    load_dotenv()

    agent = QAAgent()
    agent.run_interactive()


if __name__ == "__main__":
    main()
