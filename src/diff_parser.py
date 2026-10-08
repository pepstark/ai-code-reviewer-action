import subprocess
import re
import sys
from typing import List, Dict, Any


class GitDiffParser:
    @staticmethod
    def get_pr_diff(base_ref: str = "origin/main") -> str:
        """Runs local git diff command to capture changes introduced in the PR."""
        cmd = ["git", "diff", "-U0", f"{base_ref}...HEAD"]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return result.stdout
        except subprocess.CalledProcessError as e:
            # Fallback attempts in case shallow fetch or alternative branch format exists
            err_summary = e.stderr.strip().splitlines()[0] if e.stderr else str(e)
            print(f"[WARNING] 'git diff -U0 {base_ref}...HEAD' failed: {err_summary}")
            alt_cmd = ["git", "diff", "-U0", "HEAD~1...HEAD"]
            try:
                alt_result = subprocess.run(alt_cmd, capture_output=True, text=True, check=True)
                return alt_result.stdout
            except Exception:
                return ""
        except FileNotFoundError:
            print("[ERROR] Git executable not found in system PATH.")
            return ""

    @staticmethod
    def parse_diff(diff_text: str) -> List[Dict[str, Any]]:
        """
        Parses unified diff into structured dictionaries containing:
        - file_path
        - line_number (in the incoming file)
        - content
        """
        parsed_files = []
        current_file = None
        current_line = 0

        for line in diff_text.splitlines():
            # Handle deleted files
            if line.startswith("+++ /dev/null"):
                current_file = None
                continue

            # Match target file header: +++ b/path/to/file.py
            if line.startswith("+++ b/"):
                current_file = line[6:]
                continue

            # Match hunk header: @@ -old,count +new,count @@
            hunk_match = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
            if hunk_match:
                current_line = int(hunk_match.group(1))
                continue

            # Identify added lines
            if line.startswith("+") and not line.startswith("+++"):
                added_code = line[1:]
                if current_file:
                    parsed_files.append({
                        "file_path": current_file,
                        "line_number": current_line,
                        "content": added_code
                    })
                current_line += 1
            elif not line.startswith("-"):
                current_line += 1

        return parsed_files
