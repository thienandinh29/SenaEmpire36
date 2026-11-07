"""Job-local research configuration; no global mutable backend shared across requests."""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from app.research.agent import ResearchAgent

_agent: ContextVar[ResearchAgent | None] = ContextVar("research_agent", default=None)


@contextmanager
def research_scope(agent: ResearchAgent) -> Iterator[None]:
    token = _agent.set(agent)
    try:
        yield
    finally:
        _agent.reset(token)


def current_agent() -> ResearchAgent:
    agent = _agent.get()
    if agent is None:
        from app.research.search import default_agent

        return default_agent()
    return agent
