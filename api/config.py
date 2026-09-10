"""API configuration: environment variables with sane defaults. Constants
that already live in src/config.py (or src/model.py) are imported, not
re-declared, so there's one source of truth for each."""

import os

from src.config import SOLVE_TIME_LIMIT as _DEFAULT_SOLVE_TIME_LIMIT
from src.model import MODEL_PATH as _DEFAULT_MODEL_PATH

APP_VERSION = "0.1.0"

# Default host "postgres" matches the service name in docker-compose.yml;
# override via env when running api/main.py outside that network.
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://blockplanner:blockplanner@postgres:5432/blockplanner")
SOLVE_TIME_LIMIT = float(os.environ.get("SOLVE_TIME_LIMIT", _DEFAULT_SOLVE_TIME_LIMIT))
MODEL_PATH = os.environ.get("MODEL_PATH", _DEFAULT_MODEL_PATH)
