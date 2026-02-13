"""
QA Agent Memory - Memoria Persistente com SQLite
================================================

Sistema de memoria que permite ao agente:
- Armazenar aprendizados do usuario
- Lembrar contexto de conversas anteriores
- Guardar padroes de teste descobertos
- Salvar configuracoes e preferencias
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

# Caminho do banco de dados
DB_PATH = Path(__file__).parent.parent / "data" / "qa_agent_memory.db"


def init_database():
    """Inicializa o banco de dados com as tabelas necessarias"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # Tabela de aprendizados
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS learnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            tags TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Tabela de conversas (historico)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            tool_used TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Tabela de padroes de teste
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS test_patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            template TEXT NOT NULL,
            category TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Tabela de configuracoes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Tabela de resultados de testes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS test_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_path TEXT NOT NULL,
            passed INTEGER DEFAULT 0,
            failed INTEGER DEFAULT 0,
            skipped INTEGER DEFAULT 0,
            duration REAL,
            output TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Indices para busca rapida
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_learnings_category ON learnings(category)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_learnings_tags ON learnings(tags)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(session_id)")

    conn.commit()
    conn.close()


def add_learning(category: str, title: str, content: str, tags: List[str] = None) -> Dict[str, Any]:
    """
    Adiciona um novo aprendizado ao banco.

    Args:
        category: Categoria (ex: "api", "security", "best_practice", "bug_fix")
        title: Titulo do aprendizado
        content: Conteudo detalhado
        tags: Lista de tags para busca

    Returns:
        Dict com resultado da operacao
    """
    try:
        init_database()
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        tags_str = ",".join(tags) if tags else ""

        cursor.execute("""
            INSERT INTO learnings (category, title, content, tags)
            VALUES (?, ?, ?, ?)
        """, (category, title, content, tags_str))

        learning_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return {
            "success": True,
            "id": learning_id,
            "message": f"Aprendizado '{title}' salvo com sucesso!"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def search_learnings(query: str = "", category: str = "", limit: int = 10) -> Dict[str, Any]:
    """
    Busca aprendizados no banco.

    Args:
        query: Texto para buscar no titulo ou conteudo
        category: Filtrar por categoria
        limit: Limite de resultados

    Returns:
        Dict com lista de aprendizados
    """
    try:
        init_database()
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        sql = "SELECT id, category, title, content, tags, created_at FROM learnings WHERE 1=1"
        params = []

        if query:
            sql += " AND (title LIKE ? OR content LIKE ? OR tags LIKE ?)"
            search_term = f"%{query}%"
            params.extend([search_term, search_term, search_term])

        if category:
            sql += " AND category = ?"
            params.append(category)

        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()

        learnings = []
        for row in rows:
            learnings.append({
                "id": row[0],
                "category": row[1],
                "title": row[2],
                "content": row[3],
                "tags": row[4].split(",") if row[4] else [],
                "created_at": row[5]
            })

        return {
            "success": True,
            "learnings": learnings,
            "total": len(learnings)
        }
    except Exception as e:
        return {"success": False, "learnings": [], "error": str(e)}


def get_all_learnings() -> Dict[str, Any]:
    """Retorna todos os aprendizados"""
    return search_learnings(limit=100)


def delete_learning(learning_id: int) -> Dict[str, Any]:
    """Remove um aprendizado"""
    try:
        init_database()
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        cursor.execute("DELETE FROM learnings WHERE id = ?", (learning_id,))
        deleted = cursor.rowcount

        conn.commit()
        conn.close()

        if deleted:
            return {"success": True, "message": f"Aprendizado {learning_id} removido"}
        else:
            return {"success": False, "error": "Aprendizado nao encontrado"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def save_conversation(session_id: str, role: str, content: str, tool_used: str = None) -> bool:
    """Salva uma mensagem da conversa"""
    try:
        init_database()
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO conversations (session_id, role, content, tool_used)
            VALUES (?, ?, ?, ?)
        """, (session_id, role, content[:5000], tool_used))

        conn.commit()
        conn.close()
        return True
    except:
        return False


def get_conversation_history(session_id: str, limit: int = 20) -> List[Dict]:
    """Recupera historico de conversa"""
    try:
        init_database()
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT role, content, tool_used, created_at
            FROM conversations
            WHERE session_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (session_id, limit))

        rows = cursor.fetchall()
        conn.close()

        return [{
            "role": row[0],
            "content": row[1],
            "tool_used": row[2],
            "created_at": row[3]
        } for row in reversed(rows)]
    except:
        return []


def save_test_pattern(name: str, description: str, template: str, category: str = "general") -> Dict[str, Any]:
    """Salva um padrao de teste reutilizavel"""
    try:
        init_database()
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO test_patterns (name, description, template, category)
            VALUES (?, ?, ?, ?)
        """, (name, description, template, category))

        conn.commit()
        conn.close()

        return {"success": True, "message": f"Padrao '{name}' salvo!"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_test_patterns(category: str = "") -> Dict[str, Any]:
    """Recupera padroes de teste"""
    try:
        init_database()
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        if category:
            cursor.execute("""
                SELECT name, description, template, category FROM test_patterns WHERE category = ?
            """, (category,))
        else:
            cursor.execute("SELECT name, description, template, category FROM test_patterns")

        rows = cursor.fetchall()
        conn.close()

        return {
            "success": True,
            "patterns": [{
                "name": row[0],
                "description": row[1],
                "template": row[2],
                "category": row[3]
            } for row in rows]
        }
    except Exception as e:
        return {"success": False, "patterns": [], "error": str(e)}


def save_test_result(test_path: str, passed: int, failed: int, skipped: int, duration: float, output: str) -> bool:
    """Salva resultado de execucao de teste"""
    try:
        init_database()
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO test_results (test_path, passed, failed, skipped, duration, output)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (test_path, passed, failed, skipped, duration, output[:10000]))

        conn.commit()
        conn.close()
        return True
    except:
        return False


def get_test_history(test_path: str = "", limit: int = 10) -> Dict[str, Any]:
    """Recupera historico de execucoes de teste"""
    try:
        init_database()
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        if test_path:
            cursor.execute("""
                SELECT test_path, passed, failed, skipped, duration, created_at
                FROM test_results
                WHERE test_path LIKE ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (f"%{test_path}%", limit))
        else:
            cursor.execute("""
                SELECT test_path, passed, failed, skipped, duration, created_at
                FROM test_results
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))

        rows = cursor.fetchall()
        conn.close()

        return {
            "success": True,
            "results": [{
                "test_path": row[0],
                "passed": row[1],
                "failed": row[2],
                "skipped": row[3],
                "duration": row[4],
                "created_at": row[5]
            } for row in rows]
        }
    except Exception as e:
        return {"success": False, "results": [], "error": str(e)}


def set_setting(key: str, value: Any) -> bool:
    """Salva uma configuracao"""
    try:
        init_database()
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        value_str = json.dumps(value) if not isinstance(value, str) else value

        cursor.execute("""
            INSERT OR REPLACE INTO settings (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (key, value_str))

        conn.commit()
        conn.close()
        return True
    except:
        return False


def get_setting(key: str, default: Any = None) -> Any:
    """Recupera uma configuracao"""
    try:
        init_database()
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()

        if row:
            try:
                return json.loads(row[0])
            except:
                return row[0]
        return default
    except:
        return default


def get_context_for_agent() -> str:
    """
    Gera contexto dos aprendizados para incluir no prompt do agente.
    Expandido para manter mais contexto.
    """
    learnings = search_learnings(limit=15)  # Aumentado para 15

    if not learnings.get("learnings"):
        return "Nenhum aprendizado ainda."

    context = ""
    for l in learnings["learnings"]:
        # Aumentado limite de conteudo por aprendizado
        context += f"[{l['category']}] {l['title']}: {l['content'][:200]}\n"

    return context[:2000]  # Aumentado para 2000 caracteres


# Ferramentas para o agente
MEMORY_TOOLS = [
    {
        "name": "save_learning",
        "description": "Salva um novo aprendizado na memoria do agente. Use quando o usuario ensinar algo novo, compartilhar uma boa pratica, ou quando descobrir algo importante.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Categoria do aprendizado: api, security, best_practice, bug_fix, test_pattern, configuration",
                    "enum": ["api", "security", "best_practice", "bug_fix", "test_pattern", "configuration", "other"]
                },
                "title": {
                    "type": "string",
                    "description": "Titulo curto e descritivo do aprendizado"
                },
                "content": {
                    "type": "string",
                    "description": "Conteudo detalhado do aprendizado"
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags para facilitar busca futura"
                }
            },
            "required": ["category", "title", "content"]
        }
    },
    {
        "name": "search_memory",
        "description": "Busca aprendizados na memoria do agente. Use para recuperar informacoes aprendidas anteriormente.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Texto para buscar nos aprendizados"
                },
                "category": {
                    "type": "string",
                    "description": "Filtrar por categoria especifica"
                }
            },
            "required": []
        }
    },
    {
        "name": "get_test_history",
        "description": "Recupera historico de execucoes de testes anteriores.",
        "input_schema": {
            "type": "object",
            "properties": {
                "test_path": {
                    "type": "string",
                    "description": "Filtrar por caminho do teste"
                },
                "limit": {
                    "type": "integer",
                    "description": "Limite de resultados",
                    "default": 10
                }
            },
            "required": []
        }
    }
]


def execute_memory_tool(tool_name: str, tool_input: Dict[str, Any]) -> str:
    """Executa uma ferramenta de memoria"""
    if tool_name == "save_learning":
        result = add_learning(
            category=tool_input.get("category", "other"),
            title=tool_input.get("title", ""),
            content=tool_input.get("content", ""),
            tags=tool_input.get("tags", [])
        )
    elif tool_name == "search_memory":
        result = search_learnings(
            query=tool_input.get("query", ""),
            category=tool_input.get("category", "")
        )
    elif tool_name == "get_test_history":
        result = get_test_history(
            test_path=tool_input.get("test_path", ""),
            limit=tool_input.get("limit", 10)
        )
    else:
        result = {"error": f"Ferramenta desconhecida: {tool_name}"}

    return json.dumps(result, ensure_ascii=False, indent=2)


# Inicializar banco ao importar
init_database()
