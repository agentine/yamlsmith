"""Tests for the yamlsmith parser."""

from __future__ import annotations

from yamlsmith.parser import (
    AliasEvent,
    DocumentEndEvent,
    DocumentStartEvent,
    MappingEndEvent,
    MappingStartEvent,
    ScalarEvent,
    SequenceEndEvent,
    SequenceStartEvent,
    StreamEndEvent,
    StreamStartEvent,
    parse,
)


def event_types(text: str) -> list[type[object]]:
    """Return just the event types from parsing text."""
    return [type(e) for e in parse(text)]


class TestStreamAndDocument:
    def test_empty_stream(self) -> None:
        types = event_types("")
        assert types[0] == StreamStartEvent
        assert types[-1] == StreamEndEvent

    def test_document_markers(self) -> None:
        types = event_types("---\nfoo\n...")
        assert DocumentStartEvent in types
        assert DocumentEndEvent in types

    def test_multi_document(self) -> None:
        types = event_types("---\nfoo\n---\nbar\n...")
        assert types.count(DocumentStartEvent) == 2
        assert types.count(DocumentEndEvent) == 2


class TestScalarEvents:
    def test_plain_scalar(self) -> None:
        events = parse("hello")
        scalars = [e for e in events if isinstance(e, ScalarEvent)]
        assert len(scalars) == 1
        assert scalars[0].value == "hello"

    def test_quoted_scalar(self) -> None:
        events = parse("'hello'")
        scalars = [e for e in events if isinstance(e, ScalarEvent)]
        assert scalars[0].value == "hello"
        assert scalars[0].style == "single"

    def test_scalar_with_comment(self) -> None:
        events = parse("value # comment")
        scalars = [e for e in events if isinstance(e, ScalarEvent)]
        assert scalars[0].value == "value"
        assert scalars[0].inline_comment is not None


class TestMappingEvents:
    def test_simple_mapping(self) -> None:
        types = event_types("key: value")
        assert MappingStartEvent in types
        assert MappingEndEvent in types

    def test_nested_mapping(self) -> None:
        types = event_types("a:\n  b: c")
        assert types.count(MappingStartEvent) == 2
        assert types.count(MappingEndEvent) == 2

    def test_mapping_values(self) -> None:
        events = parse("a: 1\nb: 2")
        scalars = [e for e in events if isinstance(e, ScalarEvent)]
        vals = [s.value for s in scalars]
        assert vals == ["a", "1", "b", "2"]

    def test_flow_mapping(self) -> None:
        events = parse("{a: 1, b: 2}")
        mappings = [e for e in events if isinstance(e, MappingStartEvent)]
        assert len(mappings) == 1
        assert mappings[0].flow_style is True


class TestSequenceEvents:
    def test_block_sequence(self) -> None:
        types = event_types("- a\n- b")
        assert SequenceStartEvent in types
        assert SequenceEndEvent in types

    def test_sequence_values(self) -> None:
        events = parse("- a\n- b\n- c")
        scalars = [e for e in events if isinstance(e, ScalarEvent)]
        vals = [s.value for s in scalars]
        assert vals == ["a", "b", "c"]

    def test_flow_sequence(self) -> None:
        events = parse("[1, 2, 3]")
        seqs = [e for e in events if isinstance(e, SequenceStartEvent)]
        assert len(seqs) == 1
        assert seqs[0].flow_style is True

    def test_nested_sequence(self) -> None:
        types = event_types("-\n  - a\n  - b")
        assert types.count(SequenceStartEvent) == 2


class TestCommentMetadata:
    def test_pre_comment_preserved(self) -> None:
        text = "# header\nkey: value"
        events = parse(text)
        scalars = [e for e in events if isinstance(e, ScalarEvent)]
        # The pre_comment might be on the key or value
        has_comment = any(s.pre_comment is not None for s in scalars)
        # Or on the mapping
        mappings = [e for e in events if isinstance(e, MappingStartEvent)]
        has_map_comment = any(m.pre_comment is not None for m in mappings)
        assert has_comment or has_map_comment

    def test_inline_comment_preserved(self) -> None:
        events = parse("key: value # inline")
        scalars = [e for e in events if isinstance(e, ScalarEvent)]
        has_inline = any(s.inline_comment is not None for s in scalars)
        assert has_inline


class TestAnchorsAndAliases:
    def test_anchor_on_scalar(self) -> None:
        events = parse("&ref value")
        scalars = [e for e in events if isinstance(e, ScalarEvent)]
        assert scalars[0].anchor == "ref"

    def test_alias_event(self) -> None:
        events = parse("a: &ref value\nb: *ref")
        aliases = [e for e in events if isinstance(e, AliasEvent)]
        assert len(aliases) == 1
        assert aliases[0].anchor == "ref"


class TestExplicitKeys:
    def test_explicit_key(self) -> None:
        types = event_types("? key\n: value")
        assert MappingStartEvent in types
        scalars_events = parse("? key\n: value")
        scalars = [
            e for e in scalars_events if isinstance(e, ScalarEvent)
        ]
        vals = [s.value for s in scalars]
        assert "key" in vals
        assert "value" in vals
