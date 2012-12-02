# -*- coding: utf-8 -*-

from   pluggdapps.web.webapp        import WebApp
from   pluggdapps.web.webinterfaces import IHTTPRouter
import pluggdapps.utils             as h

_default_settings = h.ConfigDict()
_default_settings.__doc__ = \
    "Configuration settings for WebApp base class inherited by all " \
    "pluggdapps web-applications."

_default_settings['encoding']  = {{
    'default' : 'utf8',
    'types'   : (str,),
    'help'    : "Unicode/String encoding to be used.",
}}
_default_settings['IHTTPRouter']  = {{
    'default' : '{webapp_name}router',
    'types'   : (str,),
    'help'    : "Name of the plugin implementing :class:`IHTTPRouter` "
                "interface. A request is resolved for a view-callable by this "
                "router plugin."
}}
_default_settings['IHTTPCookie']  = {{
    'default' : 'httpcookie',
    'types'   : (str,),
    'help'    : "Name of the plugin implementing :class:`IHTTPCookie` "
                "interface spec. Methods from this plugin will be used "
                "to process both request cookies and response cookies. "
                "This configuration can be overriden by corresponding "
                "request / response plugin settings."
}}
_default_settings['IHTTPSession']  = {{
    'default' : 'httpsession',
    'types'   : (str,),
    'help'    : "Name of the plugin implementing :class:`IHTTPSession` "
                "interface spec. Will be used to handle cookie based "
                "user-sessions."
}}
_default_settings['IHTTPEtag']  = {{
    'default' : 'httpetag',
    'types'   : (str,),
    'help'    : "Name of the plugin implementing :class:`IHTTPEtag` "
                "interface spec. Will be used to compute etag for response "
                "body."
}}
_default_settings['IHTTPRequest']  = {{
    'default' : 'httprequest',
    'types'   : (str,),
    'help'    : "Name of the plugin to encapsulate HTTP request. "
}}
_default_settings['IHTTPResponse']  = {{
    'default' : 'httpresponse',
    'types'   : (str,),
    'help'    : "Name of the plugin to encapsulate HTTP response."
}}
_default_settings['resource']  = {{
    'default' : '{webapp_name}resource',
    'types'   : (str,),
    'help'    : "Plugin name implementing :class:`IHTTPResource` interface. "
                "Or, a callable object or string that imports a callable "
                "object. This resource will be called for all requests that "
                "are routed through this application. View specific resource "
                "calls can be configured via add_view()."
}}

class {webapp_name}( WebApp ):

    def startapp( self ):
        super().startapp()

    def dorequest( self, request, body=None, chunk=None, trailers=None ):
        super().dorequest( request, body=body, chunk=chunk, trailers=trailers )

    def dochunk( self, request, chunk=None, trailers=None ):
        super().dochunk( request, chunk=chunk, trailers=trailers )

    def onfinish( self, request ):
        super().onfinish( request )

    def shutdown( self ):
        super().shutdown()


    #---- ISettings interface methods

    @classmethod
    def default_settings( cls ):
        return _default_settings

    @classmethod
    def normalize_settings( cls, sett ):
        return sett

