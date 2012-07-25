# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 Netscale Computing

from   pprint import pprint

from   pluggdapps.config     import defaultsettings, loadsettings, app2sec, \
                                    sec2app, plugin2sec, sec2plugin
from   pluggdapps.plugin     import implements, IWebApp, Plugin, pluginname
from   pluggdapps.platform   import Pluggdapps
from   pluggdapps.interfaces import ICommand
import pluggdapps.utils      as h


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
        from  pluggdapps.platform import Pluggdapps, settings
        if args.modname :
            print( "Settings for module %r" % args.modname )
            pprint( settings.get( args.modname, None ))
            return

        if args.defsett :
            appdefaults, plugindefaults = defaultsettings()
            if args.appname :
                print( "Default settings for web-app %r" % args.appname )
                pprint( appdefaults.get( app2sec(args.appname), None ))
            if args.plugin :
                print( "Default settings for plugin %r" % args.plugin )
                pprint( plugindefaults.get( plugin2sec(args.plugin), None ))
            if (args.plugin, args.appname) == (None, None) :
               print( "Default settings for all web-apps" )
               pprint( appdefaults )
               print( "Default settings for all plugins" )
               pprint( plugindefaults )

        else :
            if args.appname :
                webapp = Pluggdapps.webapps.get( args.appname, None )
                if webapp == None :
                    raise Exception( "Web-app %r is not found" % args.appname )
                instsett = settings.get( webapp.instkey, {} )

            if args.appname and args.plugin :
                s = instsett.get( plugin2sec(args.plugin), None )
                print( "%r plugin settings for application %r" % (
                       args.plugin, args.appname) )
                pprint( s )

            elif args.plugin :
                s = settings.get( plugin2sec(args.plugin), None )
                print( "%r plugin settings" % args.plugin )
                pprint( s )

            elif args.appname :
                print( "Application settings for %r" % args.appname )
                pprint( instsett )

            else :
                print( "Full settings" )
                pprint( settings )


    def _arguments( self, parser ):
        parser.add_argument( "-a", 
                             dest="appname", default=None,
                             help="application's settings" )
        parser.add_argument( "-m", 
                             dest="modname", default=None,
                             help="module settings" )
        parser.add_argument( "-p", 
                             dest="plugin", default=None,
                             help="plugin's settings" )
        parser.add_argument( "-d", action="store_true", 
                             dest="defsett",
                             help="Show default settings" )
        return parser

