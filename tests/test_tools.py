"""
Testes para as ferramentas core do QA Agent
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()


class TestReadFile:
    def test_read_existing_file(self):
        from core.tools import read_file
        result = read_file(__file__)
        assert result["success"] is True
        assert "content" in result
        assert "test_read_existing_file" in result["content"]

    def test_read_nonexistent_file(self):
        from core.tools import read_file
        result = read_file("/nonexistent/file.py")
        assert result["success"] is False
        assert "error" in result


class TestWriteFile:
    def test_write_and_read(self, tmp_path):
        from core.tools import write_file, read_file
        test_file = tmp_path / "test_output.txt"
        content = "Hello, QA Agent!"
        result = write_file(str(test_file), content)
        assert result["success"] is True
        read_result = read_file(str(test_file))
        assert read_result["content"] == content


class TestListDirectory:
    def test_list_root(self):
        from core.tools import list_directory
        root = Path(__file__).parent.parent
        result = list_directory(str(root))
        assert result["success"] is True
        assert "files" in result
        assert len(result["files"]) > 0

    def test_list_nonexistent(self):
        from core.tools import list_directory
        result = list_directory("/nonexistent/path")
        assert result["success"] is False


class TestSearchInFiles:
    def test_search_existing_pattern(self):
        from core.tools import search_in_files
        test_dir = Path(__file__).parent
        result = search_in_files("def test_", directory=str(test_dir), file_pattern="*.py")
        assert result["success"] is True
        assert len(result["results"]) > 0

    def test_search_nonexistent_pattern(self):
        from core.tools import search_in_files
        result = search_in_files("XYZZZ_NOT_FOUND_12345")
        assert result["success"] is True
        assert len(result["results"]) == 0


class TestExecuteCommand:
    def test_echo(self):
        from core.tools import execute_command
        result = execute_command("echo Hello")
        assert result["success"] is True

    def test_failing_command(self):
        from core.tools import execute_command
        result = execute_command("nonexistent_command_xyz123")
        assert result["success"] is False


class TestEnvironment:
    def test_set_valid_environment(self):
        from core.tools import set_environment
        result = set_environment("Desenvolvimento")
        assert result["success"] is True
        assert result["environment"] == "Desenvolvimento"

    def test_set_invalid_environment(self):
        from core.tools import set_environment
        result = set_environment("AmbienteInexistente")
        assert result["success"] is False

    def test_get_current_environment(self):
        from core.tools import get_current_environment, set_environment
        set_environment("Desenvolvimento")
        result = get_current_environment()
        assert result["name"] == "Desenvolvimento"
        assert "api_base_url" in result


class TestKnownEndpoints:
    def test_list_endpoints(self):
        from core.tools import list_api_endpoints
        result = list_api_endpoints()
        assert result["success"] is True
        assert len(result["endpoints"]) > 0

    def test_list_endpoints_by_category(self):
        from core.tools import list_api_endpoints
        result = list_api_endpoints(category="posts")
        assert result["success"] is True


class TestMemory:
    def test_save_and_search_learning(self):
        from core.memory import init_database, add_learning, search_learnings
        init_database()
        add_learning("test", "Test Learning", "This is a test learning entry")
        result = search_learnings("test learning")
        assert result["success"] is True
        key = "learnings" if "learnings" in result else "results"
        items = result.get(key, [])
        assert len(items) > 0
        found = any("test learning" in r.get("content", "").lower() for r in items)
        assert found


class TestQATools:
    def test_create_and_list_bugs(self):
        from core.qa_tools import init_qa_database, create_bug, list_bugs
        init_qa_database()
        result = create_bug(title="Test Bug", description="Test description", severity="low")
        assert result["success"] is True
        bugs = list_bugs()
        assert bugs["success"] is True

    def test_create_and_list_features(self):
        from core.qa_tools import init_qa_database, create_feature, list_features
        init_qa_database()
        result = create_feature(title="Test Feature", description="Test feature description")
        assert result["success"] is True
        features = list_features()
        assert features["success"] is True

    def test_create_test_case(self):
        from core.qa_tools import init_qa_database, create_test_case
        init_qa_database()
        result = create_test_case(
            title="Test Case",
            description="A test case",
            steps="Step 1\nStep 2",
            expected_results="Expected result"
        )
        assert result["success"] is True


class TestProviders:
    def test_provider_registry(self):
        from core.providers import PROVIDER_REGISTRY
        assert "anthropic" in PROVIDER_REGISTRY
        assert "openai" in PROVIDER_REGISTRY
        assert "gemini" in PROVIDER_REGISTRY

    def test_provider_models(self):
        from core.providers import PROVIDER_MODELS
        assert "anthropic" in PROVIDER_MODELS
        assert "openai" in PROVIDER_MODELS
        assert "gemini" in PROVIDER_MODELS

    def test_check_provider_key(self):
        from core.providers import check_provider_key
        result = check_provider_key("anthropic")
        assert isinstance(result, bool)
