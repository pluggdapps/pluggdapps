# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 Netscale Computing

import socket, time, re
from   urllib.parse import urlunsplit
from   copy         import deepcopy

from   pluggdapps.config     import ConfigDict
import pluggdapps.utils      as h
from   pluggdapps.plugin     import implements, Plugin, query_plugin
from   pluggdapps.interfaces import IRequest, IResponse, ICookie

_default_settings = ConfigDict()
_default_settings.__doc__ = \
    "Configuration settings for HTTPRequest implementing IRequest interface."

_default_settings['icookie']  = {
    'default' : 'httpcookie',
    'types'   : (str,),
    'help'    : "Plugin class implementing ICookie interface specification. "
                "Methods from this plugin will be used to process request "
                "cookies. Overrides :class:`ICookie` if defined in "
                "application plugin."
}

class HTTPRequest( Plugin ):
    implements( IRequest )

    do_methods = ('GET', 'HEAD', 'POST', 'DELETE', 'PUT', 'OPTIONS')

    elapsedtime = property( lambda self : time.time() - self.receivedat )

    # IRequest interface methods and attributes
    def __init__( self, conn, address, method, uri, uriparts, version,
                  headers, body ):
        self.receivedat = time.time()
        self.finishedat = None
        xheaders = getattr( conn, 'xheaders', None ) if conn else None

        self.cookie_plugin = self.query_plugin(
                                    self.webapp, ICookie, self['icookie'] )
        
        # Socket attributes
        self.connection = conn

        # Request attributes
        self.method = method
        self.uriparts = uriparts
        self.version = version
        self.headers = headers or h.HTTPHeaders()
        self.body = body or b""
        self.baseurl = self.webapp.pa.baseurl( self )
        self.uri = h.make_url(
            self.baseurl, uriparts['path'], uriparts['query'],
            uriparts['fragment'] )
        # Client's ip-address and port number
        remoteip, port = address
        self.address = (
            h.parse_remoteip( remoteip, self.headers, xheaders ),
            port )
        # A dictionary of http.cookies.Morsel
        self.cookies = self.cookie_plugin.parse_cookies( self.headers )
        self.getparams = uriparts.query
        # Parse request body here.
        self.postparams, self.files = \
                        h.parse_body( method, self.headers, body )

        # Processed attributes
        self.params = {}
        self.params.update( self.getparams )
        self.params.update( self.postparams )

        # Framework attributes
        self.session = None

        # Router attributes
        self.resolve_path = uriparts.path
        self.traversed = []
        self.matchrouter = None
        self.matchdict = None
        self.view_name = None

    def supports_http_1_1( self ):
        return self.version == "HTTP/1.1"

    def get_ssl_certificate(self):
        try    :
            return self.connection.get_ssl_certificate()
        except :
            return None

    def get_cookie( self, name, default=None ):
        """Gets the value of the cookie with the given name, else default."""
        return self.cookies[name].value if name in self.cookies else default

    def get_secure_cookie( self, name, value=None ):
        """Returns the given signed cookie if it validates, or None."""
        if value is None :
            value = self.get_cookie(name)
        return self.cookie_plugin.decode_signed_value( name, value ) 

    def onfinish( self ):
        """Callback when :meth:`IResponse.finish()` is called."""
        self.connection.finish()
        self.finishedat = time.time()

    def query_plugin( self, *args, **kwargs ):
        return query_plugin( self.webapp, *args, **kwargs )

    def query_plugins( self, *args, **kwargs ):
        return query_plugin( self.webapp, *args, **kwargs )

    def urlfor( name, *traverse, **matchdict ):
        return self.webapp.urlfor( None, self, name, *traverse, **matchdict )

    def pathfor( name, *traverse, **matchdict ):
        return self.webapp.pathfor( self, name, *traverse, **matchdict )

    def appurl( appname, name, *traverse, **matchdict ):
        return self.webapp.urlfor( appname, self, name *traverse, **matchdict )

    def __repr__( self ):
        attrs = ( "uriparts", "address", "body" )
        args = ", ".join( 
                    "%s=%r" % (n, getattr(self, n, None)) for n in attrs )
        return "%s(%s, headers=%s)" % (
            self.__class__.__name__, args, dict(getattr(self,'headers',{})) )

    #---- ISettings interface methods

    @classmethod
    def default_settings( cls ):
        return _default_settings

