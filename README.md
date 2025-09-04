Faxanatools
===========

[Faxanadu](https://www.mobygames.com/game/7331/faxanadu/) is a criminally
under-appreciated game for the NES, combining action, platforming, and some
puzzle-solving with an atmosphere you don't often see on the NES.

I've been working on a project for doing a full disassembly of the game, and
have found some interesting elements, including level select code and a full
interaction scripting language. In order to better work on this project and to
play around with what I've learned, I built Faxanatools.

Faxanatools is a Python package and command line tool for dumping content
from Faxanadu ROMs, modifying the content, and injecting back in. It can
be used today to customize some aspects of the game, and the hope is that,
down the road, it can be used to craft whole new adventures for our little
Faxanadu hero.


# Installation

For now, there are no released packages. You can install straight from the
source tree:

```shell
$ pip install -e .
```


# Capabilities

This can dump and patch the following information:

* Message strings used for dialogue interactions and some events.

* Interaction scripts used for interacting with NPCs, shops, items, and
  certain events.

* Shop items and prices.

Specifics will be documented as part of my disassembly effort.


# Usage

## Dump information from a Faxanadu ROM

```shell
$ faxanatool --dump faxanadu.nes --dump-file=faxanadu.json
```


## Patch a Faxanadu ROM from a Faxanatools JSON file

```shell
$ faxanatool --patch faxanadu.nes --dump-file=faxanadu.json
```


# Notes

Some caveats:

* This has only been tested with a ``Faxanadu (U).nes`` ROM file with a
  SHA1 of ``a59d8f3877aa63b4ce1449dca23f3fd686896505``.

* Interaction scripts are limited to a resulting byte size of 1,582 bytes.
