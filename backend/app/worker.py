"""
BomaSec — Redpanda Consumer Worker (Placeholder)
=================================================
Stub for Phase 1 — will be implemented in Phase 3.
Starts, logs readiness, and waits so the container stays alive.
"""

import logging
import time
import signal
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("bomasec.worker")

_running = True


def _signal_handler(signum, frame):
    global _running
    logger.info("Received shutdown signal (%s). Exiting gracefully...", signum)
    _running = False


signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)


def main():
    logger.info("╔══════════════════════════════════════════════════════╗")
    logger.info("║  BomaSec Worker — Phase 1 Placeholder               ║")
    logger.info("║  Consumer logic will be implemented in Phase 3.     ║")
    logger.info("╚══════════════════════════════════════════════════════╝")

    while _running:
        time.sleep(5)

    logger.info("Worker shut down cleanly.")
    sys.exit(0)


if __name__ == "__main__":
    main()
