"""Gemini's async schema-constrained adapter; policy and validation stay server-side."""

import asyncio
import json

import httpx
from google import genai
from google.genai import errors, types

from gatherly.domain.ideas import Ideas, IdeasResponse, RefinementResponse
from gatherly.infra.prompts import Prompts, build_message
from gatherly.services.ports import IdeasUnavailable, IdeaTask

IDEAS_TEMPERATURE = 0.6
REFINEMENT_TEMPERATURE = 0.2
MAX_OUTPUT_TOKENS = 3072
MAX_RESPONSE_CHARACTERS = 32_000
_SAFETY_CATEGORIES = (
    types.HarmCategory.HARM_CATEGORY_HARASSMENT,
    types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
    types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
    types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
)


def _response_text(response: types.GenerateContentResponse) -> str:
    candidates = response.candidates or []
    if len(candidates) != 1 or candidates[0].finish_reason != types.FinishReason.STOP:
        raise IdeasUnavailable()
    content = candidates[0].content
    if content is None:
        raise IdeasUnavailable()
    text = "".join(part.text or "" for part in content.parts or [] if not part.thought)
    if not text.strip() or len(text) > MAX_RESPONSE_CHARACTERS:
        raise IdeasUnavailable()
    return text


def _parse(text: str, task: IdeaTask) -> Ideas:
    if task.current is None:
        response = IdeasResponse.model_validate_json(text)
        if not response.in_scope or response.ideas is None:
            raise IdeasUnavailable()
        return response.ideas
    refined = RefinementResponse.model_validate_json(text)
    if not refined.in_scope or refined.changes is None:
        raise IdeasUnavailable()
    changes = refined.changes.model_dump(mode="json", exclude_none=True)
    if set(changes) != set(task.sections):
        raise IdeasUnavailable()
    merged = task.current.model_dump(mode="json") | changes
    return Ideas.model_validate_json(json.dumps(merged))


class GeminiIdeasGenerator:
    """Limit concurrent provider calls; services own timeouts, retries and fallback."""

    def __init__(
        self, client: genai.Client, model: str, prompts: Prompts, concurrency: int
    ) -> None:
        """Inject an SDK client, verified model configuration and versioned policies."""
        self._client = client
        self._model = model
        self._prompts = prompts
        self._slots = asyncio.Semaphore(concurrency)

    async def generate(self, task: IdeaTask) -> Ideas:
        """Make one structured call and strictly validate the returned JSON."""
        refining = task.current is not None
        config = types.GenerateContentConfig(
            system_instruction=self._prompts.system
            + ("\n" + self._prompts.refinement if refining else ""),
            response_mime_type="application/json",
            response_schema=RefinementResponse if refining else IdeasResponse,
            temperature=REFINEMENT_TEMPERATURE if refining else IDEAS_TEMPERATURE,
            max_output_tokens=MAX_OUTPUT_TOKENS,
            candidate_count=1,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                disable=True
            ),
            safety_settings=[
                types.SafetySetting(
                    category=category,
                    threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                )
                for category in _SAFETY_CATEGORIES
            ],
        )
        try:
            async with self._slots:
                response = await self._client.aio.models.generate_content(
                    model=self._model,
                    contents=build_message(task),
                    config=config,
                )
            return _parse(_response_text(response), task)
        except (errors.APIError, httpx.HTTPError, ValueError):
            raise IdeasUnavailable() from None
