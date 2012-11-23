# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

import socket

from pluggdapps.plugin import Interface, Attribute

__all__ = [ 'ICommand', 'IWebApp', 'IHTTPServer', 'IHTTPConnection' ]

class ICommand( Interface ):
    """Handle sub-commands issued from command line script. The general
    purpose is to parse the command line string arguments into `options` and
    `arguments` and handle sub-commands as pluggable functions."""

    description = Attribute( "Text to display before the argument help." )
    usage = Attribute( "String describing the program usage" )
    cmd = Attribute( "Name of the command" )

    def subparser( parser, subparsers ):
        """Use ``subparsers`` to create a sub-command parser. The `subparsers`
        object would have been created using ArgumentParser object ``parser``.
        """

    def handle( args ):
        """While :meth:`subparser` is invoked, the sub-command plugin can 
        use set_default() method on subparser to set `handler` attribute to
        this method.

        So that this handler will automatically be invoked if the sub-command
        is used on the command line.

        ``args``,
            parsed args from ArgumentParser's parse_args() method.
        """

class IWebApp( Interface ):
    """In pluggdapps, Web-Application is a plugin, whereby, a plugin is a bunch
    of configuration parameters implementing one or more interface
    specification. Note that application plugins are singletons are the first
    ones to be instantiated along with platform singleton. Attributes,
        `script`, `subdomain`, `instkey`, `router`
    are initialized by platform initialization code. 

    There is a base class :class:`WebApp` which implements this interface
    and provides necessary support functions for application creators.
    Therefore application plugins must derive from this base class.
    """
    instkey = Attribute(
        "Index into global settings"
    )
    appsetting = Attribute(
        "Optional Read only copy of application's settings."
        # TODO : Make this as read only copy.
    )
    script = Attribute(
        "The script name on which the application will be mounted. If "
        "application is mounted on a sub-domain this will be ``None``"
    )
    subdomain = Attribute(
        "The subdomain name on which the application will be mounted. If "
        "application is mounted on a script name this will be ``None``"
    )
    baseurl = Attribute(
        "Computed base url for web application."
    )
    router = Attribute(
        "Plugin instance implementing :class:`IHTTPRouter` interface. This is "
        "the root router using which request urls will be resolved to a view "
        "callable. Should be instantiated during boot time inside "
        ":meth:`startapp` method."
    )
    cookie = Attribute(
        "Plugin instance implementing IHTTPCookie interface spec. Methods "
        "from this plugin will be used to process both request cookies "
        "and response cookies. This can be overriden at corresponding "
        "request / response plugin settings."
    )

    def startapp():
        """Boot this applications. Called at platform boot-time. 
        Instantiate :attr:`router` attribute."""

    def shutdown():
        """Shutdown this application. Reverse of :meth:`startapp`."""

    def dorequest( request, body=None, chunk=None, trailers=None ):
        """`request` was resolved for this application. Request handling
        callback for application. The callback will be issued when,
            * A new request without body is received, where the request
              data is available in `request`.
            * A new request with a body is received, in which case kwarg
              `body` gives the request body as byte-string.
        """
 
    def dochunk( request, chunk=None, trailers=None ):
        """`request` was resolved for this application. Request handling
        callback for application. The callback will be issued when,
            * A new request with a chunk is received, in which case kwarg
              `chunks` gives a single element list with received chunk as,
                ( chunk_size, chunk_ext, chunk_data ) 
            * A request is being received in chunked mode and a request chunk
              just received, in which case `chunk` is a tuple of,
                ( chunk_size, chunk_ext, chunk_data )
            * The last chunk of the request is received without a trailer.
            * The last chunk of the request is received with a trailer.
        """
 
    def onfinish( request ):
        """When a finish is called on the response. And this call back is 
        issued beginning a finish sequence for this ``request`` in the 
        application's context. Plugin's implementing this method must call
        request.onfinish()."""

    def urlfor( request, name, **matchdict ):
        """Generate url (full url) identified by routing-name `name`. Use
        `pathfor` method to generate the relative url and join the result
        with the web-application's `base_url`. To know more about method
        arguments refer pathfor() interface method.
        """

    def pathfor( request, name, **matchdict ):
        """Generate relative url for request using route definitions.

        ``name``,
            Name of the route definition to use. Previously added via
            add_view() interface method.

        ``request``,
            The :class:`IHTTPRequest` object for which url is generated.

        ``matchdict``,
            A dictionary of variables in url-patterns and their corresponding
            value string. Every route definition will have variable (aka
            dynamic components in path segments) that will be matched with
            url. If matchdict contains the following keys,

            `_query`, its value, which must be a dictionary similar to 
            :attr:`IHTTPRequest.getparams`, will be interpreted as query
            parameters and encoded to query string.

            `_anchor`, its value will be attached at the end of the url as
            "#<_anchor>".
        """

class IHTTPServer( Interface ):
    """Interface to bind and listen for accept HTTP connections."""

    sockets = Attribute(
        "Dictionary of listening sockets."
    )
    connections = Attribute(
        "List of accepted connections. Each connection is a plugin "
        "implementing :class:`IConnection` interface."
    )
    version = Attribute(
        "HTTP Version supported by this server."
    )

    def start( *args, **kwargs ):
        """Starts this server and returns a server object."""

    def stop():
        """Stops listening for new connections.

        Requests currently in progress may still continue after the
        server is stopped.
        """

class IHTTPConnection( Interface ):
    """Interface for handling HTTP connections accepted by IHTTPServer.
    Received request are dispatched using :class:`IHTTPRequest` plugin."""

    conn = Attribute(
        "Accepted connection object."
    )
    address = Attribute(
       "Client's IP address and port number. If running behind a "
       "load-balancer or a proxy, the real IP address provided by a load "
       "balancer will be passed in the ``X-Real-Ip`` header."
    )
    server = Attribute(
        ":class:`IHTTPServer` plugin"
    )
    product = Attribute(
        "HTTP product string (byte-string) for this server. Typically sent "
        "with HTTP `Server` Reponse header."
    )
    version = Attribute(
        "HTTP Version supported by this connection."
    )
    request = Attribute(
        ":class:`IHTTPResource` plugin instance for current on-going request."
    )

    def __init__( self, conn, addr, server, version ):
        """Positional arguments:

        `conn`,
            Accepted connection object.

        `addr`,
            Accepted client's address.

        `server`
            :class:`IHTTPServer` plugin object.
        """

    def get_ssl_certificate() :
        """In case of SSL traffic, return SSL certifacte."""

    def set_close_callback( callback ):
        """Subscribe a `callback` function, to be called when this connection
        closed."""

    def set_finish_callback( callback ):
        """Subscribe a `callback` function, to be called when an on-going
        request/response if finished."""

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
            None, instead this argument will contain the request chunk in
            byte-string. Passed a tuple of,
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
        the on-going request's :class:`IHTTPRequest` plugin.

        ``chunk`,
            Request chunk to be handled. Passed as a tuple of,
                (chunk_size, chunk_ext, chunk_data).

        ``trailers``,
            Dictionary of chunk trailer headers. Key names in this dictionary
            will be decoded to string-type. Value names will be preserved as
            byte-string.
        """

    def write( chunk, callback=None ):
        """Write the `chunk` of data (bytes) to the connection and optionally
        subscribe a `callback` function to be called when data is successfully
        transfered."""

    def finish( callback=None ) :
        """Call this method when there is no more response to send back for
        the on-going request. To know when the response is done, which is when
        the last byte is sent on the wire, subscribe a `callback` to be 
        called on finishing the response.
        """

    def close():
        """Close this connection."""


class IScaffold( Interface ):
    """Interface specification for automatically creating scaffolding logic
    based on collection of user-fed variables and a source-template."""

    description = Attribute(
        "One line description of scaffolding logic."
    )

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
