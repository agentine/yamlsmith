"""YAML 1.2 scanner/tokenizer with comment metadata preservation."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field


class TokenType(enum.Enum):
    """All token types produced by the YAML scanner."""

    STREAM_START = "STREAM_START"
    STREAM_END = "STREAM_END"
    DOCUMENT_START = "DOCUMENT_START"
    DOCUMENT_END = "DOCUMENT_END"
    BLOCK_MAPPING_START = "BLOCK_MAPPING_START"
    BLOCK_SEQUENCE_START = "BLOCK_SEQUENCE_START"
    BLOCK_END = "BLOCK_END"
    KEY = "KEY"
    VALUE = "VALUE"
    SCALAR = "SCALAR"
    FLOW_MAPPING_START = "FLOW_MAPPING_START"
    FLOW_MAPPING_END = "FLOW_MAPPING_END"
    FLOW_SEQUENCE_START = "FLOW_SEQUENCE_START"
    FLOW_SEQUENCE_END = "FLOW_SEQUENCE_END"
    FLOW_ENTRY = "FLOW_ENTRY"
    COMMENT = "COMMENT"
    ANCHOR = "ANCHOR"
    ALIAS = "ALIAS"
    TAG = "TAG"


class ScalarStyle(enum.Enum):
    """Scalar quoting/block style."""

    PLAIN = "plain"
    SINGLE_QUOTED = "single"
    DOUBLE_QUOTED = "double"
    LITERAL = "literal"  # |
    FOLDED = "folded"  # >


@dataclass(frozen=True)
class Mark:
    """Position in the input stream."""

    line: int
    column: int
    index: int


@dataclass
class Token:
    """A single token produced by the scanner."""

    type: TokenType
    value: str
    start: Mark
    end: Mark
    style: ScalarStyle | None = None
    comment: str | None = None  # attached comment text


class ScannerError(Exception):
    """Error during scanning."""

    def __init__(self, message: str, mark: Mark | None = None) -> None:
        self.mark = mark
        super().__init__(message)


_ESCAPE_MAP: dict[str, str] = {
    "0": "\0",
    "a": "\x07",
    "b": "\x08",
    "t": "\t",
    "\t": "\t",
    "n": "\n",
    "v": "\x0b",
    "f": "\x0c",
    "r": "\r",
    "e": "\x1b",
    " ": " ",
    '"': '"',
    "/": "/",
    "\\": "\\",
    "N": "\x85",
    "_": "\xa0",
    "L": "\u2028",
    "P": "\u2029",
}


class Scanner:
    """Stream-based YAML 1.2 tokenizer."""

    def __init__(self, text: str) -> None:
        self._text = text
        self._index = 0
        self._line = 0
        self._column = 0
        self._tokens: list[Token] = []
        self._done = False
        # Stack of indentation levels for block contexts.
        self._indents: list[int] = []
        self._indent: int = -1
        # Flow level (0 = block context).
        self._flow_level = 0
        # Whether we've emitted a KEY token for the current key.
        self._allow_simple_key = True
        # Track whether we need to check for implicit keys.
        self._possible_simple_key: dict[int, _SimpleKey] = {}

    # -- Public API --

    def scan(self) -> list[Token]:
        """Scan the entire input and return all tokens."""
        self._tokens.append(
            Token(
                TokenType.STREAM_START,
                "",
                self._mark(),
                self._mark(),
            )
        )
        while not self._done:
            self._fetch_next_token()
        return self._tokens

    # -- Position helpers --

    def _mark(self) -> Mark:
        return Mark(self._line, self._column, self._index)

    def _peek(self, offset: int = 0) -> str:
        idx = self._index + offset
        if idx >= len(self._text):
            return ""
        return self._text[idx]

    def _peek_chars(self, count: int) -> str:
        return self._text[self._index : self._index + count]

    def _advance(self, count: int = 1) -> str:
        result: list[str] = []
        for _ in range(count):
            if self._index >= len(self._text):
                break
            ch = self._text[self._index]
            result.append(ch)
            self._index += 1
            if ch == "\n":
                self._line += 1
                self._column = 0
            else:
                self._column += 1
        return "".join(result)

    def _at_end(self) -> bool:
        return self._index >= len(self._text)

    # -- Whitespace / comment handling --

    def _skip_whitespace(self) -> None:
        """Skip spaces and tabs (not newlines)."""
        while not self._at_end() and self._peek() in (" ", "\t"):
            self._advance()

    def _skip_whitespace_and_newlines(self) -> None:
        """Skip spaces, tabs, and newlines."""
        while not self._at_end() and self._peek() in (" ", "\t", "\n", "\r"):
            self._advance()

    def _scan_to_next_token(self) -> None:
        """Skip whitespace and comments until the next meaningful token."""
        while True:
            self._skip_whitespace()
            if self._peek() == "#":
                self._scan_comment()
            if self._peek() == "\n" or self._peek() == "\r":
                self._advance()
                if self._flow_level == 0:
                    self._allow_simple_key = True
            else:
                break

    def _scan_comment(self) -> None:
        """Scan a comment token."""
        start = self._mark()
        self._advance()  # skip #
        text_parts: list[str] = []
        while not self._at_end() and self._peek() != "\n":
            text_parts.append(self._advance())
        text = "".join(text_parts)
        self._tokens.append(
            Token(TokenType.COMMENT, text, start, self._mark())
        )

    # -- Block structure --

    def _unwind_indent(self, column: int) -> None:
        """Emit BLOCK_END tokens for indentation levels deeper than column."""
        while self._indent > column:
            mark = self._mark()
            self._tokens.append(
                Token(TokenType.BLOCK_END, "", mark, mark)
            )
            self._indent = self._indents.pop()

    def _add_indent(self, column: int) -> bool:
        """Push a new indentation level if column is deeper than current."""
        if self._indent < column:
            self._indents.append(self._indent)
            self._indent = column
            return True
        return False

    # -- Token fetching --

    def _fetch_next_token(self) -> None:
        self._scan_to_next_token()

        if self._at_end():
            self._unwind_indent(-1)
            mark = self._mark()
            self._tokens.append(
                Token(TokenType.STREAM_END, "", mark, mark)
            )
            self._done = True
            return

        if self._flow_level == 0:
            self._unwind_indent(self._column)

        ch = self._peek()
        ch2 = self._peek_chars(2)
        ch3 = self._peek_chars(3)

        # Document markers (only at column 0 in block context).
        if self._flow_level == 0 and self._column == 0:
            if ch3 == "---" and self._is_separator(3):
                self._fetch_document_start()
                return
            if ch3 == "..." and self._is_separator(3):
                self._fetch_document_end()
                return

        if ch == "{":
            self._fetch_flow_mapping_start()
            return
        if ch == "}":
            self._fetch_flow_mapping_end()
            return
        if ch == "[":
            self._fetch_flow_sequence_start()
            return
        if ch == "]":
            self._fetch_flow_sequence_end()
            return
        if ch == ",":
            self._fetch_flow_entry()
            return
        if ch == "?" and self._flow_level > 0 and self._peek(1) in (
            " ",
            "\t",
            "\n",
            "\r",
            "",
        ):
            self._fetch_key()
            return
        if ch2 == "? " or (
            ch == "?"
            and self._flow_level == 0
            and self._peek(1) in ("\n", "\r", "")
        ):
            self._fetch_key()
            return
        if ch == "-" and self._flow_level == 0 and self._peek(1) in (
            " ",
            "\n",
            "\r",
            "",
        ):
            self._fetch_block_entry()
            return
        if ch == ":" and (
            self._flow_level > 0
            and self._peek(1) in (" ", "\t", "\n", "\r", ",", "}", "]", "")
        ):
            self._fetch_value()
            return
        if ch == ":" and self._flow_level == 0 and self._peek(1) in (
            " ",
            "\n",
            "\r",
            "",
        ):
            self._fetch_value()
            return
        if ch == "*":
            self._fetch_alias()
            return
        if ch == "&":
            self._fetch_anchor()
            return
        if ch == "!":
            self._fetch_tag()
            return
        if ch == "|" and self._flow_level == 0:
            self._fetch_block_scalar(literal=True)
            return
        if ch == ">" and self._flow_level == 0:
            self._fetch_block_scalar(literal=False)
            return
        if ch == "'":
            self._fetch_single_quoted_scalar()
            return
        if ch == '"':
            self._fetch_double_quoted_scalar()
            return

        # Plain scalar.
        self._fetch_plain_scalar()

    def _is_separator(self, offset: int) -> bool:
        """Check that char at offset is whitespace, newline, or end."""
        ch = self._peek(offset)
        return ch in (" ", "\t", "\n", "\r", "")

    # -- Document markers --

    def _fetch_document_start(self) -> None:
        self._unwind_indent(-1)
        start = self._mark()
        self._advance(3)
        self._tokens.append(
            Token(TokenType.DOCUMENT_START, "---", start, self._mark())
        )

    def _fetch_document_end(self) -> None:
        self._unwind_indent(-1)
        start = self._mark()
        self._advance(3)
        self._tokens.append(
            Token(TokenType.DOCUMENT_END, "...", start, self._mark())
        )

    # -- Flow tokens --

    def _fetch_flow_mapping_start(self) -> None:
        self._flow_level += 1
        start = self._mark()
        self._advance()
        self._tokens.append(
            Token(TokenType.FLOW_MAPPING_START, "{", start, self._mark())
        )

    def _fetch_flow_mapping_end(self) -> None:
        self._flow_level = max(0, self._flow_level - 1)
        start = self._mark()
        self._advance()
        self._tokens.append(
            Token(TokenType.FLOW_MAPPING_END, "}", start, self._mark())
        )

    def _fetch_flow_sequence_start(self) -> None:
        self._flow_level += 1
        start = self._mark()
        self._advance()
        self._tokens.append(
            Token(TokenType.FLOW_SEQUENCE_START, "[", start, self._mark())
        )

    def _fetch_flow_sequence_end(self) -> None:
        self._flow_level = max(0, self._flow_level - 1)
        start = self._mark()
        self._advance()
        self._tokens.append(
            Token(TokenType.FLOW_SEQUENCE_END, "]", start, self._mark())
        )

    def _fetch_flow_entry(self) -> None:
        start = self._mark()
        self._advance()
        self._tokens.append(
            Token(TokenType.FLOW_ENTRY, ",", start, self._mark())
        )

    # -- Block tokens --

    def _fetch_key(self) -> None:
        if self._flow_level == 0:
            if self._add_indent(self._column):
                mark = self._mark()
                self._tokens.append(
                    Token(TokenType.BLOCK_MAPPING_START, "", mark, mark)
                )
        start = self._mark()
        self._advance()
        self._tokens.append(
            Token(TokenType.KEY, "?", start, self._mark())
        )

    def _fetch_block_entry(self) -> None:
        if self._add_indent(self._column):
            mark = self._mark()
            self._tokens.append(
                Token(TokenType.BLOCK_SEQUENCE_START, "", mark, mark)
            )
        start = self._mark()
        self._advance()
        self._tokens.append(
            Token(TokenType.VALUE, "-", start, self._mark())
        )

    def _fetch_value(self) -> None:
        if self._flow_level == 0:
            if self._add_indent(self._column):
                mark = self._mark()
                self._tokens.append(
                    Token(TokenType.BLOCK_MAPPING_START, "", mark, mark)
                )
        start = self._mark()
        self._advance()
        self._tokens.append(
            Token(TokenType.VALUE, ":", start, self._mark())
        )

    # -- Anchor / Alias / Tag --

    def _fetch_anchor(self) -> None:
        start = self._mark()
        self._advance()  # skip &
        name = self._scan_anchor_name()
        self._tokens.append(
            Token(TokenType.ANCHOR, name, start, self._mark())
        )

    def _fetch_alias(self) -> None:
        start = self._mark()
        self._advance()  # skip *
        name = self._scan_anchor_name()
        self._tokens.append(
            Token(TokenType.ALIAS, name, start, self._mark())
        )

    def _scan_anchor_name(self) -> str:
        parts: list[str] = []
        while not self._at_end():
            ch = self._peek()
            if ch in (
                " ",
                "\t",
                "\n",
                "\r",
                ",",
                ":",
                "?",
                "[",
                "]",
                "{",
                "}",
            ):
                break
            parts.append(self._advance())
        if not parts:
            raise ScannerError(
                "Expected anchor/alias name", self._mark()
            )
        return "".join(parts)

    def _fetch_tag(self) -> None:
        start = self._mark()
        self._advance()  # skip !
        tag_parts: list[str] = ["!"]
        while not self._at_end() and self._peek() not in (
            " ",
            "\t",
            "\n",
            "\r",
        ):
            tag_parts.append(self._advance())
        self._tokens.append(
            Token(TokenType.TAG, "".join(tag_parts), start, self._mark())
        )

    # -- Scalars --

    def _fetch_block_scalar(self, *, literal: bool) -> None:
        start = self._mark()
        self._advance()  # skip | or >
        style = ScalarStyle.LITERAL if literal else ScalarStyle.FOLDED
        # Parse optional chomping indicator and indent.
        chomp = ""
        explicit_indent = 0
        while not self._at_end() and self._peek() not in ("\n", "\r"):
            ch = self._peek()
            if ch in ("+", "-"):
                chomp = ch
                self._advance()
            elif ch.isdigit():
                explicit_indent = int(ch)
                self._advance()
            elif ch == " " or ch == "\t":
                self._advance()
            elif ch == "#":
                # Inline comment after block scalar indicator.
                self._scan_comment()
                break
            else:
                break

        # Consume the newline.
        if not self._at_end() and self._peek() in ("\n", "\r"):
            self._advance()

        # Determine the indentation of the block content.
        if explicit_indent > 0:
            block_indent = self._indent + explicit_indent + 1
        else:
            # Auto-detect: find first non-empty line.
            block_indent = self._detect_block_indent()

        lines: list[str] = []
        while not self._at_end():
            line_start_col = self._column
            # Check if this line is part of the block.
            if self._peek() == "\n":
                lines.append("")
                self._advance()
                continue
            if self._peek() == "\r":
                lines.append("")
                self._advance()
                if self._peek() == "\n":
                    self._advance()
                continue
            # Count indentation.
            indent = 0
            while not self._at_end() and self._peek() == " ":
                indent += 1
                self._advance()

            if indent < block_indent and self._peek() not in ("\n", "\r", ""):
                # Unindented non-empty line means end of block.
                # Push back the indentation.
                self._index -= indent
                self._column = line_start_col
                break

            if self._peek() in ("\n", "\r", ""):
                lines.append("")
                if not self._at_end() and self._peek() in ("\n", "\r"):
                    self._advance()
                continue

            # Read the line content.
            line_parts: list[str] = []
            while not self._at_end() and self._peek() not in ("\n", "\r"):
                line_parts.append(self._advance())
            line = "".join(line_parts)
            lines.append(line)
            if not self._at_end() and self._peek() in ("\n", "\r"):
                self._advance()

        # Apply chomping.
        text = self._chomp_block(lines, chomp, literal=literal)

        self._tokens.append(
            Token(TokenType.SCALAR, text, start, self._mark(), style=style)
        )

    def _detect_block_indent(self) -> int:
        """Detect block scalar indentation from first non-empty line."""
        saved_index = self._index
        indent = 0
        while saved_index + indent < len(self._text):
            ch = self._text[saved_index + indent]
            if ch == " ":
                indent += 1
            elif ch in ("\n", "\r"):
                # Empty line, skip it and try next.
                idx = saved_index + indent + 1
                if (
                    ch == "\r"
                    and idx < len(self._text)
                    and self._text[idx] == "\n"
                ):
                    idx += 1
                saved_index = idx
                indent = 0
            else:
                break
        return indent if indent > 0 else self._indent + 1

    def _chomp_block(
        self, lines: list[str], chomp: str, *, literal: bool
    ) -> str:
        # Remove trailing empty lines for strip/clip.
        content_lines = list(lines)

        if literal:
            joined = "\n".join(content_lines)
        else:
            # Folded: join non-empty lines with spaces, but preserve blank lines as newlines.
            parts: list[str] = []
            for line in content_lines:
                if line == "":
                    parts.append("\n")
                else:
                    if parts and parts[-1] != "\n":
                        parts.append(" ")
                    parts.append(line)
            joined = "".join(parts)

        if chomp == "-":
            # Strip: remove all trailing newlines.
            joined = joined.rstrip("\n")
        elif chomp == "+":
            # Keep: add final newline.
            joined = joined + "\n"
        else:
            # Clip (default): single trailing newline.
            joined = joined.rstrip("\n") + "\n"

        return joined

    def _fetch_single_quoted_scalar(self) -> None:
        start = self._mark()
        self._advance()  # skip opening '
        parts: list[str] = []
        while True:
            if self._at_end():
                raise ScannerError(
                    "Unterminated single-quoted scalar", start
                )
            ch = self._peek()
            if ch == "'":
                self._advance()
                if self._peek() == "'":
                    parts.append("'")
                    self._advance()
                else:
                    break
            elif ch == "\n":
                self._advance()
                # Fold newlines in single-quoted scalars.
                # Skip leading whitespace on next line.
                spaces = 0
                while self._peek() == " ":
                    self._advance()
                    spaces += 1
                parts.append("\n" if spaces == 0 else " ")
            else:
                parts.append(self._advance())
        value = "".join(parts)
        self._tokens.append(
            Token(
                TokenType.SCALAR,
                value,
                start,
                self._mark(),
                style=ScalarStyle.SINGLE_QUOTED,
            )
        )

    def _fetch_double_quoted_scalar(self) -> None:
        start = self._mark()
        self._advance()  # skip opening "
        parts: list[str] = []
        while True:
            if self._at_end():
                raise ScannerError(
                    "Unterminated double-quoted scalar", start
                )
            ch = self._peek()
            if ch == '"':
                self._advance()
                break
            if ch == "\\":
                self._advance()
                esc = self._peek()
                if esc in _ESCAPE_MAP:
                    parts.append(_ESCAPE_MAP[esc])
                    self._advance()
                elif esc == "x":
                    self._advance()
                    code = self._advance(2)
                    parts.append(chr(int(code, 16)))
                elif esc == "u":
                    self._advance()
                    code = self._advance(4)
                    parts.append(chr(int(code, 16)))
                elif esc == "U":
                    self._advance()
                    code = self._advance(8)
                    parts.append(chr(int(code, 16)))
                elif esc == "\n":
                    # Line continuation.
                    self._advance()
                    while self._peek() in (" ", "\t"):
                        self._advance()
                else:
                    parts.append(esc)
                    self._advance()
            elif ch == "\n":
                self._advance()
                while self._peek() == " ":
                    self._advance()
                parts.append(" ")
            else:
                parts.append(self._advance())
        value = "".join(parts)
        self._tokens.append(
            Token(
                TokenType.SCALAR,
                value,
                start,
                self._mark(),
                style=ScalarStyle.DOUBLE_QUOTED,
            )
        )

    def _fetch_plain_scalar(self) -> None:
        start = self._mark()
        parts: list[str] = []
        spaces: list[str] = []

        while not self._at_end():
            ch = self._peek()

            if ch == "#" and parts and self._text[self._index - 1] in (
                " ",
                "\t",
            ):
                break

            if ch == ":" and self._peek(1) in (
                " ",
                "\t",
                "\n",
                "\r",
                "",
                ",",
                "}",
                "]",
            ):
                break

            if self._flow_level > 0 and ch in (",", "}", "]", "{", "["):
                break

            if ch in ("\n", "\r"):
                if self._flow_level > 0:
                    break
                # Multi-line plain scalar.
                saved = self._mark()
                self._advance()
                # Skip whitespace on new line.
                line_indent = 0
                while self._peek() == " ":
                    line_indent += 1
                    self._advance()
                # If indentation is less or equal to current indent, scalar ends.
                if line_indent <= self._indent:
                    self._index = saved.index
                    self._line = saved.line
                    self._column = saved.column
                    break
                # Check for block indicators or document markers.
                next_ch = self._peek()
                if next_ch in ("#", "", ""):
                    self._index = saved.index
                    self._line = saved.line
                    self._column = saved.column
                    break
                next3 = self._peek_chars(3)
                if next3 in ("---", "...") and self._is_separator(3):
                    self._index = saved.index
                    self._line = saved.line
                    self._column = saved.column
                    break
                if next_ch in ("-",) and self._peek(1) == " ":
                    self._index = saved.index
                    self._line = saved.line
                    self._column = saved.column
                    break
                # Fold the newline to a space.
                if spaces:
                    parts.extend(spaces)
                    spaces = []
                parts.append(" ")
                continue

            if ch in (" ", "\t"):
                spaces.append(ch)
                self._advance()
                continue

            if spaces:
                parts.extend(spaces)
                spaces = []
            parts.append(self._advance())

        value = "".join(parts).rstrip(" \t")
        if not value:
            raise ScannerError("Expected a scalar value", start)

        self._tokens.append(
            Token(
                TokenType.SCALAR,
                value,
                start,
                self._mark(),
                style=ScalarStyle.PLAIN,
            )
        )


@dataclass
class _SimpleKey:
    """Tracking data for possible simple keys."""

    token_number: int = 0
    required: bool = False
    mark: Mark = field(default_factory=lambda: Mark(0, 0, 0))


def scan(text: str) -> list[Token]:
    """Convenience function to scan YAML text into tokens."""
    return Scanner(text).scan()
