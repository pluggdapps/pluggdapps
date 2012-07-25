# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 Netscale Computing

from   pprint import pprint
import os.path

from   pluggdapps.plugin import PluginMeta, implements, Plugin, pluginname
from   pluggdapps.interfaces import ICommand
import pluggdapps.utils as h

class List( Plugin ):
    implements( ICommand )

    description = "list of plugins, interfaces."

    def subparser( self, parser, subparsers ):
        name = pluginname( self )
        self.subparser = subparsers.add_parser( 
                                name, description=self.description )
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
        else :
            self._listinterfs( args )

    def _arguments( self, parser ):
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

    def _listinterfs( self, args ):
        l = sorted( list( PluginMeta._interfmap.items() ))
        for iname, info in l :
            print(( "%s in %r" % (iname, info['file']) ))
            for line in h.docstr( info['cls'] ).splitlines() :
                print( "    ", line.strip() )
            print()

    def _listplugins( self, args ):
        l = sorted( list( PluginMeta._pluginmap.items() ))
        for pname, info in l :
            print(( "%-15s: in %r" % ( pname, info['file']) ))

    def _listinterf( self, args ):
        nm = args.interface
        info = PluginMeta._interfmap.get( nm, None )
        if info == None :
            print( "Interface %r not defined" % nm )
        else :
            print( "\n%-15s " % nm )
            print( "\nAttribute dictionary : " )
            pprint( info['attributes'] )
            print( "\nMethod dictionary : " )
            pprint( info['methods'] )

    def _listplugin( self, args ):
        nm = args.plugin
        info = PluginMeta._pluginmap.get( nm, None )
        if info == None :
            print(( "Plugin %r not defined" % nm ))
        else :
            print(( "%-15s: defined as %r in %r" % (
                        nm, info['name'], info['file']) ))

