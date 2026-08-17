#!/usr/bin/env python3
"""Run Campaign099 after repairing only the nested compact-loader bindings."""

from __future__ import annotations

import hashlib
import json
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from scripts import a_share_three_day_walkforward_campaign099 as campaign


REPO_ROOT = Path(__file__).resolve().parents[1]
ORIGINAL_RUNNER = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign099.py"
ORIGINAL_RUNNER_SHA256 = (
    "b251b3049095f05b4aec87d6f6784c12517ac32c1542dbc63eaf6f1511d4bef4"
)
PREREGISTRATION = (
    REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_099_preregistration.json"
)
PREREGISTRATION_SHA256 = (
    "2c8e4d9c3a5c90a58d0f739ed2381cc82a77ed164203e30b30a3d944a33a3974"
)
FAILURE_RECORD = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_099_development_compact_loader_namespace_failure_20260807.json"
)
FAILURE_RECORD_SHA256 = (
    "830f4b974ecfe1ba72ac17b693264287312e792592420ff00ce9bab05551ba8b"
)
PRE_REPAIR_LEDGER = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_099/research_attempt_ledger_v17.json"
)
PRE_REPAIR_LEDGER_SHA256 = (
    "4f8232c16a72a239bb8fc533dc45912c6e5cb56cbe01285eda0c7092b883e33d"
)
TRIAL_LEDGER = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_099/walkforward/trial_ledger.json"
)
PRE_REPAIR_TRIAL_LEDGER_SHA256 = (
    "7ec96814c82df780deff5e801ca1465ea46faa45ead3f3108a995bb53b4d911c"
)
REPAIR_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_099_development_repair_implementation_freeze_v2_20260807.json"
)
REPAIR_ACTIVATION_BINDING = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_099_development_repair_activation_binding_v2_20260807.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign099_development_repair_v2.py"
)
NONCOMPACT_MANIFEST = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign099_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign099_feature_library_v1/snapshot_manifest.json"
)


class Campaign099DevelopmentRepairError(RuntimeError):
    """Fail-closed Campaign099 repair error."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_pre_retry_trial_ledger() -> dict[str, Any]:
    if not TRIAL_LEDGER.is_file() or _sha256(TRIAL_LEDGER) != (
        PRE_REPAIR_TRIAL_LEDGER_SHA256
    ):
        raise Campaign099DevelopmentRepairError(
            "Campaign099 pre-repair trial ledger changed"
        )
    ledger = json.loads(TRIAL_LEDGER.read_text(encoding="utf-8"))
    entries = list(ledger.get("entries") or [])
    if not (
        len(entries) == 1
        and entries[0].get("phase") == "infrastructure_failure"
        and entries[0].get("trial_id") == "wf099_infrastructure__development_load_001"
        and (entries[0].get("status_and_rejection_reason") or {}).get("status")
        == "infrastructure_failed"
        and not any(
            entry.get("phase") == "development_walkforward" for entry in entries
        )
    ):
        raise Campaign099DevelopmentRepairError(
            "Campaign099 pre-repair trial ledger semantics changed"
        )
    return ledger


@contextmanager
def _temporary_nested_loader_binding_repair() -> Iterator[None]:
    globals_dict = campaign._load_compact_factor_panel.__globals__
    original = {
        name: globals_dict[name]
        for name in (
            "CANDIDATE_MANIFEST",
            "CANDIDATE_MANIFEST_SHA256",
            "CANDIDATE_DATASET_SHA256",
        )
    }
    if not (
        Path(original["CANDIDATE_MANIFEST"]) == NONCOMPACT_MANIFEST
        and original["CANDIDATE_MANIFEST_SHA256"] == campaign.COMPACT_MANIFEST_SHA256
        and original["CANDIDATE_DATASET_SHA256"] == campaign.COMPACT_DATASET_SHA256
    ):
        raise Campaign099DevelopmentRepairError(
            "Campaign099 nested loader no longer matches the recorded failure"
        )
    globals_dict["CANDIDATE_MANIFEST"] = campaign.COMPACT_MANIFEST
    globals_dict["CANDIDATE_MANIFEST_SHA256"] = campaign.COMPACT_MANIFEST_SHA256
    globals_dict["CANDIDATE_DATASET_SHA256"] = campaign.COMPACT_DATASET_SHA256
    try:
        yield
    finally:
        globals_dict.update(original)


def _load_repair_activation() -> dict[str, Any]:
    required = {
        ORIGINAL_RUNNER: ORIGINAL_RUNNER_SHA256,
        PREREGISTRATION: PREREGISTRATION_SHA256,
        FAILURE_RECORD: FAILURE_RECORD_SHA256,
        PRE_REPAIR_LEDGER: PRE_REPAIR_LEDGER_SHA256,
    }
    if any(
        not path.is_file() or _sha256(path) != digest
        for path, digest in required.items()
    ):
        raise Campaign099DevelopmentRepairError(
            "Campaign099 repair prerequisite fingerprint changed"
        )
    if not REPAIR_IMPLEMENTATION_FREEZE.is_file():
        raise Campaign099DevelopmentRepairError(
            "Campaign099 repair implementation freeze is absent"
        )
    freeze = json.loads(REPAIR_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    if not (
        freeze.get("kind")
        == "a_share_three_day_walkforward_campaign099_development_repair_implementation_freeze_v2"
        and freeze.get("status")
        == "frozen_after_one_infrastructure_failure_before_repair_retry"
        and (freeze.get("repair_runner") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and (freeze.get("tests") or {}).get("sha256") == _sha256(TEST_PATH)
        and freeze.get("complete_development_trial_count_before_repair_retry") == 0
        and freeze.get("stress_2024_2025_read_before_repair_retry") is False
        and freeze.get("provider_request_issued_before_repair_retry") is False
    ):
        raise Campaign099DevelopmentRepairError(
            "Campaign099 repair implementation freeze changed"
        )
    if not REPAIR_ACTIVATION_BINDING.is_file():
        raise Campaign099DevelopmentRepairError(
            "Campaign099 repair activation binding is absent"
        )
    activation = json.loads(REPAIR_ACTIVATION_BINDING.read_text(encoding="utf-8"))
    if not (
        activation.get("kind")
        == "a_share_three_day_walkforward_campaign099_development_repair_activation_binding_v2"
        and activation.get("status")
        == "one_repaired_development_retry_authorized_before_complete_trial"
        and (activation.get("implementation_freeze") or {}).get("sha256")
        == _sha256(REPAIR_IMPLEMENTATION_FREEZE)
        and (activation.get("development_preregistration") or {}).get("sha256")
        == PREREGISTRATION_SHA256
        and (activation.get("append_only_internal_ledger") or {}).get("sha256")
        == PRE_REPAIR_LEDGER_SHA256
        and activation.get("remaining_complete_development_trials_authorized") == 1
        and activation.get("stress_2024_2025_authorized") is False
        and activation.get("provider_request_authorized") is False
    ):
        raise Campaign099DevelopmentRepairError(
            "Campaign099 repair activation binding changed"
        )
    return activation


def main() -> int:
    _load_repair_activation()
    _validate_pre_retry_trial_ledger()
    with _temporary_nested_loader_binding_repair():
        return campaign.main()


if __name__ == "__main__":
    raise SystemExit(main())
