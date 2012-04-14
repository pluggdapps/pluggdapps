# Derived work from Facebook's tornado server.

"""TCPServer using non-blocking evented polling loop."""

from __future__ import absolute_import, division, with_statement

import os, socket, errno, logging, stat
import ssl  # Python 2.6+

from pluggdapps.interfaces          import ISettings
from pluggdapps.evserver            import process
from pluggdapps.evserver.httpioloop import HTTPIOLoop
from pluggdapps.evserver.iostream   import HTTPIOStream, HTTPSSLIOStream
from pluggdapps.util                import set_close_exec, settingsfor


class TCPServer( object ):
    """A non-blocking, single-threaded "Mixin class" implementing TCP server.

    To use `TCPServer`, define a `Plugin` subclass which overrides the 
    `handle_stream` method.

    `TCPServer` can serve SSL traffic with Python 2.6+ and OpenSSL.
    To make this server serve SSL traffic, configure the sub-class plugin with
    `ssloptions.*` settings. which is required for the `ssl.wrap_socket` method,
    including "certfile" and "keyfile" 
    """

    def __init__( self ):
        self._sockets = {}  # fd -> socket object
        self._pending_sockets = []
        self._started = False
        self.ioloop = None

    def listen( self, port, address="" ):
        """Starts accepting connections on the given port.

        This method may be called more than once to listen on multiple ports.
        `listen` takes effect immediately; it is not necessary to call
        `TCPServer.start` afterwards.  It is, however, necessary to start
        the `HTTPIOLoop`.
        """
        sockets = bind_sockets(port, address=address)
        self.add_sockets(sockets)

    def add_sockets( self, sockets ):
        """Makes this server start accepting connections on the given sockets.

        The ``sockets`` parameter is a list of socket objects such as
        those returned by `bind_sockets`.
        `add_sockets` is typically used in combination with that
        method and `process.fork_processes` to provide greater
        control over the initialization of a multi-process server.
        """
        from pluggdapps import query_plugin, ROOTAPP
        if self.ioloop == None :
            self.ioloop = query_plugin( ROOTAPP, ISettings, 'httpioloop' )
        for sock in sockets:
            self._sockets[sock.fileno()] = sock
            add_accept_handler( sock, self._handle_connection, self.ioloop )

    def add_socket( self, socket ):
        """Singular version of `add_sockets`.  Takes a single socket object."""
        self.add_sockets([socket])

    def bind( self, port, address=None, family=socket.AF_UNSPEC, backlog=128 ):
        """Binds this server to the given port on the given address.

        To start the server, call `start`. If you want to run this server
        in a single process, you can call `listen` as a shortcut to the
        sequence of `bind` and `start` calls.

        Address may be either an IP address or hostname.  If it's a hostname,
        the server will listen on all IP addresses associated with the
        name.  Address may be an empty string or None to listen on all
        available interfaces.  Family may be set to either ``socket.AF_INET``
        or ``socket.AF_INET6`` to restrict to ipv4 or ipv6 addresses, otherwise
        both will be used if available.

        The ``backlog`` argument has the same meaning as for
        `socket.listen`.

        This method may be called multiple times prior to `start` to listen
        on multiple ports or interfaces.
        """
        sockets = bind_sockets(port, address=address, family=family,
                               backlog=backlog)
        if self._started:
            self.add_sockets(sockets)
        else:
            self._pending_sockets.extend(sockets)

    def start( self ):
        """Starts this server in the HTTPIOLoop.

        By default, we run the server in this process and do not fork any
        additional child process.

        If `multiprocess` settings not configured or configured as <= 0, we 
        detect the number of cores available on this machine and fork that 
        number of child processes. If `multiprocess` settings configured as
        > 0, we fork that specific number of sub-processes.

        Since we use processes and not threads, there is no shared memory
        between any server code.

        Note that multiple processes are not compatible with the autoreload
        module (or the ``debug=True`` option to `Platform`). When using 
        multiple processes, no HTTPIOLoop can be created or referenced until
        after the call to ``TCPServer.start(n)``.
        """
        assert not self._started
        self._started = True
        multiprocess = self['multiprocess']
        port, host = self['port'], self['host']

        if multiprocess <= 0:   # Single process
            self.listen( port, address )
        else :                  # multi-process
            sockets = bind_sockets( port, address )
            process.fork_processes( multiprocess )
            self.add_sockets( sockets )

        self.ioloop.start() # Block !

    def stop(self):
        """Stops listening for new connections.

        Requests currently in progress may still continue after the
        server is stopped.
        """
        for fd, sock in self._sockets.iteritems():
            self.ioloop.remove_handler(fd)
            sock.close()

    def handle_stream(self, stream, address):
        """Override to handle a new `IOStream` from an incoming connection."""
        raise NotImplementedError()

    def _handle_connection( self, conn, address ):
        from pluggdapps import query_plugin, ROOTAPP

        ssloptions = settingsfor( 'ssloptions.', self )
        if ssloptions :
            assert ssl, "Python 2.6+ and OpenSSL required for SSL"
            try:
                conn = ssl.wrap_socket( conn,
                                        server_side=True,
                                        do_handshake_on_connect=False,
                                        **ssloptions )
            except ssl.SSLError, err:
                if err.args[0] == ssl.SSL_ERROR_EOF:
                    return conn.close()
                else:
                    raise
            except socket.error, err:
                if err.args[0] == errno.ECONNABORTED:
                    return conn.close()
                else:
                    raise
        try:
            if ssloptions is not None:
                stream = query_plugin( ROOTAPP,
                            ISettings, 'httpssliostream', conn, self.ioloop,
                            ssloptions=ssloptions )
            else:
                stream = query_plugin( ROOTAPP,
                            ISettings, 'httpiostream', conn, self.ioloop )
            self.handle_stream( stream, address )
        except Exception:
            logging.error("Error in connection callback", exc_info=True)


def bind_sockets(port, address=None, family=socket.AF_UNSPEC, backlog=128):
    """Creates listening sockets bound to the given port and address.

    Returns a list of socket objects (multiple sockets are returned if
    the given address maps to multiple IP addresses, which is most common
    for mixed IPv4 and IPv6 use).

    Address may be either an IP address or hostname.  If it's a hostname,
    the server will listen on all IP addresses associated with the
    name.  Address may be an empty string or None to listen on all
    available interfaces.  Family may be set to either socket.AF_INET
    or socket.AF_INET6 to restrict to ipv4 or ipv6 addresses, otherwise
    both will be used if available.

    The ``backlog`` argument has the same meaning as for
    ``socket.listen()``.
    """
    sockets = []
    if address == "":
        address = None
    flags = socket.AI_PASSIVE
    if hasattr(socket, "AI_ADDRCONFIG"):
        # AI_ADDRCONFIG ensures that we only try to bind on ipv6
        # if the system is configured for it, but the flag doesn't
        # exist on some platforms (specifically WinXP, although
        # newer versions of windows have it)
        flags |= socket.AI_ADDRCONFIG
    for res in set(socket.getaddrinfo(address, port, family, socket.SOCK_STREAM,
                                  0, flags)):
        af, socktype, proto, canonname, sockaddr = res
        sock = socket.socket(af, socktype, proto)
        set_close_exec(sock.fileno())
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
                sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
        sock.setblocking(0)
        sock.bind(sockaddr)
        sock.listen(backlog)
        sockets.append(sock)
    return sockets

def add_accept_handler(sock, callback, ioloop):
    """Adds an ``HTTPIOLoop`` event handler to accept new connections on 
    ``sock``.

    When a connection is accepted, ``callback(connection, address)`` will
    be run (``connection`` is a socket object, and ``address`` is the
    address of the other end of the connection).  Note that this signature
    is different from the ``callback(fd, events)`` signature used for
    ``HTTPIOLoop`` handlers.
    """
    def accept_handler(fd, events):
        while True:
            try:
                connection, address = sock.accept()
            except socket.error, e:
                if e.args[0] in (errno.EWOULDBLOCK, errno.EAGAIN):
                    return
                raise
            callback(connection, address)
    ioloop.add_handler( sock.fileno(), accept_handler, HTTPIOLoop.READ )
