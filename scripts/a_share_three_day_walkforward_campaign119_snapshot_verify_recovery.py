#!/usr/bin/env python3
"""Verify Campaign119's existing snapshot after a metadata-only verifier mismatch."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


_TEMPLATE_PATH = (
    Path(__file__).resolve().parent
    / "a_share_three_day_walkforward_campaign117_snapshot_verify_recovery.py"
)
_TEMPLATE_SHA256 = "0dafa52aa8e39f6b42f93c4142198bfde16ffe2f94ff69ee2a18140be3a21ef4"


def _template_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _template_sha256(_TEMPLATE_PATH) != _TEMPLATE_SHA256:
    raise RuntimeError("frozen Campaign117 snapshot-verifier template changed")


_source = _TEMPLATE_PATH.read_text(encoding="utf-8")
for _old, _new in (
    (
        "114bb5dd2ac28d8e51e6a35c234cfe06f7d3810b4d7c46303e38af33d4566879",
        "30aaf36f807011891309c969359db26a342f0d87234fdca38df1d43e27d59188",
    ),
    (
        "4f5bf6ee2c26f6956178d6954aae92821530c90a6334375e8cf0e9938fa71c18",
        "66eb5902abf806005c2e938b4506d08c3106637b695ae99b2d4e322f55dfbbf2",
    ),
    (
        "aed04a80f21f5e1a6ed2e5a3f51446943a0f924f95d788f2e03a5014f1c3129e",
        "99e669b77002b6aec016d9a71e5e7e20ed40ad0bd02640146b46b9530276f634",
    ),
    ("weak_order_state_count", "range_boundary_direction_state_count"),
    (
        'manifest.get("range_boundary_direction_state_count") == 13',
        'manifest.get("range_boundary_direction_state_count") == 9',
    ),
    ("positive_total_amount_required", "exact_pair_support_required"),
    (
        "amount_magnitude_used_after_ordinal_encoding",
        "range_magnitude_used_after_state_encoding",
    ),
    (
        'and quality.get("invalid_amount_sessions") == 0',
        'and quality.get("invalid_range_value_sessions") == 0\n'
        '        and quality.get("invalid_high_below_low_sessions") == 0',
    ),
    ("Campaign117", "Campaign119"),
    ("campaign117", "campaign119"),
    ("campaign_117", "campaign_119"),
):
    if _old not in _source:
        raise RuntimeError(
            f"Campaign119 recovery transformation token absent: {_old!r}"
        )
    _source = _source.replace(_old, _new)


_implementation: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign119_snapshot_verify_recovery_implementation",
}
exec(compile(_source, str(_TEMPLATE_PATH), "exec"), _implementation)
for _name, _value in _implementation.items():
    if _name not in {"__builtins__", "__file__", "__name__"}:
        globals()[_name] = _value


if __name__ == "__main__":
    raise SystemExit(_implementation["main"]())
