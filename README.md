# Museum AI Chatbot (Heritage Guide)

A production-grade, multilingual AI chatbot designed for Indian museums. It handles ticket bookings, provides museum information (hours, parking, cafe), and supports context-aware conversations in multiple Indian languages and scripts.

## 🌟 Features

- **Multilingual Support**: Supports English and 9+ Indian languages (Hindi, Tamil, Punjabi, Bengali, Telugu, Kannada, Malayalam, Gujarati, Marathi).
- **Dual Script Recognition**: Detects and responds in both Native scripts (e.g., नमस्ते) and Romanized/Latin scripts (e.g., Namaste).
- **AI-Powered & Resilient**: Integrated with Google Gemini AI for natural conversations, with a robust rule-based fallback system for offline usage or quota limits.
- **Secure Ticketing**: In-chat ticket booking workflow with SQLite backend and unique ticket ID generation.
- **Authentication**: Secure login via Google OAuth or standard username/password with OTP verification.
- **Deployment Ready**: Fully containerized with Docker, Nginx (Reverse Proxy), and Gunicorn.

## 📁 Project Structure

| File / Directory | Description |
| :--- | :--- |
| `app.py` | Main Flask application containing routes for Auth, API, and UI. |
| `chatbot_engine.py` | Core logic for language detection, translation, and AI orchestration. |
| `database.py` | SQLite database schema and connection management. |
| `templates/` | HTML files (Chat interface, Login, Registration, OTP). |
| `static/` | CSS and JS assets for the frontend. |
| `data/museum.db` | SQLite database file (auto-generated). |
| `Dockerfile` / `docker-compose.yml` | Containerization configurations. |
| `nginx.conf` | Configuration for Nginx reverse proxy. |
| `Jenkinsfile` | CI/CD pipeline definition. |
| `test_*.py` | Comprehensive test suite for multilingual flows and engine logic. |

## 🛠️ Workflow

1.  **User Arrival**: User lands on the home page and is prompted to log in.
2.  **Authentication**: User authenticates via Google or manual registration. If manual, an OTP is sent (or logged in console in dev mode).
3.  **Chat Interaction**: 
    - The `chatbot_engine` detects the user's language and script.
    - AI (Gemini) generates a response based on strict system instructions.
    - If AI fails/is unavailable, the "Backup Brain" (Rule-based) takes over.
4.  **Booking Flow**:
    - User asks for tickets.
    - Bot presents exhibition options from the database.
    - User selects an exhibition and quantity.
    - Bot generates a "Proceed to Payment" button.
    - On success, a booking record is created and a unique hash is displayed.

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.9+
- Docker (optional)

### 2. Setup
```bash
# Clone the repository
git clone <your-repo-url>
cd CAPSTONE

# Install dependencies
pip install -r requirements.txt

# Configure environment
# Copy .env.example to .env and fill in the details
cp .env.example .env
```

### 3. Running Locally
```bash
python app.py
```
The app will be available at `http://localhost:5000`.

## 🔑 Recommended Free API Keys

To get the most out of this chatbot, you'll need an AI API key. Here are the best **free** options:

1.  **Google Gemini AI (Recommended)**
    - **Model**: Gemini 1.5 Flash
    - **How to Get**: Visit [Google AI Studio](https://aistudio.google.com/).
    - **Pros**: Very generous free tier (15 RPM / 1M TPM for Flash). Already integrated into `chatbot_engine.py`.
    
2.  **Groq API**
    - **Models**: Llama 3, Mixtral
    - **How to Get**: Sign up at [Groq Console](https://console.groq.com/).
    - **Pros**: Extremely fast inference speeds and a generous free beta tier.

3.  **Hugging Face Inference API**
    - **Models**: Thousands of open-source models.
    - **How to Get**: Create an account at [Hugging Face](https://huggingface.co/settings/tokens).
    - **Pros**: Completely free for hosted inference of many popular models.

4.  **OpenRouter**
    - **Models**: Access to dozens of providers.
    - **How to Get**: Sign up at [OpenRouter.ai](https://openrouter.ai/).
    - **Pros**: Some models are permanently free, and it provides a unified API.

---
*Created for the Museum AI Capstone Project.*
