"""YAML representer: maps Python objects to YAML nodes."""

from __future__ import annotations

import base64
import datetime
import math
from typing import Any

from yamlsmith.nodes import MappingNode, Node, ScalarNode, SequenceNode
from yamlsmith.roundtrip import RoundTripDict, RoundTripList, RoundTripScalar


class RepresenterError(Exception):
    """Error during representation."""


class Representer:
    """Maps Python objects to YAML nodes, preserving round-trip metadata."""

    def represent(self, obj: Any) -> Node:
        """Represent a Python object as a YAML node."""
        if isinstance(obj, RoundTripScalar):
            return self._represent_roundtrip_scalar(obj)
        if isinstance(obj, RoundTripDict):
            return self._represent_roundtrip_dict(obj)
        if isinstance(obj, RoundTripList):
            return self._represent_roundtrip_list(obj)
        if isinstance(obj, dict):
            return self._represent_dict(obj)
        if isinstance(obj, (list, tuple)):
            return self._represent_list(obj)
        return self._represent_scalar(obj)

    def _represent_scalar(self, obj: Any) -> ScalarNode:
        """Represent a plain Python scalar as a YAML node."""
        if obj is None:
            return ScalarNode(
                tag="tag:yaml.org,2002:null", value="null", style="plain"
            )
        if isinstance(obj, bool):
            return ScalarNode(
                tag="tag:yaml.org,2002:bool",
                value="true" if obj else "false",
                style="plain",
            )
        if isinstance(obj, int):
            return ScalarNode(
                tag="tag:yaml.org,2002:int",
                value=str(obj),
                style="plain",
            )
        if isinstance(obj, float):
            if math.isnan(obj):
                value = ".nan"
            elif math.isinf(obj):
                value = ".inf" if obj > 0 else "-.inf"
            else:
                value = repr(obj)
            return ScalarNode(
                tag="tag:yaml.org,2002:float", value=value, style="plain"
            )
        if isinstance(obj, datetime.datetime):
            if obj.tzinfo is not None:
                value = obj.isoformat()
            else:
                value = obj.isoformat()
            return ScalarNode(
                tag="tag:yaml.org,2002:timestamp",
                value=value,
                style="plain",
            )
        if isinstance(obj, datetime.date):
            return ScalarNode(
                tag="tag:yaml.org,2002:timestamp",
                value=obj.isoformat(),
                style="plain",
            )
        if isinstance(obj, bytes):
            encoded = base64.b64encode(obj).decode("ascii")
            return ScalarNode(
                tag="tag:yaml.org,2002:binary",
                value=encoded,
                style="plain",
            )
        if isinstance(obj, str):
            return ScalarNode(
                tag="tag:yaml.org,2002:str", value=obj, style="plain"
            )
        raise RepresenterError(f"Cannot represent {type(obj)}")

    def _represent_roundtrip_scalar(self, obj: RoundTripScalar) -> ScalarNode:
        inner = self._represent_scalar(obj.value)
        inner.pre_comment = obj.pre_comment
        inner.inline_comment = obj.inline_comment
        if obj.style:
            inner.style = obj.style
        if obj.tag:
            inner.tag = obj.tag
        return inner

    def _represent_dict(self, obj: dict[Any, Any]) -> MappingNode:
        node = MappingNode(tag="tag:yaml.org,2002:map")
        for key, value in obj.items():
            key_node = self.represent(key)
            value_node = self.represent(value)
            node.pairs.append((key_node, value_node))
        return node

    def _represent_roundtrip_dict(self, obj: RoundTripDict) -> MappingNode:
        node = MappingNode(
            tag="tag:yaml.org,2002:map",
            pre_comment=obj._yaml_pre_comment,
            inline_comment=obj._yaml_inline_comment,
            post_comment=obj._yaml_post_comment,
        )
        for key, value in obj.items():
            key_node = self.represent(key)
            value_node = self.represent(value)

            # Restore key comments.
            pre, inline = obj.get_comment(key)
            if isinstance(key_node, ScalarNode):
                key_node.pre_comment = pre
            if isinstance(value_node, ScalarNode) and inline:
                value_node.inline_comment = inline

            node.pairs.append((key_node, value_node))
        return node

    def _represent_list(self, obj: list[Any] | tuple[Any, ...]) -> SequenceNode:
        node = SequenceNode(tag="tag:yaml.org,2002:seq")
        for item in obj:
            node.items.append(self.represent(item))
        return node

    def _represent_roundtrip_list(self, obj: RoundTripList) -> SequenceNode:
        node = SequenceNode(
            tag="tag:yaml.org,2002:seq",
            pre_comment=obj._yaml_pre_comment,
            inline_comment=obj._yaml_inline_comment,
            post_comment=obj._yaml_post_comment,
        )
        for i, item in enumerate(obj):
            item_node = self.represent(item)

            # Restore item comments.
            pre, inline = obj.get_item_comment(i)
            if isinstance(item_node, ScalarNode):
                if pre:
                    item_node.pre_comment = pre
                if inline:
                    item_node.inline_comment = inline

            node.items.append(item_node)
        return node
