# Changelog

All notable changes to yamlsmith are documented here.

## [Unreleased]

## v0.1.1 (2026-03-15)

### Fixed

- **Pre-comment placement:** Pre-comments (standalone comment lines before a key) were incorrectly emitted as inline comments on the previous key line. They are now preserved on their own line above the key.
- **Integer/float/bool round-trip quoting:** Plain scalars such as `5432` were quoted after a load→dump cycle. The constructor now stores `None` as the tag for implicitly resolved non-string types so the representer derives the correct tag from the Python type rather than a stale string tag stored in `RoundTripScalar`.
- **Plain scalar quoting:** Unquoted scalars that resolve to non-string types no longer receive spurious quotes on re-emit.

## v0.1.0 (2026-03-14)

Initial release.

### Added

- YAML 1.2 scanner/tokenizer with comment metadata
- Event-stream parser
- Node graph composer with anchor/alias resolution
- Constructor: YAML nodes → Python objects (`str`, `int`, `float`, `bool`, `None`, `datetime`, `bytes`)
- Representer: Python objects → YAML nodes
- Emitter with comment preservation and block/flow style support
- Round-trip types: `RoundTripDict`, `RoundTripList`, `RoundTripScalar`
- Public API: `YAML` class and `load` / `dump` / `load_all` / `dump_all` convenience functions
- Error hierarchy: `YAMLError`, `ScannerError`, `ParserError`, `ComposerError`, `ConstructorError`, `EmitterError`
- PEP 561 typed package (`py.typed` marker)
- Python 3.10+ support
- Zero runtime dependencies
