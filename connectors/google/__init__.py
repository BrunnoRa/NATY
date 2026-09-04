"""Google Workspace connectors, loaded only after explicit configuration."""

from connectors.google.auth import GoogleAuth

__all__ = ["GoogleAuth"]
