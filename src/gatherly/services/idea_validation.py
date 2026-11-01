"""Treat generated text as untrusted before it reaches a plan or cache."""

import json
import re
from html import unescape
from html.parser import HTMLParser

from gatherly.domain.ideas import Ideas
from gatherly.domain.models import BudgetPlan

_CONTACT = re.compile(
    r"https?://\S+|www\.\S+|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|"
    r"\b[\w-]+(?:\.[\w-]+)*\.[A-Za-z]{2,}(?:/\S*)?|"
    r"(?<!\w)\+?\d(?:[\s().-]*\d){6,}(?!\w)",
    re.IGNORECASE,
)
_PRICE = re.compile(
    r"[₹$€£¥]|\b(?:USD|INR|EUR|GBP|JPY)\s*\d|\d\s*(?:dollars?|rupees?|euros?|pounds?|yen)\b",
    re.IGNORECASE,
)
_POLICY_MARKERS = ("GATHERLY_POLICY_V1", "GATHERLY_REFINEMENT_V1")


class _PlainText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.blocked = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self.blocked += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self.blocked:
            self.blocked -= 1

    def handle_data(self, data: str) -> None:
        if not self.blocked:
            self.parts.append(data)


def _clean_text(text: str, forbidden: tuple[str, ...]) -> str:
    decoded = unescape(unescape(text))
    if any(
        value and value.casefold() in decoded.casefold()
        for value in forbidden + _POLICY_MARKERS
    ):
        raise ValueError("Confidential content in creative output.")
    if _PRICE.search(decoded):
        raise ValueError("Creative output must not contain prices.")
    parser = _PlainText()
    parser.feed(decoded)
    parser.close()
    cleaned = _CONTACT.sub("", " ".join(parser.parts))
    cleaned = " ".join(cleaned.split())
    if not cleaned:
        raise ValueError("Creative text is empty after sanitisation.")
    return cleaned


def _clean_value(value: object, forbidden: tuple[str, ...]) -> object:
    if isinstance(value, str):
        return _clean_text(value, forbidden)
    if isinstance(value, list):
        return [_clean_value(item, forbidden) for item in value]
    if isinstance(value, dict):
        return {key: _clean_value(item, forbidden) for key, item in value.items()}
    return value


def sanitise_ideas(
    ideas: Ideas, budget: BudgetPlan, forbidden: tuple[str, ...] = ()
) -> Ideas:
    """Strip markup/contacts, reject prices/disclosures and validate budget links."""
    cleaned = _clean_value(ideas.model_dump(mode="json"), forbidden)
    # Python strict models require tuples; JSON decoding restores their schema types.
    result = Ideas.model_validate_json(json.dumps(cleaned))
    categories = {line.category for line in budget.lines}
    if any(tip.category not in categories for tip in result.saving_tips):
        raise ValueError("Saving tips must reference allocated budget categories.")
    return result
