# Derived work from Facebook's tornado server.

"""A non-blocking, single-threaded HTTP server.

Typical applications have little direct interaction with the `HTTPIOServer`
class except to start a server at the beginning of the process
(and even that is often done indirectly via `Platform.listen`).
"""

from __future__ import absolute_import, division, with_statement

import logging, socket
import ssl  # Python 2.6+

from   pluggdapps.plugin              import Plugin, implements, pluginname, \
                                             query_plugin
from   pluggdapps.interfaces          import IServer, IRequest
from   pluggdapps.evserver.tcpserver  import TCPServer
from   pluggdapps.evserver            import stack_context
from   pluggdapps.evserver.httputil   import utf8, native_str, parse_qs_bytes, \
                                             parse_multipart_form_data
import pluggdapps.util                as h 

log = logging.getLogger( __name__ )

_default_settings = h.ConfigDict()
_default_settings.__doc__ = \
    "Configuration settings for event poll based HTTP server."

_default_settings['host']  = {
    'default' : '127.0.0.1',
    'types'   : (str,),
    'help'    : "Host addres to bind the http server."
}
_default_settings['port']  = {
    'default' : 5000,
    'types'   : (int,),
    'help'    : "Port addres to bind the http server."
}
_default_settings['multiprocess']  = {
    'default' : 0,
    'types'   : (int,),
    'help'    : "Number process to fork and listen for HTTP connections.",
}
_default_settings['max_restart']  = {
    'default' : 5,
    'types'   : (int,),
    'help'    : "In multi-process mode, maximum number of times to restart "
                "the child process.",
}
_default_settings['no_keep_alive']  = {
    'default' : False,
    'types'   : (bool,),
    'help'    : "HTTP /1.1, whether to close the connection after every "
                "request.",
}
_default_settings['backlog']  = {
    'default' : 128,
    'types'   : (int,),
    'help'    : "Back log of http request that can be queued at listening "
                "port. This option is directly passed to socket.listen()."
}
_default_settings['xheaders']  = {
    'default' : False,
    'types'   : (bool,),
    'help'    : "If `True`, `X-Real-Ip`` and `X-Scheme` headers are supported, "
                "will override the remote IP and HTTP scheme for all "
                "requests. These headers are useful when running pluggdapps "
                "behind a reverse proxy or load balancer.",
}
_default_settings['request_factory']  = {
    'default' : 'httprequest',
    'types'   : (str,),
    'help'    : "Request class whose instance will be the single argument "
                "passed on to request handler callable.",
}
_default_settings['ssloptions.certfile']  = {
    'default' : '',
    'types'   : (str,),
    'help'    : "SSL Certificate file location.",

}
_default_settings['ssloptions.keyfile']   = {
    'default' : '',
    'types'   : (str,),
    'help'    : "SSL Key file location.",

}
_default_settings['ssloptions.cert_reqs']  = {
    'default' : ssl.CERT_REQUIRED,
    'types'   : (int,),
    'options' : [ ssl.CERT_NONE, ssl.CERT_OPTIONAL, ssl.CERT_REQUIRED ],
    'help'    : "Whether a certificate is required from the other side of the "
                "connection, and whether it will be validated if provided. "
                "It must be one of the three values CERT_NONE (certificates "
                "ignored), CERT_OPTIONAL (not required, but validated if "
                "provided), or CERT_REQUIRED (required and validated). If the "
                "value of this value is not CERT_NONE, then the `ca_certs` "
                "parameter must point to a file of CA certificates."
}
_default_settings['ssloptions.ca_certs']   = {
    'default' : None,
    'types'   : (int,),
    'help'    : "The ca_certs file contains a set of concatenated "
                "certification authority. certificates, which are used to "
                "validate certificates passed from the other end of the "
                "connection."
}

class _BadRequestException(Exception):
    """Exception class for malformed HTTP requests."""
    pass


class HTTPIOServer( TCPServer, Plugin ):
    """Plugin deriving TCPServer, a non-blocking, single-threaded HTTP server.

    A server is defined by a request callback that takes a plugin implementing
    :class:`IRequest` interface as an argument and writes a valid HTTP 
    response using :class:`IResponse` interface. Finishing the request does
    not necessarily close the connection in the case of HTTP/1.1 keep-alive
    requests. A simple example server that echoes back the URI you
    requested::

        import httpserver
        import httpioloop

        def handle_request(request):
           message = "You requested %s\n" % request.uri
           request.write("HTTP/1.1 200 OK\r\nContent-Length: %d\r\n\r\n%s" % (
                         len(message), message))
           request.finish()

        http_server = httpserver.HTTPIOServer(handle_request)
        http_server.listen(8888)
        ioloop = query_plugin( ROOTAPP, ISettings, 'httpioloop' )
        ioloop.start()

    `HTTPIOServer` is a very basic connection handler. Beyond parsing the
    HTTP request body and headers, the only HTTP semantics implemented
    in `HTTPIOServer` is HTTP/1.1 keep-alive connections. We do not, however,
    implement chunked encoding, so the request callback must provide a
    ``Content-Length`` header or implement chunked encoding for HTTP/1.1
    requests for the server to run correctly for HTTP/1.1 clients. If
    the request handler is unable to do this, you can provide the
    ``no_keep_alive`` argument to the `HTTPIOServer` constructor, which will
    ensure the connection is closed on every request no matter what HTTP
    version the client is using.

    If ``xheaders`` is ``True``, we support the ``X-Real-Ip`` and ``X-Scheme``
    headers, which override the remote IP and HTTP scheme for all requests.
    These headers are useful when running pluggdapps behind a reverse proxy or
    load balancer.

    `HTTPIOServer` can serve SSL traffic with Python 2.6+ and OpenSSL. The
    implementation is available via base class TCPServer.

    """
    implements( IServer )

    def __init__( self, appname, platform, **kwargs ):
        Plugin.__init__( self, appname, platform, **kwargs )
        TCPServer.__init__( self )
        self.platform = platform

    def handle_stream( self, stream, address ):
        settings = dict([ (k,self[k]) for k in self ])
        HTTPConnection( stream, address, self.platform, settings=settings )

    def start( self, *args, **kwargs ):
        TCPServer.start( self, *args, **kwargs )

    # ISettings interface methods
    @classmethod
    def default_settings( cls ):
        return _default_settings

    @classmethod
    def normalize_settings( cls, settings ):
        settings['multiprocess']  = h.asint( 
            settings['multiprocess'], _default_settings['multiprocess'] )
        settings['no_keep_alive'] = h.asbool(
            settings['no_keep_alive'], _default_settings['no_keep_alive'] )
        settings['xheaders']      = h.asbool(
            settings['xheaders'], _default_settings['xheaders'] )
        return settings


class HTTPConnection(object):
    """Handles a connection to an HTTP client, executing HTTP requests.

    We parse HTTP headers and bodies, and execute the request callback
    until the HTTP conection is closed.
    """
    def __init__( self, stream, address, platform, settings ={} ):
        self.stream = stream
        if self.stream.socket.family not in (socket.AF_INET, socket.AF_INET6):
            # Unix (or other) socket; fake the remote address
            address = ('0.0.0.0', 0)
        self.address = address
        self.platform = platform
        self.request_factory = settings['request_factory']
        self.no_keep_alive = settings['no_keep_alive']
        self.xheaders = settings['xheaders']
        self._request = None
        self._request_finished = False
        # Save stack context here, outside of any request.  This keeps
        # contexts from one request from leaking into the next.
        self._header_callback = stack_context.wrap(self._on_headers)
        self.stream.read_until( b"\r\n\r\n", self._header_callback )
        self._write_callback = None

    def write( self, chunk, callback=None ):
        assert self._request, "Request closed"
        if not self.stream.closed():
            self._write_callback = stack_context.wrap(callback)
            self.stream.write(chunk, self._on_write_complete)

    def finish( self ):
        assert self._request, "Request closed"
        self._request_finished = True
        if not self.stream.writing():
            self._finish_request()

    def dispatch( self, request ):
        appname = self.platform.appfor( request )
        request.app = query_plugin( appname, 'IApplication', appname )
        request.app.start( request )

    def _on_write_complete(self):
        if self._write_callback is not None:
            callback = self._write_callback
            self._write_callback = None
            callback()
        # _on_write_complete is enqueued on the IOLoop whenever the
        # IOStream's write buffer becomes empty, but it's possible for
        # another callback that runs on the IOLoop before it to
        # simultaneously write more data and finish the request.  If
        # there is still data in the IOStream, a future
        # _on_write_complete will be responsible for calling
        # _finish_request.
        if self._request_finished and not self.stream.writing():
            self._finish_request()

    def _finish_request(self):
        if self.no_keep_alive:
            disconnect = True
        else:
            connection_header = self._request.headers.get("Connection")
            if connection_header is not None:
                connection_header = connection_header.lower()
            if self._request.supports_http_1_1():
                disconnect = connection_header == "close"
            elif ("Content-Length" in self._request.headers
                    or self._request.method in ("HEAD", "GET")):
                disconnect = connection_header != "keep-alive"
            else:
                disconnect = True
        self._request = None
        self._request_finished = False
        if disconnect:
            self.stream.close()
            return
        self.stream.read_until(b"\r\n\r\n", self._header_callback)

    def _on_headers(self, data):
        from pluggdapps import ROOTAPP
        try:
            data = native_str(data.decode('latin1'))
            eol = data.find("\r\n")
            start_line = data[:eol]
            try:
                method, uri, version = start_line.split(" ")
            except ValueError:
                raise _BadRequestException("Malformed HTTP request line")
            if not version.startswith("HTTP/"):
                raise _BadRequestException("Malformed HTTP version in HTTP Request-Line")

            headers = h.HTTPHeaders.parse( data[eol:] )
            self._request = query_plugin( 
                ROOTAPP, IRequest, self.request_factory,
                self, method, uri, version, headers, self.address[0],
                None, None, None )

            content_length = headers.get( "Content-Length" )
            if content_length:
                content_length = int(content_length)
                if content_length > self.stream.max_buffer_size:
                    raise _BadRequestException("Content-Length too long")
                if headers.get("Expect") == "100-continue":
                    self.stream.write(b"HTTP/1.1 100 (Continue)\r\n\r\n")
                self.stream.read_bytes(content_length, self._on_request_body)
                return

            self.dispatch( self._request )

        except _BadRequestException, e:
            logging.info( "Malformed HTTP request from %s: %s",
                          self.address[0], e )
            self.stream.close()
            return

    def _on_request_body(self, data):
        self._request.body = data
        content_type = self._request.headers.get("Content-Type", "")
        if self._request.method in ("POST", "PUT"):
            if content_type.startswith("application/x-www-form-urlencoded"):
                arguments = parse_qs_bytes(native_str(self._request.body))
                for name, values in arguments.iteritems():
                    values = [v for v in values if v]
                    if values:
                        self._request.arguments.setdefault(name, []).extend(
                            values)
            elif content_type.startswith("multipart/form-data"):
                fields = content_type.split(";")
                for field in fields:
                    k, sep, v = field.strip().partition("=")
                    if k == "boundary" and v:
                        httputil.parse_multipart_form_data(
                            utf8(v), data,
                            self._request.arguments,
                            self._request.files)
                        break
                else:
                    logging.warning("Invalid multipart/form-data")

        self.dispatch( self._request )
