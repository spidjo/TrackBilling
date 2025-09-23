#!/bin/bash
# TrackBilling Deployment Script with Enhanced Color Scheme
# Run as root on Ubuntu 22.04

# ------------------------------
# 0️⃣ Set variables
# ------------------------------
APP_DIR="/home/ubuntu/sgltrack"
GIT_REPO="git@github.com:spidjo/TrackBilling.git"
DOMAIN="sgltrack.com"
APP_SUBDOMAIN="app.sgltrack.com"
EMAIL=$(echo "siphiwo@sgltrack.com" | openssl enc -base64)
RUN_AS_USER="ubuntu"

# Enhanced Color Scheme - Burgundy + Teal (Option B)
PRIMARY_COLOR="#800020"      /* Rich Burgundy */
SECONDARY_COLOR="#600018"    /* Darker Burgundy */
ACCENT_COLOR="#A00028"       /* Lighter Burgundy */
TEAL_COLOR="#008080"         /* Sophisticated Teal */
LIGHT_TEAL="#E0F2F1"         /* Light Teal Background */
NAVY_BLUE="#003366"          /* Deep Navy */
LIGHT_BG="#F8F9FA"           /* Light Gray Background */
TEXT_COLOR="#2D2D2D"         /* Dark Gray Text */
WHITE="#FFFFFF"              /* White */

# ------------------------------
# 1️⃣ Update system & install base packages
# ------------------------------
apt update && apt upgrade -y
apt install -y python3-venv python3-pip build-essential libpq-dev python3-dev nginx certbot python3-certbot-nginx git

# ------------------------------
# 2️⃣ Clone or update app from GitHub as ubuntu user
# ------------------------------
if [ ! -d "$APP_DIR" ]; then
    sudo -u "$RUN_AS_USER" git clone "$GIT_REPO" "$APP_DIR"
else
    sudo -u "$RUN_AS_USER" bash -c "cd '$APP_DIR' && git reset --hard && git pull"
fi

chown -R "$RUN_AS_USER:$RUN_AS_USER" "$APP_DIR"

# ------------------------------
# 3️⃣ Create virtual environment if not exists as ubuntu user
# ------------------------------
if [ ! -d "$APP_DIR/venv" ]; then
    sudo -u "$RUN_AS_USER" python3 -m venv "$APP_DIR/venv"
fi

sudo -u "$RUN_AS_USER" bash <<EOF
source "$APP_DIR/venv/bin/activate"
pip install --upgrade pip setuptools wheel
pip install -r "$APP_DIR/requirements.txt" || pip install psycopg2-binary==2.9.10
deactivate
EOF

# ------------------------------
# 4️⃣ Create systemd service for Streamlit
# ------------------------------
cat > /etc/systemd/system/streamlit.service <<EOL
[Unit]
Description=SglTrack SaaS Billing Platform
After=network.target

[Service]
User=$RUN_AS_USER
Group=$RUN_AS_USER
WorkingDirectory=$APP_DIR
Environment=PATH=$APP_DIR/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=$APP_DIR/venv/bin/streamlit run src/main.py --server.port 8501 --server.address 127.0.0.1
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOL

systemctl daemon-reload
systemctl enable streamlit
systemctl restart streamlit
systemctl status streamlit --no-pager

# ------------------------------
# 5️⃣ Setup Nginx with Professional Landing Page (Option 2 Logo)
# ------------------------------
mkdir -p /var/www/$DOMAIN/html
mkdir -p /var/www/$DOMAIN/html/assets

# Create professional landing page HTML with enhanced color scheme
cat > /var/www/$DOMAIN/html/index.html <<EOL
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SglTrack - Enterprise SaaS Billing Platform</title>
    <meta name="description" content="Streamline your billing operations with SglTrack's comprehensive SaaS billing platform. Multi-tenant, secure, and enterprise-ready.">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        :root {
            --burgundy-primary: $PRIMARY_COLOR;
            --burgundy-secondary: $SECONDARY_COLOR;
            --burgundy-accent: $ACCENT_COLOR;
            --teal-primary: $TEAL_COLOR;
            --teal-light: $LIGHT_TEAL;
            --navy-blue: $NAVY_BLUE;
            --light-bg: $LIGHT_BG;
            --text-dark: $TEXT_COLOR;
            --white: $WHITE;
        }

        body {
            font-family: 'Inter', sans-serif;
            line-height: 1.6;
            color: var(--text-dark);
            background: linear-gradient(135deg, var(--white) 0%, var(--light-bg) 100%);
            min-height: 100vh;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 20px;
        }

        /* Enhanced Logo Styles */
        .logo-container {
            display: flex;
            align-items: center;
            gap: 12px;
            text-decoration: none;
            transition: transform 0.3s ease;
        }

        .logo-container:hover {
            transform: translateY(-2px);
        }

        .logo-icon {
            width: 45px;
            height: 45px;
            background: linear-gradient(135deg, var(--burgundy-primary), var(--teal-primary));
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;
            overflow: hidden;
            box-shadow: 0 4px 15px rgba(128, 0, 32, 0.2);
        }

        .logo-icon::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
            animation: shine 3s infinite;
        }

        @keyframes shine {
            0% { left: -100%; }
            100% { left: 100%; }
        }

        .logo-icon-inner {
            width: 25px;
            height: 25px;
            border: 2px solid white;
            border-radius: 4px;
            position: relative;
        }

        .logo-icon-inner::after {
            content: '';
            position: absolute;
            bottom: 3px;
            left: 3px;
            right: 3px;
            height: 6px;
            background: white;
            border-radius: 2px;
        }

        .logo-text {
            font-family: 'Inter', sans-serif;
            font-weight: 700;
            font-size: 1.8rem;
            background: linear-gradient(135deg, var(--burgundy-primary), var(--teal-primary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            line-height: 1;
        }

        .logo-tagline {
            font-size: 0.7rem;
            color: var(--teal-primary);
            margin-top: 2px;
            letter-spacing: 1px;
            font-weight: 500;
        }

        /* Enhanced Header */
        header {
            background: var(--white);
            box-shadow: 0 2px 20px rgba(128, 0, 32, 0.1);
            position: fixed;
            width: 100%;
            top: 0;
            z-index: 1000;
        }

        .navbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1rem 0;
        }

        .nav-links {
            display: flex;
            list-style: none;
            gap: 2rem;
        }

        .nav-links a {
            text-decoration: none;
            color: var(--text-dark);
            font-weight: 500;
            transition: all 0.3s ease;
            position: relative;
        }

        .nav-links a:hover {
            color: var(--burgundy-primary);
        }

        .nav-links a::after {
            content: '';
            position: absolute;
            bottom: -5px;
            left: 0;
            width: 0;
            height: 2px;
            background: linear-gradient(90deg, var(--burgundy-primary), var(--teal-primary));
            transition: width 0.3s ease;
        }

        .nav-links a:hover::after {
            width: 100%;
        }

        .cta-button {
            background: linear-gradient(135deg, var(--burgundy-primary), var(--teal-primary));
            color: white;
            padding: 0.75rem 1.5rem;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 600;
            transition: all 0.3s ease;
            border: none;
            box-shadow: 0 4px 15px rgba(128, 0, 32, 0.3);
        }

        .cta-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(128, 0, 32, 0.4);
        }

        /* Enhanced Hero Section */
        .hero {
            padding: 160px 0 80px;
            text-align: center;
            background: linear-gradient(135deg, var(--white) 0%, var(--teal-light) 100%);
            position: relative;
            overflow: hidden;
        }

        .hero::before {
            content: '';
            position: absolute;
            top: -50%;
            right: -10%;
            width: 300px;
            height: 300px;
            background: linear-gradient(45deg, var(--burgundy-primary), transparent);
            border-radius: 50%;
            opacity: 0.1;
        }

        .hero::after {
            content: '';
            position: absolute;
            bottom: -30%;
            left: -10%;
            width: 400px;
            height: 400px;
            background: linear-gradient(45deg, var(--teal-primary), transparent);
            border-radius: 50%;
            opacity: 0.1;
        }

        .hero-logo {
            display: inline-flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 2rem;
            padding: 1.5rem;
            background: var(--white);
            border-radius: 20px;
            box-shadow: 0 10px 40px rgba(0, 128, 128, 0.1);
            position: relative;
            z-index: 2;
        }

        .hero-logo .logo-icon {
            width: 60px;
            height: 60px;
        }

        .hero-logo .logo-icon-inner {
            width: 35px;
            height: 35px;
        }

        .hero-logo .logo-text {
            font-size: 2.5rem;
        }

        .hero-logo .logo-tagline {
            font-size: 0.9rem;
            letter-spacing: 2px;
        }

        .hero h1 {
            font-size: 3.5rem;
            font-weight: 700;
            margin-bottom: 1rem;
            background: linear-gradient(135deg, var(--burgundy-primary), var(--teal-primary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            position: relative;
            z-index: 2;
        }

        .hero p {
            font-size: 1.3rem;
            color: var(--navy-blue);
            margin-bottom: 2rem;
            max-width: 600px;
            margin-left: auto;
            margin-right: auto;
            position: relative;
            z-index: 2;
        }

        .hero-buttons {
            display: flex;
            gap: 1rem;
            justify-content: center;
            flex-wrap: wrap;
            position: relative;
            z-index: 2;
        }

        .secondary-button {
            background: transparent;
            color: var(--burgundy-primary);
            padding: 0.75rem 1.5rem;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 600;
            transition: all 0.3s ease;
            border: 2px solid var(--burgundy-primary);
        }

        .secondary-button:hover {
            background: var(--burgundy-primary);
            color: white;
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(128, 0, 32, 0.3);
        }

        /* Enhanced Features Section */
        .features {
            padding: 80px 0;
            background: var(--white);
        }

        .section-title {
            text-align: center;
            margin-bottom: 3rem;
        }

        .section-title h2 {
            font-size: 2.5rem;
            background: linear-gradient(135deg, var(--burgundy-primary), var(--teal-primary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 1rem;
        }

        .section-title p {
            color: var(--navy-blue);
            font-size: 1.1rem;
            max-width: 600px;
            margin: 0 auto;
        }

        .features-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 2rem;
            margin-top: 3rem;
        }

        .feature-card {
            background: var(--white);
            padding: 2rem;
            border-radius: 12px;
            box-shadow: 0 5px 20px rgba(0, 0, 0, 0.08);
            transition: all 0.3s ease;
            border-top: 4px solid;
            border-image: linear-gradient(135deg, var(--burgundy-primary), var(--teal-primary)) 1;
        }

        .feature-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 40px rgba(0, 128, 128, 0.15);
        }

        .feature-icon {
            font-size: 2.5rem;
            background: linear-gradient(135deg, var(--burgundy-primary), var(--teal-primary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 1rem;
        }

        .feature-card h3 {
            font-size: 1.3rem;
            margin-bottom: 1rem;
            color: var(--text-dark);
        }

        .feature-card p {
            color: #666;
            line-height: 1.6;
        }

        /* Enhanced CTA Section */
        .cta-section {
            padding: 80px 0;
            background: linear-gradient(135deg, var(--burgundy-primary), var(--navy-blue));
            color: white;
            text-align: center;
            position: relative;
            overflow: hidden;
        }

        .cta-section::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" preserveAspectRatio="none"><path d="M0,0 L100,0 L100,100 Z" fill="rgba(255,255,255,0.05)"/></svg>');
            background-size: cover;
        }

        .cta-logo {
            display: inline-flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 1.5rem;
            padding: 1rem;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 15px;
            backdrop-filter: blur(10px);
            position: relative;
            z-index: 2;
        }

        .cta-logo .logo-icon {
            width: 40px;
            height: 40px;
            background: rgba(255, 255, 255, 0.2);
        }

        .cta-logo .logo-text {
            color: white;
            font-size: 1.5rem;
            background: none;
            -webkit-text-fill-color: white;
        }

        .cta-section h2 {
            font-size: 2.5rem;
            margin-bottom: 1rem;
            position: relative;
            z-index: 2;
        }

        .cta-section p {
            font-size: 1.2rem;
            margin-bottom: 2rem;
            opacity: 0.9;
            max-width: 600px;
            margin-left: auto;
            margin-right: auto;
            position: relative;
            z-index: 2;
        }

        .cta-button-light {
            background: var(--white);
            color: var(--burgundy-primary);
            padding: 0.75rem 1.5rem;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 600;
            transition: all 0.3s ease;
            border: 2px solid var(--white);
            position: relative;
            z-index: 2;
        }

        .cta-button-light:hover {
            background: transparent;
            color: var(--white);
            transform: translateY(-2px);
        }

        /* Enhanced Footer */
        footer {
            background: var(--navy-blue);
            color: var(--white);
            padding: 3rem 0 1rem;
        }

        .footer-logo {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 1rem;
        }

        .footer-logo .logo-icon {
            width: 35px;
            height: 35px;
        }

        .footer-logo .logo-text {
            font-size: 1.3rem;
            color: white;
            background: none;
            -webkit-text-fill-color: white;
        }

        .footer-content {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 2rem;
            margin-bottom: 2rem;
        }

        .footer-column h3 {
            color: var(--white);
            margin-bottom: 1rem;
            font-size: 1.2rem;
        }

        .footer-column ul {
            list-style: none;
        }

        .footer-column ul li {
            margin-bottom: 0.5rem;
        }

        .footer-column ul li a {
            color: #ccc;
            text-decoration: none;
            transition: color 0.3s ease;
        }

        .footer-column ul li a:hover {
            color: var(--teal-primary);
        }

        .footer-bottom {
            text-align: center;
            padding-top: 2rem;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            color: #ccc;
        }

        /* Responsive Design */
        @media (max-width: 768px) {
            .navbar {
                flex-direction: column;
                gap: 1rem;
            }

            .nav-links {
                gap: 1rem;
            }

            .hero h1 {
                font-size: 2.5rem;
            }

            .hero p {
                font-size: 1.1rem;
            }

            .hero-buttons {
                flex-direction: column;
                align-items: center;
            }

            .features-grid {
                grid-template-columns: 1fr;
            }

            .logo-text {
                font-size: 1.4rem;
            }

            .logo-tagline {
                font-size: 0.6rem;
            }

            .hero-logo {
                flex-direction: column;
                gap: 10px;
                text-align: center;
            }

            .hero-logo .logo-text {
                font-size: 2rem;
            }
        }
    </style>
</head>
<body>
    <!-- Header -->
    <header>
        <div class="container">
            <nav class="navbar">
                <a href="/" class="logo-container">
                    <div class="logo-icon">
                        <div class="logo-icon-inner"></div>
                    </div>
                    <div>
                        <div class="logo-text">SglTrack</div>
                        <div class="logo-tagline">SAAS BILLING</div>
                    </div>
                </a>
                <ul class="nav-links">
                    <li><a href="#features">Features</a></li>
                    <li><a href="#about">About</a></li>
                    <li><a href="#contact">Contact</a></li>
                </ul>
                <a href="https://$APP_SUBDOMAIN" class="cta-button">
                    Launch App <i class="fas fa-arrow-right"></i>
                </a>
            </nav>
        </div>
    </header>

    <!-- Hero Section -->
    <section class="hero">
        <div class="container">
            <div class="hero-logo">
                <div class="logo-icon">
                    <div class="logo-icon-inner"></div>
                </div>
                <div>
                    <div class="logo-text">SglTrack</div>
                    <div class="logo-tagline">ENTERPRISE SAAS BILLING</div>
                </div>
            </div>
            <h1>Streamline Your Billing Operations</h1>
            <p>Comprehensive, multi-tenant SaaS billing solution. Secure, scalable, and built for modern businesses.</p>
            <div class="hero-buttons">
                <a href="https://$APP_SUBDOMAIN" class="cta-button">
                    Get Started <i class="fas fa-rocket"></i>
                </a>
                <a href="#features" class="secondary-button">
                    Learn More <i class="fas fa-book-open"></i>
                </a>
            </div>
        </div>
    </section>

    <!-- Features Section -->
    <section class="features" id="features">
        <div class="container">
            <div class="section-title">
                <h2>Powerful Features</h2>
                <p>Everything you need to manage your billing operations efficiently</p>
            </div>
            <div class="features-grid">
                <!-- Features cards remain the same -->
                <div class="feature-card">
                    <div class="feature-icon">
                        <i class="fas fa-users"></i>
                    </div>
                    <h3>Multi-Tenant Architecture</h3>
                    <p>Serve multiple clients with complete data isolation and customized billing solutions.</p>
                </div>
                <!-- ... other feature cards ... -->
            </div>
        </div>
    </section>

    <!-- CTA Section -->
    <section class="cta-section" id="about">
        <div class="container">
            <div class="cta-logo">
                <div class="logo-icon">
                    <div class="logo-icon-inner"></div>
                </div>
                <div class="logo-text">SglTrack</div>
            </div>
            <h2>Ready to Transform Your Billing?</h2>
            <p>Join hundreds of businesses that trust SglTrack for their billing operations.</p>
            <a href="https://$APP_SUBDOMAIN" class="cta-button-light">
                Start Free Trial <i class="fas fa-play-circle"></i>
            </a>
        </div>
    </section>

    <!-- Footer -->
    <footer id="contact">
        <div class="container">
            <div class="footer-content">
                <div class="footer-column">
                    <div class="footer-logo">
                        <div class="logo-icon">
                            <div class="logo-icon-inner"></div>
                        </div>
                        <div class="logo-text">SglTrack</div>
                    </div>
                    <p>Enterprise-grade SaaS billing platform designed for modern businesses.</p>
                </div>
                <!-- ... footer content ... -->
            </div>
        </div>
    </footer>

    <script>
        // JavaScript remains the same
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });

        window.addEventListener('scroll', function() {
            const header = document.querySelector('header');
            if (window.scrollY > 100) {
                header.style.background = 'rgba(255, 255, 255, 0.95)';
                header.style.backdropFilter = 'blur(10px)';
            } else {
                header.style.background = 'var(--white)';
                header.style.backdropFilter = 'none';
            }
        });
    </script>
</body>
</html>
EOL

# ... [Rest of the deployment script remains the same for Nginx, SSL, auto-update, etc.]

# Create Nginx configuration for landing page
cat > /etc/nginx/sites-available/$DOMAIN <<EOL
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;

    root /var/www/$DOMAIN/html;
    index index.html;

    access_log /var/log/nginx/$DOMAIN.access.log;
    error_log  /var/log/nginx/$DOMAIN.error.log;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;

    location / {
        try_files \$uri \$uri/ =404;
    }

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
EOL

# Streamlit app configuration
cat > /etc/nginx/sites-available/$APP_SUBDOMAIN <<EOL
server {
    listen 80;
    server_name $APP_SUBDOMAIN;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeout settings
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Block sensitive files
    location ~ /\. {
        deny all;
    }
}
EOL

# Enable sites
ln -sf /etc/nginx/sites-available/$DOMAIN /etc/nginx/sites-enabled/
ln -sf /etc/nginx/sites-available/$APP_SUBDOMAIN /etc/nginx/sites-enabled/

# Remove default nginx site
rm -f /etc/nginx/sites-enabled/default

# Test and reload Nginx
nginx -t
systemctl reload nginx

# ------------------------------
# 6️⃣ Setup SSL with Let's Encrypt
# ------------------------------
certbot --nginx -d $DOMAIN -d www.$DOMAIN -d $APP_SUBDOMAIN --redirect --non-interactive --agree-tos -m $(echo $EMAIL | openssl enc -base64 -d)

# ------------------------------
# 7️⃣ Create auto-update script
# ------------------------------
AUTO_UPDATE_SCRIPT="/usr/local/bin/trackbilling_update.sh"

cat > $AUTO_UPDATE_SCRIPT <<'EOL'
#!/bin/bash
#
# TrackBilling auto-update script
#

LOG_PREFIX="[$(date '+%a %b %d %H:%M:%S %Z %Y')]"

REPO_DIR="/home/ubuntu/sgltrack"
RUN_AS_USER="ubuntu"
VENV_DIR="$REPO_DIR/venv"

echo "$LOG_PREFIX ===== TrackBilling update started ====="

if [ ! -d "$REPO_DIR/.git" ]; then
    echo "$LOG_PREFIX ❌ Repo not found at $REPO_DIR"
    exit 1
fi

sudo -u "$RUN_AS_USER" bash <<EOF
cd "$REPO_DIR" || exit 1
chown -R $RUN_AS_USER:$RUN_AS_USER "$REPO_DIR"

git fetch origin main

LOCAL=\$(git rev-parse HEAD)
REMOTE=\$(git rev-parse origin/main)

if [ "\$LOCAL" != "\$REMOTE" ]; then
    echo "$LOG_PREFIX 🔄 Updating repository..."
    git reset --hard origin/main

    if [ -f "$VENV_DIR/bin/activate" ]; then
        source "$VENV_DIR/bin/activate"
        pip install --quiet --break-system-packages -r requirements.txt
        echo "$LOG_PREFIX 📦 Dependencies installed"
    else
        echo "$LOG_PREFIX ⚠️ Virtualenv not found at $VENV_DIR"
    fi

    # Restart Streamlit (passwordless sudo required)
    sudo systemctl restart streamlit.service
    echo "$LOG_PREFIX ✅ Streamlit service restarted successfully"
else
    echo "$LOG_PREFIX ⏩ No updates found. Nothing to do."
fi
EOF

echo "$LOG_PREFIX ===== TrackBilling update completed ====="
EOL

chmod +x $AUTO_UPDATE_SCRIPT

# ------------------------------
# 8️⃣ Setup cron job to auto-update every 5 minutes
# ------------------------------
sudo -u "$RUN_AS_USER" bash -c "(crontab -l 2>/dev/null; echo '*/5 * * * * /usr/local/bin/trackbilling_update.sh >> /var/log/trackbilling_update.log 2>&1') | crontab -"

# ------------------------------
# 9️⃣ Set proper permissions
# ------------------------------
chown -R www-data:www-data /var/www/$DOMAIN
chmod -R 755 /var/www/$DOMAIN

touch /var/log/trackbilling_update.log
chown "$RUN_AS_USER:$RUN_AS_USER" /var/log/trackbilling_update.log
chmod 644 /var/log/trackbilling_update.log

if ! grep -q "ubuntu ALL=(root) NOPASSWD: /bin/systemctl restart streamlit.service" /etc/sudoers; then
    echo "ubuntu ALL=(root) NOPASSWD: /bin/systemctl restart streamlit.service" >> /etc/sudoers.d/trackbilling
    chmod 440 /etc/sudoers.d/trackbilling
fi

echo "✅ Deployment completed with Option 2 Logo!"
echo "🎯 Landing page: https://$DOMAIN"
echo "🚀 App: https://$APP_SUBDOMAIN"
echo "👤 Running as user: $RUN_AS_USER"
echo "🎨 Option 2 Logo integrated throughout the site"
echo "✨ Features: Animated icon, responsive design, burgundy color scheme"