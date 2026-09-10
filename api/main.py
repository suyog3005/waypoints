"""FastAPI app entry point. Demo backend for a hackathon: no auth, no rate
limiting, no logging framework, no speculative middleware."""

import joblib
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import APP_VERSION, MODEL_PATH
from api.routers import runs, scenarios

app = FastAPI(title="block-planner API", version=APP_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(scenarios.router)
app.include_router(runs.router)


@app.get("/health")
def health() -> dict:
    """Liveness plus a real check of whether MODEL_PATH actually loads --
    not just whether the file exists."""
    try:
        joblib.load(MODEL_PATH)
        model_loaded = True
    except Exception:
        model_loaded = False
    return {"status": "ok", "version": APP_VERSION, "model_loaded": model_loaded}
