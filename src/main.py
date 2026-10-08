import os
import json
import sys

# Ensure src directory is in sys.path for direct script execution
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import DatabaseManager
from diff_parser import GitDiffParser
from llm_engine import LLMReviewEngine
from comment_router import GitHubCommentRouter
from config import Config


def main():
    print("=== AI 'Code Reviewer' GitHub Action Starting ===")

    # 1. Read Environment & Event Context
    config = Config.from_env()

    if not config.github_event_path or not os.path.exists(config.github_event_path):
        print(f"[ERROR] GITHUB_EVENT_PATH missing or invalid: {config.github_event_path}")
        sys.exit(0)  # Exit 0 so builds don't fail unexpectedly during non-PR or test runs

    with open(config.github_event_path, "r", encoding="utf-8") as f:
        event_data = json.load(f)

    pr_data = event_data.get("pull_request", {})
    if not pr_data:
        print("[INFO] Event is not a pull_request. Terminating execution.")
        sys.exit(0)

    pr_number = pr_data.get("number")
    author = pr_data.get("user", {}).get("login", "default_user")
    repo = event_data.get("repository", {}).get("full_name")
    commit_sha = pr_data.get("head", {}).get("sha")
    base_ref = pr_data.get("base", {}).get("ref", "main")

    head_display = commit_sha[:7] if commit_sha else "unknown"
    print(f"[INFO] Evaluating PR #{pr_number} by @{author} in {repo} [Head: {head_display}]")

    # 2. Initialize Database & Query Historical Anti-Patterns
    db = DatabaseManager(config.db_path)
    mistakes = db.get_developer_mistakes(author)
    print(f"[INFO] Loaded {len(mistakes)} historical anti-pattern(s) for @{author}.")

    # 3. Parse Git Diff Lines
    raw_diff = GitDiffParser.get_pr_diff(base_ref=f"origin/{base_ref}")
    parsed_diff = GitDiffParser.parse_diff(raw_diff)
    print(f"[INFO] Extracted {len(parsed_diff)} modified code lines across incoming commits.")

    if not parsed_diff:
        print("[INFO] No code additions found to review. Exiting.")
        sys.exit(0)

    # 4. Invoke LLM Review Engine
    engine = LLMReviewEngine(api_key=config.gemini_api_key, db_manager=db, model_name=config.gemini_model)
    reviews = engine.evaluate_code(parsed_diff, mistakes)
    print(f"[INFO] LLM generated {len(reviews)} review critique(s).")

    # 5. Route & Post Comments
    if reviews:
        if config.github_token:
            router = GitHubCommentRouter(
                github_token=config.github_token,
                repo=repo,
                pr_number=pr_number,
                commit_sha=commit_sha,
                db_manager=db
            )
            posted_count = router.post_annotations(reviews)
            print(f"[INFO] Dispatched {posted_count} inline review comment(s) to PR #{pr_number}.")
        else:
            print("[WARNING] GITHUB_TOKEN not provided; skipping inline comment posting to GitHub API.")
    else:
        print("[INFO] No code issues flagged by AI reviewer.")

    print("=== AI 'Code Reviewer' Action Execution Completed Successfully ===")


if __name__ == "__main__":
    main()
