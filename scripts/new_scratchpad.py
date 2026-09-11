#!/usr/bin/env python3
"""Create a fable5-1-deepthink scratchpad."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def ascii_safe(value: object) -> str:
    return str(value).encode("ascii", "backslashreplace").decode("ascii")


TEMPLATE = """# GOAL
- <one line: what "done" looks like, incl. constraints>

# FACTS (verified only — each with evidence pointer)
- <fact> [src: path:line | cmd output]

# ASSUMPTIONS (unverified — promote to FACTS or kill)
- <assumption> [risk if wrong: high/med/low]

# HYPOTHESES
| # | candidate | prior | cheapest discriminating check | status |
|---|-----------|-------|-------------------------------|--------|
| H1 | ... | high | ... | open/testing/confirmed |

# KILLED
- H_: <one-line reason>

# NEXT
- <single next action>

# RISKS / OPEN
- <unresolved concern>
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create .deepthink/thinking.md in a target directory."
    )
    parser.add_argument(
        "--dir",
        default=".",
        help="Target directory. Defaults to the current working directory.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing scratchpad.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    target_dir = Path(args.dir).expanduser().resolve()
    scratchpad = target_dir / ".deepthink" / "thinking.md"

    try:
        if scratchpad.exists() and not args.force:
            print(ascii_safe(scratchpad))
            return 0

        scratchpad.parent.mkdir(parents=True, exist_ok=True)
        scratchpad.write_text(TEMPLATE, encoding="utf-8")
        print(ascii_safe(scratchpad))
        return 0
    except OSError as exc:
        print(f"ERROR: {ascii_safe(exc)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
