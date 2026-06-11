#!/bin/bash
# Promoly — Quick Update Script (code changes deploy karne ke liye)
# Run: bash ~/Promolymvp/update.sh

set -e
APP_DIR="$HOME/Promolymvp"

echo "[1/3] Pulling latest code..."
cd "$APP_DIR" && git pull origin master

echo "[2/3] Rebuilding frontend..."
cd "$APP_DIR/frontend"
npm install --quiet
npm run build

echo "[3/3] Restarting backend..."
cd "$APP_DIR/backend"
source venv/bin/activate
pip install -q -r requirements.txt
pm2 restart promoly-backend

echo ""
echo "Update complete! http://$(curl -s ifconfig.me 2>/dev/null)"
