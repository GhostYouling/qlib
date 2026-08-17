#!/usr/bin/env python3
"""Compatibility export for Campaign093's immutable v1 feature implementation."""

from __future__ import annotations

from typing import Any

from scripts import a_share_three_day_walkforward_campaign093_features as v1

bindings = v1._generated["bindings"]


def __getattr__(name: str) -> Any:
    if hasattr(v1, name):
        return getattr(v1, name)
    if name in v1._generated:
        return v1._generated[name]
    raise AttributeError(name)
