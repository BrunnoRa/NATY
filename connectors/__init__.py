"""Optional external connectors. Importing this package performs no network work."""

from connectors.registry import ConnectorRegistry

__all__ = ["ConnectorRegistry"]
