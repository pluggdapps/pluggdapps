# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

from plugincore     import Interface, Attribute

__all__ = [ 'ICommand' ]

class ICommand( Interface ):
    """Handle sub-commands issued from command line script. The general
    purpose is to parse the command line string arguments into `options` and
    `arguments` and then perform the sub-command in the user desired 
    fashion."""

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


class ISettings( Interface ):
    """ISettings is a mixin interface that can be implemented of any plugin.
    Especially plugins that support configuration. Note that a plugin is a
    bunch of configuration parameters implementing one or more interface
    specification.
    """

    def normalize_settings( settings ):
        """Static interface method.
        `settings` is a dictionary of configuration parameters. This method 
        will be called after aggregating all configuration parameters for a
        plugin and before updating the plugin instance with its configuration
        parameters.

        Use this method to do any post processing on plugin's configuration
        parameter and return the final form of configuration parameters.
        Processed parameters are updated in-pace"""

    def default_settings():
        """Static interface method.
        Return instance of :class:`ConfigDict` providing meta data
        associated with each configuration parameters supported by the plugin.
        Like - default value, value type, help text, wether web configuration
        is allowed, optional values, etc ...
        
        To be implemented by classed deriving :class:`Plugin`.
        """

    def web_admin( settings ):
        """Plugin settings can be configured via web interfaces and stored in
        a backend like database, files etc ... Use this method for the
        following,
        
        * To update the in-memory configuration settings with new `settings`
        * To persist new `settings` in a backend data-store."""


class IHTTPServer( Interface ):
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

    appname = Attribute( "Application name" )

    def boot( inifile ):
        """Every application boots from an inifile which is a one time
        activity. Configuration settings from this inifile overrides
        application package's default settings. The implementer of this method
        can also can be
        settings from the original inifile can be overriden using settings derived from """

    def start( request ):

    def finish( request ):

    def router( request ):

    def query_plugins( interface, name, *args, **kwargs ):

    def query_plugin( interface, name, *args, **kwargs ):


class IHTTPRequest( Interface ):
    """Entry point for every request into the application code. Typically
    pluggdapps platform will provide a collection of request handler plugins
    implementing this interface. While the applications can simply derive
    their handler class from the base class and override necessary methods."""

    app = Attribute(
        "Application instance deriving from :class:`Plugin` implementing "
        ":class:`IApplication` interface."
    )
    do_methods = Attribute(
        "Request handler can override this attribute to provide a sequence of "
        "HTTP Methods supported by the class. "
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
        ":method:`IHTTPRequest.get_argument`, which returns argument values as "
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
    remote_ip = Attribure(
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
        "into sections, special section `DEFAULT` provides as global "
        "settings. Other sections are application specific settings for "
        "modules and plugins."
    )
    rootsettings = Attribute(
        "A copy of root settings common to all applications, plugins and "
        "modules."
    )

    def __init__( connection, method, uri, version, headers, remote_ip ):
        """Instance of plugin implementing this interface corresponds to a
        single HTTP request. Note that instantiating this class does not
        essentially mean the entire request is received. Only when
        :method:`IHTTPRequest.handle` is called complete request is available
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

    def handle():
        """Once complete request is available, handle the request. This is
        a potential point where actual request handling can be dispatched
        to a process-pool.
        
        Typically, applications are resolved at this point and the request is
        passed on to the application."""

    def supports_http_1_1():
        """Returns True if this request supports HTTP/1.1 semantics"""

    def get_ssl_certificate():
        """Returns the client's SSL certificate, if any.

        To use client certificates, `cert_reqs` configuration value must be
        set to ssl.CERT_REQUIRED,

        The return value is a dictionary, see SSLSocket.getpeercert() in
        the standard library for more details.
        http://docs.python.org/library/ssl.html#sslsocket-objects
        """

class IURLRouter( Interface ):

    def route( request ):
        pass

    def match( request ):
        pass


class IHTTPResponse( Interface ):

    def __init__( request ):

    def write( chunk, callback=None ):
        """Writes the given chunk to the response stream."""

    def finish():
        """Finishes this HTTP request on the open connection."""

