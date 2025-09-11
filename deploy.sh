#!/bin/bash
# TrackBilling Deployment Script with GitHub Auto-Update
# Run as root on Ubuntu 22.04

# ------------------------------
# 0️⃣ Set variables
# ------------------------------
APP_DIR="/root/sgltrack"
GIT_REPO="git@github.com:spidjo/TrackBilling.git"  # Replace with your repo
DOMAIN="sgltrack.com"
APP_SUBDOMAIN="app.sgltrack.com"
EMAIL=$(echo "siphiwolum@gmail.com" | openssl enc -base64)  # Encrypted email (base64)

# ------------------------------
# 1️⃣ Update system & install base packages
# ------------------------------
apt update && apt upgrade -y
apt install -y python3-venv python3-pip build-essential libpq-dev python3-dev nginx certbot python3-certbot-nginx git

# ------------------------------
# 2️⃣ Clone or update app from GitHub
# ------------------------------
if [ ! -d "$APP_DIR" ]; then
    git clone "$GIT_REPO" "$APP_DIR"
else
    cd "$APP_DIR"
    git reset --hard
    git pull
fi

cd "$APP_DIR"

# ------------------------------
# 3️⃣ Create virtual environment if not exists
# ------------------------------
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate

# Upgrade pip and setuptools
pip install --upgrade pip setuptools wheel

# Install requirements
pip install -r requirements.txt || pip install psycopg2-binary==2.9.10

deactivate

# ------------------------------
# 4️⃣ Create systemd service for Streamlit
# ------------------------------
cat > /etc/systemd/system/streamlit.service <<EOL
[Unit]
Description=TrackBilling Streamlit App
After=network.target

[Service]
User=root
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/venv/bin/streamlit run src/main.py --server.port 8501 --server.address 127.0.0.1
Restart=always

[Install]
WantedBy=multi-user.target
EOL

# Enable & start service
systemctl daemon-reload
systemctl enable streamlit
systemctl restart streamlit
systemctl status streamlit --no-pager

# ------------------------------
# 5️⃣ Setup Nginx reverse proxy
# ------------------------------
# Landing page
mkdir -p /var/www/$DOMAIN/html
echo "<h1>Welcome to $DOMAIN 🚀</h1>" > /var/www/$DOMAIN/html/index.html

cat > /etc/nginx/sites-available/$DOMAIN <<EOL
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;

    root /var/www/$DOMAIN/html;
    index index.html;

    access_log /var/log/nginx/$DOMAIN.access.log;
    error_log  /var/log/nginx/$DOMAIN.error.log;

    location / {
        try_files \$uri \$uri/ =404;
    }
}
EOL

# Streamlit app
cat > /etc/nginx/sites-available/$APP_SUBDOMAIN <<EOL
server {
    listen 80;
    server_name $APP_SUBDOMAIN;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOL

# Enable sites
ln -sf /etc/nginx/sites-available/$DOMAIN /etc/nginx/sites-enabled/
ln -sf /etc/nginx/sites-available/$APP_SUBDOMAIN /etc/nginx/sites-enabled/

# Test and reload Nginx
nginx -t
systemctl reload nginx

# ------------------------------
# 6️⃣ Setup SSL with Let's Encrypt
# ------------------------------
certbot --nginx -d $DOMAIN -d www.$DOMAIN -d $APP_SUBDOMAIN --redirect --non-interactive --agree-tos -m $EMAIL

# ------------------------------
# 7️⃣ Create auto-update script
# ------------------------------
AUTO_UPDATE_SCRIPT="/usr/local/bin/trackbilling_update.sh"

cat > $AUTO_UPDATE_SCRIPT <<EOL
#!/bin/bash
cd $APP_DIR
git reset --hard
git pull
source $APP_DIR/venv/bin/activate
pip install -r requirements.txt || pip install psycopg2-binary==2.9.10
deactivate
systemctl restart streamlit
EOL

chmod +x $AUTO_UPDATE_SCRIPT

# ------------------------------
# 8️⃣ Setup cron job to auto-update every hour
# ------------------------------
(crontab -l 2>/dev/null; echo "0 * * * * $AUTO_UPDATE_SCRIPT >> /var/log/trackbilling_update.log 2>&1") | crontab -

echo "✅ Deployment & auto-update setup completed!"
echo "Landing page: https://$DOMAIN"
echo "App: https://$APP_SUBDOMAIN"
echo "Auto-update cron job running every hour"
