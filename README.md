# AI "Code Reviewer" GitHub Action

A GitHub Action and DevOps intelligence pipeline that reviews incoming Pull Requests against developer-specific historical anti-pattern inventories stored in a 3NF SQLite database. It leverages Google Gemini to detect recurring mistakes and critical bugs, posting inline Markdown annotations directly on pull request lines via the GitHub REST API v3.

---

## 1. System Architecture

```
                                  [ GitHub Repository ]
                                            │
                                            │ (PR Opened / Synchronized)
                                            ▼
                              [ GitHub Actions Runner ]
                                            │
                     ┌──────────────────────┴──────────────────────┐
                     ▼                                             ▼
            [ GitDiffParser ]                             [ Local SQLite DB ]
       (Extracts changed files                       (Tables: DEVELOPER,
        & diff line numbers)                          MISTAKE_LOG, HISTORY)
                     │                                             │
                     └──────────────────────┬──────────────────────┘
                                            ▼
                                  [ LLMReviewEngine ]
                              - Correlates Diff with Past Bugs
                              - Injects System Anti-Patterns
                              - Calls Gemini API (gemini-1.5-flash)
                              - Handles Safe Fallback Loops
                                            │
                                            ▼
                                [ GitHubCommentRouter ]
                              - Formats Markdown Annotations
                              - Calls GitHub Pull Request API
                              - Writes to PR_REVIEW_HISTORY
```

---

## 2. Directory Structure

```
ai-code-reviewer-action/
├── .github/
│   └── workflows/
│       └── review.yml            # Automated CI/CD trigger on PR open/sync
├── action.yml                    # GitHub Action metadata & input definitions
├── Dockerfile                    # Container definition for runner environment
├── requirements.txt              # Python runtime dependencies
├── reviewer.db                   # Pre-seeded 3NF SQLite database
├── src/
│   ├── __init__.py
│   ├── config.py                 # Centralized configuration & environment loader
│   ├── database.py               # 3NF SQLite schema, migrations & query interfaces
│   ├── diff_parser.py            # Git diff extractor & line number mapper
│   ├── llm_engine.py             # Prompt assembler, Gemini client & fallback loops
│   ├── comment_router.py         # GitHub REST API client for inline PR comments
│   ├── main.py                   # Master entrypoint coordinating the pipeline
│   └── cli.py                    # Developer CLI tool to manage anti-patterns locally
├── tests/
│   ├── test_database.py          # Database integrity, schema, and logging tests
│   ├── test_diff_parser.py       # Git diff parser unit tests
│   ├── test_cli.py               # Developer CLI tests
│   ├── test_llm_engine.py        # LLM prompt & fallback resilience tests
│   └── test_comment_router.py    # GitHub inline comment router tests
└── README.md
```

---

## 3. Database Design (3NF Schema)

The embedded SQLite database (`reviewer.db`) enforces relational integrity across 4 core entities:

```sql
-- 1. DEVELOPER (User Profile)
CREATE TABLE IF NOT EXISTS DEVELOPER (
    developer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL
);

-- 2. MISTAKE_LOG (Recurring Anti-Patterns logged per developer)
CREATE TABLE IF NOT EXISTS MISTAKE_LOG (
    mistake_id INTEGER PRIMARY KEY AUTOINCREMENT,
    developer_id INTEGER NOT NULL,
    tag_category TEXT NOT NULL,       -- 'SECURITY', 'RESOURCE_LEAK', 'BOUNDARY_CHECK', 'SQL_INJECTION', 'LOGIC'
    description TEXT NOT NULL,
    date_logged TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (developer_id) REFERENCES DEVELOPER(developer_id) ON DELETE CASCADE
);

-- 3. PR_REVIEW_HISTORY (Violations caught during PR runs)
CREATE TABLE IF NOT EXISTS PR_REVIEW_HISTORY (
    review_id INTEGER PRIMARY KEY AUTOINCREMENT,
    mistake_id INTEGER,
    pr_number INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    line_number INTEGER NOT NULL,
    status_flag TEXT NOT NULL CHECK(status_flag IN ('FLAGGED', 'RESOLVED', 'FALSE_POSITIVE')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (mistake_id) REFERENCES MISTAKE_LOG(mistake_id) ON DELETE SET NULL
);

-- 4. API_DECISION_LOG (Operational audit trail for AI rate-limits & fallback handling)
CREATE TABLE IF NOT EXISTS API_DECISION_LOG (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    endpoint_url TEXT NOT NULL,
    retry_count INTEGER DEFAULT 0,
    response_code INTEGER NOT NULL,
    status_message TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_developer_username ON DEVELOPER(username);
CREATE INDEX IF NOT EXISTS idx_mistake_tag ON MISTAKE_LOG(tag_category);
CREATE INDEX IF NOT EXISTS idx_pr_history ON PR_REVIEW_HISTORY(pr_number);
```

### Pre-Seeded Anti-Patterns for `@SeshanthSathish`
1. `[SECURITY]`: Hardcoding plaintext secrets or API tokens inside source files rather than using environment variables.
2. `[RESOURCE_LEAK]`: Opening file handlers or database connections without using "with" context managers or proper finally-close blocks.
3. `[BOUNDARY_CHECK]`: Writing array loops using <= array.length causing out-of-bounds indexing exceptions.
4. `[SQL_INJECTION]`: Constructing SQL statements using Python f-strings or direct concatenation rather than parameterized queries.

---

## 4. Local CLI Management Utility

Manage developers and historical anti-patterns directly from your terminal:

### Seed Default Database
```bash
python src/cli.py seed
```

### Register Developer
```bash
python src/cli.py add-dev --username "john_doe" --email "john@example.com"
```

### Log an Anti-Pattern
```bash
python src/cli.py add-mistake \
  --username "john_doe" \
  --category "SECURITY" \
  --description "Accidental exposure of AWS secret access keys in scripts"
```

### List Anti-Patterns
```bash
python src/cli.py list --username "SeshanthSathish"
```

---

## 5. GitHub Action CI/CD Setup

### 1. Add Repository Secret
In your repository on GitHub:
- Go to **Settings** $\rightarrow$ **Secrets and variables** $\rightarrow$ **Actions**.
- Click **New repository secret**.
- Name: `GEMINI_API_KEY`
- Value: `<Your Google Gemini API Key>`

### 2. Workflow Trigger (`.github/workflows/review.yml`)
```yaml
name: "AI Code Review"

on:
  pull_request:
    types: [opened, synchronize]

permissions:
  contents: read
  pull-requests: write

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Run AI Code Reviewer Action
        uses: ./
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          gemini_api_key: ${{ secrets.GEMINI_API_KEY }}
          db_path: 'reviewer.db'
```

---

## 6. Testing & Quality Assurance

Run the automated test suite locally:

```bash
# Activate virtual environment
source .venv/bin/activate  # Or on Windows: .venv\Scripts\activate

# Run pytest
pytest -v tests/
```

### Test Coverage
- **`tests/test_database.py`**: Validates 3NF schema, cascade rules, indexing, and logging.
- **`tests/test_diff_parser.py`**: Verifies unified git diff parsing, line numbering, and deleted file handling.
- **`tests/test_cli.py`**: Validates command-line arguments and profile updates.
- **`tests/test_llm_engine.py`**: Tests prompt assembly, JSON generation, and non-blocking failure recovery.
- **`tests/test_comment_router.py`**: Verifies GitHub REST API v3 PR inline comment posting.
