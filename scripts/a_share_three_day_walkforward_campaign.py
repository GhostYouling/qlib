#!/usr/bin/env python3
"""Run one frozen historical three-session walk-forward campaign.

The runner has two deliberately separate return-reading phases:

* ``run-development`` reads only 2019-2023 and records every frozen trial.
* ``run-lockbox --confirm-open-lockbox`` reads 2024-2025 once for the
  deterministic validation survivors and permanently consumes that lockbox.

Candidate49 is not part of the feature catalog and this runner never reads or
writes its prospective signal, execution, or evaluation ledgers.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import statistics
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
import pyarrow.dataset as pa_dataset


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import a_share_short_horizon_factor_research as research  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CAMPAIGN = (
    REPO_ROOT
    / "docs"
    / "a_share_three_day_walkforward_campaign_001r1_preregistration.json"
)
DEFAULT_OUTPUT_ROOT = (
    REPO_ROOT
    / "data"
    / "experiments"
    / "short_horizon"
    / "historical_walkforward"
    / "campaign_001r1"
)
LEDGER_FILENAME = "trial_ledger.json"
SURVIVOR_FILENAME = "development_survivors.json"
LOCKBOX_INTENT_FILENAME = "lockbox_open_intent.json"
LOCKBOX_RECORD_FILENAME = "lockbox_consumption_record.json"
REPORT_FILENAME = "campaign_report.json"
LEDGER_KIND = "a_share_three_day_historical_walkforward_trial_ledger"
LEDGER_VERSION = 1
CHAIN_GENESIS = "0" * 64
MIN_SIGNAL_NAMES = 50
ONE_PRICE_MOVE_THRESHOLD = 0.045
ONE_PRICE_ABSOLUTE_TOLERANCE = 1e-8
ONE_PRICE_RELATIVE_TOLERANCE = 1e-8
MAX_EXIT_DELAY_SESSIONS = 20
FACTOR_COLUMN_PREFIX = "factor_score__"


class WalkForwardError(RuntimeError):
    """Fail-closed campaign error."""


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=research._json_default,
        allow_nan=False,
    ).encode("utf-8")


def value_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            default=research._json_default,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise WalkForwardError(f"required JSON is missing: {path}") from error
    except json.JSONDecodeError as error:
        raise WalkForwardError(f"required JSON is invalid: {path}") from error
    if not isinstance(value, dict):
        raise WalkForwardError(f"required JSON must be an object: {path}")
    return value


def resolve_bound_path(raw_path: str) -> Path:
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path.resolve()


def validate_file_binding(binding: dict[str, Any], label: str) -> Path:
    path = resolve_bound_path(str(binding.get("path") or ""))
    expected = str(binding.get("sha256") or "")
    if len(expected) != 64 or not path.is_file():
        raise WalkForwardError(f"{label} binding is incomplete or missing: {path}")
    observed = file_sha256(path)
    if observed != expected:
        raise WalkForwardError(
            f"{label} fingerprint changed: expected {expected}, observed {observed}"
        )
    return path


def materialize_campaign_revision(
    revision: dict[str, Any],
) -> dict[str, Any]:
    allowed_revision_keys = {
        "version",
        "kind",
        "campaign_id",
        "status",
        "frozen_at",
        "revision",
        "base_campaign",
        "infrastructure_repair",
        "implementation",
    }
    unexpected = sorted(set(revision) - allowed_revision_keys)
    if unexpected:
        raise WalkForwardError(
            "campaign revision contains unauthorized methodology overrides: "
            + ", ".join(unexpected)
        )
    base_path = validate_file_binding(
        revision.get("base_campaign") or {}, "base_campaign"
    )
    repair_path = validate_file_binding(
        revision.get("infrastructure_repair") or {}, "infrastructure_repair"
    )
    base = load_json(base_path)
    repair = load_json(repair_path)
    base_sha = file_sha256(base_path)
    failed_campaign = repair.get("failed_campaign") or {}
    if (
        revision.get("kind")
        != "a_share_three_day_historical_walkforward_campaign_preregistration"
        or revision.get("status")
        != "frozen_before_campaign_development_or_lockbox_return_read"
        or revision.get("campaign_id")
        != "a_share_three_day_walkforward_campaign_001"
        or revision.get("revision") != "r1"
        or base.get("kind")
        != "a_share_three_day_historical_walkforward_campaign_preregistration"
        or base.get("status")
        != "frozen_before_campaign_development_or_lockbox_return_read"
        or base.get("campaign_id") != "a_share_three_day_walkforward_campaign_001"
        or failed_campaign.get("sha256") != base_sha
    ):
        raise WalkForwardError("campaign revision base or repair provenance is invalid")
    authorized = repair.get("authorized_repair") or {}
    unchanged_flags = (
        "factor_library_changed",
        "factor_formula_or_direction_changed",
        "search_space_changed",
        "fold_or_purge_changed",
        "survivor_rule_changed",
        "execution_or_lockbox_gate_changed",
    )
    if any(authorized.get(flag) is not False for flag in unchanged_flags):
        raise WalkForwardError("campaign revision repair changes frozen methodology")
    implementation = revision.get("implementation") or {}
    if set(implementation) != {
        "script",
        "development_command",
        "lockbox_command",
        "output_root",
    }:
        raise WalkForwardError("campaign revision implementation is incomplete")
    campaign = dict(base)
    campaign["implementation"] = implementation
    campaign["revision"] = revision.get("revision")
    campaign["revision_provenance"] = {
        "base_campaign": revision.get("base_campaign"),
        "infrastructure_repair": revision.get("infrastructure_repair"),
    }
    return campaign


def load_campaign(path: Path) -> tuple[dict[str, Any], str]:
    path = path.expanduser().resolve()
    source_campaign = load_json(path)
    campaign = (
        materialize_campaign_revision(source_campaign)
        if source_campaign.get("base_campaign")
        else source_campaign
    )
    if (
        campaign.get("kind")
        != "a_share_three_day_historical_walkforward_campaign_preregistration"
        or campaign.get("status")
        != "frozen_before_campaign_development_or_lockbox_return_read"
        or campaign.get("campaign_id") != "a_share_three_day_walkforward_campaign_001"
    ):
        raise WalkForwardError("campaign preregistration is not the frozen campaign 001")
    campaign_sha = file_sha256(path)
    implementation = campaign.get("implementation") or {}
    script_path = validate_file_binding(implementation.get("script") or {}, "runner")
    if script_path != Path(__file__).resolve():
        raise WalkForwardError("campaign runner binding does not identify this script")
    for group_name in (
        "governance_bindings",
        "daily_data_bindings",
        "execution_policy_bindings",
    ):
        group = campaign.get(group_name) or {}
        for name, binding in sorted(group.items()):
            if (binding or {}).get("kind") == "directory":
                directory = resolve_bound_path(str((binding or {}).get("path") or ""))
                if not directory.is_dir():
                    raise WalkForwardError(
                        f"{group_name}.{name} directory is missing: {directory}"
                    )
            else:
                validate_file_binding(binding, f"{group_name}.{name}")
    for name, binding in sorted((campaign.get("feature_overlays") or {}).items()):
        validate_file_binding(binding, f"feature_overlays.{name}")
    for factor in campaign.get("factor_library") or []:
        for index, binding in enumerate(factor.get("bindings") or []):
            validate_file_binding(
                binding, f"factor_library.{factor.get('name')}.bindings[{index}]"
            )
    trials = build_trial_catalog(campaign)
    expected = int((campaign.get("search_space") or {}).get("expected_trial_count", -1))
    if len(trials) != expected:
        raise WalkForwardError(
            f"frozen trial catalog has {len(trials)} trials, expected {expected}"
        )
    return campaign, campaign_sha


def factor_score_column(name: str) -> str:
    return f"{FACTOR_COLUMN_PREFIX}{name}"


def build_trial_catalog(campaign: dict[str, Any]) -> list[dict[str, Any]]:
    factors = list(campaign.get("factor_library") or [])
    names = [str(item.get("name") or "") for item in factors]
    if not names or len(names) != len(set(names)) or any(not name for name in names):
        raise WalkForwardError("factor library names must be nonempty and unique")
    if "intraday_cumulative_vwap_crossing_rate_240m" in names:
        raise WalkForwardError("Candidate49 is forbidden from the historical catalog")
    canonical = sorted(names)
    search = campaign.get("search_space") or {}
    weights = list(search.get("pair_weight_grid_for_canonical_factor_order") or [])
    trials: list[dict[str, Any]] = []
    for name in canonical:
        trials.append(
            {
                "trial_id": f"wf001_single__{name}",
                "parent_trial_id": None,
                "kind": "single_factor",
                "feature_set": [name],
                "weights": [1.0],
                "complexity": 1,
            }
        )
    for left_index, left in enumerate(canonical):
        for right in canonical[left_index + 1 :]:
            for pair in weights:
                if (
                    not isinstance(pair, list)
                    or len(pair) != 2
                    or not math.isclose(sum(float(value) for value in pair), 1.0)
                    or any(float(value) <= 0.0 for value in pair)
                ):
                    raise WalkForwardError("pair weight grid must contain positive pairs summing to one")
                left_weight, right_weight = (float(pair[0]), float(pair[1]))
                suffix = f"w{round(left_weight * 100):02d}_{round(right_weight * 100):02d}"
                trials.append(
                    {
                        "trial_id": f"wf001_pair__{left}__{right}__{suffix}",
                        "parent_trial_id": None,
                        "kind": "pair_rank_blend",
                        "feature_set": [left, right],
                        "weights": [left_weight, right_weight],
                        "complexity": 2,
                    }
                )
    identifiers = [item["trial_id"] for item in trials]
    if len(identifiers) != len(set(identifiers)):
        raise WalkForwardError("trial catalog identifiers are not unique")
    return trials


def empty_ledger(campaign_path: Path, campaign_sha: str) -> dict[str, Any]:
    return {
        "version": LEDGER_VERSION,
        "kind": LEDGER_KIND,
        "campaign": {
            "path": str(campaign_path),
            "sha256": campaign_sha,
            "campaign_id": "a_share_three_day_walkforward_campaign_001",
        },
        "append_only": True,
        "chain_genesis": CHAIN_GENESIS,
        "entries": [],
        "chain_tip_sha256": CHAIN_GENESIS,
    }


def entry_payload_for_hash(entry: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in entry.items() if key != "entry_sha256"}


def validate_ledger(
    ledger: dict[str, Any], campaign_path: Path, campaign_sha: str
) -> dict[str, Any]:
    if (
        ledger.get("version") != LEDGER_VERSION
        or ledger.get("kind") != LEDGER_KIND
        or ledger.get("append_only") is not True
        or ledger.get("chain_genesis") != CHAIN_GENESIS
    ):
        raise WalkForwardError("trial ledger header is invalid")
    campaign = ledger.get("campaign") or {}
    if (
        campaign.get("path") != str(campaign_path)
        or campaign.get("sha256") != campaign_sha
        or campaign.get("campaign_id")
        != "a_share_three_day_walkforward_campaign_001"
    ):
        raise WalkForwardError("trial ledger campaign binding changed")
    previous = CHAIN_GENESIS
    identifiers: set[str] = set()
    for ordinal, entry in enumerate(ledger.get("entries") or [], start=1):
        if entry.get("ordinal") != ordinal:
            raise WalkForwardError("trial ledger ordinal sequence changed")
        if entry.get("previous_entry_sha256") != previous:
            raise WalkForwardError("trial ledger previous hash link changed")
        identifier = str(entry.get("trial_id") or "")
        if not identifier or identifier in identifiers:
            raise WalkForwardError("trial ledger contains a missing or duplicate trial_id")
        identifiers.add(identifier)
        observed = value_sha256(entry_payload_for_hash(entry))
        if entry.get("entry_sha256") != observed:
            raise WalkForwardError("trial ledger entry payload hash changed")
        previous = observed
    if ledger.get("chain_tip_sha256") != previous:
        raise WalkForwardError("trial ledger chain tip changed")
    return ledger


def load_or_initialize_ledger(
    path: Path, campaign_path: Path, campaign_sha: str
) -> dict[str, Any]:
    if path.exists():
        return validate_ledger(load_json(path), campaign_path, campaign_sha)
    ledger = empty_ledger(campaign_path, campaign_sha)
    atomic_write_json(path, ledger)
    return ledger


def append_ledger_entry(
    path: Path,
    ledger: dict[str, Any],
    payload: dict[str, Any],
    campaign_path: Path,
    campaign_sha: str,
) -> dict[str, Any]:
    validate_ledger(ledger, campaign_path, campaign_sha)
    existing = {str(item["trial_id"]): item for item in ledger["entries"]}
    trial_id = str(payload.get("trial_id") or "")
    if trial_id in existing:
        candidate = dict(payload)
        candidate["ordinal"] = existing[trial_id]["ordinal"]
        candidate["previous_entry_sha256"] = existing[trial_id][
            "previous_entry_sha256"
        ]
        candidate["entry_sha256"] = value_sha256(entry_payload_for_hash(candidate))
        if candidate != existing[trial_id]:
            raise WalkForwardError(f"existing ledger trial changed: {trial_id}")
        return ledger
    entry = dict(payload)
    entry["ordinal"] = len(ledger["entries"]) + 1
    entry["previous_entry_sha256"] = ledger["chain_tip_sha256"]
    entry["entry_sha256"] = value_sha256(entry_payload_for_hash(entry))
    updated = dict(ledger)
    updated["entries"] = [*ledger["entries"], entry]
    updated["chain_tip_sha256"] = entry["entry_sha256"]
    atomic_write_json(path, updated)
    return validate_ledger(load_json(path), campaign_path, campaign_sha)


def partition_parquet_paths(root: Path, years: Iterable[int]) -> list[str]:
    paths: list[str] = []
    for year in sorted(set(int(year) for year in years)):
        year_paths = sorted(root.glob(f"*/{year}.parquet"))
        if not year_paths:
            raise WalkForwardError(f"no factor partitions found for {year}: {root}")
        paths.extend(str(path) for path in year_paths)
    return paths


def read_partitioned_columns(
    root: Path, years: Iterable[int], columns: list[str]
) -> pd.DataFrame:
    dataset = pa_dataset.dataset(partition_parquet_paths(root, years), format="parquet")
    table = dataset.to_table(columns=columns, use_threads=True)
    frame = table.to_pandas(split_blocks=True, self_destruct=True)
    return frame


def normalize_factor_keys(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["trade_date"] = pd.to_datetime(
        result["trade_date"], errors="coerce"
    ).dt.normalize()
    result["instrument"] = result["symbol"].astype(str).str.upper()
    if result["trade_date"].isna().any() or result.duplicated(
        ["trade_date", "instrument"]
    ).any():
        raise WalkForwardError("factor data contains invalid or duplicate keys")
    return result.drop(columns=["symbol"])


def apply_fieldwise_overlay(
    base: pd.DataFrame,
    overlay: pd.DataFrame,
    factor_names: Iterable[str],
) -> pd.DataFrame:
    """Outer-union the valid supplement rows from the frozen small overlay."""

    keys = ["trade_date", "instrument"]
    if base.duplicated(keys).any() or overlay.duplicated(keys).any():
        raise WalkForwardError("fieldwise overlay merge keys are not unique")
    base_indexed = base.set_index(keys)
    overlay_indexed = overlay.set_index(keys)
    result = base_indexed.reindex(base_indexed.index.union(overlay_indexed.index))
    for name in factor_names:
        overlay_values = pd.to_numeric(overlay_indexed[name], errors="coerce")
        result[name] = overlay_values.combine_first(
            pd.to_numeric(result[name], errors="coerce")
        )
    return result.reset_index()


def load_factor_panel(
    campaign: dict[str, Any],
    years: Iterable[int],
    signal_dates: pd.DatetimeIndex,
) -> pd.DataFrame:
    factors = list(campaign["factor_library"])
    groups: dict[str, list[dict[str, Any]]] = {}
    for factor in factors:
        groups.setdefault(str(factor["dataset_group"]), []).append(factor)
    merged: pd.DataFrame | None = None
    date_values = set(pd.DatetimeIndex(signal_dates).normalize())
    for group_name, group_factors in sorted(groups.items()):
        root = resolve_bound_path(str(group_factors[0]["partition_root"]))
        columns = ["trade_date", "symbol", *[str(item["name"]) for item in group_factors]]
        frame = normalize_factor_keys(read_partitioned_columns(root, years, columns))
        frame = frame.loc[frame["trade_date"].isin(date_values)].copy()
        for factor in group_factors:
            name = str(factor["name"])
            frame[name] = pd.to_numeric(frame[name], errors="coerce")
        if group_name == "cleaned_four":
            overlay_binding = (campaign.get("feature_overlays") or {}).get(
                "cleaned_four_fieldwise"
            ) or {}
            overlay_path = validate_file_binding(overlay_binding, "cleaned four overlay")
            overlay = normalize_factor_keys(
                pd.read_parquet(
                    overlay_path,
                    columns=["trade_date", "symbol", *[str(item["name"]) for item in group_factors]],
                )
            )
            overlay = overlay.loc[overlay["trade_date"].isin(date_values)]
            frame = apply_fieldwise_overlay(
                frame,
                overlay,
                [str(item["name"]) for item in group_factors],
            )
        keep = ["trade_date", "instrument", *[str(item["name"]) for item in group_factors]]
        frame = frame[keep]
        merged = frame if merged is None else merged.merge(
            frame, on=["trade_date", "instrument"], how="outer", validate="one_to_one"
        )
    if merged is None:
        raise WalkForwardError("factor library did not produce a panel")
    return merged


def directional_rank_panel(
    panel: pd.DataFrame, campaign: dict[str, Any]
) -> pd.DataFrame:
    result = panel[["trade_date", "instrument"]].copy()
    for factor in campaign["factor_library"]:
        name = str(factor["name"])
        values = pd.to_numeric(panel[name], errors="coerce")
        temporary = pd.DataFrame(
            {
                "trade_date": panel["trade_date"],
                "value": values,
            }
        )
        higher = str(factor["direction"]) == "higher"
        result[factor_score_column(name)] = temporary.groupby(
            "trade_date", sort=False
        )["value"].rank(method="average", pct=True, ascending=higher)
    return result


def load_market_context(
    campaign: dict[str, Any], phase_end: str, target_start: str, batch_size: int
) -> tuple[pd.DataFrame, pd.DatetimeIndex]:
    daily = campaign["daily_data_bindings"]
    provider_uri = resolve_bound_path(str(daily["provider_uri"]["path"]))
    fundamentals_path = resolve_bound_path(str(daily["quarterly_quality"]["path"]))
    fundamentals = research.load_fundamentals(fundamentals_path)
    market = research.load_market_execution_data(
        provider_uri, "2019-01-01", phase_end, batch_size
    )
    market = research.attach_quality_asof(
        market,
        fundamentals,
        max_age_days=550,
        availability_calendar=pd.DatetimeIndex(market["datetime"].unique()),
    )
    market["datetime"] = pd.to_datetime(market["datetime"]).dt.normalize()
    calendar = pd.DatetimeIndex(sorted(market["datetime"].unique()))
    target = market.loc[market["datetime"].ge(pd.Timestamp(target_start))].copy()
    return target, calendar


def global_signal_schedule(
    calendar: pd.DatetimeIndex, hold_days: int = 3, stride: int = 3
) -> pd.DataFrame:
    calendar = pd.DatetimeIndex(calendar).normalize().unique().sort_values()
    rows: list[dict[str, Any]] = []
    for position in range(0, max(len(calendar) - hold_days, 0), stride):
        if position + hold_days >= len(calendar):
            break
        rows.append(
            {
                "signal_date": calendar[position],
                "entry_date": calendar[position + 1],
                "exit_date": calendar[position + hold_days],
            }
        )
    return pd.DataFrame(rows)


def purged_period_schedule(
    schedule: pd.DataFrame,
    start: str,
    end: str,
    purge_signal_count: int,
) -> pd.DataFrame:
    start_date = pd.Timestamp(start)
    end_date = pd.Timestamp(end)
    selected = schedule.loc[
        schedule["signal_date"].between(start_date, end_date)
        & schedule["entry_date"].between(start_date, end_date)
        & schedule["exit_date"].between(start_date, end_date)
    ].copy()
    if len(selected) <= 2 * purge_signal_count:
        return selected.iloc[0:0].copy()
    if purge_signal_count:
        selected = selected.iloc[purge_signal_count:-purge_signal_count].copy()
    return selected.reset_index(drop=True)


def quote_key_frame(market: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "datetime",
        "instrument",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "amount",
        "price_factor",
    ]
    result = market[columns].drop_duplicates(["datetime", "instrument"]).copy()
    if result.duplicated(["datetime", "instrument"]).any():
        raise WalkForwardError("daily quote context has duplicate keys")
    return result.set_index(["datetime", "instrument"]).sort_index()


def build_signal_panel(
    market: pd.DataFrame,
    factor_ranks: pd.DataFrame,
    schedule: pd.DataFrame,
) -> pd.DataFrame:
    schedule_map = schedule.set_index("signal_date")[["entry_date", "exit_date"]]
    signals = market.loc[
        market["quality_eligible"].fillna(False)
        & market["datetime"].isin(schedule["signal_date"])
    ].copy()
    signals = signals.rename(columns={"datetime": "signal_date"})
    signals = signals.merge(
        factor_ranks.rename(columns={"trade_date": "signal_date"}),
        on=["signal_date", "instrument"],
        how="left",
        validate="one_to_one",
    )
    signals = signals.join(schedule_map, on="signal_date")
    quotes = quote_key_frame(market).reset_index()
    entry = quotes.rename(
        columns={
            "datetime": "entry_date",
            "open": "entry_open",
            "high": "entry_high",
            "low": "entry_low",
            "close": "entry_close",
            "volume": "entry_volume",
            "amount": "entry_amount",
            "price_factor": "entry_factor",
        }
    )[
        [
            "entry_date",
            "instrument",
            "entry_open",
            "entry_high",
            "entry_low",
            "entry_close",
            "entry_volume",
            "entry_amount",
            "entry_factor",
        ]
    ]
    exit_quote = quotes.rename(
        columns={
            "datetime": "exit_date",
            "open": "exit_open",
            "high": "exit_high",
            "low": "exit_low",
            "close": "exit_close",
            "volume": "exit_volume",
            "amount": "exit_amount",
            "price_factor": "exit_factor",
        }
    )[
        [
            "exit_date",
            "instrument",
            "exit_open",
            "exit_high",
            "exit_low",
            "exit_close",
            "exit_volume",
            "exit_amount",
            "exit_factor",
        ]
    ]
    signals = signals.merge(
        entry, on=["entry_date", "instrument"], how="left", validate="many_to_one"
    )
    signals = signals.merge(
        exit_quote, on=["exit_date", "instrument"], how="left", validate="many_to_one"
    )
    signals["forward_gross_return"] = (
        pd.to_numeric(signals["exit_close"], errors="coerce")
        / pd.to_numeric(signals["entry_open"], errors="coerce")
        - 1.0
    )
    return signals


def trial_score(panel: pd.DataFrame, trial: dict[str, Any]) -> pd.Series:
    components = [
        pd.to_numeric(panel[factor_score_column(name)], errors="coerce")
        for name in trial["feature_set"]
    ]
    score = sum(
        weight * component for weight, component in zip(trial["weights"], components)
    )
    available = pd.Series(True, index=panel.index)
    for component in components:
        available &= component.notna() & np.isfinite(component)
    return score.where(available)


def finite_positive(value: Any) -> bool:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(numeric) and numeric > 0.0


def quote_is_valid(row: pd.Series, prefix: str = "") -> bool:
    return all(
        finite_positive(row.get(f"{prefix}{field}"))
        for field in ("open", "high", "low", "close", "volume")
    )


def is_one_price(open_value: float, high: float, low: float, close: float) -> bool:
    values = np.asarray([open_value, high, low, close], dtype=float)
    return bool(
        np.allclose(
            values,
            values[0],
            rtol=ONE_PRICE_RELATIVE_TOLERANCE,
            atol=ONE_PRICE_ABSOLUTE_TOLERANCE,
        )
    )


def association_metrics(
    panel: pd.DataFrame, schedule: pd.DataFrame, score: pd.Series, topk: int
) -> dict[str, Any]:
    allowed = set(pd.to_datetime(schedule["signal_date"]))
    working = panel.loc[panel["signal_date"].isin(allowed)].copy()
    working["score"] = score.loc[working.index]
    working = working.loc[
        working["score"].notna()
        & np.isfinite(working["score"])
        & working["forward_gross_return"].notna()
        & np.isfinite(working["forward_gross_return"])
    ]
    cohorts: list[dict[str, Any]] = []
    for signal_date, group in working.groupby("signal_date", sort=True):
        if len(group) < MIN_SIGNAL_NAMES or group["score"].nunique() < 2:
            continue
        rank_ic = group["score"].corr(group["forward_gross_return"], method="spearman")
        if pd.isna(rank_ic):
            continue
        ordered = group.sort_values(
            ["score", "instrument"], ascending=[False, True], kind="stable"
        )
        top = ordered.head(topk)["forward_gross_return"]
        bottom = ordered.tail(topk)["forward_gross_return"]
        gross = float(top.mean())
        net = float((1.0 - 0.00012) * (1.0 + gross) * (1.0 - 0.00062) - 1.0)
        cohorts.append(
            {
                "signal_date": pd.Timestamp(signal_date),
                "rank_ic": float(rank_ic),
                "top_minus_bottom_gross_return": float(top.mean() - bottom.mean()),
                "topk_net_return": net,
            }
        )
    if not cohorts:
        return {
            "cohorts": 0,
            "mean_rank_ic": None,
            "median_rank_ic": None,
            "positive_rank_ic_rate": None,
            "mean_top3_minus_bottom3_gross_return": None,
            "top3_net_cumulative_return": None,
            "top3_maximum_drawdown": None,
            "tail": {},
            "by_year": {},
        }
    frame = pd.DataFrame(cohorts)
    wealth = (1.0 + frame["topk_net_return"]).cumprod()
    drawdown = wealth / wealth.cummax() - 1.0
    by_year = {}
    for year, group in frame.groupby(frame["signal_date"].dt.year, sort=True):
        by_year[str(year)] = {
            "cohorts": int(len(group)),
            "mean_rank_ic": float(group["rank_ic"].mean()),
            "positive_rank_ic_rate": float((group["rank_ic"] > 0.0).mean()),
            "top3_net_cumulative_return": float(
                (1.0 + group["topk_net_return"]).prod() - 1.0
            ),
        }
    returns = frame["topk_net_return"]
    return {
        "cohorts": int(len(frame)),
        "mean_rank_ic": float(frame["rank_ic"].mean()),
        "median_rank_ic": float(frame["rank_ic"].median()),
        "positive_rank_ic_rate": float((frame["rank_ic"] > 0.0).mean()),
        "mean_top3_minus_bottom3_gross_return": float(
            frame["top_minus_bottom_gross_return"].mean()
        ),
        "top3_net_cumulative_return": float(wealth.iloc[-1] - 1.0),
        "top3_maximum_drawdown": float(drawdown.min()),
        "tail": {
            "p01_net_return": float(returns.quantile(0.01)),
            "p05_net_return": float(returns.quantile(0.05)),
            "median_net_return": float(returns.median()),
            "negative_return_rate": float((returns < 0.0).mean()),
            "worst_net_return": float(returns.min()),
        },
        "by_year": by_year,
    }


def selected_signal_baskets(
    panel: pd.DataFrame, schedule: pd.DataFrame, score: pd.Series, topk: int
) -> dict[pd.Timestamp, list[dict[str, Any]]]:
    allowed = set(pd.to_datetime(schedule["signal_date"]))
    working = panel.loc[panel["signal_date"].isin(allowed)].copy()
    working["score"] = score.loc[working.index]
    signal_valid = (
        working["score"].notna()
        & np.isfinite(working["score"])
        & working[["open", "high", "low", "close", "volume"]]
        .apply(pd.to_numeric, errors="coerce")
        .gt(0.0)
        .all(axis=1)
    )
    working = working.loc[signal_valid]
    baskets: dict[pd.Timestamp, list[dict[str, Any]]] = {}
    for signal_date, group in working.groupby("signal_date", sort=True):
        if len(group) < MIN_SIGNAL_NAMES or group["score"].nunique() < 2:
            continue
        selected = group.sort_values(
            ["score", "instrument"], ascending=[False, True], kind="stable"
        ).head(topk)
        if len(selected) != topk:
            continue
        baskets[pd.Timestamp(signal_date)] = [
            {
                "signal_date": pd.Timestamp(row.signal_date),
                "entry_date": pd.Timestamp(row.entry_date),
                "planned_exit_date": pd.Timestamp(row.exit_date),
                "instrument": str(row.instrument),
                "rank": rank,
                "signal_close": float(row.close),
                "signal_factor": float(row.price_factor),
            }
            for rank, row in enumerate(selected.itertuples(index=False), start=1)
        ]
    return baskets


@dataclass
class Position:
    instrument: str
    adjusted_units: float
    raw_shares: float
    planned_exit_date: pd.Timestamp
    entry_date: pd.Timestamp
    signal_date: pd.Timestamp
    last_mark_adjusted_close: float
    exit_attempts: int = 0


class QuoteStore:
    """Lazy quote lookup that avoids a multi-million-row Python dictionary."""

    def __init__(self, frame: pd.DataFrame):
        self.frame = frame
        self.cache: dict[tuple[pd.Timestamp, str], dict[str, float]] = {}

    def get(
        self,
        key: tuple[pd.Timestamp, str],
        default: Any = None,
    ) -> dict[str, float] | Any:
        normalized = (pd.Timestamp(key[0]), str(key[1]))
        if normalized in self.cache:
            return self.cache[normalized]
        try:
            row = self.frame.loc[normalized]
        except KeyError:
            return default
        quote = {
            "open": float(row["open"]) if pd.notna(row["open"]) else math.nan,
            "high": float(row["high"]) if pd.notna(row["high"]) else math.nan,
            "low": float(row["low"]) if pd.notna(row["low"]) else math.nan,
            "close": float(row["close"]) if pd.notna(row["close"]) else math.nan,
            "volume": float(row["volume"]) if pd.notna(row["volume"]) else math.nan,
            "amount": float(row["amount"]) if pd.notna(row["amount"]) else math.nan,
            "factor": (
                float(row["price_factor"])
                if pd.notna(row["price_factor"])
                else math.nan
            ),
        }
        self.cache[normalized] = quote
        return quote


def quote_lookup(market: pd.DataFrame) -> QuoteStore:
    columns = [
        "datetime",
        "instrument",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "amount",
        "price_factor",
    ]
    frame = (
        market[columns]
        .drop_duplicates(["datetime", "instrument"])
        .set_index(["datetime", "instrument"])
        .sort_index()
    )
    if not frame.index.is_unique:
        raise WalkForwardError("daily quote lookup keys are not unique")
    return QuoteStore(frame)


def valid_quote(quote: dict[str, float] | None) -> bool:
    return bool(
        quote
        and all(finite_positive(quote.get(name)) for name in ("open", "high", "low", "close", "volume"))
        and finite_positive(quote.get("factor"))
    )


def raw_price(quote: dict[str, float], field: str) -> float:
    return float(quote[field]) / float(quote["factor"])


def entry_blocked(
    quote: dict[str, float] | None, signal_raw_close: float
) -> tuple[bool, str | None]:
    if not valid_quote(quote):
        return True, "invalid_or_nonpositive_entry_quote"
    assert quote is not None
    if is_one_price(quote["open"], quote["high"], quote["low"], quote["close"]):
        move = raw_price(quote, "open") / signal_raw_close - 1.0
        if move >= ONE_PRICE_MOVE_THRESHOLD:
            return True, "upper_limit_like_queue"
    return False, None


def exit_blocked(
    quote: dict[str, float] | None, previous_quote: dict[str, float] | None
) -> tuple[bool, str | None]:
    if not valid_quote(quote):
        return True, "invalid_or_nonpositive_exit_quote"
    if not valid_quote(previous_quote):
        return True, "missing_previous_close_reference"
    assert quote is not None and previous_quote is not None
    if is_one_price(quote["open"], quote["high"], quote["low"], quote["close"]):
        move = raw_price(quote, "close") / raw_price(previous_quote, "close") - 1.0
        if move <= -ONE_PRICE_MOVE_THRESHOLD:
            return True, "lower_limit_like_queue"
    return False, None


def simulate_portfolio(
    quotes: Any,
    calendar: pd.DatetimeIndex,
    schedule: pd.DataFrame,
    baskets: dict[pd.Timestamp, list[dict[str, Any]]],
    *,
    pilot: bool,
    slippage: float,
) -> dict[str, Any]:
    if pilot:
        initial_equity = 200000.0
        buy_fee = 0.00012
        sell_fee = 0.00062
    else:
        initial_equity = 1.0
        buy_fee = 0.00012
        sell_fee = 0.00062
    cash = initial_equity
    positions: list[Position] = []
    calendar = pd.DatetimeIndex(calendar).normalize().unique().sort_values()
    position_by_date = {date: index for index, date in enumerate(calendar)}
    entries_by_date: dict[pd.Timestamp, list[dict[str, Any]]] = {}
    for signal_date, basket in baskets.items():
        for slot in basket:
            entries_by_date.setdefault(pd.Timestamp(slot["entry_date"]), []).append(slot)
    equity_curve: list[float] = []
    entry_blocks: dict[str, int] = {}
    exit_blocks: dict[str, int] = {}
    filled_entries = 0
    registered_slots = sum(len(value) for value in baskets.values())
    affordable_opportunities = 0
    affordability_denominator = 0
    participation_values: list[float] = []
    amount_missing_count = 0
    entry_gross_cap_violation_count = 0
    delayed_exits = 0
    on_time_exits = 0
    for date in calendar:
        prior_equity = equity_curve[-1] if equity_curve else initial_equity
        entry_slots = sorted(
            entries_by_date.get(date, []),
            key=lambda item: (int(item["rank"]), str(item["instrument"])),
        )
        normalized_slot_budget = cash / 3.0 if entry_slots and not pilot else None
        for slot in entry_slots:
            instrument = str(slot["instrument"])
            quote = quotes.get((date, instrument))
            signal_raw_close = float(slot["signal_close"]) / float(slot["signal_factor"])
            blocked, reason = entry_blocked(quote, signal_raw_close)
            if blocked:
                entry_blocks[str(reason)] = entry_blocks.get(str(reason), 0) + 1
                continue
            assert quote is not None
            if pilot:
                target_budget = prior_equity * 0.05
                gross_value = sum(
                    position.adjusted_units
                    * (
                        quotes.get((date, position.instrument), {}).get(
                            "close", position.last_mark_adjusted_close
                        )
                    )
                    for position in positions
                )
                headroom = max(prior_equity * 0.15 - gross_value, 0.0)
                available = min(target_budget, cash, headroom)
                adverse_price = raw_price(quote, "open") * (1.0 + slippage)
                affordability_denominator += 1
                one_lot_cost = 100.0 * adverse_price * (1.0 + buy_fee)
                if target_budget + 1e-12 >= one_lot_cost:
                    affordable_opportunities += 1
                shares = math.floor(available / (adverse_price * (1.0 + buy_fee)) / 100.0) * 100.0
                if shares <= 0.0:
                    entry_blocks["unaffordable_or_capital_constrained"] = (
                        entry_blocks.get("unaffordable_or_capital_constrained", 0) + 1
                    )
                    continue
                cost = shares * adverse_price * (1.0 + buy_fee)
                if cost > cash + 1e-8 or shares * adverse_price > headroom + 1e-8:
                    entry_gross_cap_violation_count += 1
                    continue
                adjusted_units = shares / quote["factor"]
                notional = shares * adverse_price
            else:
                assert normalized_slot_budget is not None
                budget = normalized_slot_budget
                adjusted_units = budget * (1.0 - buy_fee) / quote["open"]
                shares = adjusted_units * quote["factor"]
                cost = budget
                notional = budget
            cash -= cost
            filled_entries += 1
            if not finite_positive(quote.get("amount")):
                amount_missing_count += 1
            else:
                participation_values.append(float(notional / quote["amount"]))
            positions.append(
                Position(
                    instrument=instrument,
                    adjusted_units=float(adjusted_units),
                    raw_shares=float(shares),
                    planned_exit_date=pd.Timestamp(slot["planned_exit_date"]),
                    entry_date=date,
                    signal_date=pd.Timestamp(slot["signal_date"]),
                    last_mark_adjusted_close=float(quote["close"]),
                )
            )
        for position in positions:
            quote = quotes.get((date, position.instrument))
            if valid_quote(quote):
                assert quote is not None
                position.last_mark_adjusted_close = float(quote["close"])
        remaining: list[Position] = []
        for position in positions:
            if date < position.planned_exit_date:
                remaining.append(position)
                continue
            if position.exit_attempts >= MAX_EXIT_DELAY_SESSIONS:
                remaining.append(position)
                continue
            position.exit_attempts += 1
            current_quote = quotes.get((date, position.instrument))
            previous_date = (
                calendar[position_by_date[date] - 1]
                if position_by_date[date] > 0
                else None
            )
            previous_quote = (
                quotes.get((previous_date, position.instrument))
                if previous_date is not None
                else None
            )
            blocked, reason = exit_blocked(current_quote, previous_quote)
            if blocked:
                exit_blocks[str(reason)] = exit_blocks.get(str(reason), 0) + 1
                remaining.append(position)
                continue
            assert current_quote is not None
            delay = position_by_date[date] - position_by_date[position.planned_exit_date]
            if delay:
                delayed_exits += 1
            else:
                on_time_exits += 1
            if pilot:
                exit_shares = position.adjusted_units * current_quote["factor"]
                adverse_price = raw_price(current_quote, "close") * (1.0 - slippage)
                notional = exit_shares * adverse_price
                proceeds = notional * (1.0 - sell_fee)
            else:
                notional = position.adjusted_units * current_quote["close"]
                proceeds = notional * (1.0 - sell_fee)
            if not finite_positive(current_quote.get("amount")):
                amount_missing_count += 1
            else:
                participation_values.append(float(notional / current_quote["amount"]))
            cash += proceeds
        positions = remaining
        marked = cash + sum(
            position.adjusted_units * position.last_mark_adjusted_close
            for position in positions
        )
        equity_curve.append(float(marked))
    unresolved = len(positions)
    if equity_curve:
        series = pd.Series(equity_curve, dtype=float)
        drawdown = series / series.cummax() - 1.0
        net_return = float(series.iloc[-1] / initial_equity - 1.0)
        maximum_drawdown = float(drawdown.min())
    else:
        net_return = 0.0
        maximum_drawdown = 0.0
    return {
        "initial_equity": initial_equity,
        "final_marked_equity": (
            float(equity_curve[-1]) if equity_curve else initial_equity
        ),
        "net_cumulative_return": net_return,
        "maximum_drawdown": maximum_drawdown,
        "registered_signal_count": int(len(baskets)),
        "registered_entry_slot_count": int(registered_slots),
        "filled_entry_slot_count": int(filled_entries),
        "entry_blocked_by_reason": dict(sorted(entry_blocks.items())),
        "on_time_exit_count": int(on_time_exits),
        "delayed_exit_count": int(delayed_exits),
        "exit_blocked_attempts_by_reason": dict(sorted(exit_blocks.items())),
        "terminal_unresolved_position_count": int(unresolved),
        "board_lot_affordability_rate": (
            float(affordable_opportunities / affordability_denominator)
            if pilot and affordability_denominator
            else (None if pilot else 1.0)
        ),
        "maximum_filled_trade_daily_amount_participation": (
            float(max(participation_values)) if participation_values else 0.0
        ),
        "filled_trade_amount_missing_count": int(amount_missing_count),
        "entry_gross_cap_violation_count": int(entry_gross_cap_violation_count),
        "slippage_rate_each_side": float(slippage),
        "raw_daily_prices_persisted": False,
        "individual_trade_notionals_persisted": False,
    }


def evaluate_trial_period(
    panel: pd.DataFrame,
    quotes: Any,
    calendar: pd.DatetimeIndex,
    schedule: pd.DataFrame,
    trial: dict[str, Any],
    start: str,
    end: str,
    purge_signal_count: int,
    *,
    include_sensitivity: bool,
) -> dict[str, Any]:
    period_schedule = purged_period_schedule(
        schedule, start, end, purge_signal_count
    )
    score = trial_score(panel, trial)
    association = association_metrics(panel, period_schedule, score, topk=3)
    baskets = selected_signal_baskets(panel, period_schedule, score, topk=3)
    period_calendar = calendar[
        (calendar >= pd.Timestamp(start)) & (calendar <= pd.Timestamp(end))
    ]
    normalized = simulate_portfolio(
        quotes, period_calendar, period_schedule, baskets, pilot=False, slippage=0.0
    )
    pilot = simulate_portfolio(
        quotes, period_calendar, period_schedule, baskets, pilot=True, slippage=0.001
    )
    sensitivity = {}
    if include_sensitivity:
        for rate in (0.0, 0.0005, 0.001, 0.002):
            result = simulate_portfolio(
                quotes,
                period_calendar,
                period_schedule,
                baskets,
                pilot=True,
                slippage=rate,
            )
            sensitivity[f"{rate:.4f}"] = {
                "net_cumulative_return": result["net_cumulative_return"],
                "maximum_drawdown": result["maximum_drawdown"],
            }
    return {
        "start": start,
        "end": end,
        "purge_signal_count_each_boundary": purge_signal_count,
        "scheduled_signal_count_after_containment_and_purge": int(
            len(period_schedule)
        ),
        "association": association,
        "normalized_execution": normalized,
        "pilot_execution_primary_10bp": pilot,
        "pilot_slippage_sensitivity": sensitivity,
    }


def development_trial_payload(
    campaign: dict[str, Any],
    campaign_path: Path,
    campaign_sha: str,
    trial: dict[str, Any],
    panel: pd.DataFrame,
    quotes: Any,
    calendar: pd.DatetimeIndex,
    schedule: pd.DataFrame,
    created_at: str,
) -> dict[str, Any]:
    folds = []
    purge = int(campaign["split_protocol"]["purge_signal_sessions_each_boundary"])
    for fold in campaign["walkforward_folds"]:
        training = fold["training"]
        validation = fold["validation"]
        folds.append(
            {
                "fold": int(fold["fold"]),
                "training_metrics": evaluate_trial_period(
                    panel,
                    quotes,
                    calendar,
                    schedule,
                    trial,
                    training["start"],
                    training["end"],
                    purge,
                    include_sensitivity=False,
                ),
                "validation_metrics": evaluate_trial_period(
                    panel,
                    quotes,
                    calendar,
                    schedule,
                    trial,
                    validation["start"],
                    validation["end"],
                    purge,
                    include_sensitivity=False,
                ),
            }
        )
    aggregate = evaluate_trial_period(
        panel,
        quotes,
        calendar,
        schedule,
        trial,
        "2019-01-01",
        "2023-12-31",
        purge,
        include_sensitivity=True,
    )
    factor_lookup = {
        str(item["name"]): item for item in campaign["factor_library"]
    }
    formula = " + ".join(
        f"{weight:.2f}*directional_percentile_rank({name})"
        for name, weight in zip(trial["feature_set"], trial["weights"])
    )
    economic_hypothesis = "Rank blend of: " + "; ".join(
        str(factor_lookup[name]["economic_hypothesis"])
        for name in trial["feature_set"]
    )
    return {
        "trial_id": trial["trial_id"],
        "parent_trial_id": trial["parent_trial_id"],
        "campaign_id": campaign["campaign_id"],
        "phase": "development_walkforward",
        "created_at": created_at,
        "economic_hypothesis": economic_hypothesis,
        "formula": formula,
        "direction": "higher_combined_directional_score_is_better",
        "feature_set": list(trial["feature_set"]),
        "window_transform_threshold_filter_and_weight_configuration": {
            "kind": trial["kind"],
            "weights": list(trial["weights"]),
            "all_components_required": True,
            "daily_cross_sectional_rank_method": "average_percentile",
            "minimum_signal_names": MIN_SIGNAL_NAMES,
            "quality_maximum_age_days": 550,
            "minimum_listing_sessions": 20,
        },
        "training_and_validation_folds": folds,
        "data_and_code_fingerprints": {
            "campaign_preregistration": {
                "path": str(campaign_path),
                "sha256": campaign_sha,
            },
            "runner": {
                "path": str(Path(__file__).resolve()),
                "sha256": file_sha256(Path(__file__).resolve()),
            },
        },
        "fixed_execution_policy_fingerprints": campaign[
            "execution_policy_bindings"
        ],
        "training_metrics": [
            item["training_metrics"] for item in folds
        ],
        "validation_metrics": [
            item["validation_metrics"] for item in folds
        ],
        "development_aggregate_metrics": aggregate,
        "locked_backtest_metrics_when_opened": None,
        "status_and_rejection_reason": {
            "status": "development_walkforward_completed",
            "rejection_reason": None,
        },
        "candidate49_historical_return_read": False,
        "current_scoring_selection_sizing_or_orders_performed": False,
    }


def median(values: Iterable[float]) -> float:
    return float(statistics.median(float(value) for value in values))


def survivor_decision(
    entry: dict[str, Any], campaign: dict[str, Any]
) -> dict[str, Any]:
    rule = campaign["survivor_rule"]
    validations = list(entry.get("validation_metrics") or [])
    reasons: list[str] = []
    if len(validations) != len(campaign["walkforward_folds"]):
        reasons.append("incomplete_validation_fold_count")
    minimum_cohorts = int(rule["minimum_validation_association_cohorts_per_fold"])
    for index, result in enumerate(validations, start=1):
        association = result.get("association") or {}
        normalized = result.get("normalized_execution") or {}
        pilot = result.get("pilot_execution_primary_10bp") or {}
        if int(association.get("cohorts") or 0) < minimum_cohorts:
            reasons.append(f"fold_{index}_insufficient_association_cohorts")
        if int(normalized.get("terminal_unresolved_position_count") or 0) != 0:
            reasons.append(f"fold_{index}_normalized_unresolved_positions")
        if int(pilot.get("terminal_unresolved_position_count") or 0) != 0:
            reasons.append(f"fold_{index}_pilot_unresolved_positions")
        affordability = pilot.get("board_lot_affordability_rate")
        if (
            affordability is None
            or float(affordability)
            < float(rule["minimum_board_lot_affordability_rate_each_fold"])
        ):
            reasons.append(f"fold_{index}_board_lot_affordability")
        participation = pilot.get(
            "maximum_filled_trade_daily_amount_participation"
        )
        if (
            participation is None
            or float(participation)
            > float(rule["maximum_daily_amount_participation_each_fold"])
        ):
            reasons.append(f"fold_{index}_amount_participation")
    mean_ics = [
        float(item["association"]["mean_rank_ic"])
        for item in validations
        if (item.get("association") or {}).get("mean_rank_ic") is not None
    ]
    spreads = [
        float(item["association"]["mean_top3_minus_bottom3_gross_return"])
        for item in validations
        if (item.get("association") or {}).get(
            "mean_top3_minus_bottom3_gross_return"
        )
        is not None
    ]
    normalized_returns = [
        float(item["normalized_execution"]["net_cumulative_return"])
        for item in validations
    ]
    pilot_returns = [
        float(item["pilot_execution_primary_10bp"]["net_cumulative_return"])
        for item in validations
    ]
    drawdowns = [
        float(item["normalized_execution"]["maximum_drawdown"])
        for item in validations
    ]
    positive_ic_folds = sum(value > 0.0 for value in mean_ics)
    positive_execution_folds = sum(value > 0.0 for value in normalized_returns)
    validation_quality_passed = bool(
        len(mean_ics) == 3
        and positive_ic_folds >= int(rule["quality_view_positive_ic_fold_count_gte"])
        and positive_execution_folds
        >= int(rule["quality_view_positive_normalized_return_fold_count_gte"])
        and median(mean_ics) > 0.0
        and median(spreads) > 0.0
        and min(drawdowns) >= float(rule["quality_view_worst_drawdown_gte"])
    )
    return {
        "operationally_admissible": not reasons,
        "operational_rejection_reasons": reasons,
        "validation_quality_view_passed": validation_quality_passed,
        "positive_mean_rank_ic_fold_count": int(positive_ic_folds),
        "positive_normalized_return_fold_count": int(positive_execution_folds),
        "median_validation_mean_rank_ic": (
            median(mean_ics) if mean_ics else -math.inf
        ),
        "median_validation_spread": median(spreads) if spreads else -math.inf,
        "median_validation_normalized_return": median(normalized_returns),
        "median_validation_pilot_return": median(pilot_returns),
        "worst_validation_normalized_drawdown": min(drawdowns),
        "complexity": int(
            (
                entry.get(
                    "window_transform_threshold_filter_and_weight_configuration"
                )
                or {}
            ).get("kind")
            != "single_factor"
        )
        + 1,
    }


def build_survivor_record(
    campaign: dict[str, Any],
    campaign_path: Path,
    campaign_sha: str,
    ledger: dict[str, Any],
) -> dict[str, Any]:
    catalog = build_trial_catalog(campaign)
    development = {
        str(entry["trial_id"]): entry
        for entry in ledger["entries"]
        if entry.get("phase") == "development_walkforward"
    }
    if set(development) != {item["trial_id"] for item in catalog}:
        raise WalkForwardError("development ledger is incomplete; survivors cannot freeze")
    decisions = []
    for item in catalog:
        trial_id = item["trial_id"]
        decision = survivor_decision(development[trial_id], campaign)
        decisions.append({"trial_id": trial_id, **decision})
    admissible = [item for item in decisions if item["operationally_admissible"]]
    ranked = sorted(
        admissible,
        key=lambda item: (
            -int(item["positive_mean_rank_ic_fold_count"]),
            -int(item["positive_normalized_return_fold_count"]),
            -float(item["median_validation_mean_rank_ic"]),
            -float(item["median_validation_pilot_return"]),
            -float(item["worst_validation_normalized_drawdown"]),
            int(item["complexity"]),
            str(item["trial_id"]),
        ),
    )
    maximum = int(campaign["survivor_rule"]["maximum_lockbox_survivors"])
    selected = [str(item["trial_id"]) for item in ranked[:maximum]]
    return {
        "version": 1,
        "kind": "a_share_three_day_walkforward_development_survivors",
        "status": "development_complete_survivors_frozen_before_lockbox_open",
        "campaign": {"path": str(campaign_path), "sha256": campaign_sha},
        "ledger_prefix": {
            "entry_count": len(ledger["entries"]),
            "chain_tip_sha256": ledger["chain_tip_sha256"],
            "entries_sha256": value_sha256(ledger["entries"]),
        },
        "survivor_rule": campaign["survivor_rule"],
        "trial_decisions": decisions,
        "ranked_operationally_admissible_trial_ids": [
            str(item["trial_id"]) for item in ranked
        ],
        "selected_lockbox_survivor_trial_ids": selected,
        "selected_survivor_count": len(selected),
        "created_at": max(str(entry["created_at"]) for entry in development.values()),
        "lockbox_return_fields_read": False,
        "candidate49_historical_return_read": False,
        "current_scoring_selection_sizing_or_orders_allowed": False,
    }


def ensure_survivor_record(
    path: Path,
    campaign: dict[str, Any],
    campaign_path: Path,
    campaign_sha: str,
    ledger: dict[str, Any],
) -> dict[str, Any]:
    expected = build_survivor_record(
        campaign, campaign_path, campaign_sha, ledger
    )
    if path.exists():
        observed = load_json(path)
        if observed != expected:
            raise WalkForwardError("frozen survivor record changed")
        return observed
    atomic_write_json(path, expected)
    return load_json(path)


def prepare_phase_data(
    campaign: dict[str, Any],
    *,
    phase_end: str,
    target_start: str,
    years: Iterable[int],
    batch_size: int,
) -> tuple[
    pd.DataFrame,
    QuoteStore,
    pd.DatetimeIndex,
    pd.DataFrame,
]:
    market, calendar = load_market_context(
        campaign, phase_end, target_start, batch_size
    )
    schedule = global_signal_schedule(calendar)
    target_schedule = schedule.loc[
        schedule["signal_date"].ge(pd.Timestamp(target_start))
    ].copy()
    factors = load_factor_panel(
        campaign,
        years,
        pd.DatetimeIndex(target_schedule["signal_date"]),
    )
    ranks = directional_rank_panel(factors, campaign)
    panel = build_signal_panel(market, ranks, target_schedule)
    quotes = quote_lookup(market)
    return panel, quotes, calendar, schedule


def run_development(args: argparse.Namespace) -> dict[str, Any]:
    campaign_path = Path(args.campaign).expanduser().resolve()
    campaign, campaign_sha = load_campaign(campaign_path)
    output_root = Path(args.output_root).expanduser().resolve()
    ledger_path = output_root / LEDGER_FILENAME
    survivor_path = output_root / SURVIVOR_FILENAME
    if (output_root / LOCKBOX_INTENT_FILENAME).exists():
        raise WalkForwardError("development cannot run after the lockbox was opened")
    ledger = load_or_initialize_ledger(
        ledger_path, campaign_path, campaign_sha
    )
    catalog = build_trial_catalog(campaign)
    existing = {
        str(entry["trial_id"])
        for entry in ledger["entries"]
        if entry.get("phase") == "development_walkforward"
    }
    expected = {item["trial_id"] for item in catalog}
    unexpected = existing - expected
    if unexpected:
        raise WalkForwardError(
            f"development ledger has unexpected trials: {sorted(unexpected)}"
        )
    if existing == expected:
        survivors = ensure_survivor_record(
            survivor_path,
            campaign,
            campaign_path,
            campaign_sha,
            ledger,
        )
        return {
            "status": "development_already_complete_idempotent",
            "trial_count": len(existing),
            "survivor_count": survivors["selected_survivor_count"],
            "ledger_path": str(ledger_path),
            "survivor_path": str(survivor_path),
            "lockbox_return_fields_read": False,
        }
    print("loading 2019-2023 market, quality, and frozen factor panels", flush=True)
    panel, quotes, calendar, schedule = prepare_phase_data(
        campaign,
        phase_end="2023-12-31",
        target_start="2019-01-01",
        years=range(2019, 2024),
        batch_size=int(args.batch_size),
    )
    created_at = utc_now()
    for index, trial in enumerate(catalog, start=1):
        if trial["trial_id"] in existing:
            continue
        try:
            payload = development_trial_payload(
                campaign,
                campaign_path,
                campaign_sha,
                trial,
                panel,
                quotes,
                calendar,
                schedule,
                created_at,
            )
        except Exception as error:
            payload = {
                "trial_id": trial["trial_id"],
                "parent_trial_id": trial["parent_trial_id"],
                "campaign_id": campaign["campaign_id"],
                "phase": "development_walkforward",
                "created_at": created_at,
                "economic_hypothesis": "frozen trial failed before complete metrics",
                "formula": "frozen_by_campaign_preregistration",
                "direction": "frozen_by_campaign_preregistration",
                "feature_set": list(trial["feature_set"]),
                "window_transform_threshold_filter_and_weight_configuration": {
                    "kind": trial["kind"],
                    "weights": list(trial["weights"]),
                },
                "training_and_validation_folds": [],
                "data_and_code_fingerprints": {
                    "campaign_preregistration": {
                        "path": str(campaign_path),
                        "sha256": campaign_sha,
                    }
                },
                "fixed_execution_policy_fingerprints": campaign[
                    "execution_policy_bindings"
                ],
                "training_metrics": [],
                "validation_metrics": [],
                "locked_backtest_metrics_when_opened": None,
                "status_and_rejection_reason": {
                    "status": "infrastructure_failed",
                    "rejection_reason": f"{type(error).__name__}: {error}",
                },
                "candidate49_historical_return_read": False,
                "current_scoring_selection_sizing_or_orders_performed": False,
            }
        ledger = append_ledger_entry(
            ledger_path,
            ledger,
            payload,
            campaign_path,
            campaign_sha,
        )
        print(f"recorded development trial {index}/{len(catalog)}", flush=True)
    survivors = ensure_survivor_record(
        survivor_path,
        campaign,
        campaign_path,
        campaign_sha,
        ledger,
    )
    return {
        "status": "development_completed",
        "trial_count": len(catalog),
        "survivor_count": survivors["selected_survivor_count"],
        "ledger_path": str(ledger_path),
        "ledger_sha256": file_sha256(ledger_path),
        "survivor_path": str(survivor_path),
        "survivor_sha256": file_sha256(survivor_path),
        "lockbox_return_fields_read": False,
        "candidate49_historical_return_read": False,
    }


def lockbox_trial_payload(
    campaign: dict[str, Any],
    campaign_path: Path,
    campaign_sha: str,
    survivor_record: dict[str, Any],
    original_entry: dict[str, Any],
    trial: dict[str, Any],
    panel: pd.DataFrame,
    quotes: Any,
    calendar: pd.DatetimeIndex,
    schedule: pd.DataFrame,
    created_at: str,
) -> dict[str, Any]:
    purge = int(campaign["split_protocol"]["purge_signal_sessions_each_boundary"])
    full = evaluate_trial_period(
        panel,
        quotes,
        calendar,
        schedule,
        trial,
        "2024-01-01",
        "2025-12-31",
        purge,
        include_sensitivity=True,
    )
    yearly = {
        str(year): evaluate_trial_period(
            panel,
            quotes,
            calendar,
            schedule,
            trial,
            f"{year}-01-01",
            f"{year}-12-31",
            purge,
            include_sensitivity=False,
        )
        for year in (2024, 2025)
    }
    association = full["association"]
    normalized = full["normalized_execution"]
    pilot = full["pilot_execution_primary_10bp"]
    annual_ic_positive = all(
        (yearly[str(year)]["association"]["mean_rank_ic"] or -math.inf) > 0.0
        for year in (2024, 2025)
    )
    annual_normalized_positive = all(
        yearly[str(year)]["normalized_execution"]["net_cumulative_return"] > 0.0
        for year in (2024, 2025)
    )
    annual_pilot_positive = all(
        yearly[str(year)]["pilot_execution_primary_10bp"]["net_cumulative_return"] > 0.0
        for year in (2024, 2025)
    )
    failures: list[str] = []
    if (association.get("mean_rank_ic") or -math.inf) <= 0.0:
        failures.append("nonpositive_lockbox_mean_rank_ic")
    if (association.get("positive_rank_ic_rate") or -math.inf) <= 0.5:
        failures.append("lockbox_positive_rank_ic_rate_not_above_half")
    if (
        association.get("mean_top3_minus_bottom3_gross_return") or -math.inf
    ) <= 0.0:
        failures.append("nonpositive_lockbox_top3_minus_bottom3_spread")
    if not annual_ic_positive:
        failures.append("nonpositive_lockbox_annual_mean_rank_ic")
    if normalized["net_cumulative_return"] <= 0.0:
        failures.append("nonpositive_lockbox_normalized_return")
    if normalized["maximum_drawdown"] < -0.20:
        failures.append("lockbox_normalized_drawdown_below_minus_20pct")
    if not annual_normalized_positive:
        failures.append("nonpositive_lockbox_annual_normalized_return")
    if normalized["terminal_unresolved_position_count"] != 0:
        failures.append("lockbox_normalized_terminal_unresolved")
    if pilot["net_cumulative_return"] <= 0.0:
        failures.append("nonpositive_lockbox_pilot_return")
    if not annual_pilot_positive:
        failures.append("nonpositive_lockbox_annual_pilot_return")
    if (pilot["board_lot_affordability_rate"] or 0.0) < 0.90:
        failures.append("lockbox_board_lot_affordability_below_90pct")
    if (
        pilot["maximum_filled_trade_daily_amount_participation"] > 0.01
        or pilot["filled_trade_amount_missing_count"] != 0
    ):
        failures.append("lockbox_amount_participation_or_missing_amount")
    if pilot["terminal_unresolved_position_count"] != 0:
        failures.append("lockbox_pilot_terminal_unresolved")
    return {
        "trial_id": f"{trial['trial_id']}::lockbox_2024_2025",
        "parent_trial_id": trial["trial_id"],
        "campaign_id": campaign["campaign_id"],
        "phase": "locked_2024_2025_backtest",
        "created_at": created_at,
        "economic_hypothesis": original_entry["economic_hypothesis"],
        "formula": original_entry["formula"],
        "direction": original_entry["direction"],
        "feature_set": list(trial["feature_set"]),
        "window_transform_threshold_filter_and_weight_configuration": original_entry[
            "window_transform_threshold_filter_and_weight_configuration"
        ],
        "training_and_validation_folds": original_entry[
            "training_and_validation_folds"
        ],
        "data_and_code_fingerprints": {
            "campaign_preregistration": {
                "path": str(campaign_path),
                "sha256": campaign_sha,
            },
            "survivor_record_sha256": value_sha256(survivor_record),
            "runner": {
                "path": str(Path(__file__).resolve()),
                "sha256": file_sha256(Path(__file__).resolve()),
            },
        },
        "fixed_execution_policy_fingerprints": campaign[
            "execution_policy_bindings"
        ],
        "training_metrics": original_entry["training_metrics"],
        "validation_metrics": original_entry["validation_metrics"],
        "locked_backtest_metrics_when_opened": {
            "combined_2024_2025": full,
            "standalone_year_replays": yearly,
            "final_gate": {
                "passed": not failures,
                "failures": failures,
                "historical_pass_can_directly_promote_or_select": False,
            },
        },
        "status_and_rejection_reason": {
            "status": (
                "lockbox_passed_research_only"
                if not failures
                else "lockbox_rejected"
            ),
            "rejection_reason": failures or None,
        },
        "candidate49_historical_return_read": False,
        "current_scoring_selection_sizing_or_orders_performed": False,
    }


def run_lockbox(args: argparse.Namespace) -> dict[str, Any]:
    if not args.confirm_open_lockbox:
        raise WalkForwardError("run-lockbox requires --confirm-open-lockbox")
    campaign_path = Path(args.campaign).expanduser().resolve()
    campaign, campaign_sha = load_campaign(campaign_path)
    output_root = Path(args.output_root).expanduser().resolve()
    ledger_path = output_root / LEDGER_FILENAME
    survivor_path = output_root / SURVIVOR_FILENAME
    intent_path = output_root / LOCKBOX_INTENT_FILENAME
    record_path = output_root / LOCKBOX_RECORD_FILENAME
    ledger = validate_ledger(
        load_json(ledger_path), campaign_path, campaign_sha
    )
    survivors = ensure_survivor_record(
        survivor_path,
        campaign,
        campaign_path,
        campaign_sha,
        ledger,
    )
    if record_path.exists():
        record = load_json(record_path)
        if (
            record.get("campaign_sha256") != campaign_sha
            or record.get("survivor_record_sha256") != file_sha256(survivor_path)
            or record.get("status") != "lockbox_consumed_once_complete"
        ):
            raise WalkForwardError("existing lockbox record is invalid")
        return {
            "status": "lockbox_already_consumed_idempotent",
            "record_path": str(record_path),
            "record_sha256": file_sha256(record_path),
        }
    expected_intent_core = {
        "version": 1,
        "kind": "a_share_three_day_walkforward_lockbox_open_intent",
        "status": "opened_once_pending_completion",
        "campaign_sha256": campaign_sha,
        "survivor_record_sha256": file_sha256(survivor_path),
        "runner_sha256": file_sha256(Path(__file__).resolve()),
        "lockbox_start": "2024-01-01",
        "lockbox_end": "2025-12-31",
        "candidate49_historical_return_read": False,
    }
    if intent_path.exists():
        intent = load_json(intent_path)
        for key, value in expected_intent_core.items():
            if intent.get(key) != value:
                raise WalkForwardError("lockbox open intent changed")
    else:
        intent = {**expected_intent_core, "opened_at": utc_now()}
        atomic_write_json(intent_path, intent)
    selected_ids = list(survivors["selected_lockbox_survivor_trial_ids"])
    if not selected_ids:
        raise WalkForwardError(
            "frozen survivor rule selected zero trials; lockbox remains opened "
            "but cannot produce candidate results"
        )
    print("lockbox intent is frozen; loading 2024-2025 once", flush=True)
    panel, quotes, calendar, schedule = prepare_phase_data(
        campaign,
        phase_end="2025-12-31",
        target_start="2024-01-01",
        years=(2024, 2025),
        batch_size=int(args.batch_size),
    )
    catalog = {item["trial_id"]: item for item in build_trial_catalog(campaign)}
    development = {
        str(entry["trial_id"]): entry
        for entry in ledger["entries"]
        if entry.get("phase") == "development_walkforward"
    }
    created_at = str(intent["opened_at"])
    for index, trial_id in enumerate(selected_ids, start=1):
        lockbox_id = f"{trial_id}::lockbox_2024_2025"
        if any(entry["trial_id"] == lockbox_id for entry in ledger["entries"]):
            continue
        payload = lockbox_trial_payload(
            campaign,
            campaign_path,
            campaign_sha,
            survivors,
            development[trial_id],
            catalog[trial_id],
            panel,
            quotes,
            calendar,
            schedule,
            created_at,
        )
        ledger = append_ledger_entry(
            ledger_path,
            ledger,
            payload,
            campaign_path,
            campaign_sha,
        )
        print(f"recorded lockbox survivor {index}/{len(selected_ids)}", flush=True)
    lockbox_entries = [
        entry
        for entry in ledger["entries"]
        if entry.get("phase") == "locked_2024_2025_backtest"
        and entry.get("parent_trial_id") in selected_ids
    ]
    if len(lockbox_entries) != len(selected_ids):
        raise WalkForwardError("lockbox ledger is incomplete after the run")
    passers = [
        entry
        for entry in lockbox_entries
        if (
            entry.get("locked_backtest_metrics_when_opened") or {}
        ).get("final_gate", {}).get("passed")
    ]
    champion = None
    if passers:
        champion = sorted(
            passers,
            key=lambda entry: (
                -float(
                    entry["locked_backtest_metrics_when_opened"][
                        "combined_2024_2025"
                    ]["association"]["mean_rank_ic"]
                ),
                -float(
                    entry["locked_backtest_metrics_when_opened"][
                        "combined_2024_2025"
                    ]["pilot_execution_primary_10bp"]["net_cumulative_return"]
                ),
                str(entry["parent_trial_id"]),
            ),
        )[0]["parent_trial_id"]
    record = {
        "version": 1,
        "kind": "a_share_three_day_walkforward_lockbox_consumption_record",
        "status": "lockbox_consumed_once_complete",
        "campaign_sha256": campaign_sha,
        "survivor_record_sha256": file_sha256(survivor_path),
        "lockbox_intent_sha256": file_sha256(intent_path),
        "ledger": {
            "path": str(ledger_path),
            "entry_count": len(ledger["entries"]),
            "chain_tip_sha256": ledger["chain_tip_sha256"],
            "file_sha256": file_sha256(ledger_path),
        },
        "selected_survivor_trial_ids": selected_ids,
        "completed_lockbox_trial_ids": [
            str(entry["parent_trial_id"]) for entry in lockbox_entries
        ],
        "final_gate_passer_trial_ids": [
            str(entry["parent_trial_id"]) for entry in passers
        ],
        "research_only_champion_trial_id": champion,
        "opened_at": intent["opened_at"],
        "completed_at": utc_now(),
        "lockbox_classification": "historically_exposed_quasi_out_of_sample_not_pristine",
        "candidate49_historical_return_read": False,
        "current_scoring_allowed": False,
        "selection_allowed": False,
        "sizing_allowed": False,
        "orders_allowed": False,
    }
    atomic_write_json(record_path, record)
    write_report(
        output_root / REPORT_FILENAME,
        campaign,
        campaign_sha,
        ledger,
        survivors,
        record,
    )
    return {
        "status": "lockbox_consumed_once_complete",
        "survivor_count": len(selected_ids),
        "final_gate_passer_count": len(passers),
        "research_only_champion_trial_id": champion,
        "record_path": str(record_path),
        "record_sha256": file_sha256(record_path),
        "report_path": str(output_root / REPORT_FILENAME),
    }


def write_report(
    path: Path,
    campaign: dict[str, Any],
    campaign_sha: str,
    ledger: dict[str, Any],
    survivors: dict[str, Any],
    lockbox: dict[str, Any] | None,
) -> None:
    development = [
        entry
        for entry in ledger["entries"]
        if entry.get("phase") == "development_walkforward"
    ]
    failures = [
        entry
        for entry in development
        if (entry.get("status_and_rejection_reason") or {}).get("status")
        == "infrastructure_failed"
    ]
    report = {
        "version": 1,
        "kind": "a_share_three_day_walkforward_campaign_report",
        "campaign_id": campaign["campaign_id"],
        "campaign_sha256": campaign_sha,
        "classification": "historically_exposed_quasi_out_of_sample_not_pristine",
        "development_trial_count": len(development),
        "development_infrastructure_failure_count": len(failures),
        "selected_lockbox_survivor_count": survivors["selected_survivor_count"],
        "selected_lockbox_survivor_trial_ids": survivors[
            "selected_lockbox_survivor_trial_ids"
        ],
        "lockbox": lockbox,
        "ledger": {
            "path": str(path.parent / LEDGER_FILENAME),
            "entry_count": len(ledger["entries"]),
            "chain_tip_sha256": ledger["chain_tip_sha256"],
        },
        "candidate49": {
            "historical_return_read": False,
            "prospective_registration_or_ledgers_changed": False,
        },
        "current_scoring_selection_sizing_or_orders_allowed": False,
        "survivorship_bias_warning": (
            "The local holding universe derives from a current listing snapshot "
            "and can introduce survivorship bias."
        ),
    }
    atomic_write_json(path, report)


def status(args: argparse.Namespace) -> dict[str, Any]:
    campaign_path = Path(args.campaign).expanduser().resolve()
    campaign, campaign_sha = load_campaign(campaign_path)
    output_root = Path(args.output_root).expanduser().resolve()
    result: dict[str, Any] = {
        "status": "campaign_frozen_pending_development",
        "campaign_path": str(campaign_path),
        "campaign_sha256": campaign_sha,
        "expected_trial_count": len(build_trial_catalog(campaign)),
        "candidate49_historical_return_read": False,
    }
    ledger_path = output_root / LEDGER_FILENAME
    if ledger_path.exists():
        ledger = validate_ledger(
            load_json(ledger_path), campaign_path, campaign_sha
        )
        result["ledger_entry_count"] = len(ledger["entries"])
        result["ledger_chain_tip_sha256"] = ledger["chain_tip_sha256"]
        result["development_trial_count"] = sum(
            entry.get("phase") == "development_walkforward"
            for entry in ledger["entries"]
        )
        result["lockbox_trial_count"] = sum(
            entry.get("phase") == "locked_2024_2025_backtest"
            for entry in ledger["entries"]
        )
        result["status"] = "development_in_progress_or_complete"
    survivor_path = output_root / SURVIVOR_FILENAME
    if survivor_path.exists():
        survivors = load_json(survivor_path)
        result["survivor_count"] = survivors["selected_survivor_count"]
        result["status"] = "survivors_frozen_lockbox_unopened"
    if (output_root / LOCKBOX_INTENT_FILENAME).exists():
        result["status"] = "lockbox_opened_pending_completion"
    record_path = output_root / LOCKBOX_RECORD_FILENAME
    if record_path.exists():
        lockbox = load_json(record_path)
        result["status"] = lockbox["status"]
        result["final_gate_passer_trial_ids"] = lockbox[
            "final_gate_passer_trial_ids"
        ]
        result["research_only_champion_trial_id"] = lockbox[
            "research_only_champion_trial_id"
        ]
    return result


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--campaign", default=str(DEFAULT_CAMPAIGN))
    value.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    subcommands = value.add_subparsers(dest="command", required=True)
    subcommands.add_parser("status")
    development = subcommands.add_parser("run-development")
    development.add_argument("--batch-size", type=int, default=100)
    lockbox = subcommands.add_parser("run-lockbox")
    lockbox.add_argument("--batch-size", type=int, default=100)
    lockbox.add_argument("--confirm-open-lockbox", action="store_true")
    return value


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "status":
            result = status(args)
        elif args.command == "run-development":
            result = run_development(args)
        elif args.command == "run-lockbox":
            result = run_lockbox(args)
        else:
            raise WalkForwardError(f"unsupported command: {args.command}")
    except (WalkForwardError, ValueError, FileNotFoundError) as error:
        print(
            json.dumps(
                {"status": "failed", "error": str(error)},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2
    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
            default=research._json_default,
            allow_nan=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
