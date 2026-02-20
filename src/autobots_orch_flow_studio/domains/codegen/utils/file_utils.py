"""Shared read/write utilities for nurture gen meta files (agentic-generator-meta/...)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from autobots_devtools_shared_lib.common.observability import get_logger

from autobots_agents_mer.common.utils.context_utils import get_workspace_context
from autobots_agents_mer.common.utils.file_service_utils import mer_read_file, mer_write_file
from autobots_agents_mer.domains.nurture.constants import AGENTIC_GENERATOR_META

if TYPE_CHECKING:
    from collections.abc import Mapping

logger = get_logger(__name__)


def read_meta_json_list_file(
    state: Mapping[str, Any],
    meta_subdir: str,
    file_name: str,
    error_label: str,
    list_key: str,
) -> dict[str, list[Any]]:
    """Read a JSON list from agentic-generator-meta/{meta_subdir}/{jira_number}/{file_name}.

    Resolves workspace path and jira_number from state, reads via file server,
    parses JSON and validates it is a list. Returns {list_key: list}.

    Args:
        state: MerState (or similar) with user_name, repo_name, jira_number.
        meta_subdir: e.g. FBP_BEHAVIOUR_META, FBP_SCENARIO_META, FBP_MODEL_META from constants.
        file_name: e.g. BEHAVIOUR_LIST_JSON, SCENARIO_LIST_JSON, MODEL_LIST_JSON from constants.
        error_label: Prefix for error messages, e.g. "behaviour_list", "scenario_list".
        list_key: Key for the returned dict, e.g. "behaviour_list", "scenario_list", "model_list".

    Returns:
        Dict with single key list_key mapping to the parsed JSON list.

    Raises:
        ValueError: If workspace_base_path is missing or read fails.
        TypeError: If file content is not a JSON array.
    """
    ws = get_workspace_context(state)
    workspace_base_path = ws.get("workspace_base_path", "").strip()
    if not workspace_base_path:
        raise ValueError(
            "get_workspace_context did not return workspace_base_path; ensure user_name, repo_name, jira_number are set"
        )
    jira_number = state.get("jira_number", "").strip()
    path = f"{workspace_base_path}/{AGENTIC_GENERATOR_META}/{meta_subdir}/{jira_number}/{file_name}"
    content = mer_read_file(path, state)
    if content.startswith("Error"):
        raise ValueError(f"{error_label}: failed to read {path}: {content}")
    lst = json.loads(content)
    if not isinstance(lst, list):
        raise TypeError(f"{error_label}: expected JSON array in {path}, got {type(lst).__name__}")
    return {list_key: lst}


def write_meta_json_file(
    state: Mapping[str, Any],
    meta_subdir: str,
    file_name: str,
    content: str | list[Any] | dict[str, Any],
    error_label: str,
) -> str:
    """Write JSON content to agentic-generator-meta/{meta_subdir}/{jira_number}/{file_name}.

    Resolves workspace path and jira_number from state, serializes content if not already a string,
    writes via file server, and raises ValueError on failure.

    Args:
        state: MerState (or similar) with user_name, repo_name, jira_number.
        meta_subdir: e.g. FBP_BEHAVIOUR_META, FBP_SCENARIO_META, FBP_MODEL_META from constants.
        file_name: e.g. BEHAVIOUR_LIST_JSON, SCENARIO_LIST_JSON, MODEL_LIST_JSON from constants.
        content: Data to write; dict/list are serialized with json.dumps(..., indent=2).
        error_label: Prefix for error messages, e.g. "behaviour_list", "scenario_list".

    Returns:
        Result string from mer_write_file (for logging).

    Raises:
        ValueError: If workspace_base_path is missing or write fails.
    """
    ws = get_workspace_context(state)
    workspace_base_path = ws.get("workspace_base_path", "").strip()
    if not workspace_base_path:
        raise ValueError(
            "get_workspace_context did not return workspace_base_path; ensure user_name, repo_name, jira_number are set"
        )
    jira_number = state.get("jira_number", "").strip()
    path = f"{workspace_base_path}/{AGENTIC_GENERATOR_META}/{meta_subdir}/{jira_number}/{file_name}"
    payload = content if isinstance(content, str) else json.dumps(content, indent=2)
    result = mer_write_file(path, payload, state=state)
    if result.startswith("Error"):
        raise ValueError(f"{error_label}: failed to write {path}: {result}")
    logger.info(f"Wrote {error_label} via file server: {result}")
    return result
