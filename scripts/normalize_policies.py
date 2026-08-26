"""Normalize canonical policy Markdown files in place."""

from __future__ import annotations

import argparse
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY_DIR = REPOSITORY_ROOT / "data" / "policies"


def normalize_policy_files(input_dir: Path, output_dir: Path) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for source in sorted(input_dir.glob("*.md")):
        content = source.read_text(encoding="utf-8").replace("\r\n", "\n").rstrip() + "\n"
        destination = output_dir / source.name
        destination.write_text(content, encoding="utf-8")
        count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize policy Markdown files")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_POLICY_DIR,
                        help="Input directory, relative to the repository root")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_POLICY_DIR,
                        help="Output directory, relative to the repository root")
    args = parser.parse_args()
    count = normalize_policy_files(args.input_dir, args.output_dir)
    print(f"Normalized {count} policy document(s) in {args.output_dir}")


if __name__ == "__main__":
    main()
