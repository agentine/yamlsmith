"""Tests for the yamlsmith constructor."""

from __future__ import annotations

import datetime
import math

from yamlsmith.composer import compose
from yamlsmith.constructor import Constructor
from yamlsmith.roundtrip import RoundTripDict, RoundTripList, RoundTripScalar


def construct(text: str) -> object:
    """Helper: compose + construct YAML text."""
    node = compose(text)
    assert node is not None
    return Constructor().construct(node)


class TestScalarTypes:
    def test_string(self) -> None:
        assert construct("hello") == "hello"

    def test_quoted_string(self) -> None:
        assert construct("'123'") == "123"

    def test_integer(self) -> None:
        assert construct("42") == 42

    def test_negative_integer(self) -> None:
        assert construct("-7") == -7

    def test_hex_integer(self) -> None:
        assert construct("0xFF") == 255

    def test_octal_integer(self) -> None:
        assert construct("0o77") == 63

    def test_float(self) -> None:
        assert construct("3.14") == 3.14

    def test_float_scientific(self) -> None:
        assert construct("1.5e3") == 1500.0

    def test_infinity(self) -> None:
        assert construct(".inf") == math.inf

    def test_neg_infinity(self) -> None:
        assert construct("-.inf") == -math.inf

    def test_nan(self) -> None:
        result = construct(".nan")
        assert isinstance(result, float)
        assert math.isnan(result)

    def test_bool_true(self) -> None:
        assert construct("true") is True

    def test_bool_false(self) -> None:
        assert construct("false") is False

    def test_yaml12_no_yes_no(self) -> None:
        # YAML 1.2: yes/no/on/off are strings, not booleans.
        assert construct("yes") == "yes"
        assert construct("no") == "no"
        assert construct("on") == "on"
        assert construct("off") == "off"

    def test_null(self) -> None:
        assert construct("null") is None

    def test_tilde_null(self) -> None:
        assert construct("~") is None

    def test_empty_null(self) -> None:
        result = construct("key:")
        assert isinstance(result, RoundTripDict)
        assert result["key"] is None


class TestDatetime:
    def test_date(self) -> None:
        result = construct("2023-01-15")
        assert result == datetime.date(2023, 1, 15)

    def test_datetime(self) -> None:
        result = construct("2023-01-15T10:30:00")
        assert isinstance(result, datetime.datetime)
        assert result.hour == 10
        assert result.minute == 30

    def test_datetime_utc(self) -> None:
        result = construct("2023-01-15T10:30:00Z")
        assert isinstance(result, datetime.datetime)
        assert result.tzinfo == datetime.timezone.utc

    def test_datetime_offset(self) -> None:
        result = construct("2023-01-15T10:30:00+05:30")
        assert isinstance(result, datetime.datetime)
        assert result.tzinfo is not None


class TestBinary:
    def test_binary(self) -> None:
        result = construct("!!binary aGVsbG8=")
        assert result == b"hello"


class TestMapping:
    def test_simple_mapping(self) -> None:
        result = construct("a: 1\nb: 2")
        assert isinstance(result, RoundTripDict)
        assert result["a"] == 1
        assert result["b"] == 2

    def test_nested_mapping(self) -> None:
        result = construct("outer:\n  inner: value")
        assert isinstance(result, RoundTripDict)
        assert isinstance(result["outer"], RoundTripDict)
        assert result["outer"]["inner"] == "value"


class TestSequence:
    def test_simple_sequence(self) -> None:
        result = construct("- a\n- b\n- c")
        assert isinstance(result, RoundTripList)
        assert list(result) == ["a", "b", "c"]

    def test_sequence_of_ints(self) -> None:
        result = construct("- 1\n- 2\n- 3")
        assert isinstance(result, RoundTripList)
        assert list(result) == [1, 2, 3]

    def test_sequence_of_mappings(self) -> None:
        result = construct("- name: a\n- name: b")
        assert isinstance(result, RoundTripList)
        assert len(result) == 2
        assert result[0]["name"] == "a"


class TestCommentPreservation:
    def test_inline_comment_on_scalar(self) -> None:
        result = construct("key: value # comment")
        assert isinstance(result, RoundTripDict)
        val = result["key"]
        assert isinstance(val, RoundTripScalar)
        assert val.value == "value"
        assert val.inline_comment is not None

    def test_mapping_key_comments(self) -> None:
        result = construct("a: 1 # first\nb: 2 # second")
        assert isinstance(result, RoundTripDict)
        _, inline_a = result.get_comment("a")
        _, inline_b = result.get_comment("b")
        assert inline_a is not None
        assert inline_b is not None


class TestExplicitTags:
    def test_str_tag(self) -> None:
        assert construct("!!str 123") == "123"

    def test_int_tag(self) -> None:
        assert construct("!!int '42'") == 42

    def test_float_tag(self) -> None:
        result = construct("!!float '3.14'")
        assert result == 3.14

    def test_bool_tag(self) -> None:
        assert construct("!!bool true") is True

    def test_null_tag(self) -> None:
        assert construct("!!null ''") is None
