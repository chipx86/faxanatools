"""JSON serializer for the Faxanatools format."""

from __future__ import annotations

from typing import TYPE_CHECKING

from faxanatools.iscripts import (
    IScriptAction,
    IScriptLabel,
    IScriptActionParamType,
    IScriptTargetRef,
)
from faxanatools.messages import Message
from faxanatools.shops import ShopRef

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from typing import Any

    from faxanatools.iscripts import (
        IScript,
        IScriptActionParamValue,
        IScriptCodeSegment,
    )
    from faxanatools.rom import FaxanaduROM


class JSONSerializerError(Exception):
    """An error during serialization."""


class JSONSerializer:
    """Serializer for the Faxanatools JSON format."""

    ######################
    # Instance variables #
    ######################

    #: The Faxanadu ROM information to serialize.
    rom: FaxanaduROM

    def __init__(
        self,
        *,
        rom: FaxanaduROM,
    ) -> None:
        """Initialize the serializer.

        Args:
            rom (faxanatools.rom.FaxanaduROM):
                The Faxanadu ROM information to serialize.
        """
        self.rom = rom

    def serialize(self) -> dict[str, Any]:
        """Serialize the ROM information to a JSON payload.

        Returns:
            dict:
            The resulting JSON payload.
        """
        return {
            'iscript_entrypoints': self._serialize_iscript_entrypoints(),
            'iscripts': self._serialize_iscripts(),
            'messages': self._serialize_messages(),
            'shops': self._serialize_shops(),
        }

    def _serialize_messages(self) -> Mapping[str, str]:
        """Serialize messages to a JSON payload.

        Returns:
            dict:
            The resulting JSON payload.
        """
        return {
            message.message_id: message.string
            for message in self.rom.messages
        }

    def _serialize_iscript_entrypoints(self) -> Sequence[str]:
        """Serialize IScript entrypoint addresses to a JSON payload.

        Returns:
            dict:
            The resulting JSON payload.
        """
        return self.rom.iscripts.entrypoints

    def _serialize_iscripts(self) -> Sequence[Mapping[str, Any]]:
        """Serialize IScripts to a JSON payload.

        Returns:
            list of dict:
            The resulting JSON payload.
        """
        return [
            self._serialize_iscript(iscript)
            for iscript in self.rom.iscripts
        ]

    def _serialize_iscript(
        self,
        iscript: IScript,
    ) -> Mapping[str, Any]:
        """Serialize an IScript to a JSON payload.

        Args:
            iscript (faxanatools.iscripts.IScript):
                The IScript to serialize.

        Returns:
            dict:
            The resulting JSON payload.
        """
        result: dict[str, Any] = {
            'code': list(filter(None, (
                self._serialize_iscript_code(code)
                for code in iscript.code
            ))),
            'name': iscript.name,
        }

        if iscript.entity is not None:
            result['entity'] = iscript.entity

        return result

    def _serialize_iscript_code(
        self,
        code: IScriptCodeSegment,
    ) -> Mapping[str, Any] | None:
        """Serialize an IScript code segment to a JSON payload.

        Args:
            code (faxanatools.iscripts.IScriptCodeSegment):
                The code segment to serialize.

        Returns:
            dict:
            The resulting JSON payload.
        """
        if isinstance(code, IScriptAction):
            return self._serialize_iscript_action(code)
        elif isinstance(code, IScriptLabel):
            return self._serialize_iscript_label(code)
        else:
            raise JSONSerializerError(
                f'Unsupported IScript code segment: {code!r}'
            )

    def _serialize_iscript_action(
        self,
        action: IScriptAction,
    ) -> Mapping[str, Any]:
        """Serialize an IScript action to a JSON payload.

        Args:
            action (faxanatools.iscripts.IScriptAction):
                The action to serialize.

        Returns:
            dict:
            The resulting JSON payload.
        """
        return {
            'action': action.action_type.name,
            'params': [
                self._serialize_iscript_action_param(param)
                for param in action.params
            ],
        }

    def _serialize_iscript_action_param(
        self,
        param: IScriptActionParamValue,
    ) -> Any:
        """Serialize an IScript action parameter to a JSON payload.

        Args:
            param (faxanatools.iscripts.IScriptActionParamValue):
                The parameter value to serialize.

        Returns:
            object:
            The resulting JSON value.
        """
        param_type = param.info.type
        param_value = param.value

        if param_type == IScriptActionParamType.SCRIPT_JUMP_ADDR:
            assert isinstance(param_value, IScriptTargetRef)

            param_value = param_value.target.name
        elif param_type == IScriptActionParamType.SHOP_ADDR:
            assert isinstance(param_value, ShopRef)

            param_value = param_value.shop.name
        elif param_type == IScriptActionParamType.MESSAGE:
            assert isinstance(param_value, Message)

            param_value = param_value.message_id

        return param_value

    def _serialize_iscript_label(
        self,
        label: IScriptLabel,
    ) -> Mapping[str, Any] | None:
        """Serialize an IScript label to a JSON payload.

        If the label has no ref counts, it won't be serialized.

        Args:
            label (faxanatools.iscripts.IScriptLabel):
                The label to serialize.

        Returns:
            dict:
            The resulting label, or None.
        """
        if label.ref_count == 0:
            return None

        return {
            'label': label.name,
        }

    def _serialize_shops(self) -> Mapping[str, Any]:
        """Serialize shops to a JSON payload.

        Returns:
            dict:
            The resulting JSON payload.
        """
        return {
            shop.name: {
                'items': [
                    {
                        'item': shop_item.item,
                        'price': shop_item.price,
                    }
                    for shop_item in shop.items
                ]
            }
            for shop in self.rom.shops.values()
        }
