import os
import pytest
from unittest.mock import patch, MagicMock
from src.database import DatabaseManager
from src.comment_router import GitHubCommentRouter


@pytest.fixture
def temp_db(tmp_path):
    path = str(tmp_path / "router_test.db")
    db = DatabaseManager(path)
    db.seed_default_data()
    return db


def test_comment_router_post_success(temp_db):
    router = GitHubCommentRouter(
        github_token="mock_token",
        repo="octocat/Hello-World",
        pr_number=10,
        commit_sha="abcdef1234567890",
        db_manager=temp_db
    )

    reviews = [
        {
            "file_path": "auth.py",
            "line_number": 15,
            "tag_category": "SECURITY",
            "critique": "Avoid storing passwords in plaintext.",
            "mistake_id": 1
        }
    ]

    mock_response = MagicMock()
    mock_response.status_code = 201

    with patch("requests.post", return_value=mock_response) as mock_post:
        posted = router.post_annotations(reviews)
        assert posted == 1
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args.kwargs
        assert call_kwargs["json"]["commit_id"] == "abcdef1234567890"
        assert call_kwargs["json"]["path"] == "auth.py"
        assert call_kwargs["json"]["line"] == 15
        assert "AI Code Reviewer Warning (`SECURITY`)" in call_kwargs["json"]["body"]

    # Verify written to PR_REVIEW_HISTORY
    with temp_db.get_connection() as conn:
        history = conn.cursor().execute("SELECT * FROM PR_REVIEW_HISTORY WHERE pr_number = 10").fetchone()
        assert history is not None
        assert history["file_path"] == "auth.py"
        assert history["line_number"] == 15
        assert history["status_flag"] == "FLAGGED"
        assert history["mistake_id"] == 1


def test_comment_router_post_failure(temp_db):
    router = GitHubCommentRouter(
        github_token="mock_token",
        repo="octocat/Hello-World",
        pr_number=10,
        commit_sha="abcdef1234567890",
        db_manager=temp_db
    )

    reviews = [
        {
            "file_path": "auth.py",
            "line_number": 15,
            "tag_category": "SECURITY",
            "critique": "Avoid storing passwords in plaintext.",
            "mistake_id": 1
        }
    ]

    mock_response = MagicMock()
    mock_response.status_code = 422
    mock_response.text = "Unprocessable Entity"

    with patch("requests.post", return_value=mock_response):
        posted = router.post_annotations(reviews)
        assert posted == 0

    with temp_db.get_connection() as conn:
        history = conn.cursor().execute("SELECT * FROM PR_REVIEW_HISTORY WHERE pr_number = 10").fetchall()
        assert len(history) == 0
