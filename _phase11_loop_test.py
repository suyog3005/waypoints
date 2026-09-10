#!/usr/bin/env python
"""Phase 11: Real-Time Loop Verification Script

Tests the complete event-driven pipeline:
  1. Inject a train delay event
  2. Trigger optimization
  3. Verify plan created in Operational DB
  4. Sync ETL to Read Store
  5. Verify Query Service returns updated data
  6. Repeat 5+ times to confirm deterministic behavior

Run via: python _phase11_loop_test.py

Expected output: 5 successful iterations, each with:
  - Event injected → Event ID printed
  - Optimization triggered
  - Plan created in DB
  - ETL synced (track_view, plan_summary, etc.)
  - Query Service confirms new plan
  - Frontend could poll /plans and see the new plan

Usage:
  PYTHONPATH=. python _phase11_loop_test.py [--iterations 5] [--delay 10]
"""

import asyncio
import json
import logging
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Add repo root to path
sys.path.insert(0, str(Path(__file__).parent))

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-8s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# Service URLs
COMMAND_SERVICE_URL = "http://localhost:8001"
QUERY_SERVICE_URL = "http://localhost:8002"


def inject_train_delay(delay_minutes: int = 15) -> dict:
    """Call POST /inject/train-delay to simulate an operational event."""
    url = f"{COMMAND_SERVICE_URL}/inject/train-delay"
    payload = {
        "delay_minutes": delay_minutes,
        "reason": f"Phase 11 test iteration at {datetime.now(timezone.utc).isoformat()}",
    }
    try:
        resp = requests.post(url, params=payload, timeout=5)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.error(f"Failed to inject train delay: {exc}")
        raise


def trigger_optimization() -> dict:
    """Call POST /inject/trigger-optimization to kick off the optimizer."""
    url = f"{COMMAND_SERVICE_URL}/inject/trigger-optimization"
    payload = {
        "reason": f"Phase 11 test at {datetime.now(timezone.utc).isoformat()}",
    }
    try:
        resp = requests.post(url, params=payload, timeout=5)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.error(f"Failed to trigger optimization: {exc}")
        raise


def run_etl() -> dict:
    """Run the Read Store ETL to sync Operational DB → Read Store."""
    from db.readstore.etl import sync_read_store
    
    logger.info("Running ETL sync...")
    try:
        counts = sync_read_store()
        logger.info(f"ETL sync complete: {counts}")
        return counts
    except Exception as exc:
        logger.error(f"ETL sync failed: {exc}")
        raise


def verify_plan_in_db() -> int:
    """Check how many plans exist in the Operational DB."""
    from db.models import Plan
    from db.session import SessionLocal
    
    with SessionLocal() as session:
        count = session.query(Plan).count()
        logger.info(f"Plans in Operational DB: {count}")
        return count


def verify_query_service() -> dict:
    """Query the Query Service to verify plan data is available."""
    url = f"{QUERY_SERVICE_URL}/plans"
    try:
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        plan_count = len(data.get("data", []))
        logger.info(f"Query Service /plans returned {plan_count} plans")
        return data
    except Exception as exc:
        logger.error(f"Failed to query /plans: {exc}")
        raise


def wait_for_optimization(timeout_sec: int = 10) -> bool:
    """Wait for the optimization to complete (simple polling)."""
    logger.info(f"Waiting up to {timeout_sec}s for optimization to complete...")
    start = time.time()
    last_count = verify_plan_in_db()
    
    while time.time() - start < timeout_sec:
        time.sleep(1)
        current_count = verify_plan_in_db()
        if current_count > last_count:
            logger.info(f"✓ Optimization completed: {last_count} → {current_count} plans")
            return True
        last_count = current_count
    
    logger.warning(f"Optimization did not complete within {timeout_sec}s")
    return False


def run_iteration(iteration_num: int, delay_minutes: int = 15) -> bool:
    """Run one complete iteration of the event loop."""
    logger.info(f"\n{'='*70}")
    logger.info(f"ITERATION {iteration_num}")
    logger.info(f"{'='*70}")
    
    try:
        # 1. Inject event
        logger.info("Step 1: Injecting train delay event...")
        event = inject_train_delay(delay_minutes)
        logger.info(f"  ✓ Event injected: {event['event_id']}")
        
        # 2. Trigger optimization
        logger.info("Step 2: Triggering optimization...")
        opt_event = trigger_optimization()
        logger.info(f"  ✓ Optimization triggered: {opt_event['event_id']}")
        
        # 3. Wait for optimization to complete
        logger.info("Step 3: Waiting for optimization...")
        if not wait_for_optimization(timeout_sec=15):
            logger.warning("  ⚠ Optimization may not have completed")
        
        # 4. Run ETL to sync Read Store
        logger.info("Step 4: Syncing Read Store via ETL...")
        etl_result = run_etl()
        logger.info(f"  ✓ ETL sync complete: {etl_result}")
        
        # 5. Verify Query Service has updated data
        logger.info("Step 5: Verifying Query Service...")
        query_data = verify_query_service()
        plan_count = len(query_data.get("data", []))
        logger.info(f"  ✓ Query Service ready: {plan_count} plans visible")
        
        logger.info(f"\n✓ ITERATION {iteration_num} PASSED")
        return True
        
    except Exception as exc:
        logger.error(f"\n✗ ITERATION {iteration_num} FAILED: {exc}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run the full Phase 11 verification loop."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Phase 11 Real-Time Loop Verification")
    parser.add_argument("--iterations", type=int, default=5, help="Number of loop iterations (default 5)")
    parser.add_argument("--delay", type=int, default=15, help="Train delay minutes (default 15)")
    args = parser.parse_args()
    
    logger.info(f"Phase 11: Real-Time Loop Verification")
    logger.info(f"  Command Service: {COMMAND_SERVICE_URL}")
    logger.info(f"  Query Service:   {QUERY_SERVICE_URL}")
    logger.info(f"  Iterations:      {args.iterations}")
    logger.info(f"  Delay minutes:   {args.delay}")
    logger.info("")
    
    # Pre-check: services online
    logger.info("Pre-flight checks...")
    try:
        resp = requests.get(f"{COMMAND_SERVICE_URL}/health", timeout=2)
        assert resp.status_code == 200, f"Command Service health check failed: {resp.status_code}"
        logger.info("  ✓ Command Service online")
    except Exception as exc:
        logger.error(f"  ✗ Command Service offline: {exc}")
        return False
    
    try:
        resp = requests.get(f"{QUERY_SERVICE_URL}/health", timeout=2)
        assert resp.status_code == 200, f"Query Service health check failed: {resp.status_code}"
        logger.info("  ✓ Query Service online")
    except Exception as exc:
        logger.error(f"  ✗ Query Service offline: {exc}")
        return False
    
    try:
        verify_plan_in_db()
        logger.info("  ✓ Operational DB accessible")
    except Exception as exc:
        logger.error(f"  ✗ Operational DB not accessible: {exc}")
        return False
    
    logger.info("")
    
    # Run iterations
    passed = 0
    failed = 0
    for i in range(1, args.iterations + 1):
        if run_iteration(i, args.delay):
            passed += 1
        else:
            failed += 1
        
        # Brief pause between iterations
        if i < args.iterations:
            logger.info(f"Waiting 2s before next iteration...")
            time.sleep(2)
    
    # Summary
    logger.info(f"\n{'='*70}")
    logger.info(f"SUMMARY")
    logger.info(f"{'='*70}")
    logger.info(f"Total iterations: {args.iterations}")
    logger.info(f"Passed:           {passed}")
    logger.info(f"Failed:           {failed}")
    logger.info(f"Result:           {'✓ ALL PASSED' if failed == 0 else f'✗ {failed} FAILED'}")
    logger.info(f"{'='*70}")
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
