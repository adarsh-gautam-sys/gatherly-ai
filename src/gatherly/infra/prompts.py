"""Load packaged policies and keep every free-text value inside escaped data blocks."""

import json
from dataclasses import dataclass
from importlib.resources import files

from gatherly.services.ports import IdeaTask


@dataclass(frozen=True)
class Prompts:
    """Versioned system and refinement instructions loaded once at composition."""

    system: str
    refinement: str


def load_prompts() -> Prompts:
    """Read the same policy resources in editable installs and built wheels."""
    root = files("prompts")
    return Prompts(
        system=root.joinpath("system.v1.txt").read_text(encoding="utf-8"),
        refinement=root.joinpath("refinement.v1.txt").read_text(encoding="utf-8"),
    )


def build_message(task: IdeaTask) -> str:
    """Separate validated quantities from escaped untrusted text and prior ideas."""
    trusted = {
        "type": task.event.type,
        "date": task.event.date.isoformat(),
        "guests": task.event.guests,
        "currency": task.event.currency,
        "budget": task.budget.model_dump(mode="json"),
        "requested_sections": task.sections,
    }
    untrusted = {
        "event": task.event.model_dump(
            mode="json", exclude={"type", "date", "guests", "currency", "budget"}
        ),
        "instruction": task.instruction,
        "previous_ideas": task.current.model_dump(mode="json")
        if task.current
        else None,
    }
    data = json.dumps(untrusted, ensure_ascii=True, sort_keys=True)
    data = data.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return (
        "TRUSTED_CONTEXT\n"
        + json.dumps(trusted, sort_keys=True)
        + "\n<UNTRUSTED_DATA>\n"
        + data
        + "\n</UNTRUSTED_DATA>"
    )
