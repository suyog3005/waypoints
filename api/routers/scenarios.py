"""Scenario endpoints: create a scenario, and kick off runs against it.
Thin -- request parsing and response shaping only, all logic in services."""

from fastapi import APIRouter, BackgroundTasks, HTTPException

from api.schemas import CreateRunRequest, CreateScenarioRequest, RunCreatedResponse, ScenarioResponse
from api.services.persistence import (
    create_run,
    create_scenario,
    get_latest_results_by_approach,
    get_scenario,
    list_scenarios_with_latest_run_status,
)
from api.services.solve_runner import run_scenario
from api.services.transform import build_comparison_response

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


@router.get("")
def list_scenarios() -> list[dict]:
    return list_scenarios_with_latest_run_status()


@router.post("", response_model=ScenarioResponse)
def create_scenario_endpoint(body: CreateScenarioRequest) -> ScenarioResponse:
    scenario = create_scenario(
        seed=body.seed, backlog_size=body.backlog_size, jobs_per_day=body.jobs_per_day, name=body.name
    )
    return ScenarioResponse(id=scenario.id)


@router.post("/{scenario_id}/runs", response_model=RunCreatedResponse)
def create_run_endpoint(scenario_id: int, body: CreateRunRequest, background_tasks: BackgroundTasks) -> RunCreatedResponse:
    if get_scenario(scenario_id) is None:
        raise HTTPException(status_code=404, detail="scenario not found")
    run = create_run(scenario_id=scenario_id, approach=body.approach, solve_time_limit=body.solve_time_limit)
    background_tasks.add_task(run_scenario, run.id, scenario_id, body.approach, body.solve_time_limit)
    return RunCreatedResponse(id=run.id, status=run.status)


def _build_comparison(scenario_id: int) -> dict:
    results_by_approach = get_latest_results_by_approach(scenario_id)
    metrics_by_approach = {approach.value: result.metrics_json for approach, result in results_by_approach.items()}
    return build_comparison_response(scenario_id, metrics_by_approach)


@router.get("/{scenario_id}/comparison")
def get_scenario_comparison(scenario_id: int) -> dict:
    if get_scenario(scenario_id) is None:
        raise HTTPException(status_code=404, detail="scenario not found")
    return _build_comparison(scenario_id)


@router.get("/{scenario_id}/summary")
def get_scenario_summary(scenario_id: int) -> dict:
    """Scenario parameters plus its comparison, in one call -- what the
    frontend's scenario picker renders."""
    scenario = get_scenario(scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="scenario not found")
    comparison = _build_comparison(scenario_id)
    return {
        "id": scenario.id,
        "name": scenario.name,
        "seed": scenario.seed,
        "backlog_size": scenario.backlog_size,
        "jobs_per_day": scenario.jobs_per_day,
        "horizon_days": scenario.horizon_days,
        "metrics": comparison["metrics"],
        "comparison_to_baseline": comparison["comparison_to_baseline"],
    }
