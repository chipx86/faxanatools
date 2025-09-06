"""Command line tool for working with Faxanadu ROMs.

This can output content from a Faxanadu ROM or patch new data into a ROM.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from faxanatools.decoder import ROMReader
from faxanatools.deserializer import JSONDeserializer
from faxanatools.encoder import ROMPatcher
from faxanatools.rom import FaxanaduROM
from faxanatools.serializer import JSONSerializer


def add_common_rom_options(
    rom: FaxanaduROM,
    argparser: argparse.ArgumentParser,
) -> None:
    """Add common options for subcommands.

    Args:
        rom (faxanatools.rom.FaxanaduROM):
            The Faxanadu ROM information.

        argparser (argparse.ArgumentParser):
            The subcommand argument parser to add to.
    """
    argparser.add_argument(
        'filename',
        help='Path to the ROM file.',
    )

    argparser.add_argument(
        '--script-addrs-offset',
        help=(
            'Offset into the ROM where the IScript address offsets '
            'lookup table can be found.'
        ),
        default=hex(rom.iscript_addrs_offset),
    )
    argparser.add_argument(
        '--messages-offset',
        help='Offset into the ROM where the message strings can be found.',
        default=hex(rom.messages_offset),
    )
    argparser.add_argument(
        '--num-scripts',
        help='Number of scripts present in the table.',
        default=rom.max_iscript_addrs,
    )


def update_rom_information(
    argparser: argparse.ArgumentParser,
    rom: FaxanaduROM,
    options: argparse.Namespace,
) -> None:
    """Update the ROM information based on the parsed arguments.

    Args:
        argparser (argparse.ArgumentParser):
            The subcommand argument parser to add to.

        rom (faxanatools.rom.FaxanaduROM):
            The Faxanadu ROM information.

        options (argparser.Namespace):
            The parsed options.
    """
    try:
        if options.script_addrs_offset.startswith('0x'):
            script_addrs_offset = int(options.script_addrs_offset, 16)
        else:
            script_addrs_offset = int(options.script_addrs_offset)
    except ValueError:
        argparser.error('--script-addrs-offset must be a hex offset.')

    try:
        if options.messages_offset.startswith('0x'):
            messages_offset = int(options.messages_offset, 16)
        else:
            messages_offset = int(options.messages_offset)
    except ValueError:
        argparser.error('--strings-offset must be a hex offset.')

    filename = options.filename

    if not os.path.exists(filename):
        argparser.error('The ROM file was not found.')

    rom.messages_offset = messages_offset
    rom.iscript_addrs_offset = script_addrs_offset
    rom.max_iscript_addrs = options.num_scripts


def main() -> None:
    """Main entrypoint for faxanatool.

    Args:
        args (list of str):
            The command line arguments.
    """
    rom = FaxanaduROM()

    argparser = argparse.ArgumentParser()
    subparsers = argparser.add_subparsers(dest='action',
                                          required=True)

    # Create the "dump" subcommand.
    subparser = subparsers.add_parser('dump')
    subparser.add_argument(
        '--dump-file',
        help='Path to the dump file.',
        required=True,
    )
    add_common_rom_options(rom, subparser)

    # Create the "parse-password" subcommand.
    subparser = subparsers.add_parser('parse-password')
    subparser.add_argument(
        '--password',
        help='The password to parse',
        required=True,
    )

    # Create the "patch" subcommnad.
    subparser = subparsers.add_parser('patch')
    subparser.add_argument(
        '--dump-file',
        help='Path to the dump file.',
        required=True,
    )
    add_common_rom_options(rom, subparser)

    # Parse the command line options and run the command.
    options = argparser.parse_args(sys.argv[1:])

    COMMANDS[options.action](argparser=argparser,
                             options=options,
                             rom=rom)


def handle_dump_command(
    argparser: argparse.ArgumentParser,
    options: argparse.Namespace,
    rom: FaxanaduROM,
) -> None:
    """Handle the "dump" command.

    Args:
        argparser (argparse.ArgumentParser):
            The subcommand argument parser to add to.

        options (argparser.Namespace):
            The parsed options.

        rom (faxanatools.rom.FaxanaduROM):
            The Faxanadu ROM information.
    """
    dump_file = options.dump_file

    update_rom_information(argparser=argparser,
                           options=options,
                           rom=rom)

    # Read the ROM.
    rom_reader = ROMReader(rom=rom)
    rom_reader.read(options.filename)

    # Serialize to JSON.
    serializer = JSONSerializer(rom=rom)

    with open(dump_file, 'w') as fp:
        json.dump(serializer.serialize(),
                  fp,
                  sort_keys=True,
                  indent=True)

    print(f'Wrote Faxanadump file to {dump_file}')


def handle_patch_command(
    argparser: argparse.ArgumentParser,
    options: argparse.Namespace,
    rom: FaxanaduROM,
) -> None:
    """Handle the "patch" command.

    Args:
        argparser (argparse.ArgumentParser):
            The subcommand argument parser to add to.

        options (argparser.Namespace):
            The parsed options.

        rom (faxanatools.rom.FaxanaduROM):
            The Faxanadu ROM information.
    """
    dump_file = options.dump_file
    filename = options.filename

    if not os.path.exists(dump_file):
        argparser.error(f'The dump file ({dump_file}) was not found.')

    update_rom_information(argparser=argparser,
                           options=options,
                           rom=rom)

    # Patch the ROM.
    with open(dump_file, 'r') as fp:
        rom = (
            JSONDeserializer(json.load(fp))
            .deserialize()
        )

    patched_file = '%s-patched.nes' % filename.rstrip('.nes')

    rom_patcher = ROMPatcher(rom=rom)
    rom_patcher.patch(filename,
                      patched_filename=patched_file)

    print(f'Wrote patched file to {patched_file}')


COMMANDS = {
    'dump': handle_dump_command,
    'patch': handle_patch_command,
}
