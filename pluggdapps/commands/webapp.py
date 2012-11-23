# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 Netscale Computing

import os

from   pluggdapps.plugin     import implements, Plugin
from   pluggdapps.interfaces import ICommand, IScaffold
import pluggdapps.utils as h

class CommandWebApp( Plugin ):
    """Subcommand to create scaffolding logic for web-application under a
    project."""
    implements( ICommand )

    description = "Create scaffolding logic for web-application under project"
    cmd = 'webapp'

    #---- ICommand API
    def subparser( self, parser, subparsers ):
        self.subparser = subparsers.add_parser( 
                                self.cmd, description=self.description )
        self.subparser.set_defaults( handler=self.handle )
        self.subparser.add_argument( 'name',
                                     help="Web application name" )
        return parser

    def handle( self, args ):
        sett = { 'target_dir'  : os.getcwd(),
                 'webapp_name' : args.name }

        scaff = self.query_plugin( 
                        IScaffold, 'scaffoldingwebapp', settings=sett )
        scaff.query_cmdline()
        print( "Generating Web-application %s" % args.name )
        scaff.generate()
