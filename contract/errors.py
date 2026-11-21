"""Typed exceptions shared across the project."""


class ContractError(Exception):
    """Base class for errors raised by contract-level checks."""


class ConfigError(ContractError):
    """Config folder is missing, malformed or contains forbidden settings."""
