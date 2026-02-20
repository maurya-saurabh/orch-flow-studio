from autobots_devtools_shared_lib.common.observability import get_logger
from autobots_devtools_shared_lib.dynagent import BatchResult

logger = get_logger(__name__)


def log_batches(batch_result: BatchResult, step_name: str) -> None:
    """Log batch summary and per-record success/failure."""
    logger.info(
        "%s: %s total, %s succeeded, %s failed",
        step_name,
        batch_result.total,
        len(batch_result.successes),
        len(batch_result.failures),
    )
    for r in batch_result.results:
        if r.success:
            logger.info("  [%s] ok: %s...", r.index, (r.output or "")[:120])
        else:
            logger.info("  [%s] error: %s", r.index, r.error)
