import os
import random
import logging
from typing import Any
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from dotenv import load_dotenv
import google.generativeai as genai

# -- Configuration --
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("opticsense")

# Required environment variables
_REQUIRED_ENV = ("SUPABASE_URL", "SUPABASE_KEY", "GEMINI_API_KEY")
_missing = [key for key in _REQUIRED_ENV if not os.getenv(key)]
if _missing:
    raise EnvironmentError(
        f"Missing required environment variables: {', '.join(_missing)}"
    )

# Supabase client
supabase: Client = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_KEY"],
)

# Gemini client
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
gemini_model = genai.GenerativeModel("gemini-2.5-flash")

# -- Constants --
TELEMETRY_HISTORY_LIMIT = 5
SIMULATE_FAULT_PROBABILITY = 0.20

SIGNAL_HEALTHY_RANGE = (-25.0, -18.0)   # dBm  (good signal)
SIGNAL_WARN_RANGE    = (-32.0, -28.0)   # dBm  (degraded)
SIGNAL_CRIT_RANGE    = (-35.0, -32.0)   # dBm  (critical)

SIGNAL_CRITICAL_THRESHOLD = -30.0       # dBm

# -- App factory --
app = FastAPI(
    title="OpticSense AI Backend",
    description="Fiber-optic infrastructure monitoring with AI-powered diagnostics.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Restrict to known origins in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# -- Helper utilities --
def _get_latest_telemetry(infra_id: str) -> dict[str, Any]:
    """Return the most recent telemetry log for *infra_id*, or a default stub."""
    result = (
        supabase.table("telemetry_logs")
        .select("signal_dbm, status, timestamp")
        .eq("infra_id", infra_id)
        .order("timestamp", desc=True)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else {
        "signal_dbm": None,
        "status": "No Data",
        "timestamp": None,
    }


def _build_analysis_prompt(infra_id: str, logs: list[dict]) -> str:
    """Construct the Gemini prompt for fiber-optic infrastructure analysis."""
    current = logs[0]
    signal_history = [entry["signal_dbm"] for entry in logs]

    return (
        f"Analisis infrastruktur Fiber Optik berikut:\n"
        f"  ID          : {infra_id}\n"
        f"  Sinyal Saat Ini : {current['signal_dbm']} dBm\n"
        f"  Status      : {current['status']}\n"
        f"  Riwayat Sinyal (5 log terakhir, dBm): {signal_history}\n\n"
        "Tugas Anda: Berikan analisis singkat (maks 3 kalimat) dalam Bahasa Indonesia "
        "tentang kemungkinan penyebab kerusakan fisik kabel optik dan langkah teknis "
        "yang harus diambil teknisi Telkom Akses."
    )


def _simulate_signal() -> tuple[float, str]:
    """
    Return a simulated (signal_dbm, status) pair.

    With probability SIMULATE_FAULT_PROBABILITY the reading represents a
    degraded or critical link; otherwise it is healthy.
    """
    if random.random() < SIMULATE_FAULT_PROBABILITY:
        # Randomly choose between warning and critical bands
        if random.random() < 0.5:
            signal = round(random.uniform(*SIGNAL_WARN_RANGE), 2)
            return signal, "Warning"
        signal = round(random.uniform(*SIGNAL_CRIT_RANGE), 2)
        return signal, "Critical"

    signal = round(random.uniform(*SIGNAL_HEALTHY_RANGE), 2)
    return signal, "Healthy"


# -- Routes --
@app.get(
    "/api/v1/network-status",
    summary="List all infrastructure nodes with latest telemetry",
    tags=["Monitoring"],
)
async def get_network_status() -> dict[str, Any]:
    """
    Retrieve every infrastructure record and attach its most recent
    telemetry reading.

    .. note::
        For large fleets consider replacing per-row queries with a
        Supabase SQL view or RPC that performs the join server-side.
    """
    try:
        infra_result = supabase.table("infrastructures").select("*").execute()
        nodes = infra_result.data or []

        enriched = [
            {**node, "latest_telemetry": _get_latest_telemetry(node["id"])}
            for node in nodes
        ]

        logger.info("Network status fetched — %d nodes returned.", len(enriched))
        return {"status": "success", "data": enriched}

    except Exception as exc:
        logger.exception("Failed to fetch network status.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@app.post(
    "/api/v1/analyze/{infra_id}",
    summary="Run AI diagnostics on a specific infrastructure node",
    tags=["AI Diagnostics"],
)
async def analyze_infra(infra_id: str) -> dict[str, Any]:
    """
    Pull the last *TELEMETRY_HISTORY_LIMIT* telemetry records for
    *infra_id* and ask Gemini for a root-cause analysis.

    Returns a short Indonesian-language recommendation suitable for
    Telkom Akses field technicians.
    """
    logs_result = (
        supabase.table("telemetry_logs")
        .select("*")
        .eq("infra_id", infra_id)
        .order("timestamp", desc=True)
        .limit(TELEMETRY_HISTORY_LIMIT)
        .execute()
    )

    if not logs_result.data:
        logger.warning("Analysis requested for '%s' but no telemetry found.", infra_id)
        return {
            "infra_id": infra_id,
            "analysis": "Data tidak cukup untuk analisis.",
        }

    prompt = _build_analysis_prompt(infra_id, logs_result.data)
    gemini_response = gemini_model.generate_content(prompt)

    logger.info("AI analysis completed for infra_id='%s'.", infra_id)
    return {"infra_id": infra_id, "analysis": gemini_response.text}


@app.post(
    "/api/v1/simulate",
    summary="Inject simulated telemetry for all infrastructure nodes",
    tags=["Simulation"],
)
async def simulate_data() -> dict[str, Any]:
    """
    Generate one synthetic telemetry reading per infrastructure node and
    bulk-insert into *telemetry_logs*.

    Signal distribution:
    - **{healthy_pct}% Healthy** — signal between {lo} and {hi} dBm  
    - **{fault_pct}% Faulty**   — split evenly between Warning and Critical bands
    """.format(
        healthy_pct=int((1 - SIMULATE_FAULT_PROBABILITY) * 100),
        fault_pct=int(SIMULATE_FAULT_PROBABILITY * 100),
        lo=SIGNAL_HEALTHY_RANGE[0],
        hi=SIGNAL_HEALTHY_RANGE[1],
    )
    infra_result = supabase.table("infrastructures").select("id").execute()
    nodes = infra_result.data or []

    new_logs: list[dict[str, Any]] = []
    for node in nodes:
        signal_dbm, status_label = _simulate_signal()
        new_logs.append(
            {
                "infra_id": node["id"],
                "signal_dbm": signal_dbm,
                "status": status_label,
            }
        )

    if new_logs:
        supabase.table("telemetry_logs").insert(new_logs).execute()

    logger.info("Simulated %d telemetry entries.", len(new_logs))
    return {
        "message": f"Simulated telemetry inserted for {len(new_logs)} device(s).",
        "count": len(new_logs),
    }