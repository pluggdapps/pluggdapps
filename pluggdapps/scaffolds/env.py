# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

import os
from   os.path  import dirname, join, abspath

import pluggdapps.utils             as h
from   pluggdapps.plugin            import implements, Plugin
from   pluggdapps.interfaces        import IScaffold, ICommand

class Env( Plugin ):
    """Sub-command plugin to generate scaffolding logic for pluggdapps
    development environment. Can be invoked from pa-script and meant for
    upstream authors."""

    implements( IScaffold, ICommand )

    description = (
        "Scaffolding logic to create a new pluggdapps environment" )

    #---- IScaffold API methods.

    def query_cmdline( self ):
        """:meth:`pluggdapps.interfaces.IScaffold.query_cmdline` interface
        method."""
        if not self['target_dir'] :
            self['target_dir'] = input( 
                    "Enter target directory to create environment :" )
        if not self['host_name'] :
            self['host_name'] = input( 
                    "Enter host name for the environment :" )

    def generate( self ):
        """:meth:`pluggdapps.interfaces.IScaffold.generate` interface
        method."""
        _vars = { 'host_name' : self['host_name'] }
        target_dir = abspath( self['target_dir'] )
        host_name = abspath( self['host_name'] )
        os.makedirs( target_dir, exist_ok=True )
        h.template_to_source( self['template_dir'], target_dir, _vars,
                              overwrite=True, verbose=True )

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

    description = "Scaffolding logic to create a new pluggdapps environment."
    cmd = 'env'

    def subparser( self, parser, subparsers ):
        """:meth:`pluggdapps.interfaces.ICommand.subparser` interface
        method."""
        self.subparser = subparsers.add_parser( 
                                self.cmd, description=self.description )
        self.subparser.set_defaults( handler=self.handle )
        self.subparser.add_argument(
                "-n", dest="host_name",
                default=None,
                help="Host name" )
        self.subparser.add_argument(
                "-t", dest="target_dir",
                default=None,
                help="Target directory location for web application" )
        return parser

    def handle( self, args ):
        """:meth:`pluggdapps.interfaces.ICommand.handle` interface
        method."""
        sett = { 'target_dir'  : args.target_dir or os.getcwd(),
                 'host_name'   : args.host_name,
               }
        scaff = self.qp( IScaffold, 'pluggdapps.Env', settings=sett )
        scaff.query_cmdline()
        print( "Generating pluggdapps environment." )
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


_default_settings = h.ConfigDict()
_default_settings.__doc__ = Env.__doc__

_default_settings['template_dir']  = {
    'default' : join( dirname(__file__), 'env_template'),
    'types'   : (str,),
    'help'    : "Obsolute file path of template source-tree to be used for "
                "the scaffolding logic."
}
_default_settings['target_dir'] = {
    'default' : '',
    'types'   : (str,),
    'help'    : "Target directory to place the scaffolding logic."
}
_default_settings['host_name'] = {
    'default' : '',
    'types'   : (str,),
    'help'    : "Host name for the environment :"
}

