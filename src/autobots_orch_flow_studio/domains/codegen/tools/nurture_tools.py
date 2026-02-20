# ABOUTME: NURTURE use-case tools — the 10 document-management tools that NURTURE registers.
# ABOUTME: Context (component/version) lives in workspace/_doc_context.json, not state.

from autobots_devtools_shared_lib.common.observability import (
    get_logger,
)
from langchain.tools import ToolRuntime, tool

from autobots_agents_mer.common.tools.workspace_tools import get_workspace_context_tool
from autobots_agents_mer.domains.nurture.services.behaviour_gen import trigger_behaviour_gen
from autobots_agents_mer.domains.nurture.services.model_gen import trigger_model_gen
from autobots_agents_mer.domains.nurture.services.scenario_gen import trigger_scenario_gen
from autobots_agents_mer.domains.nurture.tools.prepare_tools import trigger_prepare_gen
from autobots_agents_mer.models import MerState


@tool
def get_context() -> str:
    """Return current SDLC/workspace context (stub when sdlcReqContext not available). Returns empty JSON."""
    return "{}"


@tool
def set_sdlc_context() -> str:
    """Set SDLC context (stub when not connected to context store). No-op."""
    return "OK"


logger = get_logger(__name__)


@tool
async def get_orchestrators():
    """Return a list of available orchestrators"""
    logger.info("Fetching list of orchestrators...")
    return [
        trigger_prepare_gen,
        trigger_behaviour_gen,
        trigger_model_gen,
        trigger_scenario_gen,
    ]


@tool
async def prepare_gen(runtime: ToolRuntime[None, MerState], _input: str) -> str:
    """Trigger prepare generation."""
    logger.info("Starting prepare generation...")
    return await trigger_prepare_gen(runtime, _input)  # pyright: ignore[reportCallIssue]


@tool
async def trigger_behaviour_gen_tool(runtime: ToolRuntime[None, MerState]) -> str:
    """Trigger behaviour generation."""
    logger.info("Starting behaviour generation...")
    trigger_behaviour_gen(state=runtime.state)
    return "Behaviour generation completed successfully."


@tool
async def trigger_model_gen_tool(runtime: ToolRuntime[None, MerState]) -> str:
    """Trigger model generation."""
    logger.info("Starting model generation...")
    trigger_model_gen(state=runtime.state)
    return "Model generation completed successfully."


@tool
async def trigger_scenario_gen_tool(runtime: ToolRuntime[None, MerState]) -> str:
    """Trigger scenario generation."""
    logger.info("Starting scenario generation...")
    trigger_scenario_gen(state=runtime.state)
    return "Scenario generation completed successfully."


def register_nurture_tools() -> None:
    """Register NURTURE tools into the dynagent usecase pool."""
    from autobots_devtools_shared_lib.dynagent import (
        register_usecase_tools,
    )

    register_usecase_tools(
        [
            get_orchestrators,
            trigger_prepare_gen,
            trigger_behaviour_gen_tool,  # @tool; do not use trigger_behaviour_gen (plain function has no .name)
            trigger_model_gen_tool,
            trigger_scenario_gen_tool,
            get_context,
            set_sdlc_context,
            get_workspace_context_tool,
        ]
    )
