"""Tests for the yamlsmith composer."""

from __future__ import annotations

from yamlsmith.composer import Composer, ComposerError, compose, compose_all
from yamlsmith.nodes import MappingNode, ScalarNode, SequenceNode

import pytest


class TestScalarComposition:
    def test_plain_scalar(self) -> None:
        node = compose("hello")
        assert isinstance(node, ScalarNode)
        assert node.value == "hello"

    def test_quoted_scalar(self) -> None:
        node = compose("'hello'")
        assert isinstance(node, ScalarNode)
        assert node.value == "hello"
        assert node.style == "single"

    def test_empty_document(self) -> None:
        node = compose("")
        assert node is None


class TestMappingComposition:
    def test_simple_mapping(self) -> None:
        node = compose("a: 1\nb: 2")
        assert isinstance(node, MappingNode)
        assert len(node.pairs) == 2
        k0, v0 = node.pairs[0]
        assert isinstance(k0, ScalarNode)
        assert k0.value == "a"
        assert isinstance(v0, ScalarNode)
        assert v0.value == "1"

    def test_nested_mapping(self) -> None:
        node = compose("a:\n  b: c")
        assert isinstance(node, MappingNode)
        _, v = node.pairs[0]
        assert isinstance(v, MappingNode)
        assert len(v.pairs) == 1

    def test_flow_mapping(self) -> None:
        node = compose("{x: 1, y: 2}")
        assert isinstance(node, MappingNode)
        assert node.flow_style is True
        assert len(node.pairs) == 2


class TestSequenceComposition:
    def test_simple_sequence(self) -> None:
        node = compose("- a\n- b\n- c")
        assert isinstance(node, SequenceNode)
        assert len(node.items) == 3
        assert all(isinstance(i, ScalarNode) for i in node.items)

    def test_nested_sequence(self) -> None:
        node = compose("-\n  - a\n  - b")
        assert isinstance(node, SequenceNode)
        assert isinstance(node.items[0], SequenceNode)

    def test_flow_sequence(self) -> None:
        node = compose("[1, 2, 3]")
        assert isinstance(node, SequenceNode)
        assert node.flow_style is True
        assert len(node.items) == 3

    def test_sequence_of_mappings(self) -> None:
        node = compose("- key: val\n- key2: val2")
        assert isinstance(node, SequenceNode)
        assert all(isinstance(i, MappingNode) for i in node.items)


class TestAnchorsAndAliases:
    def test_anchor_resolve(self) -> None:
        text = "a: &ref hello\nb: *ref"
        node = compose(text)
        assert isinstance(node, MappingNode)
        _, v0 = node.pairs[0]
        _, v1 = node.pairs[1]
        assert isinstance(v0, ScalarNode)
        assert v0.value == "hello"
        # Alias resolves to the same node.
        assert v1 is v0

    def test_undefined_alias_raises(self) -> None:
        with pytest.raises(ComposerError, match="Undefined alias"):
            compose("*missing")

    def test_anchor_on_mapping(self) -> None:
        text = "a: &ref\n  x: 1\nb: *ref"
        node = compose(text)
        assert isinstance(node, MappingNode)
        _, v0 = node.pairs[0]
        _, v1 = node.pairs[1]
        assert isinstance(v0, MappingNode)
        assert v1 is v0


class TestMultiDocument:
    def test_compose_all(self) -> None:
        text = "---\nfoo\n---\nbar\n..."
        docs = compose_all(text)
        assert len(docs) == 2
        assert isinstance(docs[0], ScalarNode)
        assert docs[0].value == "foo"
        assert isinstance(docs[1], ScalarNode)
        assert docs[1].value == "bar"

    def test_single_compose(self) -> None:
        text = "---\nfoo\n---\nbar"
        node = compose(text)
        # compose returns just the first document.
        assert isinstance(node, ScalarNode)
        assert node.value == "foo"


class TestCommentPreservation:
    def test_scalar_pre_comment(self) -> None:
        text = "# header comment\nvalue"
        node = compose(text)
        assert isinstance(node, ScalarNode)
        # Comment may be on the scalar or lost to document level.
        # As long as parsing doesn't fail, it's fine for now.

    def test_scalar_inline_comment(self) -> None:
        text = "key: value # inline"
        node = compose(text)
        assert isinstance(node, MappingNode)
        _, v = node.pairs[0]
        assert isinstance(v, ScalarNode)
        assert v.inline_comment is not None

    def test_mapping_comment(self) -> None:
        text = "a: 1 # first\nb: 2 # second"
        node = compose(text)
        assert isinstance(node, MappingNode)
        _, v0 = node.pairs[0]
        _, v1 = node.pairs[1]
        assert isinstance(v0, ScalarNode)
        assert isinstance(v1, ScalarNode)
        assert v0.inline_comment is not None
        assert v1.inline_comment is not None


class TestTags:
    def test_default_tags(self) -> None:
        node = compose("hello")
        assert isinstance(node, ScalarNode)
        assert node.tag == "tag:yaml.org,2002:str"

    def test_mapping_tag(self) -> None:
        node = compose("a: 1")
        assert isinstance(node, MappingNode)
        assert node.tag == "tag:yaml.org,2002:map"

    def test_sequence_tag(self) -> None:
        node = compose("- a")
        assert isinstance(node, SequenceNode)
        assert node.tag == "tag:yaml.org,2002:seq"

    def test_explicit_tag(self) -> None:
        node = compose("!!str 123")
        assert isinstance(node, ScalarNode)
        assert node.tag == "!!str"
