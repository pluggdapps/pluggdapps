# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 Netscale Computing

from   pprint import pprint
from   copy   import deepcopy
import os.path, io

from   pluggdapps.const      import SPECIAL_SECS
from   pluggdapps.plugin     import PluginMeta, implements, Plugin, \
                                    pluginname, applications
from   pluggdapps.platform   import defaultsettings
from   pluggdapps.interfaces import ICommand
import pluggdapps.utils as h

class CommandLs( Plugin ):
    """Subcommand for pa-script to list various information about pluggdapps
    environment."""
    implements( ICommand )

    description = "list various information about Pluggdapps environment."
    cmd = 'ls'

    #---- ICommand API
    def subparser( self, parser, subparsers ):
        self.subparser = subparsers.add_parser( 
                                self.cmd, description=self.description )
        self.subparser.set_defaults( handler=self.handle )
        self.subparser.add_argument( "-p", dest="plugin",
                                     default=None,
                                     help="Plugin name" )
        self.subparser.add_argument( "-i", dest="interface",
                                     default=None,
                                     help="Interface name" )
        self.subparser.add_argument( "-s", dest="ls_summary",
                                     action="store_true", default=False,
                                     help="Summary of pluggdapps environment" )
        self.subparser.add_argument( "-m", dest="ls_implementers",
                                     action="store_true", default=False,
                                     help="list of interfaces and their "
                                          "plugins" )
        self.subparser.add_argument( "-M", dest="ls_implementers_r",
                                     action="store_true", default=False,
                                     help="list of plugins and interfaces they "
                                          "implement" )
        self.subparser.add_argument( "-e", dest="ls_settings",
                                     default=None,
                                     help="Settings of pluggdapps environment, "
                                          "special plugin wa default")
        self.subparser.add_argument( "-K", dest="ls_packages",
                                     action="store_true", default=False,
                                     help="List of pluggdapps packages loaded" )
        self.subparser.add_argument( "-W", dest="ls_webapps",
                                     action="store_true", default=False,
                                     help="List all web application and its "
                                          "mount configuration" )
        self.subparser.add_argument( "-P", dest="ls_plugins", 
                                     action="store_true", default=False,
                                     help="List plugins defined" )
        self.subparser.add_argument( "-I", dest="ls_interfaces",
                                     action="store_true", default=False,
                                     help="List interfaces defined" )
        return parser

    def handle( self, args ):
        opts = [ 'ls_summary', 'ls_settings', 'ls_plugins', 'ls_interfaces',
                 'ls_webapps', 'ls_packages', 'ls_implementers',
                 'ls_implementers_r' ]
        for opt in opts :
            if getattr( args, opt, False ) :
                getattr( self, opt )( args )
                break
        else :
            if args.interface :
                self.ls_interface( args )
            elif args.plugin :
                self.ls_plugin( args )

    #---- Internal functions
    def ls_summary( self, args ):
        import pluggdapps

        webapps = getattr( self.pa, 'webapps', {} ).keys()
        print( "Pluggdapps environment" )
        print( "  Configuration file : %s" % self.pa.inifile )
        print( "  Port               : %s" % (self.pa.port or None) )
        print( "  Loaded packages    : %s" % len(pluggdapps.packages) )
        print( "  Interfaces defined : %s" % len(PluginMeta._interfmap) )
        print( "  Plugins loaded     : %s" % len(PluginMeta._pluginmap) )
        print( "  Applications loaded: %s" % len(applications()) )
        print( "Web-application instances")
        pprint( list(webapps), indent=2 )

    def ls_settings( self, args ):
        sett = deepcopy( self.pa.settings )
        if args.ls_settings.startswith('spec') :
            print( "Special sections" )
            pprint(
                { k : sett.pop( k, {} ) for k in SPECIAL_SECS+['DEFAULT'] },
                indent=2 )
        elif args.ls_settings.startswith('plug') :
            print( "Plugin sections" )
            pprint(
                { k : sett[k] for k in sett if h.is_plugin_section(k) },
                indent=2 )
        elif args.ls_settings.startswith('wa') and args.plugin :
            webapps = getattr( self.pa, 'webapps', {} )
            for instkey, webapp in webapps.items() :
                appsec, t, moutname, instconfig = instkey
                if h.sec2plugin( appsec ) == args.plugin :
                    print( "Settings for %r" % (instkey,) )
                    pprint( webapp.appsettings, indent=2 )
                    print()
        elif args.ls_settings.startswith('def') and args.plugin :
            print( "Default settings for plugin %r" % args.plugin )
            pprint( defaultsettings().get( h.plugin2sec(args.plugin), {} ),
                    indent=2 )

    def ls_plugins( self, args ):
        l = sorted( list( PluginMeta._pluginmap.items() ))
        for pname, info in l :
            print(( "  %-15s in %r" % ( pname, info['file']) ))


    def ls_interfaces( self, args ):
        l = sorted( list( PluginMeta._interfmap.items() ))
        for iname, info in l :
            print(( "  %-15s in %r" % (iname, info['file']) ))

    def ls_interface( self, args ):
        nm = args.interface
        info = PluginMeta._interfmap.get( nm, None )
        if info == None :
            print( "Interface %r not defined" % nm )
        else :
            print( "\nAttribute dictionary : " )
            pprint( info['attributes'], indent=4 )
            print( "\nMethod dictionary : " )
            pprint( info['methods'], indent=4 )
            print( "\nPlugins implementing interface" )
            plugins = PluginMeta._implementers.get( info['cls'], {} )
            pprint( plugins, indent=4 )

    def ls_plugin( self, args ):
        from  pluggdapps.web.webapp import WebApp
        for instkey, webapp in self.pa.webapps.items() :
            appsec, t, mountname, config = instkey
            if h.sec2plugin( appsec ) == args.plugin :
                print("Mounted app %r" % appsec )
                print("  Instkey   : ", end='')
                pprint( webapp.instkey, indent=4 )
                print("  Script    : ", webapp.script )
                print("  Subdomain : ", webapp.subdomain )
                print("  Router    : ", webapp.router )
                print("Application settings")
                pprint( webapp.appsettings, indent=4 )
                print()

    def ls_webapps( self, args ):
        print( "[webmounts]")
        pprint( self.pa.webapps, indent=2 )
        print( "\nWeb-apps mounted as script" )
        pprint( self.pa.m_scripts, indent=2 )
        print( "\nWeb-apps mounted as subdomain" )
        pprint( self.pa.m_subdomains, indent=2 )

    def ls_packages( self, args ):
        import pluggdapps
        print( "List of loaded packages" )
        pprint( pluggdapps.packages, indent=2 )

    def ls_implementers( self, args ):
        print("List of interfaces and plugins implementing them")
        print()
        for i, pmap in PluginMeta._implementers.items() :
            print( "  %-15s" % i.__name__, end='' )
            pprint( list( pmap.keys() ), indent=8 )

    def ls_implementers_r( self, args ):
        print("List of plugins and interfaces implemented by them")
        for name, info in PluginMeta._pluginmap.items() :
            intrfs = list( map( lambda x : x.__name__, info['cls']._interfs ))
            print( "  %-20s" % name, end='' )
            pprint( intrfs, indent=8 )
