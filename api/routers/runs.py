"""Run endpoints: status metadata plus the payload endpoints (schedule,
metrics) for a completed run. Metadata only on GET /{run_id} -- the
schedule/possessions payload lives on Result and is only returned by the
dedicated /schedule route (hundreds of KB per run)."""

from fastapi import APIRouter, HTTPException

from api.models.tables import Run, RunStatus
from api.schemas import RunStatusResponse
from api.services.persistence import get_result, get_run
from api.services.transform import build_schedule_response

router = APIRouter(prefix="/runs", tags=["runs"])


def _get_complete_run(run_id: int) -> Run:
    run = get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    if run.status != RunStatus.complete:
        raise HTTPException(status_code=409, detail=f"run is {run.status.value}, not complete")
    return run


@router.get("/{run_id}", response_model=RunStatusResponse)
def get_run_endpoint(run_id: int) -> RunStatusResponse:
    run = get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    return RunStatusResponse(
        status=run.status,
        solver_status=run.solver_status,
        solve_time_actual=run.solve_time_actual,
        error_message=run.error_message,
    )


@router.get("/{run_id}/schedule")
def get_run_schedule(run_id: int) -> dict:
    _get_complete_run(run_id)
    result = get_result(run_id)
    return build_schedule_response(result.schedule_json, result.possessions_json, result.unscheduled_json)


@router.get("/{run_id}/metrics")
def get_run_metrics(run_id: int) -> dict:
    _get_complete_run(run_id)
    result = get_result(run_id)
    return result.metrics_json
