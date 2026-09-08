-- Creates the separate Read Store database on first Postgres boot.
--
-- The Operational DB (block_planning) is created automatically from
-- POSTGRES_DB. The Read Store (block_planning_read) is a distinct database
-- holding denormalized projections (architecture Section 8), populated by the
-- polling ETL (db/readstore/etl.py) and migrated via
-- `alembic -c db/readstore/alembic.ini upgrade head`.
--
-- NOTE: docker-entrypoint-initdb.d scripts only run when the pgdata volume is
-- empty (first boot). If you already have a running stack, create it manually:
--   docker compose exec postgres psql -U postgres -c "CREATE DATABASE block_planning_read;"

CREATE DATABASE block_planning_read;
