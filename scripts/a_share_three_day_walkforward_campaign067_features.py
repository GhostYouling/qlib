#!/usr/bin/env python3
"""Build the frozen Campaign067 ROE-versus-profit-scale rank-gap snapshot."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_RUNNER = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign066_features.py"
BASE_RUNNER_SHA256 = "ff8bd4aef61f7eec00299d1b38e21c30e15a4e7b010d157b0ea60d0576adf614"
BASE_FACTOR = "quarterly_quality_rank_balance_3f"
FACTOR_NAME = "quarterly_roe_profit_scale_efficiency_gap_2r"
FACTOR_FORMULA = "r_roe-r_net_profit"
PROTOCOL_SHA256 = "94073ae194468b2aa95d40dd63b29c80332d8e1e5fa47c61ca94c640060d1d07"
MECHANISM_AUDIT_SHA256 = "1d2d5313d4b2a2544575c5aae02085354dd7467bd5f4f54571830e759ebbda06"
FULL_DEFINITION_COUNT = 98
FULL_DEFINITION_ORDER_SHA256 = "847e6e3e960da3b18106b91af742395fc44518bc37b91398b6191f853cc3b22c"
COMPARISON_COUNT = 97
COMPARISON_ORDER_SHA256 = "e860581f2b2022a189259db7bf32e105960ca655fe2793d114e38315a251fbca"
C66_FACTOR = BASE_FACTOR
EVENT_FIELDS = ("instrument", "report_date", "announcement_date", "roe", "net_profit")
STATE_FIELDS = ("roe", "net_profit")
OUTPUT_COLUMNS = ("trade_date", "symbol", "provider", FACTOR_NAME, f"{FACTOR_NAME}_eligible")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if not BASE_RUNNER.is_file() or _sha256(BASE_RUNNER) != BASE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign066 feature runner changed")


_source = BASE_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign066", "Campaign067"),
    ("campaign066", "campaign067"),
    ("campaign_066", "campaign_067"),
    (BASE_FACTOR, FACTOR_NAME),
    ("1-(max(r_roe,r_profit,r_revenue)-min(r_roe,r_profit,r_revenue))", FACTOR_FORMULA),
    ("ab850ef8ff194c1172070e2ffd388eff2d7924354abf06a8b32c5bd43584a278", PROTOCOL_SHA256),
    ("1e5fe44c0cde5097646cf058ec8149c189cf65e2ce62093e221c0d5022b98b8b", MECHANISM_AUDIT_SHA256),
    ("FULL_DEFINITION_COUNT = 97", "FULL_DEFINITION_COUNT = 98"),
    ("bc66abb94f62bef5fe9912059ade232c6c86b16b82f162df577fa8d74afeca7d", FULL_DEFINITION_ORDER_SHA256),
    ("COMPARISON_COUNT = 96", "COMPARISON_COUNT = 97"),
    ("794dff48d649b8dec1fdf609583ad87260c3e71a681a48b9a0ce77726de4763b", COMPARISON_ORDER_SHA256),
    ("C65_FACTOR", "C66_FACTOR"),
    ("intraday_range_weak_order_time_reversal_divergence_236t", C66_FACTOR),
    ("campaign065", "campaign066"),
    (
        'EVENT_FIELDS = ("instrument", "report_date", "announcement_date", "roe", "profit_yoy", "revenue_yoy")',
        'EVENT_FIELDS = ("instrument", "report_date", "announcement_date", "roe", "net_profit")',
    ),
    ('STATE_FIELDS = ("roe", "profit_yoy", "revenue_yoy")', 'STATE_FIELDS = ("roe", "net_profit")'),
    ("states = np.full((len(out), 3), np.nan, dtype=np.float64)", "states = np.full((len(out), 2), np.nan, dtype=np.float64)"),
    ("(values[eligible] < 0.0) | (values[eligible] > 1.0)", "(values[eligible] < -1.0) | (values[eligible] > 1.0)"),
):
    _source = _source.replace(_old, _new)

_runtime: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign067_features_generated",
}
exec(compile(_source, str(BASE_RUNNER), "exec"), _runtime)


Campaign067FeatureError = _runtime["Campaign067FeatureError"]
bindings = _runtime["bindings"]
DEFAULT_DATA_ROOT: Path = _runtime["DEFAULT_DATA_ROOT"]
DEFAULT_PROTOCOL = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_067_no_return_preregistration.json"
DEFAULT_IMPLEMENTATION_FREEZE = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_067_feature_implementation_freeze_v2_20260805.json"
DEFAULT_CALENDAR: Path = _runtime["DEFAULT_CALENDAR"]
CLEAN_MANIFEST_RELATIVE: Path = _runtime["CLEAN_MANIFEST_RELATIVE"]
QUARTERLY_PATH: Path = _runtime["QUARTERLY_PATH"]
QUARTERLY_MANIFEST_PATH: Path = _runtime["QUARTERLY_MANIFEST_PATH"]
EXPECTED_PARTITIONS = int(_runtime["EXPECTED_PARTITIONS"])
EXPECTED_ROWS = int(_runtime["EXPECTED_ROWS"])


def reconstruct_comparisons(spec: dict[str, Any] | None = None) -> list[dict[str, str]]:
    spec = spec or json.loads(DEFAULT_PROTOCOL.read_text(encoding="utf-8"))
    link = (spec.get("source_chain") or {}).get("campaign066_completed_numeric_comparison_catalog") or {}
    path = REPO_ROOT / str(link.get("path") or "")
    if not path.is_file() or _sha256(path) != str(link.get("sha256") or ""):
        raise Campaign067FeatureError("Campaign066 comparison catalog changed")
    audit = json.loads(path.read_text(encoding="utf-8"))
    previous = (audit.get("uniqueness") or {}).get(C66_FACTOR) or {}
    items = [
        {"name": str(item["comparison_factor"]), "score_direction": str(item["score_direction"])}
        for item in previous.get("comparisons") or []
    ]
    items.append({"name": C66_FACTOR, "score_direction": "higher"})
    if len(items) != COMPARISON_COUNT or _runtime["_comparison_order_digest"](items) != COMPARISON_ORDER_SHA256:
        raise Campaign067FeatureError("Campaign067 comparison order changed")
    return items


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    path = path.expanduser().resolve()
    if not path.is_file() or _sha256(path) != PROTOCOL_SHA256:
        raise Campaign067FeatureError(f"Campaign067 protocol changed: {path}")
    report = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if report.get("all_bindings_passed") is not True:
        raise Campaign067FeatureError("Campaign067 protocol binding failed")
    spec = json.loads(path.read_text(encoding="utf-8"))
    candidate = spec.get("candidate") or {}
    unique = ((spec.get("ordered_no_return_gates") or {}).get("uniqueness_after_coverage_only") or {})
    finite = spec.get("finite_development_catalog_if_admitted") or {}
    comparisons = reconstruct_comparisons(spec)
    if not (
        spec.get("kind") == "a_share_three_day_walkforward_campaign067_no_return_preregistration"
        and spec.get("status") == "frozen_before_campaign067_source_candidate_comparison_daily_price_or_return_values"
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and tuple(candidate.get("quarterly_source_projection") or ()) == EVENT_FIELDS
        and candidate.get("combination_rule", "").startswith("Exactly r_roe-r_net_profit")
        and unique.get("complete_definition_count") == FULL_DEFINITION_COUNT
        and unique.get("complete_definition_order_sha256") == FULL_DEFINITION_ORDER_SHA256
        and unique.get("numeric_comparator_count") == COMPARISON_COUNT
        and unique.get("numeric_comparator_order_sha256") == COMPARISON_ORDER_SHA256
        and unique.get("all_97_numeric_comparators_must_pass") is True
        and len(comparisons) == COMPARISON_COUNT
        and finite.get("trial_id") == "wf067_quarterly_roe_profit_scale_efficiency_gap_2r_single_higher"
        and finite.get("expected_trial_count") == 1
        and spec.get("research_boundary", {}).get("historical_forward_return_fields_read") is False
    ):
        raise Campaign067FeatureError("Campaign067 protocol semantics changed")
    return spec


def compute_gap_values(ranks: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    values = np.asarray(ranks, dtype=np.float64)
    if values.ndim != 2 or values.shape[1] != 2:
        raise Campaign067FeatureError("rank gap requires an n-by-2 array")
    eligible = np.isfinite(values).all(axis=1) & ((values >= 0.0) & (values <= 1.0)).all(axis=1)
    result = np.full(len(values), np.nan, dtype=np.float64)
    result[eligible] = values[eligible, 0] - values[eligible, 1]
    if ((result[eligible] < -1.0) | (result[eligible] > 1.0)).any():
        raise Campaign067FeatureError("rank gap escaped [-1,1]")
    return result, eligible


def rank_and_balance_year_frame(frame: pd.DataFrame) -> pd.DataFrame:
    work = frame.copy()
    ranks = [work.groupby("trade_date", sort=False)[column].rank(method="average", pct=True) for column in STATE_FIELDS]
    rank_matrix = np.column_stack([series.to_numpy(dtype=np.float64) for series in ranks])
    values, eligible = compute_gap_values(rank_matrix)
    work[FACTOR_NAME] = values
    work[f"{FACTOR_NAME}_eligible"] = eligible
    work["provider"] = "eastmoney_quarterly_quality"
    return work


for _name, _value in {
    "FACTOR_NAME": FACTOR_NAME,
    "FACTOR_FORMULA": FACTOR_FORMULA,
    "PROTOCOL_SHA256": PROTOCOL_SHA256,
    "MECHANISM_AUDIT_SHA256": MECHANISM_AUDIT_SHA256,
    "FULL_DEFINITION_COUNT": FULL_DEFINITION_COUNT,
    "FULL_DEFINITION_ORDER_SHA256": FULL_DEFINITION_ORDER_SHA256,
    "COMPARISON_COUNT": COMPARISON_COUNT,
    "COMPARISON_ORDER_SHA256": COMPARISON_ORDER_SHA256,
    "C66_FACTOR": C66_FACTOR,
    "EVENT_FIELDS": EVENT_FIELDS,
    "STATE_FIELDS": STATE_FIELDS,
    "OUTPUT_COLUMNS": OUTPUT_COLUMNS,
    "DEFAULT_PROTOCOL": DEFAULT_PROTOCOL,
    "DEFAULT_IMPLEMENTATION_FREEZE": DEFAULT_IMPLEMENTATION_FREEZE,
    "reconstruct_comparisons": reconstruct_comparisons,
    "load_protocol": load_protocol,
    "compute_balance_values": compute_gap_values,
    "rank_and_balance_year_frame": rank_and_balance_year_frame,
}.items():
    _runtime[_name] = _value


_runtime["FACTOR_RANGES"] = {FACTOR_NAME: (-1.0, 1.0)}
_runtime["FACTOR_FORMULAS"] = {FACTOR_NAME: FACTOR_FORMULA}

_comparison_order_digest = _runtime["_comparison_order_digest"]
prepare_events = _runtime["prepare_events"]
attach_states = _runtime["attach_states"]
output_root = _runtime["output_root"]
build_snapshot = _runtime["build_snapshot"]
verify_snapshot_files = _runtime["verify_snapshot_files"]
status = _runtime["status"]
main = _runtime["main"]


if __name__ == "__main__":
    raise SystemExit(main())
