FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl jq && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY admin/ admin/

COPY frontend-miniapp/ frontend-miniapp/

EXPOSE 8001

CMD ["bash", "-c", "\
  set -e; \
  echo 'Fetching admin secrets from Vault...' && \
  data=$(curl -s -H \"X-Vault-Token: $(cat /run/secrets/vault_token)\" \"$VAULT_ADDR/v1/$VAULT_SECRET_PATH\") && \
  export NEO4J_URI=$(echo \"$data\" | jq -r '.data.data.NEO4J_URI') && \
  export NEO4J_USER=$(echo \"$data\" | jq -r '.data.data.NEO4J_USER') && \
  export NEO4J_PASS=$(echo \"$data\" | jq -r '.data.data.NEO4J_PASS') && \
  echo 'Secrets loaded. Starting admin API...' && \
  exec uvicorn admin.admin_api:app --host 0.0.0.0 --port 8001 \
"]
