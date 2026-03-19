class APIKeyNotConfiguredError(Exception):
    """Raised when LLM API key is not configured."""

    def __init__(
        self, message: str = "LLM not configured. Set provider and API key in Settings."
    ):
        self.message = message
        super().__init__(self.message)


class LLMCallError(Exception):
    """Raised when LLM call fails."""

    def __init__(self, message: str = "LLM call failed."):
        self.message = message
        super().__init__(self.message)
