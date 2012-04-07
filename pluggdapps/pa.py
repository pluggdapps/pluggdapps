#! /usr/bin/env python

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

import sys
from   optparse      import OptionParser

import pluggdapps
from   plugincore    import plugin_init, plugin_names, query_plugin
from   interfaces    import ICommand

usage = "pa [options] <command> [command_options]"


def parse( usage ):
    """Parse master script options."""
    return options( OptionParser( usage=usage ))


    parser.add_option( '-d', action="store_true", dest='daemonize',
                       help="run server as a daemon")
    parser.add_option( '-p', '--pidfile', dest='pidfile', default=None,
                       help="store the process id in the given file")

def options( parser ):
    """Supported command options for master script."""
    parser.add_option( '-c', '--config', action="append", dest='config',
                       help="specify config file(s)" )
    parser.add_option( '-i', '--import', action="append", dest='imports',
                       help="specify modules to import")
    parser.add_option( '-e', '--environment', dest='environment', default=None,
                       help="apply the given config environment")
    parser.add_option( '--pa', action="append", dest='tostartpath', default=[],
                       help="add given paths to the beginning of sys.path")
    parser.add_option( '--pz', action="append", dest='toendpath', default=[],
                       help="add given paths to the end of sys.path")
    return parser


def docommand( command, argv ):
    """Handle sub-commands."""
    comm = query_plugin( ICommand, command, argv=argv )
    comm.run()


def doscript( paargs ):
    """Default handling for master script."""
    from  pluggdapps        import appsettings
    parser = parse( usage )
    options, args = parser.parse_args( paargs )

    # -c (config file)
    boot( inifile=options.config )

    # --pa option
    [ sys.path.insert(0, p) for p in options.tostartpath ]

    # --pz option
    [ sys.path.append(p) for p in options.toendpath ]

    # -i (import)
    sys.path.insert( 0, '' )
    [ exec( "import %s" % i ) for i in imports or [] ]

    # -e environment, setupt cmd-line environment options to appsetting's root
    if options.environment is not None :
        appsettings['root']['environment'] = options.environment


if __name__ == '__main__' :
    paargs, cmd, cmdargs = [], None, sys.argv[1:]
    plugin_init()
    commands = plugin_names( ICommand )
    while cmdargs :
        arg = cmdargs.pop(0)
        if arg in commands :
            cmd = arg
            break
        else :
            paargs.append( arg )
    doscript( paargs )
    docommand( cmd, cmdargs ) if cmd else None
