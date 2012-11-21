# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 Netscale Computing

import http.client, itertools
import datetime as dt
from   http.cookies import CookieError, SimpleCookie

from   pluggdapps.plugin            import implements, Plugin
from   pluggdapps.web.webinterfaces import IHTTPResponse, IHTTPOutBound, \
                                           IHTTPCookie
import pluggdapps.utils             as h

# TODO :
#   1. user locale (server side).
#   2. Browser locale.
#   3. clear_cookie() method doesn't seem to use expires field to remove the
#      cookie from browser. Should we try that implementation instead ?

_default_settings = h.ConfigDict()
_default_settings.__doc__ = (
    "Configuration settings for HTTPResponse implementing IHTTPResponse "
    "interface." )

class HTTPResponse( Plugin ):
    implements( IHTTPResponse )

    start_response = False
    """Response headers are already sent on the connection."""

    write_buffers = None
    """Either a list of byte-string buffered by write() method. Or a generator
    function created via chunk_generator() method."""

    flush_callback = None
    """Flush callback subscribed using flush() method."""

    finish_callback = None
    """Finish callback subscribed using set_finish_callback() method."""

    finished = False
    """A request is considered finished when there is no more response data to
    be sent for the on-going request. This is typically indicated by calling
    finish() method on the response."""

    def __init__( self, request ):
        # Plugin attributes
        self.statuscode = b'200'
        self.reason = http.client.responses[ int(self.statuscode) ]
        self.version = request.httpconn.version
        self.headers = {}
        self.body = b''
        self.chunk_generator = None
        self.trailers = {}
        self.setcookies = SimpleCookie()
        self.request = request
        self.context = h.Context()

        # Book keeping
        self.httpconn = request.httpconn
        self.encoding = self.webapp['encoding']
        self.start_response = False
        self.write_buffers = None
        self.finished = False
        self.flush_callback = None
        self.finish_callback = None

    #---- IHTTPResponse APIs

    def set_header( self, name, value ):
        value = value if isinstance( value, bytes ) \
                      else str( value ).encode( self.encoding )
        self.headers[ name ] = value
        return value

    def add_header( self, name, value ):
        value = value if isinstance( value, bytes ) \
                      else str( value ).encode( self.encoding )
        self.headers[ name ] = b','.join( self.headers.get( name, b'' ), value )
        return self.headers[name]

    def set_trailer( self, name, value ):
        value = value if isinstance( value, bytes ) \
                      else str( value ).encode( self.encoding )
        self.trailers[name] = value
        return value

    def add_trailer( self, name, value ):
        value = value if isinstance( value, bytes ) \
                      else str( value ).encode( self.encoding )
        self.trailers[name] = b','.join( self.trailers.get( name, b'' ), value )
        return self.trailers[name]

    def set_cookie( self, name, value, **kwargs ):
        return self.request.cookie.set_cookie(
                    self.setcookies, name, value, **kwargs )

    def set_secure_cookie( self, name, value, expires_days=30, **kwargs ):
        cookie = self.request.cookie
        value = cookie.create_signed_value(name, value)
        return cookie.set_cookie( self.setcookies, name, value, **kwargs )

    def clear_cookie( self, name, path="/", domain=None ):
        value = self.setcookies[ name ]
        expires = dt.datetime.utcnow() - dt.timedelta(days=365)
        self.request.cookie.set_cookie( 
                    self.setcookies, name, "", path=path, expires=expires, 
                    domain=domain )
        return value

    def clear_all_cookies(self):
        map( self.clear_cookie, self.setcookies.keys() )
        return None

    def set_finish_callback(self, callback):
        self.finish_callback = callback

    def has_finished( self ):
        return self.finished

    def ischunked( self ):
        x = h.parse_transfer_encoding( 
                self.headers.get( 'transfer-encoding', None ))
        return x and x[0][0] == 'chunked'

    def write( self, data ):
        if self.has_finished() :
            raise Exception( "Cannot write() after finish()." )

        data = data.encode(self.encoding) if isinstance(data, str) else data
        self.write_buffers = self.write_buffers or []
        self.write_buffers.append( data )

    def flush( self, finishing=True, callback=None ):
        if callback :
            self.flush_callback = callback

        self.finished = finishing

        if callable( self.write_buffers ) :
            self.add_headers( 'transfer-encoding', 'chunked' )
            chunk = self.write_buffers( self.request, self.c )
            self.try_start_headers( finishing=finishing )
            if finishing and self.trailers :
                data = self.header_data( self.trailers )
                self.httpconn.write( data, self.headers, onflush )

        else :
            data = b''.join( self.write_buffers )
            if finishing == True :
                if "Content-Length" not in self.headers :
                    self.set_header( "Content-Length", len( data ) )
            self.try_start_headers( finishing=finishing )
            if data and self.request.method not in [ b'HEAD' ] :
                self.httpconn.write( data, callback=self.onflush )

            self.write_buffers = None

    def httperror( self, statuscode=500, message=b'' ):
        self.set_status( statuscode )
        self.write( message ) if message else None
        self.flush( finished=True )

    def render( self, *args, **kwargs ):
        self.request.view

    def chunk_generator( self, callback, request, c ):

        class ChunkGenerator( object ):

            def __iter__( self ):
                return self

            def next( self ):
                return callback( request, c )

        return ChunkGenerator()


    #---- Local functions

    def try_start_headers( self, finishing=True ) :
        """Generate default headers for this response. This can be overriden
        by view callable attributes."""
        if self.start_response : return True

        self.set_header( 'Date', h.http_fromdate( dt.datetime.now() ))
        self.set_header( 'Server', self.httpconn.product )

        # Automatically support ETags and add the Content-Length header of
        # non-chunked transfer-coding.
        if ( self.ischunked() == False and
             self.statuscode == b'200' and
             self.request.method in ("GET", "HEAD") ) :
            if "Etag" not in self.headers :
                etagv = self.etag.compute( self ) if self.etag else None
                if etagv :
                    self.set_header( "Etag", etag )
                    inm = self.request.headers.get( "if-none-match" )
                    if inm and inm.find( etag ) != -1:
                        self.write_buffers = None
                        self.set_status( b'304' )

        # For HTTP/1.1 connection can be kept alive across multiple request
        # and response.
        if not self.request.supports_http_1_1() :
            if self.request.headers.get( "Connection", None ) == "Keep-Alive" :
                self.set_header( "Connection", "Keep-Alive" )

        self.start_response = True
        data = self.header_data( self.headers )
        self.httpconn.write( data, self.headers )

    def header_data( self, headers ):
        # TODO : 3 header field types are specifically prohibited from
        # appearing as a trailer field: Transfer-Encoding, Content-Length and
        # Trailer.

        code = self.statuscode
        reason = http.client.responses[ code ].encode( self.encoding )
        lines = [ b' '.join([ self.version, code, reason ]) ]

        [ lines.append( h.hdr_camelcase[n] + b': ' + v ) for n, v in headers ]

        [ lines.append( b"Set-Cookie: " + cookie.OutputString() )
          for c in self.setcookies.values() ]

        return b"\r\n".join(lines) + b"\r\n\r\n"

    def onflush( self ):
        if self.flush_callback :
            callback, self.flush_callback = self.flush_callback, None
            callback()

        if self.has_finished() : self.onfinish()

    def onfinish( self ):
        callback, self.finish_callback = self.finish_callback, None
        callback()
        self.request.onfinish()

    #---- ISettings interface methods

    @classmethod
    def default_settings( cls ):
        return _default_settings

