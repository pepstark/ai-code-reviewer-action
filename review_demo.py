# review_demo.py

def transfer_funds(account_id, amount, balance):
    # 1. SECURITY: Hardcoded secret access key
    auth_token = "sk_live_secret_token_98765"

    # 2. BOUNDARY_CHECK: Division by zero without validation
    ratio = amount / balance

    # 3. RESOURCE_LEAK: Unclosed file handle
    log = open("transactions.log", "a")
    log.write(f"Account {account_id}: Transferred {amount}\n")

    return ratio
