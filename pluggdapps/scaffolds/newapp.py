# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

import os
from   os.path                  import dirname, join, abspath

import pluggdapps.utils             as h
from   pluggdapps.plugin            import implements, Plugin
from   pluggdapps.interfaces        import IScaffold, ICommand

class NewWebApp( Plugin ):
    """
    Inside a pluggapps package, more than one web-application can be defined.
    Typically a web-application, which is going to be a plugin, must implement
    :class:`IWebApp` interface and a bunch of plugins to handle http request
    - like, routing url to view-callables, view-plugin, resource-plugin,
    and reply back with valid response. To facilitate this repeatitive activity,
    pa-script provides this command to create a webapp-source-tree base on
    couple of parameters.

    .. code-block:: bash

        $ pa -c <master.ini> webapp [-t TARGET_DIR] <webapp-name>

    creates a new web application under project source tree. This command 
    creates relevant scaffolds, as modules and directories, under the 
    specified target directory.

    to learn more options on this sub-command use ``--help``."""

    implements( IScaffold, ICommand )

    description = (
        "Scaffolding logic to create a new web application source tree."
    )

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

        scaff = self.qp( IScaffold, 'pluggdapps.NewWebApp', settings=sett )
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

_default_settings = h.ConfigDict()
_default_settings.__doc__ = NewWebApp.__doc__

_default_settings['template_dir']  = {
    'default' : join( dirname(__file__), 'webapp_template'),
    'types'   : (str,),
    'help'    : "Obsolute file path of template source-tree to be used for "
                "the scaffolding logic."
}
_default_settings['target_dir'] = {
    'default' : '',
    'types'   : (str,),
    'help'    : "Target directory to place the generated modules and "
                "directories. If not specified uses the current working "
                "directory."
}
_default_settings['webapp_name'] = {
    'default' : '',
    'types'   : (str,),
    'help'    : "Name of the web application. Since a web application is "
                "also a plugin, it must be a unique name."
}
