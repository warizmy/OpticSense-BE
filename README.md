# OpticSense.ai Backend
OpticSense.ai is a network infrastructure management and monitoring platform that integrates geospatial data with artificial intelligence. The system is designed to monitor the health of fiber optic distribution points (ODP/ODC) in real-time and deliver predictive diagnostic analysis using a Large Language Model (LLM).

---

## Key Features

| Feature | Description |
|---|---|
| **Geospatial Asset Management** | Manage infrastructure asset data with accurate geographic coordinates via PostGIS integration. |
| **Automated Telemetry Simulation** | A simulation engine that generates signal attenuation data (dBm) for system testing across various fault scenarios. |
| **AI-Driven Diagnostics** | Google Gemini AI integration for technical recommendations based on historical data and detected signal anomalies. |
| **Real-time Network Status** | API endpoint delivering up-to-date network health status for dashboard visualization. |

---

## Technology Stack

| Layer | Technology |
|---|---|
| **Framework** | FastAPI (Python) |
| **Database** | PostgreSQL with PostGIS extension (via Supabase) |
| **Intelligence Engine** | Google Generative AI — Gemini 2.5 Flash |
| **Database Interface** | Supabase Python Client |
| **Environment Management** | Python-dotenv |

---

## Database Schema

The system uses two primary tables for data management.

**`infrastructures`**
Stores master data for physical assets including device ID, type (STO, ODC, ODP), geographic coordinates (geometry point), and port capacity.

**`telemetry_logs`**
Stores transactional network performance data, including signal attenuation value (dBm), health status, and timestamp.

---

## Installation

### Prerequisites

- Python **3.10** or higher
- A Supabase account with the **PostGIS** extension enabled
- A **Google Gemini** API key

### Steps

**1. Clone the repository**

```bash
git clone https://github.com/username/opticsense-be.git
cd opticsense-be
```

**2. Create and activate a virtual environment**

```bash
python -m venv venv

# Linux / macOS
source venv/bin/activate

# Windows
venv\Scripts\activate
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

**4. Configure environment variables**

Create a `.env` file in the project root and fill in the following values:

```env
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your_supabase_anon_key
GEMINI_API_KEY=your_gemini_api_key
```

---

## Running the Application

Start the development server with Uvicorn:

```bash
uvicorn main:app --reload
```

The application will be available at **http://127.0.0.1:8000** by default.

Interactive API documentation (Swagger UI) is accessible at **http://localhost:8000/docs**.

---

## API Reference

### `GET /api/v1/network-status`

Retrieves all infrastructure records along with their latest telemetry status.

**Response**
```json
{
  "status": "success",
  "data": [
    {
      "id": "odp-001",
      "type": "ODP",
      "latest_telemetry": {
        "signal_dbm": -21.5,
        "status": "Healthy",
        "timestamp": "2025-01-15T10:30:00Z"
      }
    }
  ]
}
```

---

### `POST /api/v1/analyze/{infra_id}`

Performs an in-depth AI analysis on a specific infrastructure node using the last 5 telemetry readings.

**Path Parameters**

| Parameter | Type | Description |
|---|---|---|
| `infra_id` | `string` | Unique identifier of the target infrastructure node |

**Response**
```json
{
  "infra_id": "odp-001",
  "analysis": "Signal degradation detected over the last 3 readings..."
}
```

---

### `POST /api/v1/simulate`

Generates randomized telemetry data for all infrastructure nodes and inserts it into the database. Useful for load testing and dashboard validation.

**Signal distribution:**
- **80% Healthy** — signal between −18 and −25 dBm
- **10% Warning** — signal between −28 and −32 dBm
- **10% Critical** — signal between −32 and −35 dBm

**Response**
```json
{
  "message": "Simulated telemetry inserted for 12 device(s).",
  "count": 12
}
```

---

## Project Structure

```
opticsense-be/
├── main.py            # Application entry point, routes, and business logic
├── requirements.txt   # Python dependencies
├── .env               # Environment variables (not committed to version control)
└── README.md
```

---

## License

This project was developed for professional portfolio and internal development purposes. All rights reserved by the developer.
