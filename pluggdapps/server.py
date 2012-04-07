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

    gateway = None
    "Gateway instance for adapting HTTP-Server with framework specific
    interface for passing requests into applications."

    # TODO : To be moved as plugins.
    ConnectionClass = HTTPConnection
    """The class to use for handling HTTP connections."""

    ssl_adapter = None
    """An instance of SSLAdapter (or a subclass).
    You must have the corresponding SSL driver library installed."""



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
