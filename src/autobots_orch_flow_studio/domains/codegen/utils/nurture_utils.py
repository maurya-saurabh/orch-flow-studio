"""Utility helpers for the NURTURE agent."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Mapping

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def workspace_from_state(state: Mapping[str, Any]) -> dict:
    """Extract workspace fields for file server from state (when available)."""
    return {
        "user_name": state.get("user_name"),
        "repo_name": state.get("repo_name"),
        "jira_number": state.get("jira_number"),
    }


def get_lld_default_prompt() -> str:
    """Return default test input for behaviour list extraction when run as script."""
    return "Extract the behaviour list for the current workspace."
