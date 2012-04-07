# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

import time, socket

from   pluggdapps   import __version__
from   plugincore   import Plugin, implements
from   interfaces   import IHTTPServer
from   utils        import ConfigDict
                    
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

    implements( IHTTPServer )

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
        Plugin.__init__( self )

        self.bind_addr = (self['host'], self['port'])
        self.gateway = gateway
        self.pool = multiprocessing.Pool( 
            self['minprocess'], None, [], self['maxtaskperchild'] )
        self._clear_stats()

    def _clear_stats( self ):
        self._start_time = None
        self._run_time = 0
        self.stats = {
            'Enabled'     : False,
            'Bind Address': lambda s: repr( self.bind_addr ),
            'Run time'    : lambda s: (not s['Enabled']) and -1 or self.runtime(),
            'Accepts': 0,
            'Accepts/sec': lambda s: s['Accepts'] / self.runtime(),
            'Queue': lambda s: getattr(self.requests, "qsize", None),
            'Threads': lambda s: len(getattr(self.requests, "_threads", [])),
            'Threads Idle': lambda s: getattr(self.requests, "idle", None),
            'Socket Errors': 0,
            'Requests': lambda s: (not s['Enabled']) and -1 or sum([w['Requests'](w) for w
                                       in s['Worker Threads'].values()], 0),
            'Bytes Read': lambda s: (not s['Enabled']) and -1 or sum([w['Bytes Read'](w) for w
                                         in s['Worker Threads'].values()], 0),
            'Bytes Written': lambda s: (not s['Enabled']) and -1 or sum([w['Bytes Written'](w) for w
                                            in s['Worker Threads'].values()], 0),
            'Work Time': lambda s: (not s['Enabled']) and -1 or sum([w['Work Time'](w) for w
                                         in s['Worker Threads'].values()], 0),
            'Read Throughput': lambda s: (not s['Enabled']) and -1 or sum(
                [w['Bytes Read'](w) / (w['Work Time'](w) or 1e-6)
                 for w in s['Worker Threads'].values()], 0),
            'Write Throughput': lambda s: (not s['Enabled']) and -1 or sum(
                [w['Bytes Written'](w) / (w['Work Time'](w) or 1e-6)
                 for w in s['Worker Threads'].values()], 0),
            'Worker Threads': {},
            }
        logging.statistics["CherryPy HTTPServer %d" % id(self)] = self.stats

    def start( self ):
        self._interrupt = None

        # Support both AF_INET and AF_INET6 family of address
        host, port = self.bind_addr
        try:
            info = socket.getaddrinfo( 
                        host, port, socket.AF_UNSPEC, 
                        socket.SOCK_STREAM, 0, socket.AI_PASSIVE 
                   )
        except socket.gaierror:
            if ':' in self.bind_addr[0]:
                info = [( socket.AF_INET6, socket.SOCK_STREAM,
                           0, "", self.bind_addr + (0, 0) )]
            else:
                info = [( socket.AF_INET, socket.SOCK_STREAM,
                          0, "", self.bind_addr )]

        msg = "No socket could be created"
        self.socket = None
        for af, socktype, proto, caname, sa in info:
            try:
                self.bind( af, socktype, proto )
                break
            except socket.error:
                self.socket.close() if self.socket else None
                self.socket = None

        if not self.socket:
            raise socket.error( msg ).

        # Timeout so KeyboardInterrupt can be caught on Win32
        self.socket.settimeout(1)
        # Listen
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

            if self.interrupt:
                # Wait for self.stop() to complete. See _set_interrupt.
                while self.interrupt is True : time.sleep(0.1)
                if self.interrupt : raise self.interrupt

    # ISettings interface methods.
    def normalize_settings( self, settings ):
        return settings

    def default_settings():
        return _default_settings.items()

    def web_admin( self, settings ):
        """Web admin interface is not allowed for this plugin."""
        pass


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


