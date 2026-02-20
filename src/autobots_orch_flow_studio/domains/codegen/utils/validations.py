from __future__ import annotations

import os
from typing import TYPE_CHECKING

from autobots_devtools_shared_lib.common.observability.logging_utils import get_logger

if TYPE_CHECKING:
    from autobots_devtools_shared_lib.dynagent import BatchResult

logger = get_logger(__name__)


def parse_scenario_list(scenario_list: dict | list) -> list:
    """Validate and return scenario list from either {"scenario_list": [...]} or a raw list."""
    lst = (
        scenario_list.get("scenario_list")
        if isinstance(scenario_list, dict)
        else scenario_list
        if isinstance(scenario_list, list)
        else None
    )
    if not lst or not isinstance(lst, list):
        raise ValueError(
            "scenario_list: expected a non-empty list or dict with 'scenario_list' key"
        )
    return lst


def parse_model_list(model_list: dict | list) -> list:
    """Validate and return model list from either {"model_list": [...]} or a raw list."""
    lst = (
        model_list.get("model_list")
        if isinstance(model_list, dict)
        else model_list
        if isinstance(model_list, list)
        else None
    )
    if not lst or not isinstance(lst, list):
        raise ValueError("model_list: expected a non-empty list or dict with 'model_list' key")
    return lst


def parse_behaviour_list(behaviour_list: dict | list) -> list:
    """Validate and return behaviour list from either {"behaviour_list": [...]} or a raw list."""
    lst = (
        behaviour_list.get("behaviour_list")
        if isinstance(behaviour_list, dict)
        else behaviour_list
        if isinstance(behaviour_list, list)
        else None
    )
    if not lst or not isinstance(lst, list):
        raise ValueError(
            "behaviour_list: expected a non-empty list or dict with 'behaviour_list' key"
        )
    return lst


def _validate_batch_success(result: BatchResult, step_name: str) -> None:
    """Log batch failures; does not raise, so execution continues with partial results."""
    if result.failures:
        err = result.failures[0].error or "unknown"
        logger.warning(
            "%s: %s/%s records failed. First error: %s",
            step_name,
            len(result.failures),
            result.total,
            err,
        )


def _build_user_message(
    initial_input: str,
    user_name: str | None = None,
    repo_name: str | None = None,
    jira_number: str | None = None,
) -> str:
    """Prepend workspace context to the message so the behaviour-list-extractor agent can use it for file server calls."""
    workspace = user_name or os.getenv("WORKSPACE_USER_NAME")
    repo = repo_name or os.getenv("WORKSPACE_REPO_NAME")
    jira = jira_number or os.getenv("WORKSPACE_JIRA_NUMBER")
    if workspace and repo and jira:
        header = f"Workspace (use these for file server calls): user_name={workspace}, repo_name={repo}, jira_number={jira}\n\n"
        return header + initial_input
    return initial_input


def _raise_no_items() -> None:
    raise ValueError("Behaviour list extraction returned no items.")
