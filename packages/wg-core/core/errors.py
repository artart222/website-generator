"""Typed exception hierarchy for the website generator.

A single, explicit hierarchy lets callers catch precisely what they can handle
and lets the build fail loudly instead of silently shipping wrong output.

    WgError                     base for everything raised on purpose by wg-core
      ConfigError               configuration is missing, malformed, or invalid
      ContentValidationError    a page failed content-model validation
      BuildError                a build step failed
      TemplateError             a template failed to render or was not found
      PluginError               a plugin raised while running a hook (strict mode)
      IntegrationError          a runtime integration could not be resolved/run
"""

from __future__ import annotations


class WgError(Exception):
    """Base class for all intentional website-generator errors."""


class ConfigError(WgError):
    """Raised when configuration cannot be loaded or fails validation."""


class ContentValidationError(WgError):
    """Raised when page data fails content-model validation."""


class BuildError(WgError):
    """Raised when a build step fails."""


class TemplateError(WgError):
    """Raised when a template cannot be found or rendered."""


class PluginError(WgError):
    """Raised when a plugin hook fails and the build is running in strict mode."""


class IntegrationError(WgError):
    """Raised when a runtime integration cannot be resolved or executed."""
