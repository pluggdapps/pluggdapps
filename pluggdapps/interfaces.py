# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

import socket

from   pluggdapps.plugin import Interface, Attribute

__all__ = [ 
    'ICommand', 'IServer', 'IRequest', 'IApplication', 'IRouter',
    'IResponse'
]

class ICommand( Interface ):
    """Handle sub-commands issued from command line script. The general
    purpose is to parse the command line string arguments into `options` and
    `arguments` and then perform the sub-command in the user desired 
    fashion."""

    description = Attribute(
        "Description about this command"
    )

    def __init__( argv=[], settings={} ):
        """Parse command line arguments using argv list and return a tuple of
        (options, args).
        """

    def argparse( argv ):
        """Parse command line arguments using argv list and return a tuple of
        (options, args). Also overwrite self's `options` and `args` attributes
        initialized during instantiation.
        """

    def run( options=None, args=[] ):
        """Run the command using command line `options` and non-option 
        parameters, `args`. If either or both `options` and `args` are None 
        then previously parsed `options` and `args` using argparse() will be
        used."""


class IServer( Interface ):
    """Interface to bind, listen, accept HTTP server."""

    def __init__( platform, *args, **kwargs ):
        """
        ``platform``
            instance of :class:`Platform`
        """

    def listen( port, address="" ):
        """Starts accepting connections on the given port and address.
        This method may be called more than once to listen on multiple ports.
        `listen` takes effect immediately;
        """

    def bind( port, address=None, family=socket.AF_UNSPEC, backlog=128 ):
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

    def start( *args, **kwargs ):
        """Starts this server and returns a server object."""

    def stop():
        """Stops listening for new connections.

        Requests currently in progress may still continue after the
        server is stopped.
        """

    def handle_stream( stream, address ):
        """To handle a new connection stream."""


class IApplication( Interface ):
    """In pluggdapps, an application is a plugin, whereby, a plugin is a bunch
    of configuration parameters implementing one or more interface
    specification."""

    def boot( settings ):
        """Do necessary activities to boot this applications. Called at
        platform boot-time.

        ``settings``,
            configuration dictionary for this application. Dictionary is a
            collection of sections and its settings. Plugin section names will
            follow the following format, 'plugin:<pluginname>'. There is a
            special section by name 'DEFAULT', whose settings are global to
            all other section settings.
        """

    def start( request ):
        """Once a `request` is resolved for an application, this method is the
        entry point for the request into the resolved application. Typically 
        this method will be implemented by :class:`Application` base class 
        which automatically does url route-mapping and invokes the configured 
        request handler."""

    def router( request ):
        """Return the router plugin implementing :class:`IRouter` 
        interface."""

    def finish( request ):
        """Finish this request. Reverse of start."""

    def shutdown( settings ):
        """Shutdown this application. Reverse of boot.
        
        ``settings``,
            configuration dictionary for this application. Dictionary is a
            collection of sections and its settings. Plugin section names will
            follow the following format, 'plugin:<pluginname>'. There is a
            special section by name 'DEFAULT', whose settings are global to
            all other section settings.
        """


class IRouter( Interface ):
        """Every `IRouter` plugin must either treat a request's url as a chain
        of resource and resolve them based on the next path component or 
        the plugin must resolve the request's url by mapping rules."""

    def onboot( settings ):
        """During application boot time, every router object will be resolved,
        if available, using :method:`IApplication.router' or 
        :method:`IRouter.route` methods, which will return an instance of 
        plugin implementing this interface. And `onboot` will be called on
        those plugins.
        
        Typically url route mapping is initialized here.
        """

    def route( request ):
        """If a `request` url is treated as a chain of resource and resolved 
        based on the next path component. Return a `IRouter` plugin that will
        be used for further url resolution."""

    def match( request ):
        """If route() method should return None, then match must succeed in 
        resolving the `request` url based on mapping urls."""


class IRequest( Interface ):
    """Request object, the only parameter that will be passed to
    :class:`IRquestHandler`."""

    app = Attribute(
        "Application instance deriving from :class:`Plugin` implementing "
        ":class:`IApplication` interface."
    )
    method = Attribute(
        "HTTP request method, e.g. 'GET' or 'POST'"
    )
    host = Attribute(
        "The requested hostname, usually taken from the ``Host`` header."
    )
    uri = Attribute(
        "HTTP Request URI"
    )
    full_url = Attribute(
        "Reconstructs the full URL for this request, which is, "
        "protocol + host + uri"
    )
    path = Attribute(
        "Path portion of HTTP request URI"
    )
    query = Attribute(
        "Query portion of HTTP request URI"
    )
    arguments = Attribute(
        "GET/POST arguments are available in the arguments property, which "
        "maps arguments names to lists of values (to support multiple values "
        "for individual names). Names are of type `str`, while arguments "
        "are byte strings. Note that this is different from "
        ":method:`IRequest.get_argument`, which returns argument values as "
        "unicode strings."
    )
    version = Attribute(
        "HTTP protocol version specified in request, e.g. 'HTTP/1.1'"
    )
    headers = Attribute(
       "Dictionary-like object for HTTP headers. Acts like a "
       "case-insensitive dictionary."
    )
    body = Attribute(
       "Request body, if present, as a byte string."
    )
    remote_ip = Attribute(
       "Client's IP address as a string. If running behind a load-balancer "
       "or a proxy, the real IP address provided by a load balancer will be "
       "passed in the ``X-Real-Ip`` header."
    )
    protocol = Attribute(
        "The protocol used, either 'http' or 'https'.  If running behind a "
        "load-balancer or a proxy, the real scheme will be passed along via "
        "via an `X-Scheme` header."
    )
    files = Attribute(
        "File uploads are available in the files property, which maps file "
        "names to lists of :class:`HTTPFile`."
    )
    connection = Attribute(
        "An HTTP request is attached to a single HTTP connection, which can "
        "be accessed through the 'connection' attribute. Since connections "
        "are typically kept open in HTTP/1.1, multiple requests can be handled "
        "sequentially on a single connection."
    )
    cookies = Attribute(
        "A dictionary of Cookie.Morsel objects."
    )
    receivedat = Attribute(
        "Timestamp when request was recieved"
    )
    elapsedtime = Attribute(
        "Amount of time, in floating seconds, elapsed since the request was "
        "received. Call this method while servicing the request. To know the "
        "final elapsed time, that is after servicing the request, use "
        "``servicetime`` attribute."
    )
    servicetime = Attribute(
        "Amount of time, in floating seconds, elapsed since the request was "
        "received."
    )
    settings = Attribute(
        "A copy of application settings dictionary. Settings are organised "
        "into sections, special section `DEFAULT` provides global "
        "settings for all application sectionw. Other sections are "
        "application specific settings for modules and plugins."
    )
    appsettings = Attribute(
        "A copy of global appsettings containing settings configuration for "
        "all applications, including root-application. Read only data
        structure."
    )

    def __init__( connection, method, uri, version, headers, remote_ip ):
        """Instance of plugin implementing this interface corresponds to a
        single HTTP request. Note that instantiating this class does not
        essentially mean the entire request is received. Only when
        :method:`IRequest.handle` is called complete request is available
        and partially parsed.

        ``connection``,
            HTTP socket connection that can receive / transmit http packets.
        ``method``,
            HTTP request method parsed from start_line.
        ``uri``,
            HTTP request URI parsed from start_line.
        ``version``,
            HTTP protocol version, parsed from start_line
        ``headers``,
            HTTP request headers that comes after start_line and before an
            optional body.
        ``body``,
            Optional HTTP body. If request body is not found pass this as
            None.
        ``remote_ip``,
            IP address of the remote client making this request.
        """

    def supports_http_1_1():
        """Returns True if this request supports HTTP/1.1 semantics"""

    def get_ssl_certificate():
        """Returns the client's SSL certificate, if any.

        To use client certificates, `cert_reqs` configuration value must be
        set to ssl.CERT_REQUIRED,

        The return value is a dictionary, see SSLSocket.getpeercert() in
        the standard library for more details.
        http://docs.python.org/library/ssl.html#sslsocket-objects."""

    def query_plugins( interface, name, *args, **kwargs ):
        """Query plugins in the request's context. Since every request is
        under the context of an application, appname will be used to make the
        actual query. Will be using `IRequest.app` attribute"""

    def query_plugin( interface, name, *args, **kwargs ):
        """Query plugin in the request's context. Since every request is
        under the context of an application, appname will be used to make the
        actual query. Will be using `IRequest.app` attribute"""

    def url( *args, **kwargs ) :
        """Generate url for same application handling the current request."""

    def path( *args, **kwargs ) :
        """Generate url-path for same application handling the current 
        request."""

    def appurl( appname, *args, **kwargs ) :
        """Generate url for different application other than the one handling 
        the current request."""

    def path( appname, *args, **kwargs ) :
        """Generate url-path for the same application handling this request."""


class IResponse( Interface ):
    """Response object to send reponse status, headers and body."""

    def write( chunk, callback=None ):
        """Writes the given chunk to the response stream."""
        pass

    def finish():
        """Finishes this HTTP request on the open connection."""
        pass


class IRequestHandler( Interface ):

    methods = Attribute(
        "Request handler can override this attribute to provide a sequence of "
        "HTTP Methods supported by the plugin. "
    )

    def head( request ):
        """Callback method for HEAD request. 
        
        ``request``,
            Object instance implementing :class:`IRequest` interface.
        """

    def get( request ):
        """Callback method for GET request. 
        
        ``request``,
            Object instance implementing :class:`IRequest` interface.
        """

    def post( request ):
        """Callback method for POST request. 
        
        ``request``,
            Object instance implementing :class:`IRequest` interface.
        """

    def delete( request ):
        """Callback method for DELETE request. 
        
        ``request``,
            Object instance implementing :class:`IRequest` interface.
        """

    def put( request ):
        """Callback method for PUT request. 
        
        ``request``,
            Object instance implementing :class:`IRequest` interface.
        """
