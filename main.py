#!/usr/bin/env python3
"""
QA Agent - Ponto de Entrada Principal
=====================================

Agente de IA para automacao completa de QA.
Analisa, cria, executa testes e gera relatorios.

Uso:
    python main.py                  # Modo interativo
    python main.py analisar <path>  # Analisar codigo
    python main.py executar smoke   # Executar testes
    python main.py --help           # Ajuda
"""

import sys
import os
from pathlib import Path

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Adicionar diretorio ao path
sys.path.insert(0, str(Path(__file__).parent))

import click
from rich.console import Console
from rich.panel import Panel
from dotenv import load_dotenv

# Carregar variaveis de ambiente
load_dotenv()

from config.settings import AgentConfig, Environment
from core.agent import QAAgent

console = Console()


def print_banner():
    """Exibe banner do QA Agent"""
    banner = r"""
[bold cyan]
   ____    _       _                    _
  / __ \  / \     / \   __ _  ___ _ __ | |_
 | |  | |/ _ \   / _ \ / _` |/ _ \ '_ \| __|
 | |__| / ___ \ / ___ \ (_| |  __/ | | | |_
  \___\_\_/   \_\_/   \_\__, |\___|_| |_|\__|
                         |___/
[/bold cyan]
[dim]Engenheiro de QA Virtual - Powered by Claude AI[/dim]
"""
    console.print(banner)


@click.group(invoke_without_command=True)
@click.pass_context
@click.option('--debug', is_flag=True, help='Modo debug')
@click.option('--env', type=click.Choice(['uat', 'prod']), default='uat', help='Ambiente')
def cli(ctx, debug, env):
    """QA Agent - Assistente de QA com IA"""
    ctx.ensure_object(dict)
    ctx.obj['debug'] = debug
    ctx.obj['env'] = Environment.UAT if env == 'uat' else Environment.PRODUCTION

    if ctx.invoked_subcommand is None:
        # Modo interativo
        print_banner()
        run_interactive(ctx.obj['env'], debug)


@cli.command()
@click.argument('target')
@click.pass_context
def analisar(ctx, target):
    """Analisa codigo e sugere testes"""
    agent = QAAgent()
    agent.current_env = ctx.obj['env']
    result = agent.execute_command("analisar", [target])
    console.print(result)


@cli.command()
@click.argument('feature')
@click.option('--type', 'test_type', type=click.Choice(['api', 'e2e', 'security']), default='api')
@click.pass_context
def criar(ctx, feature, test_type):
    """Cria casos de teste para uma funcionalidade"""
    agent = QAAgent()
    agent.current_env = ctx.obj['env']
    result = agent.execute_command("criar", [feature, "--type", test_type])
    console.print(result)


@cli.command()
@click.argument('suite', default='smoke')
@click.option('--parallel', is_flag=True, help='Executar em paralelo')
@click.pass_context
def executar(ctx, suite, parallel):
    """Executa suite de testes"""
    agent = QAAgent()
    agent.current_env = ctx.obj['env']

    args = [suite, "--env", ctx.obj['env'].value]
    if parallel:
        args.append("--parallel")

    result = agent.execute_command("executar", args)
    console.print(result)


@cli.command()
@click.argument('period', default='today')
@click.option('--format', 'fmt', type=click.Choice(['html', 'md', 'json']), default='html')
@click.pass_context
def relatorio(ctx, period, fmt):
    """Gera relatorio de execucoes"""
    agent = QAAgent()
    result = agent.execute_command("relatorio", [period, "--format", fmt])
    console.print(result)


@cli.command()
@click.pass_context
def cobertura(ctx):
    """Analisa cobertura de testes"""
    agent = QAAgent()
    result = agent.execute_command("cobertura", [])
    console.print(result)


@cli.command()
@click.pass_context
def sugerir(ctx):
    """Sugere novos cenarios de teste"""
    agent = QAAgent()
    agent.current_env = ctx.obj['env']
    result = agent.execute_command("sugerir", [])
    console.print(result)


@cli.command()
@click.argument('target', default='api')
@click.pass_context
def descobrir(ctx, target):
    """Descobre funcionalidades para testar"""
    agent = QAAgent()
    result = agent.execute_command("descobrir", [target])
    console.print(result)


def run_interactive(environment: Environment, debug: bool = False):
    """Executa agente em modo interativo"""
    # Verificar API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        console.print(Panel(
            "[red]ANTHROPIC_API_KEY nao configurada![/red]\n\n"
            "Configure a variavel de ambiente:\n"
            "  [cyan]set ANTHROPIC_API_KEY=sua-chave-aqui[/cyan]  (Windows)\n"
            "  [cyan]export ANTHROPIC_API_KEY=sua-chave-aqui[/cyan]  (Linux/Mac)",
            title="Erro de Configuracao"
        ))
        sys.exit(1)

    config = AgentConfig()
    config.debug = debug

    agent = QAAgent(config)
    agent.current_env = environment
    agent.run_interactive()


if __name__ == "__main__":
    cli()
