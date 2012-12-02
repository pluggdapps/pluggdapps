# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy


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
    """Reponse plugin."""

    implements( IHTTPResponse )

    start_response = False
    """Response headers are already sent on the connection."""

    write_buffer = []
    """Either a list of byte-string buffered by write() method. Or a generator
    function created via chunk_generator() method."""

    flush_callback = None
    """Flush callback subscribed using flush() method."""

    finish_callback = None
    """Finish callback subscribed using set_finish_callback() method."""

    finished = False
    """A request is considered finished when there is no more response data to
    be sent for the on-going request. This is typically indicated by flushing
    the response with finishing=True argument."""

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

        # Book keeping
        self.httpconn = request.httpconn
        self.encoding = self.webapp['encoding']
        self.start_response = False
        self.write_buffer = []
        self.finished = False
        self.flush_callback = None
        self.finish_callback = None

    #---- IHTTPResponse APIs

    def set_status( self, code ):
        """:meth:`pluggdapps.web.webinterfaces.IHTTPResponse.set_status`
        interface method."""
        if isinstance(code, int) :
            self.statuscode = str(code).encode( self.encoding )
        elif isinstance(code, str) :
            self.statuscode = code.encode( self.encoding )
        else :
            self.statuscode = code
        return self.statuscode

    def set_header( self, name, value ):
        """:meth:`pluggdapps.web.webinterfaces.IHTTPResponse.set_header`
        interface method."""
        value = value if isinstance( value, bytes ) \
                      else str( value ).encode( self.encoding )
        self.headers[ name ] = value
        return value

    def add_header( self, name, value ):
        """:meth:`pluggdapps.web.webinterfaces.IHTTPResponse.add_header`
        interface method."""
        value = value if isinstance( value, bytes ) \
                      else str( value ).encode( self.encoding )
        self.headers[ name ] = b','.join( self.headers.get( name, b'' ), value )
        return self.headers[name]

    def set_trailer( self, name, value ):
        """:meth:`pluggdapps.web.webinterfaces.IHTTPResponse.set_trailer`
        interface method."""
        value = value if isinstance( value, bytes ) \
                      else str( value ).encode( self.encoding )
        self.trailers[name] = value
        return value

    def add_trailer( self, name, value ):
        """:meth:`pluggdapps.web.webinterfaces.IHTTPResponse.add_trailer`
        interface method."""
        value = value if isinstance( value, bytes ) \
                      else str( value ).encode( self.encoding )
        self.trailers[name] = b','.join( self.trailers.get( name, b'' ), value )
        return self.trailers[name]

    def set_cookie( self, name, value, **kwargs ):
        """:meth:`pluggdapps.web.webinterfaces.IHTTPResponse.set_cookie`
        interface method."""
        return self.request.cookie.set_cookie(
                    self.setcookies, name, value, **kwargs )

    def set_secure_cookie( self, name, value, expires_days=30, **kwargs ):
        """:meth:`pluggdapps.web.webinterfaces.IHTTPResponse.set_secure_cookie`
        interface method."""
        cookie = self.request.cookie
        value = cookie.create_signed_value(name, value)
        return cookie.set_cookie( self.setcookies, name, value, **kwargs )

    def clear_cookie( self, name, path="/", domain=None ):
        """:meth:`pluggdapps.web.webinterfaces.IHTTPResponse.clear_cookie`
        interface method."""
        value = self.setcookies[ name ]
        expires = dt.datetime.utcnow() - dt.timedelta(days=365)
        self.request.cookie.set_cookie( 
                    self.setcookies, name, "", path=path, expires=expires, 
                    domain=domain )
        return value

    def clear_all_cookies(self):
        """:meth:`pluggdapps.web.webinterfaces.IHTTPResponse.clear_all_cookies`
        interface method."""
        map( self.clear_cookie, self.setcookies.keys() )
        return None

    def set_finish_callback(self, callback):
        """:meth:`pluggdapps.web.webinterfaces.IHTTPResponse.set_finish_callback`
        interface method."""
        self.finish_callback = callback

    def has_finished( self ):
        """:meth:`pluggdapps.web.webinterfaces.IHTTPResponse.has_finished`
        interface method."""
        return self.finished

    def ischunked( self ):
        """:meth:`pluggdapps.web.webinterfaces.IHTTPResponse.ischunked`
        interface method."""
        x = h.parse_transfer_encoding( 
                self.headers.get( 'transfer_encoding', None ))
        return x and x[0][0] == 'chunked'

    def write( self, data ):
        """:meth:`pluggdapps.web.webinterfaces.IHTTPResponse.write`
        interface method."""
        if self.has_finished() :
            raise Exception( "Cannot write() after the response is finished." )

        data = data.encode(self.encoding) if isinstance(data, str) else data
        self.write_buffer = self.write_buffer or []
        self.write_buffer.append( data )

    def flush( self, finishing=False, callback=None ):
        """:meth:`pluggdapps.web.webinterfaces.IHTTPResponse.flush`
        interface method."""
        if callback :
            self.flush_callback = callback

        self.finished = finishing

        if callable( self.write_buffer ) :
            self.add_headers( 'transfer_encoding', 'chunked' )
            data = self._try_start_headers( finishing=finishing )
            chunk = self.write_buffer( self.request, self.c )
            data += ( hex(len(chunk)).encode( self.encoding ) + b'\r\n' +
                      chunk + b'\r\n' )
            if finishing and self.trailers :
                data += b'0\r\n' + chunk + b'\r\n'
                data += self._header_data( self.trailers )
                self.httpconn.write( data, callback=self._onflush )
            elif finishing and chunk :
                data += b'0\r\n' + chunk + b'\r\n'
                self.httpconn.write( data, callback=self._onflush )
            else :
                self.httpconn.write( data )

        else :
            respdata = b''.join( self.write_buffer )
            if finishing == True :
                if "content_length" not in self.headers :
                    self.set_header( "content_length", len( respdata ) )
            data = self._try_start_headers( finishing=finishing )
            data += respdata
            if data and self.request.method not in [ b'HEAD' ] :
                self.httpconn.write( data, callback=self._onflush )

            self.write_buffer = []

    def httperror( self, statuscode=500, message=b'' ):
        """:meth:`pluggdapps.web.webinterfaces.IHTTPResponse.httperror`
        interface method."""
        self.statuscode = statuscode
        self.write( message ) if message else None
        self.flush( finishing=True )

    def render( self, *args, **kwargs ):
        """:meth:`pluggdapps.web.webinterfaces.IHTTPResponse.render`
        interface method."""
        self.request.view

    def chunk_generator( self, callback, request, c ):
        """:meth:`pluggdapps.web.webinterfaces.IHTTPResponse.chunk_generator`
        interface method."""

        class ChunkGenerator( object ):

            def __iter__( self ):
                return self

            def next( self ):
                return callback( request, c )

        return ChunkGenerator()


    #---- Local functions

    def _try_start_headers( self, finishing=True ) :
        """Generate default headers for this response. And return the
        byte-string of response header to write. This can be overriden
        by view callable attributes."""
        if self.start_response : return b''

        self.set_header( 'date', h.http_fromdate( dt.datetime.now() ))
        self.set_header( 'server', self.httpconn.product )

        # Automatically support ETags and add the Content-Length header of
        # non-chunked transfer-coding.
        if ( self.ischunked() == False and
             self.statuscode == b'200' and
             self.request.method in ("GET", "HEAD") ) :
            if "etag" not in self.headers :
                etagv = self.etag.compute( self ) if self.etag else None
                if etagv :
                    self.set_header( "etag", etag )
                    inm = self.request.headers.get( "if_none_match" )
                    if inm and inm.find( etag ) != -1:
                        self.write_buffer = None
                        self.statuscode= b'304'

        # For HTTP/1.1 connection can be kept alive across multiple request
        # and response.
        if not self.request.supports_http_1_1() :
            if self.request.headers.get( "connection", None ) == b"Keep-Alive" :
                self.set_header( "connection", b"Keep-Alive" )

        self.start_response = True
        return self._header_data( self.headers )

    def _header_data( self, headers ):
        # TODO : 3 header field types are specifically prohibited from
        # appearing as a trailer field: Transfer-Encoding, Content-Length and
        # Trailer.

        code = self.statuscode
        reason = http.client.responses[ int(code) ].encode( self.encoding )
        lines = [ b' '.join([ self.version, code, reason ]) ]

        [ lines.append( h.hdr_str2camelcase[n] + b': ' + v )
                for n, v in headers.items() ]

        [ lines.append( b"Set-Cookie: " + cookie.OutputString() )
          for c in self.setcookies.values() ]

        return b"\r\n".join(lines) + b"\r\n\r\n"

    def _onflush( self ):
        if self.flush_callback :
            callback, self.flush_callback = self.flush_callback, None
            callback()

        if self.has_finished() : self._onfinish()

    def _onfinish( self ):
        if self.finish_callback :
            callback, self.finish_callback = self.finish_callback, None
            callback()
        self.request._onfinish()

    #---- ISettings interface methods

    @classmethod
    def default_settings( cls ):
        """:meth:`pluggdapps.web.webinterfaces.IHTTPResponse.add_header`
        interface method."""
        return _default_settings

