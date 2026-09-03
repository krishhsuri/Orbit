"""Typed errors for the LLM layer — callers must handle these explicitly."""


class LLMError(Exception):
    """Base class for LLM failures."""


class LLMUnavailable(LLMError):
    """Groq client missing, API down, rate-limited past retries, or model unavailable."""

    def __init__(self, message: str, *, cause: Exception | None = None):
        super().__init__(message)
        self.cause = cause


class LLMSchemaError(LLMError):
    """Response could not be parsed or failed Pydantic validation after repair retry."""

    def __init__(self, message: str, *, raw_content: str | None = None):
        super().__init__(message)
        self.raw_content = raw_content
