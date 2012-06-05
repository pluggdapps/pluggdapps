# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

import logging
import http.client, itertools
import datetime as dt

from   pluggdapps.config        import ConfigDict
from   pluggdapps.core          import implements
from   pluggdapps.plugin        import Plugin, query_plugin
from   pluggdapps.interfaces    import IResponse, IResponseTransformer, \
                                       ICookie, IErrorPage
import pluggdapps.utils.stack_context as sc
import pluggdapps.utils         as h

# TODO :
#   1. user locale (server side).
#   2. Browser locale.
#   3. clear_cookie() method doesn't seem to use expires field to remove the
#      cookie from browser. Should we try that implementation instead ?

log = logging.getLogger(__name__)

_default_settings = ConfigDict()
_default_settings.__doc__ = \
    "Configuration settings for HTTPResponse implementing IResponse interface."

_default_settings['transforms']     = {
    'default' : '',
    'types'   : (str,),
    'help'    : "Comma separated transformation plugins to be applied on "
                "response headers and body.",
}
_default_settings['ICookie']  = {
    'default' : 'httpcookie',
    'types'   : (str,),
    'help'    : "Plugin class implementing ICookie interface specification. "
                "methods from this plugin will be used to process request "
                "cookies. Overrides :class:`ICookie` if defined in "
                "application plugin."
}
_default_settings['IErrorPage']     = {
    'default' : 'HTTPErrorPage',
    'types'   : (str,),
    'help'    : "",
}

class HTTPResponse( Plugin ):
    implements( IResponse )

    _status_code = 200
    """HTTP response status code."""

    def __init__( self, request ):
        # Attributes from request
        self.app = request.app
        # Book keeping
        self._status_code = 200
        self._headers = {}
        self._list_headers = []
        self._headers_written = False
        self._write_buffer = []
        self._transforms = h.parsecsvlines( self['transforms'] )
        self._close_callback = None
        self._finished = False
        self._auto_finish = True
        # Cookies
        self.cookies = Cookie.SimpleCookie()
        self.cookie_plugin = request.query_plugin(
                ICookie, self['ICookie'] or self.app['ICookie'] )
        # Start from a clean slate
        self.clear()
        self.context = h.Context()

        self.default_headers()

    def default_headers( self ) :
        """Generate default headers for this response. This can be overriden
        by view callable attributes."""
        self.set_header( 'Date', h.http_fromdate( dt.datetime.now() ))

    def clear( self ):
        """Resets all headers and content for this response."""
        from pluggdapps import __version__
        # The performance cost of ``HTTPHeaders`` is significant
        # (slowing down a benchmark with a trivial handler by more than 10%),
        # and its case-normalization is not generally necessary for
        # headers we generate on the server side, so use a plain dict
        # and list instead.
        self._list_headers = []
        self._write_buffer = []
        self._status_code = 200
        self._headers = {
            "Server": "PluggdappsServer/%s" % __version__,
            "Content-Type": "text/html; charset=UTF-8",
        }
        self._keep_alive( request )

    def set_status( self, status_code ):
        """Sets the status code for our response."""
        assert status_code in http.client.responses
        self._status_code = status_code

    def get_status( self ):
        """Returns the status code for our response."""
        return self._status_code

    def set_header( self, name, value ):
        """Sets the given response header name and value.

        If a datetime is given, we automatically format it according to the
        HTTP specification. If the value is not a string, we convert it to
        a string. All header values are then encoded as UTF-8.
        """
        self._headers[name] = h.convert_header_value( value )

    def add_header( self, name, value ):
        """Adds the given response header and value.

        Unlike `set_header`, `add_header` may be called multiple times
        to return multiple values for the same header.
        """
        self._list_headers.append((name, h.convert_header_value(value)))

    def set_cookie( self, name, value, **kwargs ):
        """Sets the given cookie name/value with the given options. Key-word
        arguments typically contains,
          domain, expires_days, expires, path
        Additional keyword arguments are set on the Cookie.Morsel directly.

        By calling this method cookies attribute will be updated inplace.

        See http://docs.python.org/library/cookie.html#morsel-objects
        for available attributes.
        """
        return self.cookie_plugin.set_cookie( 
                                self.cookies, name, value, **kwargs )

    def set_secure_cookie( self, name, value, expires_days=30, **kwargs ):
        """Signs and timestamps a cookie so it cannot be forged.

        You must specify the ``secret`` setting in your Application
        to use this method. It should be a long, random sequence of bytes
        to be used as the HMAC secret for the signature.

        To read a cookie set with this method, use `get_secure_cookie()`.

        Note that the ``expires_days`` parameter sets the lifetime of the
        cookie in the browser, but is independent of the ``max_age_days``
        parameter to `get_secure_cookie`.
        """
        value = self.cookie_plugin.create_signed_value(name, value)
        return self.cookie_plugin.set_cookie( 
            self.cookies, name, value, expires_days=expires_days, **kwargs )

    def clear_cookie( self, name, path="/", domain=None ):
        """Deletes the cookie with the given name."""
        expires = dt.datetime.utcnow() - dt.timedelta(days=365)
        self.cookie_plugin.set_cookie( 
            self.cookies, name, "", path=path, expires=expires, domain=domain )

    def clear_all_cookies(self):
        """Deletes all the cookies the user sent with this request."""
        [ self.clear_cookie(name) for name in list( self.cookies.keys() ) ]

    def set_close_callback( self, callback ):
        """Set a call back to be called when either the server or client
        closes this connection."""
        self._close_callback = sc.wrap( callback )

    def on_connection_close( self ):
        """Callback with this response object."""
        if self._close_callback :
            self._close_callback( self )
            self._close_callback = None

    def write( self, chunk ):
        """Writes the given chunk to the output buffer.

        To write the output to the network, use the flush() method below.

        If the given chunk is a dictionary, we write it as JSON and set
        the Content-Type of the response to be application/json.
        (if you want to send JSON as a different Content-Type, call
        set_header *after* calling write()).

        Note that lists are not converted to JSON because of a potential
        cross-site security vulnerability.  All JSON output should be
        wrapped in a dictionary.  More details at
        http://haacked.com/archive/2008/11/20/anatomy-of-a-subtle-json-vulnerability.aspx
        """
        if self._finished:
            raise Exception( "Cannot write() after finish()." )
        if isinstance( chunk, dict ):
            chunk = h.json_encode(chunk)
            self.set_header( 
                    "Content-Type", "application/json; charset=UTF-8" )
        self._write_buffer.append( chunk.encode('utf-8') )

    def flush( self, finishing=False, callback=None ):
        """Flushes the current output buffer to the network.

        The ``callback`` argument, if given, can be used for flow control:
        it will be run when all flushed data has been written to the socket.
        Note that only one flush callback can be outstanding at a time;
        if another flush occurs before the previous flush's callback
        has been run, the previous callback will be discarded.
        """
        chunk = b"".join( self._write_buffer )
        self._write_buffer = []
        if not self._headers_written :
            self._headers_written = True
            for name in self._transforms :
                t = self.request.query_plugin( IResponseTransformer, name )
                self._headers, chunk = \
                        t.start_transform( self._headers, chunk, finishing )
            headers = self._generate_headers()
        else:
            for name in self._transforms :
                chunk = t.transform( chunk, finishing )
            headers = b""

        # Ignore the chunk and only write the headers for HEAD requests
        if self.request.method == "HEAD" :
            if headers :
                self._dowrite( headers, callback=callback )
            return

        if headers or chunk:
            self._dowrite( headers + chunk, callback=callback )

    def finish( self, chunk=None ):
        """Finishes this response, ending the HTTP request."""
        if self._finished:
            raise Exception( "finish() called twice." )

        self.write(chunk) if chunk is not None else None

        # Automatically support ETags and add the Content-Length header if
        # we have not flushed any content yet.
        if not self._headers_written:
            if ( self._status_code == 200 and
                 self.request.method in ("GET", "HEAD") and
                 "Etag" not in self._headers ):
                etag = h.compute_etag()
                if etag is not None :
                    self.set_header("Etag", etag)
                    inm = self.request.headers.get( "If-None-Match" )
                    if inm and inm.find( etag ) != -1:
                        self._write_buffer = []
                        self.set_status(304)
            if "Content-Length" not in self._headers :
                self.set_header( "Content-Length", 
                                 sum( map( len, self._write_buffer )) )

        if hasattr( self.request, "connection" ):
            # TODO : Understand and fix this.
            # Now that the request is finished, clear the callback we
            # set on the IOStream (which would otherwise prevent the
            # garbage collection of the RequestHandler when there
            # are keepalive connections)
            self.request.connection.stream.set_close_callback(None)

        self.flush( finishing=True, callback=self.onfinish )

    def onfinish( self ):
        self._finished = True
        self.app.onfinish( self.request )
    
    def httperror( self, status_code=500, **kwargs ):
        """Sends the given HTTP error code to the browser.

        If `flush()` has already been called, it is not possible to send
        an error, so this method will simply terminate the response.
        If output has been written but not yet flushed, it will be discarded
        and replaced with the error page.

        It is the responsibility of the caller to finish the request by
        calling :method:`IResponse.finish`."""
        if self._headers_written :
            log.error( "Cannot send error response after headers written" )
            return
        self.clear()
        self.set_status( status_code )
        errorpage = self.request.query_plugin( IErrorPage, 'httperrorpage' )
        try:
            return errorpage.render( self.request, status_code, **kwargs )
        except Exception:
            log.error( "Uncaught exception in write_error", exc_info=True )
        return

    def redirect( self, url, permanent=False, status=None ):
        """Sends a redirect to the given (optionally relative) URL.

        If the ``status`` argument is specified, that value is used as the
        HTTP status code; otherwise either 301 (permanent) or 302
        (temporary) is chosen based on the ``permanent`` argument.
        The default is 302 (temporary).

        It is the responsibility of the caller to finish the request by
        calling :method:`IResponse.finish`.
        """
        if self._headers_written :
            raise Exception("Cannot redirect after headers have been written")
        if status is None :
            status = 301 if permanent else 302
        else:
            assert isinstance(status, int) and 300 <= status <= 399
        self.set_status( status )
        # Remove whitespace
        url = re.sub(b(r"[\x00-\x20]+"), "", url.encode('utf-8') )
        self.set_header( 
          "Location", urlparse.urljoin( self.request.uri.encode('utf-8'), url))

    def render( self, templatefile, c ):
        """Generate HTML content for request and write them using
        :method:`IResponse.write`.
        It is the responsibility of the caller to finish the request by
        calling :method:`IResponse.finish`."""
        pass

    def _keep_alive( self, request ):
        """For HTTP/1.1 connection can be kept alive across multiple request
        and response."""
        if not request.supports_http_1_1() :
            if request.headers.get( "Connection", None ) == "Keep-Alive" :
                self.set_header( "Connection", "Keep-Alive" )

    def _generate_headers( self ):

        # TODO : 3 header field types are specifically prohibited from appearing as a
        # trailer field: Transfer-Encoding, Content-Length and Trailer.

        code = str( self._status_code )
        reason = http.client.responses[ self._status_code ]
        response_line = [ self.request.version, code, reason ]
        lines = [ ' '.join( response_line ).encode('utf-8') ]

        headers = itertools.chain( self._headers.items(), self._list_headers )
        lines.extend(
            n.encode('utf-8') + b": " + v.encode('utf-8') for n, v in headers )

        [ lines.append(
            "Set-Cookie: ".encode('utf-8') + cookie.OutputString(None) 
          ) for cookie in list(self.cookies.values()) ]
        return b"\r\n".join(lines) + b"\r\n\r\n"

    def _dowrite( self, chunk, callback=None ):
        assert isinstance(chunk, bytes)
        self.connection.write( chunk, callback=callback )


    #---- ISettings interface methods

    @classmethod
    def default_settings( cls ):
        return _default_settings

    @classmethod
    def normalize_settings( cls, settings ):
        sett = super().normalize_settings( settings )
        return sett

