"""YAML composer: builds a node graph from the event stream."""

from __future__ import annotations

from yamlsmith.nodes import MappingNode, Node, ScalarNode, SequenceNode
from yamlsmith.parser import (
    AliasEvent,
    DocumentEndEvent,
    DocumentStartEvent,
    Event,
    MappingEndEvent,
    MappingStartEvent,
    Parser,
    ScalarEvent,
    SequenceEndEvent,
    SequenceStartEvent,
    StreamEndEvent,
    StreamStartEvent,
)
from yamlsmith.scanner import Mark


class ComposerError(Exception):
    """Error during composition."""

    def __init__(self, message: str, mark: Mark | None = None) -> None:
        self.mark = mark
        super().__init__(message)


class Composer:
    """Builds a node graph from a YAML event stream."""

    def __init__(self, text: str) -> None:
        self._events = Parser(text).parse()
        self._index = 0
        self._anchors: dict[str, Node] = {}

    def compose_all(self) -> list[Node]:
        """Compose all documents and return a list of root nodes."""
        documents: list[Node] = []
        self._expect(StreamStartEvent)

        while not self._check(StreamEndEvent):
            doc = self._compose_document()
            if doc is not None:
                documents.append(doc)

        self._expect(StreamEndEvent)
        return documents

    def compose(self) -> Node | None:
        """Compose a single document."""
        docs = self.compose_all()
        return docs[0] if docs else None

    # -- Event helpers --

    def _peek(self) -> Event | None:
        if self._index >= len(self._events):
            return None
        return self._events[self._index]

    def _advance(self) -> Event:
        e = self._events[self._index]
        self._index += 1
        return e

    def _check(self, event_type: type[Event]) -> bool:
        e = self._peek()
        return isinstance(e, event_type)

    def _expect(self, event_type: type[Event]) -> Event:
        e = self._peek()
        if not isinstance(e, event_type):
            actual = type(e).__name__ if e else "EOF"
            raise ComposerError(
                f"Expected {event_type.__name__}, got {actual}"
            )
        return self._advance()

    # -- Composition --

    def _compose_document(self) -> Node | None:
        self._expect(DocumentStartEvent)
        self._anchors = {}

        node: Node | None = None
        if not self._check(DocumentEndEvent):
            node = self._compose_node()

        self._expect(DocumentEndEvent)
        return node

    def _compose_node(self) -> Node:
        e = self._peek()

        if isinstance(e, AliasEvent):
            self._advance()
            if e.anchor not in self._anchors:
                raise ComposerError(f"Undefined alias: {e.anchor}")
            return self._anchors[e.anchor]

        if isinstance(e, ScalarEvent):
            return self._compose_scalar()

        if isinstance(e, MappingStartEvent):
            return self._compose_mapping()

        if isinstance(e, SequenceStartEvent):
            return self._compose_sequence()

        actual = type(e).__name__ if e else "EOF"
        raise ComposerError(f"Unexpected event: {actual}")

    def _compose_scalar(self) -> ScalarNode:
        e = self._advance()
        assert isinstance(e, ScalarEvent)
        node = ScalarNode(
            tag=e.tag or "tag:yaml.org,2002:str",
            value=e.value,
            style=e.style,
            anchor=e.anchor,
            pre_comment=e.pre_comment,
            inline_comment=e.inline_comment,
        )
        if e.anchor:
            self._anchors[e.anchor] = node
        return node

    def _compose_mapping(self) -> MappingNode:
        e = self._advance()
        assert isinstance(e, MappingStartEvent)
        node = MappingNode(
            tag=e.tag or "tag:yaml.org,2002:map",
            flow_style=e.flow_style,
            anchor=e.anchor,
            pre_comment=e.pre_comment,
        )
        if e.anchor:
            self._anchors[e.anchor] = node

        while not self._check(MappingEndEvent):
            key = self._compose_node()
            value = self._compose_node()
            node.pairs.append((key, value))

        self._expect(MappingEndEvent)
        return node

    def _compose_sequence(self) -> SequenceNode:
        e = self._advance()
        assert isinstance(e, SequenceStartEvent)
        node = SequenceNode(
            tag=e.tag or "tag:yaml.org,2002:seq",
            flow_style=e.flow_style,
            anchor=e.anchor,
            pre_comment=e.pre_comment,
        )
        if e.anchor:
            self._anchors[e.anchor] = node

        while not self._check(SequenceEndEvent):
            node.items.append(self._compose_node())

        self._expect(SequenceEndEvent)
        return node


def compose(text: str) -> Node | None:
    """Convenience function to compose a single YAML document."""
    return Composer(text).compose()


def compose_all(text: str) -> list[Node]:
    """Convenience function to compose all YAML documents."""
    return Composer(text).compose_all()
