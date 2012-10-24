# -*- coding: utf-8 -*-

"""HTTP web server based on epoll event-loop using non-blocking sockets.

In addition to I/O events, the server also does generic callback handling and
schedule time-based events.
"""

import datetime, errno, heapq, time, os, select, socket, re, collections
import ssl  # Python 2.6+

import pluggdapps.utils         as h
from   pluggdapps.plugin        import Plugin, implements, query_plugin
from   pluggdapps.interfaces    import IServer


# TODO :
#   * All Internet-based HTTP/1.1 servers MUST respond with a 400 (Bad Request)
#     status code to any HTTP/1.1 request message which lacks a Host header
#     field.

_default_settings = h.ConfigDict()
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
_default_settings['ssl.certfile']  = {
    'default' : '',
    'types'   : (str,),
    'help'    : "SSL Certificate file location.",

}
_default_settings['ssl.keyfile']   = {
    'default' : '',
    'types'   : (str,),
    'help'    : "SSL Key file location.",

}
_default_settings['ssl.cert_reqs']  = {
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
_default_settings['ssl.ca_certs']   = {
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
    'default' : 104857600,  # 100MB
    'types'   : (int,),
    'help'    : "Maximum size of read buffer. Will be used by HTTPIOStream "
                "definition",
}
_default_settings['read_chunk_size'] = {
    'default' : 4096,
    'types'   : (int,),
    'help'    : "Reach chunk size. Will be used by HTTPIOStream definition",
}


class HTTPEPollServer( Plugin ):
    """A non-blocking, single-threaded HTTP Server plugin.

    `HTTPEPollServer` can serve SSL traffic with Python 2.6+ and OpenSSL. 
    To make this server serve SSL traffic, configure this plugin with
    `ssl.*` settings which is required for the `ssl.wrap_socket`
    method, including "certfile" and "keyfile".

    A server is defined by a request callback that takes a plugin implementing
    :class:`IRequest` interface as an argument and writes a valid HTTP 
    response using :class:`IResponse` interface. Finishing the request does
    not necessarily close the connection in the case of HTTP/1.1 keep-alive
    requests.

    :class:`HTTPEPollServer` is a very basic connection handler. Beyond parsing
    the HTTP request body and headers, the only HTTP semantics implemented
    by this plugin is is HTTP/1.1 keep-alive connections. ``no_keep_alive``
    settings will ensure that connection is closed on every request no matter
    what HTTP version the client is using.

    If ``xheaders`` is ``True``, we support the ``X-Real-Ip`` and ``X-Scheme``
    headers, which override the remote IP and HTTP scheme for all requests.
    These headers are useful when running pluggdapps behind a reverse proxy or
    load balancer. """

    implements( IServer )

    _sockets = {}
    """Dictionary of listening sockets."""

    ioloop = None
    "IOLoop instance for event-polling."""

    def __init__( self ):
        # configuration settings
        self._sockets = {}  # fd->socket mapping.
        self.ioloop = None

    def start( self ):
        """Starts this server using IOloop."""
        self.listen()
        self.ioloop.start() # Block !
        self.ioloop.close()

    def listen( self ):
        """Starts accepting connections on the given port.

        This method may be called more than once to listen on multiple ports.
        `listen` takes effect immediately; it is not necessary to call
        `HTTPEPollServer.start` afterwards.  It is, however, necessary to start
        the `IOLoop`.
        """
        port, host, backlog = self['port'], self['host'], self['backlog']
        sockets = self.bind_sockets( port, host, None, backlog )
        self.add_sockets( sockets )

    def add_sockets( self, sockets ):
        """Make the server start accepting connections using event loop on the
        given sockets.

        The ``sockets`` parameter is a list of socket objects such as
        those returned by `bind_sockets`.
        """
        self.ioloop = IOLoop( self )
        for sock in sockets:
            self._sockets[ sock.fileno() ] = sock
            add_accept_handler(self, sock, self.handle_connection, self.ioloop)

    def stop( self ):
        """Stops listening for new connections.

        Requests currently in progress may still continue after the
        server is stopped.
        """
        for fd, sock in self._sockets.items() :
            self.ioloop.remove_handler(fd)
            self.ioloop.stop()
            sock.close()

    def handle_connection( self, conn, address ):
        sslopts = h.settingsfor( 'ssl.', self.sett )
        is_ssl = sslopts['keyfile'] and sslopts['certfile']
        if is_ssl :
            try:
                conn = ssl.wrap_socket( conn,
                                        server_side=True,
                                        do_handshake_on_connect=False,
                                        **sslopts )
            except ssl.SSLError as err:
                self.pa.logerror( "Error in SSL connection with %s" % address )
                if err.args[0] == ssl.SSL_ERROR_EOF:
                    return conn.close()
                else:
                    raise
            except socket.error as err:
                if err.args[0] == errno.ECONNABORTED:
                    return conn.close()
                else:
                    raise
        try:
            if is_ssl :
                stream = SSLIOStream( conn, address, self.ioloop, self )
            else :
                stream = IOStream( conn, address, self.ioloop, self ) 

            HTTPConnection( stream, address, self )

        except Exception:
            self.pa.logerror( "Error in connection callback" )
            pass

    def bind_sockets( self )
        """Creates listening sockets (server) bound to the given port and address.

        Returns a list of socket objects (multiple sockets are returned if
        the given address maps to multiple IP addresses, which is most common
        for mixed IPv4 and IPv6 use).

        Address may be either an IP address or hostname.  If it's a hostname,
        the server will listen on all IP addresses associated with the
        name.  Address may be an empty string or None to listen on all
        available interfaces.  Family may be set to either socket.AF_INET
        or socket.AF_INET6 to restrict to ipv4 or ipv6 addresses, otherwise
        both will be used if available.

        The ``backlog`` argument has the same meaning as for ``socket.listen()``.
        """
        address, port, family, backlog = \
                self['address'], self['port'], self['family'], self['backlog']

        family = family or socket.AF_UNSPEC
        sockets = []
        address = None if address == "" else address
        flags = socket.AI_PASSIVE
        addrinfo = set([])

        if hasattr(socket, "AI_ADDRCONFIG"):
            # AI_ADDRCONFIG ensures that we only try to bind on ipv6
            # if the system is configured for it, but the flag doesn't
            # exist on some platforms (specifically WinXP, although
            # newer versions of windows have it)
            flags |= socket.AI_ADDRCONFIG
            addrinfo = set(
                socket.getaddrinfo(
                    address, port, family, socket.SOCK_STREAM, 0, flags))

        for res in addrinfo :
            self.pa.loginfo( "Binding socket for %s" % res )
            af, socktype, proto, canonname, sockaddr = res
            sock = socket.socket(af, socktype, proto)
            h.set_close_exec( sock.fileno() )
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if af == socket.AF_INET6:
                # On linux, ipv6 sockets accept ipv4 too by default,
                # but this makes it impossible to bind to both
                # 0.0.0.0 in ipv4 and :: in ipv6.  On other systems,
                # separate sockets *must* be used to listen for both ipv4
                # and ipv6.  For consistency, always disable ipv4 on our
                # ipv6 sockets and use a separate ipv4 socket when needed.
                #
                # Python 2.x on windows doesn't have IPPROTO_IPV6.
                if hasattr(socket, "IPPROTO_IPV6"):
                    sock.setsockopt( socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1 )
            self.pa.loginfo( "Set server socket to non-blocking mode ..." )
            sock.setblocking(0) # Set to non-blocking.
            sock.bind( sockaddr )
            self.pa.loginfo( "Server listening with a backlog of %s" % backlog )
            sock.listen( backlog )
            sockets.append( sock )
        return sockets

    #---- ISettings interface methods

    @classmethod
    def default_settings( cls ):
        return _default_settings

    @classmethod
    def normalize_settings( cls, sett ):
        _ds = _default_settings
        sett['port']  = h.asint( sett['port'], _ds['port'] )
        sett['no_keep_alive'] = h.asbool( sett['no_keep_alive'], _ds['no_keep_alive'] )
        sett['backlog'] = h.asint( sett['backlog'], _ds['backlog'] )
        sett['xheaders'] = h.asbool( sett['xheaders'], _ds['xheaders'] )
        sett['ssl.cert_reqs'] = h.asint( sett['ssl.cert_reqs'], _ds['ssl.cert_reqs'] )
        sett['poll_threshold'] = h.asint( sett['poll_threshold'], _ds['poll_threshold'] )
        sett['poll_timeout']   = h.asfloat( sett['poll_timeout'], _ds['poll_timeout'] )
        sett['max_buffer_size'] = h.asint( sett['max_buffer_size'], _ds['max_buffer_size'] )
        sett['read_chunk_size'] = h.asint( sett['read_chunk_size'], _ds['read_chunk_size'] )
        return sett


class HTTPConnection( object ):
    """Handles a connection to an HTTP client, executing HTTP requests.

    We parse HTTP headers and bodies, and execute the request callback
    until the HTTP conection is closed."""

    startline = None
    """Request startline."""

    headers = None
    """Request headers."""

    body = None
    """Request body."""

    receiving = False
    """Connection is currently receiving a request."""

    responding = False
    """Connection is currently sending a response."""

    _write_callback = None
    """Call-back for writing data to connection."""

    _close_callback = None
    """Call-back when connection is closed."""

    def __init__( self, stream, address, server ):
        self.stream = stream
        if self.stream.socket.family not in (socket.AF_INET, socket.AF_INET6):
            # Unix (or other) socket; fake the remote address
            address = ('0.0.0.0', 0)
        self.address = address
        self.pa = server.pa
        self.server = server

        # Per request attributes
        self.startline = None
        self.headers = None
        self.body = None
        self.receiving = False
        self.responding = False

        # Save stack context here, outside of any request.  This keeps
        # contexts from one request from leaking into the next.
        self._write_callback = None

        self.stream.read_until( b"\r\n\r\n", self.on_headers )

        self.stream.set_close_callback( self.on_connection_close )

    def get_ssl_certificate( self ):
        try:
            return self.stream.socket.get_ssl_certificate()
        except ssl.SSLError:
            return None

    def set_close_callback( self, callback ):
        self._close_callback = callback

    def write( self, chunk, callback=None ):
        """Write a chunk of data."""
        assert self.responding, "Request closed"
        if not self.stream.closed() :
            self._write_callback = callback
            self.stream.write( chunk, self.on_write_complete )

    def finish( self ):
        assert self.responding, "Request closed"
        if not self.stream.writing() :
            self._finish_request()

    def dispatch( self ):
        # Move to responding state.
        self.receiving = False
        self.responding = True
        # Resolve, compose and handle request.
        # request = self.server.pa.makerequest( 
        #         self, self.address, self.startline, self.headers, self.body )
        # request.app.start( request )

        # Reset request attributes
        self.startline = self.headers = self.body = None

    #---- Callback handlers

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
        if self.server['no_keep_alive']:
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
        self.stream.read_until( b"\r\n\r\n", self.on_headers )

    def on_headers( self, data ):
        self.receiving = True
        try :
            data = data.decode( 'utf-8' )
            # Remove empty-lines CRLFs prefixed to request message
            data = data.rstrip('\r\n')
            # Get request-startline
            eol = data.find("\r\n")
            self.startline = sline = data[:eol]

            self.method, self.uri, self.version = h.parse_startline(data[:eol])
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
            #log.warn("Malformed HTTP request from %s: %s", self.address[0], e)
            self.stream.close()
            self.receiving = False
            return

    def on_request_body( self, data ):
        self.body = data
        self.dispatch()

    def on_connection_close( self ):
        """This method will be invoked by the stream object when socket is
        closed. In return this connection must call any subscribed callback.
        """
        if self._close_callback is not None:
            callback = self._close_callback
            self._close_callback = None
            callback()


def run_callback( server, callback, *args ):
    """Run a callback with `args`."""
    try:
        callback( *args )
    except Exception:
        server.pa.logerror( "Exception in callback %r" % callback )

class Timeout( object ):
    """Heapable timeout, a UNIX timestamp and a callback"""

    # Reduce memory overhead when there are lots of pending callbacks
    __slots__ = ['deadline', 'callback']

    def __init__( self, deadline, callback ):
        if isinstance( deadline, (int, float) ):
            self.deadline = deadline
        elif isinstance( deadline, datetime.timedelta ):
            self.deadline = time.time() + h.timedelta_to_seconds(deadline)
        else:
            raise TypeError( "Unsupported deadline %r" % deadline )
        self.callback = callback

    # Comparison methods to sort by deadline, with object id as a tiebreaker
    # to guarantee a consistent ordering.  The heapq module uses __le__
    # in python2.5, and __lt__ in 2.6+ (sort() and most other comparisons
    # use __lt__).
    def __lt__( self, other ):
        return ( (self.deadline, id(self)) < (other.deadline, id(other)) )

    def __le__( self, other ):
        return ( (self.deadline, id(self)) <= (other.deadline, id(other)) )


class Waker( object ):
    """A dummy file-descriptor watched by event-poll. To wake up the epoll as
    we desire."""

    def __init__(self):
        r, w = os.pipe()
        h.set_nonblocking(r, w)
        h.set_close_exec(r, w)
        self.reader = os.fdopen(r, "rb", 0)
        self.writer = os.fdopen(w, "wb", 0)

    def fileno(self):
        return self.reader.fileno()

    def wake(self):
        try           : self.writer.write("x")
        except IOError: pass

    def consume(self):
        try :
            ss, s = b'', self.reader.read()
            while s :
                ss += s 
                s = self.reader.read()
        except IOError:
            pass
        return ss

    def close(self):
        self.reader.close()
        self.writer.close()


class IOLoop( Plugin ):
    """A level-triggered I/O loop using Linux epoll and requires python 3."""

    # Constants from the epoll module
    _EPOLLIN    = 0x001
    _EPOLLPRI   = 0x002
    _EPOLLOUT   = 0x004
    _EPOLLERR   = 0x008
    _EPOLLHUP   = 0x010
    _EPOLLRDHUP = 0x2000
    _EPOLLONESHOT = (1 << 30)
    _EPOLLET    = (1 << 31)

    # Our events map exactly to the epoll events
    NONE  = 0
    READ  = _EPOLLIN
    WRITE = _EPOLLOUT
    ERROR = _EPOLLERR | _EPOLLHUP

    # Book keeping
    _evpoll = {}
    """EPoll descriptor, returned by select.epoll()."""

    _handlers = {}
    """A map of polled descriptor and callback handlers."""

    _events = {}
    """Dictionary of file-descriptors and events that woke-up the
    descriptor."""

    _callbacks = []
    """Lock object to handle ioloop callbacks in a multi-threaded
    environment."""

    _timeouts = []
    """A heap queue list to manage timeout events and its callbacks."""

    _running = False
    """Initialized to True when start() is called and set to False to
    indicate that stop() is called."""

    _stopped = False
    """Set to True when stop() is called and reset to False when start()
    exits."""

    _waker = None
    """Create a pipe that we send bogus data to when we want to wake
    the I/O loop when it is idle."""

    def __init__( self, server ):

        self.poll_threshold = server['poll_threshold']
        self.poll_timeout = server['poll_timeout']
        self.server = server

        self._evpoll = select.epoll()
        self._waker = Waker()

        h.set_close_exec( self._evpoll.fileno() )

        # Book keeping
        self._handlers = {}
        self._events = {}
        self._callbacks = []
        self._timeouts = []
        self._running = False
        self._stopped = False

        self.server.pa.loginfo( "Adding poll-loop waker ..." )
        self.add_handler( self._waker.fileno(), 
                          lambda fd, events: self._waker.consume(), # handler
                          self.READ )

    #---- Manage polled descriptors and its callback handlers.

    def add_handler( self, fd, handler, events ):
        """Registers the given handler to receive the given events for fd."""
        self._handlers[fd] = handler
        self._evpoll.register( fd, events | self.ERROR )
        if len(self._handlers) > self.poll_threshold :
            msg = "Polled descriptors exceeded threshold" % self.poll_threshold
            self.server.pa.logwarn( msg )

    def update_handler( self, fd, events ):
        """Changes the events we listen for fd."""
        self._evpoll.modify( fd, events | self.ERROR )

    def remove_handler( self, fd ):
        """Stop listening for events on fd."""
        self._handlers.pop(fd, None)
        self._events.pop(fd, None)
        try:
            self._evpoll.unregister(fd)
        except (OSError, IOError):
            self.server.pa.logwarn( "Error deleting fd from epoll" )

    #---- Manage timeout handlers on this epoll using heap queue.

    def add_timeout( self, deadline, callback ):
        """Calls the given callback at the time deadline from IOloop.

        Returns a handle that may be passed to remove_timeout to cancel.

        ``deadline`` may be a number denoting a unix timestamp (as returned
        by ``time.time()`` or a ``datetime.timedelta`` object for a deadline
        relative to the current time."""
        timeout = Timeout( deadline, callback )
        heapq.heappush( self._timeouts, timeout )
        return timeout

    def remove_timeout( self, timeout ):
        """Cancels a pending timeout. The argument is a handle as returned by
        add_timeout().
        """
        # Removing from a heap is complicated, so just leave the defunct
        # timeout object in the queue (see discussion in
        # http://docs.python.org/library/heapq.html).
        # If this turns out to be a problem, we could add a garbage
        # collection pass whenever there are too many dead timeouts.
        timeout.callback = None


    #---- manage straight-forward callbacks inside evented ioloop.

    def add_callback( self, callback ):
        """Calls the given callback on the next I/O loop iteration."""
        list_empty = not self._callbacks
        self._callbacks.append( callback )
        self._waker.wake() if list_empty else None

    #---- Perform evented polling.

    def start( self ):
        """Starts the I/O loop.

        The loop will run until one of the I/O handlers calls stop(), which
        will make the loop stop after the current event iteration completes.
        """
        if self._stopped :
            self._stopped = False
            return

        self._running = True
        while True :
            poll_timeout = self.poll_timeout

            # Prevent IO event starvation by delaying new callbacks
            # to the next iteration of the event loop.
            callbacks = self._callbacks
            self._callbacks = []
            [ run_callback( self.server, callback ) for callback in callbacks ]

            # Handle timeouts
            if self._timeouts :
                now = time.time()
                while self._timeouts :
                    if self._timeouts[0].callback is None: # cancelled timeout
                        heapq.heappop( self._timeouts )
                    elif self._timeouts[0].deadline <= now:
                        timeout = heapq.heappop( self._timeouts )
                        run_callback( self.server, timeout.callback )
                    else:
                        seconds = self._timeouts[0].deadline - now
                        poll_timeout = min(seconds, poll_timeout)
                        break

            if self._callbacks :
                # If any callbacks or timeouts called add_callback,
                # we don't want to wait in poll() before we run them.
                poll_timeout = 0.0

            if self._running == False : # stop() is called !
                break

            try:
                event_pairs = self._evpoll.poll( poll_timeout )
            except Exception as e:
                # Depending on python version and event-loop implementation,
                # different exception types may be thrown and there are
                # two ways EINTR might be signaled:
                # * e.errno == errno.EINTR
                # * e.args is like (errno.EINTR, 'Interrupted system call')
                if (getattr(e, 'errno', None) == errno.EINTR or
                    (isinstance(getattr(e, 'args', None), tuple) and
                     len(e.args) == 2 and e.args[0] == errno.EINTR)):
                    continue
                else:
                    raise

            # Pop one fd at a time from the set of pending fds and run
            # its handler. Since that handler may perform actions on
            # other file descriptors, there may be reentrant calls to
            # this IOLoop that update self._events
            self._events.update(event_pairs)
            while self._events :
                fd, events = self._events.popitem()
                try:
                    if fd in self._handlers :
                        self._handlers[fd]( fd, events )
                except (OSError, IOError) as e:
                    if e.args[0] == errno.EPIPE:
                        # Happens when the client closes the connection
                        pass
                    else:
                        msg = "Exception in I/O handler for fd %s" % fd
                        self.server.pa.logerror( msg )
                except Exception:
                    msg = "Exception in I/O handler for fd %s" % fd
                    self.server.pa.logerror( msg )

        # reset the stopped flag so another start/stop pair can be issued
        self._stopped = False

    #---- Shutdown methods

    def stop( self ):
        """Stop the loop after the current event loop iteration is complete.
        If the event loop is not currently running, the next call to start()
        will return immediately.

        Note that even after `stop` has been called, epoll is not completely
        stopped until `self.start()` has also returned.
        """
        self.server.pa.loginfo( "Stopping poll loop ..." )
        self._running = False
        self._stopped = True
        self._waker.wake()  # Wake the ioloop

    def close( self ):
        """Closes the event-poll, freeing any resources used.

        An IOLoop must be completely stopped before it can be closed.  This
        means that `self.stop()` must be called *and* 
        `self.start()` must be allowed to return before attempting to 
        call `IOLoop.close()`. Therefore the call to `close` will usually 
        appear just after the call to `start` rather than near the call to 
        `stop`. """
        self.remove_handler( self._waker.fileno() )
        for fd in self._handlers.keys() :
            try : os.close( fd )
            except Exception :
                self.server.pa.loginfo( "error closing fd %s" % fd )
        self._waker.close()
        self._evpoll.close()


class IOStream( object ):
    """A utility class to write to and read from a non-blocking socket.

    We support a non-blocking ``write()`` and a family of ``read_*()`` methods.
    All of the methods take callbacks (since writing and reading are
    non-blocking and asynchronous).

    The socket is a resulting connected socket via socket.accept()."""

    socket = None
    """Socket object (accepted by the server) to stream data."""

    address = None
    """socket address for the other end of connection."""

    ioloop = None
    """Event loop for epoll service."""

    server = None
    """Server plugin instance."""

    max_buffer_size = 0
    """Maximum read / write buffer size."""

    read_chunk_size = 0
    """Maximum chunk of data to read at a time."""

    _read_buffer = None
    """A collection object to buffer read bytes from socket."""

    _write_buffer = None
    """A collection object to buffer bytes to be written to socket."""

    _read_buffer_size = 0
    """Indicates the size of available read data in _read_buffer."""

    _write_buffer_frozen = False

    _read_delimiter = None
    """stream reads data from the socket until this delimiter is detected."""

    _read_regex = None
    """stream reads data from the socket until a pattern specified by this
    regular expression is detected"""

    _read_bytes = None
    """stream reads specified number of bytes from the socket."""

    _read_until_close = False
    """stream reads data from the socket until the socket is closed."""

    _read_callback = None
    """Call back for one of the read*() APIs."""

    _streaming_callback = None
    """In case of reading specified number of bytes or read until close, this 
    callback is called for every chunk that are read."""

    _write_callback = None
    """Call back for one of the write*() APIs."""

    _close_callback = None
    """Call back when socket is closed."""

    _state = None
    """IO Events for which this connection is polled for."""

    _pending_callbacks = 0

    def __init__( self, socket, address, ioloop, server ):
        self.socket = socket
        self.address = address
        self.ioloop = ioloop
        self.server = server
        self.socket.setblocking( False )

        # configuration settings
        self.max_buffer_size = server['max_buffer_size']
        self.read_chunk_size = server['read_chunk_size']

        self._read_buffer = collections.deque()
        self._write_buffer = collections.deque()
        self._read_buffer_size = 0
        self._write_buffer_frozen = False
        self._read_delimiter = None
        self._read_regex = None
        self._read_bytes = None
        self._read_until_close = False
        self._read_callback = None
        self._streaming_callback = None
        self._write_callback = None
        self._close_callback = None
        self._state = None
        self._pending_callbacks = 0

    #---- API methods.

    def read_until_regex(self, regex, callback):
        """Call callback when we read the given regex pattern. Callback
        is passed with binary data."""
        self.set_read_callback( callback )
        self._read_regex = re.compile( regex )
        self.tryread()

    def read_until(self, delimiter, callback):
        """Call callback when we read the given delimiter. Callback is passed
        with binary data."""
        self.set_read_callback( callback )
        self._read_delimiter = delimiter
        self.tryread()

    def read_bytes( self, num_bytes, callback, streaming_callback=None ):
        """Call callback when we read the given number of bytes. Callback is
        passed with binary data.

        If a ``streaming_callback`` is given, it will be called with chunks
        of data as they become available, and the argument to the final
        ``callback`` will be empty.
        """
        self.set_read_callback( callback )
        self._read_bytes = num_bytes
        self._streaming_callback = streaming_callback
        self.tryread()

    def read_until_close( self, callback, streaming_callback=None ):
        """Reads all data from the socket until it is closed. Callback is
        passed with binary data.

        If a ``streaming_callback`` is given, it will be called with chunks
        of data as they become available, and the argument to the final
        ``callback`` will be empty.

        Subject to ``max_buffer_size`` limit if a ``streaming_callback`` is 
        not used.
        """
        self.set_read_callback(callback)

        if self.closed() : # Already closed.
            self.docallback( self._read_buffer_size, callback )
            return

        self._read_until_close = True
        self._streaming_callback = streaming_callback
        self.add_io_state( self.ioloop.READ )

    def write( self, data, callback=None ):
        """Write the given data to this stream. `data` is expected to be in
        bytes.

        If callback is given, we call it when all of the buffered write
        data has been successfully written to the stream. If there was
        previously buffered write data and an old write callback, that
        callback is simply overwritten with this new callback.
        """
        self.check_closed()
        if data :
            # We use bool(_write_buffer) as a proxy for write_buffer_size>0,
            # so never put empty strings in the buffer.
            self._write_buffer.append( data )
        self._write_callback = callback
        self.handle_write()
        if self._write_buffer :
            self.add_io_state( self.ioloop.WRITE )
        self.maybe_add_error_listener()

    def set_close_callback( self, callback ):
        """Call the given callback when the stream is closed."""
        self._close_callback = callback

    def close( self ):
        """Close this stream."""
        self.server.logifo( "Closing the stream for %r", self.address )
        if self.socket is not None:

            if self._read_until_close:
                self.docallback( self._read_buffer_size, self._read_callback )

            if self._state is not None:
                self.ioloop.remove_handler( self.socket.fileno() )
                self._state = None

            self.socket.close()
            self.socket = None
        self.maybe_run_close_callback()

    def reading(self):
        """Returns true if we are currently reading from the stream."""
        return self._read_callback is not None

    def writing(self):
        """Returns true if we are currently writing to the stream."""
        return bool(self._write_buffer)

    def closed(self):
        """Returns true if the stream has been closed."""
        return self.socket is None

    #---- Local methods.

    def maybe_run_close_callback(self):
        """If a close-callback is subscribed, try calling back.  If there are
        pending callbacks, don't run the close callback until they're done
        (see _maybe_add_error_handler)."""
        if ( self.socket is None and self._close_callback and
             self._pending_callbacks == 0 ):

            cb = self._close_callback
            self._close_callback = None
            run_callback( self.server, cb )

    def docallback( self, consume_bytes, callback ):
        """There can be only one callback subscribed on a read. Either for 
             read_bytes(), read_until(), read_until_regex(),
             read_until_close()
        """
        self._read_bytes = None
        self._read_delimiter = None
        self._read_regex = None
        self._read_until_close = False

        self._read_callback = None
        self._streaming_callback = None

        data = self.consume( consume_bytes )
        run_callback( self.server, callback, data )

    def handle_events(self, fd, events):
        """IOLoop handler."""

        if not self.socket:
            self.server.pa.logwarn( "Got events for closed stream %d" % fd )
            return

        try:
            if events & self.ioloop.READ :
                self.handle_read()
            if not self.socket : return

            if events & self.ioloop.WRITE :
                self.handle_write()
            if not self.socket: return

            if events & self.ioloop.ERROR:
                # We may have queued up a user callback in handle_read or
                # handle_write, so don't close the HTTPIOStream until those
                # callbacks have had a chance to run.
                self.ioloop.add_callback( self.close )
                return

            state = self.ioloop.ERROR
            if self.reading() :
                state |= self.ioloop.READ
            if self.writing() :
                state |= self.ioloop.WRITE
            if state == self.ioloop.ERROR :
                state |= self.ioloop.READ

            if state != self._state:
                if self._state is not None :
                    err = "shouldn't happen: handle_events without self._state"
                    raise Exception( err )
                self._state = state
                self.ioloop.update_handler( self.socket.fileno(), self._state )
        except Exception :
            self.server.pa.logerror( "Uncaught exception, closing connection." )
            self.close()
            raise

    def handle_read( self ):
        try:
            try:
                # Pretend to have a pending callback so that an EOF in
                # read_to_buffer() doesn't trigger an immediate close
                # callback.  At the end of this method we'll either
                # estabilsh a real pending callback via # read_from_buffer or
                # run the close callback
                
                # We need two try statements here so that
                # pending_callbacks is decremented before the `except`
                # clause below (which calls `close` and does need to
                # trigger the callback)
                self._pending_callbacks += 1
                while True:
                    # Read from the socket until we get EWOULDBLOCK or equivalent.
                    # SSL sockets do some internal buffering, and if the data is
                    # sitting in the SSL object's buffer select() and friends
                    # can't see it; the only way to find out if it's there is to
                    # try to read it.
                    if self.read_to_buffer() == 0:
                        break
            finally:
                self._pending_callbacks -= 1
        except Exception:
            self.server.pa.logwarn( "error on read" )
            self.close()
            return

        if self.read_from_buffer() :
            return
        else:
            self.maybe_run_close_callback()

    def read_from_socket( self ):
        """Attempts to read from the socket.
        Returns the data read or None if there is nothing to read.
        """
        try:
            chunk = self.socket.recv( self.read_chunk_size )
        except socket.error as e:
            if e.args[0] in (errno.EWOULDBLOCK, errno.EAGAIN):
                return None
            else:
                raise
        if not chunk : # May be the remote end closed
            self.close()
            return None
        return chunk

    def read_to_buffer(self):
        """Reads from the socket and appends the result to the read buffer.

        Returns the number of bytes read.  Returns 0 if there is nothing
        to read (i.e. the read returns EWOULDBLOCK or equivalent).  On
        error closes the socket and raises an exception.
        """
        try:
            chunk = self.read_from_socket()
        except socket.error as e:
            # ssl.SSLError is a subclass of socket.error
            err = "Read error on %d: %s" % (self.socket.fileno(), e)
            self.server.pa.logwarn( err )
            self.close()
            raise

        if chunk is None: return 0

        self._read_buffer.append( chunk )
        self._read_buffer_size += len(chunk)
        if self._read_buffer_size >= self.max_buffer_size :
            err = "Reached maximum read buffer size"
            self.close()
            self.server.pa.logerror( err )
            raise IOError( err )

        return len(chunk)

    def read_from_buffer(self):
        """Attempts to complete the currently-pending read from the buffer.

        Returns True if the read was completed and the callback registered via
        on of the API is issued and returned.
        """

        # Do streaming callback, in case of read_bytes() API, for chunked read.
        if self._streaming_callback is not None and self._read_buffer_size :
            bytes_to_consume = self._read_buffer_size
            if self._read_bytes is not None :
                bytes_to_consume = min(self._read_bytes, bytes_to_consume)
                self._read_bytes -= bytes_to_consume
            data = self.consume( bytes_to_consume )
            run_callback( self.server, self._streaming_callback, data )

        # For read_bytes() API
        if self._read_bytes != None and self._read_buffer_size >= self._read_bytes:
            self.docallback( self._read_bytes, self._read_callback )
            return True

        # For read_until() API
        elif self._read_delimiter is not None and self._read_buffer:
            # Multi-byte delimiters (e.g. '\r\n') may straddle two
            # chunks in the read buffer, so we can't easily find them
            # without collapsing the buffer.  However, since protocols
            # using delimited reads (as opposed to reads of a known
            # length) tend to be "line" oriented, the delimiter is likely
            # to be in the first few chunks.  Merge the buffer gradually
            # since large merges are relatively expensive and get undone in
            # consume().
            while True:
                loc = self._read_buffer[0].find( self._read_delimiter )
                if loc != -1 :  # Do callback
                    l = loc + len(self._read_delimiter)
                    self.docallback( l, self._read_callback )
                    return True

                if len(self._read_buffer) == 1: # Let us wait for more data.
                    break

                # Join with next chunk and try to find a delimiter.
                self.double_prefix( self._read_buffer )

        # For read_until_regex() API
        elif self._read_regex is not None and self._read_buffer :
            while True:
                m = self._read_regex.search( self._read_buffer[0] )
                if m is not None:
                    self.docallback( m.end(), self._read_callback )
                    return True

                if len(self._read_buffer) == 1:
                    break

                self.double_prefix(self._read_buffer)

        return False

    def set_read_callback(self, callback):
        assert not self._read_callback, "Already reading"
        self._read_callback = callback

    def tryread(self):
        """Attempt to complete the current read operation from buffered data.

        If the read can be completed without blocking, schedules the
        read callback on the next IOLoop iteration; otherwise starts
        listening for reads on the socket.
        """
        # See if we've already got the data from a previous read
        if self.read_from_buffer() : return

        # If the socket is not closed, then try reading from the socket.
        self.check_closed()
        while True :
            if self.read_to_buffer() == 0 : break
            self.check_closed()

        # And see if we've already got the data from this read
        if self.read_from_buffer(): return

        self.add_io_state( self.ioloop.READ )

    def handle_write(self):
        while self._write_buffer:
            try:
                if not self._write_buffer_frozen :
                    # On windows, socket.send blows up if given a
                    # write buffer that's too large, instead of just
                    # returning the number of bytes it was able to
                    # process.  Therefore we must not call socket.send
                    # with more than 128KB at a time.
                    self.merge_prefix(self._write_buffer, 128 * 1024)
                num_bytes = self.socket.send(self._write_buffer[0])
                if num_bytes == 0:
                    # With OpenSSL, if we couldn't write the entire buffer,
                    # the very same string object must be used on the
                    # next call to send.  Therefore we suppress
                    # merging the write buffer after an incomplete send.
                    # A cleaner solution would be to set
                    # SSL_MODE_ACCEPT_MOVING_WRITE_BUFFER, but this is
                    # not yet accessible from python
                    # (http://bugs.python.org/issue8240)
                    self._write_buffer_frozen = True
                    break
                self._write_buffer_frozen = False
                self.merge_prefix(self._write_buffer, num_bytes)
                self._write_buffer.popleft()
            except socket.error as e:
                if e.args[0] in (errno.EWOULDBLOCK, errno.EAGAIN):
                    self._write_buffer_frozen = True
                    break
                else:
                    err = "Write error on %d: %s" % (self.socket.fileno(), e)
                    self.server.pa.logwarn( err )
                    self.close()
                    return

        if not self._write_buffer and self._write_callback :
            callback = self._write_callback
            self._write_callback = None
            run_callback( self.server, callback )

    def consume( self, loc ):
        if loc == 0:
            return b""
        self.merge_prefix( self._read_buffer, loc )
        self._read_buffer_size -= loc
        return self._read_buffer.popleft()

    def check_closed(self):
        if not self.socket: raise IOError("Stream is closed")

    def maybe_add_error_listener( self ):
        if self._state is None and self._pending_callbacks == 0:
            if self.socket is None:
                self.maybe_run_close_callback()
            else:
                self.add_io_state( self.ioloop.READ )

    def add_io_state(self, state):
        """Adds `state` (IOLoop.{READ,WRITE} flags) to our event handler.

        Implementation notes: Reads and writes have a fast path and a
        slow path.  The fast path reads synchronously from socket
        buffers, while the slow path uses `add_io_state()` to schedule
        an IOLoop callback.  Note that in both cases, the callback is
        run asynchronously with `_run_callback`.

        To detect closed connections, we must have called
        `add_io_state()` at some point, but we want to delay this as
        much as possible so we don't have to set an `IOLoop.ERROR`
        listener that will be overwritten by the next slow-path
        operation.  As long as there are callbacks scheduled for
        fast-path ops, those callbacks may do more reads.
        If a sequence of fast-path ops do not end in a slow-path op,
        (e.g. for an @asynchronous long-poll request), we must add
        the error handler.  This is done in `_run_callback` and `write`
        (since the write callback is optional so we can have a
        fast-path write with no `_run_callback`)
        """
        # Check for closed connection.
        if self.socket is None : return

        if self._state is None :
            self._state = self.ioloop.ERROR | state
            self.ioloop.add_handler(
                    self.socket.fileno(), self.handle_events, self._state )

        elif not self._state & state :
            self._state = self._state | state
            self.ioloop.update_handler( self.socket.fileno(), self._state )

    def double_prefix( self, deque ):
        """Grow by doubling, but don't split the second chunk just because the
        first one is small.
        """
        new_len = max( len(deque[0]) * 2, (len(deque[0]) + len(deque[1])) )
        self.merge_prefix( deque, new_len )

    def merge_prefix( self, deque, size ):
        """Replace the first entries in a deque of strings with a single
        string of up to size bytes.

        >>> d = collections.deque(['abc', 'de', 'fghi', 'j'])
        >>> merge_prefix(d, 5); print d
        deque(['abcde', 'fghi', 'j'])

        Strings will be split as necessary to reach the desired size.
        >>> merge_prefix(d, 7); print d
        deque(['abcdefg', 'hi', 'j'])

        >>> merge_prefix(d, 3); print d
        deque(['abc', 'defg', 'hi', 'j'])

        >>> merge_prefix(d, 100); print d
        deque(['abcdefghij'])
        """
        if len(deque) == 1 and len(deque[0]) <= size:
            return
        prefix = []
        remaining = size
        while deque and remaining > 0:
            chunk = deque.popleft()
            if len(chunk) > remaining:
                deque.appendleft(chunk[remaining:])
                chunk = chunk[:remaining]
            prefix.append(chunk)
            remaining -= len(chunk)
        # This data structure normally just contains byte strings, but
        # the unittest gets messy if it doesn't use the default str() type,
        # so do the merge based on the type of data that's actually present.
        if prefix:
            deque.appendleft(type(prefix[0])().join(prefix))
        if not deque:
            deque.appendleft(b"")


class SSLIOStream( IOStream ):
    """A utility class to write to and read from a non-blocking SSL socket.

    If a dictionary is provided as keyword argument ssl-options,
    it will be used as additional keyword arguments to ssl.wrap_socket.
    """

    def __init__( self, socket, address, ioloop, server )
        self.ssloptions = h.settingsfor( 'ssl.', server )
        super().__init__( socket, address, ioloop, server )
        self._ssl_accepting = True
        self._handshake_reading = False
        self._handshake_writing = False

    def reading(self):
        return self._handshake_reading or super().reading(self)

    def writing(self):
        return self._handshake_writing or super().writing(self)

    def _do_ssl_handshake(self):
        # Based on code from test_ssl.py in the python stdlib
        try:
            self._handshake_reading = False
            self._handshake_writing = False
            self.socket.do_handshake()
        except ssl.SSLError as err:
            if err.args[0] == ssl.SSL_ERROR_WANT_READ:
                self._handshake_reading = True
                return
            elif err.args[0] == ssl.SSL_ERROR_WANT_WRITE:
                self._handshake_writing = True
                return
            elif err.args[0] in (ssl.SSL_ERROR_EOF,
                                 ssl.SSL_ERROR_ZERO_RETURN):
                return self.close()
            elif err.args[0] == ssl.SSL_ERROR_SSL:
                #log.warning( "SSL Error on %d: %s", self.socket.fileno(), err )
                return self.close()
            raise
        except socket.error as err:
            if err.args[0] == errno.ECONNABORTED:
                return self.close()

    def handle_read(self):
        if self._ssl_accepting:
            self._do_ssl_handshake()
            return
        super().handle_read()

    def handle_write(self):
        if self._ssl_accepting:
            self._do_ssl_handshake()
            return
        super().handle_write()

    def read_from_socket(self):
        if self._ssl_accepting:
            # If the handshake hasn't finished yet, there can't be anything
            # to read (attempting to read may or may not raise an exception
            # depending on the SSL version)
            return None
        try:
            # SSLSocket objects have both a read() and recv() method,
            # while regular sockets only have recv().
            # The recv() method blocks (at least in python 2.6) if it is
            # called when there is nothing to read, so we have to use
            # read() instead.
            chunk = self.socket.read( self.read_chunk_size )
        except ssl.SSLError as e:
            # SSLError is a subclass of socket.error, so this except
            # block must come first.
            if e.args[0] == ssl.SSL_ERROR_WANT_READ:
                return None
            else:
                raise
        except socket.error as e:
            if e.args[0] in (errno.EWOULDBLOCK, errno.EAGAIN):
                return None
            else:
                raise
        if not chunk:
            self.close()
            return None
        return chunk


def add_accept_handler( server, sock, callback, ioloop ):
    """Adds an ``IOLoop`` event handler to accept new connections on 
    ``sock``.

    When a connection is accepted, ``callback(connection, address)`` will
    be run (``connection`` is a socket object, and ``address`` is the
    address of the other end of the connection).  Note that this signature
    is different from the ``callback(fd, events)`` signature used for
    ``IOLoop`` handlers.
    """
    def accept_handler( fd, events ):
        while True:
            try:
                connection, address = sock.accept()
            except socket.error as e:
                if e.args[0] in (errno.EWOULDBLOCK, errno.EAGAIN):
                    return
                raise
            server.pa.loginfo( "Accepting new connection from %s", address )
            callback( connection, address )
    ioloop.add_handler( sock.fileno(), accept_handler, IOLoop.READ )


