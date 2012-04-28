# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

from   optparse   import OptionParser
from   pprint     import pprint
import logging

from   pluggdapps.plugin        import Plugin, implements, query_plugin,\
                                       IApplication
from   pluggdapps.interfaces    import ICommand
import pluggdapps.helper        as h

log = logging.getLogger(__name__)

class Config( Plugin ):
    implements( ICommand )

    description = "Display application's configuration settings."
    usage = "usage: pa [options] commands"

    def __init__( self, platform, argv=[] ):
        self.platform = platform
        parser = self._parse( Config.usage )
        self.options, self.args = parser.parse_args( argv )

    def argparse( self, argv ):
        parser = self._parse( List.usage )
        self.options, self.args = parser.parse_args( argv )
        return self.options, self.args

    def run( self, options=None, args=[] ):
        from pluggdapps.config import default_appsettings, load_inisettings
        from pluggdapps import ROOTAPP
        options = options or self.options
        args = args or self.args

        appname = options.appname or ROOTAPP
        if options.defsett :
            appsett = default_appsettings
        elif options.inisett :
            appsett = load_inisettings( platform.inifile )

        app = query_plugin( appname, IApplication, appname )
        appsett = app.settings

        plugin = options.plugin and ('plugin:' + options.plugin)
        if plugin in appsett :
            pprint( appsett[plugin] )
        else :
            pprint( appsett )

    def _parse( self, usage ):
        return self._options( OptionParser( usage=usage ))

    def _options( self, parser ):
        parser.add_option( "-a", dest="appname", default=None,
                           help="application's settings" )
        parser.add_option( "-p", dest="plugin", default=None,
                           help="plugin's settings" )
        parser.add_option( "-d", action="store_true", dest="defsett",
                           help="Show default settings" )
        parser.add_option( "-i", action="store_true", dest="inisett",
                           help="Show Ini settings" )
        return parser

