#config.py
import os
import json
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
from neo4j import GraphDatabase, AsyncGraphDatabase
import logging
import pandas as pd
import warnings

logger = logging.getLogger(__name__)

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
    TOKEN = get_from_vault("app", "bot_token")
    BOT_USERNAME = get_from_vault("app", "BOT_USERNAME")
else:
    TOKEN = os.getenv("bot_token")
    BOT_USERNAME = os.getenv("BOT_USERNAME")

# сервисный аккаунт Google Sheets из переменной окружения и локально
def get_gsheets_credentials(scopes=None):
    if scopes is None:
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]

    # 1. пытаемся достать JSON из Vault
    try:
        creds_json = get_from_vault("app", "GOOGLE_CREDENTIALS_JSON")
    except Exception as e:
        logging.debug(f"[WARN] не удалось получить GOOGLE_CREDENTIALS_JSON из Vault: {e}")
        creds_json = None

    # 2. если удалось — используем его
    if creds_json:
        try:
            creds_dict = json.loads(creds_json)
            return Credentials.from_service_account_info(creds_dict, scopes=scopes)
        except Exception as e:
            logging.error(f"[WARN] не удалось распарсить GOOGLE_CREDENTIALS_JSON: {e}")

    # 3. fallback — локальный файл service_account.json
    if os.path.exists("alcohol-service-agent.json"):
        logging.info("[INFO] Используем локальный alcohol-service-agent.json")
        return Credentials.from_service_account_file("alcohol-service-agent.json", scopes=scopes)

    # 4. если ничего не нашли
    raise RuntimeError("Google service account credentials not found (Vault и локальный файл недоступны)")

# ==========================================================
# 🕸 Настройки Neo4j
# ==========================================================
if MODE == "prod":
    URI  = "bolt://neo4j:7687"
    USER = "neo4j"
    PASS = get_from_vault("app", "neo4j_password")
else:
    URI  = os.getenv("NEO4J_URI")
    USER = os.getenv("NEO4J_USER")
    PASS = os.getenv("NEO4J_PASS")

# 🟢 Shared SYNC driver (used by workers, bot, normalizers, parsers)
driver = GraphDatabase.driver(URI, auth=(USER, PASS))

# 🟢 NEW: Shared ASYNC driver (used by admin API / FastAPI)

async_driver = AsyncGraphDatabase.driver(URI, auth=(USER, PASS))


#Silence pandas warning about column types
pd.set_option('future.no_silent_downcasting', True)

#silence xml in xlsx warning
warnings.filterwarnings(
    "ignore",
    message="Unknown extension is not supported and will be removed",
    module="openpyxl.worksheet._reader"
)

# ==========================================================
# 🌐 Admin API base URL (used by MiniApp)
# ==========================================================
#
if MODE == "prod":
    ADMIN_API_BASE = os.getenv("ADMIN_API_BASE", "https://your-admin-domain/admin")
else:
    ADMIN_API_BASE = "http://localhost:8001/admin"

#Separate mode for admin secrets
IS_ADMIN = os.environ.get("ADMIN_MODE") == "1"

if not IS_ADMIN:
    TOKEN = get_from_vault("app", "bot_token")
    GOOGLE_CREDS = get_from_vault("app", "google_credentials")
else:
    TOKEN = None
    GOOGLE_CREDS = None
