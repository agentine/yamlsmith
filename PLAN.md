# yamlsmith — Round-Trip YAML 1.2 Library for Python

## Target Library

**ruamel.yaml** — the only production-ready Python library for round-trip YAML editing with comment preservation.

| Metric | Value |
|--------|-------|
| Downloads | ~155M/month |
| Maintainers | 1 (Anthon van der Neut) |
| Dependent packages | 3,080 |
| Latest release | v0.19.1 (Jan 2026) |
| Hosting | SourceForge/Mercurial |
| Community fork | ruyaml (stalled, no releases 12+ months) |

### Why Replace

- **Bus factor = 1.** Single maintainer with no governance structure.
- **PEP 625 crisis.** Maintainer signaled potential inability to continue uploading to PyPI due to namespace package naming requirements.
- **Hostile contribution model.** SourceForge/Mercurial hosting makes PRs/community contribution nearly impossible.
- **Failed fork.** ruyaml (pycontribs) was created specifically to address these risks and has itself stalled.
- **No alternative.** PyYAML does not support round-trip editing or comment preservation. There is no production-ready substitute.

## Package Name

**yamlsmith** — verified available on PyPI.

## Scope

A modern Python library for YAML 1.2 parsing and emitting with full round-trip fidelity: comments, ordering, formatting, and whitespace are preserved through load/modify/dump cycles.

## Architecture

### Core Components

1. **Scanner/Tokenizer** — Stream-based YAML 1.2 tokenizer that captures comments and whitespace as metadata tokens.
2. **Parser** — Produces an event stream (similar to SAX) from tokens, attaching comment metadata.
3. **Composer** — Builds a document tree (node graph) from the event stream, with anchor/alias resolution.
4. **Representer** — Maps Python objects to YAML nodes, preserving type information.
5. **Constructor** — Maps YAML nodes back to Python objects.
6. **Emitter** — Serializes the node graph back to YAML text, replaying preserved comments and formatting.
7. **Public API** — Simple `load()`, `dump()`, `load_all()`, `dump_all()` functions plus a `YAML` class for configuration.

### Key Design Decisions

- **Pure Python, zero dependencies.** No C extensions, no Rust. Simple `pip install`.
- **YAML 1.2 only.** No YAML 1.1 legacy support (boolean `yes/no/on/off` quirks).
- **Round-trip by default.** The primary API preserves comments and formatting. Safe-load semantics by default (no arbitrary Python object construction).
- **Type-annotated.** Full PEP 561 type stubs, mypy-clean.
- **Python 3.10+.**

### API Surface

```python
from yamlsmith import YAML

yaml = YAML()

# Round-trip load and dump
data = yaml.load(text)
yaml.dump(data, stream)

# Convenience functions
from yamlsmith import load, dump, load_all, dump_all

data = load(text)           # round-trip mode
text = dump(data)           # preserves comments
```

### Comment Preservation Strategy

Comments attach to the nearest node:
- **Pre-comments:** Lines before a mapping key or sequence item.
- **Inline comments:** `# comment` on the same line as a value.
- **Post-comments:** Trailing comments after a block.
- **Document-level:** Comments before `---` or after `...`.

Comments are stored as metadata on the node objects, not in a separate side-channel.

## Deliverables

1. Core YAML 1.2 scanner, parser, composer, emitter with comment preservation
2. Python object construction/representation (dict, list, str, int, float, bool, None, datetime, binary)
3. Round-trip API (`YAML` class + convenience functions)
4. Anchor/alias support
5. Multi-document support (`load_all` / `dump_all`)
6. Flow style vs block style preservation
7. Comprehensive test suite (YAML Test Suite compliance)
8. PyPI package with PEP 561 type stubs
9. README with migration guide from ruamel.yaml

## Non-Goals (v1)

- YAML 1.1 compatibility mode
- Custom Python object serialization (no `!!python/object`)
- C extension acceleration
- Schema validation
