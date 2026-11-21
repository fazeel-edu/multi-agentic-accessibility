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
