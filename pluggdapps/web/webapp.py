# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 Netscale Computing

from   urllib.parse import urljoin

from   pluggdapps.plugin            import implements, isimplement, \
                                           Plugin, pluginname
from   pluggdapps.interfaces        import IWebApp
from   pluggdapps.web.webinterfaces import IHTTPView, IHTTPRouter
import pluggdapps.utils             as h

_default_settings = h.ConfigDict()
_default_settings.__doc__ = \
    "Configuration settings for WebApp base class inherited by all " \
    "pluggdapps web-applications."

_default_settings['encoding']  = {
    'default' : 'utf8',
    'types'   : (str,),
    'help'    : "Unicode/String encoding to be used.",
}
_default_settings['IHTTPRouter']  = {
    'default' : 'matchrouter',
    'types'   : (str,),
    'help'    : "Name of the plugin implementing :class:`IHTTPRouter` "
                "interface. A request is resolved for a view-callable by this "
                "router plugin."
}
_default_settings['IHTTPCookie']  = {
    'default' : 'httpcookie',
    'types'   : (str,),
    'help'    : "Name of the plugin implementing :class:`IHTTPCookie` "
                "interface spec. Methods from this plugin will be used "
                "to process both request cookies and response cookies. "
                "This configuration can be overriden by corresponding "
                "request / response plugin settings."
}
_default_settings['IHTTPSession']  = {
    'default' : 'httpsession',
    'types'   : (str,),
    'help'    : "Name of the plugin implementing :class:`IHTTPSession` "
                "interface spec. Will be used to handle cookie based "
                "user-sessions."
}
_default_settings['IHTTPEtag']  = {
    'default' : 'httpetag',
    'types'   : (str,),
    'help'    : "Name of the plugin implementing :class:`IHTTPEtag` "
                "interface spec. Will be used to compute etag for response "
                "body."
}
_default_settings['IHTTPRequest']  = {
    'default' : 'httprequest',
    'types'   : (str,),
    'help'    : "Name of the plugin to encapsulate HTTP request. "
}
_default_settings['IHTTPResponse']  = {
    'default' : 'httpresponse',
    'types'   : (str,),
    'help'    : "Name of the plugin to encapsulate HTTP response."
}

class WebApp( Plugin ):
    """Base class for all web applications."""

    implements( IWebApp )

    def __init__( self ):
        self.router = None  # TODO : Make this into default router

    def startapp( self ):
        """Inheriting plugins should not forget to call its super() method."""
        self.router = self.query_plugin( IHTTPRouter, self['IHTTPRouter'] )
        self.router.onboot()

    def dorequest( self, request, body=None, chunk=None, trailers=None ):
        if not request.router :
            request.router = self.webapp.router

        if not request.cookie :
            request.cookie = request.query_plugin( 
                                IHTTPCookie, self['IHTTPCookie'] )
        if not request.response :
            request.response = request.query_plugin(
                                IHTTPResponse, self['IHTTPResponse'], request )

        if not request.session :
            request.session = request.query_plugin(
                                IHTTPSession, self['IHTTPSession'] )

        if not request.etag :
            response.etag = response.query_plugin( 
                                IHTTPEtag, self['IHTTPEtag'] )

        return request.handle( body=body, chunk=chunk, trailers=trailers )

    def onfinish( self, request ):
        pass

    def shutdown( self ):
        self.router = None
        self.cookie = None

    def urlfor( self, request, name, **matchdict ):
        return urljoin( self.baseurl.encode('utf8'),
                        self.pathfor(request, name, **matchdict) )

    def pathfor( self, request, name, **matchdict ):
        query = matchdict.pop( '_query', None )
        fragment = matchdict.pop( '_anchor', None ).encode('utf8')
        path = self.router.urlpath( request, name, **matchdict )
        return h.make_url( None, path, query, fragment )


    #---- ISettings interface methods

    @classmethod
    def default_settings( cls ):
        return _default_settings

    @classmethod
    def normalize_settings( cls, sett ):
        sett['encoding'] = sett['encoding'].lower()
        return sett
