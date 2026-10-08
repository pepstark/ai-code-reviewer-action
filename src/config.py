import os
from dataclasses import dataclass
from typing import Optional


def _load_dotenv(filepath: str = ".env"):
    """Lightweight zero-dependency .env loader."""
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k and k not in os.environ:
                            os.environ[k] = v
        except Exception:
            pass


@dataclass
class Config:
    """Centralized configuration for AI Code Reviewer GitHub Action."""

    github_token: Optional[str]
    gemini_api_key: Optional[str]
    db_path: str
    github_event_path: Optional[str]
    gemini_model: str

    @classmethod
    def from_env(cls) -> "Config":
        _load_dotenv()
        return cls(
            github_token=os.getenv("GITHUB_TOKEN"),
            gemini_api_key=os.getenv("SESH_GEMINI_BABA_KEY") or os.getenv("GEMINI_API_KEY"),
            db_path=os.getenv("DB_PATH", "reviewer.db"),
            github_event_path=os.getenv("GITHUB_EVENT_PATH"),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
        )

    def validate(self) -> list[str]:
        """Validates configuration parameters and returns a list of warning/error messages."""
        issues = []
        if not self.gemini_api_key:
            issues.append("GEMINI_API_KEY is not set.")
        if not self.github_token:
            issues.append("GITHUB_TOKEN is not set.")
        if not self.github_event_path:
            issues.append("GITHUB_EVENT_PATH is not set.")
        return issues
