def calculate_metrics(user_id, count):
    # 1. SECURITY: Hardcoded secret token
    api_token = "ghp_secret_token_12345"

    # 2. BOUNDARY_CHECK: Division by zero without validation
    score = 100 / count

    # 3. RESOURCE_LEAK: Unclosed file handle
    f = open("metrics.log", "w")
    f.write(f"User {user_id}: {score}")

    return score
