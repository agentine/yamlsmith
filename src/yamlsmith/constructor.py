"""YAML constructor: maps YAML nodes to Python objects."""

from __future__ import annotations

import base64
import datetime
import math
import re
from typing import Any

from yamlsmith.nodes import MappingNode, Node, ScalarNode, SequenceNode
from yamlsmith.roundtrip import RoundTripDict, RoundTripList, RoundTripScalar


_BOOL_TRUE = frozenset({"true", "True", "TRUE"})
_BOOL_FALSE = frozenset({"false", "False", "FALSE"})
_NULL_VALUES = frozenset({"null", "Null", "NULL", "~", ""})

_INT_RE = re.compile(r"^[-+]?[0-9]+$")
_INT_OCT_RE = re.compile(r"^0o[0-7]+$")
_INT_HEX_RE = re.compile(r"^0x[0-9a-fA-F]+$")
_FLOAT_RE = re.compile(
    r"^[-+]?(\.[0-9]+|[0-9]+(\.[0-9]*)?)([eE][-+]?[0-9]+)?$"
)
_INF_RE = re.compile(r"^[-+]?\.(inf|Inf|INF)$")
_NAN_RE = re.compile(r"^\.(nan|NaN|NAN)$")

_DATETIME_RE = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})"
    r"(?:[Tt ](\d{2}):(\d{2}):(\d{2})"
    r"(?:\.(\d+))?"
    r"(?:[ ]*(Z|[-+]\d{1,2}(?::?\d{2})?))?)?$"
)


class ConstructorError(Exception):
    """Error during construction."""


class Constructor:
    """Maps YAML nodes to Python objects with round-trip metadata."""

    def construct(self, node: Node) -> Any:
        """Construct a Python object from a YAML node."""
        if isinstance(node, ScalarNode):
            return self._construct_scalar(node)
        if isinstance(node, MappingNode):
            return self._construct_mapping(node)
        if isinstance(node, SequenceNode):
            return self._construct_sequence(node)
        raise ConstructorError(f"Unknown node type: {type(node)}")

    def _construct_scalar(self, node: ScalarNode) -> Any:
        tag = node.tag
        value = node.value

        # For plain scalars with the default str tag, do implicit resolution.
        if (tag == "tag:yaml.org,2002:str" and
                (node.style is None or node.style == "plain")):
            result = self._resolve_plain(value)
        elif tag == "!!str":
            result = value
        elif tag == "!!int" or tag == "tag:yaml.org,2002:int":
            result = self._parse_int(value)
        elif tag == "!!float" or tag == "tag:yaml.org,2002:float":
            result = self._parse_float(value)
        elif tag == "!!bool" or tag == "tag:yaml.org,2002:bool":
            result = self._parse_bool(value)
        elif tag == "!!null" or tag == "tag:yaml.org,2002:null":
            result = None
        elif tag == "!!binary" or tag == "tag:yaml.org,2002:binary":
            result = base64.b64decode(value)
        elif tag == "!!timestamp" or tag == "tag:yaml.org,2002:timestamp":
            result = self._parse_datetime(value)
        else:
            # Implicit type resolution for plain scalars.
            if node.style is None or node.style == "plain":
                result = self._resolve_plain(value)
            else:
                result = value

        # Wrap in RoundTripScalar if there are comments.
        if node.pre_comment or node.inline_comment:
            # Don't store the default str tag when the value was implicitly
            # resolved to a different type (e.g., plain "5432" -> int).
            stored_tag: str | None = node.tag
            if (
                stored_tag == "tag:yaml.org,2002:str"
                and (node.style is None or node.style == "plain")
                and not isinstance(result, str)
            ):
                stored_tag = None
            return RoundTripScalar(
                result,
                pre_comment=node.pre_comment,
                inline_comment=node.inline_comment,
                style=node.style,
                tag=stored_tag,
            )
        return result

    def _construct_mapping(self, node: MappingNode) -> RoundTripDict:
        result = RoundTripDict()
        result._yaml_pre_comment = node.pre_comment
        result._yaml_inline_comment = node.inline_comment
        result._yaml_post_comment = node.post_comment

        for key_node, value_node in node.pairs:
            key = self.construct(key_node)
            val = self.construct(value_node)

            # Unwrap RoundTripScalar keys but preserve comments.
            actual_key: Any
            if isinstance(key, RoundTripScalar):
                actual_key = key.value
                result.set_comment(
                    actual_key,
                    pre=key.pre_comment,
                    inline=key.inline_comment,
                )
            else:
                actual_key = key

            # If value has inline comment, store it on the key entry.
            if isinstance(val, RoundTripScalar) and val.inline_comment:
                _, existing_inline = result.get_comment(actual_key)
                if not existing_inline:
                    result.set_comment(
                        actual_key,
                        pre=result.get_comment(actual_key)[0],
                        inline=val.inline_comment,
                    )

            result[actual_key] = val

        return result

    def _construct_sequence(self, node: SequenceNode) -> RoundTripList:
        result = RoundTripList()
        result._yaml_pre_comment = node.pre_comment
        result._yaml_inline_comment = node.inline_comment
        result._yaml_post_comment = node.post_comment

        for i, item_node in enumerate(node.items):
            val = self.construct(item_node)
            result.append(val)

            if isinstance(val, RoundTripScalar):
                result.set_item_comment(
                    i,
                    pre=val.pre_comment,
                    inline=val.inline_comment,
                )

        return result

    # -- Type resolution --

    def _resolve_plain(self, value: str) -> Any:
        """Resolve a plain scalar value to its Python type."""
        if value in _NULL_VALUES:
            return None
        if value in _BOOL_TRUE:
            return True
        if value in _BOOL_FALSE:
            return False

        # Integer.
        if _INT_RE.match(value):
            return int(value)
        if _INT_OCT_RE.match(value):
            return int(value, 8)
        if _INT_HEX_RE.match(value):
            return int(value, 16)

        # Float.
        if _FLOAT_RE.match(value):
            return float(value)
        if _INF_RE.match(value):
            return math.inf if not value.startswith("-") else -math.inf
        if _NAN_RE.match(value):
            return math.nan

        # Datetime.
        m = _DATETIME_RE.match(value)
        if m:
            return self._parse_datetime(value)

        return value

    def _parse_int(self, value: str) -> int:
        if value.startswith("0o"):
            return int(value, 8)
        if value.startswith("0x"):
            return int(value, 16)
        return int(value)

    def _parse_float(self, value: str) -> float:
        if _INF_RE.match(value):
            return math.inf if not value.startswith("-") else -math.inf
        if _NAN_RE.match(value):
            return math.nan
        return float(value)

    def _parse_bool(self, value: str) -> bool:
        if value in _BOOL_TRUE:
            return True
        if value in _BOOL_FALSE:
            return False
        raise ConstructorError(f"Invalid boolean: {value}")

    def _parse_datetime(self, value: str) -> datetime.date | datetime.datetime:
        m = _DATETIME_RE.match(value)
        if not m:
            raise ConstructorError(f"Invalid datetime: {value}")

        year = int(m.group(1))
        month = int(m.group(2))
        day = int(m.group(3))

        if m.group(4) is None:
            return datetime.date(year, month, day)

        hour = int(m.group(4))
        minute = int(m.group(5))
        second = int(m.group(6))

        microsecond = 0
        if m.group(7):
            frac = m.group(7)[:6].ljust(6, "0")
            microsecond = int(frac)

        tz: datetime.timezone | None = None
        if m.group(8):
            tz_str = m.group(8)
            if tz_str in ("Z", "z"):
                tz = datetime.timezone.utc
            else:
                sign = 1 if tz_str[0] == "+" else -1
                tz_str = tz_str[1:].replace(":", "")
                tz_hours = int(tz_str[:2])
                tz_minutes = int(tz_str[2:4]) if len(tz_str) > 2 else 0
                offset = datetime.timedelta(
                    hours=tz_hours, minutes=tz_minutes
                )
                tz = datetime.timezone(sign * offset)

        return datetime.datetime(
            year, month, day, hour, minute, second, microsecond, tzinfo=tz
        )
