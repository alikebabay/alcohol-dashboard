# Use Python 3.11 base image (official slim variant)
#Dockerfile
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["bash", "-c", "\
set -e; \
if [ \"$MODE\" = \"prod\" ]; then \
  echo 'Fetching app secrets from Vault...'; \
  data=$(curl -s -H \"X-Vault-Token: $(cat /run/secrets/vault_token)\" \"$VAULT_ADDR/v1/$VAULT_SECRET_PATH\"); \
  export NEO4J_URI=$(echo \"$data\" | jq -r '.data.data.NEO4J_URI'); \
  export NEO4J_USER=$(echo \"$data\" | jq -r '.data.data.NEO4J_USER'); \
  export NEO4J_PASS=$(echo \"$data\" | jq -r '.data.data.NEO4J_PASS'); \
  echo \"$data\" | jq -r '.data.data.GOOGLE_CREDENTIALS_JSON' > /run/secrets/google_credentials.json; \
  export GOOGLE_APPLICATION_CREDENTIALS=/run/secrets/google_credentials.json; \
  echo 'Secrets loaded.'; \
else \
  echo 'DEV mode — skipping Vault'; \
fi; \
exec python main.py \
"]
