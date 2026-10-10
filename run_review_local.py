import os
import sys

# Ensure UTF-8 output on Windows consoles
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure src is in sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from config import Config
from database import DatabaseManager
from llm_engine import LLMReviewEngine


def main():
    print("=" * 60)
    print("LOCAL AI CODE REVIEWER EXECUTION")
    print("=" * 60)

    # 1. Load Config
    config = Config.from_env()
    db = DatabaseManager(config.db_path)

    # 2. Query Developer Mistakes
    username = "pepstark"
    mistakes = db.get_developer_mistakes(username)
    print(f"\n[1] Loaded {len(mistakes)} historical anti-patterns for @{username} from SQLite database:")
    for m in mistakes:
        print(f"    - [{m['tag_category']}] {m['description']}")

    # 3. Target File to Review
    target_file = sys.argv[1] if len(sys.argv) > 1 else "calculate.py"
    if not os.path.exists(target_file):
        print(f"\n[ERROR] File '{target_file}' not found.")
        return

    print(f"\n[2] Scanning target file: '{target_file}'...")
    with open(target_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Build diff chunks from target file lines
    diff_chunks = []
    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            diff_chunks.append({
                "file_path": target_file,
                "line_number": idx,
                "content": line.rstrip("\n")
            })

    print(f"    - Extracted {len(diff_chunks)} code lines for AI evaluation.")

    # 4. Invoke LLM Engine
    print(f"\n[3] Calling Gemini AI Review Engine (Model: {config.gemini_model})...")
    engine = LLMReviewEngine(api_key=config.gemini_api_key, db_manager=db, model_name=config.gemini_model)
    reviews = engine.evaluate_code(diff_chunks, mistakes)

    # 5. Display Results
    print(f"\n[4] Review Output: Found {len(reviews)} issue(s):\n")
    if not reviews:
        print("    [INFO] No code issues flagged by AI reviewer.")
        return

    for item in reviews:
        file_path = item.get("file_path")
        line_num = item.get("line_number")
        tag = item.get("tag_category", "GENERAL")
        critique = item.get("critique", "")

        print("-" * 60)
        print(f"[FLAGGED] {file_path} at Line {line_num} [{tag}]")
        print("-" * 60)
        print(critique)
        print()

    print("=" * 60)
    print("[SUCCESS] Local AI Review Completed Successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
