# ABOUTME: Split a single LLD MD file into multiple MD files by first-level (#) headers.

import argparse
import re
import sys
from pathlib import Path

from autobots_orch_flow_studio.configs.constants import (
    LLD_SPLIT_OUTPUT_BASE_DIR,
)


def _slugify(text: str) -> str:
    """Convert header text to a safe filename (lowercase, spaces to hyphens, alphanumeric + hyphen)."""
    s = text.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[-\s]+", "-", s).strip("-")
    return s or "section"


def _flush_section(
    sections: list[tuple[str, str]], title: str, body_lines: list[str]
) -> None:
    body = "\n".join(body_lines).strip()
    if title or body:
        sections.append((title or "Intro", body))


def split_by_first_level_headers(content: str) -> list[tuple[str, str]]:
    """Split markdown content into (title, body) pairs for each first-level (# ) section.

    Content before the first # header is included as section ("", body) or ("Intro", body).
    """
    sections: list[tuple[str, str]] = []
    lines = content.splitlines()
    current_title = ""
    current_body: list[str] = []

    for line in lines:
        is_h1 = line.startswith("# ") and not line.startswith("## ")
        if is_h1:
            _flush_section(sections, current_title, current_body)
            current_title = line[2:].strip()
            current_body = []
        else:
            current_body.append(line)

    _flush_section(sections, current_title, current_body)
    return sections


def process_lld_md(md_path: str | Path) -> Path:
    """Read an MD file, split by first-level headers, write one MD per section into a named folder.

    Output folder is {LLD_SPLIT_OUTPUT_BASE_DIR}/{md_stem}/. Each section is written as
    {slug}.md. Returns the output directory path.

    Args:
        md_path: Path to the source markdown file.

    Returns:
        Path to the created output directory (named after the MD file).

    Raises:
        FileNotFoundError: If md_path does not exist.
    """
    path = Path(md_path)
    if not path.exists():
        raise FileNotFoundError(f"MD file not found: {path}")

    content = path.read_text(encoding="utf-8")
    sections = split_by_first_level_headers(content)

    stem = path.stem
    out_dir = Path(LLD_SPLIT_OUTPUT_BASE_DIR) / stem
    out_dir.mkdir(parents=True, exist_ok=True)

    for i, (title, body) in enumerate(sections):
        slug = _slugify(title) if title else "intro"
        if not slug:
            slug = f"section-{i:02d}"
        out_file = out_dir / f"{slug}.md"
        counter = 0
        while out_file.exists():
            counter += 1
            out_file = out_dir / f"{slug}-{counter}.md"

        full_content = f"# {title}\n\n{body}\n" if title else f"{body}\n"
        out_file.write_text(full_content, encoding="utf-8")

    return out_dir


def main() -> int:
    """Run from CLI: input_path + filename = actual MD file; output path from constants."""
    parser = argparse.ArgumentParser(
        description="Split an LLD MD file by first-level headers. Output written to constant base path."
    )
    parser.add_argument(
        "input_path",
        type=Path,
        help="Base directory containing the input MD file",
    )
    parser.add_argument(
        "filename",
        type=str,
        help="Input MD filename (e.g. doc.md). Actual file = input_path/filename",
    )
    args = parser.parse_args()
    actual_file = args.input_path / args.filename
    if not actual_file.exists():
        print(f"Error: file not found: {actual_file}", file=sys.stderr)
        return 1
    out_dir = process_lld_md(actual_file)
    print(f"Output (from constant): {LLD_SPLIT_OUTPUT_BASE_DIR}")
    print(f"Wrote {len(list(out_dir.glob('*.md')))} files to: {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
