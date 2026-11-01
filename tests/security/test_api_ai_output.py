"""Verify the actual HTTP composition never returns provider credentials."""

import logging
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from google.genai import types
from pydantic import SecretStr

from gatherly.config import Settings
from gatherly.domain.ideas import Ideas, IdeasResponse
from gatherly.main import create_app
from tests.api.helpers import api_client
from tests.unit.ai_helpers import FakeGenerator, sample_ideas
from tests.unit.domain_helpers import event_request


def test_provider_secret_echo_falls_back_without_response_or_log_disclosure(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Runtime secret filtering remains active through the complete HTTP stack."""
    secret = "private-provider-credential"
    ideas = Ideas.model_validate(sample_ideas().model_dump() | {"menu": (secret,)})
    response = types.GenerateContentResponse(
        candidates=[
            types.Candidate(
                finish_reason=types.FinishReason.STOP,
                content=types.Content(
                    parts=[
                        types.Part(
                            text=IdeasResponse(
                                in_scope=True, ideas=ideas
                            ).model_dump_json()
                        )
                    ]
                ),
            )
        ]
    )
    caplog.set_level(logging.INFO, logger="gatherly.requests")
    with patch("gatherly.infra.runtime.genai.Client") as factory:
        sdk = factory.return_value
        sdk.aio.models.generate_content = AsyncMock(return_value=response)
        sdk.aio.aclose = AsyncMock()
        app = create_app(Settings(gemini_api_key=SecretStr(secret)))
        with TestClient(app) as client:
            result = client.post(
                "/api/v1/plans", json=event_request().model_dump(mode="json")
            )
        assert sdk.aio.models.generate_content.await_count == 2
    assert result.status_code == 200
    assert result.json()["ai_status"] == "unavailable"
    assert secret not in result.text + caplog.text


def test_generated_html_and_contacts_are_sanitised_at_the_http_boundary() -> None:
    """Schema-valid creative output is sanitised before response encoding."""
    ideas = Ideas.model_validate(
        sample_ideas().model_dump()
        | {
            "concept_summary": "<b>Welcome</b><script>bad()</script> https://example.com",
        }
    )
    with api_client(FakeGenerator([ideas])) as client:
        response = client.post(
            "/api/v1/plans", json=event_request().model_dump(mode="json")
        )
    assert response.status_code == 200
    assert response.json()["ai_status"] == "available"
    assert response.json()["ideas"]["concept_summary"] == "Welcome"
