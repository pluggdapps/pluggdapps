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
    appname = Attribute(
        "Should be same as pluginm(app)."
    )
    connection = Attribute(
        "An HTTP request is attached to a single HTTP connection, which can "
        "be accessed through the 'connection' attribute. Since connections "
        "are typically kept open in HTTP/1.1, multiple requests can be handled "
        "sequentially on a single connection."
    )
    method = Attribute(
        "HTTP request method, e.g. 'GET' or 'POST'"
    )
    uri = Attribute(
        "HTTP Request URI"
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
    host = Attribute(
        "The requested hostname, usually taken from the ``Host`` header."
    )
    path = Attribute(
        "Path portion of HTTP request URI"
    )
    query = Attribute(
        "Query portion of HTTP request URI"
    )
    full_url = Attribute(
        "Reconstructs the full URL for this request, which is, "
        "protocol + host + uri"
    )
    protocol = Attribute(
        "The protocol used, either 'http' or 'https'.  If running behind a "
        "load-balancer or a proxy, the real scheme will be passed along via "
        "via an `X-Scheme` header."
    )
    remote_ip = Attribute(
       "Client's IP address as a string. If running behind a load-balancer "
       "or a proxy, the real IP address provided by a load balancer will be "
       "passed in the ``X-Real-Ip`` header."
    )
    arguments = Attribute(
        "GET/POST arguments are available in the arguments property, which "
        "maps arguments names to lists of values (to support multiple values "
        "for individual names). Names are of type `str`, while arguments "
        "are byte strings. Note that this is different from "
        ":method:`IRequest.get_argument`, which returns argument values as "
        "unicode strings."
    )
    files = Attribute(
        "File uploads are available in the files property, which maps file "
        "names to lists of :class:`HTTPFile`."
    )
    cookies = Attribute(
        "A dictionary of Cookie.Morsel objects representing request cookies "
        "from client"
    )
    settings = Attribute(
        "A copy of application settings dictionary. Settings are organised "
        "into sections, special section `DEFAULT` provides global "
        "settings for all application sectionw. Other sections are "
        "application specific settings for modules and plugins."
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
    response = Attribute(
        "Response object corresponding to this request. The object is an "
        "instance of plugin implementing :class:`IResponse` interface."
    )

    def __init__( app, connection, address, startline, headers, body ):
        """Instance of plugin implementing this interface corresponds to a
        single HTTP request. Note that instantiating this class does not
        essentially mean the entire request is received. Only when
        :method:`IRequest.handle` is called complete request is available
        and partially parsed.

        ``app``,
            application plugin implementing :class:`IApplication` interface
            in whose context the current request is processed.
        ``connection``,
            HTTP socket returned as a result of accepting the connection.
        ``address``
            Remote client-ip address initiating the connection.
        ``startline``,
            HTTP request startline.
        ``headers``,
            HTTP request headers that comes after start_line and before an
            optional body.
        ``body``,
            Optional HTTP body. If request body is not found pass this as
            None.
        """

    def get_argument( name, default=None, strip=True ):
        """Returns the value of the argument with the given name.

        If default is not provided, the argument is considered to be
        required, and we throw an exception if it is missing.

        If the argument appears in the url more than once, we return the
        last value.

        The returned value is always unicode.
        """

    def get_arguments( name, default=[], strip=True ):
        """Returns a list of the arguments with the given name.

        If the argument is not present, returns an empty list.

        The returned values are always unicode.
        """

    def decode_argument( value, name=None ):
        """Decodes an argument from the request.

        The argument has been percent-decoded and is now a byte string.
        By default, this method decodes the argument as utf-8 and returns
        a unicode string, but this may be overridden in subclasses.

        This method is used as a filter for both get_argument() and for
        values extracted from the url and passed to get()/post()/etc.

        The name of the argument is provided if known, but may be None
        (e.g. for unnamed groups in the url regex).
        """

    def get_cookie( name, default=None ):
        """Gets the value of the cookie with the given name, else default."""

    def get_secure_cookie( name, value=None, max_age_days=31 ):
        """Returns the given signed cookie if it validates, or None."""

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

    def on_connection_close():
        """Called back when remote client close the connection on this request
        currently processed."""


class IResponse( Interface ):
    """Response object to send reponse status, headers and body."""

    cookies = Attribute(
        "A dictionary of Cookie.Morsel objects representing response cookies "
        "to be sent from server."
    )

    def __init__( request ):
        """
        ``request``,
            is an instance object for plugin implementing :class:`IResponse`
            interface.
        """

    def clear():
        """Resets all headers and content for this response."""

    def set_status( status_code ):
        """Sets the status code for our response."""
        pass

    def get_status():
        """Returns the status code for our response."""

    def set_header( name, value ):
        """Sets the given response header name and value.

        If a datetime is given, we automatically format it according to the
        HTTP specification. If the value is not a string, we convert it to
        a string. All header values are then encoded as UTF-8."""

    def add_header( name, value ):
        """Adds the given response header and value.

        Unlike `set_header`, `add_header` may be called multiple times
        to return multiple values for the same header.
        """

    def set_cookie( name, value, domain=None, expires=None, path="/",
                    expires_days=None, **kwargs ):
        """Sets the given cookie name/value with the given options.

        Additional keyword arguments are set on the Cookie.Morsel
        directly.
        See http://docs.python.org/library/cookie.html#morsel-objects
        for available attributes.
        """

    def clear_cookie( name, path="/", domain=None ):
        """Deletes the cookie with the given name."""

    def clear_all_cookies():
        """Deletes all the cookies the user sent with this request."""

    def set_secure_cookie( name, value, expires_days=30, **kwargs ):
        """Signs and timestamps a cookie so it cannot be forged.

        You must specify the ``cookie_secret`` setting in your Application
        to use this method. It should be a long, random sequence of bytes
        to be used as the HMAC secret for the signature.

        To read a cookie set with this method, use `get_secure_cookie()`.

        Note that the ``expires_days`` parameter sets the lifetime of the
        cookie in the browser, but is independent of the ``max_age_days``
        parameter to `get_secure_cookie`.
        """

    def create_signed_value( name, value ):
        """Signs and timestamps a string so it cannot be forged.

        Normally used via set_secure_cookie, but provided as a separate
        method for non-cookie uses.  To decode a value not stored
        as a cookie use the optional value argument to get_secure_cookie.
        """

    def render( template_name, **kwargs ):
        """Renders the template with the given arguments as the response."""

    def write( chunk ):
        """Writes the given chunk to the output buffer.

        To write the output to the network, use the flush() method below.

        If the given chunk is a dictionary, we write it as JSON and set
        the Content-Type of the response to be application/json.
        (if you want to send JSON as a different Content-Type, call
        set_header *after* calling write()).

        Note that lists are not converted to JSON because of a potential
        cross-site security vulnerability.  All JSON output should be
        wrapped in a dictionary.  More details at
        http://haacked.com/archive/2008/11/20/anatomy-of-a-subtle-json-vulnerability.aspx
        """

    def flush( include_footers=False, callback=None ):
        """Flushes the current output buffer to the network.

        The ``callback`` argument, if given, can be used for flow control:
        it will be run when all flushed data has been written to the socket.
        Note that only one flush callback can be outstanding at a time;
        if another flush occurs before the previous flush's callback
        has been run, the previous callback will be discarded.
        """

    def finish():
        """Finishes this HTTP request on the open connection."""
        pass

    def redirect( url, permanent=False, status=None ):
        """Sends a redirect to the given (optionally relative) URL.

        If the ``status`` argument is specified, that value is used as the
        HTTP status code; otherwise either 301 (permanent) or 302
        (temporary) is chosen based on the ``permanent`` argument.
        The default is 302 (temporary).
        """

    def send_error( status_code=500, **kwargs ):
        """Sends the given HTTP error code to the browser.

        If `flush()` has already been called, it is not possible to send
        an error, so this method will simply terminate the response.
        If output has been written but not yet flushed, it will be discarded
        and replaced with the error page.

        Override `write_error()` to customize the error page that is returned.
        Additional keyword arguments are passed through to `write_error`.
        """

    def write_error( status_code, **kwargs ):
        """Override to implement custom error pages.

        ``write_error`` may call `write`, `render`, `set_header`, etc
        to produce output as usual.

        If this error was caused by an uncaught exception, an ``exc_info``
        triple will be available as ``kwargs["exc_info"]``.  Note that this
        exception may not be the "current" exception for purposes of
        methods like ``sys.exc_info()`` or ``traceback.format_exc``.

        For historical reasons, if a method ``get_error_html`` exists,
        it will be used instead of the default ``write_error`` implementation.
        ``get_error_html`` returned a string instead of producing output
        normally, and had different semantics for exception handling.
        Users of ``get_error_html`` are encouraged to convert their code
        to override ``write_error`` instead.
        """

class IResponseTransformer( Interface ):
    """Specification to transform response headers and body. A chain of
    transforms can be configured with plugins implementing 
    :class:`IResponse`."""

    def start_transform( self, headers, chunk, finished=False ):
        """Start transformation using complete list of response headers and
        first ``chunk`` of response body, if ``finished`` is False. If
        ``finished`` is True, then ``chunk`` becomes the first and last part
        of response body."""

    def transform( self, chunk, finished=False ):
        """Continue with the current transformation with subsequent chunks
        response body. If ``finished`` is True, then ``chunk is the last chunk
        of response body."""


class IRequestHandler( Interface ):

    methods = Attribute(
        "Request handler can override this attribute to provide a sequence of "
        "HTTP Methods supported by the plugin. "
    )
    default_headers = Attribute(
        "Default HTTP headers to be set automatically for every reponse."
    )

    def __call__( request ):
        """In the absence of method specific attributes or if the resolver
        cannot find an instance attribute to apply the handler call back, the
        object will simply be called.
        
        ``request``,
            Object instance implementing :class:`IRequest` interface.
        """

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

    def onfinish():
        """Called after the end of a request, after the response has been sent
        to the client."""

