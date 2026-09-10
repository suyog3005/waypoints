"""Seed script for local development and demos.

Run after migrations are applied:
    python -m db.seed

Creates a large, realistic dataset: one zone/division/section, departments,
a 5×4 grid of tracks (main + parallel lines), 50+ trains with schedules
covering the current time. The map will show a busy rail corridor.
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

        # Create a 5×4 grid of tracks (20 tracks total)
        # Rows represent parallel lines (UP/DOWN/Goods/etc.)
        # Columns represent sections
        track_grid = []
        track_names = [
            ("UP Main", "UP"),
            ("DOWN Main", "DOWN"),
            ("Goods Loop", "UP"),
            ("Siding A", "UP"),
            ("Siding B", "DOWN"),
        ]
        section_names = ["North", "Central", "South", "Express"]

        for row, (name_base, direction) in enumerate(track_names):
            for col, section_name in enumerate(section_names):
                code = f"TRK-{chr(65 + row)}{col + 1}"  # TRK-A1, A2, ..., B1, B2, ...
                name = f"{name_base} ({section_name})"
                track = Track(section_id=section.id, code=code, name=name, direction=direction)
                session.add(track)
                track_grid.append((track, row, col))

        session.flush()

        # Create 50+ trains with various numbers
        trains = []
        train_types = ["EXPRESS", "PASSENGER", "GOODS", "LOCAL"]
        for i in range(1, 51):  # 50 trains
            train_num = 10000 + (i % 40) * 100 + (i // 40) * 11  # Variety in numbers
            train_type = train_types[i % len(train_types)]
            train = Train(train_number=str(train_num), train_type=train_type)
            session.add(train)
            trains.append(train)

        session.flush()

        now = datetime.now(timezone.utc)

        # Create schedules: each train assigned to multiple tracks with overlapping schedules
        # This creates a busy, realistic network with trains spread across the grid
        schedules = []
        for train_idx, train in enumerate(trains):
            # Each train gets 1-3 tracks, varying start times so they're spread out
            num_tracks = (train_idx % 3) + 1
            for track_offset in range(num_tracks):
                track_col = (train_idx + track_offset) % 4  # Spread across section columns
                track_row = (train_idx // 4 + track_offset) % 5  # Spread across rows

                # Find the track at this grid position
                matching_track = None
                for t, r, c in track_grid:
                    if r == track_row and c == track_col:
                        matching_track = t
                        break

                if matching_track:
                    # Stagger start times: trains active at different times throughout the day
                    offset_hours = (train_idx * 2) % 24  # Every 2 hours: train 0 @ -12h, train 1 @ -10h, etc.
                    start = now - timedelta(hours=12) + timedelta(hours=offset_hours)
                    end = start + timedelta(hours=4)  # Each train runs for 4 hours

                    schedule = TrainSchedule(
                        train_id=train.id,
                        track_id=matching_track.id,
                        scheduled_start=start,
                        scheduled_end=end,
                        created_at=now,
                        updated_at=now,
                    )
                    schedules.append(schedule)
                    session.add(schedule)

        # Create sample block request
        from db.models import BlockRequest

        sample_request = BlockRequest(
            department_id=engineering.id,
            requested_by_user_id=requester.id,
            request_type=RequestType.OPERATIONAL,
            priority=RequestPriority.NORMAL,
            track_id=track_grid[0][0].id,  # First track in grid
            requested_start=now + timedelta(days=1, hours=2),
            requested_end=now + timedelta(days=1, hours=4),
            status=RequestStatus.DRAFT,
        )
        session.add(sample_request)

        session.commit()
        print(f"Seed data created: {len(track_grid)} tracks, {len(trains)} trains, {len(schedules)} schedules.")


if __name__ == "__main__":
    seed()
