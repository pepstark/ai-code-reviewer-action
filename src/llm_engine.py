import os
import json
from typing import List, Dict, Any, Optional

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


class LLMReviewEngine:
    def __init__(self, api_key: Optional[str], db_manager, model_name: str = "gemini-1.5-flash"):
        self.api_key = api_key
        self.db = db_manager
        self.model_name = os.getenv("GEMINI_MODEL", model_name)
        self.model = None

        if self.api_key and GENAI_AVAILABLE:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel(self.model_name)
            except Exception as e:
                print(f"[WARNING] Failed to initialize GenerativeModel '{self.model_name}': {e}")
                self.model = None

    def assemble_prompt(self, diff_chunks: List[Dict[str, Any]], mistakes: List[Dict[str, Any]]) -> str:
        """Combines system guidelines, past anti-patterns, and live diffs into a strict JSON prompt."""
        mistake_lines = []
        for m in mistakes:
            mid = m.get("mistake_id", "N/A")
            tag = m.get("tag_category", "GENERAL")
            desc = m.get("description", "")
            mistake_lines.append(f"- ID {mid} [{tag}]: {desc}")

        mistake_text = "\n".join(mistake_lines)

        prompt = f"""
You are an expert DevOps AI Code Reviewer. You are reviewing code changes for a pull request.
The developer who wrote this code has a history of repeating the following specific anti-patterns:
{mistake_text if mistake_text else "No historical anti-patterns logged for this user."}

Evaluate the following incoming code diff lines. If you identify:
1. A recurrence of one of the developer's historical anti-patterns.
2. A critical bug, security flaw, or syntax issue.

Respond ONLY with a valid JSON array of objects with this schema:
[
  {{
    "file_path": "string",
    "line_number": integer,
    "tag_category": "string (e.g. SECURITY, RESOURCE_LEAK, BOUNDARY_CHECK, SQL_INJECTION, or GENERAL)",
    "critique": "Actionable, constructive feedback formatted in GitHub Markdown",
    "mistake_id": integer or null
  }}
]

If no issues are found, return an empty array: []

INCOMING CODE CHANGES:
{json.dumps(diff_chunks, indent=2)}
"""
        return prompt

    def evaluate_code(self, diff_chunks: List[Dict[str, Any]], mistakes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Dispatches prompt to Gemini with safe non-blocking exception fallbacks."""
        if not diff_chunks:
            return []

        endpoint = f"google.generativeai.generate_content:{self.model_name}"

        if not self.api_key:
            error_msg = "GEMINI_API_KEY is not configured or is empty."
            print(f"[WARNING] {error_msg}")
            self.db.log_api_decision(endpoint, 401, error_msg, retries=0)
            return []

        if not GENAI_AVAILABLE or self.model is None:
            error_msg = "google-generativeai SDK not available or model initialization failed."
            print(f"[WARNING] {error_msg}")
            self.db.log_api_decision(endpoint, 503, error_msg, retries=0)
            return []

        prompt = self.assemble_prompt(diff_chunks, mistakes)

        try:
            response = self.model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            raw_text = response.text.strip()
            # Clean possible markdown wrapping if returned despite json mode
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.startswith("```"):
                raw_text = raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
            raw_text = raw_text.strip()

            parsed_json = json.loads(raw_text)
            if not isinstance(parsed_json, list):
                parsed_json = []

            self.db.log_api_decision(endpoint, 200, "Critique successfully generated.", retries=0)
            return parsed_json

        except Exception as e:
            # Non-blocking fallback loop: logs exception and allows PR pipeline to succeed safely
            error_msg = f"LLM API Exception encountered: {str(e)}"
            print(f"[WARNING] {error_msg}")
            self.db.log_api_decision(endpoint, 500, error_msg, retries=1)
            return []
