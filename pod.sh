#!/bin/bash

# Install the libraries for the Linux-based OS
apt-get update && apt-get install -y \
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
    default-libmysqlclient-dev \
    pkg-config

# Check the installed Python version. If it is not 3.10, then install it and make it as default
if [ "$(python3 --version)" != "Python 3.10.0" ]; then
    wget https://www.python.org/ftp/python/3.10.0/Python-3.10.0.tgz \
        && tar -xvf Python-3.10.0.tgz \
        && cd Python-3.10.0 \
        && ./configure \
        && make \
        && make install \
        && cd .. \
        && rm -rf Python-3.10.0 \
        && rm Python-3.10.0.tgz \
        && update-alternatives --install /usr/bin/python3 python3 /usr/local/bin/python3.10 100 \
        && update-alternatives --install /usr/bin/pip3 pip3 /usr/local/bin/pip3.10 100
fi

# Install the Google Chrome
wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get install ./google-chrome-stable_current_amd64.deb -y --fix-missing \
    && rm google-chrome-stable_current_amd64.deb \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install PIP and Python libraries
pip install -U pip && pip install --no-cache-dir -r requirements.txt

# Install ChromeDriver
seleniumbase get chromedriver

# Add the current directory to the PATH
export PATH="/usr/local/bin:${PATH}"