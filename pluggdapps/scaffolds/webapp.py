# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

import os
from   os.path                  import dirname, join, basename, abspath

import pluggdapps.utils             as h
from   pluggdapps.plugin            import implements, Plugin
from   pluggdapps.interfaces        import IScaffold
from   pluggdapps.scaffolds.util    import template_to_source
from   pluggdapps.interfaces        import IScaffold

_default_settings = h.ConfigDict()
_default_settings.__doc__ = (
    "Basic configuration settings for IScaffold interface specification."
)

_default_settings['template_dir']  = {
    'default' : 'webapp_template',
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
    implements( IScaffold )

    description = "Create scaffolding logic for a web application."

    #---- IScaffold API methods.

    def __init__( self, target, template_dir=None ):
        pass

    def query_cmdline( self ):
        if self['target_dir'] == '' :
            self['target_dir'] = input( 
                    "Enter target directory to create webapp :" )

        if self['webapp_name'] == '' :
            self['webapp_name'] = input(
                    "Enter the web-application name : " )

    def generate( self ):
        _vars = { 'webapp_name' : self['webapp_name'] }
        target_dir = join( self['target_dir'], self['webapp_name'] )
        os.makedirs( target_dir )
        print( "Generated %r" % target_dir )
        template_to_source( self['template_dir'], target_dir, _vars )

    def printhelp( self ):
        sett = self.default_settings()
        print( self.description )
        for name, d in sett.specifications().items() :
            print("  %20s [%s]" % (name, d['default']))
            pprint( d['help'], indent=4 )
            print()

    #---- ISettings interface methods

    @classmethod
    def default_settings( cls ):
        return _default_settings

    @classmethod
    def normalize_settings( cls, sett ):
        return sett

