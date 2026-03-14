"""YAML emitter: serializes a node graph back to YAML text."""

from __future__ import annotations

import re
from typing import TextIO

from yamlsmith.nodes import MappingNode, Node, ScalarNode, SequenceNode

# Characters that require structural quoting in plain scalars.
_PLAIN_UNSAFE_RE = re.compile(
    r"^[\-\?\:\,\[\]\{\}\#\&\*\!\|\>\'\"\%\@\`]"
    r"|[\:\#][ ]"
    r"|[ ][\#]"
    r"|^\.$"
    r"|[\n\r]"
    r"|^$"
)

# Exact patterns for values that YAML resolves to non-string types.
_YAML_TYPED_RE = re.compile(
    r"^(true|false|null|True|False|Null|TRUE|FALSE|NULL|~)$"
    r"|^[-+]?[0-9]+$"
    r"|^0o[0-7]+$"
    r"|^0x[0-9a-fA-F]+$"
    r"|^[-+]?(\.[0-9]+|[0-9]+(\.[0-9]*)?)([eE][-+]?[0-9]+)?$"
    r"|^[-+]?\.(inf|Inf|INF)$"
    r"|^\.(nan|NaN|NAN)$"
)


class Emitter:
    """Serializes a YAML node graph to text with comment preservation."""

    def __init__(
        self,
        stream: TextIO | None = None,
        *,
        indent: int = 2,
        default_flow_style: bool = False,
    ) -> None:
        self._parts: list[str] = []
        self._stream = stream
        self._indent = indent
        self._default_flow_style = default_flow_style

    def emit(self, node: Node) -> str:
        """Emit a single node and return the YAML text."""
        self._emit_node(node, level=0, is_key=False)
        text = "".join(self._parts)
        if self._stream is not None:
            self._stream.write(text)
        return text

    def emit_document(
        self,
        node: Node,
        *,
        explicit_start: bool = False,
        explicit_end: bool = False,
    ) -> str:
        """Emit a document with optional markers."""
        if explicit_start:
            self._write("---\n")
        self._emit_node(node, level=0, is_key=False)
        if not self._parts or not self._parts[-1].endswith("\n"):
            self._write("\n")
        if explicit_end:
            self._write("...\n")
        text = "".join(self._parts)
        if self._stream is not None:
            self._stream.write(text)
        return text

    def emit_all(
        self,
        nodes: list[Node],
        *,
        explicit_start: bool = True,
        explicit_end: bool = False,
    ) -> str:
        """Emit multiple documents."""
        for i, node in enumerate(nodes):
            if i > 0 or explicit_start:
                self._write("---\n")
            self._emit_node(node, level=0, is_key=False)
            if not self._parts or not self._parts[-1].endswith("\n"):
                self._write("\n")
        if explicit_end:
            self._write("...\n")
        text = "".join(self._parts)
        if self._stream is not None:
            self._stream.write(text)
        return text

    # -- Internal --

    def _write(self, text: str) -> None:
        self._parts.append(text)

    def _write_indent(self, level: int) -> None:
        self._write(" " * (self._indent * level))

    def _emit_node(self, node: Node, level: int, *, is_key: bool) -> None:
        if isinstance(node, ScalarNode):
            self._emit_scalar(node, level, is_key=is_key)
        elif isinstance(node, MappingNode):
            self._emit_mapping(node, level, is_key=is_key)
        elif isinstance(node, SequenceNode):
            self._emit_sequence(node, level, is_key=is_key)

    def _emit_scalar(
        self, node: ScalarNode, level: int, *, is_key: bool
    ) -> None:
        # Pre-comment.
        if node.pre_comment:
            for line in node.pre_comment.split("\n"):
                self._write_indent(level)
                self._write(f"#{line}\n")

        # Anchor.
        if node.anchor:
            self._write(f"&{node.anchor} ")

        # Value.
        value = node.value
        style = node.style

        if style == "literal":
            self._emit_block_scalar(value, level, indicator="|")
        elif style == "folded":
            self._emit_block_scalar(value, level, indicator=">")
        elif style == "single":
            escaped = value.replace("'", "''")
            self._write(f"'{escaped}'")
        elif style == "double":
            self._write(f'"{self._escape_double(value)}"')
        else:
            # Plain or auto. Don't quote values with non-str tags
            # (they are typed scalars like int, float, bool, null).
            if self._needs_quoting(value, tag=node.tag):
                self._write(f'"{self._escape_double(value)}"')
            else:
                self._write(value)

        # Inline comment.
        if node.inline_comment:
            self._write(f" #{node.inline_comment}")

    def _emit_block_scalar(
        self, value: str, level: int, indicator: str
    ) -> None:
        # Determine chomping.
        if value.endswith("\n\n"):
            chomp = "+"
            content = value[:-1]  # Remove extra trailing newline.
        elif value.endswith("\n"):
            chomp = ""
            content = value[:-1]
        else:
            chomp = "-"
            content = value

        self._write(f"{indicator}{chomp}\n")
        for line in content.split("\n"):
            self._write_indent(level + 1)
            self._write(f"{line}\n")

    def _emit_mapping(
        self, node: MappingNode, level: int, *, is_key: bool
    ) -> None:
        if node.flow_style or (
            self._default_flow_style and not node.flow_style
        ):
            self._emit_flow_mapping(node)
            return

        # Pre-comment.
        if node.pre_comment:
            for line in node.pre_comment.split("\n"):
                self._write_indent(level)
                self._write(f"#{line}\n")

        if node.anchor:
            self._write(f"&{node.anchor}\n")

        for i, (key, value) in enumerate(node.pairs):
            if i > 0 or level > 0:
                self._write_indent(level)

            # Key.
            self._emit_node(key, level, is_key=True)
            self._write(":")

            # Value.
            if isinstance(value, (MappingNode, SequenceNode)) and not value.flow_style:
                self._write("\n")
                self._emit_node(value, level + 1, is_key=False)
            else:
                self._write(" ")
                self._emit_node(value, level + 1, is_key=False)
                self._write("\n")

    def _emit_flow_mapping(self, node: MappingNode) -> None:
        if node.anchor:
            self._write(f"&{node.anchor} ")
        self._write("{")
        for i, (key, value) in enumerate(node.pairs):
            if i > 0:
                self._write(", ")
            self._emit_node(key, 0, is_key=True)
            self._write(": ")
            self._emit_node(value, 0, is_key=False)
        self._write("}")

    def _emit_sequence(
        self, node: SequenceNode, level: int, *, is_key: bool
    ) -> None:
        if node.flow_style or (
            self._default_flow_style and not node.flow_style
        ):
            self._emit_flow_sequence(node)
            return

        # Pre-comment.
        if node.pre_comment:
            for line in node.pre_comment.split("\n"):
                self._write_indent(level)
                self._write(f"#{line}\n")

        if node.anchor:
            self._write(f"&{node.anchor}\n")

        for item in node.items:
            self._write_indent(level)
            self._write("- ")

            if isinstance(item, (MappingNode, SequenceNode)) and not item.flow_style:
                self._write("\n")
                self._emit_node(item, level + 1, is_key=False)
            else:
                self._emit_node(item, level + 1, is_key=False)
                self._write("\n")

    def _emit_flow_sequence(self, node: SequenceNode) -> None:
        if node.anchor:
            self._write(f"&{node.anchor} ")
        self._write("[")
        for i, item in enumerate(node.items):
            if i > 0:
                self._write(", ")
            self._emit_node(item, 0, is_key=False)
        self._write("]")

    @staticmethod
    def _needs_quoting(value: str, tag: str = "") -> bool:
        """Check if a plain scalar value needs quoting."""
        if not value:
            return True
        # Non-string typed scalars (int, float, bool, null) don't need quoting.
        if tag and tag != "tag:yaml.org,2002:str" and tag != "!!str":
            return False
        if _PLAIN_UNSAFE_RE.search(value):
            return True
        if _YAML_TYPED_RE.match(value):
            return True
        return False

    @staticmethod
    def _escape_double(value: str) -> str:
        """Escape special characters for double-quoted scalar."""
        result = value.replace("\\", "\\\\")
        result = result.replace('"', '\\"')
        result = result.replace("\n", "\\n")
        result = result.replace("\r", "\\r")
        result = result.replace("\t", "\\t")
        result = result.replace("\0", "\\0")
        result = result.replace("\x07", "\\a")
        result = result.replace("\x08", "\\b")
        result = result.replace("\x1b", "\\e")
        return result


def emit(node: Node) -> str:
    """Convenience function to emit a single node."""
    return Emitter().emit(node)


def emit_all(nodes: list[Node]) -> str:
    """Convenience function to emit multiple documents."""
    return Emitter().emit_all(nodes)
