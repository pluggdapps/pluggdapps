# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 Netscale Computing

import socket, time, re
from   urllib.parse import urlunsplit
from   copy         import deepcopy

import pluggdapps.utils             as h
from   pluggdapps.plugin            import implements, Plugin
from   pluggdapps.web.webinterfaces import IHTTPRequest, IHTTPResponse, IHTTPCookie

# TODO : Product token, header field `Server` to be automatically added in
# response.

_default_settings = h.ConfigDict()
_default_settings.__doc__ = (
    "Configuration settings for HTTPRequest implementing IHTTPRequest "
    "interface." )

class HTTPRequest( Plugin ):
    implements( IHTTPRequest )

    content_type = None
    """Parsed content type as tuple of,
        ( type, subtype, [ (attr, value), ... ] ) """

    # IHTTPRequest interface methods and attributes
    def __init__( self, httpconn, method, uri, version, headers ):

        self.router = self.cookie = None
        self.response = self.session = None

        self.httpconn = conn
        self.method, self.uri, self.version = method, uri, version
        self.headers = headers
        self.uriparts = h.parse_url( self.uri, host=headers['Host'] 
                                   ) if isinstance( uri, str ) else uri

        self.body = None
        self.chunks = []
        self.trailers = {}

        self.params = {}
        self.getparams = self.uriparts.query
        self.params.update( self.getparams )

        self.content_type = h.parse_content_type( 
                                headers.get( 'content-type', None ))
        if method in ( b'POST', b'PUT' ) :
            self.postparams, self.multiparts = \
                    h.parse_formbody( self.content_type, body )
            [ self.params.setdefault( name, [] ).extend( value )
              for name, value in self.postparams.items() ]
            [ self.params.setdefault( name, [] ).extend( value )
              for name, value in self.multiparts.items() ]
            [ self.files.setdefault( name, [] 
                                   ).extend( (f['filename'], f['value'] ) )
              for name, value in self.multiparts.items() ]
        else :
            self.postparams = {}
            self.multiparts = {}
            self.files = {}

        self.cookies = self.cookie.parse_cookies( self.headers )

        self.receivedat = time.time()
        self.finishedat = None

    def supports_http_1_1( self ):
        return self.version == b"HTTP/1.1"

    def get_ssl_certificate(self):
        return self.httpconn.get_ssl_certificate()

    def get_cookie( self, name, default=None ):
        """Gets the value of the cookie with the given name, else default."""
        return self.cookies[name].value if name in self.cookies else default

    def get_secure_cookie( self, name, value=None ):
        """Returns the given signed cookie if it validates, or None."""
        if value is None :
            value = self.get_cookie(name)
        return self.cookie.decode_signed_value( name, value ) 

    def has_finished( self ):
        return self.response.has_finished()

    def ischunked( self ):
        x = h.parse_transfer_encoding( 
                self.headers.get( 'transfer-encoding', None ))
        return (x[0][0] == 'chunked') if x else False

    def handle( self, body=None, chunk=None, trailers=None ):
        if body :
            self.body = body
        elif chunk and trailers and chunk[0] == 0 :
            self.chunks.append( chunk )
            self.trailers = trailers
        elif chunk :
            self.chunks.append( chunk )

        c = self.response.context
        self.router.route( self, c )  # Resolves a view callable.

        if self.view :   # Call the view-callable
            self.view( self, c )

    def onfinish( self ):
        """Callback when :meth:`IHTTPResponse.finish()` is called."""
        # Will be callbe by response.onfinish() callback.
        self.httpconn.finish()
        self.view.onfinish()
        self.webapp.onfinish()
        self.finishedat = time.time()

    def urlfor( name, **matchdict ):
        return self.webapp.urlfor( self, name, **matchdict )

    def pathfor( name, **matchdict ):
        return self.webapp.pathfor( self, name, **matchdict )

    def appurl( webapp, name, **matchdict ):
        return webapp.urlfor( self, name, **matchdict )


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
