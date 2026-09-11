"""Seed the operational DB with a block-planner scenario.

Generates one scenario at seed 42 with the vendored pipeline's data
generator (services/optimization-service/pipeline/data_gen.py) and writes it
into the operational DB: a Section with 40 Tracks (20 segments x Up/Down,
segment index stored as `sequence` in Track.metadata_ so the solver has an
ordered corridor), the generated timetable as TrainSchedule rows, and one
BlockRequest per generated job.

Idempotent by section name: re-running with an existing section is a no-op
unless --force is passed, which deletes that section's tracks, train
schedules and block requests and rebuilds them.

Usage:
    python -m scripts.seed_from_pipeline [--force]
"""

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PIPELINE_DIR = REPO_ROOT / "services" / "optimization-service" / "pipeline"
sys.path.insert(0, str(PIPELINE_DIR))

from data_gen import generate_dataset  # noqa: E402

from db.models import (  # noqa: E402
    BlockRequest,
    Department,
    Division,
    OperationalRequest,
    RequestPriority,
    RequestStatus,
    RequestType,
    Section,
    Track,
    Train,
    TrainSchedule,
    User,
    Zone,
)
from db.session import SessionLocal  # noqa: E402

SEED = 42

ZONE_NAME, ZONE_CODE = "Block Planner Zone", "BPZ"
DIVISION_NAME, DIVISION_CODE = "Block Planner Division", "BPD"
SECTION_NAME, SECTION_CODE = "Block Planner Corridor", "BP-CORR"

# (name, code) for the three departments the pipeline generates jobs for.
DEPARTMENTS = [("Engineering", "ENGG-BP"), ("S&T", "SNT-BP"), ("Traction", "TRAC-BP")]

# Pipeline's 4-class priority_class -> the operational DB's 3-value
# RequestPriority enum, for display only (the full 4-class label is kept
# verbatim in additional_parameters).
PRIORITY_MAP = {
    "Critical": RequestPriority.EMERGENCY,
    "High": RequestPriority.HIGH,
    "Medium": RequestPriority.NORMAL,
    "Low": RequestPriority.NORMAL,
}

# Pipeline feature columns to carry into BlockRequest.parameters, with the
# native-Python cast each needs -- jobs_df's numpy dtypes (int64/float64/
# bool_) aren't JSON-serializable as-is. Covers every column model.py's
# LightGBM classifier reads (its FEATURE_COLUMNS) plus priority_class for
# display/ground-truth comparison -- the classifier can't run without all of
# these present.
FEATURE_CASTS = {
    "days_overdue": int,
    "defect_severity": int,
    "asset_age_years": float,
    "recurrence_count": int,
    "traffic_density": float,
    "section_speed_limit": int,
    "speed_restriction_active": bool,
    "estimated_duration_min": int,
    "priority_class": str,
    "days_since_last_maintenance": int,
    "defect_type": str,
    "passenger_train_count": int,
}


def _get_or_create_department(session, name: str, code: str) -> Department:
    dept = session.query(Department).filter_by(name=name).one_or_none()
    if dept is None:
        dept = Department(name=name, code=code)
        session.add(dept)
        session.flush()
    return dept


def _get_or_create_user(session, email: str, full_name: str, employee_code: str, department_id, division_id) -> User:
    user = session.query(User).filter_by(email=email).one_or_none()
    if user is None:
        user = User(
            employee_code=employee_code,
            full_name=full_name,
            email=email,
            password_hash="seed-placeholder-not-a-real-hash",
            department_id=department_id,
            division_id=division_id,
        )
        session.add(user)
        session.flush()
    return user


def _tear_down_existing_section(session, section: Section) -> None:
    track_ids = [row[0] for row in session.query(Track.id).filter_by(section_id=section.id)]
    if track_ids:
        session.query(BlockRequest).filter(BlockRequest.track_id.in_(track_ids)).delete(
            synchronize_session=False
        )
        session.query(TrainSchedule).filter(TrainSchedule.track_id.in_(track_ids)).delete(
            synchronize_session=False
        )
        session.query(Track).filter(Track.id.in_(track_ids)).delete(synchronize_session=False)
    session.delete(section)
    session.flush()


def seed(force: bool) -> None:
    with SessionLocal() as session:
        existing = session.query(Section).filter_by(name=SECTION_NAME).one_or_none()
        if existing is not None:
            if not force:
                print(f"Section {SECTION_NAME!r} already exists; skipping (pass --force to rebuild).")
                return
            _tear_down_existing_section(session, existing)
            session.commit()

        segments_df, trains_df, jobs_df, _windows_df = generate_dataset(seed=SEED)

        zone = session.query(Zone).filter_by(code=ZONE_CODE).one_or_none()
        if zone is None:
            zone = Zone(name=ZONE_NAME, code=ZONE_CODE)
            session.add(zone)
            session.flush()

        division = session.query(Division).filter_by(zone_id=zone.id, code=DIVISION_CODE).one_or_none()
        if division is None:
            division = Division(zone_id=zone.id, name=DIVISION_NAME, code=DIVISION_CODE)
            session.add(division)
            session.flush()

        section = Section(division_id=division.id, name=SECTION_NAME, code=SECTION_CODE)
        session.add(section)
        session.flush()

        departments = {name: _get_or_create_department(session, name, code) for name, code in DEPARTMENTS}
        requesters = {
            name: _get_or_create_user(
                session,
                email=f"{code.lower()}-pipeline@seed.local",
                full_name=f"{name} Pipeline Seed",
                employee_code=f"PIPE-{code}",
                department_id=dept.id,
                division_id=division.id,
            )
            for (name, code), dept in zip(DEPARTMENTS, departments.values())
        }

        # --- Tracks: one per (segment, line), segment index stored as
        # `sequence` in metadata_ so the solver has an ordered corridor. ---
        track_by_segment_line = {}
        for seg in segments_df.itertuples():
            for line in ("Up", "Down"):
                direction = line.upper()
                track = Track(
                    section_id=section.id,
                    code=f"BP-{direction}-{seg.segment_id:02d}",
                    name=f"{line} Line Segment {seg.segment_id}",
                    direction=direction,
                    segment_start=f"{seg.start_km:.1f}",
                    segment_end=f"{seg.end_km:.1f}",
                    metadata_={"sequence": int(seg.segment_id)},
                )
                session.add(track)
                track_by_segment_line[(int(seg.segment_id), direction)] = track
        session.flush()

        # --- Trains + TrainSchedule rows from the generated timetable. ---
        now = datetime.now(timezone.utc)
        day0 = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # Train.train_number is globally unique and seed=42 is deterministic,
        # so a --force rebuild would regenerate the same train IDs -- get or
        # create rather than always inserting (Train rows aren't scoped to a
        # section, so the teardown above doesn't touch them).
        unique_trains = trains_df[["train_id", "train_type"]].drop_duplicates()
        unique_train_ids = [str(x) for x in unique_trains["train_id"]]
        train_by_id = {
            t.train_number: t
            for t in session.query(Train).filter(Train.train_number.in_(unique_train_ids)).all()
        }
        for row in unique_trains.itertuples():
            train_id = str(row.train_id)
            if train_id not in train_by_id:
                train = Train(train_number=train_id, train_type=str(row.train_type))
                session.add(train)
                train_by_id[train_id] = train
        session.flush()

        schedule_rows = []
        for row in trains_df.itertuples():
            track = track_by_segment_line[(int(row.segment), row.line.upper())]
            start = day0 + timedelta(days=int(row.day), minutes=float(row.start_min))
            end = day0 + timedelta(days=int(row.day), minutes=float(row.end_min))
            schedule_rows.append(
                {
                    "train_id": train_by_id[row.train_id].id,
                    "track_id": track.id,
                    "scheduled_start": start,
                    "scheduled_end": end,
                    "created_at": now,
                    "updated_at": now,
                }
            )
        session.bulk_insert_mappings(TrainSchedule, schedule_rows)

        # --- One BlockRequest (+ OperationalRequest carrying the pipeline's
        # feature columns) per generated job. ---
        block_requests = []
        for row in jobs_df.itertuples():
            track = track_by_segment_line[(int(row.segment), row.line.upper())]
            priority = PRIORITY_MAP[row.priority_class]
            submitted_at = day0 + timedelta(days=int(row.day))
            block_requests.append(
                BlockRequest(
                    department_id=departments[row.department].id,
                    requested_by_user_id=requesters[row.department].id,
                    request_type=RequestType.OPERATIONAL,
                    priority=priority,
                    track_id=track.id,
                    requested_start=submitted_at,
                    requested_end=submitted_at + timedelta(minutes=int(row.estimated_duration_min)),
                    status=RequestStatus.SUBMITTED,
                    is_emergency=priority == RequestPriority.EMERGENCY,
                    submitted_at=submitted_at,
                )
            )
        session.add_all(block_requests)
        session.flush()

        operational_requests = [
            OperationalRequest(
                block_request_id=block_request.id,
                reason="TRACK_MAINTENANCE",
                additional_parameters={
                    col: cast(getattr(row, col)) for col, cast in FEATURE_CASTS.items()
                },
            )
            for block_request, row in zip(block_requests, jobs_df.itertuples())
        ]
        session.add_all(operational_requests)

        session.commit()

        print(
            f"Seeded {SECTION_NAME!r}: {len(track_by_segment_line)} tracks, "
            f"{len(train_by_id)} trains, {len(schedule_rows)} train schedules, "
            f"{len(block_requests)} block requests."
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Rebuild the scenario if it already exists.")
    args = parser.parse_args()
    seed(force=args.force)
