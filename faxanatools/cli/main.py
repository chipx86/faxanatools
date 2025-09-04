"""Command line tool for working with Faxanadu ROMs.

This can output content from a Faxanadu ROM or patch new data into a ROM.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import TYPE_CHECKING

from faxanatools.decoder import ROMReader
from faxanatools.deserializer import JSONDeserializer
from faxanatools.encoder import ROMPatcher
from faxanatools.rom import FaxanaduROM
from faxanatools.serializer import JSONSerializer


def main() -> None:
    """Main entrypoint for faxanatool.

    Args:
        args (list of str):
            The command line arguments.
    """
    rom = FaxanaduROM()

    argparser = argparse.ArgumentParser()
    argparser.add_argument(
        'filename',
        help='Path to the ROM file.',
    )

    group = argparser.add_mutually_exclusive_group()
    group.add_argument(
        '--dump',
        action='store_const',
        dest='action',
        default='dump',
        const='dump',
        help='Dump state to a file.'
    )
    group.add_argument(
        '--patch',
        action='store_const',
        dest='action',
        const='patch',
        help='Write a patched ROM file instead of dumping.',
    )

    argparser.add_argument(
        '--dump-file',
        help='Path to the dump file.',
        required=True,
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

    options = argparser.parse_args(sys.argv[1:])

    # Validate and normalize our options.
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

    action = options.action
    dump_file = options.dump_file

    if action == 'dump':
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
    elif action == 'patch':
        if not os.path.exists(dump_file):
            argparser.error(f'The dump file ({dump_file}) was not found.')

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
