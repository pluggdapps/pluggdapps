# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 Netscale Computing

from   pprint     import pprint

from   pluggdapps.plugin        import implements, Plugin, pluginname
from   pluggdapps.interfaces    import ICommand
import pluggdapps.utils         as h


class Mounts( Plugin ):
    implements( ICommand )

    description = "Display application's configuration settings."

    def subparser( self, parser, subparsers ):
        name = pluginname( self )
        self.subparser = subparsers.add_parser( 
                                name, description=self.description )
        self.subparser.set_defaults( handler=self.handle )
        self._arguments( self.subparser )

    def handle( self, args ):
        from  pluggdapps.platform import m_subdomains, m_scripts
        if args.subdomains :
            print( "Applications mounted on subdomain : " )
            pprint( m_subdomains )
            print()
        elif args.scripts :
            print( "Applications mounted on script path : " )
            pprint( m_scripts )
            print()
        else :
            print( "Applications mounted on subdomain : " )
            pprint( m_subdomains )
            print( "\nApplications mounted on script path : " )
            pprint( m_scripts )
            print()

    def _arguments( self, parser ):
        parser.add_argument( "-s", action="store_true", dest="scripts",
                             help="List of script mounts" )
        parser.add_argument( "-d", action="store_true", dest="subdomains",
                             help="List of domain mounts" )
        return parser
