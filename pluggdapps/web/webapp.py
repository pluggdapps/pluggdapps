# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

from   urllib.parse import urljoin

from   pluggdapps.plugin            import implements, Plugin, plugincall
from   pluggdapps.interfaces        import IWebApp
from   pluggdapps.web.webinterfaces import IHTTPRouter, IHTTPCookie, \
                                           IHTTPResponse, IHTTPResource, \
                                           IHTTPSession, IHTTPEtag
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
_default_settings['resource']  = {
    'default' : 'httpresource',
    'types'   : (str,),
    'help'    : "Plugin name implementing :class:`IHTTPResource` interface. "
                "Or, a callable object or string that imports a callable "
                "object. This resource will be called for all requests that "
                "are routed through this application. View specific resource "
                "calls can be configured via add_view()."
}

class WebApp( Plugin ):
    """Base class for all web applications."""

    implements( IWebApp )

    def __init__( self ):
        self.router = None  # TODO : Make this into default router

    def startapp( self ):
        """:meth:`pluggdapps.interfaces.IWebApps.startapp` interface method."""
        self.router = self.query_plugin( IHTTPRouter, self['IHTTPRouter'] )
        self.cookie = self.query_plugin( IHTTPCookie, self['IHTTPCookie'] )
        self.router.onboot()

    def dorequest( self, request, body=None, chunk=None, trailers=None ):
        """:meth:`pluggdapps.interfaces.IWebApps.dorequest` interface method."""
        request.router = self.router
        request.cookie = self.cookie

        request.handle( body=body, chunk=chunk, trailers=trailers )

        request.response = response = self.query_plugin(
                            IHTTPResponse, self['IHTTPResponse'], request )
        # request.session = self.query_plugin(
        #                     IHTTPSession, self['IHTTPSession'] )
        response.etag = self.query_plugin( IHTTPEtag, self['IHTTPEtag'] )
        response.context = c = h.Context()


        # Call IHTTPResource plugin configured for `webapp`.
        res = self['resource']
        res = plugincall( res, lambda : self.query_plugin(IHTTPResource, res) )
        res( request, c ) if res else None

        self.router.route( request, c )

    def dochunk( self, request, chunk=None, trailers=None ):
        """:meth:`pluggdapps.interfaces.IWebApps.dochunk` interface method."""
        request.handle( chunk=chunk, trailers=trailers )

        # Call IHTTPResource plugin configured for `webapp`.
        res = self['resource']
        res = plugincall( res, lambda : self.query_plugin(IHTTPResource, res) )
        res( request, c ) if res else None

        self.router.route( request, c )

    def onfinish( self, request ):
        """:meth:`pluggdapps.interfaces.IWebApps.onfinish` interface method."""
        pass

    def shutdown( self ):
        """:meth:`pluggdapps.interfaces.IWebApps.shutdown` interface method."""
        self.router = None
        self.cookie = None

    def urlfor( self, request, *args, **kwargs ):
        """:meth:`pluggdapps.interfaces.IWebApps.urlfor` interface method."""
        return urljoin( self.baseurl, self.pathfor(request, *args, **kwargs) )

    def pathfor( self, request, *args, **kwargs ):
        """:meth:`pluggdapps.interfaces.IWebApps.pathfor` interface method."""
        return self.router.urlpath( request, *args, **kwargs )


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
        sett['encoding'] = sett['encoding'].lower()
        return sett
