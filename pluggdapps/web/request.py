# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

import time

import pluggdapps.utils          as h
from   pluggdapps.plugin         import Plugin, implements
from   pluggdapps.web.interfaces import IHTTPRequest

# TODO : Product token, header field `Server` to be automatically added in
# response.

class HTTPRequest( Plugin ):
    """Plugin encapsulates HTTP request. Refer to 
    :class:`pluggdapps.web.interfaces.IHTTPRequest` interface spec. to
    understand the general intent and purpose of this plugin.
    """

    implements( IHTTPRequest )

    content_type = ''
    """Parsed content type as return from :meth:`parse_content_type`."""

    # IHTTPRequest interface methods and attributes
    def __init__( self, httpconn, method, uri, uriparts, version, headers ):
        """:meth:`pluggdapps.web.interfaces.IHTTPRequest.__init__` interface
        method."""
        self.router = self.cookie = None
        self.response = self.session = None

        self.httpconn = httpconn
        self.method, self.uri, self.uriparts, self.version = \
                method, uri, uriparts, version
        self.headers = headers

        # Initialize request handler attributes, these attributes will be
        # valid only after a call to handle() method.
        self.body = b''
        self.chunks = []
        self.trailers = {}
        self.cookies = {}

        # Only in case of POST and PUT method.
        self.postparams = {}
        self.multiparts = {}
        self.files = {}

        # Initialize
        self.params = {}
        self.getparams = { h.strof(k) : list( map( h.strof, vs )) 
                           for k,vs in self.uriparts['query'].items() }
        self.params.update( self.getparams )

        self.content_type = \
                h.parse_content_type( headers.get( 'content_type', None ))

        self.view = None
        self.receivedat = time.time()
        self.finishedat = None

    def supports_http_1_1( self ):
        """:meth:`pluggdapps.web.interfaces.IHTTPRequest.supports_http_1_1`
        interface method."""
        return self.version == b"HTTP/1.1"

    def get_ssl_certificate(self):
        """:meth:`pluggdapps.web.interfaces.IHTTPRequest.get_ssl_certificate`
        interface method."""
        return self.httpconn.get_ssl_certificate()

    def get_cookie( self, name, default=None ):
        """:meth:`pluggdapps.web.interfaces.IHTTPRequest.get_cookie`
        interface method."""
        return self.cookies[name].value if name in self.cookies else default

    def get_secure_cookie( self, name, value=None ):
        """:meth:`pluggdapps.web.interfaces.IHTTPRequest.get_secure_cookie`
        interface method."""
        if value is None :
            value = self.get_cookie(name)
        return self.cookie.decode_signed_value( name, value ) 

    def has_finished( self ):
        """:meth:`pluggdapps.web.interfaces.IHTTPRequest.has_finished`
        interface method."""
        return self.response.has_finished() if self.response else True

    def ischunked( self ):
        """:meth:`pluggdapps.web.interfaces.IHTTPRequest.ischunked`
        interface method."""
        x = h.parse_transfer_encoding( 
                self.headers.get( 'transfer_encoding', b'' ))
        return (x[0][0] == 'chunked') if x else False

    def handle( self, body=None, chunk=None, trailers=None ):
        """:meth:`pluggdapps.web.interfaces.IHTTPRequest.handle`
        interface method."""
        self.cookies = self.cookie.parse_cookies( self.headers )

        # In case of `chunked` encoding, check whether this is the last chunk.
        finishing = body or ( chunk and trailers and chunk[0] == 0)

        # Apply IHTTPInBound transformers on this request.
        data = body if body != None else (chunk[2] if chunk else b'')
        for tr in self.webapp.in_transformers :
            data = tr.transform( self, data, finishing=finishing )

        # Update the request plugin with attributes.
        if body :
            self.body = data
        elif chunk :
            self.chunks.append( (chunk[0], chunk[1], data) )
        self.trailers = trailers or self.trailers

        # Process POST and PUT request interpreting multipart content.
        if self.method in ( b'POST', b'PUT' ) :
            self.postparams, self.multiparts = \
                    h.parse_formbody( self.content_type, self.body )
            self.postparams = { h.strof(k) : list( map( h.strof, vs )) 
                                for k,vs in self.postparams.items() }
            [ self.params.setdefault( name, [] ).extend( value )
              for name, value in self.postparams.items() ]
            [ self.params.setdefault( name, [] ).extend( value )
              for name, value in self.multiparts.items() ]
            [ self.files.setdefault( name, [] 
                                   ).extend( (f['filename'], f['value'] ) )
              for name, value in self.multiparts.items() ]

    def onfinish( self ):
        """:meth:`pluggdapps.web.interfaces.IHTTPRequest.onfinish`
        interface method."""
        # Will be callbe by response.onfinish() callback.
        self.view.onfinish(self) if hasattr( self.view, 'onfinish' ) else None
        self.webapp.onfinish( self )
        self.finishedat = time.time()

    def urlfor( self, name, **matchdict ):
        """:meth:`pluggdapps.web.interfaces.IHTTPRequest.urlfor`
        interface method."""
        return self.webapp.urlfor( self, name, **matchdict )

    def pathfor( self, name, **matchdict ):
        """:meth:`pluggdapps.web.interfaces.IHTTPRequest.pathfor`
        interface method."""
        return self.webapp.pathfor( self, name, **matchdict )

    def appurl( self, webapp, name, **matchdict ):
        """:meth:`pluggdapps.web.interfaces.IHTTPRequest.appurl`
        interface method."""
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
        """:meth:`pluggdapps.plugin.ISettings.default_settings` interface 
        method.
        """
        return _default_settings

_default_settings = h.ConfigDict()
_default_settings.__doc__ = (
    "Plugin encapsulates HTTP request." )
