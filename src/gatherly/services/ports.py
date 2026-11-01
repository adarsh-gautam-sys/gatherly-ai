"""Injected interfaces that keep orchestration independent of concrete adapters."""

from datetime import datetime
from typing import Protocol

from gatherly.domain.ideas import IDEA_SECTIONS, Ideas, IdeaSection
from gatherly.domain.models import BudgetPlan, DomainModel, EventRequest


class IdeaTask(DomainModel):
    """Validated event context and a bounded refinement request for creative output."""

    event: EventRequest
    budget: BudgetPlan
    current: Ideas | None = None
    instruction: str = ""
    sections: tuple[IdeaSection, ...] = IDEA_SECTIONS


class IdeasUnavailable(Exception):
    """An expected provider or output failure, carrying no user or provider text."""


class IdeasGenerator(Protocol):
    """Generate validated creative ideas without changing deterministic plan fields."""

    async def generate(self, task: IdeaTask) -> Ideas:
        """Return ideas or raise IdeasUnavailable without exposing provider details."""
        ...


class IdeasCache(Protocol):
    """Bounded transient storage of validated ideas under opaque request hashes."""

    def get(self, key: str) -> Ideas | None:
        """Return an unexpired value if present."""
        ...

    def put(self, key: str, value: Ideas) -> None:
        """Store an immutable validated value."""
        ...


class Clock(Protocol):
    """Read an aware timestamp at the service boundary."""

    def now(self) -> datetime:
        """Return the current aware timestamp."""
        ...
