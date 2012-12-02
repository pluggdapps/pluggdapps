# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

import os
from   os.path                  import dirname, join, basename, abspath

import pluggdapps.utils             as h
from   pluggdapps.plugin            import implements, Plugin
from   pluggdapps.interfaces        import IScaffold, ICommand

_default_settings = h.ConfigDict()
_default_settings.__doc__ = (
    "Basic configuration settings for IScaffold interface specification."
)

_default_settings['template_dir']  = {
    'default' : join( dirname(__file__), 'webapp_template'),
    'types'   : (str,),
    'help'    : "Obsolute file path of template source-tree to be used for "
                "the scaffolding logic."
}
_default_settings['target_dir'] = {
    'default' : '',
    'types'   : (str,),
    'help'    : "Target directory to place the generate scaffolding logic."
}
_default_settings['webapp_name'] = {
    'default' : '',
    'types'   : (str,),
    'help'    : "Web application name."
}

class ScaffoldingWebApp( Plugin ):
    """Automatically generates scaffolding logic for a new web-application.
    It also implements :class:`pluggdapps.interfaces.ICommand` so that this
    can be invoked as a sub-command.
    """
    implements( IScaffold, ICommand )

    description = "Create scaffolding logic for a web application."

    #---- IScaffold API methods.

    def query_cmdline( self ):
        """:meth:`pluggdapps.interfaces.IScaffold.query_cmdline` interface
        method."""
        if self['target_dir'] == '' :
            self['target_dir'] = input( 
                    "Enter target directory to create webapp :" )

        if self['webapp_name'] == '' :
            self['webapp_name'] = input(
                    "Enter the web-application name : " )

    def generate( self ):
        """:meth:`pluggdapps.interfaces.IScaffold.generate` interface
        method."""
        _vars = { 'webapp_name' : self['webapp_name'] }
        target_dir = abspath( join( self['target_dir'], self['webapp_name'] ))
        os.makedirs( target_dir )
        h.template_to_source( self['template_dir'], target_dir, _vars )

    def printhelp( self ):
        """:meth:`pluggdapps.interfaces.IScaffold.printhelp` interface
        method."""
        sett = self.default_settings()
        print( self.description )
        for name, d in sett.specifications().items() :
            print("  %20s [%s]" % (name, d['default']))
            pprint( d['help'], indent=4 )
            print()

    #---- ICommand attributes and methods

    cmd = 'webapp'

    def subparser( self, parser, subparsers ):
        """:meth:`pluggdapps.interfaces.ICommand.subparser` interface
        method."""
        self.subparser = subparsers.add_parser( 
                                self.cmd, description=self.description )
        self.subparser.set_defaults( handler=self.handle )
        self.subparser.add_argument( "-t", dest="target_dir",
                                     default=None,
                                     help="Target directory location for web "
                                          "application")
        self.subparser.add_argument( 'name',
                                     help="Web application name" )
        return parser

    def handle( self, args ):
        """:meth:`pluggdapps.interfaces.ICommand.handle` interface
        method."""
        sett = { 'target_dir'  : args.target_dir or os.getcwd(),
                 'webapp_name' : args.name }

        scaff = self.query_plugin( 
                        IScaffold, 'scaffoldingwebapp', settings=sett )
        scaff.query_cmdline()
        print( "Generating Web-application %s" % args.name )
        scaff.generate()
    #---- ISettings interface methods

    @classmethod
    def default_settings( cls ):
        """:meth:`pluggdapps.plugin.ISettings.default_settings` interface
        method."""
        return _default_settings

    @classmethod
    def normalize_settings( cls, sett ):
        """:meth:`pluggdapps.plugin.ISettings.normalize_settings` interface
        method."""
        return sett
