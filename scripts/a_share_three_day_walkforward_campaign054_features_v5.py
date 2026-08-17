#!/usr/bin/env python3
"""Snapshot-bound Campaign054 ordered no-return audit implementation."""

from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path
from typing import Any

try:
    import scripts.a_share_three_day_walkforward_campaign053_features_v6 as terminal_entry
    import scripts.a_share_three_day_walkforward_campaign054_features_v4 as snapshot_entry
except ModuleNotFoundError:
    import a_share_three_day_walkforward_campaign053_features_v6 as terminal_entry
    import a_share_three_day_walkforward_campaign054_features_v4 as snapshot_entry


runner = snapshot_entry.runner
terminal = terminal_entry.runner
EXPECTED_V4_ENTRYPOINT_SHA256 = (
    "9dd9195477538e764dba4b7efc93f23b77dd550d6e116347b1340f98456e8fb5"
)
EXPECTED_SNAPSHOT_MANIFEST_SHA256 = (
    "e61ec157d2119575bc53444d0c8e3c808a4c1113ace8ffa7ed2866bb5e431904"
)
EXPECTED_SNAPSHOT_DATASET_SHA256 = (
    "dbabb7ae1321f172b0ce3c3c4e6713f606245b8e2cc07387e5bacc77d58cfd7e"
)
EXPECTED_SNAPSHOT_PUBLICATION_BINDING_SHA256 = (
    "bdce301c66e2426e3acfa51f1e46c2330d9c4dc65703fb41b491c592386edd13"
)
EXPECTED_CAMPAIGN053_TERMINAL_ENTRYPOINT_SHA256 = (
    "605625b8cfc9dcc8f73601840154e57e4d72212992c42d36cf7e6bb79ac59dad"
)
SNAPSHOT_PUBLICATION_BINDING = (
    runner.REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_054_snapshot_publication_binding_20260803.json"
)
C53_SNAPSHOT_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign053_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign053_feature_library_v1/snapshot_manifest.json"
)
C53_SNAPSHOT_SHA256 = (
    "e0f0e9176580e9e6216049d026ab360aea0904e5d1db57d61311fe6da7d3c402"
)
C53_DATASET_SHA256 = (
    "d56d8628608faf32c97fb374cb05d06bfa0182d87f2d0467f5a08bca8c3f0f87"
)
C53_FACTOR_NAME = "intraday_amount_price_discovery_alignment_js_238p"

if (
    runner._sha256(runner.Path(snapshot_entry.__file__).resolve())
    != EXPECTED_V4_ENTRYPOINT_SHA256
):
    raise runner.Campaign054FeatureError("Campaign054 frozen v4 entrypoint changed")
if (
    runner._sha256(Path(terminal_entry.__file__).resolve())
    != EXPECTED_CAMPAIGN053_TERMINAL_ENTRYPOINT_SHA256
):
    raise runner.Campaign054FeatureError(
        "Campaign053 terminal entrypoint changed"
    )
runner._require_file(
    SNAPSHOT_PUBLICATION_BINDING,
    EXPECTED_SNAPSHOT_PUBLICATION_BINDING_SHA256,
    "Campaign054 snapshot publication binding",
)
runner._require_file(
    C53_SNAPSHOT_PATH,
    C53_SNAPSHOT_SHA256,
    "Campaign053 terminal snapshot",
)

runner.DEFAULT_SNAPSHOT_BINDING = SNAPSHOT_PUBLICATION_BINDING
runner.SNAPSHOT_MANIFEST_SHA256 = EXPECTED_SNAPSHOT_MANIFEST_SHA256
runner.SNAPSHOT_DATASET_SHA256 = EXPECTED_SNAPSHOT_DATASET_SHA256
runner.SNAPSHOT_PUBLICATION_BINDING_SHA256 = (
    EXPECTED_SNAPSHOT_PUBLICATION_BINDING_SHA256
)
runner._install_engine_globals()


def _load_candidate_frame(
    manifest_path: Path, manifest: dict[str, Any]
) -> Any:
    _, _, engine, _, _, _ = terminal.campaign044._context()
    return engine.load_factor_frame(manifest_path, manifest, runner.FACTOR_NAME)


def run_no_return_audit(
    *, data_root: Path, experiment_root: Path, workers: int
) -> Path:
    """Open comparisons only after coverage, then stop before all returns."""

    runner._load_implementation_freeze()
    data_root = data_root.expanduser().resolve()
    experiment_root = experiment_root.expanduser().resolve()
    spec = runner.load_protocol()

    manifest_path = runner.output_root(data_root) / "snapshot_manifest.json"
    runner._require_file(
        manifest_path,
        EXPECTED_SNAPSHOT_MANIFEST_SHA256,
        "Campaign054 repaired snapshot manifest",
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("dataset_sha256") != EXPECTED_SNAPSHOT_DATASET_SHA256:
        raise runner.Campaign054FeatureError(
            "Campaign054 repaired snapshot dataset changed"
        )
    runner._validate_snapshot_manifest(
        manifest, require_fingerprint_constants=True
    )
    existing = sorted(
        experiment_root.glob("*_campaign054_no_return_audit.json")
    )
    if existing:
        if (
            len(existing) != 1
            or not runner.NO_RETURN_AUDIT_SHA256
            or runner._sha256(existing[0]) != runner.NO_RETURN_AUDIT_SHA256
        ):
            raise runner.Campaign054FeatureError(
                "existing Campaign054 audit is ambiguous or unbound"
            )
        return existing[0]

    runner._install_engine_globals()
    candidate_verification = runner.verify_snapshot_files(
        manifest, manifest_path, workers
    )

    terminal._install_engine_globals()
    c53_manifest = json.loads(C53_SNAPSHOT_PATH.read_text(encoding="utf-8"))
    if c53_manifest.get("dataset_sha256") != C53_DATASET_SHA256:
        raise runner.Campaign054FeatureError(
            "Campaign053 terminal snapshot dataset changed"
        )
    c53_verification = terminal.verify_snapshot_files(
        c53_manifest, C53_SNAPSHOT_PATH, workers
    )

    c52_path = terminal.C52_SNAPSHOT_PATH
    terminal._require_file(
        c52_path,
        terminal.C52_SNAPSHOT_SHA256,
        "Campaign052 snapshot manifest",
    )
    c52_manifest = json.loads(c52_path.read_text(encoding="utf-8"))
    if c52_manifest.get("dataset_sha256") != terminal.C52_DATASET_SHA256:
        raise runner.Campaign054FeatureError("Campaign052 snapshot dataset changed")
    terminal.previous._install_engine_globals()
    c52_verification = terminal.previous.verify_snapshot_files(
        c52_manifest, c52_path, workers
    )

    runner._install_engine_globals()
    prior, foundation, engine, _, candidate49, comparison_engine = (
        terminal.campaign044._context()
    )
    eligible_keys = foundation.quality_listing_eligible_keys(
        prior.load_protocol()
    )
    candidate = _load_candidate_frame(manifest_path, manifest)
    quality_frame, coverage = engine.coverage_and_capacity(
        candidate,
        eligible_keys,
        spec,
        runner.FACTOR_NAME,
    )
    del candidate, eligible_keys
    gc.collect()

    if coverage["gate_passed_before_comparison_values"]:
        gate = spec["ordered_no_return_gates"][
            "uniqueness_after_coverage_only"
        ]
        expected_order = [
            str(item["name"]) for item in gate["comparison_factors"]
        ]
        directions = {
            str(item["name"]): str(item["score_direction"])
            for item in gate["comparison_factors"]
        }
        keys, values = engine._sorted_candidate_arrays(
            quality_frame, runner.FACTOR_NAME
        )
        catalog, source_verifications = terminal.campaign044._build_source_catalog(
            data_root=data_root,
            workers=workers,
            verify_files=True,
        )
        comparisons: list[dict[str, Any]] = []
        for source in catalog:
            aligned = terminal.campaign044._load_aligned_source_values(source, keys)
            for factor in source["factors"]:
                comparisons.append(
                    comparison_engine._aligned_comparison_result(
                        candidate_keys=keys,
                        candidate_values=values,
                        comparison_values=aligned.pop(factor),
                        comparison=factor,
                        direction=directions[factor],
                        gate=gate,
                    )
                )
            del aligned
            gc.collect()
        if len(comparisons) != terminal.TERMINAL_LIBRARY_COUNT:
            raise runner.Campaign054FeatureError(
                "complete 66-factor catalog changed"
            )

        _, candidate49_path, candidate49_manifest = engine._comparison_chain(
            data_root
        )
        candidate49_verification = candidate49.verify_snapshot_files(
            candidate49_manifest, candidate49_path, workers
        )
        candidate49_values = engine._load_filtered_comparison_values_explicit(
            candidate49_manifest, [candidate49.FACTOR_NAME], keys
        )[candidate49.FACTOR_NAME]
        comparisons.append(
            comparison_engine._aligned_comparison_result(
                candidate_keys=keys,
                candidate_values=values,
                comparison_values=candidate49_values,
                comparison=candidate49.FACTOR_NAME,
                direction="higher",
                gate=gate,
            )
        )
        del candidate49_values
        gc.collect()

        extra_verifications: dict[str, Any] = {}
        for (
            label,
            source_path,
            expected_sha,
            expected_dataset,
            factor,
            module,
        ) in terminal.previous._extra_comparison_sources():
            terminal._require_file(
                source_path, expected_sha, f"{label} snapshot manifest"
            )
            source_manifest = json.loads(
                source_path.read_text(encoding="utf-8")
            )
            if (
                expected_dataset is not None
                and source_manifest.get("dataset_sha256") != expected_dataset
            ):
                raise runner.Campaign054FeatureError(
                    f"{label} snapshot dataset changed"
                )
            extra_verifications[label] = module.verify_snapshot_files(
                source_manifest, source_path, workers
            )
            comparison_values = engine._load_filtered_comparison_values_explicit(
                source_manifest, [factor], keys
            )[factor]
            comparisons.append(
                comparison_engine._aligned_comparison_result(
                    candidate_keys=keys,
                    candidate_values=values,
                    comparison_values=comparison_values,
                    comparison=factor,
                    direction=directions[factor],
                    gate=gate,
                )
            )
            del comparison_values
            gc.collect()

        c52_values = engine._load_filtered_comparison_values_explicit(
            c52_manifest, [terminal.C52_FACTOR_NAME], keys
        )[terminal.C52_FACTOR_NAME]
        comparisons.append(
            comparison_engine._aligned_comparison_result(
                candidate_keys=keys,
                candidate_values=values,
                comparison_values=c52_values,
                comparison=terminal.C52_FACTOR_NAME,
                direction=directions[terminal.C52_FACTOR_NAME],
                gate=gate,
            )
        )
        del c52_values
        gc.collect()

        c53_values = engine._load_filtered_comparison_values_explicit(
            c53_manifest, [C53_FACTOR_NAME], keys
        )[C53_FACTOR_NAME]
        comparisons.append(
            comparison_engine._aligned_comparison_result(
                candidate_keys=keys,
                candidate_values=values,
                comparison_values=c53_values,
                comparison=C53_FACTOR_NAME,
                direction=directions[C53_FACTOR_NAME],
                gate=gate,
            )
        )
        del c53_values
        gc.collect()

        observed_order = [
            str(item["comparison_factor"]) for item in comparisons
        ]
        observed_correlations = [
            float(item["absolute_median_daily_rank_correlation"])
            for item in comparisons
            if item["absolute_median_daily_rank_correlation"] is not None
        ]
        passed = bool(
            observed_order == expected_order
            and len(comparisons) == runner.COMPARISON_COUNT
            and all(item["gate_passed"] for item in comparisons)
        )
        uniqueness = {
            "comparison_values_loaded_after_coverage_pass": True,
            "comparison_factor_count": len(comparisons),
            "comparison_order_matches_preregistration": (
                observed_order == expected_order
            ),
            "terminal_66_source_snapshot_verification": source_verifications,
            "candidate49_snapshot_file_verification": candidate49_verification,
            **{
                f"{key}_snapshot_file_verification": value
                for key, value in extra_verifications.items()
            },
            "campaign052_snapshot_file_verification": c52_verification,
            "campaign053_snapshot_file_verification": c53_verification,
            "comparisons": comparisons,
            "maximum_observed_absolute_median_daily_rank_correlation": (
                max(observed_correlations) if observed_correlations else None
            ),
            "all_required_comparisons_passed": passed,
        }
        del keys, values
        gc.collect()
    else:
        uniqueness = {
            "comparison_values_loaded_after_coverage_pass": False,
            "comparisons": [],
            "all_required_comparisons_passed": False,
            "failure_reason": "coverage_gate_failed",
        }

    admitted = bool(
        coverage["gate_passed_before_comparison_values"]
        and uniqueness["all_required_comparisons_passed"]
    )
    research = prior.research
    run_id = f"{research._timestamp()}_campaign054_no_return_audit"
    record = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign054_no_return_audit",
        "status": (
            "completed_with_one_admissible_factor_pending_walkforward_preregistration"
            if admitted
            else "completed_zero_admissible_factors_stop_before_historical_returns"
        ),
        "run_id": run_id,
        "created_at": research._timestamp(),
        "protocol": {
            "path": str(runner.DEFAULT_PROTOCOL.resolve()),
            "sha256": runner.PROTOCOL_SHA256,
        },
        "candidate_snapshot": {
            "path": str(manifest_path),
            "sha256": EXPECTED_SNAPSHOT_MANIFEST_SHA256,
            "dataset_sha256": EXPECTED_SNAPSHOT_DATASET_SHA256,
        },
        "snapshot_publication_binding": {
            "path": str(SNAPSHOT_PUBLICATION_BINDING.resolve()),
            "sha256": EXPECTED_SNAPSHOT_PUBLICATION_BINDING_SHA256,
        },
        "snapshot_file_verification": candidate_verification,
        "coverage_and_capacity": {runner.FACTOR_NAME: coverage},
        "uniqueness": {runner.FACTOR_NAME: uniqueness},
        "admissible_factor_names": [runner.FACTOR_NAME] if admitted else [],
        "admissible_factor_count": 1 if admitted else 0,
        "failed_factor_names": [] if admitted else [runner.FACTOR_NAME],
        "next_action": (
            "freeze the exact one-trial Campaign054 walk-forward catalog before reading 2019-2023 returns"
            if admitted
            else "record the no-return rejection and design a genuinely new campaign"
        ),
        "source_fields_read": list(runner.RAW_COLUMNS),
        "minute_open_high_low_close_fields_read": [],
        "minute_volume_and_amount_fields_read": ["volume", "amount"],
        "historical_daily_price_fields_read": [],
        "historical_forward_return_fields_read": False,
        "candidate49_historical_return_read": False,
        "candidate49_prospective_ledgers_changed": False,
        "second_prospective_candidate_created": False,
        "training_or_model_fitting_performed": False,
        "current_scoring_selection_sizing_or_orders_performed": False,
    }
    experiment_root.mkdir(parents=True, exist_ok=True)
    destination = experiment_root / f"{run_id}.json"
    foundation.atomic_write_json(record, destination)
    return destination


runner.run_no_return_audit = run_no_return_audit
runner._install_engine_globals()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    audit = subparsers.add_parser("no-return-audit")
    audit.add_argument("--data-root", type=Path, default=runner.DEFAULT_DATA_ROOT)
    audit.add_argument(
        "--experiment-root", type=Path, default=runner.DEFAULT_EXPERIMENT_ROOT
    )
    audit.add_argument("--workers", type=int, default=4)
    status = subparsers.add_parser("status")
    status.add_argument("--data-root", type=Path, default=runner.DEFAULT_DATA_ROOT)
    status.add_argument(
        "--experiment-root", type=Path, default=runner.DEFAULT_EXPERIMENT_ROOT
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "no-return-audit":
        payload = {
            "audit": str(
                run_no_return_audit(
                    data_root=args.data_root,
                    experiment_root=args.experiment_root,
                    workers=args.workers,
                )
            )
        }
    else:
        payload = runner.status(args.data_root, args.experiment_root)
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
