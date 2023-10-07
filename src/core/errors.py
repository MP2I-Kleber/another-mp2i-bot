"""
All custom errors used, to get more convenient error messages.
"""

from __future__ import annotations

from discord.app_commands import errors


class BaseError(errors.AppCommandError):
    """
    The base error used for non-specific errors.
    """
