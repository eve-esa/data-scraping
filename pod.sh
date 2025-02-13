#!/bin/bash

# Exit on error
set -e

# Install basic system dependencies
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
    pkg-config \
    software-properties-common \
    python3-apt

# Check if Python 3.10 is already installed
if ! command -v python3.10 &> /dev/null; then
    echo "Python 3.10 not found. Installing..."
    # Install Python 3.10
    add-apt-repository -y ppa:deadsnakes/ppa
    apt-get update
    apt-get install -y python3.10 python3.10-dev python3.10-distutils

    # Make Python 3.10 the default
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1
    update-alternatives --set python3 /usr/bin/python3.10

    # Install pip for Python 3.10
    curl -sS https://bootstrap.pypa.io/get-pip.py | python3.10
else
    echo "Python 3.10 is already installed"
fi

# Verify Python version
PYTHON_VERSION=$(python3 --version)
echo "Using Python: $PYTHON_VERSION"

# Install Google Chrome
wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get install ./google-chrome-stable_current_amd64.deb -y --fix-missing \
    && rm google-chrome-stable_current_amd64.deb

# Install Python requirements
python3 -m pip install -U pip
python3 -m pip install --no-cache-dir -r requirements.txt

# Install ChromeDriver
seleniumbase get chromedriver

# Add the current directory to the PATH
export PATH="/usr/local/bin:${PATH}"

# Clean up
apt-get clean && rm -rf /var/lib/apt/lists/*

echo "Setup completed successfully!"