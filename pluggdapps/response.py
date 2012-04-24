# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

import logging
import httplib, calendar, email, time, base64, hmac, hashlib, itertools
import datetime as dt

from   pluggdapps.config        import ConfigDict
from   pluggdapps.plugin        import Plugin, implements, query_plugin
from   pluggdapps.interfaces    import IResponse, IResponseTransformer
import pluggdapps.util          as h
import pluggdapps.stack_context as sc

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
_default_settings['IErrorPage']     = {
    'default' : '',
    'types'   : (str,),
    'help'    : "",
}

class HTTPResponse( Plugin ):
    implements( IResponse )

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
        # Start from a clean slate
        self.clear()

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
        assert status_code in httplib.responses
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
        return self.docookie.set_cookie( self.cookies, name, value, **kwargs )

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
        value = self.docookie.create_signed_value(name, value)
        return self.docookie.set_cookie( 
                self.cookies, name, value, expires_days=expires_days, **kwargs )

    def clear_cookie( self, name, path="/", domain=None ):
        """Deletes the cookie with the given name."""
        expires = dt.datetime.utcnow() - dt.timedelta(days=365)
        self.docookie.set_cookie( 
            self.cookies, name, "", path=path, expires=expires, domain=domain )

    def clear_all_cookies(self):
        """Deletes all the cookies the user sent with this request."""
        [ self.clear_cookie(name) for name in self.cookies.iterkeys() ]

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
            self.set_header( "Content-Type", "application/json; charset=UTF-8" )
        self._write_buffer.append( h.utf8(chunk) )

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
    
    def send_error( self, status_code=500, **kwargs ):
        """Sends the given HTTP error code to the browser.

        If `flush()` has already been called, it is not possible to send
        an error, so this method will simply terminate the response.
        If output has been written but not yet flushed, it will be discarded
        and replaced with the error page.

        Override `write_error()` to customize the error page that is returned.
        Additional keyword arguments are passed through to `write_error`."""
        if self._headers_written :
            log.error("Cannot send error response after headers written")
            self.finish() if not self._finished else None
            return
        self.clear()
        self.set_status( status_code )
        try:
            self.write_error( status_code, **kwargs )
        except Exception:
            log.error( "Uncaught exception in write_error", exc_info=True )
        self.finish() if not self._finished else None

    def write_error(self, status_code, **kwargs):
        """Override to implement custom error pages.

        ``write_error`` may call `write`, `render`, `set_header`, etc
        to produce output as usual.

        If this error was caused by an uncaught exception, an ``exc_info``
        triple will be available as ``kwargs["exc_info"]``.  Note that this
        exception may not be the "current" exception for purposes of
        methods like ``sys.exc_info()`` or ``traceback.format_exc``.

        For historical reasons, if a method ``get_error_html`` exists,
        it will be used instead of the default ``write_error`` implementation.
        ``get_error_html`` returned a string instead of producing output
        normally, and had different semantics for exception handling.
        Users of ``get_error_html`` are encouraged to convert their code
        to override ``write_error`` instead.
        """
        if hasattr(self, 'get_error_html'):
            if 'exc_info' in kwargs:
                exc_info = kwargs.pop('exc_info')
                kwargs['exception'] = exc_info[1]
                try:
                    # Put the traceback into sys.exc_info()
                    raise exc_info[0], exc_info[1], exc_info[2]
                except Exception:
                    self.finish(self.get_error_html(status_code, **kwargs))
            else:
                self.finish(self.get_error_html(status_code, **kwargs))
            return
        if self.settings.get("debug") and "exc_info" in kwargs:
            # in debug mode, try to send a traceback
            self.set_header('Content-Type', 'text/plain')
            for line in traceback.format_exception(*kwargs["exc_info"]):
                self.write(line)
            self.finish()
        else:
            self.finish("<html><title>%(code)d: %(message)s</title>"
                        "<body>%(code)d: %(message)s</body></html>" % {
                    "code": status_code,
                    "message": httplib.responses[status_code],
                    })

    def redirect( self, url, permanent=False, status=None ):
        """Sends a redirect to the given (optionally relative) URL.

        If the ``status`` argument is specified, that value is used as the
        HTTP status code; otherwise either 301 (permanent) or 302
        (temporary) is chosen based on the ``permanent`` argument.
        The default is 302 (temporary).
        """
        if self._headers_written :
            raise Exception("Cannot redirect after headers have been written")
        if status is None :
            status = 301 if permanent else 302
        else:
            assert isinstance(status, int) and 300 <= status <= 399
        self.set_status( status )
        # Remove whitespace
        url = re.sub(b(r"[\x00-\x20]+"), "", h.utf8(url))
        self.set_header( "Location", urlparse.urljoin( h.utf8(self.request.uri), url) )
        self.finish()

    def _keep_alive( self, request ):
        """For HTTP/1.1 connection can be kept alive across multiple request
        and response."""
        if not request.supports_http_1_1() :
            if request.headers.get( "Connection", None ) == "Keep-Alive" :
                self.set_header( "Connection", "Keep-Alive" )

    def _create_signature( self, secret, *parts ):
        hash_ = hmac.new( h.utf8(secret), digestmod=hashlib.sha1 )
        [ hash_.update(utf8(part)) for part in parts ]
        return h.utf8( hash_.hexdigest() )

    def _generate_headers( self ):
        lines = [ h.utf8( ' '.join([ self.request.version, 
                                     str(self._status_code), 
                                     httplib.responses[self._status_code] ])
                        )]
        headers = itertools.chain(self._headers.iteritems(), self._list_headers)
        lines.extend([ h.utf8(n) + b": " + h.utf8(v) for n, v in headers ])
        [ lines.append( h.utf8("Set-Cookie: " + cookie.OutputString(None)) )
          for cookie in self.cookies.values() ]
        return b"\r\n".join(lines) + b"\r\n\r\n"

    def _dowrite( self, chunk, callback=None ):
        assert isinstance(chunk, bytes)
        self.connection.write( chunk, callback=callback )

