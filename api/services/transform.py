"""Reshapes stored Result JSONB into frontend-facing payloads -- renaming
keys and deriving fields (possession_id, duration_min, pct diffs) so
consumers never have to know the storage-layer field names."""

BASELINE_NOT_RUN = "baseline has not been run for this scenario"


def build_schedule_response(schedule_json: list, possessions_json: list, unscheduled_json: list) -> dict:
    possessions = [
        {
            "id": p["possession_id"],
            "line": p["line"],
            "start_segment": p["segment_start"],
            "end_segment": p["segment_end"],
            "start_min": p["start_min"],
            "end_min": p["end_min"],
        }
        for p in possessions_json
    ]

    def _possession_id(job: dict) -> str | None:
        return next(
            (
                p["possession_id"]
                for p in possessions_json
                if p["line"] == job["line"]
                and p["segment_start"] <= job["segment"] <= p["segment_end"]
                and p["start_min"] <= job["start_min"]
                and job["end_min"] <= p["end_min"]
            ),
            None,
        )

    jobs = [
        {
            "id": j["job_id"],
            "possession_id": _possession_id(j),
            "segment": j["segment"],
            "line": j["line"],
            "department": j["department"],
            "priority_class": j["priority_class"],
            "start_min": j["start_min"],
            "end_min": j["end_min"],
            "wait_days": j["wait_days"],
            "duration_min": j["end_min"] - j["start_min"],
        }
        for j in schedule_json
    ]

    unscheduled = [
        {"id": u["id"], "segment": u["segment"], "department": u["department"], "priority_class": u["priority_class"]}
        for u in unscheduled_json
    ]

    return {"possessions": possessions, "jobs": jobs, "unscheduled": unscheduled}


def _pct_diff(value, baseline_value):
    """% change of `value` vs `baseline_value`; recurses into dict-shaped
    metrics (e.g. wait_days by priority_class). None where either side is
    missing (a class with zero placed jobs stores None, not NaN -- Postgres
    jsonb rejects NaN outright) or baseline is 0 -- a % change against
    nothing, or from nothing, is undefined, not zero."""
    if isinstance(value, dict):
        return {k: _pct_diff(value[k], baseline_value[k]) for k in value}
    if value is None or not baseline_value:
        return None
    return round((value - baseline_value) / baseline_value * 100, 2)


def build_comparison_response(scenario_id: int, metrics_by_approach: dict[str, dict]) -> dict:
    baseline_metrics = metrics_by_approach.get("baseline")
    comparison = {}
    for approach, metrics in metrics_by_approach.items():
        if approach == "baseline":
            continue
        comparison[approach] = BASELINE_NOT_RUN if baseline_metrics is None else _pct_diff(metrics, baseline_metrics)
    return {"scenario_id": scenario_id, "metrics": metrics_by_approach, "comparison_to_baseline": comparison}
