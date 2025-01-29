FROM python:3.10.12-slim AS system

ENV PYTHONUNBUFFERED=1
ENV WATCHFILES_FORCE_POLLING=true

### SYSTEM SETUP ###
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    xvfb \
    libzip-dev \
    gnupg \
    make \
    gcc \
    build-essential \
    openssl \
    curl \
    coreutils \
    libssl-dev \
    && wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get install ./google-chrome-stable_current_amd64.deb -y --fix-missing \
    && rm google-chrome-stable_current_amd64.deb \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

FROM system AS build

WORKDIR /app

COPY requirements.txt .
COPY Makefile .

RUN pip install -U pip && pip install --no-cache-dir -r requirements.txt

# Install ChromeDriver
RUN seleniumbase get chromedriver
ENV PATH="/usr/local/bin:${PATH}"

COPY . .

CMD ["tail", "-f", "/dev/null"]