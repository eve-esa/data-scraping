#!/bin/bash

# Exit on error
set -e

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
    pkg-config \
    software-properties-common

# Install Python 3.10 if not available
if ! command -v python3.10 &> /dev/null; then
    echo "Python 3.10 not found. Installing..."
    add-apt-repository -y ppa:deadsnakes/ppa
    apt-get update
    apt-get install -y python3.10 python3.10-venv python3.10-dev
fi

# Create and activate virtual environment
VENV_PATH="./venv"
if [ ! -d "$VENV_PATH" ]; then
    echo "Creating virtual environment..."
    python3.10 -m venv $VENV_PATH
fi

# Make sure we use the virtual environment - using the full path to python instead of source
export VIRTUAL_ENV=$VENV_PATH
export PATH="$VENV_PATH/bin:$PATH"

# Verify Python version
PYTHON_VERSION=$(python --version)
echo "Using Python: $PYTHON_VERSION"

# Install Google Chrome
wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get install ./google-chrome-stable_current_amd64.deb -y --fix-missing \
    && rm google-chrome-stable_current_amd64.deb \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install PIP and Python libraries in the virtual environment
$VENV_PATH/bin/python -m pip install -U pip
make sync-requirements-pod

# Install ChromeDriver
$VENV_PATH/bin/seleniumbase get chromedriver

# Add the current directory to the PATH
export PATH="/usr/local/bin:${PATH}"

echo "Setup completed successfully!"