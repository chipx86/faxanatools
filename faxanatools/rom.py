"""ROM information and I/O operations."""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from faxanatools.iscripts import IScripts
from faxanatools.messages import Messages
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from faxanatools.shops import Shop


@dataclass
class FaxanaduROM:
    """Information and management for a Faxanadu ROM.

    This tracks the state of the ROM (including message strings and
    IScripts), as well as offsets for the ROM and address lookup.

    All addresses are relative to the start of the PRG ROM, and not
    necessarily the .nes file. It does not take into account any ROM file
    header, which is assuming to be stripped before processing.
    """

    #: The message strings found in Bank 13.
    messages: Messages = field(default_factory=Messages)

    #: The NPC/item/event interaction scripts found in Bank 12.
    iscripts: IScripts = field(default_factory=IScripts)

    #: The shops referenced by interaction scripts found in Bank 12.
    shops: dict[str, Shop] = field(default_factory=dict)

    #: The PRG ROM offset where the message strings are found.
    messages_offset: int = 0x34300

    #: The maximum number of entrypoint interaction scripts allowed.
    max_iscript_addrs: int = 152

    #: The PRG ROM offset where the IScript entrypoint address lists are found.
    iscript_addrs_offset: int = 0x31F6B

    #: The PRG ROM offset where the interaction scripts are found.
    iscripts_offset: int = (iscript_addrs_offset + max_iscript_addrs * 2)

    #: The total maximum length allowed for interaction script data.
    max_iscripts_len: int = 0xA6C8 - 0xA09A

    #: The total maximum length allowed for message strings.
    max_messages_len: int = 0xB3BA - 0x8300

    def get_bank_for(
        self,
        rom_addr: int,
    ) -> int:
        """Return the bank number for a PRG ROM address.

        Args:
            rom_addr (int):
                The PRG ROM address.

        Returns:
            int:
            The bank number.
        """
        return (rom_addr & 0xFF0000) // 0x4000

    def get_bank_addr_for(
        self,
        rom_addr: int,
    ) -> int:
        """Return the bank-relative memory address for PRG ROM address.

        Args:
            addr (int):
                The PRG ROM address.

        Returns:
            int:
            The bank-relative address.
        """
        return (rom_addr & 0xFFFF) + 0x8000

    def get_rom_offset_for(
        self,
        *,
        bank: int,
        addr: int,
    ) -> int:
        """Return the PRG ROM offset for a bank and bank-relative address.

        Args:
            bank (int):
                The bank number.

            addr (int):
                The bank-relative address.

        Returns:
            int:
            The PRG ROM address.
        """
        return (bank * 0x4000) + addr - 0x8000


class ROMIO(io.BytesIO):
    """I/O wrapper for reading/writing ROM data.

    This allows for easy reading and writing for loaded ROM data.
    """

    ######################
    # Instance variables #
    ######################

    #: The ROM being read or written.
    rom: FaxanaduROM

    def __init__(
        self,
        data: bytes,
        *,
        rom: FaxanaduROM,
    ) -> None:
        """Initialize the ROM I/O.

        Args:
            data (bytes):
                The normalized ROM data.

                This must not contain any .nes file header.

            rom (FaxanaduROM):
                The ROM information.
        """
        super().__init__(data)

        self.rom = rom

    def peek(
        self,
        size: int,
    ) -> bytes:
        """Peek a provided number of bytes.

        This will fetch the data without advancing the file pointer.

        Args:
            size (int):
                The number of bytes to peek.

        Returns:
            bytes:
            The peeked bytes.
        """
        cur_pos = self.tell()
        data = self.read(size)
        self.seek(cur_pos)

        return data

    def read_value(
        self,
        size: int,
    ) -> int:
        """Read an integer value from the ROM.

        ROM values are stored in Big Endian. This will read a value of an
        arbitrary length from the ROM into memory, reconstructing the value.

        Args:
            size (int):
                The number of bytes to read.

        Returns:
            int:
            The value from the ROM.
        """
        value = 0

        for i in range(size):
            value |= int.from_bytes(self.read(1)) << (8 * i)

        return value

    def write_value(
        self,
        value: int,
        size: int = 1,
    ) -> None:
        """Write an integer to the ROM.

        ROM values are stored in Big Endian. This will write a value of an
        arbitrary length from the ROM into memory, storing in the appropriate
        format.

        Args:
            value (int):
                The value to write.

            size (int):
                The number of bytes to write.
        """
        for i in range(size):
            self.write(((value >> (i * 8)) & 0xFF).to_bytes())

    def seek_bank_addr(
        self,
        bank: int,
        addr: int,
    ) -> None:
        """Seek to a relative offset within a bank.

        Args:
            bank (int):
                The bank number to seek to.

            addr (int):
                The bank-relative address to seek to.
        """
        self.seek(self.rom.get_rom_offset_for(bank=bank,
                                              addr=addr))
