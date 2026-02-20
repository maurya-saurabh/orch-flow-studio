# ABOUTME: Utility to create prompt for node kg extraction agent.

import json
import uuid
from typing import TYPE_CHECKING, Any

from autobots_devtools_shared_lib.common.observability import (
    TraceMetadata,
    get_logger,
    init_tracing,
    set_conversation_id,
)
from autobots_devtools_shared_lib.dynagent import AgentMeta, invoke_agent
from dotenv import load_dotenv

if TYPE_CHECKING:
    from langchain_core.runnables import RunnableConfig

from autobots_orch_flow_studio.configs.constants import (
    KB_PATH,
    KBE_APP_NAME,
    SCHEMA_PROCESSOR_AGENT,
)

logger = get_logger(__name__)
load_dotenv()
init_tracing()

APP_NAME = KBE_APP_NAME


def _compose_user_message(schema: dict, kb_path: str) -> str:
    """Build the user message containing KB_PATH and the dereferenced schema."""
    return json.dumps({"kb_path": kb_path, "schema": schema})


def build_node_kg(
    session_id: str = str(uuid.uuid4()),
    enable_tracing: bool = True,
) -> dict[str, Any]:
    """Orchestrate the Node KG build pipeline (steps 1-2).

    1. Retrieve the Node KG Schema for the ``node_kg_extraction`` agent.
    2. Invoke the ``schema_processor`` agent with the schema and KB_PATH
       as the user message.  The agent generates an extraction guide and
       writes it to the workspace via *write_file*.

    Args:
        session_id: Optional session ID for tracing (auto-generated if None).
        enable_tracing: Whether to enable Langfuse tracing (default True).

    Returns:
        The complete final state dict from the schema_processor agent execution.

    Raises:
        ValueError: If the schema cannot be retrieved or the agent name is invalid.
    """

    # --- Step 1: Get Node KG Schema ----------------------------------------
    logger.info("Step 1 - Retrieving Node KG Schema for agent 'node_kg_extraction'")
    meta = AgentMeta.instance()
    schema: dict | None = meta.schema_map.get("node_kg_extraction")
    if schema is None:
        raise ValueError("Failed to retrieve schema for agent 'node_kg_extraction'")

    logger.info("Schema retrieved successfully (%d chars)", len(schema))

    # --- Step 2: Invoke schema_processor agent -----------------------------
    agent_name = SCHEMA_PROCESSOR_AGENT
    logger.info(f"Step 2 - invoking '{agent_name}' agent with KB_PATH={KB_PATH}")

    user_message: str = _compose_user_message(schema, KB_PATH)

    set_conversation_id(session_id)

    logger.info(f"🔑 Generated session_id: {session_id}")

    config: RunnableConfig = {
        "configurable": {
            "thread_id": session_id,
            "agent_name": agent_name,
            "app_name": APP_NAME,
        },
    }

    input_state: dict = {
        "messages": [{"role": "user", "content": user_message}],
        "agent_name": agent_name,
        "session_id": session_id,
    }

    # Prepare trace metadata
    trace_metadata = TraceMetadata(
        session_id=session_id,
        app_name=APP_NAME,
        user_id=agent_name,
        tags=[APP_NAME, agent_name, "sync"],
    )

    logger.info(f"Invoking SYNC agent '{agent_name}' for {APP_NAME}")
    result = invoke_agent(
        agent_name=agent_name,
        input_state=input_state,
        config=config,
        trace_metadata=trace_metadata,
        enable_tracing=enable_tracing,
    )

    logger.info(f"Prompt generated successfully for {APP_NAME}")

    return result


if __name__ == "__main__":
    logger.info("Running node-kb-builder")
    build_result = build_node_kg()
    logger.info(f"Build result keys: {list(build_result.keys())}")
