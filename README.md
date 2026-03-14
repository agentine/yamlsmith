# yamlsmith

[![PyPI](https://img.shields.io/pypi/v/yamlsmith)](https://pypi.org/project/yamlsmith/)
[![Python](https://img.shields.io/pypi/pyversions/yamlsmith)](https://pypi.org/project/yamlsmith/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Round-trip YAML 1.2 library with comment preservation — a modern ruamel.yaml replacement.

Pure Python, zero dependencies, fully typed (PEP 561).

## Why yamlsmith?

ruamel.yaml has 155M+ monthly downloads but is hosted on SourceForge/Mercurial with a single maintainer and a nearly impossible contribution model. yamlsmith is a drop-in replacement: pure Python, zero dependencies, YAML 1.2 only (no legacy boolean quirks), and fully type-annotated.

## Installation

```bash
pip install yamlsmith
```

## Quick Start

```python
from yamlsmith import load, dump

# Load YAML with comments preserved
text = """
# Database config
host: localhost
port: 5432  # default PostgreSQL port
"""

data = load(text)
data["port"] = 5433
result = dump(data)
# Comments are preserved in the output
```

## API

### Convenience Functions

```python
from yamlsmith import load, dump, load_all, dump_all

data = load(text)           # Load single document
docs = load_all(text)       # Load multiple documents
text = dump(data)           # Dump to string
text = dump_all([d1, d2])   # Dump multiple documents
```

### YAML Class

```python
from yamlsmith import YAML

yaml = YAML(indent=2, default_flow_style=False)

data = yaml.load(text)
yaml.dump(data, stream=file)
docs = yaml.load_all(text)
yaml.dump_all(docs, stream=file)
```

**Constructor parameters:**

| Parameter | Default | Description |
|---|---|---|
| `indent` | `2` | Indentation width for block sequences and mappings |
| `default_flow_style` | `False` | Use flow style (`{a: 1}`) instead of block style by default |

Streams can be `str`, `bytes`, or file-like objects.

### Round-Trip Types

- `RoundTripDict` — dict subclass preserving key order and comments
- `RoundTripList` — list subclass preserving item comments
- `RoundTripScalar` — scalar wrapper preserving inline comments and style

### Error Types

All errors inherit from `YAMLError`:

- `ScannerError` — tokenization errors
- `ParserError` — parsing errors
- `ComposerError` — composition errors (e.g., undefined aliases)
- `ConstructorError` — type construction errors
- `EmitterError` — serialization errors

## Migration from ruamel.yaml

| ruamel.yaml | yamlsmith |
|---|---|
| `from ruamel.yaml import YAML` | `from yamlsmith import YAML` |
| `yaml = YAML()` | `yaml = YAML()` |
| `data = yaml.load(stream)` | `data = yaml.load(stream)` |
| `yaml.dump(data, stream)` | `yaml.dump(data, stream)` |
| `CommentedMap` | `RoundTripDict` |
| `CommentedSeq` | `RoundTripList` |

## Features

- YAML 1.2 only (no legacy 1.1 boolean quirks)
- Comment preservation through load/modify/dump cycles
- Block and flow style preservation
- Anchor/alias support
- Multi-document streams
- Literal (`|`) and folded (`>`) block scalars
- Full type annotations (mypy --strict clean)

## License

MIT
