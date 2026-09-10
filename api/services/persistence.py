"""Plain functions over the ORM tables -- no repository classes, no
unit-of-work pattern. Each function opens and closes its own session."""

from datetime import datetime, timezone

from src.config import HORIZON_DAYS

from api.models.database import get_session
from api.models.tables import Approach, Result, Run, RunStatus, Scenario


def create_scenario(
    seed: int,
    backlog_size: int,
    jobs_per_day: float,
    horizon_days: int = HORIZON_DAYS,
    name: str | None = None,
) -> Scenario:
    with get_session() as session:
        scenario = Scenario(
            name=name, seed=seed, backlog_size=backlog_size, jobs_per_day=jobs_per_day, horizon_days=horizon_days
        )
        session.add(scenario)
        session.commit()
        session.refresh(scenario)
    return scenario


def create_run(scenario_id: int, approach: Approach, solve_time_limit: float | None = None) -> Run:
    with get_session() as session:
        run = Run(
            scenario_id=scenario_id,
            approach=approach,
            status=RunStatus.pending,
            solve_time_limit=solve_time_limit,
        )
        session.add(run)
        session.commit()
        session.refresh(run)
    return run


def update_run_status(
    run_id: int,
    status: RunStatus,
    solve_time_actual: float | None = None,
    solver_status: str | None = None,
    error_message: str | None = None,
) -> Run:
    """Sets `status` and whichever optional fields are given. Also stamps
    `completed_at` the first time status becomes complete or failed."""
    with get_session() as session:
        run = session.get(Run, run_id)
        run.status = status
        if solve_time_actual is not None:
            run.solve_time_actual = solve_time_actual
        if solver_status is not None:
            run.solver_status = solver_status
        if error_message is not None:
            run.error_message = error_message
        if status in (RunStatus.complete, RunStatus.failed):
            run.completed_at = datetime.now(timezone.utc)
        session.commit()
        session.refresh(run)
    return run


def save_result(
    run_id: int,
    schedule_json: list,
    possessions_json: list,
    metrics_json: dict,
    validation_violations_json: list,
    unscheduled_json: list,
) -> Result:
    with get_session() as session:
        result = Result(
            run_id=run_id,
            schedule_json=schedule_json,
            possessions_json=possessions_json,
            metrics_json=metrics_json,
            validation_violations_json=validation_violations_json,
            unscheduled_json=unscheduled_json,
        )
        session.add(result)
        session.commit()
        session.refresh(result)
    return result


def get_scenario(scenario_id: int) -> Scenario | None:
    with get_session() as session:
        return session.get(Scenario, scenario_id)


def get_scenario_by_name(name: str) -> Scenario | None:
    with get_session() as session:
        return session.query(Scenario).filter(Scenario.name == name).one_or_none()


def get_run(run_id: int) -> Run | None:
    with get_session() as session:
        return session.get(Run, run_id)


def get_latest_run(scenario_id: int, approach: Approach) -> Run | None:
    """Most recent run of one approach on one scenario, any status -- used
    to decide whether seeding needs to (re)run it, unlike
    get_latest_results_by_approach which only sees completed runs."""
    with get_session() as session:
        return (
            session.query(Run)
            .filter(Run.scenario_id == scenario_id, Run.approach == approach)
            .order_by(Run.created_at.desc())
            .first()
        )


def get_results_for_scenario(scenario_id: int) -> list[Result]:
    with get_session() as session:
        return session.query(Result).join(Run, Result.run_id == Run.id).filter(Run.scenario_id == scenario_id).all()


def get_result(run_id: int) -> Result | None:
    with get_session() as session:
        return session.query(Result).filter(Result.run_id == run_id).one_or_none()


def get_latest_results_by_approach(scenario_id: int) -> dict[Approach, Result]:
    """Most recent Result per approach for a scenario -- Results only exist
    for runs that reached `complete`, so this is implicitly complete-only."""
    with get_session() as session:
        runs = (
            session.query(Run)
            .filter(Run.scenario_id == scenario_id, Run.status == RunStatus.complete)
            .order_by(Run.completed_at.desc())
            .all()
        )
        latest: dict[Approach, Result] = {}
        for run in runs:
            if run.approach not in latest and run.result is not None:
                latest[run.approach] = run.result
        return latest


def list_scenarios_with_latest_run_status() -> list[dict]:
    """Every scenario plus, for each Approach, the status of its most
    recent run (None if that approach has never been run)."""
    with get_session() as session:
        scenarios = session.query(Scenario).order_by(Scenario.id).all()
        runs = session.query(Run).order_by(Run.created_at.desc()).all()
        latest_status: dict[int, dict[Approach, RunStatus]] = {}
        for run in runs:
            latest_status.setdefault(run.scenario_id, {}).setdefault(run.approach, run.status)
        return [
            {
                "id": s.id,
                "name": s.name,
                "seed": s.seed,
                "runs": {
                    a.value: (status.value if (status := latest_status.get(s.id, {}).get(a)) else None)
                    for a in Approach
                },
            }
            for s in scenarios
        ]
