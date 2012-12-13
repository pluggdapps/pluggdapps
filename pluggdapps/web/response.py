# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy


import http.client, itertools, time
import datetime as dt
from   http.cookies import CookieError, SimpleCookie

from   pluggdapps.const             import CONTENT_IDENTITY
from   pluggdapps.plugin            import implements, Plugin
from   pluggdapps.web.webinterfaces import IHTTPResponse, IHTTPOutBound
import pluggdapps.utils             as h

# TODO :
#   1. user locale (server side).
#   2. Browser locale.
#   3. clear_cookie() method doesn't seem to use expires field to remove the
#      cookie from browser. Should we try that implementation instead ?

_ds1 = h.ConfigDict()
_ds1.__doc__ = (
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
        self.media_type = None
        self.content_coding = None
        self.charset = self.webapp['encoding']
        self.language = self.webapp['language']
        self.context = h.Context()


        # Book keeping
        self.httpconn = request.httpconn
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
            self.statuscode = str(code).encode( self.charset )
        elif isinstance(code, str) :
            self.statuscode = code.encode( self.charset )
        else :
            self.statuscode = code
        return self.statuscode

    def set_header( self, name, value ):
        """:meth:`pluggdapps.web.webinterfaces.IHTTPResponse.set_header`
        interface method."""
        value = value if isinstance( value, bytes ) \
                      else str( value ).encode( self.charset )
        self.headers[ name ] = value
        return value

    def add_header( self, name, value ):
        """:meth:`pluggdapps.web.webinterfaces.IHTTPResponse.add_header`
        interface method."""
        value = value if isinstance( value, bytes ) \
                      else str( value ).encode( self.charset )
        self.headers[ name ] = b','.join(
                filter( None, [self.headers.get(name, b''), value] ))
        return self.headers[name]

    def set_trailer( self, name, value ):
        """:meth:`pluggdapps.web.webinterfaces.IHTTPResponse.set_trailer`
        interface method."""
        value = value if isinstance( value, bytes ) \
                      else str( value ).encode( self.charset )
        self.trailers[name] = value
        return value

    def add_trailer( self, name, value ):
        """:meth:`pluggdapps.web.webinterfaces.IHTTPResponse.add_trailer`
        interface method."""
        value = value if isinstance( value, bytes ) \
                      else str( value ).encode( self.charset )
        self.trailers[ name ] = b','.join(
                filter( None, [self.trailers.get(name, b''), value] ))
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

    def isstarted( self ):
        """:meth:`pluggdapps.web.webinterfaces.IHTTPResponse.isstarted`
        interface method."""
        return self.start_response

    def ischunked( self ):
        """:meth:`pluggdapps.web.webinterfaces.IHTTPResponse.ischunked`
        interface method."""
        x = h.transfer_encoding( 
                self.headers.get( 'transfer_encoding', None ))
        return ('chunked' in dict(x).keys()) if x else False

    def write( self, data ):
        """:meth:`pluggdapps.web.webinterfaces.IHTTPResponse.write`
        interface method."""
        if self.has_finished() :
            raise Exception( "Cannot write() after the response is finished." )

        data = data.encode(self.charset) if isinstance(data, str) else data
        self.write_buffer = self.write_buffer or []
        self.write_buffer.append( data )

    def flush( self, finishing=False, callback=None ):
        """:meth:`pluggdapps.web.webinterfaces.IHTTPResponse.flush`
        interface method."""
        if callback :
            self.flush_callback = callback

        self.finished = finishing

        self._flush_chunk( finishing ) \
            if callable( self.write_buffer ) else self._flush_body( finishing )

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
        if self.start_response : return False
        self.start_response = True
        return self._header_data( self.headers )

    def _header_data( self, headers ):
        # TODO : 3 header field types are specifically prohibited from
        # appearing as a trailer field: Transfer-Encoding, Content-Length and
        # Trailer.

        code = self.statuscode
        reason = http.client.responses[ int(code) ].encode( self.charset )
        lines = [ b' '.join([ self.version, code, reason ]) ]

        for n, v in headers.items() :
            n = h.hdr_str2camelcase.get( 
                    n,
                    '-'.join([ x.capitalize() for x in n.split('_') 
                            ]).encode('utf-8')
                )
            lines.append( n + b': ' + v )

        [ lines.append( b"Set-Cookie: " + cookie.OutputString() )
          for c in self.setcookies.values() ]

        return b"\r\n".join(lines) + b"\r\n\r\n"

    def _flush_body( self, finishing ):
        data = b''.join( self.write_buffer )
        for tr in self.webapp.out_transformers :
            data = tr.transform( self.request, data, finishing=finishing )
        self._if_etag( self.request, self.headers.get('etag', '') )
        self.body = data
        data = self._try_start_headers( finishing=finishing )
        if self.request.method == b'HEAD' :
            self.httpconn.write( data, callback=self._onflush )
        elif data :
            data += self.body
            self.httpconn.write( data, callback=self._onflush )
        else :
            self.httpconn.write( data, callback=self._onflush )
        self.write_buffer = []

    def _flush_chunk( self, finishing ):
        self.add_headers( 'transfer_encoding', 'chunked' )
        chunkdata = self.write_buffer( self.request, self.c )
        for tr in self.webapp.out_transformers :
            chunkdata = tr.transform(
                            self.request, chunkdata, finishing=finishing )

        data = self._try_start_headers( finishing=finishing )
        data += ( hex(len(chunkdata)).encode( self.charset ) + b'\r\n' +
                  chunkdata + b'\r\n' )
        if finishing and self.trailers :
            data += b'0\r\n' + chunkdata + b'\r\n'
            data += self._header_data( self.trailers )
            self.httpconn.write( data, callback=self._onflush )
        elif finishing and chunkdata :
            data += b'0\r\n' + chunkdata + b'\r\n'
            self.httpconn.write( data, callback=self._onflush )
        else :
            self.httpconn.write( data, callback=self._onflush )

    def _if_etag( self, request, etag ):
        if request.response.ischunked() == False and etag :
            im = request.headers.get( "if_match", b'' ).strip()
            inm = request.headers.get( "if_none_match", b'' ).strip()
            if ( (im and im.find( etag ) == -1) or
                 (inm and inm.find( etag ) != -1) ) :
                self.set_status( b'304' )

    def _onflush( self ):
        if self.flush_callback :
            callback, self.flush_callback = self.flush_callback, None
            callback()

        if self.has_finished() : self._onfinish()

    def _onfinish( self ):
        if self.finish_callback :
            callback, self.finish_callback = self.finish_callback, None
            callback()
        self.request.onfinish()

    #---- ISettings interface methods

    @classmethod
    def default_settings( cls ):
        """:meth:`pluggdapps.plugin.interfaces.ISettings.default_settings`
        interface method."""
        return _ds1


_ds2 = h.ConfigDict()
_ds2.__doc__ = (
    "Configuration settings" )

class ResponseHeaders( Plugin ):
    """:class:`IHTTPOutBound` plugin populating a reponse plugin with standard
    response-headers,
      * `Date, `Server`, `Content-Type`, `Content-Encoding`,
        `Content-Language`, `Connection`, `Content-Length`, `Last-Modified`,
        `Etag`.
      * `Connection` is set only in case of HTTP1.1 and when the client is not
        requesting an explicit `Close`.
      * `Content-Length` header is set only in case of non-chunked 
        transfer-coding.
      * `Last-Modified` is set only when it is available from response
        context.
      * `Etag` is set, if available, from the response context
    """

    implements( IHTTPOutBound )

    def transform( self, request, data, finishing=False ): 
        """:meth:`pluggdapps.web.webinterfaces.IHTTPOutBound.transform`
        interface method."""
        resp = request.response
        c = resp.context
        if resp.isstarted() == False :
            resp.set_header( 'date', h.http_fromdate( time.time() ))
            resp.set_header( 'server', resp.httpconn.product )

            # Content negotiated headers
            mt = resp.media_type
            mt = ('%s;charset=%s' % (mt, resp.charset)) if resp.charset else mt
            resp.set_header( 'content_type', mt ) 
            resp.set_header( 'content_language', resp.language )

            # For HTTP/1.1 connection can be kept alive across multiple request
            # and response.
            connection = h.connection(request.headers.get("connection", None))
            if request.supports_http_1_1() and b'keep-alive' in connection :
                resp.set_header( "connection", b"Keep-Alive" )

            if resp.ischunked() == False :
                resp.set_header( "content_length", len(data) )

            # If etag is available from context, compute and subsequently
            # clear them. Manage If-* request headers.
            etag = c.etag.hashout( prefix="view-", joinwith=c.pop('etag','') )
            etag = ('"%s"' % etag).encode( 'utf-8' ) if etag else etag
            c.etag.clear()
            if ( resp.ischunked() == False and resp.statuscode == b'200' and
                 request.method in (b'GET', b'HEAD') and etag ) :
                resp.set_header( "etag", etag )

            # Update Last-modified header field and If-* request headers
            last_modified = resp.context.get( 'last_modified', '' )
            if last_modified :
                resp.set_header( 'last_modified', last_modified )

            if resp.ischunked() == False and last_modified :
                ims = request.headers.get( 'if_modified_since', b'' )
                iums = request.headers.get( 'if_umodified_since', b'' )
                ims = ims and h.parse_date( ims.strip().decode('utf-8') )
                iums = iums and h.parse_date( iums.strip().decode('utf-8') )
                last_modified = h.parse_date( last_modified )
                if ( (ims and ims >= last_modified) or
                     (iums and iums < last_modified) ) :
                    resp.set_status( b'304' )
                    return b''

        return data

    @classmethod
    def default_settings( cls ):
        """:meth:`pluggdapps.plugin.interfaces.ISettings.default_settings`
        interface method."""
        return _ds2

