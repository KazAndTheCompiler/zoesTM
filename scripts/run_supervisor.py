#!/usr/bin/env python
"""
Dedicated background worker supervisor for zoesTM.

Runs multiple worker coroutines:
  - outbox dispatcher (processes pending webhook deliveries)
  - metrics snapshotter (periodic metrics collect)
  - event garbage collector (cleanup old events)

Supervisor restarts crashed workers and logs to stdout.
"""
import asyncio
import signal
import sys
import time
from datetime import datetime, UTC, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from apps.backend.app.services.outbox_worker import dispatch_once, snapshot_metrics
from apps.backend.app.db import tx, conn

GRACEFUL_SHUTDOWN = False


def handle_signal(signum, frame):
    global GRACEFUL_SHUTDOWN
    print(f"[supervisor] Received signal {signum}, initiating graceful shutdown...")
    GRACEFUL_SHUTDOWN = True


signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)


async def outbox_worker_loop():
    print("[outbox] worker starting")
    while not GRACEFUL_SHUTDOWN:
        try:
            res = dispatch_once(limit=20)
            if res['processed'] > 0:
                print(f"[outbox] Dispatched: {res['delivered']} delivered, {res['failed']} failed")
            await asyncio.sleep(5)
        except Exception as e:
            print(f"[outbox] error: {e}")
            import traceback
            traceback.print_exc()
            await asyncio.sleep(10)
    print("[outbox] worker stopping")


async def metrics_collector(interval_seconds: int = 30):
    print("[metrics] collector starting")
    while not GRACEFUL_SHUTDOWN:
        try:
            m = snapshot_metrics()
            # Log to stdout for monitoring; could also push to Prometheus endpoint
            print(f"[metrics] outbox_pending={m['outbox_pending']} outbox_retry_wait={m['outbox_retry_wait']} outbox_sent={m['outbox_sent']}")
        except Exception as e:
            print(f"[metrics] error: {e}")
        await asyncio.sleep(interval_seconds)
    print("[metrics] collector stopping")


async def gc_task(interval_hours: int = 24):
    print("[gc] housekeeping starting")
    while not GRACEFUL_SHUTDOWN:
        try:
            cutoff = datetime.now(UTC) - timedelta(days=30)
            with tx() as c:
                c.execute("DELETE FROM webhook_receipts WHERE delivered_at < ?", (cutoff.isoformat(),))
            print(f"[gc] cleaned receipts older than {cutoff.isoformat()}")
        except Exception as e:
            print(f"[gc] error: {e}")
        await asyncio.sleep(interval_hours * 3600)
    print("[gc] housekeeping stopping")


async def main():
    print("[supervisor] Starting zoesTM background workers")
    tasks = [
        asyncio.create_task(outbox_worker_loop()),
        asyncio.create_task(metrics_collector()),
        asyncio.create_task(gc_task()),
    ]
    # Wait until shutdown
    while not GRACEFUL_SHUTDOWN:
        await asyncio.sleep(1)
    print("[supervisor] Shutting down workers...")
    for t in tasks:
        t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    print("[supervisor] All workers stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    print("[supervisor] Exiting")
