# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

from   pprint                   import pprint
from   optparse                 import OptionParser

from   pluggdapps.plugin        import PluginMeta, Plugin, implements
from   pluggdapps.helper        import docstr
from   pluggdapps.interfaces    import ICommand


class List( Plugin ):
    implements( ICommand )

    description = "list of plugins, interfaces."
    usage = "usage: pa [options] list [list_options] <module>"

    def __init__( self, platform, argv=[] ):
        self.platform = platform
        parser = self._parse( List.usage )
        self.options, self.args = parser.parse_args( argv )

    def argparse( self, argv ):
        parser = self._parse( List.usage )
        self.options, self.args = parser.parse_args( argv )
        return self.options, self.args

    def run( self, options=None, args=[] ):
        options = options or self.options
        args = args or self.args
        if options.listinterfs :
            self._listinterfs( options, args )
        elif options.listplugins :
            self._listplugins( options, args )
        elif options.interface :
            self._listinterf( options, args )
        elif options.plugin :
            self._listplugin( options, args )
        else :
            self._listinterfs( options, args )

    def _parse( self, usage ):
        return self._options( OptionParser( usage=usage ))

    def _options( self, parser ):
        parser.add_option( "-I", "--interfaces",
                           action="store_true", dest="listinterfs",
                           help="List interfaces defined" )
        parser.add_option( "-P", "--plugins",
                           action="store_true", dest="listplugins",
                           help="List plugins defined")
        parser.add_option( "-i", dest="interface",
                           help="List interface definition" )
        parser.add_option( "-p", dest="plugin",
                           help="List plugin definition")
        return parser

    def _listinterfs( self, options, args ):
        for iname, info in list( PluginMeta._interfmap.items() ) :
            print(( "%s in %r" % (iname, info['file']) ))
            for line in docstr( info['cls'] ).splitlines() :
                print(( "    ", line.strip() ))
            print()

    def _listplugins( self, options, args ):
        for pname, info in list( PluginMeta._pluginmap.items() ) :
            print(( "%-15s: defined as %r in %r" % (
                        pname, info['name'], info['file']) ))

    def _listinterf( self, options, args ):
        nm = options.interface
        info = PluginMeta._interfmap.get( nm, None )
        if info == None :
            print(( "Interface %r not defined" % nm ))
        else :
            print(( "%-15s: defined as %r in %r" % (
                        nm, info['name'], info['file']) ))
            print( "\nConfiguration dictionary" )
            pprint( info['config'] )
            print( "\nAttribute dictionary" )
            pprint( info['attributes'] )
            print( "\nMethod dictionary" )
            pprint( info['methods'] )

    def _listplugin( self, options, args ):
        nm = options.plugin
        info = PluginMeta._pluginmap.get( nm, None )
        if info == None :
            print(( "Plugin %r not defined" % nm ))
        else :
            print(( "%-15s: defined as %r in %r" % (
                        nm, info['name'], info['file']) ))
            print( "\nConfiguration dictionary" )
            pprint( info['config'] )

