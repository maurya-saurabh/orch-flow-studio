import json

from autobots_devtools_shared_lib.common.observability import (
    get_logger,
)
from langchain.tools import ToolRuntime, tool

from autobots_agents_mer.domains.nurture.services.prepare_orch import prepare_gen
from autobots_agents_mer.models import MerState

logger = get_logger(__name__)


@tool
async def trigger_prepare_gen(runtime: ToolRuntime[None, MerState], _input: str) -> str:
    """Trigger prepare generation"""
    logger.info("Starting prepare generation...")
    _session_id = runtime.state.get("session_id", "default")
    result = prepare_gen()
    return json.dumps({"result": result})
