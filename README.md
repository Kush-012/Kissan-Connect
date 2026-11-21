# Kisan Connect

**Agricultural Management & Wholesale Price Discovery Platform with Integrated Groq AI Assistant ("Kisan AI")**

Kisan Connect is a modern full-stack web application designed to bridge the gap between verified Indian farmers, agricultural officers, and commercial buyers (food processors, millers, traders, and wholesalers).

---

## Key Features

1. **Direct Farm-to-Buyer Trade**:
   - Verified farmer profiles with district-level agricultural landholding mapping.
   - Seasonal crop registry (Kharif, Rabi, Zaid, Annual) with planted acreage, harvest dates, and yield estimates.
   - Commercial buyers can place direct purchase enquiries with custom bid rates and quantities.

2. **Market Crop Prices (APMC Benchmark Integration)**:
   - Integration with Government of India wholesale market prices (`data.gov.in`).
   - Searchable and filterable by commodity, state, and district.
   - Automated server-side caching (300s TTL) for high-performance price discovery.

3. **Kisan AI (Groq-Powered LLM Assistant)**:
   - Floating circular conversational assistant on the bottom-right corner.
   - Powered by Groq Cloud API (`openai/gpt-oss-120b`).
   - Dynamically grounded in live database inventory (available crops, registered farmers, prices).
   - Strict domain guardrails preventing off-topic responses.

4. **Role-Based Access Control (RBAC)**:
   - **Operator**: Registers farmers, adds crop listings, manages buyer accounts, and approves/rejects enquiries.
   - **Buyer**: Self-registers, browses verified crop listings, submits purchase enquiries, and tracks order status.

---

## Tech Stack

- **Backend**: Python 3.13, Django 6.1
- **Database**: SQLite3
- **AI / LLM**: Groq Cloud API (`groq` Python SDK)
- **External API**: Open Government Data (`data.gov.in`) APMC Mandi Price API
- **Frontend**: Django Templates, HTML5, CSS3, JavaScript (Fetch API + CSRF)

---

## Getting Started

### 1. Clone the Repository
```bash
git clone https://github.com/Kush-012/Kissan-Connect.git
cd Kissan-Connect
```

### 2. Set Up Virtual Environment & Dependencies
```bash
python -m venv venv
venv\Scripts\activate   # On Windows
# source venv/bin/activate  # On macOS/Linux

pip install django django-allauth groq requests
```

### 3. Environment Variables
Copy `.env.example` to `.env` and configure your API keys:
```bash
cp .env.example .env
```
Set your `GROQ_API_KEY`:
```bash
export GROQ_API_KEY="your-groq-api-key"   # Linux/macOS
# $env:GROQ_API_KEY="your-groq-api-key"   # PowerShell
```

### 4. Database Migrations
```bash
python manage.py migrate
```

### 5. Run the Server
```bash
python manage.py runserver
```
Visit `http://127.0.0.1:8000/` in your browser.

---

## Security & Privacy Note
- Sensitive credentials (Google OAuth 2.0 keys, Groq API keys, and local SQLite databases) are excluded via `.gitignore`.
- Provide keys via environment variables or Django Admin before deploying to production.
