import pytest
from src.database import DatabaseManager


@pytest.fixture
def temp_db(tmp_path):
    path = str(tmp_path / "test.db")
    return DatabaseManager(path)


def test_tables_and_indexes_created(temp_db):
    with temp_db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = {row["name"] for row in cursor.fetchall()}
        assert "DEVELOPER" in tables
        assert "MISTAKE_LOG" in tables
        assert "PR_REVIEW_HISTORY" in tables
        assert "API_DECISION_LOG" in tables

        cursor.execute("SELECT name FROM sqlite_master WHERE type='index';")
        indexes = {row["name"] for row in cursor.fetchall()}
        assert "idx_developer_username" in indexes
        assert "idx_mistake_tag" in indexes
        assert "idx_pr_history" in indexes


def test_seed_default_data(temp_db):
    temp_db.seed_default_data()
    mistakes = temp_db.get_developer_mistakes("SeshanthSathish")
    assert len(mistakes) == 6
    categories = {m["tag_category"] for m in mistakes}
    assert "SECURITY" in categories
    assert "RESOURCE_LEAK" in categories
    assert "BOUNDARY_CHECK" in categories
    assert "SQL_INJECTION" in categories


def test_foreign_key_cascade(temp_db):
    with temp_db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO DEVELOPER (username, email) VALUES ('alice', 'alice@test.com')")
        dev_id = cur.lastrowid
        cur.execute("INSERT INTO MISTAKE_LOG (developer_id, tag_category, description) VALUES (?, 'SECURITY', 'Leaked token')", (dev_id,))
        conn.commit()

        cur.execute("DELETE FROM DEVELOPER WHERE developer_id = ?", (dev_id,))
        conn.commit()

        cur.execute("SELECT * FROM MISTAKE_LOG WHERE developer_id = ?", (dev_id,))
        assert cur.fetchall() == []


def test_log_review_action(temp_db):
    temp_db.log_review_action(
        pr_number=42,
        file_path="src/main.py",
        line_number=10,
        status_flag="FLAGGED",
        mistake_id=None
    )
    with temp_db.get_connection() as conn:
        cur = conn.cursor()
        cursor = cur.execute("SELECT * FROM PR_REVIEW_HISTORY WHERE pr_number = 42")
        rows = cursor.fetchall()
        assert len(rows) == 1
        assert rows[0]["file_path"] == "src/main.py"
        assert rows[0]["line_number"] == 10
        assert rows[0]["status_flag"] == "FLAGGED"


def test_log_api_decision(temp_db):
    temp_db.log_api_decision(
        endpoint="https://api.gemini.com/generate",
        status_code=200,
        message="OK",
        retries=0
    )
    with temp_db.get_connection() as conn:
        cur = conn.cursor()
        cursor = cur.execute("SELECT * FROM API_DECISION_LOG WHERE response_code = 200")
        rows = cursor.fetchall()
        assert len(rows) == 1
        assert rows[0]["endpoint_url"] == "https://api.gemini.com/generate"
        assert rows[0]["status_message"] == "OK"
