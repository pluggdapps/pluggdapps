# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 Netscale Computing

from pprint import pprint
import logging

from pluggdapps.const import ROOTAPP
from pluggdapps.config import default_appsettings, load_inisettings
from pluggdapps.plugin import Plugin, query_plugin, IWebApp
from pluggdapps.core import implements, pluginname
from pluggdapps.interfaces import ICommand
import pluggdapps.utils as h


log = logging.getLogger(__name__)

class Config( Plugin ):
    implements( ICommand )

    description = "Display application's configuration settings."

    def subparser( self, parser, subparsers ):
        name = pluginname( self )
        self.subparser = subparsers.add_parser( 
                                name, description=self.description )
        self.subparser.set_defaults( handler=self.handle )
        self._arguments( self.subparser )

    def handle( self, args ):
        appname = args.appname or ROOTAPP
        if args.defsett :
            appsett = default_appsettings()
        elif args.inisett :
            appsett = load_inisettings( platform.inifile )
        else :
            app = query_plugin( appname, IWebApp, appname )
            appsett = app.settings

        plugin = args.plugin and ('plugin:' + args.plugin)
        if plugin in appsett :
            pprint( appsett[plugin] )
        else :
            pprint( appsett )

    def _arguments( self, parser ):
        parser.add_argument( "-a", dest="appname", default=None,
                             help="application's settings" )
        parser.add_argument( "-p", dest="plugin", default=None,
                             help="plugin's settings" )
        parser.add_argument( "-d", action="store_true", dest="defsett",
                             help="Show default settings" )
        parser.add_argument( "-i", action="store_true", dest="inisett",
                             help="Show Ini settings" )
        return parser

