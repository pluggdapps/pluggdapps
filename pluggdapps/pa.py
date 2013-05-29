#! /usr/bin/env python3.2

# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

"""Control and inspect pluggdapps environment using command line script.
Almost all functions of command line script are implemented as sub-commands.
To get a quick summary of available sub-commads, do,

.. code-block:: bash
    :linenos:

    $ pa commands

To learn more about available subcommand refer to :mod:`pluggdapps.commands`
package. Since sub commands are implemented as plugins, there can be other
sub-commands implemented by different package. Refer to corresponding package
for their documentation.

You can also use `--help` on the sub-command for supported options.

.. code-block:: bash
    :linenos:

    $ pa --help

    usage: pa [-h] [-m] [-c CONFIG] [-w]

    Pluggdapps command line script.

    optional arguments:
      -h, --help  show this help message and exit
      -m          Start monitor process.
      -c CONFIG   Specify config file.
      -w          Load platform with web-framework


"""

import sys
from   argparse     import ArgumentParser

import pluggdapps
from   pluggdapps.const      import DEFAULT_INI
from   pluggdapps.platform   import Pluggdapps, Webapps
from   pluggdapps.plugin     import PluginMeta
from   pluggdapps.interfaces import ICommand
import pluggdapps.utils      as h


def mainoptions():
    # setup main script arguments
    description = "Pluggdapps command line script."
    mainparser = ArgumentParser( description=description )
    mainparser.add_argument( '-m', dest='monitor',
                             action='store_true', default=False,
                             help="Start monitor process." )
    mainparser.add_argument( '-c', dest='config', 
                             default=DEFAULT_INI,
                             help="Specify config file." )
    mainparser.add_argument( '-w', dest='webapps',
                             action='store_true', default=False,
                             help="Load platform with web-framework" )
    return mainparser

def main():
    from pluggdapps import loadpackages
    import pluggdapps.commands

    loadpackages()  # This is important, otherwise plugins in other packages 
                    # will not be detected.

    # Create command line parser.
    # Get a list of sub-commands supported in command line.
    # Take only the command-line parameters uptil a subcommand.
    mainparser = mainoptions()
    mainargs = pluggdapps.commands.mainargs(
                        ICommand, 'pluggdapps.*', sys.argv[1:])
    args = mainparser.parse_args( mainargs )

    if args.webapps :
        pa = Webapps.boot( args.config )
        subcommands = pa.qpr( pa, None, ICommand, 'pluggdapps.*' )
    else :
        pa = Pluggdapps.boot( args.config )
        subcommands = pa.qpr( pa, ICommand, 'pluggdapps.*' )

    # setup sub-command arguments
    subparsers = mainparser.add_subparsers( help="Sub-commands" )
    [ subcmd.subparser( mainparser, subparsers ) for subcmd in subcommands ]

    # Do a full parsing of command line arguments.
    args = mainparser.parse_args()

    # Corresponding handler is expected to be registered during subparser()
    # call above.
    args.handler( args )

if __name__ == '__main__' :
    main()
