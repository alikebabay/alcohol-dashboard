import os
import json
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv("neo4j.env")

# ==========================================================
# 🌍 Определяем окружение: dev или prod
# ==========================================================
MODE = os.getenv("MODE", "dev").lower()

# ==========================================================
# 🔐 Функция безопасного доступа к Vault
# ==========================================================
def get_from_vault(path, key):
    import requests
    VAULT_ADDR = os.getenv("VAULT_ADDR", "http://vault:8200")

    # ищем токен только снаружи: из файла или из окружения
    token_path = os.getenv("VAULT_TOKEN_FILE")
    token = None
    if token_path and os.path.exists(token_path):
        with open(token_path) as f:
            token = f.read().strip()
    elif os.getenv("VAULT_TOKEN"):
        token = os.getenv("VAULT_TOKEN")

    if not token:
        raise RuntimeError("Vault token not provided")

    resp = requests.get(
        f"{VAULT_ADDR}/v1/secret/data/{path}",
        headers={"X-Vault-Token": token},
        timeout=5,
    )

    if resp.status_code == 200:
        return resp.json()["data"]["data"].get(key)
    raise RuntimeError(f"Vault fetch failed: {resp.status_code} {resp.text}")

# грузим локальный .env если есть
if os.path.exists("bot_token.env"):
    load_dotenv("bot_token.env")

if MODE == "prod":
    TOKEN = get_from_vault("bot", "bot_token")
    BOT_USERNAME = get_from_vault("bot", "BOT_USERNAME")
else:
    TOKEN = os.getenv("bot_token")
    BOT_USERNAME = os.getenv("BOT_USERNAME")

# сервисный аккаунт Google Sheets из переменной окружения и локально
def get_gsheets_credentials(scopes=None):
    if scopes is None:
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]

    # 1. сначала пробуем creds из переменной окружения (Heroku / облако)
    if MODE == "prod":
        creds_json = get_from_vault("google", "google_creds")
    else:
        creds_json = os.getenv("google_creds")

    if creds_json:
        creds_dict = json.loads(creds_json)
        return Credentials.from_service_account_info(creds_dict, scopes=scopes)

    # 2. fallback — локальный файл service_account.json
    if os.path.exists("service_account.json"):
        return Credentials.from_service_account_file("service_account.json", scopes=scopes)

    raise RuntimeError("Google service account credentials not found")

# ==========================================================
# 🕸 Настройки Neo4j
# ==========================================================
if MODE == "prod":
    URI  = "bolt://neo4j:7687"
    USER = "neo4j"
    PASS = get_from_vault("neo4j", "neo4j_password")
else:
    URI  = os.getenv("NEO4J_URI")
    USER = os.getenv("NEO4J_USER")
    PASS = os.getenv("NEO4J_PASS")

driver = GraphDatabase.driver(URI, auth=(USER, PASS))