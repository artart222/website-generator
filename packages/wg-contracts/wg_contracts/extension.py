"""Extension author base class (minimal hook surface)."""

from __future__ import annotations


class BaseExtension:
    """Base class for extension packages."""

    name = ""

    def register_models(self, registry) -> None:
        return None

    def register_frontend_targets(self, registry) -> None:
        return None

    def register_runtime_adapters(self, registry) -> None:
        return None

    def register_build_hooks(self, registry) -> None:
        return None

    def register_cli_commands(self, registry) -> None:
        return None
