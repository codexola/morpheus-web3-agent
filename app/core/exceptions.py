"""Domain exceptions and error codes."""

from __future__ import annotations


class AgentError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        retryable: bool = False,
        status_code: int = 400,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.status_code = status_code


class InvalidRequestError(AgentError):
    def __init__(self, message: str = "Invalid request.") -> None:
        super().__init__("INVALID_REQUEST", message, retryable=False, status_code=400)


class UnsupportedCapabilityError(AgentError):
    def __init__(self, capability: str) -> None:
        super().__init__(
            "UNSUPPORTED_CAPABILITY",
            f"Capability '{capability}' is not supported by this agent.",
            retryable=False,
            status_code=400,
        )


class InvalidAddressError(AgentError):
    def __init__(self, message: str = "Invalid blockchain address.") -> None:
        super().__init__("INVALID_ADDRESS", message)


class InvalidContractError(AgentError):
    def __init__(self, message: str = "Unable to analyze supplied contract.") -> None:
        super().__init__("INVALID_CONTRACT", message)


class RpcUnavailableError(AgentError):
    def __init__(self, message: str = "Blockchain RPC unavailable.") -> None:
        super().__init__("RPC_UNAVAILABLE", message, retryable=True, status_code=503)


class LlmUnavailableError(AgentError):
    def __init__(self, message: str = "LLM provider unavailable.") -> None:
        super().__init__("LLM_UNAVAILABLE", message, retryable=True, status_code=503)


class TimeoutError_(AgentError):
    def __init__(self, message: str = "Operation timed out.") -> None:
        super().__init__("TIMEOUT", message, retryable=True, status_code=504)


class RateLimitedError(AgentError):
    def __init__(self, message: str = "Rate limit exceeded.") -> None:
        super().__init__("RATE_LIMITED", message, retryable=True, status_code=429)


class ServiceUnavailableError(AgentError):
    def __init__(self, message: str = "Service is not accepting tasks.") -> None:
        super().__init__("INTERNAL_ERROR", message, retryable=True, status_code=503)


def error_body(exc: AgentError) -> dict:
    return {
        "success": False,
        "error": {
            "code": exc.code,
            "message": exc.message,
            "retryable": exc.retryable,
        },
    }
