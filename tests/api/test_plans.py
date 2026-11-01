"""Exercise all v1 endpoints, strict wire contracts and documented responses."""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from gatherly.config import Settings
from gatherly.domain.ideas import Plan
from gatherly.domain.models import EventType
from gatherly.main import create_app
from tests.api.helpers import api_client
from tests.unit.ai_helpers import FakeGenerator, sample_ideas, sample_plan
from tests.unit.domain_helpers import event_request


@pytest.mark.parametrize("kind", ["wedding", "birthday", "community"])
def test_create_complete_offline_plan(kind: EventType) -> None:
    """All event types return complete, round-trip-safe plans with fallback."""
    with api_client() as client:
        response = client.post(
            "/api/v1/plans", json=event_request(kind).model_dump(mode="json")
        )
    assert response.status_code == 200
    plan = Plan.model_validate_json(response.content)
    assert plan.ai_status == "unavailable"
    assert plan.budget.total == plan.request.budget
    assert plan.timeline and plan.vendors and len(plan.ideas.themes) == 3


def test_event_types_report_unadjusted_percentages() -> None:
    """Intake metadata matches the three PRD templates and sums to 100."""
    with api_client() as client:
        response = client.get("/api/v1/event-types")
    assert response.status_code == 200
    assert {item["type"] for item in response.json()} == {
        "wedding",
        "birthday",
        "community",
    }
    for item in response.json():
        assert sum(line["percent"] for line in item["categories"]) == 100


def test_budget_never_uses_ai_or_requires_a_future_date() -> None:
    """Interactive what-if arithmetic also works for historical saved plans."""
    fake = FakeGenerator([])
    with api_client(fake) as client:
        response = client.post(
            "/api/v1/plans/budget",
            json=event_request(budget=99, event_date=date(2020, 1, 1)).model_dump(
                mode="json"
            ),
        )
    assert response.status_code == 200
    assert sum(line["amount"] for line in response.json()["lines"]) == 99
    assert not fake.tasks


def test_ideas_refresh_bypasses_existing_cache_and_returns_only_ideas() -> None:
    """An explicit refresh does not return a previously cached generation."""
    fake = FakeGenerator([sample_ideas(), sample_ideas()])
    with api_client(fake) as client:
        body = event_request().model_dump(mode="json")
        assert (
            client.post("/api/v1/plans", json=body).json()["ai_status"] == "available"
        )
        response = client.post("/api/v1/plans/ideas", json=body)
    assert response.status_code == 200
    assert set(response.json()) == {"ideas", "ai_status"}
    assert response.json()["ai_status"] == "available"
    assert len(fake.tasks) == 2


def test_refinement_updates_budget_preserves_status_and_other_sections() -> None:
    """Round-tripped client state is accepted and money is updated first."""
    with api_client() as client:
        plan = client.post(
            "/api/v1/plans", json=event_request().model_dump(mode="json")
        ).json()
        plan["vendors"][0]["status"] = "booked"
        response = client.post(
            "/api/v1/plans/refine",
            json={
                "plan": plan,
                "change": {
                    "instruction": "Simpler vegetarian menu",
                    "sections": ["menu"],
                    "budget": 800_000,
                },
            },
        )
    assert response.status_code == 200
    changed = response.json()
    assert changed["budget"]["total"] == changed["request"]["budget"] == 800_000
    assert changed["vendors"][0]["status"] == "booked"
    assert changed["timeline"] == plan["timeline"]
    assert changed["ideas"]["themes"] == plan["ideas"]["themes"]


@pytest.mark.parametrize("path", ["/api/v1/plans", "/api/v1/plans/ideas"])
def test_past_dates_fail_before_llm(path: str) -> None:
    """Future-date errors follow the common envelope and avoid model calls."""
    fake = FakeGenerator([])
    with api_client(fake) as client:
        response = client.post(
            path,
            json=event_request(event_date=date(2027, 1, 1)).model_dump(mode="json"),
        )
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_plan"
    assert not fake.tasks


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("budget", 1.5),
        ("budget", True),
        ("budget", "100"),
        ("guests", "50"),
        ("guests", 5001),
        ("type", "conference"),
        ("date", "tomorrow"),
        ("date", 1_800_000_000),
        ("currency", "BTC"),
        ("notes", "x" * 2001),
        ("private-extra-field", "private-value"),
    ],
)
def test_strict_inputs_return_safe_validation_errors(field: str, value: object) -> None:
    """JSON support never weakens number, enum, length or unknown-field validation."""
    with api_client() as client:
        response = client.post(
            "/api/v1/plans",
            json=event_request().model_dump(mode="json") | {field: value},
        )
    assert response.status_code == 422
    assert set(response.json()) == {"code", "message", "details"}
    assert response.json()["details"]
    assert "private-extra-field" not in response.text
    assert "private-value" not in response.text


@pytest.mark.parametrize("body", ["{bad json", "{}", "null", "[]", '{"budget":NaN}'])
def test_malformed_or_missing_body_has_consistent_error(body: str) -> None:
    """Broken JSON and missing fields use the same safe contract."""
    with api_client() as client:
        response = client.post(
            "/api/v1/plans", content=body, headers={"Content-Type": "application/json"}
        )
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


@pytest.mark.parametrize(
    ("format", "mime"),
    [
        ("md", "text/markdown"),
        ("json", "application/json"),
        ("ics", "text/calendar"),
    ],
)
def test_exports_are_attachments_and_json_round_trips(format: str, mime: str) -> None:
    """Downloads contain the complete plan or milestone calendar with safe names."""
    with api_client() as client:
        plan = client.post(
            "/api/v1/plans", json=event_request().model_dump(mode="json")
        ).json()
        response = client.post(f"/api/v1/plans/export?format={format}", json=plan)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith(mime)
    assert (
        response.headers["content-disposition"]
        == f'attachment; filename="gatherly-plan.{format}"'
    )
    if format == "json":
        assert response.json() == plan
    elif format == "ics":
        assert response.text.count("BEGIN:VEVENT") == len(plan["timeline"])
    else:
        assert all(
            f"## {title}" in response.text
            for title in ("Budget", "Timeline", "Vendors", "Ideas")
        )


def test_unsupported_export_format_and_schema_version_are_rejected() -> None:
    """Only documented formats and version-one plans can be imported."""
    with api_client() as client:
        plan = client.post(
            "/api/v1/plans", json=event_request().model_dump(mode="json")
        ).json()
        assert (
            client.post("/api/v1/plans/export?format=pdf", json=plan).status_code == 422
        )
        plan["schema_version"] = "99"
        assert (
            client.post("/api/v1/plans/export?format=json", json=plan).status_code
            == 422
        )


def test_openapi_has_resolvable_refs_and_real_contracts() -> None:
    """Request schemas, error envelopes and export media agree with runtime."""
    with api_client(settings=Settings(environment="development")) as client:
        schema = client.get("/openapi.json").json()
    expected = {"/health", "/api/v1/event-types", "/api/v1/plans"} | {
        f"/api/v1/plans/{suffix}" for suffix in ("budget", "ideas", "refine", "export")
    }
    assert set(schema["paths"]) == expected

    def walk(value: object) -> None:
        if isinstance(value, dict):
            if "$ref" in value:
                target = schema
                for part in value["$ref"].removeprefix("#/").split("/"):
                    target = target[part]
                assert target
            for nested in value.values():
                walk(nested)
        elif isinstance(value, list):
            for nested in value:
                walk(nested)

    walk(schema)
    for path in expected - {"/health", "/api/v1/event-types"}:
        operation = schema["paths"][path]["post"]
        assert operation["requestBody"]["required"]
        assert operation["responses"]["422"]["content"]["application/json"]["schema"][
            "$ref"
        ].endswith("ErrorEnvelope")
    assert (
        schema["components"]["schemas"]["EventRequest"]["additionalProperties"] is False
    )


def test_unstarted_service_returns_503_but_budget_still_works() -> None:
    """An unavailable runtime does not disable deterministic recalculation."""
    client = TestClient(create_app())
    body = event_request().model_dump(mode="json")
    assert client.post("/api/v1/plans", json=body).status_code == 503
    assert client.post("/api/v1/plans/budget", json=body).status_code == 200


def test_default_lifespan_owns_and_releases_the_offline_planner() -> None:
    """Production composition works without a dependency override or API key."""
    app = create_app()
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/plans", json=event_request().model_dump(mode="json")
        )
        assert response.status_code == 200
        assert response.json()["ai_status"] == "unavailable"
        assert app.state.planner is not None
    assert app.state.planner is None


def test_exports_do_not_require_an_active_planner_or_ai() -> None:
    """All export formats remain available without starting provider dependencies."""
    client = TestClient(create_app())
    plan = sample_plan().model_dump(mode="json")
    for format in ("md", "json", "ics"):
        response = client.post(f"/api/v1/plans/export?format={format}", json=plan)
        assert response.status_code == 200
