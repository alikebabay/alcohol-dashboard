#config.py
import os
import json
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
from neo4j import GraphDatabase
import pandas as pd
import warnings
import socket

#минимальная длина продуктовой строки
MIN_PRODUCT_LEN = 32

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
SECRETS_PATH = "/etc/secrets/bot_token.env"
LOCAL_PATH = "bot_token.env"

if MODE == "prod":
    if os.path.exists(SECRETS_PATH):
        load_dotenv(SECRETS_PATH)
    TOKEN = os.getenv("BOT_TOKEN")
    BOT_USERNAME = os.getenv("BOT_USERNAME")
else:
    if os.path.exists(LOCAL_PATH):
        load_dotenv(LOCAL_PATH)
    TOKEN = os.getenv("BOT_TOKEN")
    BOT_USERNAME = os.getenv("BOT_USERNAME")

# сервисный аккаунт Google Sheets из переменной окружения и локально
def get_gsheets_credentials(scopes=None):
    if scopes is None:
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]

    # 1. пытаемся достать JSON из Vault
    try:
        creds_json = get_from_vault("app", "GOOGLE_CREDENTIALS_JSON")
    except Exception as e:
        print(f"[WARN] не удалось получить GOOGLE_CREDENTIALS_JSON из Vault: {e}")
        creds_json = None

    # 2. если удалось — используем его
    if creds_json:
        try:
            creds_dict = json.loads(creds_json)
            return Credentials.from_service_account_info(creds_dict, scopes=scopes)
        except Exception as e:
            print(f"[WARN] не удалось распарсить GOOGLE_CREDENTIALS_JSON: {e}")

    # 3. fallback — локальный файл service_account.json
    if os.path.exists("alcohol-service-agent.json"):
        print("[INFO] Используем локальный alcohol-service-agent.json")
        return Credentials.from_service_account_file("alcohol-service-agent.json", scopes=scopes)

    # 4. если ничего не нашли
    raise RuntimeError("Google service account credentials not found (Vault и локальный файл недоступны)")

IS_ADMIN = os.environ.get("ADMIN_MODE") == "1"

# ==========================================================
# 🕸 Настройки Neo4j
# ==========================================================
if MODE == "dev":
    # local dev
    URI  = os.getenv("NEO4J_URI")
    USER = os.getenv("NEO4J_USER")
    PASS = os.getenv("NEO4J_PASS")

elif IS_ADMIN:
    # admin container in prod
    URI  = "bolt://neo4j:7687"
    USER = "neo4j"
    PASS = get_from_vault("app", "neo4j_password")

else:
    # main backend in prod
    URI  = "bolt://neo4j:7687"
    USER = "neo4j"
    PASS = get_from_vault("app", "neo4j_password")

# 🟢 Shared SYNC driver (used by workers, bot, normalizers, parsers)
driver = GraphDatabase.driver(URI, auth=(USER, PASS))




# ==========================================================
# 🌐 Admin API base URL
# ==========================================================
try:
    IP = socket.gethostbyname(socket.gethostname())
except:
    IP = "localhost"

ADMIN_API_BASE = f"http://{IP}:8001/admin"

if MODE == "dev":
    # local dev: use .env token, google from local file
    TOKEN = TOKEN or os.getenv("bot_token")
    try:
        GOOGLE_CREDS = get_gsheets_credentials()
    except Exception:
        GOOGLE_CREDS = None

elif IS_ADMIN:
    # admin mode: no bot/google
    TOKEN = None
    GOOGLE_CREDS = None

else:
    # prod backend
    TOKEN = get_from_vault("app", "bot_token")
    GOOGLE_CREDS = get_from_vault("app", "google_credentials")


# prod google sheets
SPREADSHEET_PROD = "1dISLvKdfi5DCTeYlQ5JXiBcyusrIlJkmikDvkWAcg60"
SHEET_NAME_PROD = "master"   # имя листа в таблице
# dev google sheets
SPREADSHEET_DEV = "1Dyr2Uz3GLQ_cM4ZZVUMTV0GhHw9vbLdrq518NOVqOh4"
SHEET_NAME_DEV = "master_test"


# 🧩 Карта опечаток поставщиков, словарь замены
ABBREVIATIONS = {
    "yo": "Year Old",    
    "Grey Goose Blue": "Grey Goose",
    "PS": "Pagos Seleccionados",
    "JW": "Johnnie Walker",
}


#regression test mode
class ExecutionPolicy:
    allow_graph_writes = True
    allow_sheets = True
    allow_notifications = True

POLICY = ExecutionPolicy()

#Silence pandas warning about column types
pd.set_option('future.no_silent_downcasting', True)

#silence xml in xlsx warning
warnings.filterwarnings(
    "ignore",
    message="Unknown extension is not supported and will be removed",
    module="openpyxl.worksheet._reader"
)


