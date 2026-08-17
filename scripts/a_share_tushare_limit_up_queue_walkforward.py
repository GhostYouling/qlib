#!/usr/bin/env python3
"""Run Campaign115's exact single historical development trial.

``plan`` is metadata-only and must succeed before ``run-development`` may
read the candidate snapshot or any daily price/return value.  This runner has
no provider client and exposes no 2024-2025 stress command.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import stat
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_RUNNER = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign080.py"
BASE_RUNNER_SHA256 = "b4c4b781392c87f01b9542c2317611a936d431b0328cea9d21ea90b8f68a324b"
BASE_FACTOR = "intraday_above_median_amount_longest_run_240m"
FACTOR_NAME = "tushare_official_limit_up_queue_persistence"
FROZEN_TRIAL_ID = "wf115_tushare_official_limit_up_queue_persistence_single_higher"
PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_115_development_trial_protocol_20260809.json"
)
PROTOCOL_SHA256 = "7a6a537c53c5dbc090105cc750559ba4e163eb5878b8b619104407a0172b94ef"
IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_115_development_trial_implementation_freeze_v1_20260809.json"
)
ORDERED_NO_RETURN_AUDIT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_115/no_return/campaign115_ordered_no_return_audit_2019_2023.json"
)
SOURCE_ROOT = (
    REPO_ROOT
    / "data/raw/a_share/rich/tushare/limit_up_queue_persistence/development/campaign115_2019_2023"
)
SOURCE_MANIFEST = (
    REPO_ROOT
    / "data/metadata/rich_data/runs/campaign115_tushare_limit_queue_development_2019_2023.json"
)
SEMANTIC_RECEIPT = (
    REPO_ROOT
    / "data/metadata/rich_data/runs/campaign115_tushare_limit_queue_development_semantic_verification_2019_2023.json"
)
TEMPLATE = (
    REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_004_preregistration.json"
)
TEMPLATE_SHA256 = "e67811f265b2b744073391fa65698951b132065109f95fa47991b8254a5756e6"
OUTPUT_ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_115/walkforward"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_tushare_limit_up_queue_walkforward.py"
)
EXPECTED_SESSION_COUNT = 1214
EXPECTED_SESSION_ORDER_SHA256 = (
    "63559370c9abfe3b8e24d133d1cc102658e9f3a144c507a1c12928d93ad95059"
)
EXPECTED_COMPARATOR_COUNT = 134
EXPECTED_COMPARATOR_ORDER_SHA256 = (
    "31d788db467f558a0ac538315343090f1b3ad4cb27a26136a49ebaa88b2fdbf2"
)


class Campaign115DevelopmentError(RuntimeError):
    """Fail-closed Campaign115 development error."""


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


if digest(BASE_RUNNER) != BASE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign080 development runner changed")

_source = BASE_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign080", "Campaign115"),
    ("campaign080", "campaign115"),
    ("campaign_080", "campaign_115"),
    ("wf080", "wf115"),
    (BASE_FACTOR, FACTOR_NAME),
):
    _source = _source.replace(_old, _new)
_engine: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_tushare_limit_up_queue_walkforward_generated",
}
exec(compile(_source, str(BASE_RUNNER), "exec"), _engine)  # noqa: S102

base = _engine["base"]
_build_trial_catalog = _engine["build_trial_catalog"]
_inherited_run_development = _engine["run_development"]
_inherited_status = _engine["status"]


def _read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as error:
        raise Campaign115DevelopmentError(
            f"required JSON is unavailable: {path}"
        ) from error
    if not isinstance(value, dict):
        raise Campaign115DevelopmentError(f"required JSON is not an object: {path}")
    return value


def _resolve_bound_path(raw: object) -> Path:
    path = Path(str(raw or "")).expanduser()
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path.resolve()


def _validate_binding(binding: dict[str, Any], label: str) -> Path:
    path = _resolve_bound_path(binding.get("path"))
    expected = str(binding.get("sha256") or "")
    if len(expected) != 64 or not path.is_file() or path.is_symlink():
        raise Campaign115DevelopmentError(f"{label} binding is absent")
    if digest(path) != expected:
        raise Campaign115DevelopmentError(f"{label} binding changed")
    return path


def _private_unique_regular_file(path: Path) -> bool:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    return bool(
        stat.S_ISREG(info.st_mode)
        and not path.is_symlink()
        and info.st_nlink == 1
        and stat.S_IMODE(info.st_mode) & 0o077 == 0
    )


def _validate_protocol() -> dict[str, Any]:
    if (
        PROTOCOL.resolve()
        != (
            REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_115_development_trial_protocol_20260809.json"
        ).resolve()
        or digest(PROTOCOL) != PROTOCOL_SHA256
    ):
        raise Campaign115DevelopmentError("development protocol fingerprint changed")
    record = _read_object(PROTOCOL)
    admission = record.get("admission_gate") or {}
    search = record.get("search_space") or {}
    folds = record.get("development_folds") or []
    split = record.get("split_protocol") or {}
    survivor = record.get("survivor_rule") or {}
    factor_library = record.get("factor_library") or []
    output = record.get("research_output_boundary") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign115_development_trial_protocol"
        and record.get("status")
        == "frozen_before_campaign115_daily_price_or_forward_return_values"
        and admission.get("audit_path")
        == str(ORDERED_NO_RETURN_AUDIT.relative_to(REPO_ROOT))
        and admission.get("required_factor") == FACTOR_NAME
        and admission.get("required_numeric_comparison_count")
        == EXPECTED_COMPARATOR_COUNT
        and admission.get("required_numeric_comparator_order_sha256")
        == EXPECTED_COMPARATOR_ORDER_SHA256
        and len(factor_library) == 1
        and factor_library[0].get("name") == FACTOR_NAME
        and factor_library[0].get("direction") == "higher"
        and factor_library[0].get("exact_session_count") == EXPECTED_SESSION_COUNT
        and factor_library[0].get("exact_session_order_sha256")
        == EXPECTED_SESSION_ORDER_SHA256
        and search.get("expected_trial_count") == 1
        and search.get("trials")
        == [
            {
                "trial_id": FROZEN_TRIAL_ID,
                "kind": "single_factor",
                "feature_set": [FACTOR_NAME],
                "weights": [1.0],
                "complexity": 1,
            }
        ]
        and [item.get("validation", {}).get("start", "")[:4] for item in folds]
        == ["2021", "2022", "2023"]
        and split.get("purge_signal_sessions_each_boundary") == 3
        and split.get("label_containment_required") is True
        and split.get(
            "t_plus_1_and_t_plus_3_must_be_inside_the_same_train_or_validation_partition"
        )
        is True
        and split.get("topk") == 3
        and survivor.get("positive_ic_fold_count_gte") == 2
        and survivor.get("positive_normalized_return_fold_count_gte") == 2
        and survivor.get("positive_pilot_return_fold_count_gte") == 2
        and survivor.get("development_aggregate_20bp_return_gt") == 0.0
        and output.get("current_scoring_allowed") is False
        and output.get("selection_allowed") is False
        and output.get("sizing_allowed") is False
        and output.get("orders_allowed") is False
        and output.get("campaign116_allowed_while_campaign115_active") is False
    ):
        raise Campaign115DevelopmentError("development protocol semantics changed")
    for label, binding in (record.get("authoritative_inputs") or {}).items():
        path = _validate_binding(binding, f"protocol.{label}")
        if label == "walkforward_template" and path != TEMPLATE.resolve():
            raise Campaign115DevelopmentError("walk-forward template path changed")
    return record


def _validate_implementation_freeze() -> dict[str, Any]:
    if not _private_unique_regular_file(IMPLEMENTATION_FREEZE):
        raise Campaign115DevelopmentError("development implementation freeze absent")
    record = _read_object(IMPLEMENTATION_FREEZE)
    runner = record.get("runner") or {}
    tests = record.get("tests") or {}
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign115_development_trial_implementation_freeze"
        and record.get("status")
        == "implementation_frozen_before_campaign115_daily_price_or_forward_return_values"
        and (record.get("protocol") or {}).get("sha256") == PROTOCOL_SHA256
        and runner.get("path") == str(Path(__file__).resolve().relative_to(REPO_ROOT))
        and runner.get("sha256") == digest(Path(__file__).resolve())
        and tests.get("path") == str(TEST_PATH.relative_to(REPO_ROOT))
        and tests.get("sha256") == digest(TEST_PATH)
        and boundary.get("candidate_or_comparator_values_read_before_freeze") is False
        and boundary.get(
            "historical_daily_price_or_forward_return_values_read_before_freeze"
        )
        is False
        and boundary.get("partition_year_2024_or_2025_values_read_before_freeze")
        is False
        and boundary.get("credential_loaded_before_freeze") is False
        and boundary.get("provider_request_issued_before_freeze") is False
    ):
        raise Campaign115DevelopmentError("development implementation freeze changed")
    return record


def _validate_admission() -> dict[str, Any]:
    if not _private_unique_regular_file(ORDERED_NO_RETURN_AUDIT):
        raise Campaign115DevelopmentError("ordered no-return audit admission absent")
    audit = _read_object(ORDERED_NO_RETURN_AUDIT)
    coverage = audit.get("coverage_and_capacity") or {}
    uniqueness = audit.get("uniqueness") or {}
    candidate = audit.get("candidate") or {}
    semantic = audit.get("semantic_source") or {}
    if not (
        audit.get("kind")
        == "a_share_three_day_walkforward_campaign115_ordered_no_return_audit"
        and audit.get("status")
        == "completed_one_no_return_admissible_factor_pending_frozen_development_trial"
        and (audit.get("protocol") or {}).get("sha256")
        == "6d94e7fb638aed9f0423179a60ee3ad1a768b12c0de14a64c6dcc81168e6d12d"
        and candidate.get("factor") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and coverage.get("gate_passed_before_comparator_values") is True
        and uniqueness.get("comparison_count") == EXPECTED_COMPARATOR_COUNT
        and uniqueness.get("comparison_order_sha256")
        == EXPECTED_COMPARATOR_ORDER_SHA256
        and uniqueness.get("comparison_order_matches_preregistration") is True
        and uniqueness.get("all_required_numeric_comparisons_passed") is True
        and audit.get("admissible_factor_names") == [FACTOR_NAME]
        and audit.get("admissible_factor_count") == 1
        and audit.get("candidate_or_comparator_row_values_embedded") is False
        and audit.get("historical_daily_price_fields_read") == []
        and audit.get("historical_forward_return_fields_read") is False
        and audit.get("partition_year_2024_or_2025_values_read") is False
        and audit.get("stress_2024_2025_opened") is False
        and audit.get("provider_request_issued") is False
        and audit.get("credential_loaded") is False
        and audit.get("selection_or_promotion_allowed") is False
        and semantic.get("session_count") == EXPECTED_SESSION_COUNT
        and semantic.get("session_order_sha256") == EXPECTED_SESSION_ORDER_SHA256
    ):
        raise Campaign115DevelopmentError("ordered no-return admission changed")
    if not _private_unique_regular_file(SEMANTIC_RECEIPT):
        raise Campaign115DevelopmentError("semantic source receipt absent")
    if semantic.get("receipt_sha256") != digest(SEMANTIC_RECEIPT):
        raise Campaign115DevelopmentError("semantic source receipt binding changed")
    receipt = _read_object(SEMANTIC_RECEIPT)
    source_manifest = receipt.get("source_manifest") or {}
    source = receipt.get("source") or {}
    if not (
        receipt.get("status")
        == "complete_semantically_verified_2019_2023_candidate_snapshot_pending_ordered_no_return_audit"
        and source_manifest.get("sha256") == digest(SOURCE_MANIFEST)
        and source.get("name") == FACTOR_NAME
        and (receipt.get("verification") or {}).get("session_count")
        == EXPECTED_SESSION_COUNT
        and (receipt.get("verification") or {}).get("session_order_sha256")
        == EXPECTED_SESSION_ORDER_SHA256
    ):
        raise Campaign115DevelopmentError("semantic source receipt changed")
    if not SOURCE_ROOT.is_dir() or SOURCE_ROOT.is_symlink():
        raise Campaign115DevelopmentError("development source root absent")
    return {
        "audit_sha256": digest(ORDERED_NO_RETURN_AUDIT),
        "semantic_receipt_sha256": digest(SEMANTIC_RECEIPT),
        "source_manifest_sha256": digest(SOURCE_MANIFEST),
        "source_dataset_sha256": semantic.get("dataset_sha256"),
    }


def _plan_blocker(label: str, function: Any) -> tuple[bool, str | None]:
    try:
        function()
    except Exception:
        return False, label
    return True, None


def build_plan() -> dict[str, Any]:
    checks: dict[str, bool] = {}
    blockers: list[str] = []
    for label, function in (
        ("development_protocol_valid", _validate_protocol),
        ("development_implementation_freeze_valid", _validate_implementation_freeze),
        ("ordered_no_return_audit_admitted_one_factor", _validate_admission),
    ):
        passed, blocker = _plan_blocker(label, function)
        checks[label] = passed
        if blocker is not None:
            blockers.append(blocker)
    ready = not blockers
    return {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign115_development_trial_plan",
        "ready": ready,
        "exit_code_if_executed": 0 if ready else 2,
        "blockers": blockers,
        "checks": checks,
        "factor": FACTOR_NAME,
        "trial_id": FROZEN_TRIAL_ID,
        "expected_trial_count": 1,
        "development_years": [2019, 2020, 2021, 2022, 2023],
        "purge_signal_sessions": 3,
        "t_plus_1_and_t_plus_3_must_share_partition": True,
        "stress_2024_2025_opened": False,
        "candidate_or_comparator_values_read": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "partition_year_2024_or_2025_values_read": False,
        "credential_loaded": False,
        "provider_request_issued": False,
        "candidate49_historical_backfill_performed": False,
        "candidate49_ledgers_changed": False,
        "current_scoring_selection_sizing_or_orders_performed": False,
    }


def _factor_panel(
    _campaign: dict[str, Any],
    years: Iterable[int],
    signal_dates: pd.DatetimeIndex,
) -> pd.DataFrame:
    if tuple(int(year) for year in years) != (2019, 2020, 2021, 2022, 2023):
        raise Campaign115DevelopmentError(
            "only 2019-2023 development values are allowed"
        )
    dates = tuple(sorted(set(pd.DatetimeIndex(signal_dates).normalize())))
    frames: list[pd.DataFrame] = []
    for timestamp in dates:
        if timestamp.year not in {2019, 2020, 2021, 2022, 2023}:
            raise Campaign115DevelopmentError(
                "2024-2025 factor partition access forbidden"
            )
        path = (
            SOURCE_ROOT / "sessions" / timestamp.date().isoformat() / "factor.parquet"
        )
        if not path.is_file() or path.is_symlink():
            raise Campaign115DevelopmentError(
                f"development factor partition absent: {timestamp.date()}"
            )
        frame = pd.read_parquet(
            path,
            columns=["trade_date", "instrument", FACTOR_NAME],
        )
        frames.append(frame)
    if not frames:
        raise Campaign115DevelopmentError("development signal grid is empty")
    panel = pd.concat(frames, ignore_index=True)
    panel["trade_date"] = pd.to_datetime(
        panel["trade_date"], errors="coerce"
    ).dt.normalize()
    panel["instrument"] = panel["instrument"].astype(str).str.upper()
    values = pd.to_numeric(panel[FACTOR_NAME], errors="coerce")
    if (
        panel["trade_date"].isna().any()
        or panel.duplicated(["trade_date", "instrument"]).any()
        or not panel["trade_date"].isin(dates).all()
        or not np.isfinite(values).all()
        or ((values < 0.0) | (values > 1.0)).any()
    ):
        raise Campaign115DevelopmentError("development factor panel semantics changed")
    panel[FACTOR_NAME] = values.astype(float)
    return panel[["trade_date", "instrument", FACTOR_NAME]]


def load_campaign(path: Path) -> tuple[dict[str, Any], str]:
    if path.expanduser().resolve() != PROTOCOL.resolve():
        raise Campaign115DevelopmentError("alternate development protocol forbidden")
    protocol = _validate_protocol()
    admission = _validate_admission()
    _validate_implementation_freeze()
    template = _read_object(TEMPLATE)
    if digest(TEMPLATE) != TEMPLATE_SHA256:
        raise Campaign115DevelopmentError("walk-forward template changed")
    campaign = copy.deepcopy(template)
    campaign.update(
        {
            "version": 1,
            "kind": "a_share_three_day_walkforward_campaign115_development_trial_protocol",
            "campaign_id": "a_share_three_day_walkforward_campaign_115",
            "status": "frozen_before_campaign115_2019_2023_development_return_read",
            "frozen_at": protocol["recorded_at"],
            "purpose": protocol["purpose"],
            "evidence_classification": {
                "development_2019_2023": "historically exposed expanding walk-forward research, not unseen or pristine",
                "stress_2024_2025": "historically exposed quasi-out-of-sample stress replay kept closed by this runner",
                "point_in_time_limitation": "The local holding universe derives from a current listing snapshot and can contain survivorship bias.",
                "investment_or_current_selection_claim_allowed": False,
            },
            "governance_bindings": protocol["authoritative_inputs"],
            "no_return_bindings": {
                "protocol": protocol["authoritative_inputs"][
                    "ordered_no_return_protocol"
                ],
                "audit": {
                    "path": str(ORDERED_NO_RETURN_AUDIT.relative_to(REPO_ROOT)),
                    "sha256": admission["audit_sha256"],
                },
                "semantic_receipt": {
                    "path": str(SEMANTIC_RECEIPT.relative_to(REPO_ROOT)),
                    "sha256": admission["semantic_receipt_sha256"],
                },
            },
            "implementation": {
                "script": {
                    "path": str(Path(__file__).resolve().relative_to(REPO_ROOT)),
                    "sha256": digest(Path(__file__).resolve()),
                },
                "development_command": "python scripts/a_share_tushare_limit_up_queue_walkforward.py run-development --confirm-development-trial",
                "exposed_stress_command": "forbidden_in_campaign115_development_runner",
                "output_root": str(OUTPUT_ROOT),
            },
            "factor_library": [
                {
                    "feature_id": "wf115_f01",
                    "name": FACTOR_NAME,
                    "direction": "higher",
                    "formula": protocol["factor_library"][0]["formula"],
                    "economic_hypothesis": protocol["factor_library"][0][
                        "economic_hypothesis"
                    ],
                    "dataset_group": "campaign115_official_limit_queue_source",
                    "partition_root": str(SOURCE_ROOT),
                    "bindings": [
                        {
                            "path": str(PROTOCOL.relative_to(REPO_ROOT)),
                            "sha256": PROTOCOL_SHA256,
                        },
                        {
                            "path": str(ORDERED_NO_RETURN_AUDIT.relative_to(REPO_ROOT)),
                            "sha256": admission["audit_sha256"],
                        },
                        {
                            "path": str(SEMANTIC_RECEIPT.relative_to(REPO_ROOT)),
                            "sha256": admission["semantic_receipt_sha256"],
                        },
                        {
                            "path": str(SOURCE_MANIFEST.relative_to(REPO_ROOT)),
                            "sha256": admission["source_manifest_sha256"],
                        },
                    ],
                }
            ],
            "search_space": {
                "admissible_factor_names_canonical": [FACTOR_NAME],
                "single_factor_rule": f"Evaluate {FROZEN_TRIAL_ID} exactly once at weight 1.0.",
                "pair_rule": "No pair exists.",
                "all_components_required": True,
                "directional_rank_method": "same-day average percentile rank using the frozen higher direction",
                "weight_fitting": False,
                "threshold_search": False,
                "year_subset_search": False,
                "filter_search": False,
                "triple_or_higher_order_combinations": False,
                "old_terminal_factor_rescue_combinations": False,
                "pair_weight_grid_for_canonical_factor_order": [
                    [0.25, 0.75],
                    [0.5, 0.5],
                    [0.75, 0.25],
                ],
                "expected_single_trial_count": 1,
                "expected_pair_trial_count": 0,
                "expected_trial_count": 1,
                "record_every_trial_and_infrastructure_failure": True,
                "post_result_change_requires_new_campaign_version": True,
            },
            "candidate49_boundary": {
                "registration_id": "candidate49_intraday_cumulative_vwap_crossing_rate_240m_v1",
                "included_in_feature_library": False,
                "historical_return_read_allowed": False,
                "historical_signal_execution_or_milestone_backfill_allowed": False,
                "prospective_ledgers_changed_by_campaign": False,
            },
            "research_output_boundary": {
                "current_scoring_allowed": False,
                "selection_allowed": False,
                "sizing_allowed": False,
                "orders_allowed": False,
                "prospective_candidate_activation_allowed": False,
                "campaign004_rescue_or_reweight_allowed": False,
                "terminated_factor_rescue_or_combination_allowed": False,
                "investment_advice": False,
            },
        }
    )
    campaign["walkforward_folds"] = copy.deepcopy(protocol["development_folds"])
    campaign["split_protocol"]["purge_signal_sessions_each_boundary"] = 3
    campaign["split_protocol"]["label_containment_required"] = True
    campaign["survivor_rule"].update(protocol["survivor_rule"])
    campaign["survivor_rule"]["maximum_exposed_stress_survivors"] = 1
    trials = _build_trial_catalog(campaign)
    if trials != [
        {
            "trial_id": FROZEN_TRIAL_ID,
            "parent_trial_id": None,
            "kind": "single_factor",
            "feature_set": [FACTOR_NAME],
            "weights": [1.0],
            "complexity": 1,
        }
    ]:
        raise Campaign115DevelopmentError("single development trial catalog changed")
    return campaign, PROTOCOL_SHA256


_engine["DEFAULT_CAMPAIGN"] = PROTOCOL
_engine["DEFAULT_OUTPUT_ROOT"] = OUTPUT_ROOT
_engine["load_campaign"] = load_campaign
base.load_factor_panel = _factor_panel


def run_development(args: argparse.Namespace) -> dict[str, Any]:
    if not args.confirm_development_trial:
        raise Campaign115DevelopmentError("development trial confirmation is required")
    plan = build_plan()
    if not plan["ready"] or plan["exit_code_if_executed"] != 0:
        raise Campaign115DevelopmentError("development plan is not ready")
    _validate_admission()
    result = _inherited_run_development(
        argparse.Namespace(
            campaign=str(PROTOCOL),
            output_root=str(OUTPUT_ROOT),
            batch_size=int(args.batch_size),
        )
    )
    result["plan_revalidated_before_return_read"] = True
    result["provider_request_issued"] = False
    result["candidate49_historical_return_read"] = False
    result["stress_2024_2025_opened"] = False
    return result


def inspect_trial() -> dict[str, Any]:
    if not OUTPUT_ROOT.exists():
        return {
            "valid": True,
            "status": "no_campaign115_development_trial",
            "trial_ledger_present": False,
            "historical_daily_price_or_forward_return_values_read_by_inspection": False,
            "partition_year_2024_or_2025_values_read": False,
            "credential_loaded": False,
            "provider_request_issued": False,
        }
    if OUTPUT_ROOT.is_symlink() or not OUTPUT_ROOT.is_dir():
        raise Campaign115DevelopmentError("development output root identity changed")
    if not ORDERED_NO_RETURN_AUDIT.exists():
        raise Campaign115DevelopmentError("development output exists without admission")
    payload = _inherited_status(
        argparse.Namespace(campaign=str(PROTOCOL), output_root=str(OUTPUT_ROOT))
    )
    return {
        "valid": True,
        "status": "campaign115_development_trial_state_valid",
        **payload,
        "historical_daily_price_or_forward_return_values_read_by_inspection": False,
        "partition_year_2024_or_2025_values_read": False,
        "credential_loaded": False,
        "provider_request_issued": False,
    }


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    commands = value.add_subparsers(dest="command", required=True)
    commands.add_parser("plan")
    run = commands.add_parser("run-development")
    run.add_argument("--confirm-development-trial", action="store_true")
    run.add_argument("--batch-size", type=int, default=256)
    commands.add_parser("inspect-trial")
    return value


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "plan":
            payload = build_plan()
            print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
            return int(payload["exit_code_if_executed"])
        if args.command == "run-development":
            payload = run_development(args)
        else:
            payload = inspect_trial()
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return 0
    except Exception as error:
        print(
            json.dumps(
                {
                    "status": "failed_closed",
                    "error_type": type(error).__name__,
                    "error": str(error),
                    "credential_loaded": False,
                    "provider_request_issued": False,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
