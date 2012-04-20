# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

from   optparse   import OptionParser
from   pprint     import pprint
import logging

from   pluggdapps.plugin        import Plugin, implements
from   pluggdapps.interfaces    import ICommand
import pluggdapps.util          as h

log = logging.getLogger( __name__ )

class Mounts( Plugin ):
    implements( ICommand )

    description = "Display application's configuration settings."
    usage = "usage: pa [options] commands"

    def __init__( self, platform, argv=[] ):
        self.platform = platform
        parser = self._parse( Mounts.usage )
        self.options, self.args = parser.parse_args( argv )

    def argparse( self, argv ):
        parser = self._parse( List.usage )
        self.options, self.args = parser.parse_args( argv )
        return self.options, self.args

    def run( self, options=None, args=[] ):
        options = options or self.options
        args = args or self.args
        if options.subdomains :
            print "Applications mounted on subdomain : \n"
            pprint( self.platform.on_subdomains )
            print
        elif options.scripts :
            print "Applications mounted on script path : \n"
            pprint( self.platform.on_scripts )
            print
        else :
            print "Applications mounted on subdomain : \n"
            pprint( self.platform.on_subdomains )
            print "\nApplications mounted on script path : \n"
            pprint( self.platform.on_scripts )
            print

    def _parse( self, usage ):
        return self._options( OptionParser( usage=usage ))

    def _options( self, parser ):
        parser.add_option( "-s", action="store_true", dest="scripts",
                           help="List of script mounts" )
        parser.add_option( "-d", action="store_true", dest="subdomains",
                           help="List of domain mounts" )
        return parser
