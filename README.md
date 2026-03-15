# yamlsmith

[![PyPI](https://img.shields.io/pypi/v/yamlsmith)](https://pypi.org/project/yamlsmith/)
[![Python](https://img.shields.io/pypi/pyversions/yamlsmith)](https://pypi.org/project/yamlsmith/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Typed](https://img.shields.io/badge/typing-strict-green)](https://mypy-lang.org/)

Round-trip YAML 1.2 library with comment preservation — a modern, drop-in replacement for ruamel.yaml.

Pure Python, zero dependencies, fully typed ([PEP 561](https://peps.python.org/pep-0561/)), Python 3.10+.

---

## Why yamlsmith?

[ruamel.yaml](https://pypi.org/project/ruamel.yaml/) has 155M+ monthly downloads and is the only production-ready Python library for round-trip YAML with comment preservation. But it carries significant risk:

- **Bus factor = 1.** Single maintainer with no governance structure.
- **PEP 625 crisis.** The namespace package naming may prevent continued PyPI uploads.
- **Hostile contribution model.** SourceForge/Mercurial hosting makes community contribution nearly impossible.
- **Failed fork.** ruyaml (pycontribs) was created to address these risks and itself stalled.

yamlsmith solves this: same round-trip semantics, modern codebase, zero dependencies, YAML 1.2 strict mode (no legacy boolean quirks from 1.1).

---

## Installation

```bash
pip install yamlsmith
```

---

## Quick Start

### Load and modify without losing comments

```python
from yamlsmith import load, dump

text = """\
# Database configuration
host: localhost
port: 5432  # default PostgreSQL port
enabled: true
"""

data = load(text)
data["port"] = 5433       # modify a value
data["timeout"] = 30      # add a new key

print(dump(data))
```

Output — comments preserved, structure intact:

```yaml
# Database configuration
host: localhost
port: 5433  # default PostgreSQL port
enabled: true
timeout: 30
```

### Multi-document streams

```python
from yamlsmith import load_all, dump_all

text = """\
# Document 1
name: alice
---
# Document 2
name: bob
"""

docs = load_all(text)
docs[0]["name"] = "ALICE"
print(dump_all(docs))
```

### File I/O

```python
from yamlsmith import YAML

yaml = YAML()

with open("config.yaml") as f:
    data = yaml.load(f)

data["version"] = "2.0"

with open("config.yaml", "w") as f:
    yaml.dump(data, f)
```

---

## API Reference

### Convenience functions

```python
from yamlsmith import load, dump, load_all, dump_all
```

| Function | Signature | Description |
|---|---|---|
| `load` | `(text: str \| bytes \| IO) → Any` | Load a single YAML document |
| `dump` | `(data: Any, stream: IO \| None = None) → str` | Dump to YAML string (optionally also write to stream) |
| `load_all` | `(text: str \| bytes \| IO) → list[Any]` | Load all documents from a multi-document stream |
| `dump_all` | `(data: list[Any], stream: IO \| None = None) → str` | Dump a list of documents separated by `---` |

All functions use round-trip mode: mappings and sequences are loaded as `RoundTripDict` / `RoundTripList` with comment metadata attached.

---

### `YAML` class

```python
from yamlsmith import YAML

yaml = YAML(indent=2, default_flow_style=False)
```

**Constructor parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `indent` | `int` | `2` | Indentation width for block mappings and sequences |
| `default_flow_style` | `bool` | `False` | Emit flow style (`{a: 1}`) instead of block style by default |

**Methods:**

| Method | Signature | Description |
|---|---|---|
| `load` | `(stream: str \| bytes \| IO) → Any` | Load a single YAML document |
| `dump` | `(data: Any, stream: IO \| None = None) → str` | Dump to YAML string, optionally also write to stream |
| `load_all` | `(stream: str \| bytes \| IO) → list[Any]` | Load all documents from a stream |
| `dump_all` | `(data: list[Any], stream: IO \| None = None) → str` | Dump multiple documents with `---` separators |

Streams may be `str`, `bytes`, or any file-like object with a `.read()` / `.write()` method.

---

### Round-trip types

When you load YAML, mappings and sequences are returned as round-trip types that carry comment metadata:

#### `RoundTripDict`

A `dict` subclass preserving insertion order and YAML comments.

```python
from yamlsmith import RoundTripDict

d = RoundTripDict({"a": 1, "b": 2})

# Attach comments to a key
d.set_comment("a", pre="# section header", inline="# inline note")

# Read comments back
pre, inline = d.get_comment("a")
```

| Method | Signature | Description |
|---|---|---|
| `set_comment` | `(key, *, pre=None, inline=None)` | Attach a pre-comment and/or inline comment to `key` |
| `get_comment` | `(key) → tuple[str \| None, str \| None]` | Return `(pre_comment, inline_comment)` for `key` |

#### `RoundTripList`

A `list` subclass preserving YAML comments per item.

```python
from yamlsmith import RoundTripList

lst = RoundTripList([1, 2, 3])

# Attach a comment to item at index 0
lst.set_item_comment(0, pre="# first item", inline="# note")

pre, inline = lst.get_item_comment(0)
```

| Method | Signature | Description |
|---|---|---|
| `set_item_comment` | `(index, *, pre=None, inline=None)` | Attach a pre-comment and/or inline comment to item `index` |
| `get_item_comment` | `(index) → tuple[str \| None, str \| None]` | Return `(pre_comment, inline_comment)` for item `index` |

#### `RoundTripScalar`

A wrapper for a scalar value that carries comment metadata and style information. Returned by the loader when a scalar has an inline comment or non-default quoting style.

```python
from yamlsmith import RoundTripScalar

s = RoundTripScalar(42, inline_comment="# answer", style="plain")
print(s.value)          # 42
print(s == 42)          # True — compares by .value
```

| Attribute | Type | Description |
|---|---|---|
| `value` | `Any` | The underlying Python value |
| `pre_comment` | `str \| None` | Comment line(s) before the scalar |
| `inline_comment` | `str \| None` | Comment after the value on the same line |
| `style` | `str \| None` | Scalar style: `plain`, `single`, `double`, `literal`, `folded` |
| `tag` | `str \| None` | Explicit YAML tag, or `None` for implicit resolution |

---

### Error types

All errors inherit from `YAMLError`.

```python
from yamlsmith import YAMLError, ScannerError, ParserError, ComposerError, ConstructorError, EmitterError

try:
    data = load("key: :")
except YAMLError as e:
    print(f"YAML error: {e}")
```

| Exception | Raised when |
|---|---|
| `YAMLError` | Base class for all yamlsmith errors |
| `ScannerError` | Invalid character or token in the input stream |
| `ParserError` | Structurally invalid YAML (bad nesting, missing values) |
| `ComposerError` | Undefined alias reference (`*anchor` without `&anchor`) |
| `ConstructorError` | Unknown YAML tag or type conversion failure |
| `EmitterError` | Serialization failure during emit |

---

## Comment Preservation

yamlsmith attaches comments to the nearest YAML node:

| Comment type | Example | Stored on |
|---|---|---|
| Pre-comment | `# header` on its own line before a key | the key's node |
| Inline comment | `value  # note` after a value | the value's node |
| Post-comment | trailing comment after a block | the block node |
| Document comment | comment before `---` or after `...` | the document node |

Comments survive load → modify → dump cycles as long as the node they are attached to is not replaced with a plain Python object. If you replace a `RoundTripDict` with a plain `dict`, its comments are discarded.

---

## YAML 1.2 Strict Mode

yamlsmith implements **YAML 1.2 only**. Legacy YAML 1.1 boolean strings are treated as plain strings:

| Expression | ruamel.yaml (1.1) | yamlsmith (1.2) |
|---|---|---|
| `yes` | `True` | `"yes"` |
| `no` | `False` | `"no"` |
| `on` | `True` | `"on"` |
| `off` | `False` | `"off"` |
| `true` | `True` | `True` |
| `false` | `False` | `False` |

Only `true`/`True`/`TRUE` and `false`/`False`/`FALSE` are recognised as booleans.

---

## Migration from ruamel.yaml

### Import changes

| ruamel.yaml | yamlsmith |
|---|---|
| `from ruamel.yaml import YAML` | `from yamlsmith import YAML` |
| `from ruamel.yaml.comments import CommentedMap` | `from yamlsmith import RoundTripDict` |
| `from ruamel.yaml.comments import CommentedSeq` | `from yamlsmith import RoundTripList` |

### API compatibility

The core `YAML` class API is identical:

```python
# ruamel.yaml
from ruamel.yaml import YAML
yaml = YAML()
data = yaml.load(stream)
yaml.dump(data, stream)

# yamlsmith — same calls
from yamlsmith import YAML
yaml = YAML()
data = yaml.load(stream)
yaml.dump(data, stream)
```

### Type name changes

| ruamel.yaml | yamlsmith | Notes |
|---|---|---|
| `CommentedMap` | `RoundTripDict` | Same dict semantics |
| `CommentedSeq` | `RoundTripList` | Same list semantics |
| `CommentedSeq` | `RoundTripList` | Same list semantics |
| `scalarstring.*` | `RoundTripScalar(style=...)` | Unified scalar wrapper |

### Behaviour differences

| Behaviour | ruamel.yaml | yamlsmith |
|---|---|---|
| YAML spec | 1.1 + 1.2 hybrid | 1.2 strict |
| `yes`/`no`/`on`/`off` | booleans | plain strings |
| `dump()` return value | `None` (writes to stream) | always returns `str` |
| Initialisation | `YAML(typ="rt")` for round-trip | round-trip is the only mode |
| Python object tags | `!!python/object` supported | not supported (safe by default) |

### dump() return value

ruamel.yaml's `dump()` writes to a stream and returns `None`. yamlsmith's `dump()` always returns the YAML string and optionally also writes to the stream if one is provided:

```python
# ruamel.yaml
import io
buf = io.StringIO()
yaml.dump(data, buf)
text = buf.getvalue()

# yamlsmith — simpler
text = yaml.dump(data)           # or:
text = yaml.dump(data, stream=f) # also writes to f
```

---

## Features

- YAML 1.2 strict mode (no legacy 1.1 boolean quirks)
- Round-trip comment preservation (pre, inline, post, document-level)
- Block and flow style preservation
- Anchor and alias support
- Multi-document streams (`load_all` / `dump_all`)
- Literal (`|`) and folded (`>`) block scalars
- All standard YAML types: `str`, `int`, `float`, `bool`, `null`, `datetime`, `binary`
- Octal (`0o777`) and hexadecimal (`0xFF`) integer literals
- `inf`, `-inf`, `.nan` float values
- Full type annotations, mypy `--strict` clean
- PEP 561 typed package
- Zero dependencies

---

## License

[MIT](LICENSE)
