# ABOUTME: Flow conversion — replace unknown/custom Node-RED nodes with designer_node_existing.

import json
import os
from typing import Any

# Fallback known types when .config.nodes.json is missing (core + designer).
# NOTE: "unknown" is excluded — Node-RED uses it for missing node types; we replace those.
_FALLBACK_KNOWN_TYPES: frozenset[str] = frozenset({
    "tab",
    "junction",
    "inject",
    "debug",
    "complete",
    "catch",
    "status",
    "link in",
    "link out",
    "link call",
    "comment",
    "global-config",
    "function",
    "switch",
    "change",
    "range",
    "template",
    "delay",
    "trigger",
    "exec",
    "rbe",
    "tls-config",
    "http proxy",
    "mqtt in",
    "mqtt out",
    "mqtt-broker",
    "http in",
    "http response",
    "http request",
    "websocket in",
    "websocket out",
    "websocket-listener",
    "websocket-client",
    "tcp in",
    "tcp out",
    "tcp request",
    "udp in",
    "udp out",
    "csv",
    "html",
    "json",
    "xml",
    "yaml",
    "split",
    "join",
    "sort",
    "batch",
    "file",
    "file in",
    "watch",
    "subflow",
    "designer_node_existing",
    "designer_node_new",
})

_known_types_cache: set[str] | None = None


def _config_path() -> str:
    """Path to Node-RED .config.nodes.json relative to this package."""
    this_dir = os.path.dirname(os.path.abspath(__file__))
    # orch_flow_studio -> domains -> autobots_orch_flow_studio -> src
    return os.path.join(this_dir, "..", "..", "..", "node_red_flows", ".config.nodes.json")


def get_known_node_types() -> set[str]:
    """Load known node types from .config.nodes.json, or return built-in fallback.

    Caches result at module level.
    """
    global _known_types_cache
    if _known_types_cache is not None:
        return _known_types_cache

    path = os.path.normpath(_config_path())
    if not os.path.isfile(path):
        _known_types_cache = set(_FALLBACK_KNOWN_TYPES)
        return _known_types_cache

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        _known_types_cache = set(_FALLBACK_KNOWN_TYPES)
        return _known_types_cache

    known: set[str] = set()
    if isinstance(data, dict):
        for module_data in data.values():
            if isinstance(module_data, dict) and "nodes" in module_data:
                nodes = module_data["nodes"]
                if isinstance(nodes, dict):
                    for node_def in nodes.values():
                        if isinstance(node_def, dict) and "types" in node_def:
                            types_list = node_def["types"]
                            if isinstance(types_list, list):
                                known.update(t for t in types_list if isinstance(t, str))

    if not known:
        known = set(_FALLBACK_KNOWN_TYPES)
    else:
        known.add("tab")
        known.add("subflow")
        known.add("designer_node_existing")
        known.add("designer_node_new")
        known.discard("unknown")  # Replace unknown placeholders with designer_node_existing

    _known_types_cache = known
    return _known_types_cache


def _replace_node_if_unknown(node: dict[str, Any], known: set[str]) -> None:
    """Replace a single node with designer_node_existing if its type is unknown."""
    if not isinstance(node, dict):
        return
    node_type = node.get("type")
    if not isinstance(node_type, str):
        return
    if node_type in known:
        return
    if "id" not in node:
        return

    original_name = node.get("name") or node.get("label") or node_type
    display_name = f"{original_name} ({node_type})"

    wires = node.get("wires")
    if isinstance(wires, list) and len(wires) > 0:
        outputs = len(wires)
    else:
        outputs = 1

    # Ensure x, y are numbers (editor needs valid coords); default 0 if missing
    x = node.get("x")
    y = node.get("y")
    if x is None or not isinstance(x, (int, float)):
        x = 0
    if y is None or not isinstance(y, (int, float)):
        y = 0

    new_node: dict[str, Any] = {
        "id": node["id"],
        "type": "designer_node_existing",
        "name": display_name,
        "outputs": outputs,
        "z": node.get("z"),
        "x": int(x),
        "y": int(y),
        "wires": list(wires) if isinstance(wires, list) else [],
    }
    # Only preserve disabled; avoid copying info/env from unknown nodes (may be invalid)
    if node.get("disabled") is True:
        new_node["disabled"] = True

    node.clear()
    node.update(new_node)


def _process_node_list(nodes: list[Any], known: set[str]) -> None:
    """Process a list of nodes/flows, replacing unknown types; handle nested structure."""
    if not isinstance(nodes, list):
        return
    for item in nodes:
        if not isinstance(item, dict):
            continue
        # Nested flow container (tab/flow with nodes, configs, subflows)
        if "nodes" in item:
            _process_node_list(item.get("nodes"), known)
        if "configs" in item:
            _process_node_list(item.get("configs"), known)
        if "subflows" in item:
            for sub in item.get("subflows") or []:
                if isinstance(sub, dict) and "nodes" in sub:
                    _process_node_list(sub.get("nodes"), known)
        # Process this item as a node (has type and potentially wires)
        _replace_node_if_unknown(item, known)


def _order_flows_for_editor(flows: list[Any]) -> None:
    """Sort flat flow array so tabs and subflows appear first. Helps Node-RED editor load."""
    if not flows or not all(isinstance(n, dict) for n in flows):
        return
    # Check if nested (any item has "nodes" key) - don't sort nested structure
    if any("nodes" in n for n in flows if isinstance(n, dict)):
        return

    def _order_key(item: dict) -> int:
        t = (item.get("type") or "").strip()
        if t == "tab":
            return 0
        if t == "subflow":
            return 1
        return 2

    flows.sort(key=_order_key)


def ensure_flow_order(flows: list[Any]) -> None:
    """Sort flat flow array so tabs come first. Safe to call even when no conversion done."""
    _order_flows_for_editor(flows)


def flow_needs_conversion(flows: list[Any]) -> bool:
    """Quick scan: True if any node has unknown type and conversion is needed."""
    known = get_known_node_types()

    def _scan(items: list[Any]) -> bool:
        if not isinstance(items, list):
            return False
        for item in items:
            if not isinstance(item, dict):
                continue
            if "nodes" in item:
                if _scan(item.get("nodes")):
                    return True
            if "configs" in item:
                if _scan(item.get("configs")):
                    return True
            if "subflows" in item:
                for sub in item.get("subflows") or []:
                    if isinstance(sub, dict) and "nodes" in sub and _scan(sub.get("nodes")):
                        return True
            t = item.get("type")
            if isinstance(t, str) and t not in known:
                return True
        return False

    return _scan(flows)


def convert_unknown_nodes_to_designer(flows: list[Any]) -> list[Any]:
    """Replace unknown/custom nodes with designer_node_existing, preserving wires and layout.

    Handles flat arrays and nested flow structures (flows with nodes/configs/subflows).
    Also replaces type "unknown" (Node-RED placeholder for missing node types).
    Orders flat flows so tabs come first to improve Node-RED editor loading.

    Args:
        flows: List of flow nodes or flow objects (as dicts).

    Returns:
        Modified list (mutates in place).
    """
    if not flows:
        return flows

    known = get_known_node_types()
    _process_node_list(flows, known)
    _order_flows_for_editor(flows)
    return flows
