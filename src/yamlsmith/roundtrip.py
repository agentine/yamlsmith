"""Round-trip data types that preserve YAML comment metadata."""

from __future__ import annotations

from typing import Any


class _CommentMixin:
    """Mixin for storing comment metadata on round-trip types."""

    _yaml_pre_comment: str | None
    _yaml_inline_comment: str | None
    _yaml_post_comment: str | None
    _yaml_key_comments: dict[Any, tuple[str | None, str | None]]

    def _init_comments(self) -> None:
        self._yaml_pre_comment = None
        self._yaml_inline_comment = None
        self._yaml_post_comment = None
        self._yaml_key_comments = {}


class RoundTripDict(dict[Any, Any], _CommentMixin):
    """Dict subclass that preserves insertion order and YAML comments."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._init_comments()

    def set_comment(
        self,
        key: Any,
        *,
        pre: str | None = None,
        inline: str | None = None,
    ) -> None:
        """Attach comments to a specific key."""
        self._yaml_key_comments[key] = (pre, inline)

    def get_comment(
        self, key: Any
    ) -> tuple[str | None, str | None]:
        """Get (pre_comment, inline_comment) for a key."""
        return self._yaml_key_comments.get(key, (None, None))


class RoundTripList(list[Any], _CommentMixin):
    """List subclass that preserves YAML comments."""

    def __init__(self, *args: Any) -> None:
        super().__init__(*args)
        self._init_comments()
        self._yaml_item_comments: dict[int, tuple[str | None, str | None]] = {}

    def set_item_comment(
        self,
        index: int,
        *,
        pre: str | None = None,
        inline: str | None = None,
    ) -> None:
        """Attach comments to a specific item index."""
        self._yaml_item_comments[index] = (pre, inline)

    def get_item_comment(
        self, index: int
    ) -> tuple[str | None, str | None]:
        """Get (pre_comment, inline_comment) for an item."""
        return self._yaml_item_comments.get(index, (None, None))


class RoundTripScalar:
    """Wrapper for a scalar value that carries comment metadata."""

    __slots__ = ("value", "pre_comment", "inline_comment", "style", "tag")

    def __init__(
        self,
        value: Any,
        *,
        pre_comment: str | None = None,
        inline_comment: str | None = None,
        style: str | None = None,
        tag: str | None = None,
    ) -> None:
        self.value = value
        self.pre_comment = pre_comment
        self.inline_comment = inline_comment
        self.style = style
        self.tag = tag

    def __repr__(self) -> str:
        return f"RoundTripScalar({self.value!r})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, RoundTripScalar):
            return self.value == other.value  # type: ignore[no-any-return]
        return self.value == other  # type: ignore[no-any-return]

    def __hash__(self) -> int:
        return hash(self.value)
