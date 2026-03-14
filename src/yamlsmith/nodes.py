"""YAML node model with comment metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Union


@dataclass
class ScalarNode:
    """A scalar value node."""

    tag: str
    value: str
    style: str | None = None  # plain, single, double, literal, folded
    anchor: str | None = None
    pre_comment: str | None = None
    inline_comment: str | None = None
    post_comment: str | None = None


@dataclass
class MappingNode:
    """A mapping (dict) node containing key-value pairs."""

    tag: str
    pairs: list[tuple[Node, Node]] = field(default_factory=list)
    flow_style: bool = False
    anchor: str | None = None
    pre_comment: str | None = None
    inline_comment: str | None = None
    post_comment: str | None = None


@dataclass
class SequenceNode:
    """A sequence (list) node containing items."""

    tag: str
    items: list[Node] = field(default_factory=list)
    flow_style: bool = False
    anchor: str | None = None
    pre_comment: str | None = None
    inline_comment: str | None = None
    post_comment: str | None = None


Node = Union[ScalarNode, MappingNode, SequenceNode]
