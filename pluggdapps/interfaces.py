# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

"""Collection of some basic set of interface specifications used by pluggdapps
platform."""

import socket

from   pluggdapps.plugin import Interface

__all__ = [
    'IConfigDB', 'ICommand', 'IHTTPServer', 'IHTTPConnection', 'IWebApp',
    'IScaffold',
    
]

class IConfigDB( Interface ):
    """Interface specification to persist platform configuration to a backend
    data-store or database."""

    def connect():
        """Do necessary initialization to connect with data-store."""

    def dbinit( *args, **kwargs ):
        """If datastore does not exist, create one. Also intialize
        configuration tables for each mounted application under
        [mountloc] section. Expect this method to be called when ever platform
        starts-up. For more information refer to corresponding plugin's
        documentation
        """

    def config( **kwargs ):
        """Get or set configuration parameter for platform. For more
        information refer to corresponding plugin's documentation."""

    def close():
        """Reverse of :meth:`connect`."""


class ICommand( Interface ):
    """Handle sub-commands issued from command line script. Plugins are
    expected to parse the command line string arguments into ``options`` and
    ``arguments`` and handle the sub-commands."""

    description = ''
    """A short description about the plugin implementing this specification."""

    usage = ''
    """String describing the program usage"""

    cmd = ''
    """Name of the command"""

    def subparser( parser, subparsers ):
        """Use ``subparsers`` to create a sub-command parser. The `subparsers`
        object would have been created, by the main script, using 
        ArgumentParser object ``parser``.
        """

    def handle( args ):
        """Previously when :meth:`subparser` was invoked, the plugin can 
        use set_default() method on subparser to set the `handler` attribute 
        to this method so that this handler will automatically be invoked if
        the sub-command is used on the command line.

        ``args``,
            parsed args from ArgumentParser's parse_args() method.
        """


class IHTTPServer( Interface ):
    """Web server specification to bind and listen for new client 
    connections. Every successfull connection will further be handled by 
    :class:`IHTTPConnection` plugin.
    """

    sockets = {}
    """Mapping of socket (file-descriptor) listening for new connection and
    the socket object. These are server sockets."""

    connections = []
    """List of accepted and active connections. Each connection is a plugin
    implementing :class:`IHTTPConnection` interface."""

    version = b''
    """HTTP Version supported by this server."""

    def start( *args, **kwargs ):
        """Starts the server. This is typically a blocking call."""

    def stop():
        """Stop listening for new connections. Close ``connections`` that are 
        currently active and finally close the server sockets. Implementers
        must make sure that when this method is called :meth:`start` method
        must return from blocking.
        """

    def close_connection( httpconn ):
        """Close a client connection `httpconn` which is
        :class:`IHTTPConnection` plugin maintained in :attr:`connections`
        list."""


class IHTTPConnection( Interface ):
    """Every new client connection accepted by :class:`IHTTPServer` will
    be handled by a plugin instance implementing this interface. All
    read-writes on the connection is specified by this interface."""

    conn = None
    """Socket connection object accepted by the server."""

    address = tuple()
    """Client's IP address and port number."""

    server = None
    """:class:`IHTTPServer` plugin that accepted this connection."""

    product = b''
    """HTTP product string (byte-string) for this server. Typically sent with
    HTTP `Server` Reponse header."""

    version = b''
    """HTTP Version supported by this connection. Normally infered from
    :attr:`IHTTPServer.version` attribute. """

    request = None
    """:class:`IHTTPRequest` plugin instance for current on-going request."""

    def __init__( self, conn, addr, server, version ):
        """Positional arguments,

        ``conn``,
            Accepted connection object.

        ``addr``,
            Accepted client's address.

        ``server``,
            :class:`IHTTPServer` plugin object.

        ``version``,
            HTTP Version supported by this connection.
        """

    def get_ssl_certificate() :
        """In case of SSL traffic, return SSL certifacte."""

    def set_close_callback( callback ):
        """Subscribe a ``callback`` function, to be called when this connection
        closed."""

    def set_finish_callback( callback ):
        """Subscribe a ``callback` function, to be called when an on-going
        request/response is finished."""

    def handle_request( method, uri, version, headers, body=None, chunk=None,
                        trailers=None ):
        """When a new request is received, this method is called to handle the
        request.

        ``method``,
            Request method in byte-string.

        ``uri``,
            Request URI in byte-string.

        ``version``,
            Request version in byte-string.

        ``headers``,
            Dictionary of request headers. Key names in this dictionary will be
            decoded to string-type. Value names will be preserved as
            byte-string.

        ``body``,
            Optional request body in byte-string.

        ``chunk``,
            If the new request is chunked Transfer-Encoded, `body` will be
            None while this argument will contain the request chunk in
            byte-string. Passed as tuple of,
                (chunk_size, chunk_ext, chunk_data).

        ``trailers``,
            If the new request is chunked Transfer-Encoded, and `chunk` is the
            last chunk, then trailers might optionally contain a dictionary of
            chunk trailer headers. Key names in this dictionary will be
            decoded to string-type. Value names will be preserved as
            byte-string.

        The request is resolved for configured web-application and dispatched
        to it."""

    def handle_chunk( chunk, trailers=None ):
        """For every request chunk received, this method will be called. For
        the last chunk `trailers`, if present, will also be passed. In case of
        chunked request, ``request`` attribute of this plugin will preserve
        the on-going request as :class:`IHTTPRequest` plugin.

        ``chunk`,
            Request chunk to be handled. Passed as a tuple of,
                (chunk_size, chunk_ext, chunk_data).

        ``trailers``,
            Dictionary of chunk trailer headers. Key names in this dictionary
            will be decoded to string-type. Value names will be preserved as
            byte-string.
        """

    def write( chunk, callback=None ):
        """Write a ``chunk`` of data (bytes) to the connection and optionally
        subscribe a ``callback`` function to be called when data is successfully
        transfered.
        
        ``chunk``
            Chunk of data in byte-string to buffer and send.

        ``callback``
            Handler to callback when data is written to the socket.
        """

    def close():
        """Close this connection."""


class IWebApp( Interface ):
    """In pluggdapps, a web-Application is a plugin implementing this
    interface. And for this interface to be relevant,
    :class:`pluggdapps.platform.Webapps` must be used to boot the platform.
    There is also a base class :class:`WebApp` which implements this
    interface and provides necessary support functions for application
    creators. Therefore application plugins must derive from this base
    class.
    """

    instkey = tuple()
    """A tuple of (appsec, netpath, configini)"""

    appsettings = {}
    """Optional read only copy of application's settings. Gathered from
    plugin's default settings, ini configuration file(s) and optionally a
    backend store."""

    netpath = ''
    """Net location and script-path on which the instance of webapp is mounted.
    This is obtained from configuration settings."""

    baseurl = ''
    """Computed string of base url for web application."""

    router = None
    """Plugin instance implementing :class:`IHTTPRouter` interface. This is
    the root router using which request urls will be resolved to a view
    callable. Must be instantiated during boot time inside :meth:`startapp`
    method."""

    cookie = None
    """Plugin instance implementing IHTTPCookie interface spec. Methods "
    from this plugin will be used to process both request cookies and response
    cookies."""

    livedebug = None
    """Plugin to handle we based interactive debugging."""

    in_transformers = []
    """List of plugins implmenting :class:`IHTTPInBound` interface. In bound
    requests will be passed through this list of plugins before being
    dispatched to the router."""

    out_transformers = []
    """List of plugins implmenting :class:`IHTTPOutBound` interface. Out bound
    responses will be passed through this list of plugins before writing it on
    the connection."""

    def startapp():
        """Boot the applications. Called at platform boot-time."""

    def dorequest( request, body=None, chunk=None, trailers=None ):
        """This method is called after a new request is resolved to an
        application, typically by :class:`IHTTPConnection` plugin. The 
        callback will be issued when,

          * A new request without body is received, where the request data is 
            available in ``request``.

          * A new request with a body is received, in which case kwarg ``body`` 
            gives the request body as byte-string.
        """
 
    def dochunk( request, chunk=None, trailers=None ):
        """This method is called for a new request (of type chunked encoding)
        is resolved to an application. Otherwise it is called for an on-going
        chunked request, for every chunk of the request, in which case the
        web-application and related framework instances are preserved across
        the chunks. This is typically done by :class:`IHTTPConnection`.

        The callback will be issued when,

          * A new request with a chunk is received, in which case kwarg
            `chunks` gives a single element list with received chunk as,
            ``(chunk_size, chunk_ext, chunk_data)``.

          * A request is being received in chunked mode and a request chunk
            just received, in which case `chunk` is a tuple of,
            ``(chunk_size, chunk_ext, chunk_data)``.

          * The last chunk of the request is received without a trailer.

          * The last chunk of the request is received with a trailer.
        """
 
    def onfinish( request ):
        """When finish is called on the :attr:`request.response`, by calling
        ``flush( finished=True )``, a chain of onfinish() callbacks will be 
        issued by :class:`pluggdapps.web.interfaces.IHTTPResponse`."""

    def shutdown():
        """Shutdown this application. Reverse of :meth:`startapp`."""

    def urlfor( request, *args, **kwargs ):
        """Generate url (full url) for request using ``args`` and ``kwargs``.
        Typically, :meth:`pathfor` method shall be used to generate the
        relative url and join the result with the web-application's
        :attr:`webapp.base_url`. To know more about method arguments refer 
        corresponding router's :meth:`urlpath` interface method. Returns an
        absolute-URL as string.

        ``request``,
            The :class:`IHTTPRequest` object for which url is generated.
        """

    def pathfor( request, *args, **matchdict ):
        """Generate relative url for request using route definitions, using
        ``args`` and ``kwargs``. To learn more about ``args`` and ``kwargs``,
        refer corresponding router's :meth:`pathfor` interface method. Returns
        a URL path as string.

        ``request``,
            The :class:`IHTTPRequest` object for which url is generated.
        """


class IScaffold( Interface ):
    """Interface specification for automatically creating scaffolding logic
    based on collection of user-fed variables and a source-template."""

    description = ''
    """One line description of scaffolding logic."""

    def __init__( settings={} ):
        """Initialize interface attributes with ``settings`` parameter.
        """

    def query_cmdline():
        """Query command line for variable details."""

    def generate():
        """Generate the scaffolding logic."""

    def printhelp():
        """If executed in command line, provide a meaning full description
        about this scaffolding plugin and variables that can be defined."""


