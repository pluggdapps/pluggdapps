# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 Netscale Computing

from copy import deepcopy

from   pluggdapps.const        import URLSEP
from   pluggdapps.config       import ConfigDict
from   pluggdapps.plugin       import implements, Plugin
from   pluggdapps.interfaces   import IRouter, IResource
from   pluggdapps.views        import HTTPNotFound
from   pluggdapps.routermixins import TraverseMixin, MatchMixin
import pluggdapps.utils        as h

_ram_settings = ConfigDict()
_ram_settings.__doc__ = \
    "Configuration settings for url Router RouteAndMatch."

_ram_settings['iresource']  = {
    'default' : 'baseresource',
    'types'   : (str,),
    'help'    : "Plugin name implementing :class:`IResource` interface that "
                "accepts a :class:`IRequest` instance and :class:`Context` "
                "dictionary as its arguments. It can freely update the "
                "context dictionary. This dictionary will propogate across "
                "the route-resolution for every traversed segment and "
                "eventually to the final resource defined for a view callable."
}
_ram_settings['traverse.static']  = {
    'default' : 'routestatic',
    'types'   : (str,),
    'help'    : "Plugin name to use as traversal route, when the path segment "
                "`static` matches with requests resolve_path."
}
_ram_settings['traversewith'] = {
    'default' : '',
    'types'   : (str,),
    'help'    : "Interface name to use for traversing the routers path "
                "segment."
}

class RouteAndMatch( Plugin, TraverseMixin, MatchMixin ):
    implements( IRouter )

    def onboot( self ):
        super().onboot()

    def route( request, c ):
        res = query_plugin( self.webapp, IResource, self['iresource'] )
        res( request, c )
        view = self.fetchview( request, c )
        view = HTTPNotFound if view == None else view
        return view

    #---- ISettings interface methods

    @classmethod
    def default_settings( cls ):
        return _ram_settings


_routestatic_sett = ConfigDict()
_routestatic_sett.__doc__ = \
    "Configuration settings for url Router RouteMatch."

_routestatic_sett['iresource']  = {
    'default' : 'staticresource',
    'types'   : (str,),
    'help'    : "Plugin name implementing :class:`IResource` interface that "
                "accepts a :class:`IRequest` instance and :class:`Context` "
                "dictionary as its arguments. It can freely update the "
                "context dictionary. This dictionary will propogate across "
                "the route-resolution for every traversed segment and "
                "eventually to the final resource defined for a view callable."
}
_routestatic_sett['docroot']  = {
    'default' : None,
    'types'   : (str,),
    'help'    : "Document door for static files."
}

class RouteStatic( Plugin ):
    implements( IRouter )

    def __init__( self, *args, **kwargs ):
        self.traversals = []

    def onboot( self ):
        if 'docroot' not in self :
            path = h.sourcepath( self.webapp )
            paths = [ join( dirname(path), 'static' ),
                      join( dirname( dirname(path) ), 'static' )
                    ]
            for docroot in paths :
                if isdir( docroot ) :
                    self['docroot'] = docroot
                    break
            else :
                self['docroot'] = None
        if self['docroot'] :
            self['docroot'] = self['docroot'].rstrip( URLSEP )

    def route( request, c ):
        res = query_plugin( self.webapp, IResource, self['iresource'] )
        res( request, c )
        view = self.fetchview( request, c )
        return view


    #---- ISettings interface methods

    @classmethod
    def default_settings( cls ):
        return _routestatic_sett

