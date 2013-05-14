# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

from   urllib.parse import urljoin
import sys

from   pluggdapps.const          import URLSEP
from   pluggdapps.plugin         import implements, Plugin
from   pluggdapps.interfaces     import IWebApp
from   pluggdapps.web.interfaces import IHTTPRouter,IHTTPCookie, IHTTPResponse,\
                                        IHTTPSession, IHTTPInBound, \
                                        IHTTPOutBound, IHTTPLiveDebug
import pluggdapps.utils          as h

class WebApp( Plugin ):
    """Base class for all web applications plugins. Implements
    :class:`pluggdapps.interfaces.IWebApp` interface, refer to interface
    specification to understand the general intent and purpose of
    web-application plugins.
    
    Every http request enters the application through this plugin class.
    A comprehensive set of configuration settings are made available by this
    class.
    """

    implements( IWebApp )

    def startapp( self ):
        """:meth:`pluggdapps.interfaces.IWebApps.startapp` interface method."""
        # Initialize plugins required to handle http request. 
        self.router = self.qp( IHTTPRouter, self['IHTTPRouter'] )
        self.cookie = self.qp( IHTTPCookie, self['IHTTPCookie'] )
        self.in_transformers = [
                self.qp( IHTTPInBound, name )
                for name in self['IHTTPInBound'] ]
        self.out_transformers = [
                self.qp( IHTTPOutBound, name )
                for name in self['IHTTPOutBound'] ]

        # Live debug.
        if self['debug'] :
            self.livedebug = self.qp( IHTTPLiveDebug, self['IHTTPLiveDebug'] )
        else :
            self.livedebug = None

        # Initialize plugins.
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
              self.qp( IHTTPResponse, self['IHTTPResponse'], request )
            request.handle( body=body, chunk=chunk, trailers=trailers )
            self.router.route( request )
        except :
            self.pa.logerror( h.print_exc() )
            response.set_header( 'content_type', b'text/html' )
            if self['debug'] :
                data = self.livedebug.render( request, *sys.exc_info() )
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
        self.router.onfinish( request )

    def shutdown( self ):
        """:meth:`pluggdapps.interfaces.IWebApps.shutdown` interface method."""
        self.router = None
        self.cookie = None
        self.livedebug = None
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
        sett['IHTTPInBound'] = h.parsecsvlines( sett['IHTTPInBound'] )
        sett['IHTTPOutBound'] = h.parsecsvlines( sett['IHTTPOutBound'] )
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
    'help'    : "Default language to use in content negotiation. This can "
                "be customized for each view (or resource-variant)"
}
_default_settings['IHTTPRouter']  = {
    'default' : 'pluggdapps.MatchRouter',
    'types'   : (str,),
    'help'    : "IHTTPRouter plugin. Base router plugin for resolving "
                "requests to view-callable."
}
_default_settings['IHTTPCookie']  = {
    'default' : 'pluggdapps.HTTPCookie',
    'types'   : (str,),
    'help'    : "Plugin implementing IHTTPCookie interface spec. Methods "
                "from this plugin will be used to process both request "
                "cookies and response cookies. "
}
_default_settings['IHTTPSession']  = {
    'default' : 'pluggdapps.HTTPSession',
    'types'   : (str,),
    'help'    : "Plugin implementing IHTTPSession interface spec. Will be "
                "used to handle cookie based user-sessions."
}
_default_settings['IHTTPRequest']  = {
    'default' : 'pluggdapps.HTTPRequest',
    'types'   : (str,),
    'help'    : "Name of the plugin to encapsulate HTTP request. "
}
_default_settings['IHTTPResponse']  = {
    'default' : 'pluggdapps.HTTPResponse',
    'types'   : (str,),
    'help'    : "Name of the plugin to encapsulate HTTP response."
}
_default_settings['IHTTPInBound'] = {
    'default' : '',
    'types'   : ('csv',list),
    'help'    : "A string of comma seperated value, where each value names a "
                "IHTTPInBound plugin. Transforms will be applied in "
                "specified order."
}
_default_settings['IHTTPOutBound'] = {
    'default' : 'pluggdapps.ResponseHeaders, pluggdapps.GZipOutBound',
    'types'   : ('csv',list),
    'help'    : "A string of comma seperated value, where each value names a "
                "IHTTPOutBound plugin. Transforms will be applied in "
                "specified order."
}
_default_settings['IHTTPLiveDebug']  = {
    'default' : 'pluggdapps.CatchAndDebug',
    'types'   : (str,),
    'help'    : "Plugin implementing IHTTPLiveDebug interface spec. Will be "
                "used to catch application exception and render them on "
                "browser. Provides browser based debug interface."
}


