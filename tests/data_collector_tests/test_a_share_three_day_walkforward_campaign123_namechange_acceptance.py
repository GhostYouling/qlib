import importlib.util
import json
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = (
    REPO_ROOT
    / "scripts/a_share_three_day_walkforward_campaign123_namechange_acceptance.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "a_share_three_day_walkforward_campaign123_namechange_acceptance",
        MODULE_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Client:
    def __init__(self, rows_by_year):
        self.rows_by_year = rows_by_year
        self.calls = []

    def namechange(self, **kwargs):
        self.calls.append(kwargs)
        year = int(kwargs["start_date"][:4])
        return pd.DataFrame(
            self.rows_by_year.get(year, []),
            columns=("ts_code", "start_date", "end_date", "ann_date", "change_reason"),
        )


def event_row(index: int, year: int, reason: str = "改名") -> dict:
    prefix = "600" if index % 2 == 0 else "000"
    suffix = "SH" if prefix == "600" else "SZ"
    code = f"{prefix}{index:03d}.{suffix}"
    day = index % 20 + 1
    return {
        "ts_code": code,
        "start_date": f"{year}01{day:02d}",
        "end_date": None,
        "ann_date": f"{year}01{day:02d}",
        "change_reason": reason,
    }


def test_collect_uses_exactly_seven_nonretrying_annual_projected_calls() -> None:
    module = load_module()
    client = Client({})
    rows, receipts = module.collect_projected_rows(client)
    assert rows == []
    assert len(receipts) == len(client.calls) == 7
    assert [call["start_date"] for call in client.calls] == [
        f"{year}0101" for year in range(2019, 2026)
    ]
    assert all(
        call["fields"] == "ts_code,start_date,end_date,ann_date,change_reason"
        for call in client.calls
    )
    assert all("name" not in call["fields"].split(",") for call in client.calls)


def test_projection_mismatch_and_suspected_truncation_fail_closed() -> None:
    module = load_module()

    class BadColumns(Client):
        def namechange(self, **kwargs):
            return pd.DataFrame(columns=["ts_code", "name"])

    with pytest.raises(module.Campaign123AcceptanceError, match="projection"):
        module.collect_projected_rows(BadColumns({}))

    class Truncated(Client):
        def namechange(self, **kwargs):
            return pd.DataFrame(
                [event_row(0, 2019)] * 5000,
                columns=module.REQUEST_FIELDS,
            )

    with pytest.raises(module.Campaign123AcceptanceError, match="truncation"):
        module.collect_projected_rows(Truncated({}))


def test_provider_call_counter_preserves_partial_failure_position() -> None:
    module = load_module()

    class FailsOnThird(Client):
        def namechange(self, **kwargs):
            self.calls.append(kwargs)
            if len(self.calls) == 3:
                raise RuntimeError("synthetic provider failure")
            return pd.DataFrame(columns=module.REQUEST_FIELDS)

    client = FailsOnThird({})
    counter = [0]
    with pytest.raises(RuntimeError, match="synthetic provider failure"):
        module.collect_projected_rows(client, provider_call_counter=counter)
    assert counter == [3]
    assert len(client.calls) == 3


def test_fixed_source_capacity_acceptance_passes_without_price_or_returns() -> None:
    module = load_module()
    rows_by_year = {year: [] for year in range(2019, 2026)}
    for index in range(35):
        year = 2019 + index % 7
        rows_by_year[year].append(event_row(index, year))
    client = Client(rows_by_year)
    rows, receipts = module.collect_projected_rows(client)
    events, evidence = module.evaluate_source_acceptance(rows, receipts)
    assert len(events) == 35
    assert evidence["checks"] == {
        "minimum_events_total": True,
        "minimum_distinct_instruments": True,
        "minimum_distinct_information_dates": True,
        "2019_minimum_events": True,
        "2022_minimum_events": True,
        "2025_minimum_events": True,
    }
    assert (
        evidence["adapter_stats"]["security_name_read_requested_or_persisted"] is False
    )


def test_capacity_failure_is_terminal_before_factor_values() -> None:
    module = load_module()
    receipts = [{"year": year, "rows": 0} for year in range(2019, 2026)]
    with pytest.raises(module.Campaign123AcceptanceError, match="capacity"):
        module.evaluate_source_acceptance([], receipts)


def test_plan_does_not_create_client_or_provider_request(monkeypatch) -> None:
    module = load_module()
    monkeypatch.setattr(
        module,
        "_provider_client",
        lambda token: (_ for _ in ()).throw(AssertionError("provider called")),
    )
    plan = module.build_plan(inspect_credential=False)
    assert plan["provider_request_issued"] is False
    assert plan["maximum_provider_calls"] == 7
    assert plan["request_fields"] == list(module.REQUEST_FIELDS)


def test_safe_dotenv_requires_mode_unique_nonempty_token_and_prints_nothing(
    tmp_path, capsys
) -> None:
    module = load_module()
    dotenv = tmp_path / ".env"
    dotenv.write_text('TUSHARE_TOKEN="secret-value"\n', encoding="utf-8")
    dotenv.chmod(0o600)
    assert module._safe_dotenv_token(dotenv) == "secret-value"
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    dotenv.write_text("TUSHARE_TOKEN=a\nTUSHARE_TOKEN=b\n", encoding="utf-8")
    with pytest.raises(module.Campaign123AcceptanceError, match="duplicate"):
        module._safe_dotenv_token(dotenv)
    dotenv.write_text("TUSHARE_TOKEN=x\n", encoding="utf-8")
    dotenv.chmod(0o644)
    with pytest.raises(module.Campaign123AcceptanceError, match="mode"):
        module._safe_dotenv_token(dotenv)


def test_run_requires_both_explicit_confirmation_flags() -> None:
    module = load_module()
    with pytest.raises(module.Campaign123AcceptanceError, match="confirmation"):
        module.run_acceptance(confirm_run=True, confirm_provider_request=False)
    with pytest.raises(module.Campaign123AcceptanceError, match="confirmation"):
        module.run_acceptance(confirm_run=False, confirm_provider_request=True)


def test_failure_record_is_sanitized_and_exclusive(tmp_path, monkeypatch) -> None:
    module = load_module()
    failure = tmp_path / "failure.json"
    monkeypatch.setattr(module, "FAILURE_PATH", failure)
    module._write_failure("provider_permission_or_request_failure", 1)
    record = json.loads(failure.read_text(encoding="utf-8"))
    assert record["exception_message_persisted"] is False
    assert record["credential_value_printed_hashed_or_persisted"] is False
    assert record["raw_provider_rows_persisted"] is False
    module._write_failure("different", 2)
    assert json.loads(failure.read_text(encoding="utf-8")) == record
