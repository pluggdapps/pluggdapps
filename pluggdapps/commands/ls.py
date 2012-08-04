# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 Netscale Computing

from   pprint import pprint
import os.path

from   pluggdapps.plugin import PluginMeta, implements, Plugin, pluginname
from   pluggdapps.interfaces import ICommand
import pluggdapps.utils as h

class CommandLs( Plugin ):
    implements( ICommand )

    description = "list of plugins, interfaces."
    cmd = 'ls'

    def subparser( self, parser, subparsers ):
        self.subparser = subparsers.add_parser( 
                                self.cmd, description=self.description )
        self.subparser.set_defaults( handler=self.handle )
        self._arguments( self.subparser )

    def handle( self, args ):
        if args.listinterfs :
            self._listinterfs( args )
        elif args.listplugins :
            self._listplugins( args )
        elif args.interface :
            self._listinterf( args )
        elif args.plugin :
            self._listplugin( args )
        elif args.listall :
            self._listall( args )
        else :
            self._listall( args )

    def _arguments( self, parser ):
        parser.add_argument( "-l", action="store_true", 
                             dest="listall",
                             help="List interfaces defined" )
        parser.add_argument( "-I", action="store_true", 
                             dest="listinterfs",
                             help="List interfaces defined" )
        parser.add_argument( "-P", action="store_true",
                             dest="listplugins",
                             help="List plugins defined" )
        parser.add_argument( "-i",
                             dest="interface",
                             help="List interface definition" )
        parser.add_argument( "-p",
                             dest="plugin",
                             help="List plugin definition" )
        return parser

    def _listall( self, args ):
        l = sorted( list( PluginMeta._interfmap.items() ))
        print( "Interfaces specified" )
        for iname, info in l :
            print(( "  %s in %r" % (iname, info['file']) ))
        print( "\nPlugins defined" )
        l = sorted( list( PluginMeta._pluginmap.items() ))
        for pname, info in l :
            print(( "  %-15s in %r" % ( pname, info['file']) ))
        print( "\nInterfaces and implementing plugins" )
        for interf, d in PluginMeta._implementers.items() :
            print( "  %-15s" % interf.__name__, end='' )
            clss = [ cls for name, cls in sorted( list( d.items() )) ]
            pprint( clss, indent=17 )
            print("")

    def _listinterfs( self, args ):
        l = sorted( list( PluginMeta._interfmap.items() ))
        for iname, info in l :
            print(( "  %s in %r" % (iname, info['file']) ))
        #for iname, info in l :
        #    print(( "%s in %r" % (iname, info['file']) ))
        #    for line in h.docstr( info['cls'] ).splitlines() :
        #        print( "    ", line.strip() )
        #    print()

    def _listinterf( self, args ):
        nm = args.interface
        info = PluginMeta._interfmap.get( nm, None )
        if info == None :
            print( "Interface %r not defined" % nm )
        else :
            print( "\n%-15s " % nm )
            print( "\nAttribute dictionary : " )
            pprint( info['attributes'], indent=4 )
            print( "\nMethod dictionary : " )
            pprint( info['methods'], indent=4 )
            print( "\nPlugins implementing interface" )
            plugins = PluginMeta._implementers.get( info['cls'], {} )
            pprint( plugins, indent=4 )

    def _listplugins( self, args ):
        l = sorted( list( PluginMeta._pluginmap.items() ))
        for pname, info in l :
            print(( "  %-15s in %r" % ( pname, info['file']) ))

    def _listplugin( self, args ):
        nm = args.plugin
        info = PluginMeta._pluginmap.get( nm, None )
        if info == None :
            print(( "Plugin %r not defined" % nm ))
        else :
            print(( "%-15s: defined as %r in %r" % (
                        nm, info['name'], info['file']) ))

