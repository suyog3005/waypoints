"""Pydantic request/response schemas for the HTTP layer. Kept separate from
api/models/, which is ORM-only (see that package's docstring)."""

from pydantic import BaseModel

from src.config import BACKLOG_SIZE, JOBS_PER_DAY

from api.models.tables import Approach, RunStatus


class CreateScenarioRequest(BaseModel):
    name: str
    seed: int
    backlog_size: int = BACKLOG_SIZE
    jobs_per_day: float = JOBS_PER_DAY


class ScenarioResponse(BaseModel):
    id: int


class CreateRunRequest(BaseModel):
    approach: Approach
    solve_time_limit: float | None = None


class RunCreatedResponse(BaseModel):
    id: int
    status: RunStatus


class RunStatusResponse(BaseModel):
    status: RunStatus
    solver_status: str | None
    solve_time_actual: float | None
    error_message: str | None
