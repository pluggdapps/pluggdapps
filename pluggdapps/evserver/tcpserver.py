# -*- coding: utf-8 -*-

# Derived work from Facebook's tornado server.

"""TCPServer using non-blocking evented polling loop."""

import os, socket, errno, stat
import ssl  # Python 2.6+

from   pluggdapps.const import ROOTAPP
from   pluggdapps.config import settingsfor
from   pluggdapps.evserver import process
from   pluggdapps.evserver.httpioloop import HTTPIOLoop
from   pluggdapps.evserver.httpiostream import HTTPIOStream, HTTPSSLIOStream
import pluggdapps.utils as h


class TCPServer( object ):
    """A non-blocking, single-threaded "Mixin class" implementing TCP server.

    To use `TCPServer`, define a `Plugin` subclass which overrides the 
    `handle_stream` method.

    `TCPServer` can serve SSL traffic with Python 2.6+ and OpenSSL.
    To make this server serve SSL traffic, configure the sub-class plugin with
    `ssloptions.*` settings. which is required for the `ssl.wrap_socket` 
    method, including "certfile" and "keyfile" 
    """

    def __init__( self, sett ):
        # configuration settings
        self.sett = sett
        self._sockets = {}  # fd -> socket object
        self._pending_sockets = []
        self._started = False
        self.ioloop = None

    def listen( self ):
        """Starts accepting connections on the given port.

        This method may be called more than once to listen on multiple ports.
        `listen` takes effect immediately; it is not necessary to call
        `TCPServer.start` afterwards.  It is, however, necessary to start
        the `HTTPIOLoop`.
        """
        sett = self.sett
        sockets = bind_sockets( 
                        sett['port'], sett['host'], None, sett['backlog'] )
        self.add_sockets(sockets)

    def add_sockets( self, sockets ):
        """Make the server start accepting connections using event loop on the
        given sockets.

        The ``sockets`` parameter is a list of socket objects such as
        those returned by `bind_sockets`.
        """
        self.ioloop = HTTPIOLoop( self.sett )
        for sock in sockets:
            self._sockets[ sock.fileno()] = sock
            add_accept_handler( sock, self._handle_connection, self.ioloop )

    def add_socket( self, socket ):
        """Singular version of `add_sockets`.  Takes a single socket object."""
        self.add_sockets([socket])

    def bind( self ):
        """Binds this server to the addres, port and family configured in
        server settings.

        This method may be called multiple times prior to `start` to listen
        on multiple ports or interfaces."""
        family = socket.AF_UNSPEC 
        sett = self.sett
        sockets = bind_sockets( 
                    sett['port'], sett['host'], family, sett['backlog'] )
        if self._started :
            self.add_sockets( sockets )
        else:
            self._pending_sockets.extend( sockets )

    def start( self ):
        """Starts this server using HTTPIOloop.

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
        sett = self.sett

        if sett['multiprocess'] <= 0:  # Single process
            #log.info("Starting server in single process mode ...")
            self.listen()
        else :                      # multi-process
            #log.info("Starting server in multi process mode ...")
            sockets = bind_sockets( 
                        sett['port'], sett['host'], None, sett['backlog'] )
            process.fork_processes( sett['multiprocess'], sett['max_restart'] )
            self.add_sockets( sockets )
        # TODO : Setup logging for multiple process ?

        self.ioloop.start() # Block !


    def stop(self):
        """Stops listening for new connections.

        Requests currently in progress may still continue after the
        server is stopped.
        """
        for fd, sock in self._sockets.items() :
            self.ioloop.remove_handler(fd)
            sock.close()

    def handle_stream(self, stream, address):
        """Override to handle a new `IOStream` from an incoming connection."""
        raise NotImplementedError()

    def _handle_connection( self, conn, address ):
        ssloptions = settingsfor( 'ssloptions.', self.sett )
        is_ssl = ssloptions['keyfile'] and ssloptions['certfile']
        if is_ssl :
            try:
                conn = ssl.wrap_socket( conn,
                                        server_side=True,
                                        do_handshake_on_connect=False,
                                        **ssloptions )
            except ssl.SSLError as err:
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
                stream = HTTPSSLIOStream( 
                            conn, address, self.ioloop, 
                            self.sett, ssloptions=ssloptions )
            else :
                stream = HTTPIOStream( conn, address, self.ioloop, self.sett ) 
            self.handle_stream( stream, address )
        except Exception:
            #log.error("Error in connection callback", exc_info=True)
            pass


def bind_sockets( port, address, family, backlog ):
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
    family = family or socket.AF_UNSPEC
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
        addrinfo = set(
            socket.getaddrinfo(
                address, port, family, socket.SOCK_STREAM, 0, flags))
    for res in addrinfo :
        #log.info("Binding socket for %s", res)
        af, socktype, proto, canonname, sockaddr = res
        sock = socket.socket(af, socktype, proto)
        h.set_close_exec(sock.fileno())
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
        #log.debug( "Set server socket to non-blocking mode ..." )
        sock.setblocking(0) # Set to non-blocking.
        sock.bind(sockaddr)
        #log.debug( "Server listening with a backlog of %s", backlog )
        sock.listen(backlog)
        sockets.append(sock)
    return sockets

def add_accept_handler( sock, callback, ioloop ):
    """Adds an ``HTTPIOLoop`` event handler to accept new connections on 
    ``sock``.

    When a connection is accepted, ``callback(connection, address)`` will
    be run (``connection`` is a socket object, and ``address`` is the
    address of the other end of the connection).  Note that this signature
    is different from the ``callback(fd, events)`` signature used for
    ``HTTPIOLoop`` handlers.
    """
    def accept_handler( fd, events ):
        while True:
            try:
                connection, address = sock.accept()
            except socket.error as e:
                if e.args[0] in (errno.EWOULDBLOCK, errno.EAGAIN):
                    return
                raise
            #log.info( "Accepting new connection from %s", address )
            callback( connection, address )
    ioloop.add_handler( sock.fileno(), accept_handler, HTTPIOLoop.READ )
