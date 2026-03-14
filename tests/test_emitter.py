"""Tests for the yamlsmith emitter."""

from __future__ import annotations

from yamlsmith.composer import compose
from yamlsmith.emitter import Emitter, emit, emit_all
from yamlsmith.nodes import MappingNode, ScalarNode, SequenceNode


class TestScalarEmission:
    def test_plain_scalar(self) -> None:
        node = ScalarNode(tag="tag:yaml.org,2002:str", value="hello")
        result = emit(node)
        assert result == "hello"

    def test_integer_scalar(self) -> None:
        node = ScalarNode(tag="tag:yaml.org,2002:int", value="42")
        result = emit(node)
        assert result == "42"

    def test_single_quoted(self) -> None:
        node = ScalarNode(
            tag="tag:yaml.org,2002:str", value="hello", style="single"
        )
        result = emit(node)
        assert result == "'hello'"

    def test_double_quoted(self) -> None:
        node = ScalarNode(
            tag="tag:yaml.org,2002:str", value="hello", style="double"
        )
        result = emit(node)
        assert result == '"hello"'

    def test_double_quoted_escapes(self) -> None:
        node = ScalarNode(
            tag="tag:yaml.org,2002:str",
            value="line1\nline2",
            style="double",
        )
        result = emit(node)
        assert result == '"line1\\nline2"'

    def test_literal_block(self) -> None:
        node = ScalarNode(
            tag="tag:yaml.org,2002:str",
            value="line1\nline2\n",
            style="literal",
        )
        result = emit(node)
        assert result.startswith("|")
        assert "line1" in result
        assert "line2" in result

    def test_folded_block(self) -> None:
        node = ScalarNode(
            tag="tag:yaml.org,2002:str",
            value="line1\nline2\n",
            style="folded",
        )
        result = emit(node)
        assert result.startswith(">")

    def test_auto_quoting_needed(self) -> None:
        node = ScalarNode(tag="tag:yaml.org,2002:str", value="true")
        result = emit(node)
        assert result == '"true"'

    def test_auto_quoting_numeric(self) -> None:
        node = ScalarNode(tag="tag:yaml.org,2002:str", value="123")
        result = emit(node)
        assert "123" in result
        # Should be quoted since it looks like an int.
        assert result in ('"123"', "'123'")

    def test_empty_value_quoted(self) -> None:
        node = ScalarNode(tag="tag:yaml.org,2002:str", value="")
        result = emit(node)
        assert result in ('""', "''")


class TestMappingEmission:
    def test_simple_mapping(self) -> None:
        node = MappingNode(
            tag="tag:yaml.org,2002:map",
            pairs=[
                (
                    ScalarNode(tag="tag:yaml.org,2002:str", value="key"),
                    ScalarNode(tag="tag:yaml.org,2002:str", value="value"),
                ),
            ],
        )
        result = emit(node)
        assert "key: value" in result

    def test_multi_key_mapping(self) -> None:
        node = MappingNode(
            tag="tag:yaml.org,2002:map",
            pairs=[
                (
                    ScalarNode(tag="tag:yaml.org,2002:str", value="a"),
                    ScalarNode(tag="tag:yaml.org,2002:int", value="1"),
                ),
                (
                    ScalarNode(tag="tag:yaml.org,2002:str", value="b"),
                    ScalarNode(tag="tag:yaml.org,2002:int", value="2"),
                ),
            ],
        )
        result = emit(node)
        assert "a: 1" in result
        assert "b: 2" in result

    def test_nested_mapping(self) -> None:
        inner = MappingNode(
            tag="tag:yaml.org,2002:map",
            pairs=[
                (
                    ScalarNode(tag="tag:yaml.org,2002:str", value="b"),
                    ScalarNode(tag="tag:yaml.org,2002:str", value="c"),
                ),
            ],
        )
        node = MappingNode(
            tag="tag:yaml.org,2002:map",
            pairs=[
                (
                    ScalarNode(tag="tag:yaml.org,2002:str", value="a"),
                    inner,
                ),
            ],
        )
        result = emit(node)
        assert "a:" in result
        assert "b: c" in result

    def test_flow_mapping(self) -> None:
        node = MappingNode(
            tag="tag:yaml.org,2002:map",
            pairs=[
                (
                    ScalarNode(tag="tag:yaml.org,2002:str", value="a"),
                    ScalarNode(tag="tag:yaml.org,2002:int", value="1"),
                ),
            ],
            flow_style=True,
        )
        result = emit(node)
        assert result == "{a: 1}"


class TestSequenceEmission:
    def test_simple_sequence(self) -> None:
        node = SequenceNode(
            tag="tag:yaml.org,2002:seq",
            items=[
                ScalarNode(tag="tag:yaml.org,2002:str", value="a"),
                ScalarNode(tag="tag:yaml.org,2002:str", value="b"),
            ],
        )
        result = emit(node)
        assert "- a" in result
        assert "- b" in result

    def test_flow_sequence(self) -> None:
        node = SequenceNode(
            tag="tag:yaml.org,2002:seq",
            items=[
                ScalarNode(tag="tag:yaml.org,2002:int", value="1"),
                ScalarNode(tag="tag:yaml.org,2002:int", value="2"),
            ],
            flow_style=True,
        )
        result = emit(node)
        assert result == "[1, 2]"


class TestCommentPreservation:
    def test_inline_comment(self) -> None:
        node = ScalarNode(
            tag="tag:yaml.org,2002:str",
            value="value",
            inline_comment=" my comment",
        )
        result = emit(node)
        assert "value # my comment" in result

    def test_pre_comment(self) -> None:
        node = MappingNode(
            tag="tag:yaml.org,2002:map",
            pre_comment=" header comment",
            pairs=[
                (
                    ScalarNode(tag="tag:yaml.org,2002:str", value="key"),
                    ScalarNode(tag="tag:yaml.org,2002:str", value="val"),
                ),
            ],
        )
        result = emit(node)
        assert "# header comment" in result

    def test_mapping_with_inline_comments(self) -> None:
        node = MappingNode(
            tag="tag:yaml.org,2002:map",
            pairs=[
                (
                    ScalarNode(tag="tag:yaml.org,2002:str", value="a"),
                    ScalarNode(
                        tag="tag:yaml.org,2002:int",
                        value="1",
                        inline_comment=" first",
                    ),
                ),
                (
                    ScalarNode(tag="tag:yaml.org,2002:str", value="b"),
                    ScalarNode(
                        tag="tag:yaml.org,2002:int",
                        value="2",
                        inline_comment=" second",
                    ),
                ),
            ],
        )
        result = emit(node)
        assert "1 # first" in result
        assert "2 # second" in result


class TestAnchorAlias:
    def test_anchor_emission(self) -> None:
        node = ScalarNode(
            tag="tag:yaml.org,2002:str",
            value="hello",
            anchor="ref",
        )
        result = emit(node)
        assert "&ref hello" in result


class TestDocumentEmission:
    def test_explicit_start(self) -> None:
        node = ScalarNode(tag="tag:yaml.org,2002:str", value="hello")
        result = Emitter().emit_document(node, explicit_start=True)
        assert result.startswith("---")

    def test_explicit_end(self) -> None:
        node = ScalarNode(tag="tag:yaml.org,2002:str", value="hello")
        result = Emitter().emit_document(
            node, explicit_start=True, explicit_end=True
        )
        assert "..." in result

    def test_multi_document(self) -> None:
        nodes = [
            ScalarNode(tag="tag:yaml.org,2002:str", value="foo"),
            ScalarNode(tag="tag:yaml.org,2002:str", value="bar"),
        ]
        result = emit_all(nodes)
        assert result.count("---") == 2
        assert "foo" in result
        assert "bar" in result


class TestRoundTrip:
    def test_mapping_roundtrip(self) -> None:
        text = "a: 1\nb: 2\n"
        node = compose(text)
        assert node is not None
        result = emit(node)
        assert "a:" in result
        assert "b:" in result

    def test_sequence_roundtrip(self) -> None:
        text = "- a\n- b\n- c\n"
        node = compose(text)
        assert node is not None
        result = emit(node)
        assert "- a" in result
        assert "- b" in result
        assert "- c" in result

    def test_flow_mapping_roundtrip(self) -> None:
        text = "{a: 1, b: 2}"
        node = compose(text)
        assert node is not None
        result = emit(node)
        assert "{" in result
        assert "}" in result

    def test_flow_sequence_roundtrip(self) -> None:
        text = "[1, 2, 3]"
        node = compose(text)
        assert node is not None
        result = emit(node)
        assert "[" in result
        assert "]" in result

    def test_comment_roundtrip(self) -> None:
        text = "a: 1 # comment\nb: 2\n"
        node = compose(text)
        assert node is not None
        result = emit(node)
        assert "# comment" in result

    def test_nested_mapping_roundtrip(self) -> None:
        text = "outer:\n  inner: value\n"
        node = compose(text)
        assert node is not None
        result = emit(node)
        assert "outer:" in result
        assert "inner: value" in result
