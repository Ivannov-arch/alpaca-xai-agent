#!/bin/bash
# =====================================================================
# Oracle Cloud Always Free Deployment Script for XAI Trading Agent
# =====================================================================

set -e

echo "🚀 Starting Oracle Cloud Deployment for XAI Trading Agent..."

# 1. Update Ubuntu packages
sudo apt-get update && sudo apt-get upgrade -y

# 2. Configure Ubuntu firewall (iptables) to open ports 80, 443, 8000
echo "🔓 Configuring firewall (opening ports 80, 443, 8000)..."
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT || true
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT || true
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 8000 -j ACCEPT || true
sudo netfilter-persistent save || true

# 3. Install Docker & Docker Compose if not installed
if ! command -v docker &> /dev/null; then
    echo "🐳 Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
fi

# 4. Check for .env file
if [ ! -f .env ]; then
    echo "⚠️ .env file not found! Copying from .env.example..."
    cp .env.example .env
    echo "Please fill in your actual credentials in .env before proceeding!"
    exit 1
fi

# 5. Build and run Docker container
echo "🏗️ Building and launching Docker container 24/7..."
sudo docker compose up --build -d

echo "✅ Deployment successful! Backend is running 24/7 at http://$(curl -s ifconfig.me):8000"
echo "Health check endpoint: http://$(curl -s ifconfig.me):8000/health"
