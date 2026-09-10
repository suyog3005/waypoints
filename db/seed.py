"""Seed script for local development and demos.

Run after migrations are applied:
    python -m db.seed

Creates a minimal but coherent dataset: one zone/division/section, a couple of
departments, a requester user, a few tracks/trains, and one sample block
request — enough to exercise the write path end-to-end once services exist.
"""

from datetime import datetime, timedelta, timezone

from db.models import (
    Department,
    Division,
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
from db.session import SessionLocal


def seed() -> None:
    with SessionLocal() as session:
        zone = Zone(name="Northern Zone", code="NR")
        session.add(zone)
        session.flush()

        division = Division(zone_id=zone.id, name="Delhi Division", code="DLI")
        session.add(division)
        session.flush()

        section = Section(division_id=division.id, name="Delhi-Ambala Section", code="DLI-UMB")
        session.add(section)
        session.flush()

        engineering = Department(name="Engineering", code="ENGG", contact_email="engg@example.org")
        electrical = Department(name="Electrical (OHE)", code="ELEC", contact_email="elec@example.org")
        session.add_all([engineering, electrical])
        session.flush()

        requester = User(
            employee_code="EMP0001",
            full_name="Demo Requester",
            email="requester@example.org",
            password_hash="placeholder-hash-replace-with-real-hashing",
            department_id=engineering.id,
            division_id=division.id,
        )
        session.add(requester)
        session.flush()

        track_a = Track(section_id=section.id, code="TRK-A", name="Up Main Line", direction="UP")
        track_b = Track(section_id=section.id, code="TRK-B", name="Down Main Line", direction="DOWN")
        track_c = Track(section_id=section.id, code="TRK-C", name="Goods Loop", direction="UP")
        session.add_all([track_a, track_b, track_c])
        session.flush()

        train = Train(train_number="12345", train_type="EXPRESS")
        train_2 = Train(train_number="56789", train_type="PASSENGER")
        session.add_all([train, train_2])
        session.flush()

        now = datetime.now(timezone.utc)

        # Schedules spanning the current time so the map shows trains
        # immediately (the ETL places each train at its track midpoint for the
        # duration of the schedule window).
        session.add_all(
            [
                TrainSchedule(
                    train_id=train.id,
                    track_id=track_a.id,
                    scheduled_start=now - timedelta(hours=1),
                    scheduled_end=now + timedelta(hours=3),
                    created_at=now,
                    updated_at=now,
                ),
                TrainSchedule(
                    train_id=train_2.id,
                    track_id=track_b.id,
                    scheduled_start=now - timedelta(minutes=30),
                    scheduled_end=now + timedelta(hours=2),
                    created_at=now,
                    updated_at=now,
                ),
                TrainSchedule(
                    train_id=train_2.id,
                    track_id=track_c.id,
                    scheduled_start=now + timedelta(hours=4),
                    scheduled_end=now + timedelta(hours=6),
                    created_at=now,
                    updated_at=now,
                ),
            ]
        )

        from db.models import BlockRequest

        sample_request = BlockRequest(
            department_id=engineering.id,
            requested_by_user_id=requester.id,
            request_type=RequestType.OPERATIONAL,
            priority=RequestPriority.NORMAL,
            track_id=track_a.id,
            requested_start=now + timedelta(days=1, hours=2),
            requested_end=now + timedelta(days=1, hours=4),
            status=RequestStatus.DRAFT,
        )
        session.add(sample_request)

        session.commit()
        print("Seed data created.")


if __name__ == "__main__":
    seed()
