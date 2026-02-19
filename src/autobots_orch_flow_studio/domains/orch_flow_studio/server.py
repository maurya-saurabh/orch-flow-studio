# ABOUTME: Orch Flow Studio-specific Chainlit entry point for the orch_flow_studio_chat use case.
# ABOUTME: Wires tracing, OAuth, and the shared streaming helper.

import json
import os
from typing import TYPE_CHECKING, Any

import chainlit as cl
import httpx
from autobots_devtools_shared_lib.common.observability import (
    TraceMetadata,
    flush_tracing,
    get_logger,
    init_tracing,
    set_conversation_id,
)
from autobots_devtools_shared_lib.dynagent import create_base_agent
from autobots_devtools_shared_lib.dynagent.ui import stream_agent_events
from dotenv import load_dotenv

from autobots_orch_flow_studio.common.utils.formatting import format_structured_output
from autobots_orch_flow_studio.domains.orch_flow_studio.settings import (
    init_orch_flow_studio_settings,
)
from autobots_orch_flow_studio.domains.orch_flow_studio.tools import register_orch_flow_studio_tools

if TYPE_CHECKING:
    from langchain_core.runnables import RunnableConfig

# Load environment variables from .env file
load_dotenv()

logger = get_logger(__file__)

# Application name for tracing and identification
APP_NAME = "orch_flow_studio_chat"

# Register Orch Flow Studio settings so shared-lib (dynagent) uses the same instance.
init_orch_flow_studio_settings()

# Registration must precede AgentMeta.instance() (called inside create_base_agent).
register_orch_flow_studio_tools()

NODE_RED_URL = os.environ.get("NODE_RED_URL", "http://localhost:1880").rstrip("/")
FLOWS_API_URL = f"{NODE_RED_URL}/flows"
FLOW_EXT = ".json"

# Folder for flow JSON files (save, load, list all use this folder when set)
# Set NODE_RED_FLOW_FOLDER to a directory path; flows save there, browse lists it, load uses it.
_flow_folder = os.environ.get("NODE_RED_FLOW_FOLDER", "").strip()
if _flow_folder:
    _flow_folder = os.path.abspath(_flow_folder)

# Default flow file path: NODE_RED_FLOW_PATH env, or {NODE_RED_FLOW_FOLDER}/saved_flows.json, or built-in default
NODE_RED_FLOW_PATH: str
if os.environ.get("NODE_RED_FLOW_PATH", "").strip():
    NODE_RED_FLOW_PATH = os.path.abspath(os.environ.get("NODE_RED_FLOW_PATH", "").strip())
elif _flow_folder:
    NODE_RED_FLOW_PATH = os.path.join(_flow_folder, "saved_flows.json")
else:
    NODE_RED_FLOW_PATH = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "node_red_flows", "saved_flows.json"
    )


def _get_flow_folder() -> str | None:
    """Return configured flow folder path if NODE_RED_FLOW_FOLDER is set, else None."""
    return _flow_folder if _flow_folder else None


def _get_flow_directory() -> str:
    """Return the directory containing flow JSON files (NODE_RED_FLOW_FOLDER or dirname of NODE_RED_FLOW_PATH)."""
    if _flow_folder:
        return os.path.abspath(_flow_folder)
    return os.path.dirname(NODE_RED_FLOW_PATH)


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
    return os.path.isfile(NODE_RED_FLOW_PATH)


def _read_flow_file():
    with open(NODE_RED_FLOW_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _read_flows_from_path(path: str):
    """Read flow JSON from a path; return list of flow nodes (handles array or {flows: []})."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "flows" in data:
        return data["flows"]
    return data if isinstance(data, list) else []


def _write_flow_file(flows, path: str):
    """Write flows JSON to the given absolute path."""
    path = os.path.abspath(path.strip())
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(flows, f, indent=2)


def _open_flows_message():
    return (
        f"**Open in new tab:** [Open Flows]({NODE_RED_URL}) — "
        "right-click → Open link in new tab, or Ctrl/Cmd+Click."
    )


async def _load_flows_then_send(flows, source_label: str, save_path: str | None = None):
    """POST flows to Flow and send success message with open link. Optionally store path for Update Flow."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        await _post_flows(client, flows)
    if save_path:
        cl.user_session.set("last_loaded_flow_path", save_path)
    else:
        cl.user_session.set("last_loaded_flow_path", None)
    if save_path:
        msg = f"Flow loaded from {source_label} into Flow. You can work on it, then use **Update Flow** to save changes back."
    else:
        msg = "Temp flow loaded. You can work on it, then use **Save Flow** to save with a name."
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
    logger.info("OAuth is not configured - anonymous access")
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
    """User ID for tracing and state; defaults to anonymous when OAuth is off."""
    user = cl.user_session.get("user")
    if user:
        return user.identifier[:200]
    return f"anonymous-{cl.context.session.thread_id}"[:200]


@cl.on_chat_start
async def start():
    """Initialize the chat session with the welcome agent."""
    # Create agent instance once and store it in session
    init_tracing()
    base_agent = create_base_agent()
    cl.user_session.set("base_agent", base_agent)

    # Prepare trace metadata for Langfuse observability (session-level)
    user_id = _get_user_identifier()
    cl.user_session.set("user_id", user_id)

    trace_metadata = TraceMetadata.create(
        session_id=cl.context.session.thread_id,
        app_name=APP_NAME,
        user_id=user_id,
        tags=[APP_NAME],
    )
    set_conversation_id(cl.context.session.thread_id)
    cl.user_session.set("trace_metadata", trace_metadata)

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
    """Handle incoming messages from the user."""
    set_conversation_id(cl.context.session.thread_id)
    if getattr(message, "command", None) == FLOW_COMMAND_ID:
        await cl.Message(
            content="**Flow tools** — choose one:",
            actions=_flow_tool_actions_choice(),
        ).send()
        return

    # Handle pending Load Flow: user attaches file to message or types cancel
    if cl.user_session.get(PENDING_LOAD_FLOW_KEY):
        cl.user_session.set(PENDING_LOAD_FLOW_KEY, False)
        elements = getattr(message, "elements", []) or []
        file_elements = [el for el in elements if getattr(el, "path", None)]
        if not file_elements and (message.content or "").strip().lower() == "cancel":
            await cl.Message(content="Load cancelled.").send()
            return
        if not file_elements:
            await cl.Message(
                content="No file attached. Please attach a flow `.json` file to your message (use the paperclip icon), or type `cancel` to abort."
            ).send()
            cl.user_session.set(PENDING_LOAD_FLOW_KEY, True)
            return
        el = file_elements[0]
        path = getattr(el, "path", None)
        if not path or not os.path.isfile(path):
            await cl.Message(content="Could not read attached file.").send()
            return
        try:
            flows = _read_flows_from_path(path)
            if not flows:
                await cl.Message(content="File is empty or not a valid flow JSON.").send()
                return
            upload_name = getattr(el, "name", "uploaded_flow.json")
            if not (upload_name or "").lower().endswith(FLOW_EXT):
                upload_name = f"{upload_name or 'uploaded_flow'}{FLOW_EXT}"
            save_path = os.path.join(_get_flow_directory(), upload_name)
            await _load_flows_then_send(flows, f"uploaded file `{upload_name}`", save_path=save_path)
        except httpx.ConnectError:
            await cl.Message(
                content=f"**Connection error** — Cannot reach Node-RED at `{NODE_RED_URL}`. Ensure Node-RED is running and `NODE_RED_URL` is correct."
            ).send()
        except httpx.HTTPStatusError as e:
            await cl.Message(
                content=f"**API error** ({e.response.status_code}) — Node-RED Admin API may be disabled. Enable it in Node-RED settings."
            ).send()
        except Exception as e:
            await cl.Message(content=f"**Load failed** — {e!s}").send()
        return

    # Handle pending Save Flow: user typed flow name in chat (handoff to UI)
    if cl.user_session.get(PENDING_SAVE_FLOW_KEY):
        cl.user_session.set(PENDING_SAVE_FLOW_KEY, False)
        flow_name = (message.content or "").strip()
        if not flow_name or flow_name.lower() == "cancel":
            await cl.Message(content="Save cancelled.").send()
            return
        if not flow_name.lower().endswith(FLOW_EXT):
            flow_name = f"{flow_name}{FLOW_EXT}"
        flow_dir = _get_flow_directory()
        os.makedirs(flow_dir, exist_ok=True)
        path = os.path.join(flow_dir, flow_name)
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                flows = await _get_flows(client)
            _write_flow_file(flows, path)
            await cl.Message(content=f"Flow saved to `{path}`.").send()
        except httpx.ConnectError:
            await cl.Message(
                content=f"**Connection error** — Cannot reach Node-RED. Ensure it's running at `{NODE_RED_URL}`."
            ).send()
        except httpx.HTTPStatusError as e:
            await cl.Message(
                content=f"**API error** ({e.response.status_code}) — Enable the Node-RED Admin API in settings."
            ).send()
        except Exception as e:
            await cl.Message(content=f"**Save failed** — {e!s}").send()
        return

    config: RunnableConfig = {
        "configurable": {
            "thread_id": cl.context.session.thread_id,
        },
        "recursion_limit": 50,
        "run_name": APP_NAME,  # Set trace name for Langfuse
    }

    # Reuse the same agent instance from session
    base_agent = cl.user_session.get("base_agent")
    if not base_agent:
        await cl.Message(
            content="**Session error** — Something went wrong during initialization. Please refresh the page and try again."
        ).send()
        return

    user_id = cl.user_session.get("user_id")

    input_state: dict[str, Any] = {
        "messages": [{"role": "user", "content": message.content}],
        "user_id": user_id,
        "app_name": APP_NAME,
        "session_id": cl.context.session.thread_id,
    }

    # Retrieve trace metadata from session
    trace_metadata = cl.user_session.get("trace_metadata")

    result = await stream_agent_events(
        agent=base_agent,
        input_state=input_state,
        config=config,
        on_structured_output=format_structured_output,
        enable_tracing=True,
        trace_metadata=trace_metadata,
    )
    logger.debug(f"Agent execution completed with result: {result}")


@cl.action_callback("flow_working_on_new")
async def on_flow_working_on_new(action: cl.Action):
    """Show Row 1: Open Flows, Save Flow."""
    await cl.Message(
        content="**Working on new** — choose an action:",
        actions=_flow_tool_actions_row1(),
    ).send()


@cl.action_callback("flow_working_on_existing")
async def on_flow_working_on_existing(action: cl.Action):
    """Show Row 2: List Flows, Load Flow, Update Flow."""
    await cl.Message(
        content="**Working on existing** — choose an action:",
        actions=_flow_tool_actions_row2(),
    ).send()


@cl.action_callback("open_flows")
async def on_open_flows(action: cl.Action):
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
async def on_save_flow(action: cl.Action):
    """Request flow name via chat to avoid blocking UI. User types name in chat."""
    cl.user_session.set(PENDING_SAVE_FLOW_KEY, True)
    await cl.Message(
        content="**Save Flow** — Type the flow name in the chat below (e.g. `my_flow`), or type `cancel` to abort. The chat input is ready for you."
    ).send()


@cl.action_callback("list_designer_flows")
async def on_list_designer_flows(action: cl.Action):
    """List all flow JSON files in the NODE_RED_FLOW_PATH directory (or NODE_RED_FLOW_FOLDER)."""
    dir_path = _get_flow_directory()
    if not os.path.isdir(dir_path):
        os.makedirs(dir_path, exist_ok=True)
    try:
        all_files = os.listdir(dir_path)
        json_files = sorted([f for f in all_files if f.lower().endswith(FLOW_EXT)])
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
            payload={"path": os.path.join(dir_path, f)},
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
    path = (action.payload or {}).get("path") if isinstance(action.payload, dict) else None
    if not path or not os.path.isfile(path):
        await cl.Message(content="Invalid or missing file path.").send()
        return
    try:
        flows = _read_flows_from_path(path)
        if not flows:
            await cl.Message(content=f"File is empty or not a valid flow JSON: `{path}`").send()
            return
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


@cl.action_callback("load_flow_upload")
async def on_load_flow_upload(action: cl.Action):
    """Request file via chat attachment. User attaches file or types cancel."""
    cl.user_session.set(PENDING_LOAD_FLOW_KEY, True)
    await cl.Message(
        content="**Load Flow** — Attach a flow JSON file to your next message (use the paperclip icon), or type `cancel` to abort. The chat input is ready for you."
    ).send()


@cl.action_callback("update_flow")
async def on_update_flow(action: cl.Action):
    """Save current flows back to the last loaded flow file."""
    path = cl.user_session.get("last_loaded_flow_path")
    if not path:
        await cl.Message(
            content="No flow loaded yet. Load a flow (from List Flows or Load Flow) first, then use Update Flow to save your changes back."
        ).send()
        return
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
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
    flush_tracing()
    logger.info("Chat session stopped")


if __name__ == "__main__":
    from chainlit.cli import run_chainlit

    run_chainlit(__file__)
