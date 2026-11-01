"""Deterministic, escaped text exports with no network, filesystem or model calls."""

import hashlib
import json
import re
from datetime import UTC
from html import escape

from gatherly.domain.ideas import Plan
from gatherly.domain.models import Currency, Milestone
from gatherly.services.plan_validation import validate_saved_plan

MINOR_UNITS = 100
ICS_LINE_OCTETS = 75
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_MARKDOWN = re.compile(r"([\\`*_{}\[\]()#+.!|>~\-])")


def format_money(amount: int, currency: Currency) -> str:
    """Format integer minor units without rounding through floating point."""
    if currency == "JPY":
        return f"JPY {amount:,}"
    whole, fraction = divmod(amount, MINOR_UNITS)
    return f"{currency} {whole:,}.{fraction:02d}"


def _markdown(text: str) -> str:
    plain = " ".join(_CONTROL.sub("", text).split())
    return _MARKDOWN.sub(r"\\\1", escape(plain, quote=False))


def _creative_markdown(plan: Plan) -> list[str]:
    ideas = plan.ideas
    lines = ["## Ideas", "", _markdown(ideas.concept_summary), "", "### Themes", ""]
    for theme in ideas.themes:
        lines.extend(
            [
                f"- **{_markdown(theme.name)}**: {_markdown(theme.mood)}",
                f"  - Palette: {', '.join(theme.colour_palette)}",
                f"  - Decor: {_markdown(theme.decor_notes)}",
            ]
        )
    for title, items in (
        ("Menu", ideas.menu),
        ("Activities", ideas.activities),
        ("Personal touches", ideas.personal_touches),
    ):
        lines.extend(["", f"### {title}", ""])
        lines.extend(f"- {_markdown(item)}" for item in items)
    lines.extend(["", "### Saving tips", ""])
    lines.extend(
        f"- {_markdown(tip.category)}: {_markdown(tip.suggestion)}"
        for tip in ideas.saving_tips
    )
    return lines


def _budget_markdown(plan: Plan) -> list[str]:
    event = plan.request
    lines = [
        "",
        "## Budget",
        "",
        f"Total: {format_money(plan.budget.total, event.currency)}",
        f"Per guest: {format_money(plan.budget.per_guest, event.currency)} "
        "(rounded down)",
        "",
        "| Category | Share | Allocation | Rationale |",
        "| --- | ---: | ---: | --- |",
    ]
    for line in plan.budget.lines:
        lines.append(
            f"| {_markdown(line.category)} | {line.percent}% | "
            f"{format_money(line.amount, event.currency)} | "
            f"{_markdown(line.rationale)} |"
        )
    lines.extend(f"- {_markdown(warning)}" for warning in plan.budget.warnings)
    return lines


def _vendors_markdown(plan: Plan) -> list[str]:
    lines = ["", "## Vendors", ""]
    for vendor in plan.vendors:
        lines.extend(
            [
                f"### {_markdown(vendor.category)}",
                "",
                f"Status: {vendor.status}; allocation: "
                f"{format_money(vendor.allocated_amount, plan.request.currency)}",
                f"Typical lead: {vendor.lead_time_days} days; "
                f"priority: {vendor.priority}",
                _markdown(vendor.why),
                "",
            ]
        )
        lines.extend(f"- Ask: {_markdown(text)}" for text in vendor.questions)
        lines.extend(f"- Request: {_markdown(text)}" for text in vendor.documents)
    return lines


def export_markdown(plan: Plan) -> str:
    """Produce readable event, budget, timeline, vendor and creative sections."""
    validate_saved_plan(plan)
    event = plan.request
    lines = [
        f"# {_markdown(event.name)}",
        "",
        f"{event.type.title()} · {event.date.isoformat()} · {event.guests} guests",
        f"AI status: {plan.ai_status}",
        "",
    ]
    for name in ("region", "preferences", "dietary", "interests", "notes"):
        value = getattr(event, name)
        if value:
            lines.append(f"{name.title()}: {_markdown(value)}")
    lines.extend(_budget_markdown(plan))
    lines.extend(["", "## Timeline", ""])
    lines.extend(
        f"- [{'x' if item.completed else ' '}] {item.due_date.isoformat()} "
        f"— {_markdown(item.title)} "
        f"({item.phase}; {item.status}; priority {item.priority})"
        for item in plan.timeline
    )
    lines.extend(_vendors_markdown(plan))
    return "\n".join(lines + [""] + _creative_markdown(plan)) + "\n"


def export_json(plan: Plan) -> str:
    """Preserve the complete versioned plan for strict JSON round-trip import."""
    validate_saved_plan(plan)
    return plan.model_dump_json(indent=2) + "\n"


def _ical_text(text: str) -> str:
    clean = _CONTROL.sub("", text).replace("\r\n", "\n").replace("\r", "\n")
    return (
        clean.replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace(";", "\\;")
        .replace(",", "\\,")
    )


def _fold(line: str) -> str:
    parts: list[str] = []
    current = ""
    length = 0
    for char in line:
        size = len(char.encode("utf-8"))
        if length + size > ICS_LINE_OCTETS:
            parts.append(current)
            current, length = " ", 1
        current += char
        length += size
    return "\r\n".join([*parts, current])


def _calendar_event(plan: Plan, item: Milestone) -> list[str]:
    identity = json.dumps(
        [plan.request.type, plan.request.name, str(plan.request.date), item.id]
    )
    uid = hashlib.sha256(identity.encode()).hexdigest()
    stamp = plan.generated_at.astimezone(UTC)
    timestamp = (
        f"{stamp.year:04d}{stamp.month:02d}{stamp.day:02d}T"
        f"{stamp.hour:02d}{stamp.minute:02d}{stamp.second:02d}Z"
    )
    due = item.due_date
    return [
        "BEGIN:VEVENT",
        f"UID:{uid}@gatherly.invalid",
        f"DTSTAMP:{timestamp}",
        f"DTSTART;VALUE=DATE:{due.year:04d}{due.month:02d}{due.day:02d}",
        "DURATION:P1D",
        f"SUMMARY:{_ical_text(plan.request.name + ': ' + item.title)}",
        f"DESCRIPTION:{_ical_text(item.phase + '; ' + item.status)}",
        f"PRIORITY:{item.priority}",
        "END:VEVENT",
    ]


def export_ics(plan: Plan) -> str:
    """Export all-day milestones with escaped values and UTF-8-safe RFC 5545 folding."""
    validate_saved_plan(plan)
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Gatherly AI//Planner//EN",
        "CALSCALE:GREGORIAN",
    ]
    for item in plan.timeline:
        lines.extend(_calendar_event(plan, item))
    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold(line) for line in lines) + "\r\n"
