import os
import sys

# Ensure UTF-8 output on Windows consoles
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

print("=" * 60)
print("PYTHON CODE EXECUTION DEMO")
print("=" * 60)

# -------------------------------------------------------------
# Part 1: Running the Code with Anti-Patterns (Demonstrating Bugs)
# -------------------------------------------------------------
print("\n[SCENARIO 1] Executing code with anti-patterns...")


def calculate_metrics_buggy(user_id, count):
    # 1. SECURITY: Hardcoded secret token
    api_token = "ghp_secret_token_12345"
    print(f"  [Security Alert] Hardcoded API Token exposed in memory: {api_token}")

    # 2. BOUNDARY_CHECK: Potential ZeroDivisionError
    print(f"  Attempting division: 100 / {count}")
    try:
        score = 100 / count
    except ZeroDivisionError as e:
        print(f"  [CRASH] ZeroDivisionError caught! Reason: {e}")
        score = 0

    # 3. RESOURCE_LEAK: Unclosed file handle
    f = open("metrics_buggy.log", "w")
    f.write(f"User {user_id}: {score}\n")
    print("  [Warning] File 'metrics_buggy.log' opened but f.close() was omitted!")

    return score


print("Running calculate_metrics_buggy(user_id=101, count=0)...")
calculate_metrics_buggy(101, 0)

# -------------------------------------------------------------
# Part 2: Running the Corrected Code (Clean, Secure & Robust)
# -------------------------------------------------------------
print("\n" + "=" * 60)
print("[SCENARIO 2] Executing AI-Corrected Code...")


def calculate_metrics_fixed(user_id, count):
    # Fix 1: Load secret from environment variable
    api_token = os.getenv("API_TOKEN", "default_safe_token")
    print(f"  [PASS] Secure Token loaded from environment: {api_token[:4]}****")

    # Fix 2: Defensive boundary check for zero divisor
    if count == 0:
        print("  [PASS] Boundary check passed: Divisor is 0, returning safe score 0.0")
        score = 0.0
    else:
        score = 100.0 / count

    # Fix 3: Proper context manager ensuring immediate file closure
    with open("metrics_fixed.log", "w") as f:
        f.write(f"User {user_id}: {score}\n")
    print("  [PASS] File written and automatically closed with 'with' context manager.")

    return score


print("Running calculate_metrics_fixed(user_id=101, count=0)...")
result = calculate_metrics_fixed(101, 0)
print(f"Final Clean Result: {result}")

print("\n" + "=" * 60)
print("[SUCCESS] Demo execution finished successfully!")
print("=" * 60)
