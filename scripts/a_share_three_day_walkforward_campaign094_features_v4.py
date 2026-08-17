#!/usr/bin/env python3
"""Audit compatibility exports for Campaign094's verified v3 snapshot."""

from __future__ import annotations

from typing import Any

from scripts import a_share_three_day_walkforward_campaign094_features as v1
from scripts import a_share_three_day_walkforward_campaign094_features_v3 as v3

bindings = v1._generated["bindings"]
verify_snapshot_files = v3.verify_snapshot_files


def __getattr__(name: str) -> Any:
    if hasattr(v1, name):
        return getattr(v1, name)
    if name in v1._generated:
        return v1._generated[name]
    raise AttributeError(name)
