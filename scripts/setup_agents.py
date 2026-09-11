#!/usr/bin/env python3
"""Register (or remove) the fable5-1-deepthink skill with supported agent CLIs.

Location-independent: the skill directory is resolved from this file, and every
target path is derived from the user's home directory. No absolute paths are
baked in, so the repository can be cloned anywhere and installed on any machine.

Usage:
    python scripts/setup_agents.py            # install / repair (idempotent)
    python scripts/setup_agents.py --check    # report status only, change nothing
    python scripts/setup_agents.py --uninstall  # remove what install created
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Callable

# --- Derived configuration (no hard-coded absolute paths) -------------------

# The skill directory is this script's grandparent (<skill>/scripts/this.py).
# .resolve() follows any junction/symlink so links always point at the real source.
SKILL_TARGET = Path(__file__).resolve().parent.parent
SKILL_NAME = SKILL_TARGET.name
SKILL_MD = (SKILL_TARGET / "SKILL.md").as_posix()

HOME = Path.home()
CLAUDE_HOME = HOME / ".claude"
CODEX_HOME = HOME / ".codex"
GEMINI_HOME = HOME / ".gemini"

# Antigravity/Gemini scans the *container* directory listed in skills.json for
# skill subfolders, so register the skill's parent wherever it was cloned.
GEMINI_SKILL_ROOT = SKILL_TARGET.parent.as_posix()

CLAUDE_SKILL_LINK = CLAUDE_HOME / "skills" / SKILL_NAME
CODEX_SKILL_LINK = CODEX_HOME / "skills" / SKILL_NAME
GEMINI_SKILLS_JSON = GEMINI_HOME / "config" / "skills.json"

CODEX_AGENTS = CODEX_HOME / "AGENTS.md"
ANTIGRAVITY_AGENTS = GEMINI_HOME / "config" / "AGENTS.md"

GLOBAL_INSTRUCTION_LINE = (
    "- For complex debugging, unknown root causes, design decisions, or repeatedly "
    f"failing tasks, read {SKILL_MD} and follow its protocol."
)

# Detect an existing instruction line regardless of the machine's absolute path.
_INSTRUCTION_MARKERS = (f"{SKILL_NAME}/SKILL.md", f"{SKILL_NAME}\\SKILL.md")


def ascii_safe(value: object) -> str:
    return str(value).encode("ascii", "backslashreplace").decode("ascii")


class Status:
    def __init__(self, name: str, state: str, detail: str = "") -> None:
        self.name = name
        self.state = state
        self.detail = detail

    @property
    def ok(self) -> bool:
        return self.state in ("OK", "SKIPPED", "REMOVED")

    def line(self) -> str:
        if self.detail:
            return f"{self.name}: {self.state} - {ascii_safe(self.detail)}"
        return f"{self.name}: {self.state}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Register fable5-1-deepthink with Claude Code, Codex, and Antigravity/Gemini."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--check", action="store_true", help="Report status only. Change nothing."
    )
    group.add_argument(
        "--uninstall", action="store_true", help="Remove everything install created."
    )
    return parser.parse_args()


def normalize_path(value: str) -> str:
    return value.replace("\\", "/").rstrip("/").casefold()


# Windows reparse tags that represent a link we create: junction + symlink only.
_WIN_LINK_TAGS = {0xA0000003, 0xA000000C}  # IO_REPARSE_TAG_MOUNT_POINT, _SYMLINK


def is_link(path: Path) -> bool:
    """True only for a symlink or a Windows junction/symlink (not other reparse points)."""
    if path.is_symlink():
        return True
    try:
        return path.lstat().st_reparse_tag in _WIN_LINK_TAGS  # Windows-only attribute
    except (AttributeError, OSError):
        return False


def same_target(a: Path, b: Path) -> bool:
    """True if both paths resolve to the same real location (case-insensitive on Windows)."""
    try:
        return os.path.normcase(os.path.realpath(a)) == os.path.normcase(os.path.realpath(b))
    except OSError:
        return False


# --- Skill directory link ----------------------------------------------------

def check_link(name: str, link_path: Path, present: bool) -> Status:
    if not present:
        return Status(name, "SKIPPED", "agent not installed")
    if link_path.exists() and link_path.is_dir():
        if same_target(link_path, SKILL_TARGET):
            return Status(name, "OK", str(link_path))
        return Status(name, "ERROR", f"exists but points elsewhere: {link_path}")
    if link_path.exists():
        return Status(name, "ERROR", f"exists but is not a directory: {link_path}")
    return Status(name, "MISSING", str(link_path))


def create_junction(link_path: Path) -> None:
    link_path.parent.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        # Raw command string (not a list) so we control cmd's own quoting: the
        # quoted paths make cmd metacharacters (e.g. & in a path) literal.
        # Windows paths cannot contain '"', so double-quoting is always safe.
        result = subprocess.run(
            f'cmd /d /c mklink /J "{link_path}" "{SKILL_TARGET}"',
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            message = (result.stderr or result.stdout).strip()
            raise OSError(message or "mklink failed")
    else:
        link_path.symlink_to(SKILL_TARGET, target_is_directory=True)


def ensure_link(name: str, link_path: Path, present: bool, check_only: bool) -> Status:
    status = check_link(name, link_path, present)
    if check_only or status.state != "MISSING":
        return status
    try:
        create_junction(link_path)
    except OSError as exc:
        return Status(name, "ERROR", str(exc))
    return check_link(name, link_path, present)


def remove_link(name: str, link_path: Path, present: bool) -> Status:
    # lstat-based existence so a broken symlink/junction is still detected.
    exists = is_link(link_path) or link_path.exists()
    if not present or not exists:
        return Status(name, "REMOVED", "nothing to remove")
    if not is_link(link_path):
        return Status(name, "ERROR", f"refusing to delete non-link directory: {link_path}")
    if link_path.exists() and not same_target(link_path, SKILL_TARGET):
        return Status(name, "ERROR", f"link points elsewhere, leaving it: {link_path}")
    try:
        # A POSIX symlink-to-dir needs unlink; a Windows junction needs rmdir.
        # Either way only the link is removed, never the real skill folder.
        if link_path.is_symlink():
            link_path.unlink()
        else:
            link_path.rmdir()
    except OSError as exc:
        return Status(name, "ERROR", str(exc))
    return Status(name, "REMOVED", str(link_path))


# --- Antigravity/Gemini skills.json ------------------------------------------

def read_json(path: Path) -> tuple[object | None, str | None]:
    if not path.exists():
        return {"entries": []}, None
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except (OSError, json.JSONDecodeError) as exc:
        return None, str(exc)


def gemini_entry_present(data: object) -> bool:
    if not isinstance(data, dict):
        return False
    entries = data.get("entries")
    if not isinstance(entries, list):
        return False
    expected = normalize_path(GEMINI_SKILL_ROOT)
    for entry in entries:
        if isinstance(entry, dict) and normalize_path(str(entry.get("path", ""))) == expected:
            return True
    return False


def check_gemini_skills(present: bool) -> Status:
    if not present:
        return Status("antigravity skills.json", "SKIPPED", "agent not installed")
    data, error = read_json(GEMINI_SKILLS_JSON)
    if error is not None:
        return Status("antigravity skills.json", "ERROR", error)
    if gemini_entry_present(data):
        return Status("antigravity skills.json", "OK", str(GEMINI_SKILLS_JSON))
    return Status("antigravity skills.json", "MISSING", str(GEMINI_SKILLS_JSON))


def ensure_gemini_skills(present: bool, check_only: bool) -> Status:
    status = check_gemini_skills(present)
    if check_only or status.state != "MISSING":
        return status
    data, error = read_json(GEMINI_SKILLS_JSON)
    if error is not None:
        return Status("antigravity skills.json", "ERROR", error)
    if not isinstance(data, dict):
        return Status("antigravity skills.json", "ERROR", "top-level JSON is not an object")
    entries = data.get("entries")
    if entries is None:
        entries = []
        data["entries"] = entries
    if not isinstance(entries, list):
        return Status("antigravity skills.json", "ERROR", "entries is not a list")
    entries.append({"path": GEMINI_SKILL_ROOT})
    try:
        GEMINI_SKILLS_JSON.parent.mkdir(parents=True, exist_ok=True)
        GEMINI_SKILLS_JSON.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    except OSError as exc:
        return Status("antigravity skills.json", "ERROR", str(exc))
    return check_gemini_skills(present)


def remove_gemini_skills(present: bool) -> Status:
    name = "antigravity skills.json"
    if not present or not GEMINI_SKILLS_JSON.exists():
        return Status(name, "REMOVED", "nothing to remove")
    data, error = read_json(GEMINI_SKILLS_JSON)
    if error is not None or not isinstance(data, dict):
        return Status(name, "ERROR", error or "unparseable JSON")
    entries = data.get("entries")
    if not isinstance(entries, list):
        return Status(name, "REMOVED", "no entries")
    expected = normalize_path(GEMINI_SKILL_ROOT)
    kept = [e for e in entries if not (isinstance(e, dict) and normalize_path(str(e.get("path", ""))) == expected)]
    if len(kept) == len(entries):
        return Status(name, "REMOVED", "entry absent")
    data["entries"] = kept
    try:
        GEMINI_SKILLS_JSON.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    except OSError as exc:
        return Status(name, "ERROR", str(exc))
    return Status(name, "REMOVED", str(GEMINI_SKILLS_JSON))


# --- Global instruction line (auto-trigger insurance) ------------------------

def _has_instruction(text: str) -> bool:
    return any(marker in text for marker in _INSTRUCTION_MARKERS)


def check_instruction_line(name: str, path: Path, present: bool) -> Status:
    if not present:
        return Status(name, "SKIPPED", "agent not installed")
    if not path.exists():
        return Status(name, "MISSING", str(path))
    if not path.is_file():
        return Status(name, "ERROR", f"exists but is not a file: {path}")
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return Status(name, "ERROR", str(exc))
    return Status(name, "OK", str(path)) if _has_instruction(text) else Status(name, "MISSING", str(path))


def ensure_instruction_line(name: str, path: Path, present: bool, check_only: bool) -> Status:
    status = check_instruction_line(name, path, present)
    if check_only or status.state != "MISSING":
        return status
    try:
        if path.exists():
            text = path.read_text(encoding="utf-8")
            separator = "" if text.endswith("\n") else "\n"
            path.write_text(text + separator + GLOBAL_INSTRUCTION_LINE + "\n", encoding="utf-8")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(GLOBAL_INSTRUCTION_LINE + "\n", encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return Status(name, "ERROR", str(exc))
    return check_instruction_line(name, path, present)


def remove_instruction_line(name: str, path: Path, present: bool) -> Status:
    if not present or not path.exists():
        return Status(name, "REMOVED", "nothing to remove")
    try:
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    except (OSError, UnicodeError) as exc:
        return Status(name, "ERROR", str(exc))
    kept = [ln for ln in lines if not _has_instruction(ln)]
    if len(kept) == len(lines):
        return Status(name, "REMOVED", "line absent")
    try:
        path.write_text("".join(kept), encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return Status(name, "ERROR", str(exc))
    return Status(name, "REMOVED", str(path))


# --- Orchestration -----------------------------------------------------------

def main() -> int:
    args = parse_args()
    claude = CLAUDE_HOME.is_dir()
    codex = CODEX_HOME.is_dir()
    antigravity = GEMINI_HOME.is_dir()

    if args.uninstall:
        statuses = [
            remove_link("claude skill link", CLAUDE_SKILL_LINK, claude),
            remove_link("codex skill link", CODEX_SKILL_LINK, codex),
            remove_gemini_skills(antigravity),
            remove_instruction_line("codex AGENTS.md line", CODEX_AGENTS, codex),
            remove_instruction_line("antigravity AGENTS.md line", ANTIGRAVITY_AGENTS, antigravity),
        ]
    else:
        check_only = bool(args.check)
        builders: list[Callable[[], Status]] = [
            lambda: ensure_link("claude skill link", CLAUDE_SKILL_LINK, claude, check_only),
            lambda: ensure_link("codex skill link", CODEX_SKILL_LINK, codex, check_only),
            lambda: ensure_gemini_skills(antigravity, check_only),
            lambda: ensure_instruction_line("codex AGENTS.md line", CODEX_AGENTS, codex, check_only),
            lambda: ensure_instruction_line("antigravity AGENTS.md line", ANTIGRAVITY_AGENTS, antigravity, check_only),
        ]
        statuses = [build() for build in builders]

    for status in statuses:
        print(status.line())

    ok = all(status.ok for status in statuses)
    if ok and not args.check and not args.uninstall:
        print(f"\nDone. Invoke with: /{SKILL_NAME} (Claude Code) or ${SKILL_NAME} (Codex).")
        print("Antigravity: auto-triggers, or say 'use the deepthink protocol'.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
