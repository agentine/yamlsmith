"""Error hierarchy for yamlsmith."""

from __future__ import annotations


class YAMLError(Exception):
    """Base error for all yamlsmith errors."""


class ScannerError(YAMLError):
    """Error during scanning/tokenization."""


class ParserError(YAMLError):
    """Error during parsing."""


class ComposerError(YAMLError):
    """Error during composition."""


class ConstructorError(YAMLError):
    """Error during construction."""


class EmitterError(YAMLError):
    """Error during emission."""
