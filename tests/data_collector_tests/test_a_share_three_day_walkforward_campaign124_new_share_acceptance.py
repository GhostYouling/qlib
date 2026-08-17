import importlib.util
import json
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = (
    REPO_ROOT
    / "scripts/a_share_three_day_walkforward_campaign124_new_share_acceptance.py"
)
ISSUE_SESSION = {
    2019: "20190102",
    2020: "20200102",
    2021: "20210104",
    2022: "20220104",
    2023: "20230103",
    2024: "20240102",
    2025: "20250102",
}


def load_module():
    spec = importlib.util.spec_from_file_location(
        "a_share_three_day_walkforward_campaign124_new_share_acceptance",
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

    def new_share(self, **kwargs):
        self.calls.append(kwargs)
        year = int(kwargs["start_date"][:4])
        return pd.DataFrame(
            self.rows_by_year.get(year, []),
            columns=("ts_code", "ipo_date", "issue_date", "ballot"),
        )


def event_row(index: int, year: int) -> dict:
    return {
        "ts_code": f"600{index:03d}.SH",
        "ipo_date": ISSUE_SESSION[year],
        "issue_date": ISSUE_SESSION[year],
        "ballot": 0.01 + (index % 17) / 1000,
    }


def accepted_sessions() -> tuple[str, ...]:
    return tuple(
        f"{value[:4]}-{value[4:6]}-{value[6:]}" for value in ISSUE_SESSION.values()
    )


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
        call["fields"] == "ts_code,ipo_date,issue_date,ballot" for call in client.calls
    )
    assert all(
        not set(call["fields"].split(","))
        & {
            "sub_code",
            "name",
            "amount",
            "market_amount",
            "price",
            "pe",
            "limit_amount",
            "funds",
        }
        for call in client.calls
    )


def test_projection_mismatch_and_suspected_truncation_fail_closed() -> None:
    module = load_module()

    class BadColumns(Client):
        def new_share(self, **kwargs):
            return pd.DataFrame(columns=["ts_code", "name"])

    with pytest.raises(module.Campaign124AcceptanceError, match="projection"):
        module.collect_projected_rows(BadColumns({}))

    class Truncated(Client):
        def new_share(self, **kwargs):
            return pd.DataFrame(
                [event_row(0, 2019)] * 2000,
                columns=module.REQUEST_FIELDS,
            )

    with pytest.raises(module.Campaign124AcceptanceError, match="truncation"):
        module.collect_projected_rows(Truncated({}))


def test_provider_call_counter_preserves_partial_failure_position() -> None:
    module = load_module()

    class FailsOnThird(Client):
        def new_share(self, **kwargs):
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


def test_fixed_source_coverage_acceptance_passes_without_price_or_returns() -> None:
    module = load_module()
    rows_by_year = {year: [] for year in range(2019, 2026)}
    index = 0
    for year in range(2019, 2024):
        for _ in range(30):
            rows_by_year[year].append(event_row(index, year))
            index += 1
    for year in (2024, 2025):
        for _ in range(5):
            rows_by_year[year].append(event_row(index, year))
            index += 1
    rows, receipts = module.collect_projected_rows(Client(rows_by_year))
    events, evidence = module.evaluate_source_acceptance(
        rows,
        receipts,
        accepted_calendar=accepted_sessions(),
    )
    assert len(events) == 160
    assert evidence["supported_events_total_2019_2023"] == 150
    assert all(evidence["checks"].values())
    assert evidence["price_or_forward_return_values_read"] is False
    assert (
        evidence["adapter_stats"]["forbidden_fields_read_requested_or_persisted"]
        is False
    )


def test_coverage_and_calendar_fail_before_factor_values() -> None:
    module = load_module()
    receipts = [{"year": year, "rows": 0} for year in range(2019, 2026)]
    with pytest.raises(module.Campaign124AcceptanceError, match="coverage"):
        module.evaluate_source_acceptance(
            [], receipts, accepted_calendar=accepted_sessions()
        )

    row = event_row(0, 2019)
    with pytest.raises(module.Campaign124AcceptanceError, match="accepted"):
        module.evaluate_source_acceptance(
            [row],
            [{"year": year, "rows": int(year == 2019)} for year in range(2019, 2026)],
            accepted_calendar=("2019-01-03",),
        )


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
    with pytest.raises(module.Campaign124AcceptanceError, match="duplicate"):
        module._safe_dotenv_token(dotenv)
    dotenv.write_text("TUSHARE_TOKEN=x\n", encoding="utf-8")
    dotenv.chmod(0o644)
    with pytest.raises(module.Campaign124AcceptanceError, match="mode"):
        module._safe_dotenv_token(dotenv)


def test_run_requires_both_explicit_confirmation_flags() -> None:
    module = load_module()
    with pytest.raises(module.Campaign124AcceptanceError, match="confirmation"):
        module.run_acceptance(confirm_run=True, confirm_provider_request=False)
    with pytest.raises(module.Campaign124AcceptanceError, match="confirmation"):
        module.run_acceptance(confirm_run=False, confirm_provider_request=True)


def test_failure_record_is_sanitized_and_exclusive(tmp_path, monkeypatch) -> None:
    module = load_module()
    failure = tmp_path / "failure.json"
    monkeypatch.setattr(module, "FAILURE_PATH", failure)
    module._write_failure("provider_permission_or_request_failure", 1)
    record = json.loads(failure.read_text(encoding="utf-8"))
    assert record["exception_message_persisted"] is False
    assert record["credential_value_printed_hashed_or_persisted"] is False
    assert record["raw_provider_rows_or_counts_persisted"] is False
    module._write_failure("different", 2)
    assert json.loads(failure.read_text(encoding="utf-8")) == record
