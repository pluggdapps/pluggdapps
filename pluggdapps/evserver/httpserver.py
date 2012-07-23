# -*- coding: utf-8 -*-

# Derived work from Facebook's tornado server.

# IMPORTANT NOTE : This server is outdated after bolting pluggdapps with
# netscale's erlang server. Someone clean it up and make this server as an
# alternate option for pluggdapps.

"""A non-blocking, single-threaded HTTP server.

Typical applications have little direct interaction with the `HTTPIOServer`
class except to start a server at the beginning of the process
(and even that is often done indirectly via `Pluggdapps.listen`).
"""

import logging, socket
import ssl  # Python 2.6+

from   pluggdapps.const import ROOTAPP
from   pluggdapps.config import ConfigDict
from   pluggdapps.plugin import Singleton, implements, query_plugin, \
                                ISettings, IWebApp
from   pluggdapps.interfaces          import IServer, IRequest
from   pluggdapps.evserver.tcpserver  import TCPServer
from   pluggdapps.evserver.httpiostream import HTTPIOStream
import pluggdapps.utils as h 
import pluggdapps.utils.stack_context as sc

# TODO :
#   * All Internet-based HTTP/1.1 servers MUST respond with a 400 (Bad Request)
#   status code to any HTTP/1.1 request message which lacks a Host header
#   field.

log = logging.getLogger( __name__ )

_default_settings = ConfigDict()
_default_settings.__doc__ = \
    "Configuration settings for event poll based HTTP server."

_default_settings['host']  = {
    'default' : '127.0.0.1',
    'types'   : (str,),
    'help'    : "Address may be either an IP address or hostname.  If it's a "
                "hostname, the server will listen on all IP addresses "
                "associated with the name. Address may be an empty string "
                "or None to listen on all available interfaces. Family may "
                "be set to either ``socket.AF_INET`` or ``socket.AF_INET6`` "
                "to restrict to ipv4 or ipv6 addresses, otherwise both will "
                "be used if available.",

}
_default_settings['port']  = {
    'default' : 5000,
    'types'   : (int,),
    'help'    : "Port addres to bind the http server."
}
_default_settings['multiprocess']  = {
    'default' : 0,
    'types'   : (int,),
    'help'    : "Number of process to fork and listen for HTTP connections.",
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
    'help'    : "If `True`, `X-Real-Ip`` and `X-Scheme` headers are "
                "supported, will override the remote IP and HTTP scheme for "
                "all requests. These headers are useful when running "
                "pluggdapps behind a reverse proxy or load balancer.",
}
#---- SSL settings.
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
#---- Setting for HTTPIOLoop
_default_settings['poll_threshold']     = {
    'default' : 1000,
    'types'   : (int,),
    'help'    : "A warning limit for number of descriptors being polled by a "
                "single poll instance. Will be used by HTTPIOLoop definition",
}
_default_settings['poll_timeout']       = {
    'default' : 3600.0,
    'types'   : (float,),
    'help'    : "In seconds. Poll instance will timeout after so many seconds "
                "and perform callbacks (if any) and start a fresh poll. Will "
                "be used by HTTPIOLoop definition",
}
#---- Settings for HTTPIOStream
_default_settings['max_buffer_size'] = {
    'default' : 104857600,
    'types'   : (int,),
    'help'    : "Maximum size of read buffer. Will be used by HTTPIOStream "
                "definition",
}
_default_settings['read_chunk_size'] = {
    'default' : 4096,
    'types'   : (int,),
    'help'    : "Reach chunk size. Will be used by HTTPIOStream definition",
}


class _BadRequestException(Exception):
    """Exception class for malformed HTTP requests."""
    pass


class HTTPIOServer( TCPServer, Singleton ):
    """Plugin deriving TCPServer, a non-blocking, multi-process HTTP server.

    A server is defined by a request callback that takes a plugin implementing
    :class:`IRequest` interface as an argument and writes a valid HTTP 
    response using :class:`IResponse` interface. Finishing the request does
    not necessarily close the connection in the case of HTTP/1.1 keep-alive
    requests.
    requested::

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

    def __init__( self, **kwargs ):
        self._sett = { k : self[k] for k in self }
        TCPServer.__init__( self, self._sett, **kwargs )

    def handle_stream( self, stream, address ): # Callback
        HTTPConnection( stream, address, settings=self._sett )

    def start( self, *args, **kwargs ):
        TCPServer.start( self, *args, **kwargs ) # Blocks !

    # ISettings interface methods
    @classmethod
    def default_settings( cls ):
        return _default_settings

    @classmethod
    def normalize_settings( cls, sett ):
        sett['port']  = h.asint( 
            sett['port'], _default_settings['port'] )
        sett['multiprocess']  = h.asint( 
            sett['multiprocess'], _default_settings['multiprocess'] )
        sett['max_restart']  = h.asint( 
            sett['max_restart'], _default_settings['max_restart'] )
        sett['no_keep_alive'] = h.asbool(
            sett['no_keep_alive'], _default_settings['no_keep_alive'] )
        sett['backlog'] = h.asint(
            sett['backlog'], _default_settings['backlog'] )
        sett['xheaders']      = h.asbool(
            sett['xheaders'], _default_settings['xheaders'] )
        sett['ssloptions.cert_reqs']   = h.asint( 
            sett['ssloptions.cert_reqs'],
            _default_settings['ssloptions.cert_reqs'] )
        sett['poll_threshold'] = h.asint(
            sett['poll_threshold'], _default_settings['poll_threshold'] )
        sett['poll_timeout']   = h.asfloat( 
            sett['poll_timeout'], _default_settings['poll_timeout'] )
        sett['max_buffer_size'] = h.asint(
            sett['max_buffer_size'], _default_settings['max_buffer_size'] )
        sett['read_chunk_size'] = h.asint(
            sett['read_chunk_size'], _default_settings['read_chunk_size'] )
        return sett


class HTTPConnection(object):
    """Handles a connection to an HTTP client, executing HTTP requests.

    We parse HTTP headers and bodies, and execute the request callback
    until the HTTP conection is closed."""
    def __init__( self, stream, address, settings ={} ):
        self.stream = stream
        if self.stream.socket.family not in (socket.AF_INET, socket.AF_INET6):
            # Unix (or other) socket; fake the remote address
            address = ('0.0.0.0', 0)
        self.address = address
        self.pa = query_plugin( ROOTAPP, ISettings, 'pluggdapps' )
        self.settings = settings
        self.no_keep_alive = settings['no_keep_alive']
        self.xheaders = settings['xheaders']

        # Per request attributes
        self.startline = None
        self.headers = None
        self.body = None
        self.receiving = False
        self.responding = False

        # Save stack context here, outside of any request.  This keeps
        # contexts from one request from leaking into the next.
        self._header_callback = sc.wrap( self.on_headers )
        self._write_callback = None
        self._close_callback = None
        self.stream.read_until( b"\r\n\r\n", self._header_callback )

        # on-connection
        self.stream.set_close_callback( self.on_connection_close )

    def get_ssl_certificate( self ):
        try:
            return self.stream.socket.get_ssl_certificate()
        except ssl.SSLError:
            return None

    def set_close_callback( self, callback ):
        self._close_callback = sc.wrap( callback )

    def write( self, chunk, callback=None ):
        assert self.responding, "Request closed"
        if not self.stream.closed() :
            self._write_callback = sc.wrap( callback )
            self.stream.write( chunk, self.on_write_complete )

    def finish( self ):
        assert self.responding, "Request closed"
        if not self.stream.writing() :
            self._finish_request()

    def dispatch( self ):
        # Move to respondin state.
        self.receiving = False
        self.responding = True
        # Resolve, compose and handle request.
        request = self.pa.makerequest( 
                self, self.address, self.startline, self.headers, self.body )
        request.app.start( request )
        # Reset request attributes
        self.startline = None
        self.headers = None
        self.body = None

    def on_write_complete( self ):
        if self._write_callback is not None:
            callback = self._write_callback
            self._write_callback = None
            callback()
        # on_write_complete is enqueued on the IOLoop whenever the
        # IOStream's write buffer becomes empty, but it's possible for
        # another callback that runs on the IOLoop before it to
        # simultaneously write more data and finish the request.  If
        # there is still data in the IOStream, a future
        # on_write_complete will be responsible for calling
        # _finish_request.
        if self.responding and not self.stream.writing():
            self._finish_request()

    def supports_http_1_1( self ):
        return self.version == "HTTP/1.1"

    def _finish_request( self ):
        if self.no_keep_alive:
            disconnect = True
        else:
            connection_header = self.headers.get( "Connection", None )
            if connection_header is not None:
                connection_header = connection_header.lower()
            if self.supports_http_1_1():
                disconnect = connection_header == "close"
            elif ("Content-Length" in self.headers
                    or self.method in ("HEAD", "GET")):
                disconnect = connection_header != "keep-alive"
            else:
                disconnect = True
        self.responding = False
        if disconnect:
            self.stream.close()
            return
        self.stream.read_until( b"\r\n\r\n", self._header_callback )

    def on_headers( self, data ):
        self.receiving = True
        try :
            data = data.decode( 'utf-8' )
            # Remove empty-lines CRLFs prefixed to request message
            data = data.rstrip('\r\n')
            # Get request-startline
            eol = data.find("\r\n")
            self.startline = data[:eol]

            self.method, self.uri, self.version = \
                            h.parse_startline( self.startline )

            self.headers = h.HTTPHeaders.parse( data[eol:] )

            content_length = self.headers.get( "Content-Length" )
            if content_length:
                content_length = int(content_length)
                if content_length > self.stream.max_buffer_size:
                    raise h.Error("Content-Length too long")
                if self.headers.get("Expect") == "100-continue":
                    self.stream.write(b"HTTP/1.1 100 (Continue)\r\n\r\n")
                self.stream.read_bytes(content_length, self.on_request_body)
                return

            self.dispatch()

        except h.Error as e:
            log.warn("Malformed HTTP request from %s: %s", self.address[0], e)
            self.stream.close()
            self.receiving = False
            return

    def on_request_body( self, data ):
        self.body = data
        self.dispatch()

    def on_connection_close( self ):
        if self._close_callback is not None:
            callback = self._close_callback
            self._close_callback = None
            callback()
