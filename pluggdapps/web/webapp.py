# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 Netscale Computing

from   urllib.parse import urljoin

from   pluggdapps.plugin            import implements, IWebApp, isimplement, \
                                           Plugin, pluginname
from   pluggdapps.web.webinterfaces import IController, IHTTPRouter
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
    'default' : 'patternrouter',
    'types'   : (str,),
    'help'    : "Name of the plugin implementing :class:`IHTTPRouter` "
                "interface. A request is resolved for a view_callable by this "
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
        self.cookie = self.query_plugin( IHTTPCookie, self['IHTTPCookie'] )

    def shutdown( self ):
        self.router = None
        self.cookie = None

    def dorequest( self, request ):
        c = request.response.context
        view = self.router.route( request, c )
        if isimplement(view, IController) :
            meth = hasattr( view, request.method, None )
            if meth :
                meth( request, c )
            else :
                view( request, c )
        elif callable( view ):
            view( request, c )
        else :
            raise h.Error( "Unknown view %r" % view )

    def onfinish( self, request ):
        pass

    def urlfor( self, appname, request, name, *traverse, **matchdict ):
        if appname :
            baseurl = self.pa.baseurl( request, appname=appname )
        else :
            baseurl = request.baseurl
        relurl = self.pathfor( request, name, *traverse, **matchdict )
        return urljoin( baseurl, relurl )

    def pathfor( self, request, name, *traverse, **matchdict ):
        query = matchdict.pop( '_query', None )
        anchor = matchdict.pop( '_anchor', None )
        path = self.router.genpath( request, name, *traverse, **matchdict )
        return make_url( None, path, query, fragment )

    #---- ISettings interface methods

    @classmethod
    def default_settings( cls ):
        return _default_settings

