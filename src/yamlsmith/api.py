"""Public API for yamlsmith: YAML class and convenience functions."""

from __future__ import annotations

from typing import Any, TextIO

from yamlsmith.composer import Composer
from yamlsmith.constructor import Constructor
from yamlsmith.emitter import Emitter
from yamlsmith.nodes import Node
from yamlsmith.representer import Representer


class YAML:
    """Main YAML class for loading and dumping with round-trip fidelity."""

    def __init__(
        self,
        *,
        indent: int = 2,
        default_flow_style: bool = False,
    ) -> None:
        self._indent = indent
        self._default_flow_style = default_flow_style
        self._constructor = Constructor()
        self._representer = Representer()

    def load(self, stream: str | bytes | TextIO) -> Any:
        """Load a single YAML document.

        Returns RoundTripDict/RoundTripList for mappings/sequences
        (comments preserved), or a scalar value.
        """
        text = self._read_stream(stream)
        composer = Composer(text)
        node = composer.compose()
        if node is None:
            return None
        return self._constructor.construct(node)

    def load_all(self, stream: str | bytes | TextIO) -> list[Any]:
        """Load all YAML documents from a stream."""
        text = self._read_stream(stream)
        composer = Composer(text)
        nodes = composer.compose_all()
        return [self._constructor.construct(n) for n in nodes]

    def dump(
        self,
        data: Any,
        stream: TextIO | None = None,
    ) -> str:
        """Dump a Python object to YAML text.

        If stream is provided, writes to it and returns the text.
        Accepts RoundTripDict/RoundTripList (replays comments).
        """
        node = self._representer.represent(data)
        emitter = Emitter(
            stream=stream,
            indent=self._indent,
            default_flow_style=self._default_flow_style,
        )
        text = emitter.emit(node)
        if not text.endswith("\n"):
            text += "\n"
            if stream is not None:
                stream.write("\n")
        return text

    def dump_all(
        self,
        data: list[Any],
        stream: TextIO | None = None,
    ) -> str:
        """Dump multiple documents to YAML text."""
        nodes: list[Node] = [self._representer.represent(d) for d in data]
        emitter = Emitter(
            stream=stream,
            indent=self._indent,
            default_flow_style=self._default_flow_style,
        )
        text = emitter.emit_all(nodes)
        return text

    @staticmethod
    def _read_stream(stream: str | bytes | TextIO) -> str:
        if isinstance(stream, bytes):
            return stream.decode("utf-8")
        if isinstance(stream, str):
            return stream
        return stream.read()


# -- Convenience functions --


def load(text: str | bytes | TextIO) -> Any:
    """Load a single YAML document (round-trip mode)."""
    return YAML().load(text)


def dump(data: Any, stream: TextIO | None = None) -> str:
    """Dump a Python object to YAML text."""
    return YAML().dump(data, stream=stream)


def load_all(text: str | bytes | TextIO) -> list[Any]:
    """Load all YAML documents from a stream."""
    return YAML().load_all(text)


def dump_all(data: list[Any], stream: TextIO | None = None) -> str:
    """Dump multiple documents to YAML text."""
    return YAML().dump_all(data, stream=stream)
