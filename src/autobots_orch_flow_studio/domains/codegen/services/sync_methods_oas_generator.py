# ABOUTME: Utility to create OAS for sync methods extraction agent.

import json
import uuid
from pathlib import Path

from autobots_devtools_shared_lib.common.observability import (
    TraceMetadata,
    get_logger,
    init_tracing,
    set_conversation_id,
)
from autobots_devtools_shared_lib.dynagent import (
    AgentMeta,
    BatchResult,
    batch_invoker,
    get_batch_enabled_agents,
)
from dotenv import load_dotenv

from autobots_orch_flow_studio.configs.constants import (
    KB_PATH,
)

logger = get_logger(__name__)
load_dotenv()
init_tracing()

APP_NAME = "orch-flow-studio"


def _compose_user_message(schema: dict, kb_path: str) -> str:
    """Build the user message containing KB_PATH and the dereferenced schema."""
    return json.dumps({"kb_path": kb_path, "schema": schema})


def _fetch_sync_methods_list(filename: str) -> list[str]:
    """Fetch the list of sync method names from the input JSON file.

    Reads 2-sync-methods.json from data/<filename>/json/ and returns the methods
    as a list of strings. The JSON structure contains:
    - modelName: Name of the model/class
    - methods: Array of method objects with name, parameters (optional), and do (description)

    Args:
        filename: Directory name under INPUT_DATA_BASE_PATH (e.g. MER-12345---Party-Feature).

    Returns:
        List of sync method records in format "file: <filename>, model: <modelName>, method: <method_name>".
    """
    sync_methods_path = Path(
        "/Users/varunmodi/Documents/autobots-multi-repo-ws/orch-flow-studio/data", filename, "json", "2-sync-methods.json"
    )
    with sync_methods_path.open(encoding="utf-8") as f:
        data = json.load(f)
    logger.info(f"Sync methods list: {data}")
    records = []
    model_name = data.get("modelName", "")
    methods = data.get("methods", [])
    
    for method in methods:
        method_name = method.get("name", "")
        if not method_name:
            continue
        
        # Format: file: <filename>, model: <modelName>, method: <method_name>
        text = f"file: {filename}, model: {model_name}, method: {method_name}"
        records.append(text)
    
    return records


def sync_methods_oas_batch(agent_name: str, records: list[str], user_id: str) -> BatchResult:
    """Run a batch through dynagent, gated to batch-enabled agents only.

    Args:
        agent_name: Must be a batch-enabled agent from agents.yaml.
        records:    Non-empty list of plain-string prompts.
        user_id:    User ID for tracing.

    Returns:
        BatchResult forwarded from batch_invoker.

    Raises:
        ValueError: If agent_name is not batch-enabled or records is empty.
    """
    session_id = str(uuid.uuid4())
    set_conversation_id(session_id)
    logger.info(
        f"sync_methods_batch starting: agent={agent_name} records={len(records)} user_id={user_id}"
    )

    codegen_agents = get_batch_enabled_agents()

    if agent_name not in codegen_agents:
        raise ValueError(
            f"Agent '{agent_name}' is not enabled for batch processing. "
            f"Valid batch-enabled agents: {', '.join(codegen_agents)}"
        )

    if not records:
        raise ValueError("records must not be empty")

    init_tracing()

    trace_metadata = TraceMetadata.create(
        session_id=session_id,
        app_name=f"{APP_NAME}_{agent_name}-batch_invoker",
        user_id=user_id,
        tags=[APP_NAME, agent_name, "batch"],
    )

    result = batch_invoker(
        agent_name,
        records,
        trace_metadata=trace_metadata,
    )

    logger.info(
        f"sync_methods_batch complete: agent={agent_name} successes={len(result.successes)} "
        f"failures={len(result.failures)}"
    )

    return result


def build_sync_methods_oas(
    session_id: str | None = None,
    filename: str = "",
) -> BatchResult:
    """Orchestrate the Sync Methods OAS build pipeline.

    1. Retrieve the Sync Methods Schema for the ``sync_oas_generator`` agent.
    2. Invoke the ``sync_oas_generator`` agent with the schema and KB_PATH
       as the user message.  The agent generates OAS files and
       writes them to the workspace via *write_file*.

    Args:
        session_id: Optional session ID for tracing (auto-generated if None).
        filename: Directory name under data workspace (e.g. MER-12345---Party-Feature).

    Returns:
        BatchResult from the sync_oas_generator agent execution.

    Raises:
        ValueError: If the schema cannot be retrieved or the agent name is invalid.
    """

    # --- Step 1: Get Sync Methods Schema ----------------------------------------
    logger.info("Step 1 - Retrieving Sync Methods Schema for agent 'sync_oas_generator'")
    meta = AgentMeta.instance()
    schema: dict | None = meta.schema_map.get("sync_oas_generator")
    if schema is None:
        raise ValueError("Failed to retrieve schema for agent 'sync_oas_generator'")

    logger.info("Schema retrieved successfully (%d chars)", len(schema))

    # --- Step 2: Invoke sync_oas_generator agent -----------------------------
    agent_name = "sync_oas_generator"
    logger.info(f"Step 2 - invoking '{agent_name}' agent with KB_PATH={KB_PATH}")

    if session_id is None:
        session_id = str(uuid.uuid4())
    set_conversation_id(session_id)

    logger.info(f"🔑 Generated session_id: {session_id}")

    # Prepare trace metadata
    trace_metadata = TraceMetadata(
        session_id=session_id,
        app_name=APP_NAME,
        user_id=agent_name,
        tags=[APP_NAME, agent_name, "sync"],
    )

    logger.info(f"Invoking SYNC agent '{agent_name}' for {APP_NAME}")
    records = _fetch_sync_methods_list(filename)
    result = batch_invoker(
        agent_name,
        records,
        trace_metadata=trace_metadata,
    )

    logger.info(f"Sync methods OAS generated successfully for {APP_NAME}")
    return result


if __name__ == "__main__":
    logger.info("Running sync-methods-oas-builder")
    build_result = build_sync_methods_oas(filename="MER-12345---Party-Feature")
