# AI Email Classification & Auto-Response System

> End-to-end intelligent email processing — classifies intent in real time, generates context-aware replies, and runs 24/7 without human intervention.

---

## 🎯 What it does

Enterprises receive hundreds of emails daily requiring categorization and response. This system automates the full pipeline: UiPath robots monitor the inbox, pass emails to a FastAPI + LLM backend for classification, generate appropriate responses, and send them — all automatically.

---

## 🔄 Architecture

```
Email Inbox (IMAP)
    ↓
UiPath Robot (EmailMonitor) — email monitoring + triggering
    ↓
FastAPI Backend — receives email content via REST API
    ↓
OLLAMA Llama 3 — intent detection + category tagging
    ↓
Response Generator — context-aware reply using LLM
    ↓
JSON Schema Validation — strict output format enforcement
    ↓  (retry logic on failure)
UiPath Robot (EmailDispatcher) — sends reply via SMTP + logs to tracker
```

---

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| RPA layer | UiPath Studio + Orchestrator |
| Backend | FastAPI (Python) |
| Local AI model | OLLAMA + Llama 3 |
| Email protocols | IMAP (read) + SMTP (send) |
| Data validation | JSON Schema (strict) |
| Error handling | Retry logic + fallback exception flow |

---

## ✨ Key Features

- **Real-time classification** — email intent detected via Llama 3 on each incoming message
- **Context-aware responses** — AI-generated replies tailored to email content and category
- **Local processing** — all data stays on-premises using OLLAMA + Llama 3
- **Strict validation** — JSON schema enforcement ensures clean structured outputs
- **Robust error handling** — retry logic + fallback paths for API failures
- **24/7 operation** — scheduled UiPath robot, no manual intervention required

---

## 📁 Project Structure

```
AI-Email-Classification-Auto-Response-System/
├── uipath/
│   ├── EmailMonitor.xaml         # IMAP polling workflow template
│   └── EmailDispatcher.xaml      # SMTP send + logging workflow template
├── api/
│   ├── main.py                   # FastAPI app + endpoints
│   ├── ollama_client.py          # OLLAMA + Llama 3 integration
│   ├── classifier.py             # Email intent classification
│   ├── responder.py              # Response generation
│   └── validator.py              # JSON schema validation
├── schemas/
│   └── email_schema.json         # Strict output schema definition
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment configuration template
└── README.md
```

---

## 🚀 Setup

### Prerequisites

1. **OLLAMA installed and running** with Llama 3 model:
   ```bash
   ollama pull llama3
   ollama serve
   ```
   OLLAMA will be available at `http://localhost:11434`

2. **Python 3.8+** installed

3. **UiPath Studio** installed (for workflow development)

### Backend Setup

```bash
git clone https://github.com/Slg-Vansh/AI-Email-Classification-Auto-Response-System
cd AI-Email-Classification-Auto-Response-System
pip install -r requirements.txt

# Add your credentials
cp .env.example .env
# Fill in: IMAP_HOST, IMAP_USER, IMAP_PASS, SMTP settings
```

```bash
# Run the FastAPI server
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### UiPath Workflows

1. Open UiPath Studio
2. Import `uipath/EmailMonitor.xaml` and `uipath/EmailDispatcher.xaml`
3. Configure activity properties:
   - Email credentials
   - FastAPI endpoint URL (`http://localhost:8000/api/v1/process-email`)
   - SMTP settings
4. Publish to UiPath Orchestrator
5. Create a trigger/schedule for continuous monitoring

---

## 📡 API Endpoints

### 1. **Classify Email**
```bash
POST /api/v1/classify
Content-Type: application/json

{
  "subject": "Payment Issue on Order #123",
  "body": "Hi, I was charged twice for my order...",
  "sender": "customer@example.com"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Email classified successfully",
  "data": {
    "intent": "billing",
    "confidence": 0.92,
    "summary": "Customer reporting duplicate charge",
    "priority": "high",
    "requires_response": true,
    "action_items": ["Refund duplicate charge", "Send confirmation email"]
  }
}
```

### 2. **Generate Response**
```bash
POST /api/v1/generate-response
Content-Type: application/json

{
  "subject": "Payment Issue on Order #123",
  "body": "Hi, I was charged twice for my order...",
  "sender": "customer@example.com",
  "generate_response": true
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Response generated successfully",
  "data": {
    "response_text": "Dear Customer,\n\nThank you for reaching out. We sincerely apologize for the duplicate charge on your account...",
    "response_tone": "professional",
    "length": 387,
    "includes_action_items": true
  }
}
```

### 3. **End-to-End Processing** (Used by UiPath)
```bash
POST /api/v1/process-email
Content-Type: application/json

{
  "subject": "New Order Inquiry",
  "body": "What's the pricing for bulk orders?",
  "sender": "bulk@company.com",
  "generate_response": true
}
```

---

## 🔌 UiPath Integration

### EmailMonitor Workflow
- Polls IMAP inbox every 5 minutes
- Extracts new email data (subject, body, sender)
- Calls `/api/v1/process-email` endpoint
- Parses JSON response
- Triggers EmailDispatcher for reply

### EmailDispatcher Workflow
- Receives classification + generated response
- Formats professional reply email
- Sends via SMTP
- Logs result to Orchestrator Queue/Database

---

## 🛡️ Data Privacy

All email processing happens **locally**:
- ✅ OLLAMA runs on your machine
- ✅ Llama 3 model runs locally
- ✅ No data sent to external APIs
- ✅ No cloud dependencies
- ✅ All data stays on-premises

---

## 📊 Classification Categories

- **support** — Customer support or technical issues
- **sales** — Sales inquiries or leads
- **billing** — Payment or billing related
- **feedback** — Feedback or suggestions
- **complaint** — Complaints or issue reports
- **inquiry** — General inquiries
- **spam** — Spam or unsolicited emails

---

## 🔧 Configuration

Edit `.env` to customize:

```env
OLLAMA_MODEL=llama3              # Local LLM model
API_PORT=8000                    # FastAPI port
COMPANY_NAME=Your Company        # Your company name
RESPONSE_TONE=professional       # Response tone
CLASSIFICATION_CONFIDENCE_THRESHOLD=0.6  # Minimum confidence score
```

---

## 📊 Monitoring

Check system health:
```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "ollama_connected": true,
  "model": "llama3"
}
```

---

## 🚨 Troubleshooting

**OLLAMA not connecting?**
```bash
# Check if OLLAMA is running
curl http://localhost:11434/api/tags

# If not running, start OLLAMA
ollama serve
```

**API not responding?**
```bash
# Check FastAPI logs
# Make sure port 8000 is not in use
# Try running on different port: uvicorn api.main:app --port 8001
```

**UiPath connection issues?**
- Verify `UIPATH_WEBHOOK_URL` in `.env` matches UiPath robot configuration
- Test endpoint with Postman before deploying to Orchestrator
- Check firewall rules if on network

---

## 📬 Contact

Built by [Vansh](https://github.com/Slg-Vansh) · vanshjangid1805@gmail.com
