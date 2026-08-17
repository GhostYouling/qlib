#!/usr/bin/env python3
"""Run Campaign120's frozen coverage-first no-return audit."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


_TEMPLATE_PATH = (
    Path(__file__).resolve().parent
    / "a_share_three_day_walkforward_campaign119_no_return_audit.py"
)
_TEMPLATE_SHA256 = "6974455765f7f621ad4676cd12026242e28d6bef1a2de8239bdbcb9604c219ff"


def _template_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _template_sha256(_TEMPLATE_PATH) != _TEMPLATE_SHA256:
    raise RuntimeError("frozen Campaign119 coverage-audit template changed")


_source = _TEMPLATE_PATH.read_text(encoding="utf-8")
for _old, _new in (
    ("all 136", "all 137"),
    ("all_136", "all_137"),
    ("all-136", "all-137"),
    (
        'record.get("numeric_comparator_count") == 136',
        'record.get("numeric_comparator_count") == 137',
    ),
    ("Campaign119", "Campaign120"),
    ("campaign119", "campaign120"),
    ("campaign_119", "campaign_120"),
):
    if _old not in _source:
        raise RuntimeError(f"Campaign120 audit transformation token absent: {_old!r}")
    _source = _source.replace(_old, _new)


_nested_exec = 'exec(compile(_source, str(_TEMPLATE_PATH), "exec"), _implementation)'
_range_replacements = (
    (
        "not np.isfinite(finite_values).all()\n"
        "        or (finite_values < 0.0).any()\n"
        "        or (finite_values > 1.0).any()",
        "not np.isfinite(finite_values).all()\n"
        "        or not np.equal(finite_values, np.floor(finite_values)).all()\n"
        "        or (finite_values < 2.0).any()\n"
        "        or (finite_values > 238.0).any()",
    ),
    (
        "or not np.isfinite(finite).all()\n"
        "        or (finite < 0.0).any()\n"
        "        or (finite > 1.0).any()",
        "or not np.isfinite(finite).all()\n"
        "        or not np.equal(finite, np.floor(finite)).all()\n"
        "        or (finite < 2.0).any()\n"
        "        or (finite > 238.0).any()",
    ),
)
_level_two_lines = ["for _range_old, _range_new in " + repr(_range_replacements) + ":"]
_level_two_lines.extend(
    [
        "    if _source.count(_range_old) != 1:",
        "        raise RuntimeError('Campaign120 audit range token changed')",
        "    _source = _source.replace(_range_old, _range_new)",
        _nested_exec,
    ]
)
_level_two = "\n".join(_level_two_lines)
_level_one = "\n".join(
    (
        f"if _source.count({_nested_exec!r}) != 1:",
        "    raise RuntimeError('Campaign120 audit nested template changed')",
        f"_source = _source.replace({_nested_exec!r}, {_level_two!r})",
        _nested_exec,
    )
)
if _source.count(_nested_exec) != 1:
    raise RuntimeError("Campaign120 audit outer template changed")
_source = _source.replace(_nested_exec, _level_one)


_implementation: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign120_no_return_audit_implementation",
}
exec(compile(_source, str(_TEMPLATE_PATH), "exec"), _implementation)
for _name, _value in _implementation.items():
    if _name not in {"__builtins__", "__file__", "__name__"}:
        globals()[_name] = _value


if __name__ == "__main__":
    raise SystemExit(_implementation["main"]())
