
def save_user_score(user_id, total, count):
    # 1. SECURITY Anti-Pattern (Hardcoded secret token)
    api_token = "ghp_live_secret_token_12345"

    # 2. BOUNDARY_CHECK Anti-Pattern (Division without zero check)
    average = total / count

    # 3. RESOURCE_LEAK Anti-Pattern (Open file without close/with)
    f = open("scores.txt", "w")
    f.write(f"User {user_id} Score: {average}")

    return average