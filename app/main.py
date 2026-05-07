import random
import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from opentelemetry import metrics

from app.config import config
from slo.calculator import SLOCalculator
from ai.explainer import explain_slo_status

# ─── LOGGING SETUP ────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='{"time": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}'
)
logger = logging.getLogger(__name__)

# ─── OPENTELEMETRY METRICS ────────────────────────────────
meter = metrics.get_meter("slo.demo.service")

request_counter = meter.create_counter(
    name="requests.total",
    description="Total number of requests received",
    unit="1"
)

error_counter = meter.create_counter(
    name="requests.errors",
    description="Total number of failed requests",
    unit="1"
)

latency_histogram = meter.create_histogram(
    name="requests.latency",
    description="Request latency in milliseconds",
    unit="ms"
)

# ─── IN-MEMORY REQUEST STORE ──────────────────────────────
# Tracks live request counts for SLO calculation.
# In production this would come from Prometheus or Azure Monitor.
_request_store = {"total": 0, "errors": 0, "slow": 0}

# ─── APP LIFECYCLE ────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {config.APP_NAME} in {config.ENVIRONMENT} mode")
    yield
    logger.info(f"Shutting down {config.APP_NAME}")

# ─── FASTAPI APP ──────────────────────────────────────────
app = FastAPI(
    title="SLO Demo Service",
    description="A FastAPI service instrumented for SLO tracking",
    version="1.0.0",
    lifespan=lifespan
)

# ─── MIDDLEWARE ───────────────────────────────────────────
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    latency_ms = (time.time() - start_time) * 1000

    # Skip tracking for the SLO and health endpoints themselves
    # so they don't pollute the error budget calculations
    if not request.url.path.startswith("/slo") and request.url.path != "/health":
        _request_store["total"] += 1
        if response.status_code >= 500:
            _request_store["errors"] += 1
        if latency_ms > config.SLO_LATENCY_TARGET_MS:
            _request_store["slow"] += 1

    attributes = {
        "method": request.method,
        "path": request.url.path,
        "status_code": str(response.status_code)
    }
    request_counter.add(1, attributes)
    latency_histogram.record(latency_ms, attributes)

    if response.status_code >= 500:
        error_counter.add(1, attributes)
        logger.error(f"Error response: {response.status_code} for {request.url.path}")

    return response

# ─── HEALTH ROUTE ─────────────────────────────────────────
@app.get("/health")
async def health_check():
    """
    Health check endpoint — used by Container Apps to verify
    the app is alive. Always returns 200 if the app is running.
    """
    return {
        "status": "healthy",
        "service": config.APP_NAME,
        "environment": config.ENVIRONMENT
    }

# ─── DATA ROUTES ──────────────────────────────────────────
@app.get("/api/data")
async def get_data():
    """
    Simulated data endpoint with realistic error and latency behavior.

    SRE concept: This simulates a real service with:
    - 5% error rate (500 errors) — affects availability SLI
    - Variable latency 10-300ms — affects latency SLI
    - Occasional slow requests (>200ms) — burns latency error budget
    """
    # Simulate 5% error rate
    if random.random() < 0.05:
        logger.warning("Simulated service error triggered")
        raise HTTPException(
            status_code=500,
            detail="Simulated internal service error"
        )

    # 80% fast requests, 20% slow requests
    if random.random() < 0.20:
        latency = random.uniform(100, 300)
    else:
        latency = random.uniform(10, 100)

    time.sleep(latency / 1000)

    return {
        "status": "ok",
        "data": f"Sample payload from {config.APP_NAME}",
        "simulated_latency_ms": round(latency, 2),
        "environment": config.ENVIRONMENT
    }

@app.get("/api/slow")
async def slow_endpoint():
    """
    Intentionally slow endpoint — always violates the latency SLO.
    Use this to test latency error budget burn.
    """
    time.sleep(0.5)
    return {"status": "ok", "note": "This endpoint always violates the latency SLO"}

@app.get("/api/error")
async def error_endpoint():
    """
    Intentionally always errors — use to rapidly burn availability
    error budget for testing alert thresholds.
    """
    raise HTTPException(status_code=500, detail="Intentional error for SLO testing")

# ─── SLO ROUTES ───────────────────────────────────────────
@app.get("/slo/status")
async def get_slo_status():
    """
    Returns current SLO status calculated from live request data.
    This is your error budget dashboard endpoint.
    """
    calc = SLOCalculator(
        target_availability=config.SLO_AVAILABILITY_TARGET,
        target_latency_ms=config.SLO_LATENCY_TARGET_MS
    )

    availability = calc.calculate_availability(
        total_requests=_request_store["total"],
        total_errors=_request_store["errors"]
    )

    latency = calc.calculate_latency(
        total_requests=_request_store["total"],
        slow_requests=_request_store["slow"]
    )

    return {
        "window": "session",
        "availability_slo": availability.__dict__,
        "latency_slo": latency.__dict__,
        "raw_counts": _request_store
    }

@app.get("/slo/explain")
async def explain_slo():
    """
    AI-powered SLO explanation endpoint.
    Calls Claude via OpenRouter to interpret the current SLO status
    and provide plain-English guidance for the on-call engineer.
    """
    calc = SLOCalculator(
        target_availability=config.SLO_AVAILABILITY_TARGET
    )

    availability = calc.calculate_availability(
        total_requests=_request_store["total"],
        total_errors=_request_store["errors"]
    )

    explanation = await explain_slo_status(availability)

    return {
        "slo_status": availability.__dict__,
        "ai_explanation": explanation,
        "model_used": config.OPENROUTER_MODEL
    }

@app.post("/slo/reset")
async def reset_counters():
    """Reset request counters — useful for starting a clean test window."""
    _request_store["total"] = 0
    _request_store["errors"] = 0
    _request_store["slow"] = 0
    return {"message": "Counters reset", "store": _request_store}