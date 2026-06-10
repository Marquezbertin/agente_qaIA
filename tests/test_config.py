"""
Testes para configuracao do QA Agent
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()


class TestSettings:
    def test_agent_config_creation(self):
        from config.settings import AgentConfig
        config = AgentConfig()
        assert config is not None
        assert config.model is not None

    def test_environment_enum(self):
        from config.settings import Environment
        assert Environment.UAT.value == "uat"
        assert Environment.PRODUCTION.value == "production"

    def test_environment_config(self):
        from config.settings import EnvironmentConfig
        cfg = EnvironmentConfig(
            name="test",
            api_base_url="https://api.test.com",
            api_token="token123",
            web_base_url="https://web.test.com",
            backend_url="https://backend.test.com",
        )
        assert cfg.name == "test"
        assert cfg.api_base_url == "https://api.test.com"
        assert cfg.timeout == 60

    def test_knowledge_repos(self):
        from config.settings import KNOWLEDGE_REPOS
        assert "projeto-testes" in KNOWLEDGE_REPOS

    def test_pytest_markers(self):
        from config.settings import PYTEST_MARKERS
        assert "smoke" in PYTEST_MARKERS
        assert "security" in PYTEST_MARKERS
        assert "regression" in PYTEST_MARKERS

    def test_test_types(self):
        from config.settings import TEST_TYPES
        assert "api" in TEST_TYPES
        assert "e2e" in TEST_TYPES
        assert "security" in TEST_TYPES


class TestGitTools:
    def test_git_tools_definition(self):
        from core.github_tools import GIT_TOOLS_DEFINITION
        assert len(GIT_TOOLS_DEFINITION) > 0
        tool_names = [t["name"] for t in GIT_TOOLS_DEFINITION]
        assert "list_issues" in tool_names
        assert "create_issue" in tool_names
        assert "list_pull_requests" in tool_names
        assert "create_pull_request" in tool_names

    def test_git_tool_definition_structure(self):
        from core.github_tools import GIT_TOOLS_DEFINITION
        for tool in GIT_TOOLS_DEFINITION:
            assert "name" in tool
            assert "description" in tool
            assert "input_schema" in tool


class TestMemoryConfig:
    def test_memory_tools_definition(self):
        from core.memory import MEMORY_TOOLS
        assert len(MEMORY_TOOLS) > 0
        tool_names = [t.get("name") for t in MEMORY_TOOLS]
        assert "save_learning" in tool_names

    def test_qa_tools_definition(self):
        from core.qa_tools import QA_TOOLS_DEFINITION
        assert len(QA_TOOLS_DEFINITION) > 0
        tool_names = [t["name"] for t in QA_TOOLS_DEFINITION]
        assert "create_bug" in tool_names
        assert "create_test_case" in tool_names
        assert "create_test_plan" in tool_names


class TestDataDB:
    def test_test_data_tools_definition(self):
        from core.test_data_db import TEST_DATA_DB_TOOLS
        assert len(TEST_DATA_DB_TOOLS) > 0
        tool_names = [t["name"] for t in TEST_DATA_DB_TOOLS]
        assert "get_test_cpfs" in tool_names
        assert "query_test_data" in tool_names
