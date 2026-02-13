"""
QA Tools - Ferramentas Completas de Quality Assurance
=====================================================

Modulo com ferramentas de QA:
- Registro de Bugs
- Registro de Features
- Casos de Teste
- Planos de Teste
- Execucao de Testes
- Relatorios

Autor: QA Agent
Data: 2026-02-05
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from enum import Enum

# Usar o mesmo banco de dados do agente
DB_PATH = Path(__file__).parent.parent / "data" / "qa_agent_memory.db"

# Diretorio para evidencias
EVIDENCE_DIR = Path(__file__).parent.parent / "evidencias"
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)


# ==================== ENUMS ====================

class BugSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class BugStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"
    REOPENED = "reopened"


class FeatureStatus(str, Enum):
    BACKLOG = "backlog"
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    TESTING = "testing"
    DONE = "done"


class TestCaseStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"


class TestExecutionResult(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


class TestPlanStatus(str, Enum):
    DRAFT = "draft"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


# ==================== DATABASE INIT ====================

def init_qa_database():
    """Inicializa tabelas de QA no banco de dados"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # Tabela de Bugs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bugs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            steps_to_reproduce TEXT,
            expected_result TEXT,
            actual_result TEXT,
            severity TEXT DEFAULT 'medium',
            status TEXT DEFAULT 'open',
            environment TEXT,
            browser TEXT,
            assignee TEXT,
            reporter TEXT DEFAULT 'QA Agent',
            tags TEXT,
            evidence_paths TEXT,
            related_feature_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP,
            FOREIGN KEY (related_feature_id) REFERENCES features(id)
        )
    """)

    # Tabela de Features
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS features (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            acceptance_criteria TEXT,
            status TEXT DEFAULT 'backlog',
            priority INTEGER DEFAULT 3,
            requester TEXT,
            assignee TEXT,
            tags TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        )
    """)

    # Tabela de Casos de Teste
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS test_cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            preconditions TEXT,
            steps TEXT,
            expected_results TEXT,
            category TEXT,
            priority TEXT DEFAULT 'medium',
            status TEXT DEFAULT 'active',
            automated BOOLEAN DEFAULT 0,
            automation_script_path TEXT,
            related_bug_id INTEGER,
            related_feature_id INTEGER,
            tags TEXT,
            created_by TEXT DEFAULT 'QA Agent',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (related_bug_id) REFERENCES bugs(id),
            FOREIGN KEY (related_feature_id) REFERENCES features(id)
        )
    """)

    # Tabela de Planos de Teste
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS test_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            objective TEXT,
            scope TEXT,
            environment TEXT,
            status TEXT DEFAULT 'draft',
            start_date TEXT,
            end_date TEXT,
            created_by TEXT DEFAULT 'QA Agent',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Tabela de associacao Plano <-> Casos de Teste
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS test_plan_cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_plan_id INTEGER NOT NULL,
            test_case_id INTEGER NOT NULL,
            execution_order INTEGER DEFAULT 0,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (test_plan_id) REFERENCES test_plans(id),
            FOREIGN KEY (test_case_id) REFERENCES test_cases(id),
            UNIQUE(test_plan_id, test_case_id)
        )
    """)

    # Tabela de Execucoes de Teste
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS test_executions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_plan_id INTEGER,
            test_case_id INTEGER NOT NULL,
            result TEXT NOT NULL,
            executed_by TEXT DEFAULT 'QA Agent',
            execution_time_seconds REAL,
            notes TEXT,
            evidence_paths TEXT,
            environment TEXT,
            build_version TEXT,
            executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (test_plan_id) REFERENCES test_plans(id),
            FOREIGN KEY (test_case_id) REFERENCES test_cases(id)
        )
    """)

    # Indices para performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bugs_status ON bugs(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bugs_severity ON bugs(severity)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_features_status ON features(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_test_cases_status ON test_cases(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_test_executions_result ON test_executions(result)")

    conn.commit()
    conn.close()


# ==================== BUG FUNCTIONS ====================

def create_bug(
    title: str,
    description: str = "",
    steps_to_reproduce: str = "",
    expected_result: str = "",
    actual_result: str = "",
    severity: str = "medium",
    environment: str = "",
    browser: str = "",
    tags: List[str] = None,
    related_feature_id: int = None
) -> Dict[str, Any]:
    """Cria um novo registro de bug"""
    try:
        init_qa_database()
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        tags_str = ",".join(tags) if tags else ""

        cursor.execute("""
            INSERT INTO bugs (title, description, steps_to_reproduce, expected_result,
                            actual_result, severity, environment, browser, tags, related_feature_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (title, description, steps_to_reproduce, expected_result,
              actual_result, severity, environment, browser, tags_str, related_feature_id))

        bug_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return {
            "success": True,
            "bug_id": bug_id,
            "message": f"Bug #{bug_id} criado com sucesso: {title}"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def list_bugs(
    status: str = None,
    severity: str = None,
    limit: int = 20
) -> Dict[str, Any]:
    """Lista bugs com filtros opcionais"""
    try:
        init_qa_database()
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        sql = "SELECT id, title, severity, status, environment, created_at FROM bugs WHERE 1=1"
        params = []

        if status:
            sql += " AND status = ?"
            params.append(status)
        if severity:
            sql += " AND severity = ?"
            params.append(severity)

        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()

        bugs = [{
            "id": row[0],
            "title": row[1],
            "severity": row[2],
            "status": row[3],
            "environment": row[4],
            "created_at": row[5]
        } for row in rows]

        return {
            "success": True,
            "bugs": bugs,
            "total": len(bugs)
        }
    except Exception as e:
        return {"success": False, "bugs": [], "error": str(e)}


def get_bug(bug_id: int) -> Dict[str, Any]:
    """Obtem detalhes completos de um bug"""
    try:
        init_qa_database()
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM bugs WHERE id = ?", (bug_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return {"success": False, "error": f"Bug #{bug_id} nao encontrado"}

        columns = ["id", "title", "description", "steps_to_reproduce", "expected_result",
                   "actual_result", "severity", "status", "environment", "browser",
                   "assignee", "reporter", "tags", "evidence_paths", "related_feature_id",
                   "created_at", "updated_at", "resolved_at"]

        bug = dict(zip(columns, row))
        bug["tags"] = bug["tags"].split(",") if bug["tags"] else []

        return {"success": True, "bug": bug}
    except Exception as e:
        return {"success": False, "error": str(e)}


def update_bug(
    bug_id: int,
    status: str = None,
    severity: str = None,
    assignee: str = None,
    notes: str = None
) -> Dict[str, Any]:
    """Atualiza um bug existente"""
    try:
        init_qa_database()
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        updates = []
        params = []

        if status:
            updates.append("status = ?")
            params.append(status)
            if status in ["resolved", "closed"]:
                updates.append("resolved_at = CURRENT_TIMESTAMP")
        if severity:
            updates.append("severity = ?")
            params.append(severity)
        if assignee:
            updates.append("assignee = ?")
            params.append(assignee)
        if notes:
            updates.append("description = description || ? || ?")
            params.extend(["\n\n--- Nota adicional ---\n", notes])

        if not updates:
            return {"success": False, "error": "Nenhum campo para atualizar"}

        updates.append("updated_at = CURRENT_TIMESTAMP")

        sql = f"UPDATE bugs SET {', '.join(updates)} WHERE id = ?"
        params.append(bug_id)

        cursor.execute(sql, params)
        affected = cursor.rowcount
        conn.commit()
        conn.close()

        if affected == 0:
            return {"success": False, "error": f"Bug #{bug_id} nao encontrado"}

        return {"success": True, "message": f"Bug #{bug_id} atualizado com sucesso"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== FEATURE FUNCTIONS ====================

def create_feature(
    title: str,
    description: str = "",
    acceptance_criteria: str = "",
    priority: int = 3,
    requester: str = "",
    tags: List[str] = None
) -> Dict[str, Any]:
    """Cria uma nova feature/historia de usuario"""
    try:
        init_qa_database()
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        tags_str = ",".join(tags) if tags else ""

        cursor.execute("""
            INSERT INTO features (title, description, acceptance_criteria, priority, requester, tags)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (title, description, acceptance_criteria, priority, requester, tags_str))

        feature_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return {
            "success": True,
            "feature_id": feature_id,
            "message": f"Feature #{feature_id} criada com sucesso: {title}"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def list_features(status: str = None, limit: int = 20) -> Dict[str, Any]:
    """Lista features com filtros opcionais"""
    try:
        init_qa_database()
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        sql = "SELECT id, title, status, priority, created_at FROM features WHERE 1=1"
        params = []

        if status:
            sql += " AND status = ?"
            params.append(status)

        sql += " ORDER BY priority ASC, created_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()

        features = [{
            "id": row[0],
            "title": row[1],
            "status": row[2],
            "priority": row[3],
            "created_at": row[4]
        } for row in rows]

        return {
            "success": True,
            "features": features,
            "total": len(features)
        }
    except Exception as e:
        return {"success": False, "features": [], "error": str(e)}


def update_feature(
    feature_id: int,
    status: str = None,
    priority: int = None,
    assignee: str = None
) -> Dict[str, Any]:
    """Atualiza uma feature existente"""
    try:
        init_qa_database()
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        updates = []
        params = []

        if status:
            updates.append("status = ?")
            params.append(status)
            if status == "done":
                updates.append("completed_at = CURRENT_TIMESTAMP")
        if priority is not None:
            updates.append("priority = ?")
            params.append(priority)
        if assignee:
            updates.append("assignee = ?")
            params.append(assignee)

        if not updates:
            return {"success": False, "error": "Nenhum campo para atualizar"}

        updates.append("updated_at = CURRENT_TIMESTAMP")

        sql = f"UPDATE features SET {', '.join(updates)} WHERE id = ?"
        params.append(feature_id)

        cursor.execute(sql, params)
        affected = cursor.rowcount
        conn.commit()
        conn.close()

        if affected == 0:
            return {"success": False, "error": f"Feature #{feature_id} nao encontrada"}

        return {"success": True, "message": f"Feature #{feature_id} atualizada com sucesso"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== TEST CASE FUNCTIONS ====================

def create_test_case(
    title: str,
    description: str = "",
    preconditions: str = "",
    steps: str = "",
    expected_results: str = "",
    category: str = "",
    priority: str = "medium",
    tags: List[str] = None,
    related_bug_id: int = None,
    related_feature_id: int = None
) -> Dict[str, Any]:
    """Cria um novo caso de teste"""
    try:
        init_qa_database()
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        tags_str = ",".join(tags) if tags else ""

        cursor.execute("""
            INSERT INTO test_cases (title, description, preconditions, steps, expected_results,
                                   category, priority, tags, related_bug_id, related_feature_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (title, description, preconditions, steps, expected_results,
              category, priority, tags_str, related_bug_id, related_feature_id))

        tc_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return {
            "success": True,
            "test_case_id": tc_id,
            "message": f"Caso de Teste #{tc_id} criado com sucesso: {title}"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def list_test_cases(
    category: str = None,
    status: str = None,
    related_feature_id: int = None,
    limit: int = 30
) -> Dict[str, Any]:
    """Lista casos de teste com filtros"""
    try:
        init_qa_database()
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        sql = "SELECT id, title, category, priority, status, automated, created_at FROM test_cases WHERE 1=1"
        params = []

        if category:
            sql += " AND category = ?"
            params.append(category)
        if status:
            sql += " AND status = ?"
            params.append(status)
        if related_feature_id:
            sql += " AND related_feature_id = ?"
            params.append(related_feature_id)

        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()

        test_cases = [{
            "id": row[0],
            "title": row[1],
            "category": row[2],
            "priority": row[3],
            "status": row[4],
            "automated": bool(row[5]),
            "created_at": row[6]
        } for row in rows]

        return {
            "success": True,
            "test_cases": test_cases,
            "total": len(test_cases)
        }
    except Exception as e:
        return {"success": False, "test_cases": [], "error": str(e)}


def get_test_case(test_case_id: int) -> Dict[str, Any]:
    """Obtem detalhes completos de um caso de teste"""
    try:
        init_qa_database()
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM test_cases WHERE id = ?", (test_case_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return {"success": False, "error": f"Caso de Teste #{test_case_id} nao encontrado"}

        columns = ["id", "title", "description", "preconditions", "steps", "expected_results",
                   "category", "priority", "status", "automated", "automation_script_path",
                   "related_bug_id", "related_feature_id", "tags", "created_by", "created_at", "updated_at"]

        tc = dict(zip(columns, row))
        tc["tags"] = tc["tags"].split(",") if tc["tags"] else []
        tc["automated"] = bool(tc["automated"])

        return {"success": True, "test_case": tc}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== TEST PLAN FUNCTIONS ====================

def create_test_plan(
    name: str,
    description: str = "",
    objective: str = "",
    scope: str = "",
    environment: str = "",
    start_date: str = None,
    end_date: str = None
) -> Dict[str, Any]:
    """Cria um novo plano de teste"""
    try:
        init_qa_database()
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO test_plans (name, description, objective, scope, environment, start_date, end_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (name, description, objective, scope, environment, start_date, end_date))

        plan_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return {
            "success": True,
            "test_plan_id": plan_id,
            "message": f"Plano de Teste #{plan_id} criado com sucesso: {name}"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def add_test_case_to_plan(
    test_plan_id: int,
    test_case_id: int,
    execution_order: int = 0
) -> Dict[str, Any]:
    """Adiciona um caso de teste a um plano"""
    try:
        init_qa_database()
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR IGNORE INTO test_plan_cases (test_plan_id, test_case_id, execution_order)
            VALUES (?, ?, ?)
        """, (test_plan_id, test_case_id, execution_order))

        conn.commit()
        conn.close()

        return {
            "success": True,
            "message": f"Caso de Teste #{test_case_id} adicionado ao Plano #{test_plan_id}"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def list_test_plans(status: str = None, limit: int = 20) -> Dict[str, Any]:
    """Lista planos de teste"""
    try:
        init_qa_database()
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        sql = """
            SELECT tp.id, tp.name, tp.status, tp.environment, tp.created_at,
                   COUNT(tpc.test_case_id) as case_count
            FROM test_plans tp
            LEFT JOIN test_plan_cases tpc ON tp.id = tpc.test_plan_id
            WHERE 1=1
        """
        params = []

        if status:
            sql += " AND tp.status = ?"
            params.append(status)

        sql += " GROUP BY tp.id ORDER BY tp.created_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()

        plans = [{
            "id": row[0],
            "name": row[1],
            "status": row[2],
            "environment": row[3],
            "created_at": row[4],
            "test_case_count": row[5]
        } for row in rows]

        return {
            "success": True,
            "test_plans": plans,
            "total": len(plans)
        }
    except Exception as e:
        return {"success": False, "test_plans": [], "error": str(e)}


def get_test_plan(test_plan_id: int) -> Dict[str, Any]:
    """Obtem detalhes completos de um plano de teste incluindo casos"""
    try:
        init_qa_database()
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        # Obter plano
        cursor.execute("SELECT * FROM test_plans WHERE id = ?", (test_plan_id,))
        plan_row = cursor.fetchone()

        if not plan_row:
            conn.close()
            return {"success": False, "error": f"Plano de Teste #{test_plan_id} nao encontrado"}

        columns = ["id", "name", "description", "objective", "scope", "environment",
                   "status", "start_date", "end_date", "created_by", "created_at", "updated_at"]
        plan = dict(zip(columns, plan_row))

        # Obter casos de teste do plano
        cursor.execute("""
            SELECT tc.id, tc.title, tc.priority, tc.status, tpc.execution_order
            FROM test_cases tc
            JOIN test_plan_cases tpc ON tc.id = tpc.test_case_id
            WHERE tpc.test_plan_id = ?
            ORDER BY tpc.execution_order
        """, (test_plan_id,))

        case_rows = cursor.fetchall()
        conn.close()

        plan["test_cases"] = [{
            "id": row[0],
            "title": row[1],
            "priority": row[2],
            "status": row[3],
            "execution_order": row[4]
        } for row in case_rows]

        return {"success": True, "test_plan": plan}
    except Exception as e:
        return {"success": False, "error": str(e)}


def update_test_plan_status(test_plan_id: int, status: str) -> Dict[str, Any]:
    """Atualiza status de um plano de teste"""
    try:
        init_qa_database()
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE test_plans SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?
        """, (status, test_plan_id))

        affected = cursor.rowcount
        conn.commit()
        conn.close()

        if affected == 0:
            return {"success": False, "error": f"Plano #{test_plan_id} nao encontrado"}

        return {"success": True, "message": f"Plano #{test_plan_id} atualizado para '{status}'"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== TEST EXECUTION FUNCTIONS ====================

def record_test_execution(
    test_case_id: int,
    result: str,
    notes: str = "",
    execution_time_seconds: float = None,
    evidence_paths: List[str] = None,
    environment: str = "",
    build_version: str = "",
    test_plan_id: int = None
) -> Dict[str, Any]:
    """Registra a execucao de um caso de teste"""
    try:
        init_qa_database()
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        evidence_str = ",".join(evidence_paths) if evidence_paths else ""

        cursor.execute("""
            INSERT INTO test_executions (test_case_id, result, notes, execution_time_seconds,
                                        evidence_paths, environment, build_version, test_plan_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (test_case_id, result, notes, execution_time_seconds,
              evidence_str, environment, build_version, test_plan_id))

        exec_id = cursor.lastrowid
        conn.commit()
        conn.close()

        result_emoji = {"passed": "✅", "failed": "❌", "skipped": "⏭️", "blocked": "🚫"}.get(result, "❓")

        return {
            "success": True,
            "execution_id": exec_id,
            "message": f"{result_emoji} Execucao #{exec_id} registrada para Caso #{test_case_id}: {result.upper()}"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_execution_history(
    test_case_id: int = None,
    test_plan_id: int = None,
    limit: int = 20
) -> Dict[str, Any]:
    """Obtem historico de execucoes"""
    try:
        init_qa_database()
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        sql = """
            SELECT te.id, te.test_case_id, tc.title, te.result, te.executed_by,
                   te.execution_time_seconds, te.environment, te.executed_at
            FROM test_executions te
            JOIN test_cases tc ON te.test_case_id = tc.id
            WHERE 1=1
        """
        params = []

        if test_case_id:
            sql += " AND te.test_case_id = ?"
            params.append(test_case_id)
        if test_plan_id:
            sql += " AND te.test_plan_id = ?"
            params.append(test_plan_id)

        sql += " ORDER BY te.executed_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()

        executions = [{
            "id": row[0],
            "test_case_id": row[1],
            "test_case_title": row[2],
            "result": row[3],
            "executed_by": row[4],
            "execution_time_seconds": row[5],
            "environment": row[6],
            "executed_at": row[7]
        } for row in rows]

        return {
            "success": True,
            "executions": executions,
            "total": len(executions)
        }
    except Exception as e:
        return {"success": False, "executions": [], "error": str(e)}


# ==================== REPORTS ====================

def generate_test_summary_report(test_plan_id: int = None) -> Dict[str, Any]:
    """Gera relatorio resumido de testes"""
    try:
        init_qa_database()
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        # Estatisticas gerais de bugs
        cursor.execute("""
            SELECT status, COUNT(*) FROM bugs GROUP BY status
        """)
        bug_stats = dict(cursor.fetchall())

        # Estatisticas gerais de casos de teste
        cursor.execute("""
            SELECT status, COUNT(*) FROM test_cases GROUP BY status
        """)
        tc_stats = dict(cursor.fetchall())

        # Estatisticas de execucoes
        sql_exec = "SELECT result, COUNT(*) FROM test_executions"
        params = []
        if test_plan_id:
            sql_exec += " WHERE test_plan_id = ?"
            params.append(test_plan_id)
        sql_exec += " GROUP BY result"

        cursor.execute(sql_exec, params)
        exec_stats = dict(cursor.fetchall())

        conn.close()

        total_exec = sum(exec_stats.values()) if exec_stats else 0
        passed = exec_stats.get("passed", 0)
        pass_rate = (passed / total_exec * 100) if total_exec > 0 else 0

        report = {
            "success": True,
            "report": {
                "generated_at": datetime.now().isoformat(),
                "bugs": {
                    "total": sum(bug_stats.values()),
                    "by_status": bug_stats
                },
                "test_cases": {
                    "total": sum(tc_stats.values()),
                    "by_status": tc_stats
                },
                "executions": {
                    "total": total_exec,
                    "by_result": exec_stats,
                    "pass_rate": f"{pass_rate:.1f}%"
                }
            }
        }

        if test_plan_id:
            report["report"]["test_plan_id"] = test_plan_id

        return report
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== TOOL DEFINITIONS ====================

QA_TOOLS_DEFINITION = [
    # Bug Tools
    {
        "name": "create_bug",
        "description": "Cria um novo registro de bug/defeito. Use quando encontrar um problema no sistema.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Titulo descritivo do bug"},
                "description": {"type": "string", "description": "Descricao detalhada do problema"},
                "steps_to_reproduce": {"type": "string", "description": "Passos para reproduzir o bug"},
                "expected_result": {"type": "string", "description": "Resultado esperado"},
                "actual_result": {"type": "string", "description": "Resultado obtido (incorreto)"},
                "severity": {"type": "string", "enum": ["critical", "high", "medium", "low"], "default": "medium"},
                "environment": {"type": "string", "description": "Ambiente onde ocorreu (UAT, Prod, etc)"},
                "browser": {"type": "string", "description": "Navegador usado"},
                "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags para categorizacao"}
            },
            "required": ["title"]
        }
    },
    {
        "name": "list_bugs",
        "description": "Lista bugs registrados. Pode filtrar por status ou severidade.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["open", "in_progress", "resolved", "closed", "reopened"]},
                "severity": {"type": "string", "enum": ["critical", "high", "medium", "low"]},
                "limit": {"type": "integer", "default": 20}
            }
        }
    },
    {
        "name": "get_bug",
        "description": "Obtem detalhes completos de um bug especifico.",
        "input_schema": {
            "type": "object",
            "properties": {
                "bug_id": {"type": "integer", "description": "ID do bug"}
            },
            "required": ["bug_id"]
        }
    },
    {
        "name": "update_bug",
        "description": "Atualiza status, severidade ou atribui um bug.",
        "input_schema": {
            "type": "object",
            "properties": {
                "bug_id": {"type": "integer", "description": "ID do bug"},
                "status": {"type": "string", "enum": ["open", "in_progress", "resolved", "closed", "reopened"]},
                "severity": {"type": "string", "enum": ["critical", "high", "medium", "low"]},
                "assignee": {"type": "string", "description": "Responsavel pelo bug"},
                "notes": {"type": "string", "description": "Notas adicionais"}
            },
            "required": ["bug_id"]
        }
    },
    # Feature Tools
    {
        "name": "create_feature",
        "description": "Cria uma nova feature/historia de usuario para rastrear requisitos.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Titulo da feature"},
                "description": {"type": "string", "description": "Descricao detalhada"},
                "acceptance_criteria": {"type": "string", "description": "Criterios de aceitacao"},
                "priority": {"type": "integer", "description": "Prioridade (1=alta, 5=baixa)", "default": 3},
                "requester": {"type": "string", "description": "Quem solicitou"},
                "tags": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["title"]
        }
    },
    {
        "name": "list_features",
        "description": "Lista features registradas.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["backlog", "planned", "in_progress", "testing", "done"]},
                "limit": {"type": "integer", "default": 20}
            }
        }
    },
    {
        "name": "update_feature",
        "description": "Atualiza status ou prioridade de uma feature.",
        "input_schema": {
            "type": "object",
            "properties": {
                "feature_id": {"type": "integer"},
                "status": {"type": "string", "enum": ["backlog", "planned", "in_progress", "testing", "done"]},
                "priority": {"type": "integer"},
                "assignee": {"type": "string"}
            },
            "required": ["feature_id"]
        }
    },
    # Test Case Tools
    {
        "name": "create_test_case",
        "description": "Cria um novo caso de teste com passos e resultados esperados.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Titulo do caso de teste"},
                "description": {"type": "string", "description": "Descricao do que sera testado"},
                "preconditions": {"type": "string", "description": "Pre-condicoes necessarias"},
                "steps": {"type": "string", "description": "Passos do teste (um por linha)"},
                "expected_results": {"type": "string", "description": "Resultados esperados"},
                "category": {"type": "string", "description": "Categoria (smoke, regression, security, etc)"},
                "priority": {"type": "string", "enum": ["high", "medium", "low"], "default": "medium"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "related_bug_id": {"type": "integer", "description": "ID do bug relacionado"},
                "related_feature_id": {"type": "integer", "description": "ID da feature relacionada"}
            },
            "required": ["title"]
        }
    },
    {
        "name": "list_test_cases",
        "description": "Lista casos de teste. Pode filtrar por categoria ou feature.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {"type": "string"},
                "status": {"type": "string", "enum": ["draft", "active", "deprecated"]},
                "related_feature_id": {"type": "integer"},
                "limit": {"type": "integer", "default": 30}
            }
        }
    },
    {
        "name": "get_test_case",
        "description": "Obtem detalhes completos de um caso de teste.",
        "input_schema": {
            "type": "object",
            "properties": {
                "test_case_id": {"type": "integer"}
            },
            "required": ["test_case_id"]
        }
    },
    # Test Plan Tools
    {
        "name": "create_test_plan",
        "description": "Cria um novo plano de teste para organizar a execucao.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Nome do plano"},
                "description": {"type": "string"},
                "objective": {"type": "string", "description": "Objetivo do plano"},
                "scope": {"type": "string", "description": "Escopo (o que sera testado)"},
                "environment": {"type": "string", "description": "Ambiente de teste"},
                "start_date": {"type": "string", "description": "Data de inicio (YYYY-MM-DD)"},
                "end_date": {"type": "string", "description": "Data de fim (YYYY-MM-DD)"}
            },
            "required": ["name"]
        }
    },
    {
        "name": "add_test_case_to_plan",
        "description": "Adiciona um caso de teste a um plano de teste.",
        "input_schema": {
            "type": "object",
            "properties": {
                "test_plan_id": {"type": "integer"},
                "test_case_id": {"type": "integer"},
                "execution_order": {"type": "integer", "default": 0}
            },
            "required": ["test_plan_id", "test_case_id"]
        }
    },
    {
        "name": "list_test_plans",
        "description": "Lista planos de teste.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["draft", "ready", "in_progress", "completed"]},
                "limit": {"type": "integer", "default": 20}
            }
        }
    },
    {
        "name": "get_test_plan",
        "description": "Obtem detalhes de um plano de teste incluindo seus casos.",
        "input_schema": {
            "type": "object",
            "properties": {
                "test_plan_id": {"type": "integer"}
            },
            "required": ["test_plan_id"]
        }
    },
    {
        "name": "update_test_plan_status",
        "description": "Atualiza o status de um plano de teste.",
        "input_schema": {
            "type": "object",
            "properties": {
                "test_plan_id": {"type": "integer"},
                "status": {"type": "string", "enum": ["draft", "ready", "in_progress", "completed"]}
            },
            "required": ["test_plan_id", "status"]
        }
    },
    # Execution Tools
    {
        "name": "record_test_execution",
        "description": "Registra o resultado da execucao de um caso de teste.",
        "input_schema": {
            "type": "object",
            "properties": {
                "test_case_id": {"type": "integer"},
                "result": {"type": "string", "enum": ["passed", "failed", "skipped", "blocked"]},
                "notes": {"type": "string", "description": "Observacoes da execucao"},
                "execution_time_seconds": {"type": "number"},
                "evidence_paths": {"type": "array", "items": {"type": "string"}, "description": "Caminhos de screenshots/evidencias"},
                "environment": {"type": "string"},
                "build_version": {"type": "string"},
                "test_plan_id": {"type": "integer", "description": "ID do plano se executando dentro de um plano"}
            },
            "required": ["test_case_id", "result"]
        }
    },
    {
        "name": "get_execution_history",
        "description": "Obtem historico de execucoes de testes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "test_case_id": {"type": "integer"},
                "test_plan_id": {"type": "integer"},
                "limit": {"type": "integer", "default": 20}
            }
        }
    },
    # Report Tools
    {
        "name": "generate_qa_report",
        "description": "Gera relatorio resumido com estatisticas de bugs, casos de teste e execucoes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "test_plan_id": {"type": "integer", "description": "Filtrar por plano especifico (opcional)"}
            }
        }
    }
]


def execute_qa_tool(tool_name: str, tool_input: Dict[str, Any]) -> str:
    """Executa uma ferramenta de QA"""
    try:
        # Bug functions
        if tool_name == "create_bug":
            result = create_bug(**tool_input)
        elif tool_name == "list_bugs":
            result = list_bugs(**tool_input)
        elif tool_name == "get_bug":
            result = get_bug(**tool_input)
        elif tool_name == "update_bug":
            result = update_bug(**tool_input)

        # Feature functions
        elif tool_name == "create_feature":
            result = create_feature(**tool_input)
        elif tool_name == "list_features":
            result = list_features(**tool_input)
        elif tool_name == "update_feature":
            result = update_feature(**tool_input)

        # Test case functions
        elif tool_name == "create_test_case":
            result = create_test_case(**tool_input)
        elif tool_name == "list_test_cases":
            result = list_test_cases(**tool_input)
        elif tool_name == "get_test_case":
            result = get_test_case(**tool_input)

        # Test plan functions
        elif tool_name == "create_test_plan":
            result = create_test_plan(**tool_input)
        elif tool_name == "add_test_case_to_plan":
            result = add_test_case_to_plan(**tool_input)
        elif tool_name == "list_test_plans":
            result = list_test_plans(**tool_input)
        elif tool_name == "get_test_plan":
            result = get_test_plan(**tool_input)
        elif tool_name == "update_test_plan_status":
            result = update_test_plan_status(**tool_input)

        # Execution functions
        elif tool_name == "record_test_execution":
            result = record_test_execution(**tool_input)
        elif tool_name == "get_execution_history":
            result = get_execution_history(**tool_input)

        # Report functions
        elif tool_name == "generate_qa_report":
            result = generate_test_summary_report(**tool_input)

        else:
            result = {"error": f"Ferramenta QA desconhecida: {tool_name}"}

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


# Inicializar banco ao importar
init_qa_database()
