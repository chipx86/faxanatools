"""Interaction script information.

Interaction scripts are embedded binary scripts used for interactions
with NPCs, shops, items, and certain events (like quest objective
completion or elapsed item timer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping, Sequence
    from typing import Any, TypeAlias

    IScriptCodeSegment: TypeAlias = 'IScriptAction | IScriptLabel'
    IScriptTarget: TypeAlias = 'IScript | IScriptLabel'


class IScriptActionParamType(Enum):
    """A type of parameter for an action."""

    #: A numeric value (the default).
    #:
    #: This may represent item IDs, temple IDs, or some other numeric
    #: value.
    VALUE = auto()

    #: A message string reference.
    MESSAGE = auto()

    #: A bank-relative address to jump to.
    SCRIPT_JUMP_ADDR = auto()

    #: A bank-relative address containing a thop.
    SHOP_ADDR = auto()


@dataclass
class IScriptActionInfo:
    """Information on a type of action in a script."""

    #: The numeric ID of the action.
    action_id: int

    #: The Faxanatools name for the action.
    name: str

    #: Information on the parameters accepted by this action.
    params: Sequence[IScriptActionParamInfo] = field(default_factory=list)

    #: Whether this action ends a script's execution.
    ends: bool = False


@dataclass
class IScriptActionParamInfo:
    """Information on a parameter for an action."""

    #: The name of the parameter.
    name: str

    #: The size of the parameter value in bytes.
    size: int = 1

    #: The type of parameter.
    #:
    #: This defaults to a numeric value.
    type: IScriptActionParamType = IScriptActionParamType.VALUE


@dataclass
class IScriptActionParamValue:
    """A value passed to an action."""

    #: The value for the parameter.
    value: Any

    #: Information on the parameter.
    info: IScriptActionParamInfo

    def __hash__(self) -> int:
        """Return a hash of the instance.

        This will uniquely identify the instance, rather than any value
        or state within it.

        Returns:
            int:
            The hash.
        """
        return id(self)


@dataclass
class IScriptLabel:
    """A label in a script.

    Labels can be used as a jump address for a script action parameter.
    """

    #: The Faxanatools reference name for the label.
    name: str

    #: The number of jumps that reference this label.
    ref_count: int = 0


@dataclass
class IScriptAction:
    """An action performed in a script."""

    #: The type information for the action.
    action_type: IScriptActionInfo

    #: The parameter values passed to the action.
    params: list[IScriptActionParamValue]


@dataclass
class IScript:
    """An interaction script in the ROM.

    This contains actions and labels from the beginning of an entrypoint
    or a jump target. It may be the entire script or a segment of a script
    that another script or another part of a script may jump to.
    """

    #: The contents of the script.
    code: Sequence[IScriptCodeSegment]

    #: The Faxanatools reference name for this script.
    name: str

    #: The entity ID for the script.
    #:
    #: This only applies to top-level entrypoint scripts.
    entity: (int | None) = None

    #: The number of jumps that reference this script.
    ref_count: int = 0


@dataclass(frozen=True)
class IScriptTargetRef:
    """A reference targeting a script or label within a script."""

    #: The script that's targeted, directly or through a label.
    iscript: IScript

    #: A specific label within the script that's targeted.
    label: (IScriptLabel | None) = None

    def __post_init__(self) -> None:
        """Initialize the reference.

        This will increase the reference count of the target.
        """
        self.target.ref_count += 1

    @property
    def target(self) -> IScriptTarget:
        """The target being referenced."""
        return self.label or self.iscript


class IScripts:
    """A collection of IScripts in a ROM.

    This tracks each script and the list of entrypoint addresses.
    """

    ######################
    # Instance variables #
    ######################

    #: The full list of IScripts.
    #:
    #: This may contain top-level entrypoints and partial IScripts used
    #: as jump targets.
    iscripts: list[IScript] = field(default_factory=list)

    #: The list of IScript names used as entrypoints, in ROM-specified order.
    #:
    #: This will be used to generate the addresses after scripts have been
    #: written.
    entrypoints: list[str] = field(default_factory=list)

    #: A mapping of IScripts by script name.
    _iscripts_by_id: dict[str, IScript]

    def __init__(self) -> None:
        """Initialize the IScript collection."""
        self.iscripts = []
        self.entrypoints = []
        self._iscripts_by_id = {}

    def add(
        self,
        iscript: IScript,
    ) -> None:
        """Add an IScript to the collection.

        Args:
            iscript (IScript):
                The script to add.
        """
        name = iscript.name
        assert name not in self._iscripts_by_id

        self.iscripts.append(iscript)
        self._iscripts_by_id[name] = iscript

    def add_many(
        self,
        iscripts: Sequence[IScript],
    ) -> None:
        """Add multiple scripts to the collection.

        Args:
            iscripts (list of IScript):
                The list of scripts to add.
        """
        for iscript in iscripts:
            self.add(iscript)

    def __iter__(self) -> Iterator[IScript]:
        """Iterate through each script.

        Yields:
            IScript:
            Each script in the collection.
        """
        yield from self.iscripts

    def __len__(self) -> int:
        """Return the number of scripts in the collection.

        Returns:
            int:
            The number of scripts.
        """
        return len(self.iscripts)


#: A mapping of numeric action IDs to action definitions.
ACTION_TYPES: Mapping[int, IScriptActionInfo] = {
    action.action_id: action
    for action in [
        IScriptActionInfo(
            action_id=0x00,
            name='end',
            ends=True,
        ),
        IScriptActionInfo(
            action_id=0x01,
            name='show-message',
            params=[
                IScriptActionParamInfo(
                    name='message_id',
                    type=IScriptActionParamType.MESSAGE,
                ),
            ],
        ),
        IScriptActionInfo(
            action_id=0x02,
            name='show-dismissible-message',
            params=[
                IScriptActionParamInfo(
                    name='message_id',
                    type=IScriptActionParamType.MESSAGE,
                ),
            ],
        ),
        IScriptActionInfo(
            action_id=0x03,
            name='show-message-2',
            params=[
                IScriptActionParamInfo(
                    name='message_id',
                    type=IScriptActionParamType.MESSAGE,
                ),
            ],
        ),
        IScriptActionInfo(
            action_id=0x04,
            name='if-update-player-title',
            params=[
                IScriptActionParamInfo(
                    name='then-jump',
                    size=2,
                    type=IScriptActionParamType.SCRIPT_JUMP_ADDR,
                )
            ],
        ),
        IScriptActionInfo(
            action_id=0x05,
            name='pay-gold',
            params=[
                IScriptActionParamInfo(
                    name='amount',
                    size=2,
                ),
            ],
        ),
        IScriptActionInfo(
            action_id=0x06,
            name='set-spawn-point',
            params=[
                IScriptActionParamInfo(name='temple-id'),
            ],
        ),
        IScriptActionInfo(
            action_id=0x07,
            name='add-player-item',
            params=[
                IScriptActionParamInfo(name='item-id'),
            ],
        ),
        IScriptActionInfo(
            action_id=0x08,
            name='open-shop',
            params=[
                IScriptActionParamInfo(
                    name='items',
                    size=2,
                    type=IScriptActionParamType.SHOP_ADDR,
                ),
            ],
        ),
        IScriptActionInfo(
            action_id=0x09,
            name='add-gold',
            params=[
                IScriptActionParamInfo(
                    name='amount',
                    size=2,
                ),
            ],
        ),
        IScriptActionInfo(
            action_id=0x0A,
            name='add-mp',
            params=[
                IScriptActionParamInfo(name='amount'),
            ],
        ),
        IScriptActionInfo(
            action_id=0x0B,
            name='if-quest',
            params=[
                IScriptActionParamInfo(name='quest'),
                IScriptActionParamInfo(
                    name='then-jump',
                    size=2,
                    type=IScriptActionParamType.SCRIPT_JUMP_ADDR,
                ),
            ],
        ),
        IScriptActionInfo(
            action_id=0x0C,
            name='if-player-rank',
            params=[
                IScriptActionParamInfo(name='rank'),
                IScriptActionParamInfo(
                    name='then-jump',
                    size=2,
                    type=IScriptActionParamType.SCRIPT_JUMP_ADDR,
                ),
            ],
        ),
        IScriptActionInfo(
            action_id=0x0D,
            name='if-has-gold',
            params=[
                IScriptActionParamInfo(
                    name='then-jump',
                    size=2,
                    type=IScriptActionParamType.SCRIPT_JUMP_ADDR,
                ),
            ],
        ),
        IScriptActionInfo(
            action_id=0x0E,
            name='set-quest-complete',
            params=[
                IScriptActionParamInfo(name='quest'),
            ],
        ),
        IScriptActionInfo(
            action_id=0x0F,
            name='show-buy-sell-menu',
            params=[
                IScriptActionParamInfo(
                    name='if-buy-then-jump',
                    size=2,
                    type=IScriptActionParamType.SCRIPT_JUMP_ADDR,
                ),
            ],
        ),
        IScriptActionInfo(
            action_id=0x10,
            name='take-item',
            params=[
                IScriptActionParamInfo(name='item-id'),
            ],
        ),
        IScriptActionInfo(
            action_id=0x11,
            name='show-sell-menu',
            params=[
                IScriptActionParamInfo(
                    name='sellable-items',
                    size=2,
                    type=IScriptActionParamType.SHOP_ADDR,
                ),
            ],
        ),
        IScriptActionInfo(
            action_id=0x12,
            name='if-has-item',
            params=[
                IScriptActionParamInfo(name='item-id'),
                IScriptActionParamInfo(
                    name='then-jump',
                    size=2,
                    type=IScriptActionParamType.SCRIPT_JUMP_ADDR,
                ),
            ],
        ),
        IScriptActionInfo(
            action_id=0x13,
            name='add-hp',
            params=[
                IScriptActionParamInfo(name='amount'),
            ],
        ),
        IScriptActionInfo(
            action_id=0x14,
            name='show-password',
        ),
        IScriptActionInfo(
            action_id=0x15,
            name='end-game',
        ),
        #IScriptActionInfo(
        #    action_id=0x16,
        #    name='unknown',
        #    params=[
        #        IScriptActionParamInfo(name='unknown',
        #                           size=1),
        #    ],
        #),
        IScriptActionInfo(
            action_id=0x17,
            name='jump',
            params=[
                IScriptActionParamInfo(
                    name='addr',
                    size=2,
                    type=IScriptActionParamType.SCRIPT_JUMP_ADDR,
                ),
            ],
            ends=True,
        ),
    ]
}


#: A mapping of action type names to action definitions.
ACTION_TYPES_BY_NAME = {
    action_type.name: action_type
    for action_type in ACTION_TYPES.values()
}


#: A mapping of numeric entity IDs to names.
ENTITY_MAP = {
    0x00: 'generic',
    0x80: 'king',
    0x81: 'guru',
    0x82: 'martial-artist',
    0x83: 'magician',
    0x84: 'doctor',
    0x85: 'xxx-5',
    0x88: 'meat-salesman',
    0x89: 'tools-salesman',
    0x8A: 'key-salesman',
}


#: A mapping of entity names to numeric IDs.
ENTITY_REVERSE_MAP = {
    name: value
    for value, name in ENTITY_MAP.items()
}


# NOTE: There are 4 scripts in the game not actually defined in this
#       list, and several entries here that are reused.
DEFAULT_ISCRIPT_ORDER = [
    'intro-exposition',
    'eolis-first-walking-man',
    'mark-of-jack',
    'a0b1',
    'eolis-guru',
    'a0c9',
    'eolis-smoking-man',
    'eolis-kings-guard',
    'eolis-king',
    'a0ee',
    'a0f8',
    'eolis-meat-shop',
    'eolis-key-shop',
    'eolis-tool-shop',
    'eolis-magic-shop',
    'eolis-martial-arts',
    'a10b',
    'a116',
    'a121',
    'a12c',
    'a137',
    'apolune-doctor',
    'a13b',
    'a146',
    'a151',
    'apolune-tool-shop',
    'apolune-key-shop',
    'a155',
    'apolune-guru',
    'before-apolune-tool-shop',
    'intro-exposition',
    'remember-your-mantra',
    'forepaw-greeter',
    'a162',
    'a16d',
    'a178',
    'a18a',
    'spring-of-sky',
    'spring-of-trunk',
    'a1c3',
    'forepaw-tool-shop',
    'forepaw-guru',
    'forepaw-doctor',
    'forepaw-key-shop',
    'forepaw-meat-shop',
    'intro-exposition',
    'intro-exposition',
    'intro-exposition',
    'a1d9',
    'a1e4',
    'a1ef',
    'a1fa',
    'a205',
    'overworld-mist-house-man',
    'overworld-mist-house-woman',
    'a226',
    'mascon-doctor',
    'mascon-tool-shop',
    'mascon-meat-shop',
    'mascon-key-shop',
    'after-mascon-tool-shop',
    'mascon-guru',
    'intro-exposition',
    'intro-exposition',
    'a231',
    'a23c',
    'a247',
    'a252',
    'a266',
    'a271',
    'a27c',
    'victim-doctor',
    'victim-tool-shop',
    'victim-meat-shop',
    'victim-key-shop',
    'after-victim-magic-shop',
    'victim-guru',
    'intro-exposition',
    'intro-exposition',
    'intro-exposition',
    'a290',
    'a29b',
    'a2a6',
    'a2b8',
    'a2c3',
    'conflate-guru',
    'conflate-doctor',
    'conflate-tool-shop',
    'conflate-meat-shop',
    'intro-exposition',
    'intro-exposition',
    'intro-exposition',
    'intro-exposition',
    'intro-exposition',
    'intro-exposition',
    'intro-exposition',
    'a2ce',
    'a2d9',
    'a2e4',
    'a2ef',
    'a2fa',
    'a305',
    'daybreak-tool-shop',
    'daybreak-meat-shop',
    'daybreak-key-shop',
    'daybreak-guru',
    'intro-exposition',
    'intro-exposition',
    'intro-exposition',
    'intro-exposition',
    'intro-exposition',
    'intro-exposition',
    'a310',
    'overworld-house-man',
    'overworld-house-woman',
    'a331',
    'fraternal-guru',
    'dartmoor-tool-shop',
    'dartmoor-meat-shop',
    'dartmoor-key-shop',
    'guru-final',
    'eolis-king-glad-you-are-back',
    'dartmoor-doctor',
    'mark-of-queen',
    'mark-of-king',
    'mark-of-ace',
    'mark-of-joker',
    'need-ring-for-door',
    'used-red-potion',
    'used-mattock',
    'used-hourglass',
    'used-wingboots',
    'used-key',
    'used-elixir',
    'got-elixir',
    'got-red-potion',
    'got-mattock',
    'got-wingboots',
    'got-hourglass',
    'got-battle-suit',
    'got-battle-helmet',
    'got-dragon-slayer',
    'got-black-onyx',
    'got-pendant',
    'got-magical-rod',
    'touched-poison',
    'got-power-glove',
    'power-glove-gone',
    'ointment-used',
    'ointment-gone',
    'wingboots-gone',
    'hourglass-gone',
]
