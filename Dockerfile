FROM python:3.12-slim

# System deps for Playwright + yfinance
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    ca-certificates \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpangocairo-1.0-0 \
    libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (Chromium only)
RUN playwright install chromium && playwright install-deps chromium

# Copy source
COPY agent/ ./agent/
COPY setup_blog.py .

# Data directory (mounted as Docker volume)
RUN mkdir -p /app/data

ENV PYTHONUNBUFFERED=1
ENV DB_PATH=/app/data/agent.db

CMD ["python", "-m", "agent.main"]
