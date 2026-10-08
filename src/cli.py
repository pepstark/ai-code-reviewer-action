import argparse
import os
import sys

# Ensure src directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import DatabaseManager


def main():
    parser = argparse.ArgumentParser(description="AI Code Reviewer Developer Profile Manager")
    parser.add_argument("--db", default=os.getenv("DB_PATH", "reviewer.db"), help="Path to SQLite database file")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Add Developer
    dev_parser = subparsers.add_parser("add-dev", help="Register a new developer profile")
    dev_parser.add_argument("--username", required=True, help="GitHub username")
    dev_parser.add_argument("--email", required=True, help="Developer email address")

    # Add Mistake Log
    mistake_parser = subparsers.add_parser("add-mistake", help="Log a historical anti-pattern for a developer")
    mistake_parser.add_argument("--username", required=True, help="GitHub username")
    mistake_parser.add_argument(
        "--category",
        required=True,
        choices=["SECURITY", "RESOURCE_LEAK", "BOUNDARY_CHECK", "SQL_INJECTION", "LOGIC"],
        help="Anti-pattern category tag"
    )
    mistake_parser.add_argument("--description", required=True, help="Description of recurring mistake")

    # List Mistakes
    list_parser = subparsers.add_parser("list", help="List all anti-patterns logged for a developer")
    list_parser.add_argument("--username", required=True, help="GitHub username")

    # Seed Database
    seed_parser = subparsers.add_parser("seed", help="Seed default developer profile and anti-patterns")

    args = parser.parse_args()
    db = DatabaseManager(args.db)

    if args.command == "add-dev":
        with db.get_connection() as conn:
            try:
                conn.cursor().execute(
                    "INSERT INTO DEVELOPER (username, email) VALUES (?, ?)",
                    (args.username, args.email)
                )
                conn.commit()
                print(f"[SUCCESS] Developer @{args.username} ({args.email}) added.")
            except Exception as e:
                print(f"[ERROR] Could not add developer @{args.username}: {e}")

    elif args.command == "add-mistake":
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT developer_id FROM DEVELOPER WHERE username = ?", (args.username,))
            dev = cur.fetchone()
            if not dev:
                print(f"[ERROR] Developer @{args.username} not found. Run 'add-dev' first.")
                return
            cur.execute(
                "INSERT INTO MISTAKE_LOG (developer_id, tag_category, description) VALUES (?, ?, ?)",
                (dev["developer_id"], args.category, args.description)
            )
            conn.commit()
        print(f"[SUCCESS] Anti-pattern [{args.category}] logged for @{args.username}.")

    elif args.command == "list":
        mistakes = db.get_developer_mistakes(args.username)
        print(f"--- Anti-Patterns for @{args.username} ({len(mistakes)} total) ---")
        for m in mistakes:
            print(f"[{m['mistake_id']}] [{m['tag_category']}] {m['description']}")

    elif args.command == "seed":
        db.seed_default_data()
        print(f"[SUCCESS] Database seeded at '{args.db}'.")


if __name__ == "__main__":
    main()
