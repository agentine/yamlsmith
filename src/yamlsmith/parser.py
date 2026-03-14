"""YAML event-stream parser built on top of the scanner."""

from __future__ import annotations

from dataclasses import dataclass

from yamlsmith.scanner import Mark, Scanner, Token, TokenType


# -- Events --


@dataclass
class StreamStartEvent:
    mark: Mark


@dataclass
class StreamEndEvent:
    mark: Mark


@dataclass
class DocumentStartEvent:
    explicit: bool
    mark: Mark


@dataclass
class DocumentEndEvent:
    explicit: bool
    mark: Mark


@dataclass
class MappingStartEvent:
    anchor: str | None = None
    tag: str | None = None
    flow_style: bool = False
    pre_comment: str | None = None
    mark: Mark | None = None


@dataclass
class MappingEndEvent:
    mark: Mark | None = None


@dataclass
class SequenceStartEvent:
    anchor: str | None = None
    tag: str | None = None
    flow_style: bool = False
    pre_comment: str | None = None
    mark: Mark | None = None


@dataclass
class SequenceEndEvent:
    mark: Mark | None = None


@dataclass
class ScalarEvent:
    value: str
    anchor: str | None = None
    tag: str | None = None
    style: str | None = None
    pre_comment: str | None = None
    inline_comment: str | None = None
    mark: Mark | None = None


@dataclass
class AliasEvent:
    anchor: str
    mark: Mark | None = None


Event = (
    StreamStartEvent
    | StreamEndEvent
    | DocumentStartEvent
    | DocumentEndEvent
    | MappingStartEvent
    | MappingEndEvent
    | SequenceStartEvent
    | SequenceEndEvent
    | ScalarEvent
    | AliasEvent
)


class ParserError(Exception):
    """Error during parsing."""

    def __init__(self, message: str, mark: Mark | None = None) -> None:
        self.mark = mark
        super().__init__(message)


class Parser:
    """Produces an event stream from scanner tokens."""

    def __init__(self, text: str) -> None:
        self._tokens = Scanner(text).scan()
        self._index = 0
        self._events: list[Event] = []

    def parse(self) -> list[Event]:
        """Parse the entire input and return all events."""
        self._parse_stream()
        return self._events

    # -- Token helpers --

    def _peek(self) -> Token | None:
        if self._index >= len(self._tokens):
            return None
        return self._tokens[self._index]

    def _peek_type(self) -> TokenType | None:
        t = self._peek()
        return t.type if t else None

    def _peek_mark(self) -> Mark:
        """Get the start mark of the current token, or a default."""
        t = self._peek()
        return t.start if t else Mark(0, 0, 0)

    def _advance(self) -> Token:
        t = self._tokens[self._index]
        self._index += 1
        return t

    def _expect(self, tt: TokenType) -> Token:
        t = self._peek()
        if t is None or t.type != tt:
            actual = t.type.value if t else "EOF"
            raise ParserError(
                f"Expected {tt.value}, got {actual}",
                t.start if t else None,
            )
        return self._advance()

    def _consume_comments(self) -> str | None:
        """Consume consecutive COMMENT tokens and return combined text."""
        parts: list[str] = []
        while self._peek_type() == TokenType.COMMENT:
            parts.append(self._advance().value)
        return "\n".join(parts) if parts else None

    # -- Parsing --

    def _parse_stream(self) -> None:
        self._expect(TokenType.STREAM_START)
        self._events.append(StreamStartEvent(mark=self._tokens[0].start))

        while self._peek_type() not in (TokenType.STREAM_END, None):
            self._parse_document()
            self._consume_comments()

        if self._peek_type() == TokenType.STREAM_END:
            self._events.append(StreamEndEvent(mark=self._advance().start))
        else:
            mark = self._tokens[-1].end if self._tokens else Mark(0, 0, 0)
            self._events.append(StreamEndEvent(mark=mark))

    def _parse_document(self) -> None:
        pre_comment = self._consume_comments()

        if self._peek_type() == TokenType.DOCUMENT_START:
            t = self._advance()
            self._events.append(
                DocumentStartEvent(explicit=True, mark=t.start)
            )
            self._consume_comments()
        else:
            mark = self._peek_mark()
            self._events.append(
                DocumentStartEvent(explicit=False, mark=mark)
            )

        if self._peek_type() not in (
            TokenType.DOCUMENT_END,
            TokenType.DOCUMENT_START,
            TokenType.STREAM_END,
            None,
        ):
            self._parse_node(pre_comment=pre_comment)

        if self._peek_type() == TokenType.DOCUMENT_END:
            t = self._advance()
            self._events.append(
                DocumentEndEvent(explicit=True, mark=t.start)
            )
        else:
            mark = self._peek_mark()
            self._events.append(
                DocumentEndEvent(explicit=False, mark=mark)
            )

    def _parse_node(
        self,
        pre_comment: str | None = None,
    ) -> None:
        pre_comment = pre_comment or self._consume_comments()
        anchor: str | None = None
        tag: str | None = None

        if self._peek_type() == TokenType.ANCHOR:
            anchor = self._advance().value
        if self._peek_type() == TokenType.TAG:
            tag = self._advance().value
        if anchor is None and self._peek_type() == TokenType.ANCHOR:
            anchor = self._advance().value

        self._consume_comments()

        tt = self._peek_type()

        if tt == TokenType.ALIAS:
            t = self._advance()
            self._events.append(AliasEvent(anchor=t.value, mark=t.start))
            return

        if tt == TokenType.SCALAR:
            t = self._advance()
            # Only consume a comment as inline if on the same line as scalar
            inline = None
            next_tok = self._peek()
            if (next_tok is not None
                    and next_tok.type == TokenType.COMMENT
                    and next_tok.start.line == t.end.line):
                inline = self._advance().value
            self._events.append(
                ScalarEvent(
                    value=t.value,
                    anchor=anchor,
                    tag=tag,
                    style=t.style.value if t.style else None,
                    pre_comment=pre_comment,
                    inline_comment=inline,
                    mark=t.start,
                )
            )
            return

        if tt == TokenType.BLOCK_MAPPING_START:
            self._parse_block_mapping(
                anchor=anchor, tag=tag, pre_comment=pre_comment
            )
            return

        if tt == TokenType.BLOCK_SEQUENCE_START:
            self._parse_block_sequence(
                anchor=anchor, tag=tag, pre_comment=pre_comment
            )
            return

        if tt == TokenType.FLOW_MAPPING_START:
            self._parse_flow_mapping(
                anchor=anchor, tag=tag, pre_comment=pre_comment
            )
            return

        if tt == TokenType.FLOW_SEQUENCE_START:
            self._parse_flow_sequence(
                anchor=anchor, tag=tag, pre_comment=pre_comment
            )
            return

        # Empty node (e.g. empty value in mapping).
        mark = self._peek_mark()
        self._events.append(
            ScalarEvent(
                value="",
                anchor=anchor,
                tag=tag,
                pre_comment=pre_comment,
                mark=mark,
            )
        )

    def _parse_block_mapping(
        self,
        anchor: str | None = None,
        tag: str | None = None,
        pre_comment: str | None = None,
    ) -> None:
        t = self._advance()  # BLOCK_MAPPING_START
        self._events.append(
            MappingStartEvent(
                anchor=anchor,
                tag=tag,
                flow_style=False,
                pre_comment=pre_comment,
                mark=t.start,
            )
        )

        while self._peek_type() not in (TokenType.BLOCK_END, None):
            pre = self._consume_comments()
            if self._peek_type() == TokenType.BLOCK_END:
                break

            if self._peek_type() == TokenType.KEY:
                self._advance()
                self._parse_node(pre_comment=pre)
                if self._peek_type() == TokenType.VALUE:
                    self._advance()
                    self._parse_node()
                else:
                    mark = self._peek_mark()
                    self._events.append(
                        ScalarEvent(value="", mark=mark)
                    )
            elif self._peek_type() == TokenType.SCALAR:
                # Implicit key.
                self._parse_node(pre_comment=pre)
                if self._peek_type() == TokenType.VALUE:
                    self._advance()
                    self._parse_node()
                else:
                    mark = self._peek_mark()
                    self._events.append(
                        ScalarEvent(value="", mark=mark)
                    )
            elif self._peek_type() == TokenType.VALUE:
                # Empty key.
                mark = self._peek_mark()
                self._events.append(ScalarEvent(value="", pre_comment=pre, mark=mark))
                self._advance()
                self._parse_node()
            else:
                break

        if self._peek_type() == TokenType.BLOCK_END:
            self._advance()
        self._events.append(MappingEndEvent())

    def _parse_block_sequence(
        self,
        anchor: str | None = None,
        tag: str | None = None,
        pre_comment: str | None = None,
    ) -> None:
        t = self._advance()  # BLOCK_SEQUENCE_START
        self._events.append(
            SequenceStartEvent(
                anchor=anchor,
                tag=tag,
                flow_style=False,
                pre_comment=pre_comment,
                mark=t.start,
            )
        )

        while self._peek_type() not in (TokenType.BLOCK_END, None):
            self._consume_comments()
            if self._peek_type() == TokenType.BLOCK_END:
                break
            if self._peek_type() == TokenType.VALUE:
                self._advance()  # consume -
                self._parse_node()
            else:
                break

        if self._peek_type() == TokenType.BLOCK_END:
            self._advance()
        self._events.append(SequenceEndEvent())

    def _parse_flow_mapping(
        self,
        anchor: str | None = None,
        tag: str | None = None,
        pre_comment: str | None = None,
    ) -> None:
        t = self._advance()  # FLOW_MAPPING_START
        self._events.append(
            MappingStartEvent(
                anchor=anchor,
                tag=tag,
                flow_style=True,
                pre_comment=pre_comment,
                mark=t.start,
            )
        )

        while self._peek_type() != TokenType.FLOW_MAPPING_END:
            if self._peek_type() is None:
                raise ParserError("Unterminated flow mapping")
            self._consume_comments()
            if self._peek_type() == TokenType.FLOW_MAPPING_END:
                break

            # Key.
            if self._peek_type() == TokenType.KEY:
                self._advance()
            self._parse_node()

            # Value.
            if self._peek_type() == TokenType.VALUE:
                self._advance()
                self._parse_node()
            else:
                mark = (
                    self._peek_mark()
                )
                self._events.append(ScalarEvent(value="", mark=mark))

            if self._peek_type() == TokenType.FLOW_ENTRY:
                self._advance()

        self._advance()  # FLOW_MAPPING_END
        self._events.append(MappingEndEvent())

    def _parse_flow_sequence(
        self,
        anchor: str | None = None,
        tag: str | None = None,
        pre_comment: str | None = None,
    ) -> None:
        t = self._advance()  # FLOW_SEQUENCE_START
        self._events.append(
            SequenceStartEvent(
                anchor=anchor,
                tag=tag,
                flow_style=True,
                pre_comment=pre_comment,
                mark=t.start,
            )
        )

        while self._peek_type() != TokenType.FLOW_SEQUENCE_END:
            if self._peek_type() is None:
                raise ParserError("Unterminated flow sequence")
            self._consume_comments()
            if self._peek_type() == TokenType.FLOW_SEQUENCE_END:
                break

            self._parse_node()

            if self._peek_type() == TokenType.FLOW_ENTRY:
                self._advance()

        self._advance()  # FLOW_SEQUENCE_END
        self._events.append(SequenceEndEvent())


def parse(text: str) -> list[Event]:
    """Convenience function to parse YAML text into events."""
    return Parser(text).parse()
