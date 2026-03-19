#!/usr/bin/env python3

"""Compose standardized explorer/worker prompts from role config."""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


def load_roles(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as fp:
        data = json.load(fp)
    roles = data.get("roles", {})
    if not isinstance(roles, dict):
        raise ValueError("Invalid roles.json: `roles` must be a dictionary.")
    return roles


def render_list(roles: Dict[str, Any]) -> str:
    lines = ["Available roles:"]
    for name in sorted(roles):
        meta = roles[name]
        lines.append(f"- {name} ({meta.get('agent_type', 'unknown')}): {meta.get('purpose', '').strip()}")
    return "\n".join(lines)


def _render_list_block(items: List[str], empty: str = "(none)") -> str:
    if not items:
        return f"- {empty}"
    return "\n".join(f"- {item}" for item in items)


def compose_prompt(
    role_name: str,
    role: Dict[str, Any],
    objective: str,
    contexts: List[str],
    acceptance: List[str],
    extra: str,
) -> str:
    agent_type = role.get("agent_type", "worker")
    purpose = role.get("purpose", "")
    write_paths = role.get("write_paths", [])
    read_paths = role.get("read_paths", [])
    must_do = role.get("must_do", [])
    must_not = role.get("must_not", [])
    required_checks = role.get("required_checks", [])

    lines = [
        f"You are `{role_name}` ({agent_type}).",
        f"Mission: {objective}",
    ]
    if purpose:
        lines.append(f"Role purpose: {purpose}")

    lines.extend(
        [
            "",
            "Repository context constraints:",
            "- You are not alone in this codebase.",
            "- Do not revert edits made by others.",
            "- Keep changes scoped and evidence-based.",
            "",
            "Owned write scope:",
            _render_list_block(write_paths, empty="read-only role"),
            "",
            "Allowed read scope:",
            _render_list_block(read_paths),
            "",
            "Must do:",
            _render_list_block(must_do),
            "",
            "Must not do:",
            _render_list_block(must_not),
            "",
            "Task context:",
            _render_list_block(contexts),
            "",
            "Acceptance criteria:",
            _render_list_block(acceptance),
            "",
            "Required validation commands:",
            _render_list_block(required_checks),
            "",
            "Output format (required):",
            "- Summary of what changed and why",
            "- Exact changed files",
            "- Commands run and key results",
            "- Risks / follow-ups (if any)",
        ]
    )

    if extra:
        lines.extend(["", "Additional instructions:", extra])

    return "\n".join(lines).strip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate standardized subagent prompts for Qlib.")
    parser.add_argument(
        "--roles",
        default=str(Path(__file__).with_name("roles.json")),
        help="Path to roles.json (default: scripts/subagents/roles.json).",
    )
    parser.add_argument("--list", action="store_true", help="List available roles.")
    parser.add_argument("--role", help="Role name from roles.json.")
    parser.add_argument("--objective", help="Main objective for this agent task.")
    parser.add_argument(
        "--context",
        action="append",
        default=[],
        help="Task context line, can be used multiple times.",
    )
    parser.add_argument(
        "--acceptance",
        action="append",
        default=[],
        help="Acceptance criterion line, can be used multiple times.",
    )
    parser.add_argument("--extra", default="", help="Additional instruction text.")
    args = parser.parse_args()

    roles = load_roles(Path(args.roles))

    if args.list:
        print(render_list(roles))
        return

    if not args.role:
        raise SystemExit("Error: --role is required unless --list is used.")
    if args.role not in roles:
        raise SystemExit(f"Error: unknown role `{args.role}`.")
    if not args.objective:
        raise SystemExit("Error: --objective is required when generating a prompt.")

    prompt = compose_prompt(
        role_name=args.role,
        role=roles[args.role],
        objective=args.objective,
        contexts=args.context,
        acceptance=args.acceptance,
        extra=args.extra,
    )
    print(prompt)


if __name__ == "__main__":
    main()

