"""Tests for the yamlsmith scanner/tokenizer."""

from __future__ import annotations

import pytest

from yamlsmith.scanner import (
    Scanner,
    ScannerError,
    ScalarStyle,
    Token,
    TokenType,
    scan,
)


def token_types(text: str) -> list[TokenType]:
    """Return just the token types from scanning text."""
    return [t.type for t in scan(text)]


def token_values(text: str) -> list[tuple[TokenType, str]]:
    """Return (type, value) pairs from scanning text."""
    return [(t.type, t.value) for t in scan(text)]


class TestBasicStructure:
    def test_empty_stream(self) -> None:
        types = token_types("")
        assert types == [TokenType.STREAM_START, TokenType.STREAM_END]

    def test_whitespace_only(self) -> None:
        types = token_types("   \n\n  ")
        assert types == [TokenType.STREAM_START, TokenType.STREAM_END]

    def test_document_start(self) -> None:
        types = token_types("---")
        assert TokenType.DOCUMENT_START in types

    def test_document_end(self) -> None:
        types = token_types("...")
        assert TokenType.DOCUMENT_END in types

    def test_multi_document(self) -> None:
        text = "---\nfoo\n---\nbar\n..."
        types = token_types(text)
        assert types.count(TokenType.DOCUMENT_START) == 2
        assert types.count(TokenType.DOCUMENT_END) == 1
        scalars = [t.value for t in scan(text) if t.type == TokenType.SCALAR]
        assert scalars == ["foo", "bar"]


class TestScalars:
    def test_plain_scalar(self) -> None:
        tokens = scan("hello")
        scalars = [t for t in tokens if t.type == TokenType.SCALAR]
        assert len(scalars) == 1
        assert scalars[0].value == "hello"
        assert scalars[0].style == ScalarStyle.PLAIN

    def test_single_quoted(self) -> None:
        tokens = scan("'hello world'")
        scalars = [t for t in tokens if t.type == TokenType.SCALAR]
        assert len(scalars) == 1
        assert scalars[0].value == "hello world"
        assert scalars[0].style == ScalarStyle.SINGLE_QUOTED

    def test_single_quoted_escape(self) -> None:
        tokens = scan("'it''s'")
        scalars = [t for t in tokens if t.type == TokenType.SCALAR]
        assert scalars[0].value == "it's"

    def test_double_quoted(self) -> None:
        tokens = scan('"hello world"')
        scalars = [t for t in tokens if t.type == TokenType.SCALAR]
        assert len(scalars) == 1
        assert scalars[0].value == "hello world"
        assert scalars[0].style == ScalarStyle.DOUBLE_QUOTED

    def test_double_quoted_escapes(self) -> None:
        tokens = scan(r'"hello\nworld"')
        scalars = [t for t in tokens if t.type == TokenType.SCALAR]
        assert scalars[0].value == "hello\nworld"

    def test_double_quoted_unicode(self) -> None:
        tokens = scan(r'"caf\u00e9"')
        scalars = [t for t in tokens if t.type == TokenType.SCALAR]
        assert scalars[0].value == "caf\u00e9"

    def test_literal_block(self) -> None:
        text = "|\n  line1\n  line2\n"
        tokens = scan(text)
        scalars = [t for t in tokens if t.type == TokenType.SCALAR]
        assert len(scalars) == 1
        assert scalars[0].style == ScalarStyle.LITERAL
        assert "line1" in scalars[0].value
        assert "line2" in scalars[0].value

    def test_folded_block(self) -> None:
        text = ">\n  line1\n  line2\n"
        tokens = scan(text)
        scalars = [t for t in tokens if t.type == TokenType.SCALAR]
        assert len(scalars) == 1
        assert scalars[0].style == ScalarStyle.FOLDED

    def test_literal_strip(self) -> None:
        text = "|-\n  line1\n  line2\n"
        tokens = scan(text)
        scalars = [t for t in tokens if t.type == TokenType.SCALAR]
        assert not scalars[0].value.endswith("\n")

    def test_literal_keep(self) -> None:
        text = "|+\n  line1\n  line2\n"
        tokens = scan(text)
        scalars = [t for t in tokens if t.type == TokenType.SCALAR]
        assert scalars[0].value.endswith("\n")


class TestMappings:
    def test_simple_mapping(self) -> None:
        text = "key: value"
        types = token_types(text)
        assert TokenType.BLOCK_MAPPING_START in types
        assert TokenType.VALUE in types
        vals = [t.value for t in scan(text) if t.type == TokenType.SCALAR]
        assert vals == ["key", "value"]

    def test_nested_mapping(self) -> None:
        text = "a:\n  b: c"
        types = token_types(text)
        assert types.count(TokenType.BLOCK_MAPPING_START) == 2
        vals = [t.value for t in scan(text) if t.type == TokenType.SCALAR]
        assert vals == ["a", "b", "c"]

    def test_multi_key_mapping(self) -> None:
        text = "a: 1\nb: 2\nc: 3"
        vals = [t.value for t in scan(text) if t.type == TokenType.SCALAR]
        assert vals == ["a", "1", "b", "2", "c", "3"]

    def test_explicit_key(self) -> None:
        text = "? key\n: value"
        types = token_types(text)
        assert TokenType.KEY in types


class TestSequences:
    def test_block_sequence(self) -> None:
        text = "- a\n- b\n- c"
        types = token_types(text)
        assert TokenType.BLOCK_SEQUENCE_START in types
        vals = [t.value for t in scan(text) if t.type == TokenType.SCALAR]
        assert vals == ["a", "b", "c"]

    def test_nested_sequence(self) -> None:
        text = "-\n  - a\n  - b"
        types = token_types(text)
        assert types.count(TokenType.BLOCK_SEQUENCE_START) == 2

    def test_sequence_of_mappings(self) -> None:
        text = "- key: val\n- key2: val2"
        vals = [t.value for t in scan(text) if t.type == TokenType.SCALAR]
        assert vals == ["key", "val", "key2", "val2"]


class TestFlowCollections:
    def test_flow_mapping(self) -> None:
        text = "{a: 1, b: 2}"
        types = token_types(text)
        assert TokenType.FLOW_MAPPING_START in types
        assert TokenType.FLOW_MAPPING_END in types
        assert TokenType.FLOW_ENTRY in types

    def test_flow_sequence(self) -> None:
        text = "[1, 2, 3]"
        types = token_types(text)
        assert TokenType.FLOW_SEQUENCE_START in types
        assert TokenType.FLOW_SEQUENCE_END in types

    def test_nested_flow(self) -> None:
        text = "{a: [1, 2], b: {c: 3}}"
        types = token_types(text)
        assert types.count(TokenType.FLOW_MAPPING_START) == 2
        assert types.count(TokenType.FLOW_SEQUENCE_START) == 1


class TestComments:
    def test_line_comment(self) -> None:
        text = "# this is a comment"
        types = token_types(text)
        assert TokenType.COMMENT in types
        comments = [t for t in scan(text) if t.type == TokenType.COMMENT]
        assert " this is a comment" in comments[0].value

    def test_inline_comment(self) -> None:
        text = "key: value # inline"
        tokens = scan(text)
        comments = [t for t in tokens if t.type == TokenType.COMMENT]
        assert len(comments) == 1
        assert "inline" in comments[0].value

    def test_multiple_comments(self) -> None:
        text = "# comment 1\nkey: value\n# comment 2"
        tokens = scan(text)
        comments = [t for t in tokens if t.type == TokenType.COMMENT]
        assert len(comments) == 2

    def test_comment_in_mapping(self) -> None:
        text = "a: 1 # first\nb: 2 # second"
        tokens = scan(text)
        comments = [t for t in tokens if t.type == TokenType.COMMENT]
        assert len(comments) == 2


class TestAnchorsAndAliases:
    def test_anchor(self) -> None:
        text = "&anchor value"
        tokens = scan(text)
        anchors = [t for t in tokens if t.type == TokenType.ANCHOR]
        assert len(anchors) == 1
        assert anchors[0].value == "anchor"

    def test_alias(self) -> None:
        text = "*anchor"
        tokens = scan(text)
        aliases = [t for t in tokens if t.type == TokenType.ALIAS]
        assert len(aliases) == 1
        assert aliases[0].value == "anchor"

    def test_anchor_and_alias(self) -> None:
        text = "a: &ref value\nb: *ref"
        tokens = scan(text)
        anchors = [t for t in tokens if t.type == TokenType.ANCHOR]
        aliases = [t for t in tokens if t.type == TokenType.ALIAS]
        assert len(anchors) == 1
        assert len(aliases) == 1
        assert anchors[0].value == "ref"
        assert aliases[0].value == "ref"


class TestTags:
    def test_tag(self) -> None:
        text = "!!str 123"
        tokens = scan(text)
        tags = [t for t in tokens if t.type == TokenType.TAG]
        assert len(tags) == 1
        assert tags[0].value == "!!str"

    def test_custom_tag(self) -> None:
        text = "!custom value"
        tokens = scan(text)
        tags = [t for t in tokens if t.type == TokenType.TAG]
        assert tags[0].value == "!custom"


class TestPositionTracking:
    def test_marks_present(self) -> None:
        tokens = scan("key: value")
        for token in tokens:
            assert isinstance(token.start, object)
            assert isinstance(token.end, object)
            assert token.start.line >= 0
            assert token.start.column >= 0

    def test_multiline_positions(self) -> None:
        text = "a: 1\nb: 2"
        tokens = scan(text)
        scalars = [t for t in tokens if t.type == TokenType.SCALAR]
        # "b" should be on line 1
        b_token = scalars[2]
        assert b_token.value == "b"
        assert b_token.start.line == 1


class TestEdgeCases:
    def test_empty_value(self) -> None:
        text = "key:"
        types = token_types(text)
        assert TokenType.BLOCK_MAPPING_START in types
        assert TokenType.VALUE in types

    def test_colon_in_value(self) -> None:
        text = "key: http://example.com"
        tokens = scan(text)
        scalars = [t for t in tokens if t.type == TokenType.SCALAR]
        assert scalars[1].value == "http://example.com"

    def test_document_start_not_in_middle(self) -> None:
        # --- is only a document start at column 0
        text = "key: ---value"
        tokens = scan(text)
        assert TokenType.DOCUMENT_START not in [t.type for t in tokens]

    def test_scanner_error_on_bad_input(self) -> None:
        scanner = Scanner("'unterminated")
        with pytest.raises(ScannerError):
            scanner.scan()


class TestConvenienceFunction:
    def test_scan_function(self) -> None:
        tokens = scan("hello: world")
        assert tokens[0].type == TokenType.STREAM_START
        assert tokens[-1].type == TokenType.STREAM_END
