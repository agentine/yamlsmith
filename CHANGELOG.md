# Changelog

## [Unreleased]

### Fixed
- Pre-comment placement: pre-comments (standalone comment lines before a key) were incorrectly emitted as inline comments on the previous key line; now preserved on their own line
- Integer/float/bool round-trip quoting: plain scalars like `5432` were quoted after load→dump due to stale string tag stored in `RoundTripScalar`; constructor now stores `None` tag for implicitly resolved non-string types so the representer derives the correct tag from the Python type
- Plain scalar quoting: unquoted scalars that resolve to non-string types no longer get spurious quotes on re-emit
- Type annotation for `stored_tag` in constructor to satisfy mypy strict mode

## v0.1.0 (2026-03-14)

Initial release.

- YAML 1.2 scanner/tokenizer with comment metadata
- Event-stream parser
- Node graph composer with anchor/alias resolution
- Constructor: YAML nodes to Python objects (str, int, float, bool, None, datetime, bytes)
- Representer: Python objects to YAML nodes
- Emitter with comment preservation and block/flow style support
- Round-trip types: RoundTripDict, RoundTripList, RoundTripScalar
- Public API: YAML class + load/dump/load_all/dump_all convenience functions
- Error hierarchy: YAMLError, ScannerError, ParserError, ComposerError, ConstructorError, EmitterError
- PEP 561 typed package
- Python 3.10+ support
