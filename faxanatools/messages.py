"""Message string information.

Message strings can be referenced by script and other parts of the
Faxanadu codebase.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator


@dataclass
class Message:
    """A message string."""

    #: The Faxanatools reference name for the message.
    message_id: str

    #: The string contents.
    #:
    #: This may contain the following characters:
    #:
    #: * Standard letters, numbers, and punctuation.
    #: * Spaces
    #: * Newlines
    #: * ``<<<TITLE>>>`, to insert the player's current title.
    #: * ``<<<PAUSE>>>`, to pause output until acknowledged.
    string: str


class Messages:
    """A collection of messages."""

    ######################
    # Instance variables #
    ######################

    #: A mapping of message indexes to messages.
    _messages_by_index: OrderedDict[int, Message]

    #: A mapping of message names to indexes.
    _indexes_by_id: dict[str, int]

    #: The next index for an added message.
    _next_index: int

    def __init__(self) -> None:
        """Initialize the messages collection."""
        self._messages_by_index = OrderedDict()
        self._indexes_by_id = {}
        self._next_index = 1

    def add(
        self,
        message: Message,
    ) -> int:
        """Add a message to the collection.

        Args:
            message (Message):
                The message to add.
        """
        index = self._next_index

        self._messages_by_index[index] = message
        self._indexes_by_id[message.message_id] = index
        self._next_index += 1

        return index

    def get_by_index(
        self,
        index: int,
    ) -> Message:
        """Return a message for a given 1-based index.

        Args:
            index (int):
                The 1-based index for the message.

        Returns:
            Message:
            The message at the index.
        """
        assert index > 0
        assert index < self._next_index

        return self._messages_by_index[index]

    def get_by_id(
        self,
        message_id: str,
    ) -> Message:
        """Return a message for a given reference ID.

        Args:
            message_id (str):
                The Faxanatools reference ID of the message.

        Returns:
            Message:
            The message for that ID.
        """
        return self.get_by_index(self.get_index_for_id(message_id))

    def get_index_for_id(
        self,
        message_id: str,
    ) -> int:
        """Return a message's index for a given reference ID.

        Args:
            message_id (str):
                The Faxanatools reference ID of the message.

        Returns:
            int:
            The 1-based message index.
        """
        return self._indexes_by_id[message_id]

    def __len__(self) -> int:
        """Return the number of messages in the collection.

        Returns:
            int:
            The number of messages.
        """
        return self._next_index - 1

    def __iter__(self) -> Iterator[Message]:
        """Iterate through all messages in the collection.

        Yields:
            Message:
            Each message in the collection, in added order.
        """
        yield from self._messages_by_index.values()
