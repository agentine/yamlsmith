"""Tests for the yamlsmith public API."""

from __future__ import annotations

import io


import yamlsmith
from yamlsmith import (
    YAML,
    RoundTripDict,
    RoundTripList,
    RoundTripScalar,
    YAMLError,
    dump,
    dump_all,
    load,
    load_all,
)


class TestLoad:
    def test_load_string(self) -> None:
        result = load("hello")
        assert result == "hello"

    def test_load_mapping(self) -> None:
        result = load("a: 1\nb: 2")
        assert isinstance(result, RoundTripDict)
        assert result["a"] == 1
        assert result["b"] == 2

    def test_load_sequence(self) -> None:
        result = load("- a\n- b")
        assert isinstance(result, RoundTripList)
        assert list(result) == ["a", "b"]

    def test_load_bytes(self) -> None:
        result = load(b"hello: world")
        assert isinstance(result, RoundTripDict)
        assert result["hello"] == "world"

    def test_load_file_like(self) -> None:
        stream = io.StringIO("key: value")
        result = load(stream)
        assert isinstance(result, RoundTripDict)
        assert result["key"] == "value"

    def test_load_empty(self) -> None:
        result = load("")
        assert result is None

    def test_load_null(self) -> None:
        result = load("null")
        assert result is None

    def test_load_integer(self) -> None:
        result = load("42")
        assert result == 42

    def test_load_float(self) -> None:
        result = load("3.14")
        assert result == 3.14

    def test_load_bool(self) -> None:
        assert load("true") is True
        assert load("false") is False

    def test_load_preserves_comments(self) -> None:
        result = load("key: value # comment")
        assert isinstance(result, RoundTripDict)
        val = result["key"]
        assert isinstance(val, RoundTripScalar)
        assert val.value == "value"

    def test_load_nested(self) -> None:
        text = "a:\n  b:\n    c: 1"
        result = load(text)
        assert isinstance(result, RoundTripDict)
        assert result["a"]["b"]["c"] == 1


class TestLoadAll:
    def test_load_all_multi_doc(self) -> None:
        text = "---\nfoo\n---\nbar"
        result = load_all(text)
        assert len(result) == 2
        assert result[0] == "foo"
        assert result[1] == "bar"

    def test_load_all_single_doc(self) -> None:
        result = load_all("hello")
        assert len(result) == 1
        assert result[0] == "hello"


class TestDump:
    def test_dump_string(self) -> None:
        result = dump("hello")
        assert "hello" in result

    def test_dump_mapping(self) -> None:
        data = {"a": 1, "b": 2}
        result = dump(data)
        assert "a:" in result
        assert "b:" in result

    def test_dump_sequence(self) -> None:
        data = [1, 2, 3]
        result = dump(data)
        assert "- 1" in result
        assert "- 2" in result

    def test_dump_none(self) -> None:
        result = dump(None)
        assert "null" in result

    def test_dump_bool(self) -> None:
        result = dump(True)
        assert "true" in result

    def test_dump_to_stream(self) -> None:
        stream = io.StringIO()
        dump({"key": "value"}, stream=stream)
        assert "key: value" in stream.getvalue()

    def test_dump_ends_with_newline(self) -> None:
        result = dump("hello")
        assert result.endswith("\n")

    def test_dump_roundtrip_dict(self) -> None:
        d = RoundTripDict({"a": 1, "b": 2})
        d.set_comment("a", inline=" first item")
        result = dump(d)
        assert "# first item" in result

    def test_dump_nested(self) -> None:
        data = {"outer": {"inner": "value"}}
        result = dump(data)
        assert "outer:" in result
        assert "inner: value" in result


class TestDumpAll:
    def test_dump_all(self) -> None:
        result = dump_all(["foo", "bar"])
        assert "---" in result
        assert "foo" in result
        assert "bar" in result


class TestYAMLClass:
    def test_yaml_class_load(self) -> None:
        yaml = YAML()
        result = yaml.load("a: 1")
        assert isinstance(result, RoundTripDict)
        assert result["a"] == 1

    def test_yaml_class_dump(self) -> None:
        yaml = YAML()
        result = yaml.dump({"a": 1})
        assert "a:" in result

    def test_yaml_class_load_all(self) -> None:
        yaml = YAML()
        result = yaml.load_all("---\nfoo\n---\nbar")
        assert len(result) == 2

    def test_yaml_class_dump_all(self) -> None:
        yaml = YAML()
        result = yaml.dump_all(["foo", "bar"])
        assert "---" in result

    def test_yaml_class_custom_indent(self) -> None:
        yaml = YAML(indent=4)
        result = yaml.dump({"a": {"b": 1}})
        # Should use 4-space indent.
        assert "    " in result


class TestRoundTrip:
    def test_mapping_roundtrip(self) -> None:
        original = "a: 1\nb: 2\n"
        data = load(original)
        result = dump(data)
        reloaded = load(result)
        assert isinstance(reloaded, RoundTripDict)
        assert reloaded["a"] == 1
        assert reloaded["b"] == 2

    def test_sequence_roundtrip(self) -> None:
        original = "- x\n- y\n- z\n"
        data = load(original)
        result = dump(data)
        reloaded = load(result)
        assert isinstance(reloaded, RoundTripList)
        assert list(reloaded) == ["x", "y", "z"]

    def test_comment_roundtrip(self) -> None:
        original = "key: value # important\n"
        data = load(original)
        result = dump(data)
        assert "# important" in result

    def test_integer_with_comment_roundtrip(self) -> None:
        original = "port: 5432  # db port\n"
        data = load(original)
        result = dump(data)
        # Integer must not be quoted in output.
        assert 'port: 5432' in result
        assert '"5432"' not in result
        assert "# db port" in result

    def test_float_with_comment_roundtrip(self) -> None:
        original = "rate: 3.14  # pi\n"
        data = load(original)
        result = dump(data)
        assert 'rate: 3.14' in result
        assert '"3.14"' not in result

    def test_bool_with_comment_roundtrip(self) -> None:
        original = "enabled: true  # flag\n"
        data = load(original)
        result = dump(data)
        assert 'enabled: true' in result
        assert '"true"' not in result

    def test_nested_roundtrip(self) -> None:
        original = "a:\n  b: 1\n  c: 2\n"
        data = load(original)
        result = dump(data)
        reloaded = load(result)
        assert isinstance(reloaded, RoundTripDict)
        assert reloaded["a"]["b"] == 1
        assert reloaded["a"]["c"] == 2


class TestErrorTypes:
    def test_yaml_error_hierarchy(self) -> None:
        assert issubclass(yamlsmith.ScannerError, YAMLError)
        assert issubclass(yamlsmith.ParserError, YAMLError)
        assert issubclass(yamlsmith.ComposerError, YAMLError)
        assert issubclass(yamlsmith.ConstructorError, YAMLError)
        assert issubclass(yamlsmith.EmitterError, YAMLError)


class TestEdgeCases:
    def test_empty_mapping_value(self) -> None:
        result = load("key:")
        assert isinstance(result, RoundTripDict)
        assert result["key"] is None

    def test_multiline_string(self) -> None:
        text = "|\n  line1\n  line2\n"
        result = load(text)
        assert isinstance(result, str)
        assert "line1" in result
        assert "line2" in result

    def test_flow_mapping_roundtrip(self) -> None:
        text = "{a: 1, b: 2}"
        data = load(text)
        assert isinstance(data, RoundTripDict)
        assert data["a"] == 1

    def test_flow_sequence_roundtrip(self) -> None:
        text = "[1, 2, 3]"
        data = load(text)
        assert isinstance(data, RoundTripList)
        assert list(data) == [1, 2, 3]

    def test_version_exists(self) -> None:
        assert yamlsmith.__version__ == "0.1.0"
