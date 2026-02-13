"""
QA Agent - Banco de Dados de Teste (CPF/CNPJ)
==============================================

Integra o banco SQLite de CPF/CNPJ de demonstracao para uso nos testes.

Tabelas:
- individuos: CPFs ficticios com nome, status de validacao, restricoes
- empresas: CNPJs ficticios com dados completos (endereco, cidade, estado, CEP, etc.)
- sintegra: Dados SINTEGRA por UF ficticios
"""

import sqlite3
import json
import os
import random
from pathlib import Path
from typing import Dict, Any, List, Optional

# Caminho do banco de dados de teste
# Por padrao usa o banco de demonstracao com dados ficticios
# Pode ser configurado via variavel de ambiente TEST_DATA_DB_PATH
TEST_DATA_DB_PATH = Path(os.getenv(
    "TEST_DATA_DB_PATH",
    str(Path(__file__).parent.parent / "data" / "sample_test_data.db")
))


def _get_connection():
    """Retorna conexao com o banco de dados de teste"""
    if not TEST_DATA_DB_PATH.exists():
        raise FileNotFoundError(f"Banco de dados nao encontrado: {TEST_DATA_DB_PATH}")
    conn = sqlite3.connect(str(TEST_DATA_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def query_test_data(table: str, filters: Dict[str, str] = None, limit: int = 10,
                    random_order: bool = False, columns: List[str] = None) -> Dict[str, Any]:
    """
    Consulta dados de teste do banco de CPF/CNPJ.

    Args:
        table: Tabela a consultar ("individuos", "empresas", "sintegra")
        filters: Filtros opcionais (ex: {"estado": "SP", "status_validacao": "VALIDADO"})
        limit: Numero maximo de registros (padrao 10)
        random_order: Se True, retorna registros aleatorios
        columns: Colunas especificas para retornar. Se None, retorna todas.

    Returns:
        Dict com registros encontrados
    """
    try:
        valid_tables = ["individuos", "empresas", "sintegra"]
        if table not in valid_tables:
            return {
                "success": False,
                "error": f"Tabela invalida: {table}. Use: {', '.join(valid_tables)}"
            }

        conn = _get_connection()
        cursor = conn.cursor()

        # Montar SELECT
        if columns:
            cols = ", ".join(columns)
        else:
            cols = "*"

        query = f"SELECT {cols} FROM {table}"
        params = []

        # Aplicar filtros
        if filters:
            conditions = []
            for key, value in filters.items():
                if value is None:
                    conditions.append(f"{key} IS NULL")
                elif value.startswith("%") or value.endswith("%"):
                    conditions.append(f"{key} LIKE ?")
                    params.append(value)
                else:
                    conditions.append(f"{key} = ?")
                    params.append(value)
            if conditions:
                query += " WHERE " + " AND ".join(conditions)

        # Ordenacao
        if random_order:
            query += " ORDER BY RANDOM()"

        query += f" LIMIT {min(limit, 50)}"

        cursor.execute(query, params)
        rows = cursor.fetchall()

        # Converter para lista de dicts
        results = []
        for row in rows:
            results.append(dict(row))

        # Contar total sem limite
        count_query = f"SELECT COUNT(*) FROM {table}"
        if filters and params:
            conditions_str = query.split("WHERE")[1].split("ORDER")[0].split("LIMIT")[0] if "WHERE" in query else ""
            if conditions_str:
                count_query += " WHERE " + conditions_str
                cursor.execute(count_query, params)
            else:
                cursor.execute(count_query)
        else:
            cursor.execute(count_query)
        total = cursor.fetchone()[0]

        conn.close()

        return {
            "success": True,
            "table": table,
            "results": results,
            "count": len(results),
            "total_in_table": total,
            "filters_applied": filters or {}
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def get_test_cpfs(count: int = 5, random_order: bool = True,
                  status: str = None) -> Dict[str, Any]:
    """
    Retorna CPFs do banco de dados para uso em testes.

    Args:
        count: Quantidade de CPFs (padrao 5, max 50)
        random_order: Se True, retorna CPFs aleatorios
        status: Filtrar por status de validacao (ex: "VALIDADO", "NOME DIVERGENTE")

    Returns:
        Dict com lista de CPFs e dados associados
    """
    filters = {}
    if status:
        filters["status_validacao"] = status

    result = query_test_data(
        table="individuos",
        filters=filters if filters else None,
        limit=count,
        random_order=random_order,
        columns=["cpf", "nome_original", "nome_validado", "restricao", "status_validacao"]
    )

    if result["success"]:
        # Extrair lista simples de CPFs
        cpf_list = [r["cpf"] for r in result["results"] if r.get("cpf")]
        result["cpf_list"] = cpf_list

    return result


def get_test_cnpjs(count: int = 5, random_order: bool = True,
                   estado: str = None, situacao: str = None) -> Dict[str, Any]:
    """
    Retorna CNPJs do banco de dados para uso em testes.

    Args:
        count: Quantidade de CNPJs (padrao 5, max 50)
        random_order: Se True, retorna CNPJs aleatorios
        estado: Filtrar por estado (ex: "SP", "RJ")
        situacao: Filtrar por situacao cadastral (ex: "ATIVA", "BAIXADA")

    Returns:
        Dict com lista de CNPJs e dados associados
    """
    filters = {}
    if estado:
        filters["estado"] = estado
    if situacao:
        filters["situacao_cadastral"] = situacao

    result = query_test_data(
        table="empresas",
        filters=filters if filters else None,
        limit=count,
        random_order=random_order,
        columns=["cnpj", "nome_original", "nome_validado", "estado", "cidade",
                 "situacao_cadastral", "status_validacao"]
    )

    if result["success"]:
        # Extrair lista simples de CNPJs
        cnpj_list = [r["cnpj"] for r in result["results"] if r.get("cnpj")]
        result["cnpj_list"] = cnpj_list

    return result


def get_test_data_summary() -> Dict[str, Any]:
    """
    Retorna resumo do banco de dados de teste.

    Returns:
        Dict com estatisticas de cada tabela
    """
    try:
        conn = _get_connection()
        cursor = conn.cursor()

        summary = {}

        # Individuos
        cursor.execute("SELECT COUNT(*) FROM individuos")
        total_ind = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM individuos WHERE cpf IS NOT NULL AND cpf != ''")
        with_cpf = cursor.fetchone()[0]
        cursor.execute("SELECT status_validacao, COUNT(*) FROM individuos GROUP BY status_validacao")
        ind_status = {row[0] or "NULL": row[1] for row in cursor.fetchall()}

        summary["individuos"] = {
            "total": total_ind,
            "com_cpf": with_cpf,
            "por_status": ind_status
        }

        # Empresas
        cursor.execute("SELECT COUNT(*) FROM empresas WHERE cnpj IS NOT NULL AND cnpj != ''")
        total_emp = cursor.fetchone()[0]
        cursor.execute("SELECT estado, COUNT(*) FROM empresas WHERE estado IS NOT NULL GROUP BY estado ORDER BY COUNT(*) DESC")
        emp_estado = {row[0]: row[1] for row in cursor.fetchall()}
        cursor.execute("SELECT situacao_cadastral, COUNT(*) FROM empresas WHERE situacao_cadastral IS NOT NULL GROUP BY situacao_cadastral")
        emp_situacao = {row[0]: row[1] for row in cursor.fetchall()}

        summary["empresas"] = {
            "total": total_emp,
            "por_estado": emp_estado,
            "por_situacao": emp_situacao
        }

        # Sintegra
        cursor.execute("SELECT COUNT(*) FROM sintegra")
        total_sint = cursor.fetchone()[0]
        cursor.execute("SELECT uf, COUNT(*) FROM sintegra GROUP BY uf ORDER BY uf")
        sint_uf = {row[0]: row[1] for row in cursor.fetchall()}

        summary["sintegra"] = {
            "total": total_sint,
            "por_uf": sint_uf
        }

        conn.close()

        return {
            "success": True,
            "summary": summary,
            "database_path": str(TEST_DATA_DB_PATH),
            "database_exists": TEST_DATA_DB_PATH.exists()
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# ============================================================================
# DEFINICAO DE FERRAMENTAS PARA O AGENTE
# ============================================================================

TEST_DATA_DB_TOOLS = [
    {
        "name": "get_test_cpfs",
        "description": "Retorna CPFs reais do banco de dados de teste para usar em testes de API. Pode filtrar por status.",
        "input_schema": {
            "type": "object",
            "properties": {
                "count": {"type": "integer", "default": 5, "description": "Quantidade de CPFs"},
                "random_order": {"type": "boolean", "default": True},
                "status": {"type": "string", "description": "Filtrar por status (ex: VALIDADO, NOME DIVERGENTE)"}
            },
            "required": []
        }
    },
    {
        "name": "get_test_cnpjs",
        "description": "Retorna CNPJs reais do banco de dados de teste para usar em testes de API. Pode filtrar por estado e situacao.",
        "input_schema": {
            "type": "object",
            "properties": {
                "count": {"type": "integer", "default": 5, "description": "Quantidade de CNPJs"},
                "random_order": {"type": "boolean", "default": True},
                "estado": {"type": "string", "description": "Filtrar por estado (ex: SP, RJ, MG)"},
                "situacao": {"type": "string", "description": "Filtrar por situacao (ex: ATIVA, BAIXADA)"}
            },
            "required": []
        }
    },
    {
        "name": "query_test_data",
        "description": "Consulta flexivel ao banco de dados de teste (individuos, empresas, sintegra). Use para buscar dados especificos.",
        "input_schema": {
            "type": "object",
            "properties": {
                "table": {"type": "string", "enum": ["individuos", "empresas", "sintegra"], "description": "Tabela a consultar"},
                "filters": {"type": "object", "description": "Filtros (ex: {\"estado\": \"SP\"})"},
                "limit": {"type": "integer", "default": 10},
                "random_order": {"type": "boolean", "default": False}
            },
            "required": ["table"]
        }
    },
    {
        "name": "get_test_data_summary",
        "description": "Mostra resumo do banco de dados de teste: total de CPFs, CNPJs, empresas por estado, etc.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
]


def execute_test_data_tool(tool_name: str, tool_input: Dict[str, Any]) -> str:
    """Executa uma ferramenta de dados de teste"""
    try:
        if tool_name == "get_test_cpfs":
            result = get_test_cpfs(
                count=tool_input.get("count", 5),
                random_order=tool_input.get("random_order", True),
                status=tool_input.get("status")
            )
        elif tool_name == "get_test_cnpjs":
            result = get_test_cnpjs(
                count=tool_input.get("count", 5),
                random_order=tool_input.get("random_order", True),
                estado=tool_input.get("estado"),
                situacao=tool_input.get("situacao")
            )
        elif tool_name == "query_test_data":
            result = query_test_data(
                table=tool_input.get("table", "individuos"),
                filters=tool_input.get("filters"),
                limit=tool_input.get("limit", 10),
                random_order=tool_input.get("random_order", False),
                columns=tool_input.get("columns")
            )
        elif tool_name == "get_test_data_summary":
            result = get_test_data_summary()
        else:
            result = {"error": f"Ferramenta desconhecida: {tool_name}"}

        return json.dumps(result, ensure_ascii=False, indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})
