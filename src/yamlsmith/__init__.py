"""yamlsmith — Round-trip YAML 1.2 library with comment preservation."""

from yamlsmith.api import YAML, dump, dump_all, load, load_all
from yamlsmith.errors import (
    ComposerError,
    ConstructorError,
    EmitterError,
    ParserError,
    ScannerError,
    YAMLError,
)
from yamlsmith.roundtrip import RoundTripDict, RoundTripList, RoundTripScalar

__version__ = "0.1.0"

__all__ = [
    "YAML",
    "ComposerError",
    "ConstructorError",
    "EmitterError",
    "ParserError",
    "RoundTripDict",
    "RoundTripList",
    "RoundTripScalar",
    "ScannerError",
    "YAMLError",
    "__version__",
    "dump",
    "dump_all",
    "load",
    "load_all",
]
