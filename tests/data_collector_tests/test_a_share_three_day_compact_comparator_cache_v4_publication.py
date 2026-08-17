from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_compact_comparator_cache_v4 as cache


PUBLICATION = (
    cache.REPO_ROOT
    / "docs/a_share_three_day_compact_comparator_cache_v4_publication_binding_20260806.json"
)
PUBLICATION_SHA256 = "244f70b88be0396f7473c6664835cbb3cdad9135b6692b77c74018b1d53c925b"
FAILURE = (
    cache.REPO_ROOT
    / "docs/a_share_three_day_compact_comparator_cache_v4_postpublication_test_failure_20260806.json"
)
FAILURE_SHA256 = "bae41cadc59f96f1eca6036913a2880e9b5fd6400deb9301887fe40c2bd42225"
REPORT = cache.REPO_ROOT / "data/experiments/short_horizon/three_day_research_report.md"
REPORT_SHA256 = "7023760adb54fbcb5a58a73c504f6f6eb0d969983bac6d54d2405875f63e73dc"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_v4_postpublication_status_is_present_without_reading_values() -> None:
    payload = cache.status()
    assert payload["failed_formal_outputs_exist"] is False
    assert payload["v4_output_exists"] is True
    assert payload["v4_manifest_exists"] is True
    assert payload["comparison_or_raw_auxiliary_values_read_by_status"] is False
    assert payload["historical_daily_price_or_forward_return_values_read"] is False
    assert payload["provider_request_issued"] is False


def test_v4_publication_binding_and_manifest_are_frozen() -> None:
    assert _sha256(PUBLICATION) == PUBLICATION_SHA256
    binding = json.loads(PUBLICATION.read_text(encoding="utf-8"))
    manifest_path = Path(binding["published_cache"]["manifest"]["path"])
    assert _sha256(manifest_path) == binding["published_cache"]["manifest"]["sha256"]
    assert binding["published_cache"]["dataset_sha256"] == (
        "4a56dac48c14b667b6ee431519266f27bb8ff7cc25c51d8dce3bbc7aebe0376f"
    )
    assert binding["independent_verification"]["exit_code"] == 0
    assert (
        binding["independent_verification"][
            "campaign067_all_comparison_result_objects_exactly_equal"
        ]
        is True
    )
    assert binding["published_cache"]["global_materialized_dynamic_quality_values_stored"] is False


def test_v4_unified_report_addition_is_bound_without_duplicate_prior_sections() -> None:
    assert _sha256(REPORT) == REPORT_SHA256
    report = REPORT.read_text(encoding="utf-8")
    assert report.count("## 历史滚动 Campaign067 权威追加") == 1
    assert report.count("## Candidate49 2026-08-05 前瞻数据源状态") == 1
    assert report.count("## Candidate-independent 比较缓存 v4 权威追加") == 1


def test_postpublication_failure_record_freezes_exact_state_specific_nodes() -> None:
    assert _sha256(FAILURE) == FAILURE_SHA256
    record = json.loads(FAILURE.read_text(encoding="utf-8"))
    assert record["test_result"] == {
        "passed": 24,
        "failed": 2,
        "failed_nodes": [
            "tests/data_collector_tests/test_a_share_three_day_compact_comparator_cache_v4.py::test_status_and_unconfirmed_v4_build_read_no_values",
            "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign067_terminal.py::test_unified_report_has_one_campaign067_and_one_candidate49_daily_section",
        ],
    }
    assert record["research_effect"]["historical_daily_price_or_forward_return_values_read"] is False
    assert record["research_effect"]["cache_infrastructure_failure_count_increment"] == 1
