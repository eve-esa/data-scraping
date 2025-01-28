FROM python:3.10.12-slim AS system

ENV PYTHONUNBUFFERED=1
ENV WATCHFILES_FORCE_POLLING=true

### SYSTEM SETUP ###
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    libzip-dev \
    gnupg \
    make \
    gcc \
    build-essential \
    openssl \
    curl \
    coreutils \
    libssl-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

FROM system AS build

# Set environment variable for Chrome
ENV CHROME_PATH=/usr/bin/google-chrome
ENV CHROME_OPTIONS="--no-sandbox --disable-gpu --disable-dev-shm-usage"

WORKDIR /app

COPY requirements.txt .
COPY Makefile .

RUN pip install -U pip && pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["tail", "-f", "/dev/null"]