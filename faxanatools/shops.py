"""Shop information.

Shops are used for buying and selling of items. They can be referenced
by IScripts for shop display.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator


@dataclass
class ShopItem:
    """An item in a shop."""

    #: The ID of the item.
    item: int

    #: The price of the item in gold.
    #:
    #: This allows up to a price of 65,535.
    price: int


class Shop:
    """A shop full of items."""

    ######################
    # Instance variables #
    ######################

    #: The name of the shop.
    #:
    #: IScripts within Faxanatools can use this name to reference the
    #: shop. This is not loaded from or persisted to the ROM.
    name: str

    #: The items found in the shop.
    items: list[ShopItem]

    def __init__(
        self,
        name: str,
    ) -> None:
        """Initialize the shop information.

        Args:
            name (str):
                The name for the shop.
        """
        self.items = []
        self.name = name

    def add_item(
        self,
        item: ShopItem,
    ) -> None:
        """Add an item to the shop.

        Args:
            item (ShopItem):
                The item to add.
        """
        self.items.append(item)

    def __iter__(self) -> Iterator[ShopItem]:
        """Iterate through all items in the shop.

        Yields:
            ShopItem:
            Each item in the shop.
        """
        yield from self.items


@dataclass
class ShopRef:
    """A reference to a shop.

    This is used by values in an IScript to reference a shop, for later
    serialization.
    """

    #: The shop instance to reference.
    shop: Shop
