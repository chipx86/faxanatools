"""JSON deserializer for the Faxanatools format."""

from __future__ import annotations

from typing import TYPE_CHECKING

from faxanatools.iscripts import (
    ACTION_TYPES_BY_NAME,
    IScript,
    IScriptAction,
    IScriptActionParamInfo,
    IScriptActionParamValue,
    IScriptLabel,
    IScriptActionParamType,
    IScriptTargetRef,
)
from faxanatools.messages import Message, Messages
from faxanatools.rom import FaxanaduROM
from faxanatools.shops import Shop, ShopItem, ShopRef

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import Any

    from faxanatools.iscripts import IScriptCodeSegment


class JSONDeserializerError(Exception):
    """An error during deserialization."""


class JSONDeserializer:
    """Deserializer for the Faxanatools JSON format."""

    ######################
    # Instance variables #
    ######################

    #: The loaded JSON data.
    data: Mapping[str, Any]

    #: The Faxanadu ROM information to deserialize into.
    rom: FaxanaduROM

    #: A mapping of target names to reference points.
    _iscript_targets: dict[str, tuple[IScript, IScriptLabel | None]]

    #: A list of all IScript references to resolve during deserialization.
    _iscript_refs_to_resolve: list[IScriptActionParamValue]

    def __init__(
        self,
        data: Mapping[str, Any],
        *,
        rom: (FaxanaduROM | None) = None,
    ) -> None:
        """Initialize the deserializer.

        Args:
            data (dict):
                The JSON data to load from.

            rom (faxanatools.rom.FaxanaduROM, optional):
                Information on the ROM.

                If not provided, this will be generated with defaults.
        """
        self.data = data
        self.rom = rom or FaxanaduROM()
        self._iscript_targets = {}
        self._iscript_refs_to_resolve = []

    def deserialize(self) -> FaxanaduROM:
        """Deserialize a JSON file to a Faxanadu ROM.

        Returns:
            faxanatools.rom.FaxanaduROM:
            The deserialized Faxanadu ROM information.

        Raises:
            JSONDeserializerError:
                There was an error deserializing from the payload.
        """
        rom = self.rom

        rom.messages = self._deserialize_messages()
        rom.shops = self._deserialize_shops()
        self._deserialize_iscript_entrypoints()
        self._deserialize_iscripts()
        self._resolve_iscript_refs()

        return rom

    def _deserialize_messages(self) -> Messages:
        """Deserialize the messages from the JSON payload.

        Returns:
            faxanatools.messages.Messages:
            The deserialized messages.
        """
        messages = Messages()

        for message_id, message_str in self.data['messages'].items():
            messages.add(Message(message_id=message_id,
                                 string=message_str))

        return messages

    def _deserialize_shops(self) -> dict[str, Shop]:
        """Deserialize the shops from the JSON payload.

        Returns:
            dict:
            A mapping of shop names to deserialized shops.
        """
        results: dict[str, Shop] = {}

        for name, shop_data in self.data['shops'].items():
            shop = self._deserialize_shop(shop_data,
                                          name=name)

            results[shop.name] = shop

        return results

    def _deserialize_shop(
        self,
        shop_data: Mapping[str, Any],
        name: str,
    ) -> Shop:
        """Deserialize a shop from the JSON payload.

        Args:
            shop_data (dict):
                The shop JSON data to load from.

            name (str):
                The name of the shop.

        Returns:
            faxanatools.shops.Shop:
            The deserialized shop.
        """
        shop = Shop(name=name)

        for item_data in shop_data['items']:
            shop.add_item(ShopItem(item=item_data['item'],
                                   price=item_data['price']))

        return shop

    def _deserialize_iscript_entrypoints(self) -> None:
        """Deserialize the list of IScript entrypoints."""
        self.rom.iscripts.entrypoints = self.data['iscript_entrypoints']

    def _deserialize_iscripts(self) -> None:
        """Deserialize each IScript from the payload.

        Raises:
            JSONDeserializerError:
                There was an error deserializing from the payload.
        """
        rom = self.rom

        for iscript_data in self.data['iscripts']:
            rom.iscripts.add(self._deserialize_iscript(iscript_data))

    def _deserialize_iscript(
        self,
        iscript_data: Mapping[str, Any],
    ) -> IScript:
        """Deserialize an IScript from the payload.

        Args:
            iscript_data (dict):
                The IScript JSON data to load from.

        Returns:
            faxanatools.iscripts.IScript:
            The deserialized IScript.

        Raises:
            JSONDeserializerError:
                There was an error deserializing from the payload.
        """
        name = iscript_data['name']
        code: list[IScriptCodeSegment] = []

        iscript = IScript(
            code=code,
            entity=iscript_data.get('entity'),
            name=name,
        )

        assert name not in self._iscript_targets
        self._iscript_targets[name] = (iscript, None)

        for code_data in iscript_data['code']:
            code.append(self._deserialize_iscript_code(code_data, iscript))

        return iscript

    def _deserialize_iscript_code(
        self,
        code_data: Mapping[str, Any],
        iscript: IScript,
    ) -> IScriptCodeSegment:
        """Deserialize the code segments for an IScript.

        Args:
            code_data (dict):
                The code segment JSON data to load from.

            iscript (faxanatools.iscripts.IScript):
                The IScript owning the code segments.

        Returns:
            faxanatools.iscripts.IScriptCodeSegment:
            The deserialized code segment.

        Raises:
            JSONDeserializerError:
                There was an error deserializing from the payload.
        """
        if 'label' in code_data:
            return self._deserialize_iscript_label(code_data, iscript)
        elif 'action' in code_data:
            return self._deserialize_iscript_action(code_data)
        else:
            raise JSONDeserializerError(
                f'Unsupported IScript code segment: {code_data!r}'
            )

    def _deserialize_iscript_label(
        self,
        label_data: Mapping[str, Any],
        iscript: IScript,
    ) -> IScriptLabel:
        """Deserialize an IScript label.

        Args:
            label_data (dict):
                The IScript label JSON data to load from.

            iscript (faxanatools.iscripts.IScript):
                The IScript owning the label.

        Returns:
            faxanatools.iscripts.IScriptLabel:
            The deserialized IScript label.

        Raises:
            JSONDeserializerError:
                There was an error deserializing from the payload.
        """
        name = label_data['label']
        label = IScriptLabel(name=name)

        if name in self._iscript_targets:
            existing_target = self._iscript_targets[name]

            raise JSONDeserializerError(
                f'Attempted to deserialize IScript label "{name}", but '
                f'this name was already registered to {existing_target!r}'
            )

        self._iscript_targets[name] = (iscript, label)

        return label

    def _deserialize_iscript_action(
        self,
        action_data: Mapping[str, Any],
    ) -> IScriptAction:
        """Deserialize an IScript action.

        Args:
            action_data (dict):
                The IScript action JSON data to load from.

        Returns:
            faxanatools.iscripts.IScriptLabel:
            The deserialized IScript action.

        Raises:
            JSONDeserializerError:
                There was an error deserializing from the payload.
        """
        action_type = ACTION_TYPES_BY_NAME[action_data['action']]

        return IScriptAction(
            action_type=action_type,
            params=[
                self._deserialize_iscript_action_param(param_data,
                                                       param_info)
                for param_data, param_info in zip(action_data['params'],
                                                  action_type.params)
            ],
        )

    def _deserialize_iscript_action_param(
        self,
        param_value: Any,
        param_info: IScriptActionParamInfo,
    ) -> IScriptActionParamValue:
        """Deserialize an IScript action parameter.

        Args:
            param_value (object):
                The IScript parameter JSON value to load from.

            param_info (faxanatools.iscripts.IScriptActionParamInfo):
                Information on the parameter.

        Returns:
            faxanatools.iscripts.IScriptActionParamValue:
            The deserialized IScript action parameter value.
        """
        param_type = param_info.type

        action_param_value = IScriptActionParamValue(
            info=param_info,
            value=param_value,
        )

        if param_type == IScriptActionParamType.SCRIPT_JUMP_ADDR:
            self._iscript_refs_to_resolve.append(action_param_value)
        elif param_type == IScriptActionParamType.SHOP_ADDR:
            action_param_value.value = ShopRef(self.rom.shops[param_value])
        elif param_type == IScriptActionParamType.MESSAGE:
            action_param_value.value = self.rom.messages.get_by_id(param_value)

        return action_param_value

    def _resolve_iscript_refs(self) -> None:
        """Resolve all IScript references.

        This will update all IScript parameters referencing another script
        or label with the resulting reference object.
        """
        targets = self._iscript_targets

        for action_param_value in self._iscript_refs_to_resolve:
            param_value = action_param_value.value
            target_iscript, target_label = targets[param_value]
            action_param_value.value = IScriptTargetRef(
                iscript=target_iscript,
                label=target_label)
