# ABOUTME: Convert LLD model markdown files in a folder to JSON; write to sibling json/ folder.

import json
import re
import warnings
from pathlib import Path


def _parse_is_new_model(line: str) -> bool:
    """Parse '### Is New Model: False' or 'True' or 'NEW' / 'EXISTING' / 'OLD'."""
    line = line.strip().lower()
    if "is new model:" in line:
        rest = line.split("is new model:")[-1].strip()
        if rest in ("true", "new"):
            return True
        if rest in ("false", "existing", "old"):
            return False
    return False


def _cell_at(row: list[str], i: int | None) -> str:
    """Return cell at index i, or empty string if out of range."""
    if i is None or i >= len(row):
        return ""
    return (row[i] or "").strip()


def _parse_table_row(row: str) -> list[str]:
    """Parse a markdown table row into cell strings (exclude leading/trailing empty from pipes)."""
    parts = row.split("|")
    return [c.strip() for c in parts[1:-1] if len(parts) > 2]


def _header_to_key(header: str) -> str:
    """Convert table header to camelCase key (e.g. 'Column Name' -> 'columnName')."""
    s = re.sub(r"[^\w\s]", "", header.lower())
    parts = s.split()
    if not parts:
        return header or "field"
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def _parse_generic_table(content: str) -> tuple[list[str], list[dict]]:
    """Parse first markdown table in content. Returns (list of header keys, list of row objects)."""
    lines = [ln.strip() for ln in content.strip().splitlines() if ln.strip()]
    for i, line in enumerate(lines):
        if not line.startswith("|") or "---" in line:
            continue
        header_cells = _parse_table_row(line)
        if not header_cells:
            continue
        keys = [_header_to_key(h) for h in header_cells]
        rows: list[dict] = []
        for j in range(i + 2, len(lines)):
            row_line = lines[j]
            if not row_line.startswith("|"):
                break
            cells = _parse_table_row(row_line)
            if not cells or {c.strip() for c in cells} <= {""}:
                continue
            row = {keys[k]: (cells[k].strip() if k < len(cells) else "") for k in range(len(keys))}
            rows.append(row)
        return (keys, rows)
    return ([], [])


def _model_table_header_indices(header_cells: list[str]) -> dict[str, int | None]:
    """Return map of column role -> index for Column Name, Data Type, Business Key, Mandatory, Properties, Description."""
    indices: dict[str, int | None] = {
        "col_name": None,
        "data_type": None,
        "business_key": None,
        "mandatory": None,
        "properties": None,
        "description": None,
    }
    for i, h in enumerate(header_cells):
        h_lower = h.lower()
        if "column name" in h_lower:
            indices["col_name"] = i
        elif "data type" in h_lower:
            indices["data_type"] = i
        elif "business key" in h_lower and "mandatory" not in h_lower:
            indices["business_key"] = i
        elif "mandatory" in h_lower:
            indices["mandatory"] = i
        elif "properties" in h_lower and "can be enum" not in h_lower:
            indices["properties"] = i
        elif "description" in h_lower:
            indices["description"] = i
    return indices


def _apply_8cell_index_override(
    idx: dict[str, int | None],
    n_cells: int,
    n_header: int,
) -> dict[str, int | None]:
    """When data row has 8 columns and header has 10, use fixed indices for key/mandatory/props/description."""
    if n_cells == 8 and n_header >= 10:
        idx = dict(idx)
        idx["business_key"] = 3
        idx["mandatory"] = 4
        idx["properties"] = 5
        idx["description"] = 7
    return idx


def _row_to_field_dict(cells: list[str], idx: dict[str, int | None]) -> dict:
    """Build one field entry from a data row and column indices."""

    def cell(i: int | None, default: str = "") -> str:
        if i is None or i >= len(cells):
            return default
        return (cells[i] or "").strip()

    def y_n(s: str) -> bool:
        return str(s).upper().startswith("Y")

    return {
        "type": cell(idx["data_type"]) or "String",
        "businessKey": y_n(cell(idx["business_key"])),
        "mandatory": y_n(cell(idx["mandatory"])),
        "properties": cell(idx["properties"]),
        "description": cell(idx["description"]).replace(" ", ""),
    }


def _parse_model_table(table_text: str) -> dict:
    """Parse markdown table into fields dict for one model.

    Expected columns (by header): Column Name, Data Type, Business Key [Y/N],
    Mandatory [Y/N], Properties, Description. Empty cells are preserved for alignment.
    """
    lines = [ln.strip() for ln in table_text.strip().splitlines() if ln.strip()]
    if len(lines) < 2:
        return {}

    header_cells = _parse_table_row(lines[0])
    idx = _model_table_header_indices(header_cells)
    n_header = len(header_cells)
    fields: dict = {}

    for line in lines[2:]:
        cells = _parse_table_row(line)
        if not cells:
            continue
        col_name = _cell_at(cells, idx["col_name"])
        if not col_name or col_name.strip() == "---":
            continue

        row_idx = _apply_8cell_index_override(idx, len(cells), n_header)
        fields[col_name] = _row_to_field_dict(cells, row_idx)

    return fields


def _parse_models_md(content: str) -> dict:
    """Parse full models markdown content into the target JSON structure.

    Sections: ## 1.1 ModelName, ### Is New Model: ..., ### Model Structure: table.
    Returns a dict keyed by model name with isNewModel and fields.
    """
    result: dict = {}
    # Split by ## 1.1 ModelName (optional number and dot, then model name)
    model_section_re = re.compile(r"^##\s*\d+\.\d+\s+(\w+)\s*$", re.MULTILINE)
    sections = model_section_re.split(content)
    # sections[0] is intro; then [name1, body1, name2, body2, ...]
    if len(sections) < 2:
        return result

    for i in range(1, len(sections) - 1, 2):
        model_name = sections[i].strip()
        body = sections[i + 1]

        is_new_model = False
        table_text = ""

        in_table = False
        table_lines: list[str] = []

        for line in body.splitlines():
            line_stripped = line.strip()
            if line_stripped.startswith("### Is New Model:"):
                is_new_model = _parse_is_new_model(line_stripped)
            elif line_stripped.startswith("### Model Structure:"):
                in_table = True
                table_lines = []
            elif in_table:
                if (
                    line_stripped.startswith("|") and "---" in line_stripped
                ) or "|" in line_stripped:
                    table_lines.append(line)
                elif table_lines and not line_stripped.startswith("|"):
                    in_table = False
                else:
                    table_lines.append(line)
            if not in_table and table_lines and line_stripped and not line_stripped.startswith("|"):
                in_table = False
        table_text = "\n".join(table_lines)

        fields = _parse_model_table(table_text)
        result[model_name] = {"isNewModel": is_new_model, "fields": fields}

    return result


def _parse_background_md(content: str) -> dict:
    """Parse background markdown into object: type, title, sections (## header -> content)."""
    out: dict = {"type": "background", "title": "", "sections": {}}
    lines = content.splitlines()
    current_section: str | None = None
    current_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# "):
            out["title"] = re.sub(r"^#\s*\d*\.?\s*", "", stripped).strip()
            current_section = None
            current_lines = []
        elif stripped.startswith("## "):
            if current_section is not None:
                out["sections"][current_section] = "\n".join(current_lines).strip()
            current_section = re.sub(r"^##\s*", "", stripped).strip().lower().replace(" ", "")
            if not current_section:
                current_section = "content"
            current_lines = []
        else:
            if current_section is None:
                current_section = "intro"
                if "sections" not in out or not out["sections"]:
                    out["sections"] = {}
            current_lines.append(line)
    if current_section is not None:
        out["sections"][current_section] = "\n".join(current_lines).strip()
    return out


def _strip_numbered_title(s: str) -> str:
    """Strip leading 'N. ' and trailing ':' from title (e.g. '2. Sync Methods' -> 'Sync Methods')."""
    s = re.sub(r"^\s*\d+\.\s*", "", (s or "").strip()).strip().rstrip(":")
    return s or "Untitled"


def _parse_sync_methods_md(content: str) -> dict:
    """Parse sync methods markdown into object: type, title, methods (array of objects)."""
    title_match = re.search(r"^#\s*(.+)$", content, re.MULTILINE)
    title = _strip_numbered_title(title_match.group(1)) if title_match else "Sync Methods"
    _, rows = _parse_generic_table(content)
    return {"type": "syncMethods", "title": title, "methods": rows}


def _parse_async_methods_md(content: str) -> dict:
    """Parse async methods markdown into object: type, title, methods (array of objects)."""
    title_match = re.search(r"^#\s*(.+)$", content, re.MULTILINE)
    title = _strip_numbered_title(title_match.group(1)) if title_match else "Async Methods"
    _, rows = _parse_generic_table(content)
    return {"type": "asyncMethods", "title": title, "methods": rows}


def _parse_behaviours_md(content: str) -> dict:
    """Parse behaviours markdown into object: type, title, intro, nodes (array of objects)."""
    title_match = re.search(r"^#\s*(.+)$", content, re.MULTILINE)
    title = _strip_numbered_title(title_match.group(1)) if title_match else "Behaviours"
    intro_lines: list[str] = []
    in_intro = True
    for line in content.splitlines():
        s = line.strip()
        if s.startswith("## ") or (
            s.startswith("|") and "---" not in s and "behaviour name" in s.lower()
        ):
            in_intro = False
            break
        if in_intro and s and not s.startswith("|"):
            intro_lines.append(s)
    _, rows = _parse_generic_table(content)
    return {
        "type": "behaviours",
        "title": title,
        "intro": "\n".join(intro_lines).strip(),
        "nodes": rows,
    }


def convert_models_md_to_json(md_path: Path) -> dict:
    """Read a single model markdown file and return the JSON-serializable dict."""
    text = md_path.read_text(encoding="utf-8")
    return _parse_models_md(text)


def _convert_lld_md_to_structured_json(md_path: Path) -> dict:
    """Convert a single LLD markdown file to a structured object (no raw content string).

    Dispatches by file stem: models -> model schema; 0-background, 2-sync-methods, etc.
    -> typed object with sections or table rows as arrays of objects.
    """
    text = md_path.read_text(encoding="utf-8")
    stem = md_path.stem

    # 1-models: model schema (existing parser)
    if stem == "1-models":
        data = _parse_models_md(text)
        if data:
            return data

    # Known LLD section types -> object structure
    if stem == "0-background":
        return _parse_background_md(text)
    if stem == "2-sync-methods":
        return _parse_sync_methods_md(text)
    if stem == "3-async-methods":
        return _parse_async_methods_md(text)
    if stem == "4-behaviours":
        return _parse_behaviours_md(text)

    # Fallback: still return object with type and content for unknown stems
    return {"type": "markdown", "content": text}


def lld_folder_to_json_folder(input_folder: str | Path) -> Path:
    """Convert all markdown files in input_folder to JSON in a sibling json/ folder.

    Input folder e.g. data/MER-12345---Party-Feature/lld-split/
    Output folder e.g. data/MER-12345---Party-Feature/json/

    Each .md file is converted to a structured JSON object (no single content string):
    - 1-models.md -> model schema (model name -> { isNewModel, fields })
    - 0-background.md -> { type, title, sections }
    - 2-sync-methods.md -> { type, title, methods: [ {...}, ... ] }
    - 3-async-methods.md -> { type, title, methods: [ {...}, ... ] }
    - 4-behaviours.md -> { type, title, intro, nodes: [ {...}, ... ] }

    Args:
        input_folder: Path to folder containing .md files (e.g. lld-split).

    Returns:
        Path to the output folder (json sibling of input_folder).

    Raises:
        FileNotFoundError: If input_folder does not exist or is not a directory.
    """
    in_dir = Path(input_folder).resolve()
    if not in_dir.is_dir():
        raise FileNotFoundError(f"Input folder is not a directory: {in_dir}")

    out_dir = in_dir.parent / "json"
    out_dir.mkdir(parents=True, exist_ok=True)

    for md_file in sorted(in_dir.glob("*.md")):
        json_file = out_dir / f"{md_file.stem}.json"
        try:
            data = _convert_lld_md_to_structured_json(md_file)
            json_file.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as e:
            warnings.warn(f"Skipping {md_file}: {e}", stacklevel=0)

    return out_dir


if __name__ == "__main__":
    out = lld_folder_to_json_folder(
        "/Users/saurabh/Documents/server/orch-ai-studio/data/MER-12345---Party-Feature/lld-split"
    )
    print(f"Wrote JSON files to: {out}")
