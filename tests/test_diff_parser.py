import pytest
from src.diff_parser import GitDiffParser

SAMPLE_DIFF = """diff --git a/app.py b/app.py
index e69de29..495d469 100644
--- a/app.py
+++ b/app.py
@@ -10,0 +11,3 @@
+API_KEY = "secret_12345"
+def run_query(user_input):
+    query = f"SELECT * FROM users WHERE id = {user_input}"
diff --git a/utils.py b/utils.py
index abcdef..123456 100644
--- a/utils.py
+++ b/utils.py
@@ -5,2 +5,3 @@
 context_line_1
-old_code
+new_code_line_6
+another_new_line_7
 context_line_2
"""


def test_parse_diff_empty():
    assert GitDiffParser.parse_diff("") == []


def test_parse_diff_content_and_lines():
    parsed = GitDiffParser.parse_diff(SAMPLE_DIFF)
    assert len(parsed) == 5

    # Check app.py lines
    app_lines = [p for p in parsed if p["file_path"] == "app.py"]
    assert len(app_lines) == 3
    assert app_lines[0]["line_number"] == 11
    assert app_lines[0]["content"] == 'API_KEY = "secret_12345"'
    assert app_lines[1]["line_number"] == 12
    assert app_lines[2]["line_number"] == 13

    # Check utils.py lines
    utils_lines = [p for p in parsed if p["file_path"] == "utils.py"]
    assert len(utils_lines) == 2
    assert utils_lines[0]["line_number"] == 6
    assert utils_lines[0]["content"] == "new_code_line_6"
    assert utils_lines[1]["line_number"] == 7
    assert utils_lines[1]["content"] == "another_new_line_7"


def test_parse_diff_deleted_file():
    diff_deleted = """diff --git a/old.py b/old.py
deleted file mode 100644
--- a/old.py
+++ /dev/null
@@ -1,3 +0,0 @@
-line1
-line2
"""
    parsed = GitDiffParser.parse_diff(diff_deleted)
    assert parsed == []
