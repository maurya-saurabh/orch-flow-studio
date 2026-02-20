# ABOUTME: Orch Flow Studio-specific Chainlit entry point for the orch_flow_studio_chat use case.
# ABOUTME: Wires OAuth and the shared flow tools.

import asyncio
import json
import logging
import os
import time
from pathlib import Path

import chainlit as cl
import httpx
from autobots_devtools_shared_lib.dynagent import create_base_agent
from dotenv import load_dotenv
from langchain_core.runnables import RunnableConfig

from autobots_orch_flow_studio.domains.orch_flow_studio.flow_conversion import (
    convert_unknown_nodes_to_designer,
    ensure_flow_order,
    flow_needs_conversion,
)
from autobots_orch_flow_studio.domains.orch_flow_studio.tools import register_orch_flow_studio_tools

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

# Ensure agent config is set when not provided (e.g. run from IDE)
if not os.environ.get("DYNAGENT_CONFIG_ROOT_DIR"):
    _config_dir = Path(__file__).resolve().parents[4] / "agent_configs" / "orch_flow_studio"
    if _config_dir.is_dir():
        os.environ["DYNAGENT_CONFIG_ROOT_DIR"] = str(_config_dir)

register_orch_flow_studio_tools()
_agent = create_base_agent()

# Application name for identification
APP_NAME = "orch_flow_studio_chat"

NODE_RED_URL = os.environ.get("NODE_RED_URL", "http://localhost:1880").rstrip("/")
FLOWS_API_URL = f"{NODE_RED_URL}/flows"
FLOW_EXT = ".json"

# Folder for flow JSON files (save, load, list all use this folder when set)
# Set NODE_RED_FLOW_FOLDER to a directory path; flows save there, browse lists it, load uses it.
_flow_folder_raw = os.environ.get("NODE_RED_FLOW_FOLDER", "").strip()
_flow_folder: str | None = str(Path(_flow_folder_raw).resolve()) if _flow_folder_raw else None

# Default flow file path: NODE_RED_FLOW_PATH env, or {NODE_RED_FLOW_FOLDER}/saved_flows.json, or built-in default
NODE_RED_FLOW_PATH: str
if os.environ.get("NODE_RED_FLOW_PATH", "").strip():
    NODE_RED_FLOW_PATH = str(Path(os.environ.get("NODE_RED_FLOW_PATH", "").strip()).resolve())
elif _flow_folder:
    NODE_RED_FLOW_PATH = str(Path(_flow_folder) / "saved_flows.json")
else:
    NODE_RED_FLOW_PATH = str(
        Path(__file__).resolve().parent.parent / "node_red_flows" / "saved_flows.json"
    )


def _get_flow_folder() -> str | None:
    """Return configured flow folder path if NODE_RED_FLOW_FOLDER is set, else None."""
    return _flow_folder if _flow_folder else None


def _get_flow_directory() -> str:
    """Return the directory containing flow JSON files (NODE_RED_FLOW_FOLDER or dirname of NODE_RED_FLOW_PATH)."""
    if _flow_folder:
        return str(Path(_flow_folder).resolve())
    return str(Path(NODE_RED_FLOW_PATH).resolve().parent)


# Reusable HTTP client for Node-RED API (connection pooling for faster loads)
_node_red_client: httpx.AsyncClient | None = None


def _get_node_red_client() -> httpx.AsyncClient:
    """Get or create shared httpx client for Node-RED API calls."""
    global _node_red_client
    if _node_red_client is None:
        _node_red_client = httpx.AsyncClient(
            timeout=120.0,  # Large flows can take time to deploy
            limits=httpx.Limits(max_keepalive_connections=2, max_connections=10),
        )
    return _node_red_client


def _flows_headers():
    return {"Node-RED-API-Version": "v1", "Content-Type": "application/json"}


async def _get_flows(client: httpx.AsyncClient):
    """GET current flows from Flow (v1 = array of nodes)."""
    r = await client.get(FLOWS_API_URL, headers=_flows_headers())
    r.raise_for_status()
    data = r.json()
    return data if isinstance(data, list) else data.get("flows", data)


async def _post_flows(client: httpx.AsyncClient, flows):
    """POST flows to Flow (v1 array)."""
    r = await client.post(FLOWS_API_URL, json=flows, headers=_flows_headers())
    r.raise_for_status()


def _flow_file_exists():
    return Path(NODE_RED_FLOW_PATH).is_file()


def _read_flow_file():
    with Path(NODE_RED_FLOW_PATH).open(encoding="utf-8") as f:
        return json.load(f)


def _read_flows_from_path(path: str):
    """Read flow JSON from a path; return list of flow nodes (handles array or {flows: []})."""
    with Path(path).open(encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "flows" in data:
        return data["flows"]
    return data if isinstance(data, list) else []


def _write_flow_file(flows, path: str):
    """Write flows JSON to the given absolute path."""
    p = Path(path.strip()).resolve()
    if p.parent:
        p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(flows, f, indent=2)


# Short delay after POST so Node-RED editor is ready when user opens the link (reduces need to refresh/click multiple times)
_FLOW_DEPLOY_SETTLE_SECONDS = 1.5


def _open_flows_message():
    # Cache-bust so opening the link forces a fresh load and shows the deployed flow
    open_url = f"{NODE_RED_URL}?t={int(time.time())}"
    return (
        f"[**Open Node-RED**]({open_url}) — open in a new tab to view your flow. "
        "**If Node-RED is already open, refresh that tab (F5)** to see the loaded flow."
    )


async def _load_flows_then_send(flows, source_label: str, save_path: str | None = None):
    """POST flows to Node-RED, wait for editor to settle, then send success message with open link."""
    client = _get_node_red_client()
    await _post_flows(client, flows)
    # Give Node-RED a moment to finish so the canvas shows the flow when user opens the link
    await asyncio.sleep(_FLOW_DEPLOY_SETTLE_SECONDS)
    if save_path:
        cl.user_session.set("last_loaded_flow_path", save_path)
    else:
        cl.user_session.set("last_loaded_flow_path", None)
    if save_path:
        msg = f"Flow loaded from {source_label} into Node-RED. You can work on it, then use **Update Flow** to save changes back."
    else:
        msg = "Temp flow loaded into Node-RED. You can work on it, then use **Save Flow** to save with a name."
    await cl.Message(content=f"{msg}\n\n{_open_flows_message()}").send()


def _flow_tool_actions_choice():
    """Initial choice: Working on new, Working on existing."""
    return [
        cl.Action(
            name="flow_working_on_new",
            label="Working on new",
            payload={"action": "new"},
            tooltip="Create or work on a new flow",
        ),
        cl.Action(
            name="flow_working_on_existing",
            label="Working on existing",
            payload={"action": "existing"},
            tooltip="Load and work on an existing flow",
        ),
    ]


def _flow_tool_actions_row1():
    """Row 1: Open Flows, Save Flow (for new flow)."""
    return [
        cl.Action(
            name="open_flows",
            label="Open Flows",
            payload={"action": "open"},
            tooltip="Open Flow in a new tab",
        ),
        cl.Action(
            name="save_flow",
            label="Save Flow",
            payload={"action": "save"},
            tooltip="Save current flows (you will be asked for the flow name)",
        ),
    ]


def _flow_tool_actions_row2():
    """Row 2: List Flows, Load Flow, Update Flow."""
    return [
        cl.Action(
            name="list_designer_flows",
            label="List Flows",
            payload={"action": "browse"},
            tooltip="List all flow JSON files in the flow directory; click one to load and open",
        ),
        cl.Action(
            name="load_flow_upload",
            label="Load Flow",
            payload={"action": "upload"},
            tooltip="Upload a flow JSON file, load into Flow, and get link to open",
        ),
        cl.Action(
            name="update_flow",
            label="Update Flow",
            payload={"action": "update"},
            tooltip="Save current flows back to the last loaded flow file",
        ),
    ]


FLOW_COMMAND_ID = "flow_tools"
PENDING_SAVE_FLOW_KEY = "pending_save_flow"
PENDING_LOAD_FLOW_KEY = "pending_load_flow"
LOAD_FLOW_IN_PROGRESS_KEY = "load_flow_in_progress"


# Check if OAuth is configured
OAUTH_ENABLED = bool(
    os.getenv("OAUTH_GITHUB_CLIENT_ID")
    and os.getenv("OAUTH_GITHUB_CLIENT_SECRET")
    and os.getenv("CHAINLIT_AUTH_SECRET")
)

# Only register OAuth callback if OAuth is enabled
if OAUTH_ENABLED:

    @cl.oauth_callback  # type: ignore[arg-type]
    def oauth_callback(
        provider_id: str,
        token: str,  # noqa: ARG001
        raw_user_data: dict,
        default_user: cl.User,
    ) -> cl.User | None:
        """Handle OAuth callback from GitHub.

        Args:
            provider_id: The OAuth provider ID (e.g., "github").
            token: The OAuth access token.
            raw_user_data: Raw user data from the provider.
            default_user: Default user object created by Chainlit.

        Returns:
            The authenticated user or None if authentication fails.
        """
        if provider_id != "github":
            logger.warning(f"Unsupported OAuth provider: {provider_id}")
            return None

        username = raw_user_data.get("login", "unknown")
        logger.info(f"User authenticated via GitHub: {username}")
        return default_user
else:
    # No OAuth - anonymous access
    pass


@cl.set_starters
async def set_starters(
    _user: cl.User | None = None,
    _chat_profile: str | None = None,
) -> list[cl.Starter]:
    """Suggested prompts to help users get started."""
    return [
        cl.Starter(
            label="Create a simple HTTP flow",
            message="Create a simple flow that receives HTTP requests and returns a greeting.",
        ),
        cl.Starter(
            label="Add a function node to process data",
            message="Add a function node that processes incoming JSON and returns a transformed response.",
        ),
        cl.Starter(
            label="Explain the current flow structure",
            message="Explain the structure of my current flow and what each node does.",
        ),
    ]


def _get_user_identifier() -> str:
    """User ID for session; defaults to anonymous when OAuth is off."""
    user = cl.user_session.get("user")
    if user:
        return user.identifier[:200]
    return f"anonymous-{cl.context.session.thread_id}"[:200]


@cl.on_chat_start
async def start():
    """Initialize the chat session with the welcome message."""
    user_id = _get_user_identifier()
    cl.user_session.set("user_id", user_id)

    welcome = """**Welcome to OrchFlow Studio**

I help you design, edit, and manage Node-RED flows using natural language. You can:

- **Design flows** — Use Flow Tools to design the flow
- **Code generation** — Generate code based on Low Level Design (LLD)

**Quick start:** Use the workflow icon to open the Flow editor, or tell me what flow you would like to create. How can I help you today?
"""
    await cl.Message(content=welcome).send()
    await cl.context.emitter.set_commands(
        [
            {
                "id": FLOW_COMMAND_ID,
                "description": "Flow Tools",
                "icon": "workflow",
                "button": False,
                "persistent": True,
            },
        ]
    )


@cl.on_message
async def on_message(message: cl.Message):
    run_config = RunnableConfig(
        configurable={"thread_id": cl.context.session.id},
        callbacks=[],
    )
    res = await _agent.ainvoke(
        {"messages": [{"role": "user", "content": message.content}]},
        run_config,
    )
    await cl.Message(content=res["messages"][-1].text).send()


@cl.action_callback("flow_working_on_new")
async def on_flow_working_on_new(_action: cl.Action):
    """Show Row 1: Open Flows, Save Flow."""
    await cl.Message(
        content="**Working on new** — choose an action:",
        actions=_flow_tool_actions_row1(),
    ).send()


@cl.action_callback("flow_working_on_existing")
async def on_flow_working_on_existing(_action: cl.Action):
    """Show Row 2: List Flows, Load Flow, Update Flow."""
    await cl.Message(
        content="**Working on existing** — choose an action:",
        actions=_flow_tool_actions_row2(),
    ).send()


@cl.action_callback("open_flows")
async def on_open_flows(_action: cl.Action):
    """Load temp/empty flow into Flow, then send open link."""
    try:
        await _load_flows_then_send([], "temp flow")
    except httpx.ConnectError:
        await cl.Message(
            content=f"**Connection error** — Cannot reach Node-RED. Ensure it's running at `{NODE_RED_URL}`."
        ).send()
    except httpx.HTTPStatusError as e:
        await cl.Message(
            content=f"**API error** ({e.response.status_code}) — Enable the Node-RED Admin API in settings."
        ).send()
    except Exception as e:
        await cl.Message(content=f"**Open failed** — {e!s}").send()


@cl.action_callback("save_flow")
async def on_save_flow(_action: cl.Action):
    """Request flow name via chat to avoid blocking UI. User types name in chat."""
    cl.user_session.set(PENDING_SAVE_FLOW_KEY, True)
    await cl.Message(
        content="**Save Flow** — Type the flow name in the chat below (e.g. `my_flow`), or type `cancel` to abort. The chat input is ready for you."
    ).send()


@cl.action_callback("list_designer_flows")
async def on_list_designer_flows(_action: cl.Action):
    """List all flow JSON files in the NODE_RED_FLOW_PATH directory (or NODE_RED_FLOW_FOLDER)."""
    dir_path = Path(_get_flow_directory())
    if not dir_path.is_dir():
        dir_path.mkdir(parents=True, exist_ok=True)
    try:
        json_files = sorted(f.name for f in dir_path.iterdir() if f.suffix.lower() == FLOW_EXT)
    except OSError as e:
        await cl.Message(content=f"Cannot list directory: {e!s}").send()
        return
    if not json_files:
        await cl.Message(content=f"No `.json` files found in `{dir_path}`").send()
        return
    # One action per file: click to load that file into Flow and open editor
    file_actions = [
        cl.Action(
            name="load_flow_from_path",
            label=f"Load: {f}",
            payload={"path": str(dir_path / f)},
            tooltip=f"Load {f} into Flow and open editor",
        )
        for f in json_files
    ]
    await cl.Message(
        content=f"**Flows in `{dir_path}`** — click a flow to load it into Flow and open:",
        actions=file_actions,
    ).send()


@cl.action_callback("load_flow_from_path")
async def on_load_flow_from_path(action: cl.Action):
    """Load flow from path (payload) into Flow and send open link."""
    if cl.user_session.get(LOAD_FLOW_IN_PROGRESS_KEY):
        await cl.Message(content="Flow load already in progress. Please wait…").send()
        return
    path = (action.payload or {}).get("path") if isinstance(action.payload, dict) else None
    if not path or not Path(path).is_file():
        await cl.Message(content="Invalid or missing file path.").send()
        return
    cl.user_session.set(LOAD_FLOW_IN_PROGRESS_KEY, True)
    try:
        await cl.Message(content="Reading flow file…").send()
        flows = _read_flows_from_path(path)
        if not flows:
            await cl.Message(content=f"File is empty or not a valid flow JSON: `{path}`").send()
            return
        if flow_needs_conversion(flows):
            await cl.Message(content="Converting custom nodes to placeholders…").send()
            flows = convert_unknown_nodes_to_designer(flows)
        else:
            ensure_flow_order(flows)
        await cl.Message(
            content="Loading flow into Node-RED… (wait for the next message, then open the link; refresh the Node-RED tab if the canvas is blank)"
        ).send()
        await _load_flows_then_send(flows, f"`{path}`", save_path=path)
    except httpx.ConnectError:
        await cl.Message(
            content=f"**Connection error** — Cannot reach Node-RED. Ensure it's running at `{NODE_RED_URL}`."
        ).send()
    except httpx.HTTPStatusError as e:
        await cl.Message(
            content=f"**API error** ({e.response.status_code}) — Enable the Node-RED Admin API in settings."
        ).send()
    except Exception as e:
        await cl.Message(content=f"**Load failed** — {e!s}").send()
    finally:
        cl.user_session.set(LOAD_FLOW_IN_PROGRESS_KEY, False)


@cl.action_callback("load_flow_upload")
async def on_load_flow_upload(_action: cl.Action):
    """Request file via chat attachment. User attaches file or types cancel."""
    cl.user_session.set(PENDING_LOAD_FLOW_KEY, True)
    await cl.Message(
        content="**Load Flow** — Attach a flow JSON file to your next message (use the paperclip icon), or type `cancel` to abort. The chat input is ready for you."
    ).send()


@cl.action_callback("update_flow")
async def on_update_flow(_action: cl.Action):
    """Save current flows back to the last loaded flow file."""
    path = cl.user_session.get("last_loaded_flow_path")
    if not path:
        await cl.Message(
            content="No flow loaded yet. Load a flow (from List Flows or Load Flow) first, then use Update Flow to save your changes back."
        ).send()
        return
    try:
        client = _get_node_red_client()
        flows = await _get_flows(client)
        _write_flow_file(flows, path)
        await cl.Message(content=f"Flow updated at `{path}`.").send()
    except httpx.ConnectError:
        await cl.Message(
            content=f"**Connection error** — Cannot reach Node-RED. Ensure it's running at `{NODE_RED_URL}`."
        ).send()
    except httpx.HTTPStatusError as e:
        await cl.Message(
            content=f"**API error** ({e.response.status_code}) — Enable the Node-RED Admin API in settings."
        ).send()
    except Exception as e:
        await cl.Message(content=f"**Update failed** — {e!s}").send()


@cl.on_stop
def on_stop() -> None:
    """Handle chat stop."""
    logger.debug("Chat session stopped")


if __name__ == "__main__":
    from chainlit.cli import run_chainlit

    run_chainlit(__file__)
