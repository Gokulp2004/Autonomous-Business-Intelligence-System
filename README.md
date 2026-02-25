# Autonomous Business Intelligence System

> AI-powered BI platform that turns raw Excel/CSV data into actionable business insights — automatically.

Built with **Google ADK (Gemini)**, **FastAPI**, **React**, and **Plotly**.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND (React + Tailwind)                  │
│  ┌──────────┐  ┌──────────────┐  ┌──────┐  ┌───────────────┐  │
│  │  Upload   │  │  Dashboard   │  │ Chat │  │ Report        │  │
│  │  Page     │  │  (Plotly)    │  │ Page │  │ Download      │  │
│  └────┬─────┘  └──────┬───────┘  └──┬───┘  └──────┬────────┘  │
│       │               │             │              │           │
└───────┼───────────────┼─────────────┼──────────────┼───────────┘
        │               │             │              │
        ▼               ▼             ▼              ▼
┌─────────────────── REST API (FastAPI) ─────────────────────────┐
│  /api/upload    /api/dashboard   /api/chat    /api/reports     │
└───────┬───────────────┬─────────────┬──────────────┬───────────┘
        │               │             │              │
        ▼               ▼             ▼              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     PROCESSING LAYER                            │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐│
│  │ File Parser  │  │ Data        │  │ Statistical Analysis    ││
│  │ (CSV/Excel)  │→ │ Cleaner     │→ │ • Descriptive stats     ││
│  │              │  │ (Pandas)    │  │ • Correlations          ││
│  └─────────────┘  └─────────────┘  │ • Trends                ││
│                                     │ • Anomaly detection     ││
│                                     │ • Forecasting (Prophet) ││
│                                     └───────────┬─────────────┘│
│                                                 │              │
│  ┌──────────────────────────────────────────────▼──────────┐   │
│  │              GOOGLE ADK AGENT (Gemini)                   │   │
│  │  • Interprets analysis results                           │   │
│  │  • Generates human-readable insights                     │   │
│  │  • Answers natural-language questions                     │   │
│  │  • Decides which tools to use                             │   │
│  └────────────────────────┬─────────────────────────────────┘   │
│                           │                                     │
│            ┌──────────────┼──────────────┐                     │
│            ▼              ▼              ▼                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │ Plotly       │  │ PDF Report  │  │ PPT Report  │            │
│  │ Charts       │  │ Generator   │  │ Generator   │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer          | Technology                         | Purpose                          |
|----------------|-------------------------------------|----------------------------------|
| Frontend       | React 18 + Tailwind CSS            | User interface                   |
| Backend API    | Python FastAPI                     | REST API endpoints               |
| Data Processing| Pandas, NumPy, Scikit-learn        | Cleaning, stats, ML              |
| Forecasting    | Prophet                            | Time-series prediction           |
| AI Agent       | Google ADK + Gemini                | Insight generation & chat        |
| Visualization  | Plotly                             | Interactive charts               |
| Reports        | fpdf2, python-pptx                 | PDF and PowerPoint generation    |
| Deployment     | Docker + Docker Compose            | Containerized deployment         |
| Cloud          | Google Cloud Run                   | Production hosting               |

---

## Folder Structure

```
├── backend/                        # Python FastAPI backend
│   ├── app/
│   │   ├── main.py                 # FastAPI entry point
│   │   ├── config.py               # Environment configuration
│   │   ├── api/                    # Route handlers
│   │   │   ├── upload.py           # File upload endpoints
│   │   │   ├── analysis.py         # Analysis endpoints
│   │   │   ├── chat.py             # Chat endpoints
│   │   │   ├── reports.py          # Report endpoints
│   │   │   └── dashboard.py        # Dashboard data endpoints
│   │   ├── core/                   # Business logic
│   │   │   ├── file_parser.py      # CSV/Excel parsing
│   │   │   ├── data_cleaner.py     # Data cleaning pipeline
│   │   │   ├── analyzer.py         # Statistical analysis
│   │   │   ├── forecaster.py       # Prophet forecasting
│   │   │   └── anomaly.py          # Anomaly detection
│   │   ├── agent/                  # Google ADK agent
│   │   │   ├── bi_agent.py         # Agent definition
│   │   │   ├── tools.py            # Agent tools
│   │   │   └── prompts.py          # System prompts
│   │   ├── visualization/          # Chart generation
│   │   │   └── charts.py           # Plotly chart builders
│   │   ├── reports/                # Report generation
│   │   │   ├── pdf_report.py       # PDF reports
│   │   │   └── ppt_report.py       # PowerPoint reports
│   │   └── models/                 # Pydantic schemas
│   │       └── schemas.py
│   ├── uploads/                    # Uploaded files
│   ├── outputs/                    # Generated reports
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/                       # React frontend
│   ├── src/
│   │   ├── components/             # UI components
│   │   │   ├── FileUpload.jsx
│   │   │   ├── Dashboard.jsx
│   │   │   ├── ChatInterface.jsx
│   │   │   ├── InsightCard.jsx
│   │   │   └── ReportDownload.jsx
│   │   ├── pages/                  # Pages
│   │   │   ├── HomePage.jsx
│   │   │   ├── AnalysisPage.jsx
│   │   │   └── ChatPage.jsx
│   │   ├── services/
│   │   │   └── api.js              # API client
│   │   ├── App.jsx
│   │   └── index.jsx
│   ├── package.json
│   ├── tailwind.config.js
│   ├── vite.config.js
│   └── Dockerfile
├── docker-compose.yml
├── .gitignore
└── README.md
```

---

## Quick Start (Local Development)

### Prerequisites
- Python 3.11+
- Node.js 18+
- A Google Gemini API key ([get one free](https://aistudio.google.com/apikey))

### 1. Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env         # Windows
# cp .env.example .env         # Mac/Linux
# Edit .env and add your GOOGLE_API_KEY

# Start the server
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

### 3. Open in Browser
- **Frontend:** http://localhost:3000
- **Backend API docs:** http://localhost:8000/docs

---

## Build Order (10 Steps)

| Step | Feature                          | Status |
|------|----------------------------------|--------|
| 1    | Architecture & Project Structure | ✅ Done |
| 2    | Backend FastAPI Setup            | ⬜ Next |
| 3    | Excel Upload & Parsing           | ⬜      |
| 4    | Data Cleaning Pipeline           | ⬜      |
| 5    | Automated Statistical Analysis   | ⬜      |
| 6    | Insight Generation (Google ADK)  | ⬜      |
| 7    | Visualization Dashboard          | ⬜      |
| 8    | Report Generation (PDF/PPT)      | ⬜      |
| 9    | Natural Language Chat             | ⬜      |
| 10   | Cloud Deployment                 | ⬜      |

---

## License

MIT
