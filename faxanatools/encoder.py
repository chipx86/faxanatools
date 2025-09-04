"""Encoder and ROM patcher logic."""

from __future__ import annotations

from typing import TYPE_CHECKING

from faxanatools.iscripts import (
    IScript,
    IScriptAction,
    IScriptLabel,
    IScriptActionParamType,
    IScriptTargetRef,
)
from faxanatools.messages import Message
from faxanatools.rom import FaxanaduROM, ROMIO
from faxanatools.shops import Shop, ShopRef

if TYPE_CHECKING:
    from collections.abc import Sequence

    from faxanatools.messages import Messages


class ROMPatchError(Exception):
    """An error during ROM patching."""


class ROMEncoder:
    """Encoder logic for Faxanadu game state."""

    MESSAGE_SPECIAL_CHARS = {
        b'<<<TITLE>>>': b'\xfb',
        b'<<<PAUSE>>>': b'\xfc',
        b' ': b'\xfd',
        b'\n': b'\xfe',
    }

    def encode_messages(
        self,
        fp: ROMIO,
        messages: Messages,
    ) -> None:
        """Encode the list of messages.

        This assumes the file pointer is at the correct write position.

        Args:
            fp (faxanatools.rom.ROMIO):
                The ROM file pointer to write to.

            messages (faxanatools.messages.Messages):
                The messages to encode.
        """
        special_chars = self.MESSAGE_SPECIAL_CHARS

        for message in messages:
            message_str = message.string.encode('ascii')

            for code, chars in special_chars.items():
                message_str = message_str.replace(code, chars)

            fp.write(message_str)
            fp.write(b'\xff')

    def encode_iscript_addrs(
        self,
        fp: ROMIO,
        rom_offsets: Sequence[int],
        *,
        max_iscript_addrs: int,
    ) -> None:
        """Encode the list of IScript entrypoint addresses.

        This assumes the file pointer is at the correct write position.

        Args:
            fp (faxanatools.rom.ROMIO):
                The ROM file pointer to write to.

            rom_offsets (list of int):
                The list of ROM entrypoitn offsets to encode.

            max_iscript_addrs (int):
                The maximum number of addresess to encode for the list.
        """
        iscript_lower_addrs: list[bytes] = []
        iscript_upper_addrs: list[bytes] = []

        for rom_offset in rom_offsets:
            iscript_lower_addrs.append((rom_offset & 0xFF).to_bytes())
            iscript_upper_addrs.append(((rom_offset >> 8) & 0xFF).to_bytes())

        num_addrs = len(rom_offsets)

        if num_addrs < max_iscript_addrs:
            padding = b'\0' * (max_iscript_addrs - num_addrs)

            iscript_lower_addrs.append(padding)
            iscript_upper_addrs.append(padding)

        fp.write(b''.join(iscript_lower_addrs))
        fp.write(b''.join(iscript_upper_addrs))

    def encode_iscript(
        self,
        fp: ROMIO,
        iscript: IScript,
        *,
        messages: Messages,
        iscript_refs: dict[int, str],
        shop_refs: dict[int, str],
        iscript_rom_offsets: dict[str, int],
    ) -> None:
        """Encode an IScript.

        Args:
            fp (faxanatools.rom.ROMIO):
                The ROM file pointer to write to.

            iscript (faxanatools.iscripts.IScript):
                The IScript to encode.

            messages (faxanatools.messages.Messages):
                The messages to encode.

            iscript_refs (dict):
                A mapping of bank-relative script addresses to reference
                names.

            shop_refs (dict):
                A mapping of bank-relative shop addresses to reference names.

            iscript_rom_offsets (dict):
                A mapping of IScript reference names to bank-relative
                addresses.
        """
        cur_addr = fp.tell()
        iscript_rom_offsets[iscript.name] = cur_addr

        if iscript.entity is not None:
            fp.write_value(iscript.entity)

        for segment in iscript.code:
            if isinstance(segment, IScriptLabel):
                iscript_rom_offsets[segment.name] = cur_addr
            elif isinstance(segment, IScriptAction):
                self.encode_iscript_action(
                    fp,
                    segment,
                    messages=messages,
                    iscript_refs=iscript_refs,
                    shop_refs=shop_refs,
                )

    def encode_iscript_action(
        self,
        fp: ROMIO,
        action: IScriptAction,
        *,
        messages: Messages,
        iscript_refs: dict[int, str],
        shop_refs: dict[int, str],
    ) -> None:
        """Encode an IScript action.

        Args:
            fp (faxanatools.rom.ROMIO):
                The ROM file pointer to write to.

            action (faxanatools.iscripts.IScriptAction):
                The action to encode.

            messages (faxanatools.messages.Messages):
                The messages to encode.

            iscript_refs (dict):
                A mapping of bank-relative script addresses to reference
                names.

            shop_refs (dict):
                A mapping of bank-relative shop addresses to reference names.
        """
        fp.write_value(action.action_type.action_id)

        for param in action.params:
            param_type = param.info.type
            param_value = param.value

            if param_type == IScriptActionParamType.SCRIPT_JUMP_ADDR:
                assert isinstance(param_value, IScriptTargetRef)

                iscript_refs[fp.tell()] = param_value.target.name
                param_value = 0xFFFF
            elif param_type == IScriptActionParamType.SHOP_ADDR:
                assert isinstance(param_value, ShopRef)

                shop_refs[fp.tell()] = param_value.shop.name
                param_value = 0xFFFF
            elif param_type == IScriptActionParamType.MESSAGE:
                assert isinstance(param_value, Message), (
                    f'Expected message parameter of type Message, but '
                    f'got {param_value!r}'
                )

                param_value = \
                    messages.get_index_for_id(param_value.message_id)

            fp.write_value(param_value, param.info.size)

    def encode_shop(
        self,
        fp: ROMIO,
        shop: Shop,
    ) -> None:
        """Encode a shop and its items.

        Args:
            fp (faxanatools.rom.ROMIO):
                The ROM file pointer to write to.

            shop (faxanatools.shops.Shop):
                The shop to encode.
        """
        for shop_item in shop:
            fp.write_value(shop_item.item, 1)
            fp.write_value(shop_item.price, 2)

        fp.write(b'\xff')


class ROMPatcher:
    """A patcher for Faxanadu ROMs.

    This is responsible for patching the contents of a Faxanadu ROM and
    encoding the information.
    """

    ######################
    # Instance variables #
    ######################

    #: The encoder used to encode state in the ROM.
    encoder: ROMEncoder

    #: The Faxanadu ROM information to patch in.
    rom: FaxanaduROM

    def __init__(
        self,
        *,
        rom: FaxanaduROM,
    ) -> None:
        """Initialize the patcher.

        Args:
            rom (faxanatools.rom.FaxanaduROM):
                The Faxanadu ROM information to patch in.
        """
        self.encoder = ROMEncoder()
        self.rom = rom

    def patch(
        self,
        filename: str,
        *,
        patched_filename: str,
    ) -> None:
        """Patch a Faxanadu ROM file.

        Args:
            filename (str):
                The filename of the source Faxanadu ROM to patch.

            patched_filename (str):
                The name of the patched ROM file to write.

        Raises:
            ROMPatchError:
                There was an error patching the ROM.
        """
        rom = self.rom

        with open(filename, 'rb') as in_fp:
            header = in_fp.read(16)
            fp = ROMIO(in_fp.read(),
                       rom=rom)

        entrypoints_set = set(rom.iscripts.entrypoints)

        self._patch_messages(fp)
        self._patch_iscripts(fp, entrypoints_set=entrypoints_set)

        # Write the patched file.
        fp.seek(0)

        with open(patched_filename, 'wb') as out_fp:
            out_fp.write(header)
            out_fp.write(fp.read())

    def _patch_messages(
        self,
        fp: ROMIO,
    ) -> None:
        """Patch messages into a Faxanadu ROM.

        Args:
            fp (faxanatools.rom.ROMIO):
                The ROM file pointer to write to.

        Raises:
            ROMPatchError:
                There was an error patching the ROM.
        """
        rom = self.rom

        start_addr = rom.messages_offset
        fp.seek(start_addr)

        self.encoder.encode_messages(fp, rom.messages)
        data_len = fp.tell() - start_addr

        if data_len > rom.max_messages_len:
            raise ROMPatchError(
                'The compiled message strings are too large for the ROM. It '
                'must be %s bytes or less, but was %s bytes.'
                % (rom.max_messages_len, data_len)
            )

    def _patch_iscripts(
        self,
        fp: ROMIO,
        *,
        entrypoints_set: set[str],
    ) -> None:
        """Patch IScripts into a Faxanadu ROM.

        This will patch in all the scripts and the entrypoint address table.

        Args:
            fp (faxanatools.rom.ROMIO):
                The ROM file pointer to write to.

            entrypoints_set (set):
                The set of all entrypoint script names.

        Raises:
            ROMPatchError:
                There was an error patching the ROM.
        """
        encoder = self.encoder
        rom = self.rom
        messages = rom.messages

        start_addr = rom.iscripts_offset

        fp.seek(start_addr)

        iscript_refs: dict[int, str] = {}
        shop_refs: dict[int, str] = {}
        iscript_rom_offsets: dict[str, int] = {}
        shop_rom_offsets: dict[str, int] = {}
        entrypoint_iscript_rom_offsets: list[int] = []
        total_bytes: int = 0

        # Output all the scripts and their inner scripts.
        for iscript in rom.iscripts:
            iscript_start_addr = fp.tell()

            if iscript.name in entrypoints_set:
                entrypoint_iscript_rom_offsets.append(
                    rom.get_bank_addr_for(iscript_start_addr))

            encoder.encode_iscript(
                fp,
                iscript,
                messages=messages,
                iscript_refs=iscript_refs,
                shop_refs=shop_refs,
                iscript_rom_offsets=iscript_rom_offsets,
            )

            iscript_data_len = fp.tell() - iscript_start_addr
            total_bytes += iscript_data_len

        # Output all the shops.
        for shop in sorted(rom.shops.values(),
                           key=lambda shop: shop.name):
            shop_start_addr = fp.tell()

            shop_rom_offsets[shop.name] = shop_start_addr
            encoder.encode_shop(fp, shop)
            shop_data_len = fp.tell() - shop_start_addr

            total_bytes += shop_data_len

        # Make sure we didn't go over our limit.
        if total_bytes > rom.max_iscripts_len:
            raise ROMPatchError(
                'The compiled scripts are too large for the ROM. It must be '
                '%s bytes or less, but was %s bytes.'
                % (rom.max_iscripts_len, total_bytes)
            )

        # We haven't gone over the limit, but we might be under. NUL out
        # anything remaining.
        for i in range(rom.max_iscripts_len - total_bytes):
            fp.write(b'\0')

        # Now patch any and all references to scripts.
        for patch_addr, name in iscript_refs.items():
            fp.seek(patch_addr)
            fp.write_value(rom.get_bank_addr_for(iscript_rom_offsets[name]),
                           2)

        # And to shops.
        for patch_addr, name in shop_refs.items():
            fp.seek(patch_addr)
            fp.write_value(rom.get_bank_addr_for(shop_rom_offsets[name]),
                           2)

        self._patch_iscript_entrypoints(fp, entrypoint_iscript_rom_offsets)

    def _patch_iscript_entrypoints(
        self,
        fp: ROMIO,
        entrypoint_iscript_rom_offsets: list[int],
    ) -> None:
        """Patch IScript entrypoints into a Faxanadu ROM.

        Args:
            fp (faxanatools.rom.ROMIO):
                The ROM file pointer to write to.

            entrypoint_iscript_rom_offsets (list of int):
                The list of PRG ROM offsets of all entrypoints to write.

        Raises:
            ROMPatchError:
                There was an error patching the ROM.
        """
        rom = self.rom

        # Make sure we don't have more entrypoints than there are addresses.
        num_entrypoints = len(rom.iscripts.entrypoints)

        if num_entrypoints > rom.max_iscript_addrs:
            raise ROMPatchError(
                'There are too many entrypoint script addresses for the '
                'ROM. It must be %s scripts or less, but was %s.'
                % (rom.max_iscript_addrs, num_entrypoints)
            )

        # Insert these addresses into the table.
        fp.seek(rom.iscript_addrs_offset)
        self.encoder.encode_iscript_addrs(
            fp,
            entrypoint_iscript_rom_offsets,
            max_iscript_addrs=rom.max_iscript_addrs)
