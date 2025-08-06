# 🚀 TrackBilling

**TrackBilling** is a modern, multi-tenant SaaS billing platform designed to handle complex usage-based billing, automated invoicing, and tenant-aware analytics across industries including Telecom, SaaS, Logistics, Cloud, and Fintech.

![TrackBilling Banner](assets/trackbilling-banner.png)

---

## 🌟 Features

- 🧾 Multi-metric usage tracking (API calls, seats, data, etc.)
- 💳 Automated billing and invoice generation
- 🏢 Multi-tenant architecture with company/tenant isolation
- 📊 Dashboards for SuperAdmin, Admins, and Clients
- 🔐 Role-based login with email verification & CAPTCHA 
- 📥 CSV upload for usage data
- 📤 PDF invoice preview/download + email delivery
- 📈 ARPU, churn rate, plan uptake reports
- 🛡️ Login rate limiting + password reset + email verification
- ☁️ Ready for Streamlit Cloud & Docker/VPS deployment

---

## 🚧 MVP Roadmap

- [x] Authentication + role-based access
- [x] Tenant & plan management
- [x] Usage upload + metric limits
- [x] Billing engine + invoice PDF
- [x] Notifications + dashboards
- [ ] Bug sweep & final edge case testing
- [ ] MVP Deployment on Streamlit Cloud

---

## 🔧 Tech Stack

- **Frontend/UI**: Streamlit
- **Backend**: Python, SQLite (PostgreSQL planned)
- **Auth**: JWT, Email Verification, reCAPTCHA
- **PDF**: ReportLab
- **Deployment**: Streamlit Cloud → Docker/VPS (NGINX)

---

## 📂 Folder Structure

```bash
📦 src/ # Main application code
│ ├── views/ # Streamlit page views (auth, billing, usage)
│ ├── auth/ # Authentication & token management
│ ├── utils/ # Helper functions (PDF, email, etc.)
│ └── db/ # DB connection and queries
│
├── assets/ # Demo assets, templates, logos
├── .streamlit/ # Streamlit config and secrets
├── .env.example # Example environment config
├── requirements.txt # Python dependencies
├── Dockerfile # Container setup (for future VPS deploy)
├── docker-compose.yml
├── nginx.conf # Nginx reverse proxy (optional)
├── README.md # Project documentation
└── LICENSE



---

## ⚙️ Installation

```bash
git clone https://github.com/yourusername/saas-billing-platform.git
cd saas-billing-platform
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt

streamlit run src/main.py

