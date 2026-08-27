# 🏢 BANCre — AI-Powered Commercial Real Estate Financing & Loan Marketplace

Welcome to the **BANCre Backend** repository. BANCre is an institutional-grade platform designed for the **Commercial Real Estate (CRE)** industry. It bridges the gap between **Property Sponsors (Borrowers)** and **Lenders (Banks, Private Debt Funds, Capital Providers)** by combining automated loan request workflows, quote bidding, AI-driven Offering Memorandum (OM) generation, and contextual document analysis.

---

## 🌟 High-Level Platform Architecture

```
                                  ┌────────────────────────────────┐
                                  │      BANCre REST API Core      │
                                  │  (Django 6.1 + DRF + JWT Auth) │
                                  └───────────────┬────────────────┘
                                                  │
         ┌────────────────────────┬───────────────┴───────────────┬────────────────────────┐
         │                        │                               │                        │
         ▼                        ▼                               ▼                        ▼
┌──────────────────┐    ┌──────────────────┐            ┌──────────────────┐    ┌──────────────────┐
│  accounts (Auth) │    │ properties (CRE) │            │   loan (Quotes)  │    │  notifications   │
│  - Dual Roles    │    │ - Asset profiles │            │ - Loan requests  │    │ - In-app alerts  │
│  - Zero-query    │    │ - Document files │            │ - Automated DSCR │    │ - Branded HTML   │
│  - Email OTP     │    │ - Map markers    │            │ - Atomic accept  │    │   email engine   │
└──────────────────┘    └─────────┬────────┘            └──────────────────┘    └──────────────────┘
                                  │
         ┌────────────────────────┴────────────────────────┐
         │                                                 │
         ▼                                                 ▼
┌─────────────────────────────────┐               ┌─────────────────────────────────┐
│        memorandums (AI)         │               │          chatbot (AI)           │
│  - Anthropic Claude OM engine   │               │  - OpenAI property assistant    │
│  - Parallel section synthesis   │               │  - Conversation history         │
│  - Dynamic underwriting tables  │               │  - Celery background processing │
└─────────────────────────────────┘               └─────────────────────────────────┘
```

---

## 🚀 Key Modules & Features

### 1. 👥 Accounts & Dual-Role System (`accounts/`)
* **Dual Roles Out-of-the-Box:** Every user can hold both `Sponsor` (borrower) and `Lender` (financier) capabilities.
* **Zero-Query Role Switching:** User's active state is stored in `user.active_role`. Role checks hit in-memory cache first, eliminating redundant SQL queries.
* **Enterprise Security:** JWT authentication with token blacklisting on logout, email OTP verification for signup, and secure password resets.

### 2. 🏢 Commercial Properties & Document Vault (`properties/`)
* **Property Asset Tracking:** Detailed CRE metrics (occupancy rates, rentable square footage, unit counts, parking spaces, year built/renovated).
* **Document Vault:** Upload, categorize, and serve leases, rent rolls, appraisal reports, and property photography.
* **Google Places Integration & AI Auto-fill:** Validates map addresses and automatically derives property metrics using Claude AI.

### 3. 📄 AI Offering Memorandum (OM) Generator (`memorandums/`)
* **Automated Institutional Reports:** Generates publication-grade investment memorandums directly from uploaded property documents and property metrics.
* **Parallel Synthesis:** Uses concurrent worker threads to synthesize executive summaries, location/market analyses, financial operating statements, and underwriting tables simultaneously.
* **Full Editor Lifecycle:** Allows sponsors to review sections in `Draft` mode, manually tweak text, regenerate individual sections, and transition to `Published` for lenders to inspect.

### 4. 💼 Loan Requests & Competitive Quote Marketplace (`loan/`)
* **Loan Financing Requests:** Sponsors specify their financing targets (Requested Amount, Loan Term, Target LTV).
* **Lender Marketplace & Map Isolation:** Lenders view all active loan requests in the marketplace or on an interactive map. Self-quoting and viewing one's own properties in the marketplace are strictly prevented.
* **Rich Financing Quotes:** Lenders submit formal quotes (Interest Rate, Max LTV, Debt Yield, Initial/Future Funding, Origination Fees, Reserve Funds).
* **Automated DSCR Underwriting:** DSCR (Debt Service Coverage Ratio) is automatically computed on quote creation based on Debt Yield and Annual Debt Service.
* **Atomic Deal Resolution:** Accepting a quote updates its status to `Accepted`, closes the loan request, and declines all competing quotes in a single atomic database transaction.

### 5. 🔔 Decoupled Notifications & Branded Emails (`notifications/`)
* **Event-Driven Signals:** Signals listen to loan requests, quotes, and memorandum status changes without creating hard foreign keys.
* **HTML Email Engine:** Beautiful, branded transactional emails extending `emails/base.html` with status-colored badges and data tables.
* **User Preferences:** Users can toggle email alerts on/off per event category (`email_on_new_quote`, `email_on_quote_accepted`, etc.).

### 6. 🤖 Property Assistant Chatbot (`chatbot/`)
* **Property-Specific Conversations:** Ask questions about specific properties or general real estate topics.
* **Asynchronous AI Tasks:** Heavy LLM queries run via Celery worker with Redis broker, keeping response times instant.

---

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| **Language** | Python 3.12+ |
| **Framework** | Django 6.1 & Django REST Framework 3.18 |
| **Authentication** | `djangorestframework-simplejwt` (with token blacklisting) |
| **Database** | PostgreSQL 16 (with SQLite fallback) via `psycopg2-binary` |
| **Task Queue & Cache** | Celery 5.6 & Redis |
| **AI LLM Engines** | Anthropic Claude (`anthropic`) & OpenAI (`openai`) |
| **NLP & Vectors** | `sentence-transformers`, `faiss-cpu`, `scikit-learn` |
| **Admin UI** | Django Unfold Admin Theme |
| **Documentation** | Swagger UI (`/docs/`) & ReDoc (`/redoc/`) via `drf-yasg` |

---

## ⚡ Quick Start & Setup Guide

### 1. Clone & Activate Virtual Environment

```bash
# Clone the repository
git clone <repository-url>
cd BANCre

# Create virtual environment (Python 3.12)
python -m venv .venv

# Activate environment
# On Windows (PowerShell):
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

### 2. Configure Environment Variables (`.env`)

Create or update `.env` in the project root:

```env
# Django Core Settings
SECRET_KEY=your-secure-django-secret-key
DEBUG=True
ALLOWED_HOSTS=*,localhost,127.0.0.1,.ngrok-free.app,.ngrok-free.dev,.ngrok.io

# PostgreSQL Configuration
DB_ENGINE=django.db.backends.postgresql
DB_NAME=bancre_db
DB_USER=postgres
DB_PASSWORD=your_postgres_password
DB_HOST=localhost
DB_PORT=5432

# CORS & CSRF Settings
CORS_ALLOW_ALL_ORIGINS=False
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000,http://127.0.0.1:8000
CSRF_TRUSTED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000,http://127.0.0.1:8000,https://*.ngrok-free.app,https://*.ngrok-free.dev,https://*.ngrok.io

# SMTP Email Settings
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
COMPANY_LOGO_URL=https://i.ibb.co.com/dw1P2S9K/BANCre.webp

# AI API Keys
OPENAI_API_KEY=your-openai-api-key
CLAUDE_API_KEY=your-claude-api-key
```

---

### 3. Start PostgreSQL & Redis (Docker)

If using Docker, start both database and message broker with one command:

```bash
docker-compose up -d
```

---

### 4. Run Migrations & Create Admin User

```bash
# Apply database migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

---

### 5. Start Background Workers & Dev Server

**Terminal 1 (Celery Worker):**
```bash
# Windows:
celery -A config worker -l info --pool=solo

# Linux / Production:
celery -A config worker -l info --concurrency=4
```

**Terminal 2 (Django Server):**
```bash
python manage.py runserver
```

---

## 📡 API Endpoints Reference

### 🔐 Authentication (`/auth/`)
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/auth/signup/` | Register account & trigger OTP |
| `POST` | `/auth/verify-email/` | Verify signup OTP |
| `POST` | `/auth/login/` | Login & receive JWT pair |
| `POST` | `/auth/logout/` | Blacklist refresh token & logout |
| `POST` | `/auth/token/refresh/` | Refresh access token |
| `POST` | `/auth/switch-role/` | Switch active context (Sponsor / Lender) |
| `GET/PATCH` | `/auth/profile/` | View or update profile (JSON & photo support) |

### 🏢 Properties (`/api/v1/properties/`)
| Method | Endpoint | Description |
|---|---|---|
| `GET/POST` | `/api/v1/properties/` | List sponsor properties / Create property |
| `GET/PATCH/DELETE` | `/api/v1/properties/<id>/` | Property detail, update, delete |
| `GET` | `/api/v1/properties/map/` | Lender map pins of all active properties |
| `POST` | `/api/v1/properties/places/` | Validate Google Place & auto-derive metrics |
| `POST` | `/api/v1/properties/<id>/files/` | Upload leases, rent rolls, appraisal PDFs |

### 💼 Loans & Quotes (`/api/v1/loans/`)
| Method | Endpoint | Description |
|---|---|---|
| `GET/POST` | `/api/v1/loans/requests/` | Sponsor: own requests. Lender: marketplace |
| `GET/PATCH/DELETE` | `/api/v1/loans/requests/<id>/` | Loan request detail with docs & memorandums |
| `GET/POST` | `/api/v1/loans/requests/<id>/quotes/` | List quotes on request / Submit formal quote |
| `GET` | `/api/v1/loans/quotes/` | Lender: all submitted quotes |
| `GET/PATCH` | `/api/v1/loans/quotes/<quote_id>/` | Quote detail / Update (if Submitted) |
| `POST` | `/api/v1/loans/quotes/<quote_id>/accept/` | Sponsor: accept quote (atomic deal closing) |
| `POST` | `/api/v1/loans/quotes/<quote_id>/decline/` | Sponsor: decline quote |
| `GET` | `/api/v1/loans/dashboard/sponsor/` | Sponsor financing KPIs & activity stats |
| `GET` | `/api/v1/loans/dashboard/lender/` | Lender pipeline stats & quote analytics |

### 📄 AI Memorandums (`/api/v1/memorandums/`)
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/memorandums/` | List sponsor memorandums |
| `POST` | `/api/v1/memorandums/generate/` | Trigger AI Offering Memorandum generation |
| `GET/PATCH/DELETE` | `/api/v1/memorandums/<id>/` | View memo with sections / Publish memo |
| `PATCH` | `/api/v1/memorandums/sections/<id>/` | Edit section text content |
| `POST` | `/api/v1/memorandums/sections/<id>/regenerate/` | Regenerate specific section with AI |

### 🔔 Notifications (`/api/v1/notifications/`)
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/notifications/` | List notifications (filter by `?is_read=false`) |
| `GET` | `/api/v1/notifications/unread-count/` | Unread count badge indicator |
| `PATCH` | `/api/v1/notifications/<id>/read/` | Mark single notification as read |
| `PATCH` | `/api/v1/notifications/read-all/` | Mark all notifications as read |
| `GET/PATCH` | `/api/v1/notifications/preferences/` | View or toggle email notification preferences |

---

## 🧪 Running Tests

To run the comprehensive test suite across all active apps:

```bash
python manage.py test notifications loan chatbot properties memorandums accounts
```

---

## 🏛️ Engineering & Architecture Decisions

1. **Lazy ML Model Loading:** Heavy NLP dependencies (`SentenceTransformer`, `torch`) load lazily upon the first memorandum extraction task rather than during Django server boot, keeping startup time under ~0.5s.
2. **Atomic Quote Resolution:** Accepts quotes using `transaction.atomic()` to guarantee that accepting one quote, closing the request, and declining competing quotes all happen in a single, safe DB transaction.
3. **Decoupled Cross-App Signals:** The `notifications` app listens to model events via string references (`'loan.LoanRequest'`) to eliminate circular dependencies.
4. **Dual-Mode Root Endpoint (`/`):** Visiting `/` in a browser renders a high-end status dashboard, while API clients receive structured JSON telemetry.

---

## 📄 License
Private & Proprietary. All rights reserved by **BANCre**.
