"""Thread-local context for passing question to chunkers without signature changes."""

import contextvars

_current_question: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "_current_question", default=None
)


def set_current_question(q: str | None) -> contextvars.Token:
    """Set the current question for the active context. Returns a token for reset."""
    return _current_question.set(q)


def get_current_question() -> str | None:
    """Get the current question from the active context."""
    return _current_question.get()


def reset_current_question(token: contextvars.Token) -> None:
    """Reset the question context using the token from set_current_question."""
    _current_question.reset(token)