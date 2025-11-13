from dotenv import load_dotenv, find_dotenv

if env_path := find_dotenv(usecwd=True, raise_error_if_not_found=False):
    load_dotenv(env_path, override=True)
    print(f"Environment variables loaded from {env_path}")

else:
    raise FileNotFoundError(".env file not found")
