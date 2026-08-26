"""Validate policy Markdown front matter and document identifiers."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from rag.core.chunking import parse_document


DEFAULT_POLICY_DIR = REPOSITORY_ROOT / "data" / "policies"


def validate_policy_files(input_dir: Path) -> list[str]:
    errors: list[str] = []
    document_ids: set[str] = set()
    for path in sorted(input_dir.glob("*.md")):
        try:
            document = parse_document(path.read_text(encoding="utf-8"), path.name)
            document_id = document["document_id"]
            if document_id in document_ids:
                errors.append(f"{path.name}: duplicate document_id {document_id!r}")
            document_ids.add(document_id)
        except (OSError, ValueError) as error:
            errors.append(f"{path.name}: {error}")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate policy Markdown files")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_POLICY_DIR,
                        help="Directory to validate, relative to the repository root")
    args = parser.parse_args()
    errors = validate_policy_files(args.input_dir)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)
    print(f"Validated {len(list(args.input_dir.glob('*.md')))} policy document(s)")


if __name__ == "__main__":
    main()
