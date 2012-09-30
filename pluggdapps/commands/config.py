# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 Netscale Computing

from   pprint import pprint

from   pluggdapps.plugin     import implements, IWebApp, Plugin, pluginname
from   pluggdapps.platform   import Pluggdapps
from   pluggdapps.interfaces import ICommand
import pluggdapps.utils      as h


class CommandConfig( Plugin ):
    implements( ICommand )

    description = "Display application's configuration settings."
    cmd = 'config'

    def subparser( self, parser, subparsers ):
        self.subparser = subparsers.add_parser( 
                                self.cmd, description=self.description )
        self.subparser.set_defaults( handler=self.handle )
        self._arguments( self.subparser )

    def handle( self, args ):
        from  pluggdapps.platform import Pluggdapps, settings
        if args.DEFAULT :
            print( "DEFAULT global Settings" )
            self.describe_config( pluggdapps.config.DEFAULT() )
            return

        if args.pluggdapps_default :
            print( "Pluggdapps module default Settings" )
            self.describe_config( pluggdapps.config.pluggdapps_defaultsett() )
            return

        if args.appname and args.pluginname :
            appsec = app2sec(args.appname)
            for k,sett in settings.items() :
                if not isinstance(k, tuple) : continue
                if k[0] != appsec : continue
                print( "%r plugin-settings for app-inst %r" % (
                        args.pluginname, k ))
                self.describe_config( sett[ plugin2sec(args.pluginname) ] )
            return

        if args.apps and args.defaultsett:
            appdefaults, plugindefaults = pluggdapps.config.defaultsettings()
            print( "Default settings for all applications" )
            pprint( list( appdefaults.keys() ), indent=4 )
            print("")
            self.describe_config( appdefaults )
            return
        elif args.apps :
            appdefaults, plugindefaults = pluggdapps.config.defaultsettings()
            print( "Application settings" )
            pprint( list( appdefaults.keys() ), indent=4 )
            print( "" )
            d = dict([ (k,v) 
                       for k, v in settings.items() 
                       if isinstance(k, tuple) and is_app_section(k[0]) ])
            self.describe_config( d )
            return

        if args.appname and args.defaultsett :
            appdefaults, plugindefaults = pluggdapps.config.defaultsettings()
            print( "%r default settings" % args.appname )
            appsett = appdefaults[ app2sec(args.appname) ]
            self.describe_config( appsett )
            return
        elif args.appname :
            print( "%r application settings" % args.appname )
            for k, sett in settings.items() :
                if isinstance(k, tuple) and sec2app(k[0]) == args.appname :
                    self.describe_config( sett )
            return

        if args.plugins and args.defaultsett :
            appdefaults, plugindefaults = pluggdapps.config.defaultsettings()
            print( "Default settings for all plugins" )
            pprint( list( plugindefaults.keys() ), indent=4 )
            print("")
            self.describe_config( plugindefaults )
            return
        elif args.plugins :
            print( "Plugin settings" )
            pprint( list( plugindefaults.keys() ), indent=4 )
            print( "" )
            d=dict([ (k,v) for k,v in settings.items() 
                           if (not isinstance(k, tuple)) and \
                                   is_plugin_section(k) ])
            self.describe_config( d )
            return

        if args.pluginname and args.defaultsett :
            appdefaults, plugindefaults = pluggdapps.config.defaultsettings()
            print( "%r default settings" % args.pluginname )
            pluginsett = plugindefaults[ plugin2sec(args.pluginname) ]
            self.describe_config( pluginsett )
            return
        elif args.pluginname :
            print( "%r plugin settings" % args.pluginname )
            self.describe_config( settings[ plugin2sec(args.pluginname) ] )
            return


    def describe_config( self, settings ):
        if isinstance( settings, h.ConfigDict ) :
            pprint( settings.specifications(), indent=4, width=80 )
        else :
            pprint( settings, indent=4, width=80 )


    def _arguments( self, parser ):
        parser.add_argument( "-D", action="store_true", 
                             dest="DEFAULT",
                             help="Show global default settings" )
        parser.add_argument( "-G", action="store_true", 
                             dest="pluggdapps_default",
                             help="Show default settings for pluggdapps module")
        parser.add_argument( "-d", action="store_true", 
                             dest="defaultsett",
                             help="Show default settings for plugin / app")
        parser.add_argument( "-A",  action="store_true",
                             dest="apps", default=None,
                             help="default settings for all application" )
        parser.add_argument( "-a", 
                             dest="appname", default=None,
                             help="default settings for application" )
        parser.add_argument( "-P",  action="store_true",
                             dest="plugins", default=None,
                             help="default settings for all plugin" )
        parser.add_argument( "-p", 
                             dest="pluginname", default=None,
                             help="default settings for plugin" )
        return parser

