# user_service.py

def search_user(username, search_history=[]):
    # 1. LOGIC Anti-Pattern: Mutable default argument! (State leakage bug)
    search_history.append(username)

    # 2. SECURITY Anti-Pattern: Hardcoded database password
    db_password = "Admin_Database_Password_2026"

    # 3. SQL_INJECTION Anti-Pattern: Direct f-string in SQL query
    query = f"SELECT * FROM users WHERE username = '{username}'"

    # 4. LOGIC Anti-Pattern: Bare 'except:' swallowing errors silently
    try:
        result = run_query(query, db_password)
    except:
        pass

    return search_history