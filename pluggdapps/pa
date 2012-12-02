#! /usr/bin/env python3.2

# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

"""Command line program to work with pluggdapps-platform. Use --help to learn
more about each sub-command and its options.
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
                             help="Start monitor process" )
    mainparser.add_argument( '-c', dest='config', 
                             default=DEFAULT_INI,
                             help="specify config file(s)" )
    mainparser.add_argument( '-w', dest='webapps',
                             action='store_true', default=False,
                             help="load with web-framework" )
    return mainparser

def main():
    # Create command line parser.
    # Get a list of sub-commands supported in command line.
    # Take only the command-line parameters uptil a subcommand.
    mainparser = mainoptions()
    subcmds = [ x[7:] for x in PluginMeta._implementers[ ICommand ].keys() ]
    mainargs = h.takewhile( lambda x : x not in subcmds, sys.argv[1:] )
    args = mainparser.parse_args( mainargs )

    # pluggdapps platform object.
    if not args.config :
        print("Please supply a configuration file. Do -h for help")
        sys.exit(1)

    if args.webapps :
        pa = Webapps.boot( args.config )
        subcommands = pa.query_plugins( pa, None, ICommand )
    else :
        pa = Pluggdapps.boot( args.config )
        subcommands = pa.query_plugins( pa, ICommand )

    # setup sub-command arguments
    subparsers = mainparser.add_subparsers( help="Sub-commands" )
    [ subcmd.subparser( mainparser, subparsers ) for subcmd in subcommands ]

    # Do a full parsing of command line arguments.
    args = mainparser.parse_args()

    # Handle subcommand
    args.handler( args )


if __name__ == '__main__' :
    main()
