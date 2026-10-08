import os
import sys
import pytest
from unittest.mock import patch
from io import StringIO
from src.cli import main
from src.database import DatabaseManager


@pytest.fixture
def temp_db_path(tmp_path):
    return str(tmp_path / "cli_test.db")


def test_cli_add_dev_and_mistake(temp_db_path):
    # Test add-dev
    with patch("sys.argv", ["cli.py", "--db", temp_db_path, "add-dev", "--username", "testuser", "--email", "test@example.com"]):
        main()

    db = DatabaseManager(temp_db_path)
    with db.get_connection() as conn:
        dev = conn.cursor().execute("SELECT * FROM DEVELOPER WHERE username = 'testuser'").fetchone()
        assert dev is not None
        assert dev["email"] == "test@example.com"

    # Test add-mistake
    with patch("sys.argv", ["cli.py", "--db", temp_db_path, "add-mistake", "--username", "testuser", "--category", "SECURITY", "--description", "Hardcoded API key"]):
        main()

    mistakes = db.get_developer_mistakes("testuser")
    assert len(mistakes) == 1
    assert mistakes[0]["tag_category"] == "SECURITY"
    assert mistakes[0]["description"] == "Hardcoded API key"

    # Test list
    with patch("sys.argv", ["cli.py", "--db", temp_db_path, "list", "--username", "testuser"]):
        with patch("sys.stdout", new_callable=StringIO) as mock_out:
            main()
            output = mock_out.getvalue()
            assert "SECURITY" in output
            assert "Hardcoded API key" in output


def test_cli_seed(temp_db_path):
    with patch("sys.argv", ["cli.py", "--db", temp_db_path, "seed"]):
        main()

    db = DatabaseManager(temp_db_path)
    mistakes = db.get_developer_mistakes("SeshanthSathish")
    assert len(mistakes) == 4
