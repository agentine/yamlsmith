"""Tests for the yamlsmith representer."""

from __future__ import annotations

import datetime

from yamlsmith.nodes import MappingNode, ScalarNode, SequenceNode
from yamlsmith.representer import Representer
from yamlsmith.roundtrip import RoundTripDict, RoundTripList, RoundTripScalar


def represent(obj: object) -> object:
    """Helper: represent a Python object as a YAML node."""
    return Representer().represent(obj)


class TestScalarRepresentation:
    def test_none(self) -> None:
        node = represent(None)
        assert isinstance(node, ScalarNode)
        assert node.value == "null"

    def test_true(self) -> None:
        node = represent(True)
        assert isinstance(node, ScalarNode)
        assert node.value == "true"

    def test_false(self) -> None:
        node = represent(False)
        assert isinstance(node, ScalarNode)
        assert node.value == "false"

    def test_integer(self) -> None:
        node = represent(42)
        assert isinstance(node, ScalarNode)
        assert node.value == "42"

    def test_float(self) -> None:
        node = represent(3.14)
        assert isinstance(node, ScalarNode)
        assert "3.14" in node.value

    def test_nan(self) -> None:
        node = represent(float("nan"))
        assert isinstance(node, ScalarNode)
        assert node.value == ".nan"

    def test_inf(self) -> None:
        node = represent(float("inf"))
        assert isinstance(node, ScalarNode)
        assert node.value == ".inf"

    def test_neg_inf(self) -> None:
        node = represent(float("-inf"))
        assert isinstance(node, ScalarNode)
        assert node.value == "-.inf"

    def test_string(self) -> None:
        node = represent("hello")
        assert isinstance(node, ScalarNode)
        assert node.value == "hello"

    def test_datetime(self) -> None:
        dt = datetime.datetime(2023, 1, 15, 10, 30, tzinfo=datetime.timezone.utc)
        node = represent(dt)
        assert isinstance(node, ScalarNode)
        assert "2023" in node.value

    def test_date(self) -> None:
        d = datetime.date(2023, 1, 15)
        node = represent(d)
        assert isinstance(node, ScalarNode)
        assert node.value == "2023-01-15"

    def test_bytes(self) -> None:
        node = represent(b"hello")
        assert isinstance(node, ScalarNode)
        assert node.tag == "tag:yaml.org,2002:binary"


class TestMappingRepresentation:
    def test_dict(self) -> None:
        node = represent({"a": 1, "b": 2})
        assert isinstance(node, MappingNode)
        assert len(node.pairs) == 2

    def test_roundtrip_dict(self) -> None:
        d = RoundTripDict({"x": 1})
        d._yaml_pre_comment = " header"
        d.set_comment("x", inline=" value comment")
        node = represent(d)
        assert isinstance(node, MappingNode)
        assert node.pre_comment == " header"
        # Value should have inline comment.
        _, v = node.pairs[0]
        assert isinstance(v, ScalarNode)
        assert v.inline_comment == " value comment"


class TestSequenceRepresentation:
    def test_list(self) -> None:
        node = represent([1, 2, 3])
        assert isinstance(node, SequenceNode)
        assert len(node.items) == 3

    def test_roundtrip_list(self) -> None:
        lst = RoundTripList([1, 2])
        lst._yaml_pre_comment = " list comment"
        lst.set_item_comment(0, inline=" first")
        node = represent(lst)
        assert isinstance(node, SequenceNode)
        assert node.pre_comment == " list comment"
        assert isinstance(node.items[0], ScalarNode)
        assert node.items[0].inline_comment == " first"


class TestRoundTripScalar:
    def test_roundtrip_scalar(self) -> None:
        s = RoundTripScalar(42, inline_comment=" answer")
        node = represent(s)
        assert isinstance(node, ScalarNode)
        assert node.value == "42"
        assert node.inline_comment == " answer"

    def test_roundtrip_scalar_style(self) -> None:
        s = RoundTripScalar("hello", style="single")
        node = represent(s)
        assert isinstance(node, ScalarNode)
        assert node.style == "single"


class TestRoundTrip:
    def test_construct_then_represent(self) -> None:
        """Test that construct -> represent preserves structure."""
        from yamlsmith.composer import compose
        from yamlsmith.constructor import Constructor

        text = "a: 1 # comment\nb: 2"
        node = compose(text)
        assert node is not None
        obj = Constructor().construct(node)
        result_node = Representer().represent(obj)
        assert isinstance(result_node, MappingNode)
        assert len(result_node.pairs) == 2
