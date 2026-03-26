#admin.Dockerfile
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl jq && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

COPY frontend-miniapp/ frontend-miniapp/

EXPOSE 8001

CMD ["uvicorn", "admin.admin_api:app", "--host", "0.0.0.0", "--port", "8001"]