import sqlite3
import os
from typing import List, Dict, Any, Optional


class DatabaseManager:
    def __init__(self, db_path: str = "reviewer.db"):
        self.db_path = db_path
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Creates tables and indexes if they do not exist."""
        # Ensure parent directory exists if a custom path is supplied
        parent_dir = os.path.dirname(self.db_path)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS DEVELOPER (
                developer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL
            );
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS MISTAKE_LOG (
                mistake_id INTEGER PRIMARY KEY AUTOINCREMENT,
                developer_id INTEGER NOT NULL,
                tag_category TEXT NOT NULL,
                description TEXT NOT NULL,
                date_logged TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (developer_id) REFERENCES DEVELOPER(developer_id) ON DELETE CASCADE
            );
            """)
            cursor.execute("""
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
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS API_DECISION_LOG (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                endpoint_url TEXT NOT NULL,
                retry_count INTEGER DEFAULT 0,
                response_code INTEGER NOT NULL,
                status_message TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_developer_username ON DEVELOPER(username);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_mistake_tag ON MISTAKE_LOG(tag_category);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pr_history ON PR_REVIEW_HISTORY(pr_number);")
            conn.commit()

    def seed_default_data(self):
        """Initializes default developer profiles and anti-pattern seed inventory."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Register both SeshanthSathish and their GitHub handle pepstark
            developers = [
                (1, 'SeshanthSathish', 'seshanth@example.com'),
                (2, 'pepstark', 'seshanth2007@gmail.com')
            ]
            for dev_id, username, email in developers:
                cursor.execute("""
                INSERT INTO DEVELOPER (developer_id, username, email)
                VALUES (?, ?, ?)
                ON CONFLICT(username) DO NOTHING;
                """, (dev_id, username, email))

            seed_mistakes = [
                ('SECURITY', 'Hardcoding plaintext secrets, passwords, or API tokens directly inside Python code instead of using environment variables (os.getenv).'),
                ('RESOURCE_LEAK', 'Opening files using open() or database connections without using "with" context managers or proper try-finally close blocks.'),
                ('SQL_INJECTION', 'Constructing SQL statements using Python f-strings or direct string concatenation rather than parameterized queries.'),
                ('BOUNDARY_CHECK', 'Performing division operations without checking if the divisor is zero, causing ZeroDivisionError crashes.'),
                ('LOGIC', 'Using bare "except:" clauses or catching generic Exception without logging, silently swallowing unexpected errors.'),
                ('LOGIC', 'Using mutable default arguments (e.g., def func(items=[])) in Python functions causing unexpected state persistence.')
            ]

            for _, username, _ in developers:
                cursor.execute("SELECT developer_id FROM DEVELOPER WHERE username = ?", (username,))
                dev = cursor.fetchone()
                if dev:
                    d_id = dev["developer_id"]
                    for category, description in seed_mistakes:
                        cursor.execute("""
                        SELECT mistake_id FROM MISTAKE_LOG
                        WHERE developer_id = ? AND tag_category = ? AND description = ?
                        """, (d_id, category, description))
                        if not cursor.fetchone():
                            cursor.execute("""
                            INSERT INTO MISTAKE_LOG (developer_id, tag_category, description)
                            VALUES (?, ?, ?)
                            """, (d_id, category, description))

            conn.commit()

    def get_developer_mistakes(self, username: str) -> List[Dict[str, Any]]:
        """Queries historical anti-patterns for a given GitHub username."""
        query = """
        SELECT m.mistake_id, m.tag_category, m.description
        FROM MISTAKE_LOG m
        JOIN DEVELOPER d ON m.developer_id = d.developer_id
        WHERE d.username = ?
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (username,))
            return [dict(row) for row in cursor.fetchall()]

    def log_review_action(self, pr_number: int, file_path: str, line_number: int, status_flag: str, mistake_id: Optional[int] = None):
        """Records an identified review critique into PR_REVIEW_HISTORY."""
        query = """
        INSERT INTO PR_REVIEW_HISTORY (mistake_id, pr_number, file_path, line_number, status_flag)
        VALUES (?, ?, ?, ?, ?)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(query, (mistake_id, pr_number, file_path, line_number, status_flag))
                conn.commit()
            except sqlite3.IntegrityError:
                # If mistake_id violates foreign key constraint (e.g. LLM invented an invalid ID), fallback to NULL
                cursor.execute(query, (None, pr_number, file_path, line_number, status_flag))
                conn.commit()

    def log_api_decision(self, endpoint: str, status_code: int, message: str, retries: int = 0):
        """Audit logging for API responses and fallback exceptions."""
        query = """
        INSERT INTO API_DECISION_LOG (endpoint_url, retry_count, response_code, status_message)
        VALUES (?, ?, ?, ?)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (endpoint, retries, status_code, message))
            conn.commit()
