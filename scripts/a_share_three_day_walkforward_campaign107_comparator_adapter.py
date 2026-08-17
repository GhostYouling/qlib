#!/usr/bin/env python3
"""Pure, value-blind Campaign107 raw-comparator range and NaN adapter."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from scripts import a_share_three_day_preregistration_binding_validator as bindings


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_107_raw_comparator_adapter_contract_20260808.json"
)
CONTRACT_SHA256 = "6b8ac9484b3e46ebd7bd0857eb99e24bba4ede3c8781891d0b150de0cae19962"
DEFAULT_DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")


class Campaign107ComparatorAdapterError(RuntimeError):
    """Fail closed when a raw-comparator identity, range, or missing rule changes."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_contract(path: Path = CONTRACT) -> dict[str, Any]:
    path = path.expanduser().resolve()
    if not path.is_file() or _sha256(path) != CONTRACT_SHA256:
        raise Campaign107ComparatorAdapterError("Campaign107 adapter contract changed")
    report = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if report.get("all_bindings_passed") is not True:
        raise Campaign107ComparatorAdapterError("Campaign107 adapter binding failed")
    record = json.loads(path.read_text(encoding="utf-8"))
    semantics = record.get("frozen_adapter_semantics") or {}
    registration = semantics.get("range_registration") or {}
    source = semantics.get("source_frame") or {}
    alignment = semantics.get("alignment") or {}
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign107_raw_comparator_adapter_contract"
        and record.get("status")
        == "frozen_before_campaign107_candidate_comparator_daily_price_or_return_values"
        and registration.get(
            "every_raw_numeric_comparator_requires_an_explicit_finite_lower_upper_pair"
        )
        is True
        and registration.get("lower_may_equal_upper") is False
        and registration.get("existing_identical_registration_is_idempotent") is True
        and registration.get("existing_conflicting_registration_fails_closed") is True
        and source.get("nan_is_a_valid_missing_comparator_value") is True
        and source.get("positive_or_negative_infinity_is_invalid") is True
        and source.get("nan_may_not_be_filled_ranked_or_dropped_before_alignment")
        is True
        and alignment.get("aligned_nan_must_remain_nan") is True
        and alignment.get(
            "pairwise_overlap_is_handled_only_by_the_frozen_correlation_gate"
        )
        is True
        and boundary.get("campaign107_source_rows_read") is False
        and boundary.get("campaign107_candidate_values_read") is False
        and boundary.get("campaign107_comparator_values_read") is False
        and boundary.get("historical_daily_price_or_forward_return_values_read")
        is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign107ComparatorAdapterError(
            "Campaign107 adapter contract semantics changed"
        )
    return record


def _normalize_range(value_range: Sequence[float]) -> tuple[float, float]:
    if len(value_range) != 2:
        raise Campaign107ComparatorAdapterError("factor range must contain two values")
    lower, upper = (float(value_range[0]), float(value_range[1]))
    if not (np.isfinite(lower) and np.isfinite(upper) and lower < upper):
        raise Campaign107ComparatorAdapterError(
            "factor range must have finite lower < upper"
        )
    return lower, upper


def register_raw_factor_range(
    factor_ranges: Mapping[str, Sequence[float]],
    *,
    factor: str,
    value_range: Sequence[float],
) -> dict[str, tuple[float, float]]:
    """Return a copy with one explicit raw-factor range, failing on conflicts."""

    if not factor or not isinstance(factor, str):
        raise Campaign107ComparatorAdapterError("factor name must be nonempty")
    frozen = _normalize_range(value_range)
    result: dict[str, tuple[float, float]] = {}
    for name, observed in factor_ranges.items():
        result[str(name)] = _normalize_range(observed)
    existing = result.get(factor)
    if existing is not None and existing != frozen:
        raise Campaign107ComparatorAdapterError(
            f"conflicting registered range for {factor}"
        )
    result[factor] = frozen
    return result


def sorted_raw_comparator_arrays(
    frame: pd.DataFrame,
    *,
    factor: str,
    value_range: Sequence[float],
    compact_key_fn: Callable[[pd.Series, pd.Series], Sequence[int] | np.ndarray],
) -> tuple[np.ndarray, np.ndarray]:
    """Sort unique source keys while preserving legal NaN comparator values."""

    required = ("trade_date", "symbol", factor)
    if not set(required).issubset(frame.columns):
        raise Campaign107ComparatorAdapterError("raw comparator columns changed")
    lower, upper = _normalize_range(value_range)
    try:
        keys = np.asarray(
            compact_key_fn(frame["trade_date"], frame["symbol"]), dtype=np.int64
        )
        numeric = pd.to_numeric(frame[factor], errors="raise")
        values = numeric.to_numpy(dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise Campaign107ComparatorAdapterError(
            "raw comparator identity or numeric values changed"
        ) from exc
    if keys.ndim != 1 or values.ndim != 1 or len(keys) != len(values):
        raise Campaign107ComparatorAdapterError("raw comparator array shape changed")
    order = np.argsort(keys, kind="stable")
    keys = keys[order]
    values = values[order]
    if len(keys) > 1 and np.any(keys[1:] <= keys[:-1]):
        raise Campaign107ComparatorAdapterError("raw comparator keys are not unique")
    if np.isinf(values).any():
        raise Campaign107ComparatorAdapterError("infinite raw comparator value")
    finite = np.isfinite(values)
    if np.any((values[finite] < lower) | (values[finite] > upper)):
        raise Campaign107ComparatorAdapterError("raw comparator value outside range")
    return keys, values


def align_raw_comparator_values(
    *, source_keys: np.ndarray, source_values: np.ndarray, target_keys: np.ndarray
) -> np.ndarray:
    """Align source values to candidate keys without changing source NaNs."""

    source_keys = np.asarray(source_keys, dtype=np.int64)
    source_values = np.asarray(source_values, dtype=np.float64)
    target_keys = np.asarray(target_keys, dtype=np.int64)
    if (
        source_keys.ndim != 1
        or source_values.ndim != 1
        or target_keys.ndim != 1
        or len(source_keys) != len(source_values)
        or (len(source_keys) > 1 and np.any(source_keys[1:] <= source_keys[:-1]))
        or (len(target_keys) > 1 and np.any(target_keys[1:] <= target_keys[:-1]))
    ):
        raise Campaign107ComparatorAdapterError("comparison alignment identity changed")
    positions = np.searchsorted(source_keys, target_keys, side="left")
    if (
        np.any(positions >= len(source_keys))
        or not np.array_equal(source_keys[positions], target_keys)
    ):
        raise Campaign107ComparatorAdapterError(
            "raw comparator source does not cover candidate identity"
        )
    return source_values[positions].copy()


def status() -> dict[str, Any]:
    validate_contract()
    return {
        "status": "contract_validated_value_blind",
        "candidate_values_read": False,
        "comparator_values_read": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
    }


def main() -> int:
    print(json.dumps(status(), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

