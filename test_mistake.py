def save_user_credentials():
    api_token = "ghp_super_secret_token_12345"
    f = open("credentials.txt", "w")
    f.write(api_token)
