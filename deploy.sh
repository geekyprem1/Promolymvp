#!/bin/bash
# Promoly — Full Auto Deploy Script
# Run on fresh Ubuntu 22.04 VM:
#   curl -fsSL https://raw.githubusercontent.com/geekyprem1/Promolymvp/master/deploy.sh | bash

set -e
REPO="https://github.com/geekyprem1/Promolymvp.git"
APP_DIR="$HOME/Promolymvp"
BACKEND_PORT=8001

echo ""
echo "=========================================="
echo "  PROMOLY DEPLOY SCRIPT"
echo "=========================================="
echo ""

# ── 1. System packages ────────────────────────────────────────────────────────
echo "[1/8] Installing system packages..."
sudo apt-get update -qq
sudo apt-get install -y -qq \
    python3.10 python3-pip python3-venv \
    git ffmpeg nginx curl wget \
    ca-certificates gnupg lsb-release \
    libglib2.0-0 libnss3 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2

# ── 2. Node.js 18 ─────────────────────────────────────────────────────────────
echo "[2/8] Installing Node.js 18..."
if ! command -v node &>/dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash - -qq
    sudo apt-get install -y nodejs
fi
sudo npm install -g pm2 --quiet

# ── 3. Clone / update repo ────────────────────────────────────────────────────
echo "[3/8] Cloning repository..."
if [ -d "$APP_DIR/.git" ]; then
    cd "$APP_DIR" && git pull origin master
else
    git clone "$REPO" "$APP_DIR"
fi

# ── 4. Backend setup ──────────────────────────────────────────────────────────
echo "[4/8] Setting up Python backend..."
cd "$APP_DIR/backend"
python3 -m venv venv
source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt
playwright install chromium
playwright install-deps chromium

# .env file
if [ ! -f ".env" ]; then
    echo ""
    echo "⚠  OpenRouter API key daalo (sk-or-v1-...):"
    read -r ORKEY
    echo "OPENROUTER_API_KEY=$ORKEY" > .env
    echo "GEMINI_API_KEY=$ORKEY"    >> .env
    echo ".env created ✓"
fi

# ── 5. Frontend build ─────────────────────────────────────────────────────────
echo "[5/8] Building frontend..."
cd "$APP_DIR/frontend"
npm install --quiet
npm run build

# ── 6. Remotion build ────────────────────────────────────────────────────────
echo "[6/8] Setting up Remotion..."
cd "$APP_DIR/remotion"
npm install --quiet

# ── 7. PM2 — start backend ───────────────────────────────────────────────────
echo "[7/8] Starting backend with PM2..."
cd "$APP_DIR/backend"
source venv/bin/activate
pm2 delete promoly-backend 2>/dev/null || true
pm2 start main.py \
    --name promoly-backend \
    --interpreter "$APP_DIR/backend/venv/bin/python3" \
    --cwd "$APP_DIR/backend"
pm2 save
sudo env PATH="$PATH:/usr/bin" pm2 startup systemd -u "$USER" --hp "$HOME" 2>/dev/null || true

# ── 8. Nginx config ───────────────────────────────────────────────────────────
echo "[8/8] Configuring Nginx..."
EXTERNAL_IP=$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
USERNAME=$(whoami)

sudo tee /etc/nginx/sites-available/promoly > /dev/null <<NGINXCONF
server {
    listen 80;
    server_name $EXTERNAL_IP _;

    client_max_body_size 50M;

    # Frontend — React build
    root $APP_DIR/frontend/dist;
    index index.html;

    # API + static files → FastAPI backend
    location ~ ^/(generate|progress|output|screenshots|assets|templates|styles|health|test-voice) {
        proxy_pass http://127.0.0.1:$BACKEND_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
        proxy_buffering off;
    }

    # SPA fallback
    location / {
        try_files \$uri \$uri/ /index.html;
    }
}
NGINXCONF

sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -sf /etc/nginx/sites-available/promoly /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl restart nginx
sudo systemctl enable nginx

echo ""
echo "=========================================="
echo "  DEPLOY COMPLETE!"
echo "=========================================="
echo ""
echo "  App URL:    http://$EXTERNAL_IP"
echo "  PM2 logs:   pm2 logs promoly-backend"
echo "  Nginx logs: sudo tail -f /var/log/nginx/error.log"
echo ""
