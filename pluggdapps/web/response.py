# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy


import http.client, time
import datetime as dt
from   http.cookies import SimpleCookie
from   os.path      import splitext, isfile

from   pluggdapps.plugin         import implements, Plugin
from   pluggdapps.web.interfaces import IHTTPResponse, IHTTPOutBound
from   pluggdapps.interfaces     import ITemplate
import pluggdapps.utils          as h

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
    """Plugin to encapsulate HTTP response."""

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
        """:meth:`pluggdapps.web.webinterfaces.IHTTPResponse.__init__`
        interface method."""
        # Initialize response attributes
        self.statuscode = b'200'
        self.reason = http.client.responses[ int(self.statuscode) ]
        self.version = request.httpconn.version
        self.headers = {}
        self.body = b''
        self.chunk_generator = None
        self.trailers = {}

        self.setcookies = SimpleCookie()

        # Initialize framework attributes
        self.request = request
        self.context = h.Context()
        self.media_type = None
        self.content_coding = None
        self.charset = self.webapp['encoding']
        self.language = self.webapp['language']

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
            self.statuscode = str(code).encode('utf-8')
        elif isinstance(code, str) :
            self.statuscode = code.encode('utf-8')
        else :
            self.statuscode = code
        return self.statuscode

    def set_header( self, name, value ):
        """:meth:`pluggdapps.web.webinterfaces.IHTTPResponse.set_header`
        interface method."""
        value = value if isinstance( value, bytes ) \
                      else str( value ).encode('utf-8')
        self.headers[ name ] = value
        return value

    def add_header( self, name, value ):
        """:meth:`pluggdapps.web.webinterfaces.IHTTPResponse.add_header`
        interface method."""
        value = value if isinstance(value,bytes) else str(value).encode('utf-8')
        pvalue = self.headers.get( name, b'' )
        self.headers[name] = b','.join([pvalue, value]) if pvalue else None
        return self.headers[name]

    def set_trailer( self, name, value ):
        """:meth:`pluggdapps.web.webinterfaces.IHTTPResponse.set_trailer`
        interface method."""
        value = value if isinstance(value,bytes) else str(value).encode('utf=8')
        self.trailers[name] = value
        return value

    def add_trailer( self, name, value ):
        """:meth:`pluggdapps.web.webinterfaces.IHTTPResponse.add_trailer`
        interface method."""
        value = value if isinstance(value,bytes) else str(value).encode('utf-8')
        pvalue = self.trailers.get(name, b'')
        self.trailers[name] = b','.join([pvalue, value]) if pvalue else None
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
        list( map( self.clear_cookie, self.setcookies.keys() ))
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
        vals = dict( h.parse_transfer_encoding(
                        self.headers.get( 'transfer_encoding', b'' ))).keys()
        return b'chunked' in list( vals )

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

        if callable( self.write_buffer ) :
            self._flush_chunk( finishing )
        else :
            self._flush_body( finishing )

    def httperror( self, statuscode=b'500', message=b'' ):
        """:meth:`pluggdapps.web.webinterfaces.IHTTPResponse.httperror`
        interface method."""
        self.statuscode = statuscode
        self.write( message ) if message else None
        self.flush( finishing=True )

    _renderers = {
        '.ttl' : 'tayra.TTLCompiler',
    }
    _renderer_plugins = {
    }
    def render( self, *args, **kwargs ):
        """:meth:`pluggdapps.interfaces.IHTTPResponse.render`
        interface method.
        
        positional argument,

        ``request``,
            Instance of plugin implement
            :class:`pluggdapps.web.interfaces.IHTTPRequest` interface.

        ``context``,
            Dictionary of context information to be passed.

        keyword arguments,

        ``file``,
            Template file to be used for rendering.

        ``text``,
            Template text to be used for rendering.

        ``ITemplate``,
            :class:`ITemplate` plugin to use for rendering. This argument
            must be in canonical form of plugin's name.

        If ``file`` keyword argument is passed, this method will resolve the
        correct renderer plugin based on file-extension. if ``text`` keyword
        argument is passed, better pass the ``ITemplate`` argument as
        well.
        """
        request, context = args[0], args[1]
        renderer = kwargs.get( 'ITemplate', None )
        if renderer is None :
            tfile = kwargs.get( 'file', '' )
            _, ext = splitext( tfile )
            renderer = self._renderers.get( ext, None ) if ext else None

            # If in debug mode enable ttl file reloading.
            tfile = h.abspath_from_asset_spec( tfile )
            if self['debug'] and isfile( tfile ):
                self.pa._monitoredfiles.append( tfile )

        if renderer in self._renderer_plugins :
            plugin = self._renderer_plugins[ renderer ]
        elif renderer :
            plugin = self.qp( ITemplate, renderer )
        else :
            plugin = None

        if plugin :
            self.media_type = 'text/html'
            self._renderer_plugins.setdefault( renderer, plugin )
            return plugin.render( context, **kwargs )
        else :
            raise Exception('Unknown renderer')

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
        self.start_response = True
        stline = self._status_line()
        return self._header_data( self.headers, stline=stline )

    def _status_line( self ):
        code = self.statuscode
        reason = http.client.responses[ int(code) ].encode( 'utf-8' )
        return b' '.join([ self.version, code, reason ])

    def _header_data( self, headers, stline=b'' ):
        # TODO : 3 header field types are specifically prohibited from
        # appearing as a trailer field: Transfer-Encoding, Content-Length and
        # Trailer.
        lines = [ stline ] if stline else []
        for n, v in headers.items() :
            nC =  h.hdr_str2camelcase.get( n, None )
            if nC == None :
                n = n.encode('utf-8')
                nC = b'-'.join([ x.capitalize() for x in n.split('_') ])
            lines.append( nC + b': ' + v )

        [ lines.append( b"Set-Cookie: " + cookie.OutputString() )
          for c in self.setcookies.values() ]

        return b"\r\n".join(lines) + b"\r\n\r\n"

    def _flush_body( self, finishing ):
        data = b''.join( self.write_buffer )
        for tr in self.webapp.out_transformers :
            data = tr.transform( self.request, data, finishing=finishing )
        if self._if_etag() :
            self.body = data 
        else :
            self.body = b''
        self.set_header( "content_length", len(self.body) )
        data = self._try_start_headers( finishing=finishing )
        if self.request.method == b'HEAD' :
            pass
        elif self.body :
            data += self.body
        self.httpconn.write( data, callback=self._onflush )
        self.write_buffer = []

    def _flush_chunk( self, finishing ):
        self.add_headers( 'transfer_encoding', 'chunked' )
        data = self._try_start_headers( finishing=finishing )

        chunk = self.write_buffer( self.request, self.c )
        for tr in self.webapp.out_transformers :
            chunk = tr.transform( self.request, chunk, finishing=finishing )

        if chunk :
            data += hex(len(chunk)).encode('utf-8') + b'\r\n' + chunk + b'\r\n'
        else :
            data += b'0\r\n'
            if self.trailers :
                data += self._header_data( self.trailers )
        self.httpconn.write( data, callback=self._onflush )

    def _if_etag( self ):
        etag = self.headers.get('etag', '')
        if self.ischunked() == False and etag :
            im = self.request.headers.get( "if_match", b'' ).strip()
            inm = self.request.headers.get( "if_none_match", b'' ).strip()
            if ( (im and im.find( etag ) == -1) or
                 (inm and inm.find( etag ) != -1) ) :
                self.set_status( b'304' )
                return False
        return True

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
    "IHTTPOutBound plugin to populate HTTP reponse with standard "
    "response-headers"
)

class ResponseHeaders( Plugin ):
    """:class:`IHTTPOutBound` plugin to populate HTTP reponse with standard
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
        """:meth:`pluggdapps.web.interfaces.IHTTPOutBound.transform`
        interface method."""
        resp = request.response
        c = resp.context
        if resp.isstarted() == False :
            resp.set_header( 'date', h.http_fromdate( time.time() ))
            resp.set_header( 'server', resp.httpconn.product )

            # Content negotiated headers
            if resp.media_type :
                mt = resp.media_type
                if resp.charset :
                    mt = '%s;charset=%s' % (mt, resp.charset)
                resp.set_header( 'content_type', mt ) 
            if resp.language :
                resp.set_header( 'content_language', resp.language )
            if resp.content_coding :
                resp.set_header( 'content_encoding', resp.content_coding )

            # For HTTP/1.1 connection can be kept alive across multiple request
            # and response.
            if request.supports_http_1_1() :
                connection = h.parse_connection(
                                    request.headers.get( "connection", b'' ))
                if b'keep-alive' in connection :
                    resp.set_header( "connection", b"Keep-Alive" )

            # Update Last-modified header field and If-* request headers
            last_modified = resp.context.get( 'last_modified', '' )
            if last_modified :
                resp.set_header( 'last_modified', last_modified )

            if resp.ischunked() == False and last_modified :
                ims = request.headers.get( 'if_modified_since', b'' )
                iums = request.headers.get( 'if_umodified_since', b'' )
                ims = ims and h.parse_date( ims.strip() )
                iums = iums and h.parse_date( iums.strip() )
                last_modified = h.parse_date( last_modified )
                if ( (ims and ims >= last_modified) or
                     (iums and iums < last_modified) ) :
                    resp.set_status( b'304' )
                    return b''

            # If etag is available from context, compute and subsequently
            # clear them.
            # IMPORANT : Do not change this sequence of last-modified and etag
            etag = c.etag.hashout( prefix="view-", joinwith=c.pop('etag','') )
            etag = ('"%s"' % etag).encode( 'utf-8' ) if etag else etag
            c.etag.clear()
            if ( resp.ischunked() == False and resp.statuscode == b'200' and
                 request.method in (b'GET', b'HEAD') and etag ) :
                resp.set_header( "etag", etag )

        return data

    @classmethod
    def default_settings( cls ):
        """:meth:`pluggdapps.plugin.interfaces.ISettings.default_settings`
        interface method."""
        return _ds2

