# 🏛️ Museum AI Chatbot (Heritage Guide)

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/framework-flask-orange.svg)](https://flask.palletsprojects.com/)
[![Gemini AI](https://img.shields.io/badge/AI-Google%20Gemini-green.svg)](https://aistudio.google.com/)
[![Deployment-Ready](https://img.shields.io/badge/deploy-Docker%20%2F%20Render-blue.svg)](https://render.com/)

A production-grade, multilingual AI chatbot designed for Indian museums. This Capstone project integrates cutting-edge Generative AI with a robust rule-based fallback system to handle ticket bookings, historical guidance, and museum logistics in multiple Indian languages and scripts.

---

## 🌟 Key Features

### 🧠 Dual-Brain Architecture
*   **Primary Brain**: Integrated with **Google Gemini 1.5 Flash/Pro** for natural, context-aware conversations.
*   **Backup Brain**: A high-speed, rule-based engine that handles common queries (`hours`, `parking`, `tickets`) even if the AI API is offline or quota-limited.

### 🌐 Polyglot & Script-Pure
*   **10-Language Support**: English, Hindi, Tamil, Punjabi, Bengali, Telugu, Kannada, Malayalam, Gujarati, and Marathi.
*   **Script Consistency**: Automatically detects and responds in both **Native script** (e.g., नमस्ते) and **Romanized/Latin script** (e.g., Namaste) based on user input.
*   **Session-Locking**: Once a language is detected, the session locks to that language for consistent UI/UX.

### 🎫 Interactive Ticketing Workflow
*   **Linear Booking**: A state-driven conversation flow (`Choice` → `Quantity` → `Payment`).
*   **Ledger Integration**: Generates unique booking hashes and integrates with a simulated secure payment gateway.
*   **E-Ticket Generation**: Users can download a "Modern E-Ticket" directly after booking.

### 🔒 Enterprise-Grade Security
*   **Dual Auth**: Secure login via **Google OAuth 2.0** or traditional Email/Password.
*   **OTP Verification**: Multi-factor authentication via Gmail/SendGrid with a **Fail-Safe Logging** system for production reliability.

---

## 📁 Project Architecture

| File / Directory | Role |
| :--- | :--- |
| `app.py` | Main Flask entry point; handles Auth, API routes, and Session management. |
| `chatbot_engine.py` | The "Core"; contains AI orchestration, language detection, and state logic. |
| `database.py` | Schema definitions and SQLite connection pooling. |
| `templates/` | Jinja2 templates for the chat interface, Login, Register, and OTP pages. |
| `static/` | Premium CSS (Glassmorphism) and Vanilla JS (Chat UI logic). |
| `Dockerfile` | Multi-stage build for production-ready containerization. |
| `nginx.conf` | Reverse proxy configuration for SSL and security headers. |
| `Jenkinsfile` | CI/CD pipeline for automated testing and deployment. |

---

## 🛠️ Deployment & Production Hardening

The application is optimized for **Render.com** and high-availability environments:

1.  **ProxyFix Middleware**: Correctly handles `X-Forwarded-Proto` for HTTPS redirects.
2.  **SMTP Fail-Safe**: If an email provider fails, the OTP is automatically logged to the server console (`[FAIL-SAFE] OTP: 123456`) so developers can assist users in real-time.
3.  **AI Smoke Tests**: On startup, the engine performs a "Smoke Test" to verify and select the best available model from a prioritized list (`Gemini 1.5 Flash`, `Gemini 1.5 Flash-8b`, etc.).
4.  **429 Resilience**: Intelligent retry logic with exponential backoff for AI rate limits.

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.9 or higher
- A Google AI Studio API Key ([Get it here](https://aistudio.google.com/))
- Google Cloud OAuth Credentials (Optional but recommended)

### 2. Manual Installation
```bash
# Clone the repository
git clone <your-repo-url>
cd CAPSTONE

# Set up virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure Environment
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

### 3. Running with Docker
```bash
docker-compose up --build
```

---

## 🔑 Environment Variables

| Variable | Description |
| :--- | :--- |
| `GEMINI_API_KEY` | Your Google AI Studio key (FREE). |
| `GOOGLE_CLIENT_ID` | OAuth Client ID from Google Cloud Console. |
| `GOOGLE_CLIENT_SECRET` | OAuth Client Secret. |
| `MAIL_USERNAME` | SMTP Email (Gmail recommended). |
| `MAIL_PASSWORD` | Gmail App Password (NOT your normal password). |
| `SECRET_KEY` | A long random string for session encryption. |

---

## 🛠️ Diagnostic Tools
*   **Model Checker**: Run `python check_models.py` to see which Gemini models are active on your key.
*   **OAuth Debugger**: Visit `/debug-url` on your hosted app to verify Redirect URIs.

---
*Created as part of the Museum AI Capstone Project.*
