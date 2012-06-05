# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

import time, socket, fcntl, logging

from   pluggdapps            import __version__
from   pluggdapps.plugin     import Plugin, implements
from   pluggdapps.interfaces import IServer
from   pluggdapps.config     import ConfigDict
                    
log = logging.getLogger( __name__ )

_default_settings = ConfigDict()
_default_settings.__doc__ = "Pluggdapps native HTTP Server configuration"

_default_settings['host']           = {
    'default' : '127.0.0.1',
    'types'   : (str,),
    'help'    : "Host IP address to listen for http request."
}
_default_settings['port']           = {
    'default' : 5000,
    'types'   : (int,),
    'help'    : "Host port address to listen for http request."
}
_default_settings['minprocess']     = {
    'default' : multiprocessing.cpu_count() * 2,
    'types'   : (int,),
    'help'    : "Minimum number of worker process to handle incoming "
                "request. Default is (multiprocessing.cpu_count() * 2)."
}
_default_settings['maxprocess']     = {
    'default' : multiprocessing.cpu_count() * 4,
    'types'   : (int,),
    'help'    : "The maximum number of worker process to handle incoming  "
                "request. Default is (multiprocessing.cpu_count() * 4)."
}
_default_settings['maxtaskperchild']     = {
    'default' : 1000
    'types'   : (int,),
    'help'    : "Number of tasks a worker process can complete before it will "
                "exit and be replaced with a fresh worker process, to enable "
                "unused resources to be freed. If 0, worker processes will "
                "live as long as the pool. This parameter is directly passed "
                "on to multiprocessing.Pool API."
}
_default_settings['server_name']    = {
    'default' : socket.gethostname(),
    'types'   : (str,),
    'help'    : "The name of the server; defaults to socket.gethostname()."
}
_default_settings['protocol']       = {
    'default' : "HTTP/1.1",
    'types'   : (str,),
    'help'    : "The version string to write in the Status-Line of all HTTP "
                "responses. For example, `HTTP/1.1` is the default. "
                "Where the server will permit HTTP persistent connections; "
                "The server should include an accurate Content-Length header "
                "(using send_header()) in all of its responses to clients. "
}
_default_settings['request_queue_size'] = {
    'default' : 5,
    'types'   : (int,),
    'help'    : "The 'backlog' arg to socket.listen(); max queued connections."
}
_default_settings['shutdown_timeout']   = {
    'default' : 5,
    'types'   : (int,),
    'help'    : "The total time, in seconds, to wait for worker threads to "
                "cleanly exit."
}
_default_settings['timeout']            = {
    'default' : 10,
    'types'   : (int,),
    'help'    : "The timeout in seconds for accepted connections."
}
_default_settings['max_request_header_size']    = {
    'default' : 0,
    'types'   : (int,),
    'help'    : "The maximum size, in bytes, for request headers, 0 means no "
                "limit."
}
_default_settings['max_request_body_size']      = {
    'default' : 0,
    'types'   : (int,),
    'help'    : "The maximum size, in bytes, for request bodies, 0 means no"
                "limit."
}
_default_settings['nodelay']                    = {
    'default' : True,
    'types'   : (bool,)
    'help'    : "If True (the default since 3.1), sets the TCP_NODELAY "
                "socket option."
}


class HTTPServer( Plugin ):

    implements( IServer )

    _interrupt  = False

    _version    = "pluggdapps /" + __version__
    """Version string for the HTTPServer."""

    _software   = "'pluggdapps / %s Server'" % __version__
    "SERVER_SOFTWARE entry in the WSGI environ."

    _tickloop   = False
    "Internal flag which marks whether the socket is accepting connections."

    _start_time = None
    "Internal stats on when the server object started accepting connections."

    # TODO : To be moved as plugins.
    connection_class = HTTPConnection
    """The class to use for handling HTTP connections."""

    gateway = None
    "Gateway instance for adapting HTTP-Server with framework specific
    interface for passing requests into applications."

    ssl_adapter = None
    """An instance of SSLAdapter (or a subclass).
    You must have the corresponding SSL driver library installed."""

    def __init__( self, gateway ):
        self.bind_addr = (self['host'], self['port'])
        self.procpool = multiprocessing.Pool( 
            self['minprocess'], None, [], self['maxtaskperchild'] )
        self.sockthread = threading.Thread()

    def _addrinfo( self, bind_addr ):
        # Support both AF_INET and AF_INET6 family of address
        host, port = self.bind_addr
        try:
            info = socket.getaddrinfo( 
                        host, port, socket.AF_UNSPEC, 
                        socket.SOCK_STREAM, 0, socket.AI_PASSIVE 
                   )
        except socket.gaierror:
            if ':' in self.host :
                af, sa = socket.AF_INET6, (host, port, 0, 0)
            else:
                af, sa = socket.AF_INET,  (host, port, 0, 0)
            info = [( af, socket.SOCK_STREAM, 0, "", sa )]
        return info

    def _bind( self, family, socktype, proto=0 ):
        sock = socket.socket( family, socktype, proto )
        # Mark the given socket fd as non-inheritable (POSIX).
        fd = sock.fileno()
        old_flags = fcntl.fcntl( fd, fcntl.F_GETFD )
        fcntl.fcntl( fd, fcntl.F_SETFD, old_flags | fcntl.FD_CLOEXEC )

        sock.setsockopt( socket.SOL_SOCKET, socket.SO_REUSEADDR, 1 )
        if self['nodelay'] and not isinstance( self.bind_addr, str ) :
            sock.setsockopt( socket.IPPROTO_TCP, socket.TCP_NODELAY, 1 )

        sock.bind( self.bind_addr )
        return sock

    def start( self ):
        info = self._addrinfo( self.bind_addr )
        msg = "No socket could be created"
        self.socket = None
        for af, socktype, proto, caname, sa in info:
            try:
                self.socket = self._bind( af, socktype, proto )
                break
            except socket.error:
                self.socket.close() if self.socket else None
                self.socket = None
                raise socket.error( msg ).

        self.socket.listen( self['request_queue_size'] )

        self._tickloop = True
        while self._tickloop :
            self._start_time = time.time()
            try : 
                self.tick()
            except (KeyboardInterrupt, SystemExit) :
                raise
            except :
                # TODO : Log error message

    # ISettings interface methods.
    @classmethod
    def default_settings( cls ):
        return _default_settings

    @classmethod
    def normalize_settings( cls, settings ):
        return settings

    @classmethod
    def web_admin( cls, settings ):
        return settings


class RequestHandler( BaseHTTPServer.BaseHTTPRequestHandler ):
    """Entry point for all HTTP request.

    Notes from python manual :

    * HTTP methods TRACE and CONNECT are not relevant right now.

    * Base instance variables,
        client_address, server, command, path, request_version,
        headers, rfile, wfile

    * Overridden instance variables,
        --None--

    * Base class variables,
        sys_version, error_message_format, error_content_type, 

    * Overridden class variables,
        server_version, protocol_version,
    """

    server_version = 'pluggdapps /' + __version__
    """Specifies the server software version."""

    protocol_version = 'HTTP/1.1'


    def do_HEAD( self ) :
        pass

    def do_GET( self ) :
        pass

    def do_PUT( self ) :
        pass

    def do_POST( self ) :
        pass

    def do_DELETE( self ) :
        pass
