import os
import requests
from typing import List, Dict, Any, Optional


class GitHubCommentRouter:
    def __init__(self, github_token: str, repo: str, pr_number: int, commit_sha: str, db_manager):
        self.token = github_token
        self.repo = repo
        self.pr_number = pr_number
        self.commit_sha = commit_sha
        self.db = db_manager
        self.base_url = f"https://api.github.com/repos/{self.repo}/pulls/{self.pr_number}/comments"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }

    def post_annotations(self, reviews: List[Dict[str, Any]]) -> int:
        """Posts inline comments on the exact line and file inside the active PR.
        Returns the count of successfully posted comments."""
        successful_posts = 0

        for item in reviews:
            file_path = item.get("file_path")
            line_number = item.get("line_number")
            critique = item.get("critique")
            tag = item.get("tag_category", "NOTE")
            mistake_id = item.get("mistake_id")

            if not file_path or not line_number or not critique:
                continue

            formatted_body = (
                f"### 🤖 AI Code Reviewer Warning (`{tag}`)\n\n"
                f"{critique}\n\n"
                f"> *Context: Matched against historical developer anti-pattern inventory.*"
            )

            payload = {
                "body": formatted_body,
                "commit_id": self.commit_sha,
                "path": file_path,
                "line": line_number,
                "side": "RIGHT"
            }

            try:
                response = requests.post(self.base_url, json=payload, headers=self.headers, timeout=15)
                if response.status_code == 201:
                    print(f"[SUCCESS] Posted inline comment on {file_path}:{line_number}")
                    self.db.log_review_action(
                        pr_number=self.pr_number,
                        file_path=file_path,
                        line_number=line_number,
                        status_flag="FLAGGED",
                        mistake_id=mistake_id
                    )
                    successful_posts += 1
                else:
                    print(f"[WARNING] Inline comment failed on {file_path}:{line_number} (HTTP {response.status_code}): {response.text}")
                    # Resilient fallback: Post as PR conversation comment so review is guaranteed visible!
                    issue_url = f"https://api.github.com/repos/{self.repo}/issues/{self.pr_number}/comments"
                    issue_payload = {
                        "body": f"### ⚠️ Review for `{file_path}` (Line {line_number})\n\n{formatted_body}"
                    }
                    fb_res = requests.post(issue_url, json=issue_payload, headers=self.headers, timeout=15)
                    if fb_res.status_code == 201:
                        print(f"[SUCCESS] Fallback: Posted PR conversation comment for {file_path}:{line_number}")
                        self.db.log_review_action(
                            pr_number=self.pr_number,
                            file_path=file_path,
                            line_number=line_number,
                            status_flag="FLAGGED",
                            mistake_id=mistake_id
                        )
                        successful_posts += 1
                    else:
                        print(f"[ERROR] Fallback PR comment also failed (HTTP {fb_res.status_code}): {fb_res.text}")
            except Exception as e:
                print(f"[ERROR] Network exception posting comment to {file_path}:{line_number}: {e}")

        return successful_posts
