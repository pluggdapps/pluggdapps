# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 Netscale Computing

from copy import deepcopy

import pluggdapps.utils             as h
from   pluggdapps.const             import URLSEP
from   pluggdapps.plugin            import implements, Plugin
from   pluggdapps.web.webinterfaces import IHTTPRouter, IHTTPResource
from   pluggdapps.web.views         import HTTPNotFound
from   pluggdapps.web.routermixins  import MatchMixin

# media_type : (RFC2616 Accept header)
#    If no Accept header field is present, then it is assumed that the
#    client accepts all media types. If an Accept header field is present,
#    and if the server cannot send a response which is acceptable
#    according to the combined Accept field value, then the server SHOULD
#    send a 406 (not acceptable) response.

# charset : (RFC2616 Accept-Charset header)
#    The special value "*", if present in the Accept-Charset field,
#    matches every character set (including ISO-8859-1) which is not
#    mentioned elsewhere in the Accept-Charset field. If no "*" is present
#    in an Accept-Charset field, then all character sets not explicitly
#    mentioned get a quality value of 0, except for ISO-8859-1, which gets
#    a quality value of 1 if not explicitly mentioned.


_ram_settings = h.ConfigDict()
_ram_settings.__doc__ = \
    "Configuration settings for url Router RouteAndMatch."

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

class URLRouter( Plugin, MatchMixin ):
    implements( IHTTPRouter )

    def onboot( self ):
        super().onboot()

    def route( request, c ):
        res = query_plugin( self.webapp, IHTTPResource, self['iresource'] )
        res( request, c )
        view = self.fetchview( request, c )
        view = HTTPNotFound if view == None else view
        return view

    #---- ISettings interface methods

    @classmethod
    def default_settings( cls ):
        return _ram_settings


_routestatic_sett = h.ConfigDict()
_routestatic_sett.__doc__ = \
    "Configuration settings for url Router RouteMatch."

_routestatic_sett['iresource']  = {
    'default' : 'staticresource',
    'types'   : (str,),
    'help'    : "Plugin name implementing :class:`IHTTPResource` interface "
                "accepts a :class:`IHTTPRequest` instance and :class:`Context` "
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
    implements( IHTTPRouter )

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
        res = query_plugin( self.webapp, IHTTPResource, self['iresource'] )
        res( request, c )
        view = self.fetchview( request, c )
        return view


    #---- ISettings interface methods

    @classmethod
    def default_settings( cls ):
        return _routestatic_sett

