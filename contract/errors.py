"""Typed exceptions shared across the project."""


class ContractError(Exception):
    """Base class for errors raised by contract-level checks."""


class ConfigError(ContractError):
    """Config folder is missing, malformed or contains forbidden settings."""


class CostCapReached(ContractError):
    """No new session may start: remaining budget cannot cover a reservation."""


class RunStopped(ContractError):
    """The Run was stopped at the Cost Cap; resuming needs an explicit flag."""


class LedgerError(ContractError):
    """The ledger file or a ledger operation is invalid."""


class ProviderTermsError(ContractError):
    """The dated provider-terms record is missing or incomplete (FR35)."""


class ProviderError(ContractError):
    """A model-provider or SDK failure. `retryable` errors (timeout, 429, 5xx) get bounded retries."""

    def __init__(self, kind: str, message: str, retryable: bool) -> None:
        super().__init__(message)
        self.kind = kind
        self.retryable = retryable


class MissingApiKeyError(ContractError):
    """ANTHROPIC_API_KEY is not set in the environment."""


class OrchestrationError(ContractError):
    """The orchestrator broke its own invariant (a role skipped, added or repeated)."""
