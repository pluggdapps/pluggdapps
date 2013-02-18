# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

from   urllib.parse import urljoin
import sys

from   pluggdapps.const          import URLSEP
from   pluggdapps.plugin         import implements, Plugin
from   pluggdapps.interfaces     import IWebApp
from   pluggdapps.web.interfaces import IHTTPRouter,IHTTPCookie,IHTTPResponse, \
                                        IHTTPSession, IHTTPInBound, \
                                        IHTTPOutBound, IHTTPWebDebug
import pluggdapps.utils          as h

class WebApp( Plugin ):
    """Base class for all web applications plugins. Every http request enters
    the application through this plugin class. And provides a comprehensible
    set of configuration."""

    implements( IWebApp )

    def __init__( self ):
        self.router = None  # TODO : Make this into default router

    def startapp( self ):
        """:meth:`pluggdapps.interfaces.IWebApps.startapp` interface method."""
        self.router = self.query_plugin( IHTTPRouter, self['IHTTPRouter'] )
        self.cookie = self.query_plugin( IHTTPCookie, self['IHTTPCookie'] )
        self.webdebug = self.query_plugin(IHTTPWebDebug, self['IHTTPWebDebug'])
        self.in_transformers = [
                self.query_plugin( IHTTPInBound, name )
                for name in self['IHTTPInBound'] ]
        self.out_transformers = [
                self.query_plugin( IHTTPOutBound, name )
                for name in self['IHTTPOutBound'] ]
        self.router.onboot()

    def dorequest( self, request, body=None, chunk=None, trailers=None ):
        """:meth:`pluggdapps.interfaces.IWebApps.dorequest` interface method."""
        self.pa.logdebug( 
          "[%s] %s %s" % (request.method,request.uri,request.httpconn.address))

        try :
            # Initialize framework attributes
            request.router = self.router
            request.cookie = self.cookie
            # TODO : Initialize session attribute here.
            request.response = response = \
              self.query_plugin( IHTTPResponse, self['IHTTPResponse'], request )
            request.handle( body=body, chunk=chunk, trailers=trailers )
            self.router.route( request )
        except :
            self.pa.logerror( h.print_exc() )
            response.set_header( 'content_type', b'text/html' )
            if self['debug'] :
                data = self.webdebug.handle_exc( request, *sys.exc_info() )
                response.set_status( b'200' )
            else :
                response.set_status( b'500' )
                data = ( "An error occurred.  See the error logs for more "
                         "information. (Turn debug on to display exception "
                         "reports here)" )
            response.write( data )
            response.flush( finishing=True )

    def dochunk( self, request, chunk=None, trailers=None ):
        """:meth:`pluggdapps.interfaces.IWebApps.dochunk` interface method."""
        request.handle( chunk=chunk, trailers=trailers )
        self.router.route( request )

    def onfinish( self, request ):
        """:meth:`pluggdapps.interfaces.IWebApps.onfinish` interface method."""
        pass

    def shutdown( self ):
        """:meth:`pluggdapps.interfaces.IWebApps.shutdown` interface method."""
        self.router = None
        self.cookie = None
        self.in_transformers = []
        self.out_transformers = []

    def urlfor( self, request, *args, **kwargs ):
        """:meth:`pluggdapps.interfaces.IWebApps.urlfor` interface method."""
        return urljoin( self.baseurl, self.pathfor(request, *args, **kwargs) )

    def pathfor( self, request, *args, **kwargs ):
        """:meth:`pluggdapps.interfaces.IWebApps.pathfor` interface method."""
        path = self.router.urlpath( request, *args, **kwargs )
        if path.startswith( URLSEP ) :  # Prefix uriparts['script']
            if request.uriparts['script'] :
                path = request.uriparts['script'] + path
        return path


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
        sett['IHTTPOutBound'] = h.parsecsvlines( sett['IHTTPOutBound'] )
        sett['IHTTPInBound'] = h.parsecsvlines( sett['IHTTPInBound'] )
        return sett

_default_settings = h.ConfigDict()
_default_settings.__doc__ = WebApp.__doc__

_default_settings['encoding']  = {
    'default' : 'utf-8',
    'types'   : (str,),
    'help'    : "Default character encoding to use on HTTP response. This can " 
                "be customized for each view (or resource-variant)"
}
_default_settings['language']  = {
    'default' : 'en',
    'types'   : (str,),
    'help'    : "Default language to use for content negotiation. This can "
                "be customized for each view (or resource-variant)"
}
_default_settings['IHTTPRouter']  = {
    'default' : 'matchrouter',
    'types'   : (str,),
    'help'    : "IHTTPRouter plugin. A request is resolved for a "
                "view-callable by this router plugin."
}
_default_settings['IHTTPCookie']  = {
    'default' : 'httpcookie',
    'types'   : (str,),
    'help'    : "Plugin implementing IHTTPCookie interface spec. Methods "
                "from this plugin will be used to process both request "
                "cookies and response cookies. This configuration can be "
                "overriden by corresponding request / response plugin "
                "settings."
}
_default_settings['IHTTPSession']  = {
    'default' : 'httpsession',
    'types'   : (str,),
    'help'    : "Plugin implementing IHTTPSession interface spec. Will be "
                "used to handle cookie based user-sessions."
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
_default_settings['IHTTPInBound'] = {
    'default' : '',
    'types'   : (str,),
    'help'    : "A string of comma seperated value, where each value names a "
                "IHTTPInBound plugin. Transforms will be applied in "
                "specified order."
}
_default_settings['IHTTPOutBound'] = {
    'default' : 'ResponseHeaders, GZipOutBound',
    'types'   : (str,),
    'help'    : "A string of comma seperated value, where each value names a "
                "IHTTPOutBound plugin. Transforms will be applied in "
                "specified order."
}
_default_settings['IHTTPWebDebug']  = {
    'default' : 'CatchAndDebug',
    'types'   : (str,),
    'help'    : "Plugin implementing IHTTPWebDebug interface spec. Will be "
                "used to catch application exception and render them on "
                "browser. Provides browser based debug interface."
}


