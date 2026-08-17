#!/usr/bin/env python3
"""Build and explicitly activate an isolated Tushare daily provider.

``sync-source`` writes only immutable provider-session partitions below an
explicit staging root. ``build`` converts those partitions plus the accepted
2019-2025 Tushare daily snapshot into the repository's point-in-time
per-symbol contract and materializes Qlib inside that same staging root.
``seed-refresh`` copies only hash-verified source-session checkpoints from an
already accepted active Tushare root into a new staging version, so the next
``sync-source`` requests only later sessions while preserving full rebuild
and acceptance gates.
``activate`` remains a separate explicit operation: it first validates the
completed acceptance gate, seeds only frozen non-daily roots, atomically
updates the repository data-root pointer, and restores the prior pointer if
fresh post-activation validation fails.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.dataset as pads


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import a_share_data_pipeline as pipeline  # noqa: E402
import a_share_tushare_daily_concordance as concordance  # noqa: E402
from _a_share_runtime import (  # noqa: E402
    DATA_ROOT_ENV,
    DATA_ROOT_POINTER_NAME,
    latest_completed_session_date,
    resolve_data_root,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = (
    REPO_ROOT / "docs" / "a_share_tushare_daily_provider_migration_protocol.json"
)
PROTOCOL_SHA256 = "bf3278511b5b0fe7911e1cca44ac5dae3ce8a2b0633a9928aff727dfcfd25e1c"
DEFAULT_REFERENCE_MANIFEST = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/raw/a_share/rich/tushare/daily/"
    "snapshots/tushare_daily_2019_2025_acf72e28/snapshot_manifest.json"
)
REFERENCE_START = dt.date(2019, 1, 1)
REFERENCE_END = dt.date(2025, 12, 31)
HISTORY_START = dt.date(2015, 1, 1)
MINIMUM_CALL_INTERVAL_SECONDS = 0.22
MAXIMUM_PROVIDER_ATTEMPTS = 3
DAILY_FIELDS = concordance.FIELDS
DAILY_BASIC_FIELDS = ("ts_code", "trade_date", "turnover_rate")
TRADE_CAL_FIELDS = ("cal_date", "is_open", "pretrade_date")
STOCK_BASIC_FIELDS = (
    "ts_code",
    "symbol",
    "name",
    "market",
    "list_date",
    "delist_date",
    "list_status",
)
CODE_PATTERN = concordance.CODE_PATTERN


class TushareDailyMigrationError(RuntimeError):
    """Raised when a migration source, checkpoint, or gate is rejected."""


def canonical_file_digest(path: Path) -> str:
    """Hash text with LF normalization and binary files byte-for-byte."""

    return concordance.file_digest(path)


def dataframe_digest(frame: pd.DataFrame) -> str:
    """Return the repository's stable frame-content digest."""

    return concordance.frame_digest(frame)


def atomic_write_json(payload: dict[str, Any], destination: Path) -> None:
    concordance.atomic_write_json(payload, destination)


def atomic_write_frame(frame: pd.DataFrame, destination: Path) -> None:
    concordance.atomic_write_frame(frame, destination)


def safe_exception_text(exc: BaseException) -> str:
    """Persist only an exception class and value-minimized provider message."""

    text = " ".join(str(exc).split())
    lowered = text.lower()
    if "token" in lowered:
        return f"{type(exc).__name__}: provider credential or permission rejected"
    return f"{type(exc).__name__}: {text[:300]}"


def validate_protocol() -> dict[str, Any]:
    if canonical_file_digest(PROTOCOL_PATH) != PROTOCOL_SHA256:
        raise TushareDailyMigrationError(
            f"Tushare daily migration protocol changed: {PROTOCOL_PATH}"
        )
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    if (
        protocol.get("kind")
        != "a_share_tushare_daily_provider_migration_protocol"
        or protocol.get("status") != "frozen_before_new_migration_provider_request"
        or (protocol.get("research_boundary") or {}).get("forward_return_fields_read")
        is not False
    ):
        raise TushareDailyMigrationError("Tushare daily migration protocol is rejected")
    return protocol


def _reference_file_records(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    records = manifest.get("files")
    if not isinstance(records, list) or len(records) != 7:
        raise TushareDailyMigrationError(
            "accepted Tushare daily reference must contain seven annual files"
        )
    years = [int(item.get("year", -1)) for item in records]
    if years != list(range(2019, 2026)):
        raise TushareDailyMigrationError(
            "accepted Tushare daily reference years changed"
        )
    return records


def validate_reference_snapshot(
    path: Path = DEFAULT_REFERENCE_MANIFEST,
    *,
    deep: bool = False,
) -> tuple[dict[str, Any], str]:
    """Validate the accepted source snapshot without reading any return label."""

    protocol = validate_protocol()
    path = path.expanduser().resolve()
    if not path.is_file():
        raise TushareDailyMigrationError(
            f"accepted Tushare daily snapshot is missing: {path}"
        )
    manifest_sha256 = canonical_file_digest(path)
    expected = (protocol["accepted_reference"])["snapshot_manifest_sha256"]
    if manifest_sha256 != expected:
        raise TushareDailyMigrationError(
            "accepted Tushare daily snapshot manifest fingerprint changed"
        )
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if (
        manifest.get("kind") != "a_share_tushare_daily_snapshot"
        or manifest.get("provider") != "tushare"
        or manifest.get("requested_start") != "2019-01-01"
        or manifest.get("requested_end") != "2025-12-31"
        or manifest.get("forward_return_fields_read") is not False
    ):
        raise TushareDailyMigrationError(
            "accepted Tushare daily snapshot identity changed"
        )
    for record in _reference_file_records(manifest):
        file_path = Path(str(record.get("path", ""))).expanduser().resolve()
        if (
            not file_path.is_file()
            or canonical_file_digest(file_path) != record.get("byte_sha256")
        ):
            raise TushareDailyMigrationError(
                f"accepted Tushare daily annual file changed: {file_path}"
            )
        if deep:
            frame = pd.read_parquet(file_path)
            if (
                len(frame) != int(record.get("rows", -1))
                or dataframe_digest(frame) != record.get("frame_sha256")
            ):
                raise TushareDailyMigrationError(
                    f"accepted Tushare daily annual frame changed: {file_path}"
                )
    concordance_path = REPO_ROOT / str(
        (protocol["accepted_reference"])["provider_concordance_result_path"]
    )
    if (
        not concordance_path.is_file()
        or canonical_file_digest(concordance_path)
        != (protocol["accepted_reference"])["provider_concordance_result_sha256"]
    ):
        raise TushareDailyMigrationError(
            "Tushare/BaoStock daily concordance evidence changed"
        )
    result = json.loads(concordance_path.read_text(encoding="utf-8"))
    if (
        result.get("status") != "completed_no_provider_switch"
        or (result.get("provider_comparison") or {}).get("classification") != "small"
        or (result.get("decision") or {}).get("use_tushare_daily_as_independent_mirror")
        is not True
    ):
        raise TushareDailyMigrationError(
            "Tushare/BaoStock daily concordance evidence is rejected"
        )
    return manifest, manifest_sha256


def storage_paths(staging_root: Path) -> dict[str, Path]:
    staging_root = staging_root.expanduser().resolve()
    source = (
        staging_root
        / "raw"
        / "a_share"
        / "rich"
        / "tushare"
        / "daily_provider_migration_v1"
    )
    return {
        "root": staging_root,
        "source": source,
        "calendar": source / "trade_calendar.parquet",
        "stock_basic": source / "stock_basic.parquet",
        "daily_sessions": source / "daily",
        "daily_basic_sessions": source / "daily_basic",
        "refresh_seed_intent": source / "refresh_seed_intent.json",
        "refresh_seed": source / "refresh_seed.json",
        "source_manifest": source / "source_manifest.json",
        "latest_failure": source / "latest_failure.json",
        "raw_daily": staging_root / "raw" / "a_share" / "daily",
        "metadata": staging_root / "metadata",
        "universe": staging_root / "metadata" / "universe_latest.json",
        "build_manifest": staging_root / "metadata" / "tushare_daily_build.json",
        "acceptance_manifest": (
            staging_root / "metadata" / "tushare_daily_provider_acceptance.json"
        ),
        "activation_intent": (
            staging_root / "metadata" / "tushare_daily_activation_intent.json"
        ),
        "activation_record": (
            staging_root / "metadata" / "tushare_daily_activation.json"
        ),
        "activation_failure": (
            staging_root / "metadata" / "tushare_daily_activation_failure.json"
        ),
        "qlib": staging_root / "qlib" / "cn_a_share",
        "lock": staging_root / ".a_share_tushare_daily_migration.lock",
    }


def validate_staging_boundary(
    staging_root: Path,
    *,
    allow_active: bool = False,
) -> Path:
    root = staging_root.expanduser().resolve()
    active = resolve_data_root(REPO_ROOT)
    if root == active and not allow_active:
        raise TushareDailyMigrationError(
            "Tushare migration staging root must differ from the active data root"
        )
    if active in root.parents:
        raise TushareDailyMigrationError(
            "Tushare migration staging root must not be nested inside the active root"
        )
    return root


def source_sync_staging_failures(staging_root: Path) -> list[str]:
    """Report local phases that make further provider intake immutable."""

    paths = storage_paths(staging_root)
    failures: list[str] = []
    if paths["acceptance_manifest"].exists():
        failures.append("staging_acceptance_already_exists")
    if paths["activation_intent"].exists() or paths["activation_record"].exists():
        failures.append("staging_activation_state_already_exists")
    if paths["raw_daily"].exists():
        failures.append("staging_canonical_daily_build_already_exists")
    if paths["universe"].exists():
        failures.append("staging_universe_manifest_already_exists")
    if paths["build_manifest"].exists():
        failures.append("staging_canonical_build_manifest_already_exists")
    if paths["qlib"].exists():
        failures.append("staging_qlib_build_already_exists")
    if paths["refresh_seed_intent"].exists() and not paths["refresh_seed"].exists():
        failures.append("staging_refresh_seed_incomplete")
    if paths["refresh_seed"].exists() and not paths["refresh_seed_intent"].exists():
        failures.append("staging_refresh_seed_intent_missing")
    return failures


def _session_paths(base: Path, trade_date: dt.date) -> tuple[Path, Path]:
    year_root = base / str(trade_date.year)
    return year_root / f"{trade_date.isoformat()}.parquet", year_root / (
        f"{trade_date.isoformat()}.json"
    )


def _frame_checkpoint(
    *,
    kind: str,
    frame: pd.DataFrame,
    data_path: Path,
    sidecar_path: Path,
    trade_date: dt.date | None = None,
) -> dict[str, Any]:
    atomic_write_frame(frame, data_path)
    record: dict[str, Any] = {
        "version": 1,
        "kind": kind,
        "protocol_sha256": PROTOCOL_SHA256,
        "path": str(data_path.resolve()),
        "rows": int(len(frame)),
        "columns": list(frame.columns),
        "byte_sha256": canonical_file_digest(data_path),
        "frame_sha256": dataframe_digest(frame),
        "completed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "provider": "tushare",
        "credential_value_persisted": False,
        "forward_return_fields_read": False,
    }
    if trade_date is not None:
        record["trade_date"] = trade_date.isoformat()
    atomic_write_json(record, sidecar_path)
    return record


def _load_checkpoint_record(
    *,
    kind: str,
    data_path: Path,
    sidecar_path: Path,
    trade_date: dt.date | None = None,
) -> dict[str, Any] | None:
    if not data_path.exists() and not sidecar_path.exists():
        return None
    if not data_path.is_file() or not sidecar_path.is_file():
        raise TushareDailyMigrationError(
            f"incomplete Tushare daily checkpoint: {data_path}"
        )
    record = json.loads(sidecar_path.read_text(encoding="utf-8"))
    if (
        record.get("kind") != kind
        or record.get("protocol_sha256") != PROTOCOL_SHA256
        or record.get("path") != str(data_path.resolve())
        or (trade_date is not None and record.get("trade_date") != trade_date.isoformat())
        or canonical_file_digest(data_path) != record.get("byte_sha256")
    ):
        raise TushareDailyMigrationError(
            f"changed Tushare daily checkpoint: {sidecar_path}"
        )
    return record


def _load_checkpoint(
    *,
    kind: str,
    data_path: Path,
    sidecar_path: Path,
    trade_date: dt.date | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]] | None:
    record = _load_checkpoint_record(
        kind=kind,
        data_path=data_path,
        sidecar_path=sidecar_path,
        trade_date=trade_date,
    )
    if record is None:
        return None
    frame = pd.read_parquet(data_path)
    if (
        list(frame.columns) != record.get("columns")
        or len(frame) != int(record.get("rows", -1))
        or dataframe_digest(frame) != record.get("frame_sha256")
    ):
        raise TushareDailyMigrationError(
            f"changed Tushare daily checkpoint frame: {data_path}"
        )
    return frame, record


def _refresh_seed_record_plan(
    *,
    parent_manifest: dict[str, Any],
    parent_paths: dict[str, Path],
    staging_paths: dict[str, Path],
) -> list[dict[str, Any]]:
    """Map every reusable parent source checkpoint to the new staging root."""

    plan: list[dict[str, Any]] = []
    for manifest_key, kind, parent_base, destination_base in (
        (
            "new_daily_session_records",
            "a_share_tushare_daily_session",
            parent_paths["daily_sessions"],
            staging_paths["daily_sessions"],
        ),
        (
            "daily_basic_session_records",
            "a_share_tushare_daily_basic_session",
            parent_paths["daily_basic_sessions"],
            staging_paths["daily_basic_sessions"],
        ),
    ):
        records = parent_manifest.get(manifest_key)
        if not isinstance(records, list):
            raise TushareDailyMigrationError(
                f"Tushare refresh parent {manifest_key} is invalid"
            )
        for parent_record in records:
            if not isinstance(parent_record, dict):
                raise TushareDailyMigrationError(
                    f"Tushare refresh parent {manifest_key} record is invalid"
                )
            try:
                trade_date = dt.date.fromisoformat(str(parent_record["trade_date"]))
            except (KeyError, ValueError) as exc:
                raise TushareDailyMigrationError(
                    f"Tushare refresh parent {manifest_key} date is invalid"
                ) from exc
            parent_data, parent_sidecar = _session_paths(parent_base, trade_date)
            destination_data, destination_sidecar = _session_paths(
                destination_base,
                trade_date,
            )
            if parent_record.get("path") != str(parent_data.resolve()):
                raise TushareDailyMigrationError(
                    "Tushare refresh parent checkpoint path changed"
                )
            plan.append(
                {
                    "kind": kind,
                    "trade_date": trade_date,
                    "parent_record": parent_record,
                    "parent_data": parent_data,
                    "parent_sidecar": parent_sidecar,
                    "destination_data": destination_data,
                    "destination_sidecar": destination_sidecar,
                }
            )
    return plan


def _refresh_seed_checkpoint_provenance(
    *,
    parent_root: Path,
    parent_source_manifest_sha256: str,
    item: dict[str, Any],
) -> dict[str, Any]:
    return {
        "parent_root": str(parent_root),
        "parent_source_manifest_sha256": parent_source_manifest_sha256,
        "parent_path": str(item["parent_data"].resolve()),
        "parent_sidecar_path": str(item["parent_sidecar"].resolve()),
        "parent_sidecar_sha256": canonical_file_digest(item["parent_sidecar"]),
    }


def _copy_refresh_seed_checkpoint(
    *,
    parent_root: Path,
    parent_source_manifest_sha256: str,
    item: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    """Copy one independent checkpoint and bind it to its accepted parent."""

    loaded_parent = _load_checkpoint(
        kind=item["kind"],
        data_path=item["parent_data"],
        sidecar_path=item["parent_sidecar"],
        trade_date=item["trade_date"],
    )
    if loaded_parent is None or loaded_parent[1] != item["parent_record"]:
        raise TushareDailyMigrationError(
            f"Tushare refresh parent checkpoint changed: {item['parent_data']}"
        )
    provenance = _refresh_seed_checkpoint_provenance(
        parent_root=parent_root,
        parent_source_manifest_sha256=parent_source_manifest_sha256,
        item=item,
    )
    destination_data = item["destination_data"]
    destination_sidecar = item["destination_sidecar"]
    if destination_data.exists() or destination_sidecar.exists():
        loaded_destination = _load_checkpoint(
            kind=item["kind"],
            data_path=destination_data,
            sidecar_path=destination_sidecar,
            trade_date=item["trade_date"],
        )
        if (
            loaded_destination is None
            or loaded_destination[1].get("seeded_from") != provenance
            or loaded_destination[1].get("byte_sha256")
            != item["parent_record"].get("byte_sha256")
            or loaded_destination[1].get("frame_sha256")
            != item["parent_record"].get("frame_sha256")
        ):
            raise TushareDailyMigrationError(
                f"Tushare refresh seeded checkpoint changed: {destination_data}"
            )
        if os.path.samefile(item["parent_data"], destination_data):
            raise TushareDailyMigrationError(
                f"Tushare refresh hardlink is forbidden: {destination_data}"
            )
        return loaded_destination[1], False

    destination_data.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=destination_data.parent,
        prefix=f".{destination_data.name}.",
        suffix=".partial",
        delete=False,
    ) as handle:
        temporary = Path(handle.name)
    try:
        shutil.copy2(item["parent_data"], temporary)
        if canonical_file_digest(temporary) != item["parent_record"].get(
            "byte_sha256"
        ):
            raise TushareDailyMigrationError(
                f"Tushare refresh checkpoint copy changed: {item['parent_data']}"
            )
        temporary.replace(destination_data)
    finally:
        temporary.unlink(missing_ok=True)
    seeded_record = {
        **item["parent_record"],
        "path": str(destination_data.resolve()),
        "seeded_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "seeded_from": provenance,
    }
    atomic_write_json(seeded_record, destination_sidecar)
    loaded_destination = _load_checkpoint(
        kind=item["kind"],
        data_path=destination_data,
        sidecar_path=destination_sidecar,
        trade_date=item["trade_date"],
    )
    if loaded_destination is None or loaded_destination[1] != seeded_record:
        raise TushareDailyMigrationError(
            f"Tushare refresh checkpoint post-copy validation failed: {destination_data}"
        )
    if os.path.samefile(item["parent_data"], destination_data):
        raise TushareDailyMigrationError(
            f"Tushare refresh hardlink is forbidden: {destination_data}"
        )
    return seeded_record, True


def _refresh_seed_aggregate(records: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for record in sorted(records, key=lambda value: str(value["path"])):
        digest.update(
            (
                f"{record['kind']}|{record['trade_date']}|{record['path']}|"
                f"{record['byte_sha256']}|{record['frame_sha256']}\n"
            ).encode("utf-8")
        )
    return digest.hexdigest()


def validate_refresh_seed(
    *,
    staging_root: Path,
    through_date: dt.date | None = None,
    require_parent_active: bool = False,
    deep: bool = True,
) -> dict[str, Any]:
    """Validate a completed source seed without provider or return access."""

    root = staging_root.expanduser().resolve()
    paths = storage_paths(root)
    if not paths["refresh_seed_intent"].is_file() or not paths[
        "refresh_seed"
    ].is_file():
        raise TushareDailyMigrationError(
            "Tushare refresh seed intent or completed manifest is missing"
        )
    intent = json.loads(paths["refresh_seed_intent"].read_text(encoding="utf-8"))
    seed = json.loads(paths["refresh_seed"].read_text(encoding="utf-8"))
    if (
        intent.get("kind") != "a_share_tushare_daily_refresh_seed_intent"
        or intent.get("status") != "copy_in_progress_no_provider_request"
        or intent.get("protocol_sha256") != PROTOCOL_SHA256
        or seed.get("kind") != "a_share_tushare_daily_refresh_seed"
        or seed.get("status")
        != "complete_pending_incremental_source_sync_and_full_local_rebuild"
        or seed.get("protocol_sha256") != PROTOCOL_SHA256
        or seed.get("intent_path") != str(paths["refresh_seed_intent"])
        or seed.get("intent_sha256")
        != canonical_file_digest(paths["refresh_seed_intent"])
        or seed.get("active_root_mutated") is not False
        or seed.get("provider_request_issued") is not False
        or seed.get("hardlinks_used") is not False
        or seed.get("forward_return_fields_read") is not False
    ):
        raise TushareDailyMigrationError("Tushare refresh seed identity is rejected")
    identity_keys = (
        "parent_root",
        "parent_through_date",
        "through_date",
        "parent_acceptance_path",
        "parent_acceptance_sha256",
        "parent_source_manifest_path",
        "parent_source_manifest_sha256",
    )
    if any(seed.get(key) != intent.get(key) for key in identity_keys):
        raise TushareDailyMigrationError(
            "Tushare refresh seed intent binding changed"
        )
    try:
        parent_root = Path(str(seed["parent_root"])).expanduser().resolve()
        parent_through_date = dt.date.fromisoformat(
            str(seed["parent_through_date"])
        )
        target_date = dt.date.fromisoformat(str(seed["through_date"]))
    except (KeyError, ValueError) as exc:
        raise TushareDailyMigrationError(
            "Tushare refresh seed date binding is invalid"
        ) from exc
    if (
        parent_root == root
        or target_date <= parent_through_date
        or (through_date is not None and target_date != through_date)
    ):
        raise TushareDailyMigrationError(
            "Tushare refresh seed parent or cutoff is rejected"
        )
    if require_parent_active and resolve_data_root(REPO_ROOT) != parent_root:
        raise TushareDailyMigrationError(
            "Tushare refresh seed parent is no longer the active data root"
        )
    parent_acceptance_path = Path(str(seed["parent_acceptance_path"])).resolve()
    parent_source_path = Path(str(seed["parent_source_manifest_path"])).resolve()
    if (
        not parent_acceptance_path.is_file()
        or canonical_file_digest(parent_acceptance_path)
        != seed.get("parent_acceptance_sha256")
        or not parent_source_path.is_file()
        or canonical_file_digest(parent_source_path)
        != seed.get("parent_source_manifest_sha256")
    ):
        raise TushareDailyMigrationError(
            "Tushare refresh seed parent manifest changed"
        )
    parent_acceptance = json.loads(
        parent_acceptance_path.read_text(encoding="utf-8")
    )
    parent_manifest = json.loads(parent_source_path.read_text(encoding="utf-8"))
    if (
        parent_acceptance.get("status")
        != "accepted_staging_pending_explicit_crash_safe_activation"
        or parent_acceptance.get("daily_source") != "tushare"
        or parent_acceptance.get("through_date")
        != parent_through_date.isoformat()
        or parent_acceptance.get("source_manifest_path") != str(parent_source_path)
        or parent_acceptance.get("source_manifest_sha256")
        != seed.get("parent_source_manifest_sha256")
        or parent_manifest.get("through_date") != parent_through_date.isoformat()
        or parent_manifest.get("protocol_sha256") != PROTOCOL_SHA256
    ):
        raise TushareDailyMigrationError(
            "Tushare refresh seed parent acceptance is rejected"
        )
    parent_paths = storage_paths(parent_root)
    plan = _refresh_seed_record_plan(
        parent_manifest=parent_manifest,
        parent_paths=parent_paths,
        staging_paths=paths,
    )
    records: list[dict[str, Any]] = []
    expected_data: set[Path] = set()
    expected_sidecars: set[Path] = set()
    for item in plan:
        expected_data.add(item["destination_data"])
        expected_sidecars.add(item["destination_sidecar"])
        if deep:
            loaded_checkpoint = _load_checkpoint(
                kind=item["kind"],
                data_path=item["destination_data"],
                sidecar_path=item["destination_sidecar"],
                trade_date=item["trade_date"],
            )
            loaded = (
                loaded_checkpoint[1]
                if loaded_checkpoint is not None
                else None
            )
        else:
            loaded = _load_checkpoint_record(
                kind=item["kind"],
                data_path=item["destination_data"],
                sidecar_path=item["destination_sidecar"],
                trade_date=item["trade_date"],
            )
        expected_provenance = _refresh_seed_checkpoint_provenance(
            parent_root=parent_root,
            parent_source_manifest_sha256=str(
                seed["parent_source_manifest_sha256"]
            ),
            item=item,
        )
        if (
            loaded is None
            or loaded.get("seeded_from") != expected_provenance
            or loaded.get("byte_sha256")
            != item["parent_record"].get("byte_sha256")
            or loaded.get("frame_sha256")
            != item["parent_record"].get("frame_sha256")
        ):
            raise TushareDailyMigrationError(
                f"Tushare refresh seeded checkpoint is rejected: "
                f"{item['destination_data']}"
            )
        if os.path.samefile(item["parent_data"], item["destination_data"]):
            raise TushareDailyMigrationError(
                f"Tushare refresh hardlink is forbidden: "
                f"{item['destination_data']}"
            )
        records.append(loaded)
    actual_data = set(paths["daily_sessions"].rglob("*.parquet")) | set(
        paths["daily_basic_sessions"].rglob("*.parquet")
    )
    actual_sidecars = set(paths["daily_sessions"].rglob("*.json")) | set(
        paths["daily_basic_sessions"].rglob("*.json")
    )
    if not expected_data.issubset(actual_data) or not expected_sidecars.issubset(
        actual_sidecars
    ):
        raise TushareDailyMigrationError(
            "Tushare refresh seeded checkpoint set is incomplete"
        )
    extra_data = actual_data - expected_data
    extra_sidecars = actual_sidecars - expected_sidecars
    for data_path in sorted(extra_data):
        try:
            extra_date = dt.date.fromisoformat(data_path.stem)
        except ValueError as exc:
            raise TushareDailyMigrationError(
                f"Tushare refresh has an unexpected checkpoint: {data_path}"
            ) from exc
        if not parent_through_date < extra_date <= target_date:
            raise TushareDailyMigrationError(
                f"Tushare refresh extra checkpoint date is rejected: {data_path}"
            )
        sidecar_path = data_path.with_suffix(".json")
        if sidecar_path not in extra_sidecars:
            raise TushareDailyMigrationError(
                f"Tushare refresh extra checkpoint is incomplete: {data_path}"
            )
        kind = (
            "a_share_tushare_daily_basic_session"
            if paths["daily_basic_sessions"] in data_path.parents
            else "a_share_tushare_daily_session"
        )
        if deep:
            extra_loaded = _load_checkpoint(
                kind=kind,
                data_path=data_path,
                sidecar_path=sidecar_path,
                trade_date=extra_date,
            )
        else:
            extra_loaded = _load_checkpoint_record(
                kind=kind,
                data_path=data_path,
                sidecar_path=sidecar_path,
                trade_date=extra_date,
            )
        if extra_loaded is None:
            raise TushareDailyMigrationError(
                f"Tushare refresh extra checkpoint is rejected: {data_path}"
            )
    if {path.with_suffix(".json") for path in extra_data} != extra_sidecars:
        raise TushareDailyMigrationError(
            "Tushare refresh extra checkpoint sidecar set changed"
        )
    if (
        int(seed.get("seeded_session_checkpoints", -1)) != len(records)
        or seed.get("seeded_checkpoint_aggregate_sha256")
        != _refresh_seed_aggregate(records)
    ):
        raise TushareDailyMigrationError(
            "Tushare refresh seed aggregate changed"
        )
    return seed


def seed_refresh_source(
    *,
    parent_root: Path,
    staging_root: Path,
    through_date: dt.date,
    reference_manifest: Path = DEFAULT_REFERENCE_MANIFEST,
) -> Path:
    """Seed a new staging version from the accepted active Tushare source."""

    validate_protocol()
    root = validate_staging_boundary(staging_root)
    paths = storage_paths(root)
    parent_root = parent_root.expanduser().resolve()
    active_root = resolve_data_root(REPO_ROOT)
    if parent_root != active_root:
        raise TushareDailyMigrationError(
            "Tushare refresh parent must be the current active data root"
        )
    phase_failures = [
        failure
        for failure in source_sync_staging_failures(root)
        if failure
        not in {
            "staging_refresh_seed_incomplete",
            "staging_refresh_seed_intent_missing",
        }
    ]
    if paths["refresh_seed"].is_file() and not paths["source_manifest"].exists():
        validate_refresh_seed(
            staging_root=root,
            through_date=through_date,
            require_parent_active=True,
        )
        return paths["refresh_seed"]
    if paths["source_manifest"].exists() or phase_failures:
        raise TushareDailyMigrationError(
            "Tushare refresh staging is not a resumable clean source root: "
            + ",".join(phase_failures or ["source_manifest_already_exists"])
        )
    safe_cutoff = latest_completed_session_date()
    if through_date > safe_cutoff:
        raise TushareDailyMigrationError(
            "Tushare refresh cutoff is later than the safe completed session"
        )
    parent_paths = storage_paths(parent_root)
    parent_acceptance = validate_staging_acceptance(parent_root)
    parent_manifest, _ = _load_source_manifest(
        staging_root=parent_root,
        reference_manifest=reference_manifest,
    )
    parent_through_date = dt.date.fromisoformat(
        str(parent_manifest["through_date"])
    )
    if (
        parent_acceptance.get("through_date") != parent_through_date.isoformat()
        or through_date <= parent_through_date
    ):
        raise TushareDailyMigrationError(
            "Tushare refresh cutoff must be later than the accepted parent cutoff"
        )
    parent_acceptance_sha256 = canonical_file_digest(
        parent_paths["acceptance_manifest"]
    )
    parent_source_sha256 = canonical_file_digest(parent_paths["source_manifest"])
    intent_identity = {
        "parent_root": str(parent_root),
        "parent_through_date": parent_through_date.isoformat(),
        "through_date": through_date.isoformat(),
        "parent_acceptance_path": str(parent_paths["acceptance_manifest"]),
        "parent_acceptance_sha256": parent_acceptance_sha256,
        "parent_source_manifest_path": str(parent_paths["source_manifest"]),
        "parent_source_manifest_sha256": parent_source_sha256,
    }
    if paths["refresh_seed_intent"].is_file():
        intent = json.loads(
            paths["refresh_seed_intent"].read_text(encoding="utf-8")
        )
        if (
            intent.get("kind") != "a_share_tushare_daily_refresh_seed_intent"
            or intent.get("status") != "copy_in_progress_no_provider_request"
            or intent.get("protocol_sha256") != PROTOCOL_SHA256
            or any(intent.get(key) != value for key, value in intent_identity.items())
        ):
            raise TushareDailyMigrationError(
                "Tushare refresh seed intent changed"
            )
    else:
        intent = {
            "version": 1,
            "kind": "a_share_tushare_daily_refresh_seed_intent",
            "status": "copy_in_progress_no_provider_request",
            "protocol_path": str(PROTOCOL_PATH),
            "protocol_sha256": PROTOCOL_SHA256,
            "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            **intent_identity,
            "provider_request_issued": False,
            "active_root_mutated": False,
            "hardlinks_allowed": False,
            "forward_return_fields_read": False,
        }
        atomic_write_json(intent, paths["refresh_seed_intent"])
    plan = _refresh_seed_record_plan(
        parent_manifest=parent_manifest,
        parent_paths=parent_paths,
        staging_paths=paths,
    )
    allowed_staging_files = {
        paths["refresh_seed_intent"],
        paths["refresh_seed"],
        paths["lock"],
        *(
            item[path_key]
            for item in plan
            for path_key in ("destination_data", "destination_sidecar")
        ),
    }
    unexpected_staging_files = sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path not in allowed_staging_files
    )
    if unexpected_staging_files:
        raise TushareDailyMigrationError(
            "Tushare refresh staging contains an unexpected file: "
            f"{unexpected_staging_files[0]}"
        )
    required_copy_bytes = sum(
        item["parent_data"].stat().st_size
        + item["parent_sidecar"].stat().st_size
        for item in plan
        if not item["destination_data"].exists()
        and not item["destination_sidecar"].exists()
    )
    free_bytes = shutil.disk_usage(
        root if root.exists() else root.parent
    ).free
    if free_bytes < required_copy_bytes + 1024**3:
        raise TushareDailyMigrationError(
            "Tushare refresh staging lacks copy bytes plus one GiB headroom"
        )
    records: list[dict[str, Any]] = []
    copied = 0
    copied_bytes = 0
    with concordance.ProcessLock(paths["lock"]):
        for index, item in enumerate(plan, start=1):
            record, was_copied = _copy_refresh_seed_checkpoint(
                parent_root=parent_root,
                parent_source_manifest_sha256=parent_source_sha256,
                item=item,
            )
            records.append(record)
            if was_copied:
                copied += 1
                copied_bytes += item["parent_data"].stat().st_size
            if index % 250 == 0 or index == len(plan):
                print(
                    f"refresh seed progress checkpoints={index:,}/{len(plan):,}",
                    flush=True,
                )
        seed = {
            "version": 1,
            "kind": "a_share_tushare_daily_refresh_seed",
            "status": (
                "complete_pending_incremental_source_sync_and_full_local_rebuild"
            ),
            "protocol_path": str(PROTOCOL_PATH),
            "protocol_sha256": PROTOCOL_SHA256,
            "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "intent_path": str(paths["refresh_seed_intent"]),
            "intent_sha256": canonical_file_digest(paths["refresh_seed_intent"]),
            **intent_identity,
            "seeded_session_checkpoints": len(records),
            "seeded_daily_checkpoints": sum(
                record["kind"] == "a_share_tushare_daily_session"
                for record in records
            ),
            "seeded_daily_basic_checkpoints": sum(
                record["kind"] == "a_share_tushare_daily_basic_session"
                for record in records
            ),
            "seeded_checkpoint_aggregate_sha256": _refresh_seed_aggregate(records),
            "copied_checkpoints_this_invocation": copied,
            "copied_data_bytes_this_invocation": copied_bytes,
            "required_copy_bytes_before_invocation": required_copy_bytes,
            "hardlinks_used": False,
            "trade_calendar_copied": False,
            "stock_basic_copied": False,
            "canonical_raw_or_qlib_copied": False,
            "provider_request_issued": False,
            "active_root_mutated": False,
            "forward_return_fields_read": False,
            "factor_values_read": False,
        }
        atomic_write_json(seed, paths["refresh_seed"])
    validate_refresh_seed(
        staging_root=root,
        through_date=through_date,
        require_parent_active=True,
    )
    return paths["refresh_seed"]


def canonicalize_trade_calendar(
    raw: pd.DataFrame,
    *,
    start: dt.date,
    end: dt.date,
) -> pd.DataFrame:
    if raw.empty or set(raw.columns) != set(TRADE_CAL_FIELDS):
        raise TushareDailyMigrationError("Tushare trade_cal schema is rejected")
    frame = raw.loc[:, TRADE_CAL_FIELDS].copy()
    frame["cal_date"] = pd.to_datetime(
        frame["cal_date"].astype(str), format="%Y%m%d", errors="coerce"
    )
    frame["is_open"] = pd.to_numeric(frame["is_open"], errors="coerce")
    frame["pretrade_date"] = pd.to_datetime(
        frame["pretrade_date"].astype(str), format="%Y%m%d", errors="coerce"
    )
    if (
        frame["cal_date"].isna().any()
        or frame["is_open"].isna().any()
        or not frame["is_open"].isin([0, 1]).all()
        or frame["cal_date"].duplicated().any()
    ):
        raise TushareDailyMigrationError("Tushare trade_cal values are rejected")
    frame = frame[
        frame["cal_date"].between(pd.Timestamp(start), pd.Timestamp(end))
    ].sort_values("cal_date", kind="stable")
    open_frame = frame[frame["is_open"].eq(1)].reset_index(drop=True)
    if open_frame.empty or open_frame["cal_date"].iloc[-1].date() != end:
        raise TushareDailyMigrationError(
            "requested Tushare through date is not an open session"
        )
    return frame.reset_index(drop=True)


def canonicalize_daily_basic(
    raw: pd.DataFrame,
    trade_date: dt.date,
) -> pd.DataFrame:
    if raw.empty or len(raw) >= 6000 or set(raw.columns) != set(DAILY_BASIC_FIELDS):
        raise TushareDailyMigrationError("Tushare daily_basic schema is rejected")
    frame = raw.loc[:, DAILY_BASIC_FIELDS].copy()
    frame["ts_code"] = frame["ts_code"].astype(str).str.upper().str.strip()
    if not frame["ts_code"].map(lambda value: bool(CODE_PATTERN.fullmatch(value))).all():
        raise TushareDailyMigrationError("Tushare daily_basic contains an invalid code")
    frame["trade_date"] = pd.to_datetime(
        frame["trade_date"].astype(str), format="%Y%m%d", errors="coerce"
    )
    frame["turnover_rate"] = pd.to_numeric(frame["turnover_rate"], errors="coerce")
    if (
        frame["trade_date"].isna().any()
        or set(frame["trade_date"].dt.date) != {trade_date}
        or frame.duplicated(["ts_code", "trade_date"]).any()
        or (frame["turnover_rate"].dropna() < 0.0).any()
        or np.isinf(frame["turnover_rate"].dropna().to_numpy(dtype=float)).any()
    ):
        raise TushareDailyMigrationError("Tushare daily_basic values are rejected")
    return frame.sort_values(["trade_date", "ts_code"], kind="stable").reset_index(
        drop=True
    )


def canonicalize_stock_basic(raw_frames: list[pd.DataFrame]) -> pd.DataFrame:
    if not raw_frames:
        raise TushareDailyMigrationError("Tushare stock_basic returned no frames")
    frames: list[pd.DataFrame] = []
    for raw in raw_frames:
        if raw.empty:
            continue
        if set(raw.columns) != set(STOCK_BASIC_FIELDS):
            raise TushareDailyMigrationError("Tushare stock_basic schema is rejected")
        frames.append(raw.loc[:, STOCK_BASIC_FIELDS].copy())
    if not frames:
        raise TushareDailyMigrationError("Tushare stock_basic returned no rows")
    frame = pd.concat(frames, ignore_index=True)
    frame["ts_code"] = frame["ts_code"].astype(str).str.upper().str.strip()
    frame["symbol"] = frame["symbol"].astype(str).str.strip()
    frame["list_status"] = frame["list_status"].astype(str).str.upper().str.strip()
    if not frame["ts_code"].map(
        lambda value: bool(CODE_PATTERN.fullmatch(value))
    ).all():
        raise TushareDailyMigrationError(
            "Tushare stock_basic contains an invalid ts_code"
        )
    if not frame["list_status"].isin(["L", "D", "P"]).all():
        raise TushareDailyMigrationError(
            "Tushare stock_basic contains a list_status outside L/D/P"
        )
    if frame.duplicated(["ts_code"]).any():
        raise TushareDailyMigrationError(
            "Tushare stock_basic contains duplicate ts_code identities across "
            "the L/D/P responses"
        )
    for column in ("list_date", "delist_date"):
        values = frame[column].astype("string").str.strip()
        parsed = pd.to_datetime(values, format="%Y%m%d", errors="coerce")
        invalid = values.notna() & values.ne("") & parsed.isna()
        if invalid.any():
            raise TushareDailyMigrationError(
                f"Tushare stock_basic contains an invalid {column}"
            )
        frame[column] = parsed
    return frame.sort_values("ts_code", kind="stable").reset_index(drop=True)


class AggregateRateLimiter:
    def __init__(
        self,
        minimum_interval_seconds: float = MINIMUM_CALL_INTERVAL_SECONDS,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self.minimum_interval_seconds = minimum_interval_seconds
        self.clock = clock
        self.sleeper = sleeper
        self.last_started = 0.0

    def wait(self) -> None:
        now = self.clock()
        delay = self.minimum_interval_seconds - (now - self.last_started)
        if delay > 0.0:
            self.sleeper(delay)
        self.last_started = self.clock()


def _provider_request(
    provider: Any,
    interface: str,
    *,
    limiter: AggregateRateLimiter,
    **kwargs: Any,
) -> pd.DataFrame:
    last_error: BaseException | None = None
    for attempt in range(1, MAXIMUM_PROVIDER_ATTEMPTS + 1):
        limiter.wait()
        try:
            result = getattr(provider, interface)(**kwargs)
            if not isinstance(result, pd.DataFrame):
                raise TushareDailyMigrationError(
                    f"Tushare {interface} did not return a DataFrame"
                )
            return result
        except TushareDailyMigrationError:
            raise
        except BaseException as exc:
            last_error = exc
            lowered = str(exc).lower()
            if any(
                marker in lowered
                for marker in ("权限", "积分", "permission", "token", "参数", "接口")
            ):
                break
            if attempt < MAXIMUM_PROVIDER_ATTEMPTS:
                time.sleep(float(attempt))
    raise TushareDailyMigrationError(
        f"Tushare {interface} request failed after frozen attempts: "
        f"{safe_exception_text(last_error or RuntimeError('unknown provider failure'))}"
    )


def tushare_client() -> Any:
    token = os.environ.get("TUSHARE_TOKEN", "")
    if not token:
        raise TushareDailyMigrationError(
            "TUSHARE_TOKEN is not configured in this process"
        )
    try:
        import tushare as ts  # pylint: disable=import-outside-toplevel
    except ImportError as exc:
        raise TushareDailyMigrationError("the tushare package is not installed") from exc
    return ts.pro_api(token)


def preflight(
    *,
    staging_root: Path,
    through_date: dt.date,
    reference_manifest: Path = DEFAULT_REFERENCE_MANIFEST,
    token_configured: bool | None = None,
) -> dict[str, Any]:
    """Validate the migration boundary without writing or requesting."""

    root = validate_staging_boundary(staging_root)
    _, reference_sha256 = validate_reference_snapshot(reference_manifest)
    safe_cutoff = latest_completed_session_date()
    failures: list[str] = []
    if through_date < HISTORY_START:
        failures.append("through_date_before_history_start")
    if through_date > safe_cutoff:
        failures.append("through_date_after_safe_completed_session_cutoff")
    if token_configured is None:
        token_configured = bool(os.environ.get("TUSHARE_TOKEN", ""))
    if not token_configured:
        failures.append("TUSHARE_TOKEN_missing_in_current_process")
    active_root = resolve_data_root(REPO_ROOT)
    active_sources, invalid_active_files = pipeline.inspect_existing_daily_sources(
        active_root / "raw" / "a_share" / "daily"
    )
    if invalid_active_files or len(active_sources) != 1:
        failures.append("active_daily_root_not_one_valid_source")
    free_bytes = (
        shutil.disk_usage(root.parent if not root.exists() else root).free
        if root.parent.exists()
        else 0
    )
    if free_bytes < 5 * 1024**3:
        failures.append("staging_filesystem_has_less_than_5_GiB_free")
    failures.extend(source_sync_staging_failures(root))
    refresh_seed_valid: bool | None = None
    refresh_seed_error: str | None = None
    paths = storage_paths(root)
    if paths["refresh_seed"].exists():
        try:
            validate_refresh_seed(
                staging_root=root,
                through_date=through_date,
                require_parent_active=True,
                deep=False,
            )
            refresh_seed_valid = True
        except BaseException as exc:
            refresh_seed_valid = False
            refresh_seed_error = safe_exception_text(exc)
            failures.append("staging_refresh_seed_not_valid")
    failures = list(dict.fromkeys(failures))
    ready = not failures
    return {
        "kind": "a_share_tushare_daily_provider_migration_preflight",
        "status": (
            "ready_for_explicit_tushare_source_sync"
            if ready
            else "not_ready_no_provider_request"
        ),
        "ready": ready,
        "recommended_cli_exit_code": 0 if ready else 2,
        "protocol_path": str(PROTOCOL_PATH),
        "protocol_sha256": PROTOCOL_SHA256,
        "reference_manifest_path": str(reference_manifest.expanduser().resolve()),
        "reference_manifest_sha256": reference_sha256,
        "active_data_root": str(active_root),
        "active_daily_sources": sorted(active_sources),
        "active_invalid_source_files": invalid_active_files[:20],
        "staging_root": str(root),
        "staging_free_bytes": int(free_bytes),
        "history_start": HISTORY_START.isoformat(),
        "through_date": through_date.isoformat(),
        "safe_completed_session_cutoff": safe_cutoff.isoformat(),
        "token_configured": bool(token_configured),
        "refresh_seed_valid": refresh_seed_valid,
        "refresh_seed_error": refresh_seed_error,
        "failures": failures,
        "provider_request_issued": False,
        "filesystem_write_performed": False,
        "active_root_mutated": False,
        "forward_return_fields_read": False,
    }


def _record_source_failure(
    *,
    paths: dict[str, Path],
    started_at: dt.datetime,
    through_date: dt.date,
    stage: str,
    exc: BaseException,
    provider_calls: int,
) -> None:
    record = {
        "version": 1,
        "kind": "a_share_tushare_daily_provider_migration_source_failure",
        "status": "failed_preserving_active_root_and_completed_checkpoints",
        "protocol_sha256": PROTOCOL_SHA256,
        "started_at": started_at.isoformat(),
        "failed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "through_date": through_date.isoformat(),
        "failure_stage": stage,
        "error": safe_exception_text(exc),
        "provider_calls_this_invocation": int(provider_calls),
        "credential_value_persisted": False,
        "active_root_mutated": False,
        "completed_session_checkpoints_preserved": True,
        "forward_return_fields_read": False,
    }
    atomic_write_json(record, paths["latest_failure"])


def sync_source(
    *,
    staging_root: Path,
    through_date: dt.date,
    reference_manifest: Path = DEFAULT_REFERENCE_MANIFEST,
    provider: Any | None = None,
    limiter: AggregateRateLimiter | None = None,
) -> Path:
    """Collect immutable missing daily/daily_basic sessions into staging."""

    root = validate_staging_boundary(staging_root)
    paths = storage_paths(root)
    phase_failures = [
        failure
        for failure in source_sync_staging_failures(root)
        if failure
        not in {
            "staging_refresh_seed_incomplete",
            "staging_refresh_seed_intent_missing",
        }
    ]
    if phase_failures:
        raise TushareDailyMigrationError(
            "Tushare daily staging is immutable after canonical build state: "
            + ",".join(phase_failures)
        )
    if paths["source_manifest"].is_file():
        completed, _ = _load_source_manifest(
            staging_root=root,
            reference_manifest=reference_manifest,
        )
        if completed.get("through_date") != through_date.isoformat():
            raise TushareDailyMigrationError(
                "completed Tushare source snapshot cutoff is immutable; use a "
                "new isolated staging root for a different through date"
            )
        return paths["source_manifest"]
    if paths["refresh_seed_intent"].exists() and not paths["refresh_seed"].exists():
        raise TushareDailyMigrationError(
            "Tushare refresh seed is incomplete; resume seed-refresh before sync"
        )
    refresh_seed: dict[str, Any] | None = None
    refresh_seed_present = paths["refresh_seed"].exists()
    if not refresh_seed_present and paths["refresh_seed_intent"].exists():
        raise TushareDailyMigrationError(
            "Tushare refresh seed intent is invalid"
        )
    pre = preflight(
        staging_root=root,
        through_date=through_date,
        reference_manifest=reference_manifest,
        token_configured=True if provider is not None else None,
    )
    if not pre["ready"]:
        raise TushareDailyMigrationError(
            "Tushare daily migration preflight failed: " + ",".join(pre["failures"])
        )
    if refresh_seed_present:
        refresh_seed = (
            json.loads(paths["refresh_seed"].read_text(encoding="utf-8"))
            if pre.get("refresh_seed_valid") is True
            else validate_refresh_seed(
                staging_root=root,
                through_date=through_date,
                require_parent_active=True,
                deep=False,
            )
        )
    reference, reference_sha256 = validate_reference_snapshot(reference_manifest)
    started_at = dt.datetime.now(dt.timezone.utc)
    provider_calls = 0
    stage = "initialize_provider"
    limiter = limiter or AggregateRateLimiter()
    if provider is None:
        provider = tushare_client()
    with concordance.ProcessLock(paths["lock"]):
        try:
            stage = "trade_calendar"
            raw_calendar = _provider_request(
                provider,
                "trade_cal",
                limiter=limiter,
                exchange="SSE",
                start_date=HISTORY_START.strftime("%Y%m%d"),
                end_date=through_date.strftime("%Y%m%d"),
                fields=",".join(TRADE_CAL_FIELDS),
            )
            provider_calls += 1
            calendar = canonicalize_trade_calendar(
                raw_calendar,
                start=HISTORY_START,
                end=through_date,
            )
            _frame_checkpoint(
                kind="a_share_tushare_daily_migration_trade_calendar",
                frame=calendar,
                data_path=paths["calendar"],
                sidecar_path=paths["calendar"].with_suffix(".json"),
            )

            stage = "stock_basic"
            stock_frames: list[pd.DataFrame] = []
            for list_status in ("L", "D", "P"):
                raw = _provider_request(
                    provider,
                    "stock_basic",
                    limiter=limiter,
                    exchange="",
                    list_status=list_status,
                    fields=",".join(STOCK_BASIC_FIELDS),
                )
                provider_calls += 1
                stock_frames.append(raw)
            stock_basic = canonicalize_stock_basic(stock_frames)
            _frame_checkpoint(
                kind="a_share_tushare_daily_migration_stock_basic",
                frame=stock_basic,
                data_path=paths["stock_basic"],
                sidecar_path=paths["stock_basic"].with_suffix(".json"),
            )

            open_dates = [
                value.date()
                for value in calendar.loc[calendar["is_open"].eq(1), "cal_date"]
            ]
            daily_records: list[dict[str, Any]] = []
            basic_records: list[dict[str, Any]] = []
            reused_daily_sessions = 0
            reused_daily_checkpoints = 0
            reused_daily_basic_checkpoints = 0
            requested_daily_sessions = 0
            requested_daily_basic_sessions = 0
            for index, trade_date in enumerate(open_dates, start=1):
                stage = f"daily_basic:{trade_date.isoformat()}"
                basic_path, basic_sidecar = _session_paths(
                    paths["daily_basic_sessions"], trade_date
                )
                completed_basic = _load_checkpoint(
                    kind="a_share_tushare_daily_basic_session",
                    data_path=basic_path,
                    sidecar_path=basic_sidecar,
                    trade_date=trade_date,
                )
                if completed_basic is None:
                    raw_basic = _provider_request(
                        provider,
                        "daily_basic",
                        limiter=limiter,
                        trade_date=trade_date.strftime("%Y%m%d"),
                        fields=",".join(DAILY_BASIC_FIELDS),
                    )
                    provider_calls += 1
                    requested_daily_basic_sessions += 1
                    basic_frame = canonicalize_daily_basic(raw_basic, trade_date)
                    basic_record = _frame_checkpoint(
                        kind="a_share_tushare_daily_basic_session",
                        frame=basic_frame,
                        data_path=basic_path,
                        sidecar_path=basic_sidecar,
                        trade_date=trade_date,
                    )
                else:
                    _, basic_record = completed_basic
                    reused_daily_basic_checkpoints += 1
                basic_records.append(basic_record)

                if REFERENCE_START <= trade_date <= REFERENCE_END:
                    reused_daily_sessions += 1
                else:
                    stage = f"daily:{trade_date.isoformat()}"
                    daily_path, daily_sidecar = _session_paths(
                        paths["daily_sessions"], trade_date
                    )
                    completed_daily = _load_checkpoint(
                        kind="a_share_tushare_daily_session",
                        data_path=daily_path,
                        sidecar_path=daily_sidecar,
                        trade_date=trade_date,
                    )
                    if completed_daily is None:
                        raw_daily = _provider_request(
                            provider,
                            "daily",
                            limiter=limiter,
                            trade_date=trade_date.strftime("%Y%m%d"),
                            fields=",".join(DAILY_FIELDS),
                        )
                        provider_calls += 1
                        requested_daily_sessions += 1
                        daily_frame = concordance.canonicalize_tushare_daily(
                            raw_daily,
                            trade_date,
                        )
                        daily_record = _frame_checkpoint(
                            kind="a_share_tushare_daily_session",
                            frame=daily_frame,
                            data_path=daily_path,
                            sidecar_path=daily_sidecar,
                            trade_date=trade_date,
                        )
                    else:
                        _, daily_record = completed_daily
                        reused_daily_checkpoints += 1
                    daily_records.append(daily_record)
                if index % 25 == 0 or index == len(open_dates):
                    print(
                        f"source progress sessions={index:,}/{len(open_dates):,} "
                        f"provider_calls={provider_calls:,}",
                        flush=True,
                    )

            stage = "publish_source_manifest"
            manifest = {
                "version": 1,
                "kind": "a_share_tushare_daily_provider_migration_source_snapshot",
                "status": "complete_pending_canonical_build_and_acceptance",
                "protocol_path": str(PROTOCOL_PATH),
                "protocol_sha256": PROTOCOL_SHA256,
                "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "history_start": HISTORY_START.isoformat(),
                "through_date": through_date.isoformat(),
                "open_sessions": len(open_dates),
                "calendar": {
                    "path": str(paths["calendar"]),
                    "byte_sha256": canonical_file_digest(paths["calendar"]),
                    "rows": len(calendar),
                },
                "stock_basic": {
                    "path": str(paths["stock_basic"]),
                    "byte_sha256": canonical_file_digest(paths["stock_basic"]),
                    "rows": len(stock_basic),
                },
                "accepted_reference_manifest_path": str(
                    reference_manifest.expanduser().resolve()
                ),
                "accepted_reference_manifest_sha256": reference_sha256,
                "accepted_reference_rows": int(reference["rows"]),
                "reference_daily_sessions_reused": reused_daily_sessions,
                "reference_daily_sessions_requested_this_invocation": 0,
                "new_daily_session_records": daily_records,
                "daily_basic_session_records": basic_records,
                "refresh_seed": (
                    {
                        "path": str(paths["refresh_seed"]),
                        "sha256": canonical_file_digest(paths["refresh_seed"]),
                        "parent_root": refresh_seed["parent_root"],
                        "parent_through_date": refresh_seed[
                            "parent_through_date"
                        ],
                        "seeded_session_checkpoints": refresh_seed[
                            "seeded_session_checkpoints"
                        ],
                    }
                    if refresh_seed is not None
                    else None
                ),
                "reused_daily_checkpoints_this_invocation": (
                    reused_daily_checkpoints
                ),
                "reused_daily_basic_checkpoints_this_invocation": (
                    reused_daily_basic_checkpoints
                ),
                "requested_daily_sessions_this_invocation": (
                    requested_daily_sessions
                ),
                "requested_daily_basic_sessions_this_invocation": (
                    requested_daily_basic_sessions
                ),
                "provider_calls_this_invocation": provider_calls,
                "credential_value_persisted": False,
                "active_root_mutated": False,
                "forward_return_fields_read": False,
                "factor_values_read": False,
            }
            atomic_write_json(manifest, paths["source_manifest"])
            return paths["source_manifest"]
        except BaseException as exc:
            _record_source_failure(
                paths=paths,
                started_at=started_at,
                through_date=through_date,
                stage=stage,
                exc=exc,
                provider_calls=provider_calls,
            )
            raise


def _validate_session_manifest_records(
    *,
    records: Any,
    expected_dates: list[dt.date],
    base: Path,
    kind: str,
) -> None:
    if not isinstance(records, list) or len(records) != len(expected_dates):
        raise TushareDailyMigrationError(
            f"Tushare source manifest {kind} record count changed"
        )
    expected_data_paths: set[Path] = set()
    expected_sidecars: set[Path] = set()
    for record, trade_date in zip(records, expected_dates, strict=True):
        if not isinstance(record, dict):
            raise TushareDailyMigrationError(
                f"Tushare source manifest {kind} record is invalid"
            )
        data_path, sidecar_path = _session_paths(base, trade_date)
        expected_data_paths.add(data_path)
        expected_sidecars.add(sidecar_path)
        if not data_path.is_file() or not sidecar_path.is_file():
            raise TushareDailyMigrationError(
                f"Tushare source manifest checkpoint is missing: {data_path}"
            )
        sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
        if (
            sidecar != record
            or record.get("kind") != kind
            or record.get("protocol_sha256") != PROTOCOL_SHA256
            or record.get("provider") != "tushare"
            or record.get("trade_date") != trade_date.isoformat()
            or record.get("path") != str(data_path.resolve())
            or record.get("credential_value_persisted") is not False
            or record.get("forward_return_fields_read") is not False
            or canonical_file_digest(data_path) != record.get("byte_sha256")
        ):
            raise TushareDailyMigrationError(
                f"Tushare source manifest checkpoint binding changed: {sidecar_path}"
            )
    actual_data_paths = (
        set(base.rglob("*.parquet")) if base.exists() else set()
    )
    actual_sidecars = set(base.rglob("*.json")) if base.exists() else set()
    if (
        actual_data_paths != expected_data_paths
        or actual_sidecars != expected_sidecars
    ):
        raise TushareDailyMigrationError(
            f"Tushare source manifest {kind} checkpoint set changed"
        )


def _validate_source_manifest_bindings(
    manifest: dict[str, Any],
    paths: dict[str, Path],
) -> None:
    calendar_checkpoint = _load_checkpoint(
        kind="a_share_tushare_daily_migration_trade_calendar",
        data_path=paths["calendar"],
        sidecar_path=paths["calendar"].with_suffix(".json"),
    )
    stock_checkpoint = _load_checkpoint(
        kind="a_share_tushare_daily_migration_stock_basic",
        data_path=paths["stock_basic"],
        sidecar_path=paths["stock_basic"].with_suffix(".json"),
    )
    if calendar_checkpoint is None or stock_checkpoint is None:
        raise TushareDailyMigrationError(
            "Tushare source manifest calendar or stock_basic checkpoint is missing"
        )
    calendar = calendar_checkpoint[0]
    stock_basic = stock_checkpoint[0]
    calendar_record = manifest.get("calendar")
    stock_record = manifest.get("stock_basic")
    if (
        not isinstance(calendar_record, dict)
        or calendar_record.get("path") != str(paths["calendar"])
        or calendar_record.get("byte_sha256")
        != canonical_file_digest(paths["calendar"])
        or int(calendar_record.get("rows", -1)) != len(calendar)
        or not isinstance(stock_record, dict)
        or stock_record.get("path") != str(paths["stock_basic"])
        or stock_record.get("byte_sha256")
        != canonical_file_digest(paths["stock_basic"])
        or int(stock_record.get("rows", -1)) != len(stock_basic)
    ):
        raise TushareDailyMigrationError(
            "Tushare source manifest calendar or stock_basic binding changed"
        )
    try:
        through_date = dt.date.fromisoformat(str(manifest["through_date"]))
    except (KeyError, ValueError) as exc:
        raise TushareDailyMigrationError(
            "Tushare source manifest through date is invalid"
        ) from exc
    if manifest.get("history_start") != HISTORY_START.isoformat():
        raise TushareDailyMigrationError(
            "Tushare source manifest history start changed"
        )
    open_dates = [
        value.date()
        for value in calendar.loc[calendar["is_open"].eq(1), "cal_date"]
    ]
    if (
        not open_dates
        or open_dates[-1] != through_date
        or int(manifest.get("open_sessions", -1)) != len(open_dates)
    ):
        raise TushareDailyMigrationError(
            "Tushare source manifest open-session grid changed"
        )
    reused_dates = [
        value for value in open_dates if REFERENCE_START <= value <= REFERENCE_END
    ]
    requested_daily_dates = [
        value for value in open_dates if value < REFERENCE_START or value > REFERENCE_END
    ]
    if int(manifest.get("reference_daily_sessions_reused", -1)) != len(
        reused_dates
    ):
        raise TushareDailyMigrationError(
            "Tushare source manifest reference-session count changed"
        )
    if manifest.get("reference_daily_sessions_requested_this_invocation") != 0:
        raise TushareDailyMigrationError(
            "Tushare source manifest re-requested a reference-covered daily session"
        )
    _validate_session_manifest_records(
        records=manifest.get("daily_basic_session_records"),
        expected_dates=open_dates,
        base=paths["daily_basic_sessions"],
        kind="a_share_tushare_daily_basic_session",
    )
    _validate_session_manifest_records(
        records=manifest.get("new_daily_session_records"),
        expected_dates=requested_daily_dates,
        base=paths["daily_sessions"],
        kind="a_share_tushare_daily_session",
    )


def _load_source_manifest(
    *,
    staging_root: Path,
    reference_manifest: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    paths = storage_paths(staging_root)
    if not paths["source_manifest"].is_file():
        raise TushareDailyMigrationError(
            f"Tushare daily source manifest is missing: {paths['source_manifest']}"
        )
    manifest = json.loads(paths["source_manifest"].read_text(encoding="utf-8"))
    reference, reference_sha256 = validate_reference_snapshot(
        reference_manifest,
        deep=True,
    )
    if (
        manifest.get("kind")
        != "a_share_tushare_daily_provider_migration_source_snapshot"
        or manifest.get("status")
        != "complete_pending_canonical_build_and_acceptance"
        or manifest.get("protocol_sha256") != PROTOCOL_SHA256
        or manifest.get("accepted_reference_manifest_sha256") != reference_sha256
        or manifest.get("accepted_reference_manifest_path")
        != str(reference_manifest.expanduser().resolve())
        or manifest.get("credential_value_persisted") is not False
        or manifest.get("active_root_mutated") is not False
        or manifest.get("forward_return_fields_read") is not False
        or manifest.get("factor_values_read") is not False
    ):
        raise TushareDailyMigrationError(
            "Tushare daily migration source manifest is rejected"
        )
    refresh_binding = manifest.get("refresh_seed")
    if refresh_binding is not None:
        if (
            not isinstance(refresh_binding, dict)
            or refresh_binding.get("path") != str(paths["refresh_seed"])
            or not paths["refresh_seed"].is_file()
            or refresh_binding.get("sha256")
            != canonical_file_digest(paths["refresh_seed"])
        ):
            raise TushareDailyMigrationError(
                "Tushare daily migration refresh-seed binding changed"
            )
        try:
            manifest_through_date = dt.date.fromisoformat(
                str(manifest["through_date"])
            )
        except (KeyError, ValueError) as exc:
            raise TushareDailyMigrationError(
                "Tushare daily migration source cutoff is invalid"
            ) from exc
        refresh_seed = validate_refresh_seed(
            staging_root=staging_root,
            through_date=manifest_through_date,
            require_parent_active=False,
            deep=False,
        )
        if any(
            refresh_binding.get(key) != refresh_seed.get(key)
            for key in (
                "parent_root",
                "parent_through_date",
                "seeded_session_checkpoints",
            )
        ):
            raise TushareDailyMigrationError(
                "Tushare daily migration refresh-seed identity changed"
            )
    elif paths["refresh_seed"].exists() or paths["refresh_seed_intent"].exists():
        raise TushareDailyMigrationError(
            "Tushare daily migration source manifest omitted refresh-seed state"
        )
    _validate_source_manifest_bindings(manifest, paths)
    return manifest, reference


def _reference_year_frame(
    reference: dict[str, Any],
    year: int,
) -> pd.DataFrame:
    record = next(
        (item for item in _reference_file_records(reference) if int(item["year"]) == year),
        None,
    )
    if record is None:
        raise TushareDailyMigrationError(
            f"accepted Tushare daily reference lacks year {year}"
        )
    return concordance.load_and_verify_frame_record(record)


def _load_session_year(
    *,
    base: Path,
    year_dates: list[dt.date],
    kind: str,
) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for trade_date in year_dates:
        data_path, sidecar = _session_paths(base, trade_date)
        completed = _load_checkpoint(
            kind=kind,
            data_path=data_path,
            sidecar_path=sidecar,
            trade_date=trade_date,
        )
        if completed is None:
            raise TushareDailyMigrationError(
                f"required Tushare session checkpoint is missing: {data_path}"
            )
        frames.append(completed[0])
    if not frames:
        raise TushareDailyMigrationError(
            f"no Tushare session checkpoints exist for year {year_dates[0].year}"
        )
    return pd.concat(frames, ignore_index=True)


def _symbol_from_ts_code(series: pd.Series) -> pd.Series:
    return concordance.symbol_from_ts_code(series)


def canonicalize_merged_daily_year(
    daily: pd.DataFrame,
    daily_basic: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Normalize one provider year without chaining prices across year-end."""

    if daily.duplicated(["ts_code", "trade_date"]).any():
        raise TushareDailyMigrationError("Tushare daily year has duplicate keys")
    if daily_basic.duplicated(["ts_code", "trade_date"]).any():
        raise TushareDailyMigrationError("Tushare daily_basic year has duplicate keys")
    merged = daily.merge(
        daily_basic,
        on=["ts_code", "trade_date"],
        how="left",
        validate="one_to_one",
        indicator=True,
    )
    common_share = float(merged["_merge"].eq("both").mean()) if len(merged) else 0.0
    if common_share < 0.995:
        raise TushareDailyMigrationError(
            f"Tushare daily_basic common-key share {common_share:.6f} is below 0.995"
        )
    amount_cny = pd.to_numeric(merged["amount"], errors="coerce") * 1000.0
    volume_lots = pd.to_numeric(merged["vol"], errors="coerce")
    volume_shares = volume_lots * 100.0
    raw_vwap = amount_cny.div(volume_shares.where(volume_shares.gt(0.0)))
    symbols = _symbol_from_ts_code(merged["ts_code"])
    codes = merged["ts_code"].astype(str).str[:6]
    supported = codes.map(lambda value: pipeline.classify_board(value) is not None)
    frame = pd.DataFrame(
        {
            "date": pd.to_datetime(merged["trade_date"]).dt.normalize(),
            "symbol": symbols,
            "pre_close": pd.to_numeric(merged["pre_close"], errors="coerce"),
            "pct_chg": pd.to_numeric(merged["pct_chg"], errors="coerce"),
            "amount": amount_cny,
            "turnover": pd.to_numeric(merged["turnover_rate"], errors="coerce"),
            "raw_open": pd.to_numeric(merged["open"], errors="coerce"),
            "raw_high": pd.to_numeric(merged["high"], errors="coerce"),
            "raw_low": pd.to_numeric(merged["low"], errors="coerce"),
            "raw_close": pd.to_numeric(merged["close"], errors="coerce"),
            "raw_volume": volume_lots,
            "raw_vwap": raw_vwap,
            "daily_source": "tushare",
        }
    )
    frame = frame.loc[supported.to_numpy()].reset_index(drop=True)
    if frame["symbol"].isna().any() or frame.duplicated(["symbol", "date"]).any():
        raise TushareDailyMigrationError(
            "normalized Tushare daily year has invalid symbol-date keys"
        )
    return frame, {
        "daily_rows": int(len(daily)),
        "daily_basic_rows": int(len(daily_basic)),
        "common_rows": int(merged["_merge"].eq("both").sum()),
        "daily_basic_common_key_share": common_share,
        "missing_turnover_rows": int(frame["turnover"].isna().sum()),
        "unsupported_board_rows_excluded": int((~supported).sum()),
    }


def build_symbol_bars(source: pd.DataFrame, expected_symbol: str) -> pd.DataFrame:
    """Build one complete symbol's close-known point-in-time price chain."""

    work = source.sort_values("date", kind="stable").drop_duplicates(
        "date", keep="last"
    ).copy()
    if work.empty or set(work["symbol"].astype(str)) != {expected_symbol}:
        raise TushareDailyMigrationError(
            f"Tushare symbol partition identity changed for {expected_symbol}"
        )
    close = pd.to_numeric(work["raw_close"], errors="coerce")
    pre_close = pd.to_numeric(work["pre_close"], errors="coerce")
    pct_chg = pd.to_numeric(work["pct_chg"], errors="coerce")
    derived = close.div(pre_close.where(pre_close.gt(0.0))).sub(1.0).mul(100.0)
    pct_chg = pct_chg.fillna(derived)
    if pct_chg.isna().any():
        first_index = pct_chg.index[0]
        if pd.isna(pct_chg.loc[first_index]):
            pct_chg.loc[first_index] = 0.0
    if pct_chg.isna().any():
        raise TushareDailyMigrationError(
            f"Tushare pct_chg chain has an unresolved gap for {expected_symbol}"
        )
    work["pct_chg"] = pct_chg
    for adjusted, raw in (
        ("open", "raw_open"),
        ("high", "raw_high"),
        ("low", "raw_low"),
        ("close", "raw_close"),
        ("volume", "raw_volume"),
        ("vwap", "raw_vwap"),
    ):
        work[adjusted] = work[raw]
    work["change"] = close - pre_close
    work["price_basis"] = pipeline.POINT_IN_TIME_PRICE_BASIS
    result = pipeline.rebuild_point_in_time_prices(work)
    result = result.drop(columns=["pre_close"], errors="ignore")
    result["symbol"] = expected_symbol
    counts = pipeline.price_basis_quality_counts(result)
    failures = {
        key: value
        for key, value in counts.items()
        if value and key not in pipeline.NON_FAILURE_PRICE_BASIS_COUNTS
    }
    if failures:
        raise TushareDailyMigrationError(
            f"Tushare point-in-time symbol gate failed for {expected_symbol}: {failures}"
        )
    return result


def _write_symbol_partition_dataset(
    frame: pd.DataFrame,
    *,
    destination: Path,
    year: int,
) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(frame, preserve_index=False)
    partitioning = pads.partitioning(
        pa.schema([("symbol", pa.string())]),
        flavor="hive",
    )
    pads.write_dataset(
        table,
        base_dir=str(destination),
        format="parquet",
        partitioning=partitioning,
        basename_template=f"{year}-{{i}}.parquet",
        existing_data_behavior="overwrite_or_ignore",
        max_open_files=64,
    )


def _instruments_from_stock_basic(
    frame: pd.DataFrame,
    *,
    through_date: dt.date,
) -> tuple[list[pipeline.Instrument], dict[str, int]]:
    instruments: list[pipeline.Instrument] = []
    for row in frame.itertuples(index=False):
        code = str(row.ts_code)[:6]
        board = pipeline.classify_board(code)
        if board is None:
            continue
        listing_date = (
            pd.Timestamp(row.list_date).date().isoformat()
            if not pd.isna(row.list_date)
            else None
        )
        instruments.append(
            pipeline.Instrument(
                symbol=pipeline.qlib_symbol(code),
                code=code,
                name=str(row.name),
                board=board,
                listing_date=listing_date,
                market_cap=None,
                float_market_cap=None,
                is_st=pipeline.is_st_name(str(row.name)),
            )
        )
    if len(instruments) < 5000:
        raise TushareDailyMigrationError(
            f"Tushare stock_basic retained too few factor-universe names: {len(instruments)}"
        )
    current = frame[
        frame["list_status"].eq("L")
        & frame["list_date"].notna()
        & frame["list_date"].le(pd.Timestamp(through_date))
        & (
            frame["delist_date"].isna()
            | frame["delist_date"].gt(pd.Timestamp(through_date))
        )
    ].copy()
    current["board"] = current["ts_code"].astype(str).str[:6].map(
        pipeline.classify_board
    )
    current = current[current["board"].notna()]
    counts = {
        "current_buyable_main_chinext": int(
            current["board"].isin(["main", "chinext"]).sum()
        ),
        "current_factor_main_chinext_star": int(
            current["board"].isin(["main", "chinext", "star"]).sum()
        ),
        "all_historical_supported_names": len(instruments),
    }
    return sorted(instruments, key=lambda item: item.symbol), counts


def _validate_canonical_build_for_resume(
    *,
    paths: dict[str, Path],
    source_manifest: dict[str, Any],
) -> dict[str, Any]:
    if (
        not paths["build_manifest"].is_file()
        or not paths["raw_daily"].is_dir()
        or not paths["universe"].is_file()
    ):
        raise TushareDailyMigrationError(
            "incomplete unaccepted canonical build must be preserved for audit"
        )
    build = json.loads(paths["build_manifest"].read_text(encoding="utf-8"))
    audit = build.get("price_basis_audit")
    universe_counts = build.get("universe_counts")
    if (
        build.get("kind") != "a_share_tushare_daily_provider_canonical_build"
        or build.get("status")
        != "raw_passed_pending_optional_qlib_materialization"
        or build.get("protocol_sha256") != PROTOCOL_SHA256
        or build.get("source_manifest_path") != str(paths["source_manifest"])
        or build.get("source_manifest_sha256")
        != canonical_file_digest(paths["source_manifest"])
        or build.get("through_date") != source_manifest.get("through_date")
        or build.get("universe_path") != str(paths["universe"])
        or build.get("universe_sha256") != canonical_file_digest(paths["universe"])
        or build.get("active_root_mutated") is not False
        or build.get("forward_return_fields_read") is not False
        or build.get("factor_values_read") is not False
        or not isinstance(audit, dict)
        or audit.get("status") != "passed"
        or audit.get("daily_sources") != ["tushare"]
        or audit.get("failures")
        or not isinstance(universe_counts, dict)
        or int(universe_counts.get("current_buyable_main_chinext", -1)) < 4500
        or int(universe_counts.get("current_factor_main_chinext_star", -1)) < 5000
    ):
        raise TushareDailyMigrationError(
            "existing unaccepted Tushare canonical build is rejected"
        )
    sources, invalid_files = pipeline.inspect_existing_daily_sources(
        paths["raw_daily"]
    )
    raw_files = len(list(paths["raw_daily"].glob("*.parquet")))
    if (
        sources != {"tushare"}
        or invalid_files
        or raw_files != int(build.get("raw_files", -1))
        or raw_files < 5000
    ):
        raise TushareDailyMigrationError(
            "existing unaccepted Tushare raw provider changed"
        )
    return build


def _materialize_and_accept_canonical_build(
    *,
    root: Path,
    paths: dict[str, Path],
    source_manifest: dict[str, Any],
) -> Path:
    environment = os.environ.copy()
    environment["QLIB_A_SHARE_DATA_ROOT"] = str(root)
    completed = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "a_share_data_pipeline.py"),
            "materialize",
        ],
        cwd=REPO_ROOT,
        env=environment,
        check=False,
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0:
        raise TushareDailyMigrationError(
            "Tushare staging Qlib materialization failed: "
            + " ".join((completed.stderr or completed.stdout).split())[-1000:]
        )
    price_manifest = paths["qlib"] / "price_basis.json"
    if not price_manifest.is_file():
        raise TushareDailyMigrationError(
            "Tushare staging price-basis manifest is missing after materialization"
        )
    price_basis = json.loads(price_manifest.read_text(encoding="utf-8"))
    if (
        price_basis.get("status") != "passed"
        or price_basis.get("daily_sources") != ["tushare"]
        or price_basis.get("failures")
    ):
        raise TushareDailyMigrationError(
            "Tushare staging Qlib price-basis acceptance failed"
        )
    calendar_path = paths["qlib"] / "calendars" / "day.txt"
    calendar_values = (
        calendar_path.read_text(encoding="utf-8").splitlines()
        if calendar_path.is_file()
        else []
    )
    if (
        not calendar_values
        or calendar_values[-1] != source_manifest.get("through_date")
    ):
        raise TushareDailyMigrationError(
            "Tushare staging Qlib calendar cutoff changed after materialization"
        )
    acceptance = {
        "version": 1,
        "kind": "a_share_tushare_daily_provider_migration_acceptance",
        "status": "accepted_staging_pending_explicit_crash_safe_activation",
        "protocol_path": str(PROTOCOL_PATH),
        "protocol_sha256": PROTOCOL_SHA256,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "staging_root": str(root),
        "source_manifest_path": str(paths["source_manifest"]),
        "source_manifest_sha256": canonical_file_digest(paths["source_manifest"]),
        "build_manifest_path": str(paths["build_manifest"]),
        "build_manifest_sha256": canonical_file_digest(paths["build_manifest"]),
        "price_basis_manifest_path": str(price_manifest),
        "price_basis_manifest_sha256": canonical_file_digest(price_manifest),
        "through_date": source_manifest["through_date"],
        "daily_source": "tushare",
        "price_basis": pipeline.POINT_IN_TIME_PRICE_BASIS,
        "raw_files": len(list(paths["raw_daily"].glob("*.parquet"))),
        "qlib_calendar_end": calendar_values[-1],
        "active_root_mutated": False,
        "activation_performed": False,
        "forward_return_fields_read": False,
        "factor_values_read": False,
        "aggregation_scoring_selection_sizing_or_orders_performed": False,
    }
    pipeline.write_json(paths["acceptance_manifest"], acceptance)
    return paths["acceptance_manifest"]


def build_staging(
    *,
    staging_root: Path,
    reference_manifest: Path = DEFAULT_REFERENCE_MANIFEST,
    materialize: bool = True,
) -> Path:
    """Build and audit a complete Tushare raw/Qlib provider inside staging."""

    root = validate_staging_boundary(staging_root)
    paths = storage_paths(root)
    source_manifest, reference = _load_source_manifest(
        staging_root=root,
        reference_manifest=reference_manifest,
    )
    calendar_checkpoint = _load_checkpoint(
        kind="a_share_tushare_daily_migration_trade_calendar",
        data_path=paths["calendar"],
        sidecar_path=paths["calendar"].with_suffix(".json"),
    )
    stock_checkpoint = _load_checkpoint(
        kind="a_share_tushare_daily_migration_stock_basic",
        data_path=paths["stock_basic"],
        sidecar_path=paths["stock_basic"].with_suffix(".json"),
    )
    if calendar_checkpoint is None or stock_checkpoint is None:
        raise TushareDailyMigrationError(
            "Tushare migration calendar or stock_basic checkpoint is missing"
        )
    calendar = calendar_checkpoint[0]
    stock_basic = stock_checkpoint[0]
    open_dates = [
        value.date()
        for value in calendar.loc[calendar["is_open"].eq(1), "cal_date"]
    ]
    if paths["acceptance_manifest"].is_file():
        validate_staging_acceptance(root)
        return paths["acceptance_manifest"]
    canonical_artifacts_exist = any(
        path.exists()
        for path in (
            paths["raw_daily"],
            paths["build_manifest"],
            paths["universe"],
            paths["qlib"],
        )
    )
    if canonical_artifacts_exist:
        _validate_canonical_build_for_resume(
            paths=paths,
            source_manifest=source_manifest,
        )
        if not materialize:
            return paths["build_manifest"]
        return _materialize_and_accept_canonical_build(
            root=root,
            paths=paths,
            source_manifest=source_manifest,
        )
    build_partial = paths["source"] / ".canonical_build.partial"
    partitioned = build_partial / "by_symbol"
    year_audits: list[dict[str, Any]] = []
    with concordance.ProcessLock(paths["lock"]):
        if build_partial.exists():
            shutil.rmtree(build_partial)
        build_partial.mkdir(parents=True, exist_ok=False)
        try:
            for year in range(HISTORY_START.year, max(open_dates).year + 1):
                year_dates = [value for value in open_dates if value.year == year]
                if not year_dates:
                    continue
                if 2019 <= year <= 2025:
                    daily = _reference_year_frame(reference, year)
                else:
                    daily = _load_session_year(
                        base=paths["daily_sessions"],
                        year_dates=year_dates,
                        kind="a_share_tushare_daily_session",
                    )
                daily_basic = _load_session_year(
                    base=paths["daily_basic_sessions"],
                    year_dates=year_dates,
                    kind="a_share_tushare_daily_basic_session",
                )
                expected_year_dates = set(year_dates)
                daily_dates = set(
                    pd.to_datetime(daily["trade_date"], errors="coerce").dt.date
                )
                daily_basic_dates = set(
                    pd.to_datetime(
                        daily_basic["trade_date"],
                        errors="coerce",
                    ).dt.date
                )
                if (
                    daily_dates != expected_year_dates
                    or daily_basic_dates != expected_year_dates
                ):
                    raise TushareDailyMigrationError(
                        f"Tushare source session grid differs in year {year}"
                    )
                normalized, audit = canonicalize_merged_daily_year(
                    daily,
                    daily_basic,
                )
                _write_symbol_partition_dataset(
                    normalized,
                    destination=partitioned,
                    year=year,
                )
                year_audits.append({"year": year, **audit})
                print(
                    f"normalized year={year} rows={len(normalized):,} "
                    f"daily_basic_common={audit['daily_basic_common_key_share']:.6f}",
                    flush=True,
                )

            raw_partial = build_partial / "daily"
            raw_partial.mkdir(parents=True, exist_ok=False)
            symbol_dirs = sorted(partitioned.glob("symbol=*"))
            if len(symbol_dirs) < 5000:
                raise TushareDailyMigrationError(
                    f"Tushare canonical partition count is too small: {len(symbol_dirs)}"
                )
            for index, symbol_dir in enumerate(symbol_dirs, start=1):
                symbol = symbol_dir.name.split("=", 1)[1].upper()
                frame = pads.dataset(str(symbol_dir), format="parquet").to_table().to_pandas()
                frame.insert(1, "symbol", symbol)
                bars = build_symbol_bars(frame, symbol)
                pipeline._atomic_write_parquet(  # pylint: disable=protected-access
                    bars,
                    raw_partial / f"{symbol.lower()}.parquet",
                )
                if index % 250 == 0 or index == len(symbol_dirs):
                    print(
                        f"built symbols={index:,}/{len(symbol_dirs):,}",
                        flush=True,
                    )

            audit = pipeline.audit_point_in_time_source(raw_dir=raw_partial)
            if audit["status"] != "passed" or audit["daily_sources"] != ["tushare"]:
                raise TushareDailyMigrationError(
                    f"Tushare staging price-basis gate failed: {audit['failures']}"
                )
            instruments, current_counts = _instruments_from_stock_basic(
                stock_basic,
                through_date=dt.date.fromisoformat(source_manifest["through_date"]),
            )
            if (
                current_counts["current_buyable_main_chinext"] < 4500
                or current_counts["current_factor_main_chinext_star"] < 5000
            ):
                raise TushareDailyMigrationError(
                    "Tushare staging universe acceptance counts are too small"
                )
            if paths["raw_daily"].exists():
                raise TushareDailyMigrationError(
                    "canonical staging destination already exists; refusing overwrite"
                )
            paths["raw_daily"].parent.mkdir(parents=True, exist_ok=True)
            raw_partial.replace(paths["raw_daily"])
            pipeline.write_json(
                paths["universe"],
                [asdict(item) for item in instruments],
            )
            build_manifest = {
                "version": 1,
                "kind": "a_share_tushare_daily_provider_canonical_build",
                "status": "raw_passed_pending_optional_qlib_materialization",
                "protocol_path": str(PROTOCOL_PATH),
                "protocol_sha256": PROTOCOL_SHA256,
                "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "source_manifest_path": str(paths["source_manifest"]),
                "source_manifest_sha256": canonical_file_digest(
                    paths["source_manifest"]
                ),
                "through_date": source_manifest["through_date"],
                "year_audits": year_audits,
                "price_basis_audit": audit,
                "universe_counts": current_counts,
                "raw_files": len(list(paths["raw_daily"].glob("*.parquet"))),
                "universe_path": str(paths["universe"]),
                "universe_sha256": canonical_file_digest(paths["universe"]),
                "active_root_mutated": False,
                "forward_return_fields_read": False,
                "factor_values_read": False,
            }
            pipeline.write_json(paths["build_manifest"], build_manifest)
        finally:
            shutil.rmtree(build_partial, ignore_errors=True)

    if not materialize:
        return paths["build_manifest"]
    return _materialize_and_accept_canonical_build(
        root=root,
        paths=paths,
        source_manifest=source_manifest,
    )


def validate_staging_acceptance(staging_root: Path) -> dict[str, Any]:
    """Validate every immutable daily-provider binding before activation."""

    root = validate_staging_boundary(staging_root, allow_active=True)
    paths = storage_paths(root)
    if not paths["acceptance_manifest"].is_file():
        raise TushareDailyMigrationError(
            f"Tushare staging acceptance is missing: {paths['acceptance_manifest']}"
        )
    accepted = json.loads(
        paths["acceptance_manifest"].read_text(encoding="utf-8")
    )
    if (
        accepted.get("kind")
        != "a_share_tushare_daily_provider_migration_acceptance"
        or accepted.get("status")
        != "accepted_staging_pending_explicit_crash_safe_activation"
        or accepted.get("protocol_sha256") != PROTOCOL_SHA256
        or accepted.get("staging_root") != str(root)
        or accepted.get("daily_source") != "tushare"
        or accepted.get("price_basis") != pipeline.POINT_IN_TIME_PRICE_BASIS
        or accepted.get("active_root_mutated") is not False
        or accepted.get("activation_performed") is not False
        or accepted.get("forward_return_fields_read") is not False
    ):
        raise TushareDailyMigrationError(
            "Tushare staging acceptance identity is rejected"
        )
    for path_key, sha_key in (
        ("source_manifest_path", "source_manifest_sha256"),
        ("build_manifest_path", "build_manifest_sha256"),
        ("price_basis_manifest_path", "price_basis_manifest_sha256"),
    ):
        bound_path = Path(str(accepted.get(path_key, ""))).expanduser().resolve()
        if (
            not bound_path.is_file()
            or canonical_file_digest(bound_path) != accepted.get(sha_key)
        ):
            raise TushareDailyMigrationError(
                f"Tushare staging acceptance binding changed: {path_key}"
            )
    price_basis = json.loads(
        Path(str(accepted["price_basis_manifest_path"])).read_text(encoding="utf-8")
    )
    if (
        price_basis.get("status") != "passed"
        or price_basis.get("price_basis") != pipeline.POINT_IN_TIME_PRICE_BASIS
        or price_basis.get("daily_sources") != ["tushare"]
        or price_basis.get("failures")
    ):
        raise TushareDailyMigrationError(
            "Tushare staging price-basis manifest is rejected"
        )
    calendar_path = paths["qlib"] / "calendars" / "day.txt"
    if not calendar_path.is_file():
        raise TushareDailyMigrationError(
            "Tushare staging Qlib calendar is missing"
        )
    calendar_values = [
        value
        for value in calendar_path.read_text(encoding="utf-8").splitlines()
        if value
    ]
    if not calendar_values or calendar_values[-1] != accepted.get("through_date"):
        raise TushareDailyMigrationError(
            "Tushare staging Qlib calendar does not end at the accepted cutoff"
        )
    sources, invalid_files = pipeline.inspect_existing_daily_sources(
        paths["raw_daily"]
    )
    if sources != {"tushare"} or invalid_files:
        raise TushareDailyMigrationError(
            "Tushare staging raw root is not one valid Tushare source"
        )
    if len(list(paths["raw_daily"].glob("*.parquet"))) != int(
        accepted.get("raw_files", -1)
    ):
        raise TushareDailyMigrationError(
            "Tushare staging raw-file count changed"
        )
    return accepted


AUXILIARY_SEED_ROOTS = (
    Path("derived"),
    Path("experiments"),
    Path("exports"),
    Path("handoffs"),
    Path("raw/a_share/events"),
    Path("raw/a_share/fundamentals"),
    Path("raw/a_share/rich"),
    Path("metadata/rich_data"),
)


def _excluded_auxiliary_relative(relative: Path) -> bool:
    return (
        relative.parts[:4] == ("raw", "a_share", "rich", "tushare")
        and "daily_provider_migration_v1" in relative.parts
    )


def _auxiliary_seed_plan(
    previous_root: Path,
    staging_root: Path,
) -> list[tuple[Path, Path, Path, str]]:
    """Return verified non-daily files that may safely accompany a root switch."""

    plan: list[tuple[Path, Path, Path, str]] = []
    for relative_root in AUXILIARY_SEED_ROOTS:
        source_root = previous_root / relative_root
        if not source_root.exists():
            continue
        for source in sorted(path for path in source_root.rglob("*") if path.is_file()):
            relative = source.relative_to(previous_root)
            if _excluded_auxiliary_relative(relative):
                continue
            destination = staging_root / relative
            source_sha256 = canonical_file_digest(source)
            if destination.exists():
                if (
                    not destination.is_file()
                    or canonical_file_digest(destination) != source_sha256
                ):
                    raise TushareDailyMigrationError(
                        "non-daily activation seed conflicts with staging: "
                        f"{relative}"
                    )
                continue
            plan.append((relative, source, destination, source_sha256))
    return plan


def seed_auxiliary_data(
    *,
    previous_root: Path,
    staging_root: Path,
) -> dict[str, Any]:
    """Copy and verify only the frozen non-daily allowlist before pointer switch."""

    plan = _auxiliary_seed_plan(previous_root, staging_root)
    digest = hashlib.sha256()
    copied_bytes = 0
    copied_files = 0
    for relative, source, destination, source_sha256 in plan:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".partial",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
        try:
            shutil.copy2(source, temporary)
            if canonical_file_digest(temporary) != source_sha256:
                raise TushareDailyMigrationError(
                    f"non-daily activation seed copy changed: {relative}"
                )
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)
        copied_files += 1
        copied_bytes += source.stat().st_size
        digest.update(f"{relative.as_posix()}|{source_sha256}\n".encode("utf-8"))
    # Include already-identical allowlisted files in the final reproducible
    # aggregate so an idempotent rerun reports the same complete state.
    all_records: list[tuple[str, str]] = []
    for relative_root in AUXILIARY_SEED_ROOTS:
        destination_root = staging_root / relative_root
        if not destination_root.exists():
            continue
        for destination in sorted(
            path for path in destination_root.rglob("*") if path.is_file()
        ):
            relative_path = destination.relative_to(staging_root)
            if _excluded_auxiliary_relative(relative_path):
                continue
            all_records.append(
                (relative_path.as_posix(), canonical_file_digest(destination))
            )
    complete_digest = hashlib.sha256()
    for relative, value in all_records:
        complete_digest.update(f"{relative}|{value}\n".encode("utf-8"))
    return {
        "allowlisted_roots": [value.as_posix() for value in AUXILIARY_SEED_ROOTS],
        "copied_files_this_invocation": copied_files,
        "copied_bytes_this_invocation": copied_bytes,
        "copied_files_this_invocation_sha256": digest.hexdigest(),
        "complete_seed_files": len(all_records),
        "complete_seed_sha256": complete_digest.hexdigest(),
        "old_daily_root_copied": False,
        "old_qlib_root_copied": False,
        "old_universe_or_price_basis_manifest_copied": False,
    }


def _pointer_path() -> Path:
    return REPO_ROOT / DATA_ROOT_POINTER_NAME


def _read_data_root_pointer_text() -> str | None:
    pointer = _pointer_path()
    return pointer.read_text(encoding="utf-8") if pointer.is_file() else None


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _atomic_write_data_root_pointer_text(text: str) -> str:
    if len(text.splitlines()) != 1 or not text.strip():
        raise TushareDailyMigrationError(
            "data-root pointer text must contain exactly one nonempty line"
        )
    pointer = _pointer_path()
    with tempfile.NamedTemporaryFile(
        dir=pointer.parent,
        prefix=f".{pointer.name}.",
        suffix=".partial",
        mode="w",
        encoding="utf-8",
        delete=False,
    ) as handle:
        temporary = Path(handle.name)
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        temporary.replace(pointer)
        _fsync_directory(pointer.parent)
    finally:
        temporary.unlink(missing_ok=True)
    return canonical_file_digest(pointer)


def _atomic_write_data_root_pointer(target: Path) -> str:
    target = target.expanduser().resolve()
    return _atomic_write_data_root_pointer_text(f"{target}\n")


def _restore_data_root_pointer(previous_text: str | None) -> str | None:
    pointer = _pointer_path()
    if previous_text is None:
        pointer.unlink(missing_ok=True)
        _fsync_directory(pointer.parent)
        return None
    return _atomic_write_data_root_pointer_text(previous_text)


def activation_preflight(
    *,
    staging_root: Path,
) -> dict[str, Any]:
    """Validate activation locally without copying or changing the pointer."""

    root = validate_staging_boundary(staging_root, allow_active=True)
    failures: list[str] = []
    acceptance_error: str | None = None
    try:
        accepted = validate_staging_acceptance(root)
    except BaseException as exc:
        accepted = {}
        failures.append("staging_acceptance_not_valid")
        acceptance_error = safe_exception_text(exc)
    environment_override = os.environ.get(DATA_ROOT_ENV, "").strip()
    if environment_override:
        failures.append("QLIB_A_SHARE_DATA_ROOT_environment_override_present")
    try:
        current_root = resolve_data_root(REPO_ROOT, {})
    except BaseException as exc:
        current_root = REPO_ROOT / "data"
        failures.append("current_data_root_pointer_invalid")
        if acceptance_error is None:
            acceptance_error = safe_exception_text(exc)
    current_sources, current_invalid_files = pipeline.inspect_existing_daily_sources(
        current_root / "raw" / "a_share" / "daily"
    )
    if current_root != root and (
        len(current_sources) != 1 or current_invalid_files
    ):
        failures.append("current_data_root_not_one_valid_daily_source")
    activation_record = storage_paths(root)["activation_record"]
    already_active = current_root == root
    if already_active and not activation_record.is_file():
        failures.append("pointer_targets_staging_without_completed_activation_record")
    failures = list(dict.fromkeys(failures))
    ready = not failures
    return {
        "kind": "a_share_tushare_daily_provider_activation_preflight",
        "status": (
            "already_active_idempotent"
            if ready and already_active
            else (
                "ready_for_explicit_atomic_pointer_activation"
                if ready
                else "not_ready_no_copy_or_pointer_write"
            )
        ),
        "ready": ready,
        "recommended_cli_exit_code": 0 if ready else 2,
        "protocol_sha256": PROTOCOL_SHA256,
        "staging_root": str(root),
        "accepted_through_date": accepted.get("through_date"),
        "current_data_root": str(current_root),
        "current_daily_sources": sorted(current_sources),
        "current_invalid_daily_files": current_invalid_files[:20],
        "pointer_path": str(_pointer_path()),
        "environment_override_present": bool(environment_override),
        "already_active": already_active,
        "acceptance_error": acceptance_error,
        "failures": failures,
        "filesystem_copy_performed": False,
        "pointer_write_performed": False,
        "active_daily_or_qlib_file_mutated": False,
        "provider_request_issued": False,
        "forward_return_fields_read": False,
    }


def _fresh_status_with_pointer() -> dict[str, Any]:
    environment = os.environ.copy()
    environment.pop(DATA_ROOT_ENV, None)
    completed = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "a_share_data_pipeline.py"),
            "status",
        ],
        cwd=REPO_ROOT,
        env=environment,
        check=False,
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0:
        raise TushareDailyMigrationError(
            "fresh post-activation status failed: "
            + " ".join((completed.stderr or completed.stdout).split())[-1000:]
        )
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise TushareDailyMigrationError(
            "fresh post-activation status did not return JSON"
        ) from exc


def activate_staging(
    *,
    staging_root: Path,
    confirm_activation: bool,
) -> Path:
    """Seed non-daily state and atomically point the repository at staging."""

    if not confirm_activation:
        raise TushareDailyMigrationError(
            "activation requires explicit --confirm-activation"
        )
    root = validate_staging_boundary(staging_root, allow_active=True)
    paths = storage_paths(root)
    accepted = validate_staging_acceptance(root)
    with concordance.ProcessLock(REPO_ROOT / ".qlib_a_share_data_root.lock"):
        if os.environ.get(DATA_ROOT_ENV, "").strip():
            raise TushareDailyMigrationError(
                "unset QLIB_A_SHARE_DATA_ROOT before atomic pointer activation"
            )
        current_root = resolve_data_root(REPO_ROOT, {})
        if current_root == root and paths["activation_record"].is_file():
            record = json.loads(
                paths["activation_record"].read_text(encoding="utf-8")
            )
            if (
                record.get("kind")
                != "a_share_tushare_daily_provider_activation"
                or record.get("status") != "active_via_atomic_repository_pointer"
                or record.get("protocol_sha256") != PROTOCOL_SHA256
                or record.get("staging_root") != str(root)
            ):
                raise TushareDailyMigrationError(
                    "existing Tushare activation record is rejected"
                )
            return paths["activation_record"]

        intent: dict[str, Any] | None = None
        if paths["activation_intent"].is_file():
            intent = json.loads(
                paths["activation_intent"].read_text(encoding="utf-8")
            )
            if (
                intent.get("kind")
                != "a_share_tushare_daily_provider_activation_intent"
                or intent.get("status") != "prepared_before_atomic_pointer"
                or intent.get("protocol_sha256") != PROTOCOL_SHA256
                or intent.get("staging_root") != str(root)
                or intent.get("acceptance_manifest_sha256")
                != canonical_file_digest(paths["acceptance_manifest"])
            ):
                raise TushareDailyMigrationError(
                    "existing Tushare activation intent is rejected"
                )
            previous_root = Path(str(intent["previous_data_root"])).resolve()
            if current_root not in {previous_root, root}:
                raise TushareDailyMigrationError(
                    "current data root differs from activation intent"
                )
        else:
            previous_root = current_root
            if previous_root == root:
                raise TushareDailyMigrationError(
                    "pointer targets staging without an activation intent or record"
                )
            current_sources, invalid_files = pipeline.inspect_existing_daily_sources(
                previous_root / "raw" / "a_share" / "daily"
            )
            if len(current_sources) != 1 or invalid_files:
                raise TushareDailyMigrationError(
                    "previous active root is not one valid daily provider"
                )
            seed = seed_auxiliary_data(
                previous_root=previous_root,
                staging_root=root,
            )
            previous_pointer_text = _read_data_root_pointer_text()
            intent = {
                "version": 1,
                "kind": "a_share_tushare_daily_provider_activation_intent",
                "status": "prepared_before_atomic_pointer",
                "protocol_sha256": PROTOCOL_SHA256,
                "prepared_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "staging_root": str(root),
                "previous_data_root": str(previous_root),
                "previous_daily_sources": sorted(current_sources),
                "previous_pointer_existed": previous_pointer_text is not None,
                "previous_pointer_text": previous_pointer_text,
                "acceptance_manifest_path": str(paths["acceptance_manifest"]),
                "acceptance_manifest_sha256": canonical_file_digest(
                    paths["acceptance_manifest"]
                ),
                "auxiliary_seed": seed,
                "old_daily_root_mutated_or_copied": False,
                "old_qlib_root_mutated_or_copied": False,
                "pointer_write_performed": False,
                "provider_request_issued": False,
                "forward_return_fields_read": False,
            }
            atomic_write_json(intent, paths["activation_intent"])

        previous_pointer_text = intent.get("previous_pointer_text")
        if previous_pointer_text is not None and not isinstance(
            previous_pointer_text, str
        ):
            raise TushareDailyMigrationError(
                "activation intent contains an invalid previous pointer"
            )
        if bool(intent.get("previous_pointer_existed")) != (
            previous_pointer_text is not None
        ):
            raise TushareDailyMigrationError(
                "activation intent previous-pointer identity changed"
            )
        pointer_switched = current_root == root
        try:
            if not pointer_switched:
                pointer_sha256 = _atomic_write_data_root_pointer(root)
                pointer_switched = True
            else:
                pointer_sha256 = canonical_file_digest(_pointer_path())
            fresh = _fresh_status_with_pointer()
            if (
                Path(str(fresh.get("data_root", ""))).resolve() != root
                or (fresh.get("price_basis") or {}).get("status") != "passed"
                or (fresh.get("price_basis") or {}).get("daily_sources")
                != ["tushare"]
                or fresh.get("qlib_calendar_end") != accepted["through_date"]
            ):
                raise TushareDailyMigrationError(
                    "fresh post-activation status did not resolve the accepted "
                    "Tushare root"
                )
            record = {
                "version": 1,
                "kind": "a_share_tushare_daily_provider_activation",
                "status": "active_via_atomic_repository_pointer",
                "protocol_sha256": PROTOCOL_SHA256,
                "activated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "staging_root": str(root),
                "previous_data_root": str(previous_root),
                "pointer_path": str(_pointer_path()),
                "pointer_sha256": pointer_sha256,
                "acceptance_manifest_path": str(paths["acceptance_manifest"]),
                "acceptance_manifest_sha256": canonical_file_digest(
                    paths["acceptance_manifest"]
                ),
                "accepted_through_date": accepted["through_date"],
                "daily_source": "tushare",
                "fresh_status": {
                    "data_root": fresh["data_root"],
                    "qlib_calendar_end": fresh["qlib_calendar_end"],
                    "raw_parquet_files": fresh["raw_parquet_files"],
                    "daily_sources": fresh["price_basis"]["daily_sources"],
                    "price_basis": fresh["price_basis"]["price_basis"],
                    "price_basis_status": fresh["price_basis"]["status"],
                },
                "previous_provider_preserved_for_rollback": True,
                "old_daily_or_qlib_file_mutated": False,
                "provider_request_issued": False,
                "forward_return_fields_read": False,
                "candidate49_post_activation_preflight_still_required": True,
            }
            atomic_write_json(record, paths["activation_record"])
            return paths["activation_record"]
        except BaseException as exc:
            rollback_sha256: str | None = None
            if pointer_switched:
                rollback_sha256 = _restore_data_root_pointer(
                    previous_pointer_text
                )
            failure = {
                "version": 1,
                "kind": "a_share_tushare_daily_provider_activation_failure",
                "status": "failed_and_previous_pointer_restored",
                "protocol_sha256": PROTOCOL_SHA256,
                "failed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "staging_root": str(root),
                "previous_data_root": str(previous_root),
                "error": safe_exception_text(exc),
                "rollback_pointer_sha256": rollback_sha256,
                "previous_pointer_existed": previous_pointer_text is not None,
                "previous_pointer_restored_exactly": True,
                "old_daily_or_qlib_file_mutated": False,
                "provider_request_issued": False,
                "forward_return_fields_read": False,
            }
            atomic_write_json(failure, paths["activation_failure"])
            raise


def status(
    *,
    staging_root: Path,
    reference_manifest: Path = DEFAULT_REFERENCE_MANIFEST,
) -> dict[str, Any]:
    root = validate_staging_boundary(staging_root, allow_active=True)
    paths = storage_paths(root)
    reference_valid = False
    reference_error: str | None = None
    reference_summary: dict[str, Any] | None = None
    try:
        reference, reference_sha256 = validate_reference_snapshot(
            reference_manifest
        )
        reference_valid = True
        files = _reference_file_records(reference)
        reference_summary = {
            "path": str(reference_manifest.expanduser().resolve()),
            "sha256": reference_sha256,
            "provider": reference["provider"],
            "requested_start": reference["requested_start"],
            "requested_end": reference["requested_end"],
            "rows": int(reference["rows"]),
            "annual_partitions": len(files),
            "sessions": sum(int(item["sessions"]) for item in files),
            "valid": True,
        }
    except BaseException as exc:
        reference_sha256 = None
        reference_error = safe_exception_text(exc)

    def load_optional(path: Path) -> dict[str, Any] | None:
        return (
            json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None
        )

    source = load_optional(paths["source_manifest"])
    refresh_seed_intent = load_optional(paths["refresh_seed_intent"])
    refresh_seed = load_optional(paths["refresh_seed"])
    build = load_optional(paths["build_manifest"])
    acceptance = load_optional(paths["acceptance_manifest"])
    failure = load_optional(paths["latest_failure"])
    activation = load_optional(paths["activation_record"])
    try:
        pointer_root = resolve_data_root(REPO_ROOT, {})
    except BaseException:
        pointer_root = None
    activation_performed = bool(
        activation
        and activation.get("status") == "active_via_atomic_repository_pointer"
        and pointer_root == root
    )
    return {
        "kind": "a_share_tushare_daily_provider_migration_status",
        "staging_root": str(root),
        "active_data_root": str(resolve_data_root(REPO_ROOT)),
        "reference_manifest_valid": reference_valid,
        "reference_manifest_sha256": reference_sha256,
        "reference_snapshot": reference_summary,
        "reference_error": reference_error,
        "token_configured": bool(os.environ.get("TUSHARE_TOKEN", "")),
        "refresh_seed_intent": refresh_seed_intent,
        "refresh_seed": refresh_seed,
        "source_snapshot": source,
        "canonical_build": build,
        "acceptance": acceptance,
        "activation": activation,
        "latest_failure": failure,
        "raw_parquet_files": len(list(paths["raw_daily"].glob("*.parquet"))),
        "qlib_price_basis": load_optional(paths["qlib"] / "price_basis.json"),
        "activation_performed": activation_performed,
        "provider_request_issued": False,
        "forward_return_fields_read": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    preflight_parser = subparsers.add_parser(
        "preflight",
        help="validate local migration prerequisites without writes or provider calls",
    )
    preflight_parser.add_argument("--staging-root", type=Path, required=True)
    preflight_parser.add_argument(
        "--through-date",
        type=dt.date.fromisoformat,
        default=latest_completed_session_date(),
    )
    preflight_parser.add_argument(
        "--reference-manifest",
        type=Path,
        default=DEFAULT_REFERENCE_MANIFEST,
    )
    sync_parser = subparsers.add_parser(
        "sync-source",
        help="collect immutable missing Tushare daily and daily_basic sessions",
    )
    sync_parser.add_argument("--staging-root", type=Path, required=True)
    sync_parser.add_argument(
        "--through-date",
        type=dt.date.fromisoformat,
        default=latest_completed_session_date(),
    )
    sync_parser.add_argument(
        "--reference-manifest",
        type=Path,
        default=DEFAULT_REFERENCE_MANIFEST,
    )
    sync_parser.add_argument(
        "--allow-network",
        action="store_true",
        help="required acknowledgement for provider requests",
    )
    seed_parser = subparsers.add_parser(
        "seed-refresh",
        help=(
            "copy verified source checkpoints from the accepted active Tushare "
            "root into a new staging version without provider calls"
        ),
    )
    seed_parser.add_argument("--parent-root", type=Path, required=True)
    seed_parser.add_argument("--staging-root", type=Path, required=True)
    seed_parser.add_argument(
        "--through-date",
        type=dt.date.fromisoformat,
        default=latest_completed_session_date(),
    )
    seed_parser.add_argument(
        "--reference-manifest",
        type=Path,
        default=DEFAULT_REFERENCE_MANIFEST,
    )
    build = subparsers.add_parser(
        "build",
        help="canonicalize, audit, and materialize the completed source snapshot",
    )
    build.add_argument("--staging-root", type=Path, required=True)
    build.add_argument(
        "--reference-manifest",
        type=Path,
        default=DEFAULT_REFERENCE_MANIFEST,
    )
    build.add_argument("--skip-materialize", action="store_true")
    status_parser = subparsers.add_parser(
        "status",
        help="inspect local migration state without writes or provider calls",
    )
    status_parser.add_argument("--staging-root", type=Path, required=True)
    status_parser.add_argument(
        "--reference-manifest",
        type=Path,
        default=DEFAULT_REFERENCE_MANIFEST,
    )
    activation_preflight_parser = subparsers.add_parser(
        "activation-preflight",
        help="validate an accepted staging root without copying or pointer writes",
    )
    activation_preflight_parser.add_argument(
        "--staging-root",
        type=Path,
        required=True,
    )
    activate_parser = subparsers.add_parser(
        "activate",
        help="seed non-daily state and atomically activate an accepted staging root",
    )
    activate_parser.add_argument("--staging-root", type=Path, required=True)
    activate_parser.add_argument(
        "--confirm-activation",
        action="store_true",
        help="required acknowledgement for the local data-root pointer switch",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "preflight":
        result = preflight(
            staging_root=args.staging_root,
            through_date=args.through_date,
            reference_manifest=args.reference_manifest,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return int(result["recommended_cli_exit_code"])
    if args.command == "sync-source":
        if not args.allow_network:
            raise TushareDailyMigrationError(
                "sync-source requires explicit --allow-network"
            )
        result_path = sync_source(
            staging_root=args.staging_root,
            through_date=args.through_date,
            reference_manifest=args.reference_manifest,
        )
        print(
            json.dumps(
                {
                    "status": "source_snapshot_complete",
                    "manifest_path": str(result_path),
                    "manifest_sha256": canonical_file_digest(result_path),
                    "active_root_mutated": False,
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if args.command == "seed-refresh":
        result_path = seed_refresh_source(
            parent_root=args.parent_root,
            staging_root=args.staging_root,
            through_date=args.through_date,
            reference_manifest=args.reference_manifest,
        )
        print(
            json.dumps(
                {
                    "status": (
                        "source_checkpoints_seeded_pending_incremental_sync"
                    ),
                    "manifest_path": str(result_path),
                    "manifest_sha256": canonical_file_digest(result_path),
                    "provider_request_issued": False,
                    "hardlinks_used": False,
                    "active_root_mutated": False,
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if args.command == "build":
        result_path = build_staging(
            staging_root=args.staging_root,
            reference_manifest=args.reference_manifest,
            materialize=not args.skip_materialize,
        )
        result_record = json.loads(result_path.read_text(encoding="utf-8"))
        print(
            json.dumps(
                {
                    "status": result_record["status"],
                    "manifest_path": str(result_path),
                    "manifest_sha256": canonical_file_digest(result_path),
                    "active_root_mutated": False,
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if args.command == "activation-preflight":
        result = activation_preflight(staging_root=args.staging_root)
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return int(result["recommended_cli_exit_code"])
    if args.command == "activate":
        result_path = activate_staging(
            staging_root=args.staging_root,
            confirm_activation=args.confirm_activation,
        )
        print(
            json.dumps(
                {
                    "status": "active_via_atomic_repository_pointer",
                    "manifest_path": str(result_path),
                    "manifest_sha256": canonical_file_digest(result_path),
                    "active_data_root": str(resolve_data_root(REPO_ROOT, {})),
                    "old_daily_or_qlib_file_mutated": False,
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    result = status(
        staging_root=args.staging_root,
        reference_manifest=args.reference_manifest,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except TushareDailyMigrationError as exc:
        print(f"Tushare daily migration failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
