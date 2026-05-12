FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PYTHONPATH=/workspace/src \
    CODEX_HOME=/root/.codex

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        curl \
        git \
        gnupg \
        nodejs \
        npm \
        openssh-client \
        procps \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --upgrade pip \
    && python -m pip install "pyyaml>=6.0" "mcp>=1.2.0" "playwright>=1.45.0"

RUN npm install -g @openai/codex @modelcontextprotocol/server-filesystem @playwright/mcp \
    && python -m playwright install --with-deps chromium

WORKDIR /workspace

CMD ["python", "-m", "symphony_l4_runner", "--workflow", "/workspace/WORKFLOW.md"]
