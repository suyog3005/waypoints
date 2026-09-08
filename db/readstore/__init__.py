"""Read Store package.

Denormalized, read-optimized projections of the Operational DB (architecture
Section 8). The Read Store is a *separate* database (``block_planning_read``)
populated by the polling ETL in ``db.readstore.etl`` — it is never the
authoritative write target. The Query Service (Phase 7) reads from here.
"""
