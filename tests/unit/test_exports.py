"""Verify deterministic exports, money formatting and calendar interoperability."""

import asyncio
from datetime import date, timedelta

import pytest

from gatherly.domain.ideas import Plan
from gatherly.domain.models import Currency
from gatherly.infra.cache import MemoryIdeasCache
from gatherly.services.export_service import (
    export_ics,
    export_json,
    export_markdown,
    format_money,
)
from gatherly.services.plan_service import PlanService
from tests.unit.ai_helpers import FixedClock, sample_plan
from tests.unit.domain_helpers import event_request


@pytest.mark.parametrize(
    ("amount", "currency", "expected"),
    [
        (1, "USD", "USD 0.01"),
        (123_456, "INR", "INR 1,234.56"),
        (100, "EUR", "EUR 1.00"),
        (99, "GBP", "GBP 0.99"),
        (123_456, "JPY", "JPY 123,456"),
        (999_999_999, "USD", "USD 9,999,999.99"),
    ],
)
def test_money_formatting_never_rounds_via_float(
    amount: int,
    currency: Currency,
    expected: str,
) -> None:
    """Formatting preserves every minor unit, including zero-decimal yen."""
    assert format_money(amount, currency) == expected


def test_json_export_is_lossless_and_preserves_checklist_status() -> None:
    """The versioned JSON download can be loaded without changing user state."""
    values = sample_plan().model_dump()
    values["timeline"][0]["completed"] = True
    values["vendors"][0]["status"] = "contacted"
    plan = Plan.model_validate(values)
    assert Plan.model_validate_json(export_json(plan)) == plan
    assert "- [x]" in export_markdown(plan)


def test_markdown_escapes_html_links_structure_and_user_line_breaks() -> None:
    """Untrusted text cannot introduce tags, clickable Markdown or new sections."""
    values = sample_plan().model_dump()
    values["request"]["name"] = "<img src=x> [click](javascript:alert(1))"
    values["request"]["notes"] = "First\r\n# Injected | column\x00"
    values["request"]["dietary"] = "Vegetarian"
    values["ideas"]["concept_summary"] = "<script>bad()</script> & friends"
    plan = Plan.model_validate(values)
    output = export_markdown(plan)
    assert "<img" not in output and "<script>" not in output and "\x00" not in output
    assert "&lt;img" in output and "&lt;script&gt;" in output
    assert r"\[click\]\(javascript:alert\(1\)\)" in output
    assert "\n# Injected" not in output
    assert r"Notes: First \# Injected \| column" in output
    for section in (
        "Budget",
        "Timeline",
        "Vendors",
        "Ideas",
        "Themes",
        "Menu",
        "Activities",
        "Personal touches",
        "Saving tips",
    ):
        assert section in output
    assert "USD 10,000.00" in output
    assert "Vegetarian" in output
    assert "Ask:" in output and "Request:" in output


def test_calendar_escapes_injection_and_folds_utf8_at_75_octets() -> None:
    """Newlines stay in property text and folding never splits a Unicode character."""
    values = sample_plan().model_dump()
    values["request"]["name"] = "🎉" * 30 + ",;\\\r\nBEGIN:VEVENT\x00"
    plan = Plan.model_validate(values)
    output = export_ics(plan)
    physical_lines = output.split("\r\n")
    assert output.endswith("\r\n")
    assert all(len(line.encode("utf-8")) <= 75 for line in physical_lines)
    assert any(line.startswith(" ") for line in physical_lines)
    assert output.count("\r\nBEGIN:VEVENT\r\n") == len(plan.timeline)
    assert "\x00" not in output
    unfolded = output.replace("\r\n ", "")
    assert "🎉" * 30 in unfolded
    assert r"\,\;\\\nBEGIN:VEVENT" in unfolded
    assert unfolded.count("DURATION:P1D") == len(plan.timeline)
    assert unfolded.count("DTSTAMP:20280101T000000Z") == len(plan.timeline)
    for item in plan.timeline:
        assert f"DTSTART;VALUE=DATE:{item.due_date:%Y%m%d}" in unfolded


def test_calendar_ids_are_unique_and_stable_across_regeneration_timestamps() -> None:
    """Milestone identities remain stable independently of generation time."""
    original = sample_plan()
    later = Plan.model_validate(
        original.model_dump()
        | {
            "generated_at": original.generated_at + timedelta(days=1),
        }
    )

    def uids(plan: Plan) -> list[str]:
        return [
            line
            for line in export_ics(plan).replace("\r\n ", "").split("\r\n")
            if line.startswith("UID:")
        ]

    assert uids(original) == uids(later)
    assert len(set(uids(original))) == len(original.timeline)


def test_calendar_supports_last_representable_event_day_without_end_date_overflow() -> (
    None
):
    """All-day duration avoids adding one day beyond Python's maximum date."""
    service = PlanService(None, MemoryIdeasCache(1, 10), FixedClock(), "export")
    plan = asyncio.run(service.create(event_request(event_date=date.max)))
    assert "DTSTART;VALUE=DATE:99991231" in export_ics(plan)
