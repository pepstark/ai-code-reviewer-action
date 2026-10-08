import os
import json
import pytest
from unittest.mock import MagicMock
from src.database import DatabaseManager
from src.llm_engine import LLMReviewEngine


@pytest.fixture
def temp_db(tmp_path):
    path = str(tmp_path / "llm_test.db")
    return DatabaseManager(path)


def test_assemble_prompt(temp_db):
    engine = LLMReviewEngine(api_key=None, db_manager=temp_db)
    diff_chunks = [{"file_path": "app.py", "line_number": 5, "content": "password = '123'"}]
    mistakes = [{"mistake_id": 1, "tag_category": "SECURITY", "description": "Avoid plaintext credentials"}]

    prompt = engine.assemble_prompt(diff_chunks, mistakes)
    assert "Avoid plaintext credentials" in prompt
    assert "SECURITY" in prompt
    assert "app.py" in prompt
    assert "password = '123'" in prompt


def test_evaluate_code_empty_diff(temp_db):
    engine = LLMReviewEngine(api_key="fake-key", db_manager=temp_db)
    res = engine.evaluate_code([], [])
    assert res == []


def test_evaluate_code_missing_api_key(temp_db):
    engine = LLMReviewEngine(api_key=None, db_manager=temp_db)
    diff = [{"file_path": "a.py", "line_number": 1, "content": "x = 1"}]
    res = engine.evaluate_code(diff, [])
    assert res == []

    # Check API decision log recorded the missing key
    with temp_db.get_connection() as conn:
        log = conn.cursor().execute("SELECT * FROM API_DECISION_LOG WHERE response_code = 401").fetchone()
        assert log is not None


def test_evaluate_code_mock_success(temp_db):
    engine = LLMReviewEngine(api_key="test-key", db_manager=temp_db)
    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps([
        {
            "file_path": "app.py",
            "line_number": 11,
            "tag_category": "SECURITY",
            "critique": "Do not hardcode secrets.",
            "mistake_id": 1
        }
    ])
    mock_model.generate_content.return_value = mock_response
    engine.model = mock_model

    diff = [{"file_path": "app.py", "line_number": 11, "content": "API_KEY = 'secret'"}]
    mistakes = [{"mistake_id": 1, "tag_category": "SECURITY", "description": "Hardcoding secrets"}]

    reviews = engine.evaluate_code(diff, mistakes)
    assert len(reviews) == 1
    assert reviews[0]["file_path"] == "app.py"
    assert reviews[0]["line_number"] == 11
    assert reviews[0]["tag_category"] == "SECURITY"

    # Check API decision log
    with temp_db.get_connection() as conn:
        log = conn.cursor().execute("SELECT * FROM API_DECISION_LOG WHERE response_code = 200").fetchone()
        assert log is not None


def test_evaluate_code_exception_fallback(temp_db):
    engine = LLMReviewEngine(api_key="test-key", db_manager=temp_db)
    mock_model = MagicMock()
    mock_model.generate_content.side_effect = RuntimeError("Rate limit exceeded")
    engine.model = mock_model

    diff = [{"file_path": "app.py", "line_number": 11, "content": "API_KEY = 'secret'"}]
    reviews = engine.evaluate_code(diff, [])
    # Returns empty array safely without raising exception
    assert reviews == []

    # Check fallback logged to database
    with temp_db.get_connection() as conn:
        log = conn.cursor().execute("SELECT * FROM API_DECISION_LOG WHERE response_code = 500").fetchone()
        assert log is not None
        assert "Rate limit exceeded" in log["status_message"]
