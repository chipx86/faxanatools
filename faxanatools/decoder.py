"""Decoder and ROM reader logic."""

from __future__ import annotations

from typing import TYPE_CHECKING

from faxanatools.messages import Message, Messages
from faxanatools.rom import FaxanaduROM, ROMIO
from faxanatools.iscripts import (
    ACTION_TYPES,
    DEFAULT_ISCRIPT_ORDER,
    IScript,
    IScriptAction,
    IScriptActionParamValue,
    IScriptLabel,
    IScriptActionParamType,
    IScriptTargetRef,
    IScripts,
)
from faxanatools.shops import Shop, ShopItem, ShopRef

if TYPE_CHECKING:
    from collections.abc import Iterator


class ROMDecoder:
    """Decoder logic for Faxanadu game state."""

    MESSAGE_SPECIAL_CHARS = {
        b'\xfb': b'<<<TITLE>>>',
        b'\xfc': b'<<<PAUSE>>>',
        b'\xfd': b' ',
        b'\xfe': b'\n',
    }

    def build_addr(
        self,
        upper: int,
        lower: int,
    ) -> int:
        """Return a bank-relative address for a give upper and lower value.

        Args:
            upper (int):
                The upper value.

            lower (int):
                The lower value.

        Returns:
            int:
            The bank-relative address.
        """
        return (upper << 8 | lower) & 0xFFFF

    def decode_messages(
        self,
        fp: ROMIO,
    ) -> Messages:
        """Decode the list of messages at the current file offset.

        This assumes the file pointer is at the correct read position.

        Args:
            fp (faxanatools.rom.ROMIO):
                The ROM file pointer to read from.

        Returns:
            faxanatools.messages.Messages:
            The resulting messages.
        """
        messages = Messages()
        special_chars = self.MESSAGE_SPECIAL_CHARS

        while (c := fp.peek(1)) != b'\0':
            buf: list[bytes] = []

            while (c := fp.read1(1)) != b'\xff':
                buf.append(c)

            message_str = b''.join(
                special_chars.get(c, c)
                for c in buf
            ).decode('ascii')

            messages.add(Message(message_id=f'msg-{len(messages) + 1:02x}',
                                 string=message_str))

        return messages

    def iter_decode_iscript_addrs(
        self,
        fp: ROMIO,
        *,
        num_scripts: int,
    ) -> Iterator[int]:
        """Yield each IScript entrypoint address from the ROM.

        This assumes the file pointer is at the correct read position.

        Args:
            fp (faxanatools.rom.ROMIO):
                The ROM file pointer to read from.

            num_scripts (int):
                The number of entrypoint scripts to read.

                This must be the correct amount for the ROM.

        Yields:
            int:
            Each bank-relative IScript address.
        """
        lower_addrs = fp.read(num_scripts)
        upper_addrs = fp.read(num_scripts)

        for upper_addr, lower_addr in zip(upper_addrs, lower_addrs):
            yield self.build_addr(upper_addr, lower_addr)

    def read_iscript_entity(
        self,
        fp: ROMIO,
    ) -> int:
        """Read an IScript entity ID from the ROM.

        This assumes the file pointer is at the correct read position.

        Args:
            fp (faxanatools.rom.ROMIO):
                The ROM file pointer to read from.

        Returns:
            int:
            The resulting entity ID.
        """
        return fp.read_value(1)

    def read_iscript_action(
        self,
        fp: ROMIO,
    ) -> IScriptAction:
        """Read an IScript action from the ROM.

        This will include the action's parameters.

        This assumes the file pointer is at the correct read position.

        Args:
            fp (faxanatools.rom.ROMIO):
                The ROM file pointer to read from.

        Returns:
            faxanatools.iscripts.IScriptAction:
            The resulting IScript action.
        """
        action_id = fp.read_value(1)

        try:
            action_type = ACTION_TYPES[action_id]
        except KeyError:
            raise ValueError(f'Unknown action ID {action_id}')

        params: list[IScriptActionParamValue] = []
        action = IScriptAction(action_type=action_type,
                               params=params)

        for i, param_info in enumerate(action_type.params):
            param_value = fp.read_value(param_info.size)
            params.append(IScriptActionParamValue(info=param_info,
                                                  value=param_value))

        return action

    def read_shop(
        self,
        fp: ROMIO,
        *,
        name: str,
    ) -> Shop:
        """Read shop information from the ROM.

        This will include all the shop's items.

        This assumes the file pointer is at the correct read position.

        Args:
            fp (faxanatools.rom.ROMIO):
                The ROM file pointer to read from.

        Returns:
            faxanatools.shops.Shop:
            The resulting shop.
        """
        shop = Shop(name=name)

        while (item_id := fp.read_value(1)) != 0xFF:
            price = fp.read_value(2)
            shop.add_item(ShopItem(item=item_id,
                                   price=price))

        return shop


class ROMReader:
    """Reader for a Faxanadu ROM.

    This is responsible for reading the contents of a Faxanadu ROM and
    decoding the information.
    """

    ######################
    # Instance variables #
    ######################

    #: The decoder for the information in the ROM.
    decoder: ROMDecoder

    #: The Faxanadu ROM information.
    rom: FaxanaduROM

    def __init__(
        self,
        *,
        rom: (FaxanaduROM | None) = None,
    ) -> None:
        """Initialize the reader.

        Args:
            rom (faxanatools.rom.FaxanaduROM, optional):
                Information on the ROM.

                If not provided, this will be generated with defaults.
        """
        self.decoder = ROMDecoder()
        self.rom = rom or FaxanaduROM()

    def read(
        self,
        filename: str,
    ) -> FaxanaduROM:
        """Read all supported contents from a Faxanadu ROM.

        Args:
            filename (str):
                The path to the ROM file to read.

        Returns:
            faxanatools.roms.FaxanaduROM:
            The resulting ROM information.
        """
        rom = self.rom

        with open(filename, 'rb') as raw_fp:
            raw_fp.seek(16)
            fp = ROMIO(raw_fp.read(),
                       rom=self.rom)

        messages = self._read_messages(fp)
        rom.messages = messages
        rom.iscripts = IScripts()
        rom.shops = {}

        self._read_iscripts(fp, messages=messages)

        return rom

    def _read_messages(
        self,
        fp: ROMIO,
    ) -> Messages:
        """Read message strings from the ROM.

        Args:
            fp (faxanatools.rom.ROMIO):
                The ROM file pointer to read from.

        Returns:
            faxanatools.messages.Messages:
            The resulting messages.
        """
        fp.seek(self.rom.messages_offset)

        return self.decoder.decode_messages(fp)

    def _read_iscripts(
        self,
        fp: ROMIO,
        *,
        messages: Messages,
    ) -> None:
        """Read all IScripts from the ROM.

        Args:
            fp (faxanatools.rom.ROMIO):
                The ROM file pointer to read from.

            messages (faxanatools.messages.Messages):
                The message strings used for action parameter value lookup.
        """
        decoder = self.decoder
        rom = self.rom

        bank = rom.get_bank_for(rom.iscript_addrs_offset)

        fp.seek(rom.iscript_addrs_offset)

        reffable_addrs: dict[int, tuple[IScript, IScriptLabel | None]] = {}
        seen_entrypoint_addrs: set[int] = set()

        addrs_iter = decoder.iter_decode_iscript_addrs(
            fp=fp,
            num_scripts=rom.max_iscript_addrs,
        )

        for i, bank_addr in enumerate(addrs_iter):
            name = DEFAULT_ISCRIPT_ORDER[i]
            rom.iscripts.entrypoints.append(name)

            if bank_addr in seen_entrypoint_addrs:
                continue

            seen_entrypoint_addrs.add(bank_addr)

            rom.iscripts.add_many(self._read_iscript(
                fp=fp,
                bank=bank,
                bank_addr=bank_addr,
                messages=messages,
                reffable_addrs=reffable_addrs,
                read_entity=True,
                entrypoint=True,
                name=name,
            ))

    def _read_iscript(
        self,
        *,
        fp: ROMIO,
        bank: int,
        bank_addr: int,
        messages: Messages,
        reffable_addrs: dict[int, tuple[IScript, IScriptLabel | None]],
        read_entity: bool = False,
        entrypoint: bool = False,
        name: (str | None) = None,
    ) -> list[IScript]:
        """Read one or more related IScripts from the ROM.

        Args:
            fp (faxanatools.rom.ROMIO):
                The ROM file pointer to read from.

            bank (int):
                The bank containing the IScript data.

            bank_addr (int):
                The bank-relative address of the script.

            messages (faxanatools.messages.Messages):
                The message strings used for action parameter value lookup.

            reffable_addrs (dict):
                A mapping of bank-relative addresses to reference targets.

            read_entity (bool, optional):
                Whether to read entity information for this script.

            entrypoint (bool, optional):
                Whether this is an entrypoint script, for inclusion in the
                entrypoint list.

            name (str, optional):
                The name of the script.

                If not provided, one will be calculated.

        Returns:
            list of faxanatools.iscripts.IScript:
            Each script loaded from this address.
        """
        decoder = self.decoder
        rom = self.rom

        code: list[IScriptAction | IScriptLabel] = []
        jump_queues: set[IScriptActionParamValue] = set()
        store_items_queues: set[IScriptActionParamValue] = set()
        iscripts: list[IScript] = []

        fp.seek_bank_addr(bank, bank_addr)

        # Set up the initial IScript.
        iscript = IScript(
            name=name or hex(bank_addr),
            code=code,
        )
        iscripts.append(iscript)

        reffable_addrs[bank_addr] = (iscript, None)

        # Read the entity, if any.
        if read_entity:
            iscript.entity = decoder.read_iscript_entity(fp)

        # Read and process all the actions in the script.
        while True:
            cur_addr = rom.get_bank_addr_for(fp.tell())

            if cur_addr != bank_addr:
                label = IScriptLabel(name=hex(cur_addr))
                code.append(label)
                reffable_addrs[cur_addr] = (iscript, label)

            action = decoder.read_iscript_action(fp)
            code.append(action)

            for param in action.params:
                param_type = param.info.type

                if param_type == IScriptActionParamType.SCRIPT_JUMP_ADDR:
                    jump_queues.add(param)
                elif param_type == IScriptActionParamType.SHOP_ADDR:
                    store_items_queues.add(param)
                elif param_type == IScriptActionParamType.MESSAGE:
                    param.value = messages.get_by_index(param.value)

            if action.action_type.ends:
                break

        # Handle the deferred scripts.
        for param in jump_queues:
            param_value = param.value

            if param_value not in reffable_addrs:
                iscripts.extend(self._read_iscript(
                    fp=fp,
                    bank=bank,
                    bank_addr=param_value,
                    messages=messages,
                    reffable_addrs=reffable_addrs,
                    read_entity=False,
                ))

            ref_iscript, ref_label = reffable_addrs[param_value]

            param.value = IScriptTargetRef(iscript=ref_iscript,
                                           label=ref_label)

        # Handle the shops.
        for param in store_items_queues:
            shop = self._read_shop(
                fp=fp,
                bank=bank,
                bank_addr=param.value,
            )
            rom.shops[shop.name] = shop

            param.value = ShopRef(shop)

        return iscripts

    def _read_shop(
        self,
        *,
        fp: ROMIO,
        bank: int,
        bank_addr: int,
    ) -> Shop:
        """Read one or more related shops from the ROM.

        Args:
            fp (faxanatools.rom.ROMIO):
                The ROM file pointer to read from.

            bank (int):
                The bank containing the shop data.

            bank_addr (int):
                The bank-relative address of the shop.

        Returns:
            faxanatools.shops.Shop:
            The resulting shop.
        """
        fp.seek_bank_addr(bank, bank_addr)

        return self.decoder.read_shop(
            fp,
            name=hex(bank_addr),
        )
