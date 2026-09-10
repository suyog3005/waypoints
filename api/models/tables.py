"""SQLAlchemy ORM tables: scenarios (generation parameters) -> runs (one
scheduling attempt) -> results (its output), 1:many then 1:1."""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Approach(str, enum.Enum):
    baseline = "baseline"
    solver_gt = "solver_gt"
    solver_ml = "solver_ml"


class RunStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    complete = "complete"
    failed = "failed"


class Scenario(Base):
    """The parameters that define a generated instance -- everything
    generate_dataset() needs to reproduce this exact scenario."""

    __tablename__ = "scenarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    seed: Mapped[int] = mapped_column(Integer, nullable=False)
    backlog_size: Mapped[int] = mapped_column(Integer, nullable=False)
    jobs_per_day: Mapped[float] = mapped_column(Float, nullable=False)
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    runs: Mapped[list["Run"]] = relationship(back_populates="scenario")


class Run(Base):
    """One scheduling attempt (one approach) against one scenario."""

    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenarios.id"), nullable=False)
    approach: Mapped[Approach] = mapped_column(Enum(Approach, name="approach"), nullable=False)
    status: Mapped[RunStatus] = mapped_column(Enum(RunStatus, name="run_status"), nullable=False, default=RunStatus.pending)
    solve_time_limit: Mapped[float | None] = mapped_column(Float, nullable=True)
    solve_time_actual: Mapped[float | None] = mapped_column(Float, nullable=True)
    solver_status: Mapped[str | None] = mapped_column(String, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    scenario: Mapped["Scenario"] = relationship(back_populates="runs")
    result: Mapped["Result | None"] = relationship(back_populates="run", uselist=False)


class Result(Base):
    """One run's output. schedule_json/possessions_json/metrics_json/
    unscheduled_json are stored as JSONB documents, not normalised into
    rows -- the API reads them whole and never queries inside them.

    metrics_json contract (frontend can rely on these keys; new metrics may
    be added without a migration, but keep this list in sync when they are):
        jobs_unscheduled: int
        n_possessions: int
        line_blocked_min: float
        weighted_wait: float
        wait_days: dict[str, float]  -- keyed by priority_class (Critical/High/Medium/Low)
        total_job_duration_min: float

    schedule_json rows carry a `wait_days` field per job (start_day -
    max(0, report_day), same formula as the scheduler's own mean_wait_days)
    -- computed at save time in solve_runner.py, since report_day isn't
    otherwise persisted anywhere the read endpoints can reach.

    unscheduled_json rows: {id, segment, department, priority_class} for
    every job present in the scenario but absent from schedule_json.
    """

    __tablename__ = "results"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), nullable=False, unique=True)
    schedule_json: Mapped[list] = mapped_column(JSONB, nullable=False)
    possessions_json: Mapped[list] = mapped_column(JSONB, nullable=False)
    metrics_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    validation_violations_json: Mapped[list] = mapped_column(JSONB, nullable=False)
    unscheduled_json: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")

    run: Mapped["Run"] = relationship(back_populates="result")
