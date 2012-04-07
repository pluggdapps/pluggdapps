# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

import socket
from   BaseHTTPServer

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
_default_settings['minthreads']     = {
    'default' : 10,
    'types'   : (int,),
    'help'    : "Minimum number of worker threads to handle incoming "
                "request."
}
_default_settings['maxthreads']     = {
    'default' : -1,
    'types'   : (int,),
    'help'    : "The maximum number of worker threads to create "
                "(default -1 = no limit)."
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

class HTTPServer( object ):

    _interrupt  = False

    _version    = "pluggdapps /" + __version__
    """Version string for the HTTPServer."""

    _software   = "'pluggdapps / %s Server'" % __version__
    "SERVER_SOFTWARE entry in the WSGI environ."

    _ready = False
    "Internal flag which marks whether the socket is accepting connections."

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
        self.gateway = gateway

        self.requests = ThreadPool( self, minthreads, maxthreads )

        if not server_name:
            server_name = socket.gethostname()
        self.server_name = server_name
        self.clear_stats()


_SHUTDOWNREQUEST = None
class WorkerThread( threading.Thread ):
    """Thread which continuously polls a Queue for Connection objects.

    Due to the timing issues of polling a Queue, a WorkerThread does not
    check its own 'ready' flag after it has started. To stop the thread,
    it is necessary to stick a _SHUTDOWNREQUEST object onto the Queue
    (one for each running WorkerThread).
    """

    conn = None
    """The current connection pulled off the Queue, or None."""

    server = None
    """The HTTP Server which spawned this thread, and which owns the
    Queue and is placing active connections into it."""

    ready = False
    """A simple flag for the calling server to know when this thread
    has begun polling the Queue."""


    def __init__(self, server):
        self.ready = False
        self.server = server

        self.requests_seen = 0
        self.bytes_read = 0
        self.bytes_written = 0
        self.start_time = None
        self.work_time = 0
        self.stats = {
            'Requests': lambda s: self.requests_seen + ((self.start_time is None) and trueyzero or self.conn.requests_seen),
            'Bytes Read': lambda s: self.bytes_read + ((self.start_time is None) and trueyzero or self.conn.rfile.bytes_read),
            'Bytes Written': lambda s: self.bytes_written + ((self.start_time is None) and trueyzero or self.conn.wfile.bytes_written),
            'Work Time': lambda s: self.work_time + ((self.start_time is None) and trueyzero or time.time() - self.start_time),
            'Read Throughput': lambda s: s['Bytes Read'](s) / (s['Work Time'](s) or 1e-6),
            'Write Throughput': lambda s: s['Bytes Written'](s) / (s['Work Time'](s) or 1e-6),
        }
        threading.Thread.__init__(self)

    def run(self):
        self.server.stats['Worker Threads'][self.getName()] = self.stats
        try:
            self.ready = True
            while True:
                conn = self.server.requests.get()
                if conn is _SHUTDOWNREQUEST:
                    return

                self.conn = conn
                if self.server.stats['Enabled']:
                    self.start_time = time.time()
                try:
                    conn.communicate()
                finally:
                    conn.close()
                    if self.server.stats['Enabled']:
                        self.requests_seen += self.conn.requests_seen
                        self.bytes_read += self.conn.rfile.bytes_read
                        self.bytes_written += self.conn.wfile.bytes_written
                        self.work_time += time.time() - self.start_time
                        self.start_time = None
                    self.conn = None
        except (KeyboardInterrupt, SystemExit):
            exc = sys.exc_info()[1]
            self.server.interrupt = exc


try    : import queue
except : import Queue as queue

class ThreadPool( object ):

    def __init__( self, server, minthreads, maxthreads ):
        self.server = server
        self.minthreads, self.maxthreads = minthreads, maxthreads
        self._threads = []
        self._queue = queue.Queue()
        self.get = self._queue.get

    def start(self):
        for i in range( self.minthreads ) :
            worker = WorkerThread(self.server)
            worker.setName( "CP Server " + worker.getName() )
            self._threads.append( worker )

        for worker in self._threads:
            worker.setName("CP Server " + worker.getName())
            worker.start()

        for worker in self._threads:
            while not worker.ready:
                time.sleep(.1)

    def _get_idle(self):
        """Number of worker threads which are idle. Read-only."""
        return len([t for t in self._threads if t.conn is None])
    idle = property(_get_idle, doc=_get_idle.__doc__)

    def put(self, obj):
        self._queue.put(obj)
        if obj is _SHUTDOWNREQUEST:
            return

    def grow(self, amount):
        """Spawn new worker threads (not above self.max)."""
        for i in range(amount):
            if self.max > 0 and len(self._threads) >= self.max:
                break
            worker = WorkerThread(self.server)
            worker.setName("CP Server " + worker.getName())
            self._threads.append(worker)
            worker.start()

    def shrink(self, amount):
        """Kill off worker threads (not below self.min)."""
        # Grow/shrink the pool if necessary.
        # Remove any dead threads from our list
        for t in self._threads:
            if not t.isAlive():
                self._threads.remove(t)
                amount -= 1

        if amount > 0:
            for i in range(min(amount, len(self._threads) - self.min)):
                # Put a number of shutdown requests on the queue equal
                # to 'amount'. Once each of those is processed by a worker,
                # that worker will terminate and be culled from our list
                # in self.put.
                self._queue.put(_SHUTDOWNREQUEST)

    def stop(self, timeout=5):
        # Must shut down threads here so the code that calls
        # this method can know when all threads are stopped.
        for worker in self._threads:
            self._queue.put(_SHUTDOWNREQUEST)

        # Don't join currentThread (when stop is called inside a request).
        current = threading.currentThread()
        if timeout and timeout >= 0:
            endtime = time.time() + timeout
        while self._threads:
            worker = self._threads.pop()
            if worker is not current and worker.isAlive():
                try:
                    if timeout is None or timeout < 0:
                        worker.join()
                    else:
                        remaining_time = endtime - time.time()
                        if remaining_time > 0:
                            worker.join(remaining_time)
                        if worker.isAlive():
                            # We exhausted the timeout.
                            # Forcibly shut down the socket.
                            c = worker.conn
                            if c and not c.rfile.closed:
                                try:
                                    c.socket.shutdown(socket.SHUT_RD)
                                except TypeError:
                                    # pyOpenSSL sockets don't take an arg
                                    c.socket.shutdown()
                            worker.join()
                except (AssertionError,
                        # Ignore repeated Ctrl-C.
                        # See http://www.cherrypy.org/ticket/691.
                        KeyboardInterrupt):
                    pass

    def _get_qsize(self):
        return self._queue.qsize()
    qsize = property(_get_qsize)




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


class NativeServer( Plugin ):
    implements( IHTTPServer )

    def serve( self, appsettings ):
        server_address = ( self['host'], self['port'] )
        server = HTTPServer( server_address, RequestHanlder )
        server.serve_forever()

    # ISettings interface methods.
    def normalize_settings( self, settings ):
        return settings

    def default_settings():
        return _default_settings.items()

    def web_admin( self, settings ):
        """Web admin interface is not allowed for this plugin."""
        pass
