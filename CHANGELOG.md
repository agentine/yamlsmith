# Changelog

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
