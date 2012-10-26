# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

from pluggdapps.plugin import Interface, Attribute

__all__ = [
    'IHTTPServer', 'IHTTPConnection', 'IRouter', 'IResource', 'ICookie',
    'IRequest', 'IController', 'IErrorPage', 'IRenderer', 'IResponse',
    'IResponseTransformer',
]

# TODO : IAssetDescriptor

class IHTTPServer( Interface ):
    """Interface to bind and listen for accept HTTP connections."""

    sockets = Attribute(
        "Dictionary of listening sockets."
    )

    connections = Attribute(
        "List of accepted connections. Each connection is a plugin "
        "implementing :class:`IConnection` interface."
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
    Received request are dispatched using :class:`IRequest` plugin."""

    conn = Attribute( "Accepted connection object." )

    address = Attribute( "Address of the client connected on the other end." )

    write_callback = Attribute( "Call-back for writing data to connection." )

    close_callback = Attribute( "Call-back when connection is closed." )

    def __init__( self, conn, addr, server ):
        """Positional arguments:

        `conn`,
            Accepted connection object.

        `addr`,
            Accepted client's address.

        `server`
            :class:`IServer` plugin object.
        """

    def get_ssl_certificate() :
        """In case of SSL traffic, return SSL certifacte."""

    def set_close_callback( callback ):
        """Subscribe a `callback` function to be called when this connection
        closed."""

    def write( chunk, callback=None ):
        """Write the `chunk` of data (bytes) to the connection and optionally
        subscribe a `callback` function to be called when data is successfully
        transfered."""

    def finish() :
        """Call this method once complete response is written to the
        connection-stream. When this method returns the request is considered
        closed."""

    def close():
        """Close this connection."""


class IResource( Interface ):
    """Interface specification for resource or model plugins."""

    def __call__( request, c ):
        """For ``request``, populate :class:`Context` dictionary ``c``. The
        same context object will be passed down to view callables and 
        view-templates."""


class IRouter( Interface ):
    """Every `IRouter` plugin must treat a request's url as a chain of 
    resource and resolve them based on the next path segment which are
    pluggable using :meth:`IRouter.router` method, in the absence
    of which, the plugin must match request's url against mapping rules.
    
    To avoid repeated initialization, the root-router instance will be
    rememebered by the web-application during :meth:`IWebApp.onboot`.
    Similarly chained routers will be remembered in :attr:`traversals` where
    each element in a plugin implementing :class:`IRouter`, whose name is that
    of the path segment it matches."""

    segment = Attribute(
        "If defined for a plugin, must match with first segment-name in "
        "request url-path. Only then it can be selected for traversal"
    )
    defaultview = Attribute(
        "If defined for a plugin, must be a view-callable. When there are no "
        "more traversal to be done and no more `views` left to be matched. "
        "Then this attribute is the last resort to return back a "
        "view-callable."
    )
    traversals = Attribute(
        "Dictionary of path-segment name to IRouter plugins that can be "
        "subscribed during onboot() time.If this attribute is left empty, "
        "then it normally means url will be matched with route-pattern "
        "definitions."
    )
    views = Attribute(
        "Dictionary of view names and view predicates added via `add_view()` "
        "method."
    )

    def onboot():
        """Chained call from :meth:`IWebApp.onboot`. Implementation 
        should chain the onboot() call further down.

        Typically, path-segment resolution and url route-mapping is constructed
        here using :metho:`add_view`.

        Initialization of :attr:`traversals` attribute with a list of IRouter 
        instances for this path segment."""

    def route( request, c ):
        """Resolve request url based on traversals. If there is a matching
        path-segment with one of its traversals, then use the matching router
        and invoke its router() method. This call be chained until all the
        path-segments are resolved, in which case it should return a
        view-callable, or until one of the path segment fail to match.
        
        Along the way, the context object ``c`` will be passed to 
        :class:`IResource` object configured for IRouter instances. So that
        the context object can be updated by the resource logic before they
        are passed to view callable.

        If one of the path segment fails to match along the chained router()
        call, then it is expected that the last router instance at the end of
        the chain will match the remaining resolve_path using url-pattern
        matching.

        What ever be the case, the chained call to router() must eventually 
        return back a view callable to web-application."""

    def genpath( request, name, *traverse, **matchdict ):
        """Generate path, including query and fragment (aka anchor) using this
        request and using,

        ``name``,
            Name of the view to generate a routable path for.

        ``traverse``,
            Valid list of path segment names to be prefixed in the final path.

        ``matchdict``,
            Dictionary of name, value strings, where names represent the
            variable components in the route. Following keys are treated
            special,
                _remains
            The semantics for these values are same as defined for method
            :meth:`IWebApp.pathfor`.

            Note that among the special keys _query and _anchor is expected to
            be pruned off before reaching this method.
        """

    def add_view( name, resource=None,
                  # Predicate arguments
                  pattern=None, xhr=None, method=None, arguments=None,
                  header=None, accept=None, path_info=None,
                  # View controler
                  view_callable=None, attr=None, permission=None ):
        """Add a router mapping rule for this router object which will be used
        by match() method.
        
        ``name``,
            The name of the route. This attribute is required and it must be
            unique among all defined routes in a given web-application.

        ``resource``,
            A plugin name implementing :class:`IResource` interface.

        ``pattern``,
            The pattern of the route like blog/{year}/{month}/{date}. This 
            argument is required. If the pattern doesn't match the current 
            URL, route matching continues.

        ``xhr``,
            This value should be either True or False. If this value is 
            specified and is True, the request must possess an 
            HTTP_X_REQUESTED_WITH (aka X-Requested-With) header for this route 
            to match. This is useful for detecting
            AJAX requests.
            If this predicate returns False, route matching continues.

        ``method``,
            A string representing an HTTP method name, like 'GET', 'POST' ...
            If this argument is not specified, this route will match if
            the request has any request method. 
            If specified and the predicate doesn't match, route matching 
            continues.

        ``path_info``,
            This value represents a regular expression pattern that will be
            tested against the resolve_path request attribute.
            If the regex matches, this predicate will return True.
            If this predicate returns False, route matching continues.
            Note that path_info is matched after ``pattern``.

        ``params``,
            A dictionary of key,value pairs, when specified, ensures that the 
            associated route will match only when the request has a key in the 
            :attr:`IRequest.params` dictionary with the supplied value. If
            the supplied value is None, then the predicate will return True
            if supplied key is present in the request params.  If this
            predicate returns False, route matching continues.

        ``headers``,
            A dictionary of key,value pairs, when specified, ensures that the
            associated route will match only when the request has key in the
            :attr:`IRequest.headers` dictionary with the supplied value.
            Supplied value can be a compiled regular expression, in which
            case, it will be matched against the request header value. If
            value is None, then the predicate will return True if supplied key
            is present in the request's header dictionary.
            If this predicate returns False, route matching contines.

        ``accept``,
            This value represents a match query for one or more mimetypes in 
            the Accept HTTP request header. If this value is specified, it 
            must be in one of the following forms:
              * a mimetype match token in the form text/plain, a wildcard
                mimetype.
              * match token in the form text/*.
              * or a match-all wildcard mimetype match token in the form */*. 
            If any of the forms matches the Accept header of the request, this
            predicate will be True. If this predicate returns False, route
            matching continues.

        ``view_callable``,
            Plugin name implementing :class:`IController` interface
            specification.

        ``attr``,
            Callable method attribute for ``view`` plugin.

        ``permission``,
            The permission name required to invoke the view associated with
            this route. 
        """


class ICookie( Interface ):
    """Necessary methods and plugins to be used to handle HTTP cookies. This
    specification is compatible with IRequest and python's Cookie standard 
    library."""

    def parse_cookies( headers ):
        """Use HTTP `headers` dictionary, to parse cookie name/value pairs, 
        along with its meta-information, into Cookie Morsels.
            
            headers.get( 'Cookie', '' ) 

        should give the cookie string from `headers`.
        
        Return a SimpleCookie object from python's standard-library.
        """

    def set_cookie( cookies, name, morsel, **kwargs ) :
        """Sets the given cookie name/morsel dictionary with the positional
        arguments. Optional Key-word arguments typically contains,

          domain, expires_days, expires, path

        Additional keyword arguments are set on the Cookie.Morsel directly.

        ``cookies`` is from Cookie module and updated inplace, which is again
        returned back.

        See http://docs.python.org/library/cookie.html#morsel-objects
        for available attributes.
        """

    def create_signed_value( name, value ):
        """To avoid cookie-forgery `value` is digitally signed binary of,
        typically, a cookie_secret, name, timestamp of current time and 
        value.
        
        `name` and `value` are expected to be in string.
        """

    def decode_signed_value( name, value ):
        """`value` is digitally signed binary of typically a cookie_secret, 
        name, timestamp and value. Validate the cookie and decode them if need
        be and return an interpreted value. Reverse of `create_signed_value()`
        method."""


class IRequest( Interface ):
    """Request object, the only parameter that will be passed to
    :class:`IRquestHandler`."""

    # ---- Socket Attributes
    connection = Attribute(
        "An HTTP request is attached to a single HTTP connection, which can "
        "be accessed through the 'connection' attribute. Since connections "
        "are typically kept open in HTTP/1.1, multiple requests can be "
        "handled sequentially on a single connection."
    )

    # ---- HTTP Attributes
    method = Attribute(
        "HTTP request method, e.g. 'GET' or 'POST'"
    )
    uri = Attribute(
        "HTTP Request URI"
    )
    uriparts = Attribute(
        "UserDict object of uri parts in decoded, parsed and unquoted form. "
        "`scheme`, `netloc`, `path`, `query`, `fragment`, `username`, "
        "`password`, `hostname`, `port`, `script`, keys are available. "
        "Except query, which is a dictionary of query arguments, all other "
        "values are in string."
    )
    baseurl = Attribute(
        "Computed base url for the request under web-application "
        "request.webapp. This attribute can also be used as web-application "
        "url."
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
    address = Attribute(
       "Client's IP address and port number. "
       "If running behind a load-balancer or a proxy, the real IP address "
       "provided by a load balancer will be passed in the ``X-Real-Ip`` "
       "header."
    )
    cookies = Attribute(
        "A dictionary of http.cookies.Morsel objects representing request "
        "cookies from client"
    )
    getparams = Attribute(
        "GET arguments are available in the params property, which "
        "maps parameter names to lists of values (to support multiple values "
        "for individual names). Names and values are are of type `str`."
    )
    postparams = Attribute(
        "POST arguments are available in the params property, which "
        "maps parameter names to lists of values (to support multiple values "
        "for individual names). Names and values are of type `str`."
    )

    #---- Processed attributes
    params = Attribute(
        "Combined arguments of GET/POST, which maps parameter names to lists "
        "of values (to support multiple values for individual names). Names "
        "and values are are of type `str`. "
    )
    files = Attribute(
        "File uploads are available in the files property, which maps file "
        "names to lists of :class:`HTTPFile`."
    )
    response = Attribute(
        "Response object corresponding to this request. The object is an "
        "instance of plugin implementing :class:`IResponse` interface."
    )

    #---- Framework attributes
    session = Attribute(
        "If a session factory has been configured, this attribute will "
        "represent the current user's session object."
    )

    #---- Routing attributes
    resolve_path = Attribute(
        "Remaining portion of uri after removing the `baseurl` part that can "
        "be used to url routing. As and when a segment is consumed for "
        "routing it is removed from resolve_path and the remaining portion "
        "is eventually matched with route mapping."
    )
    traversed = Attribute(
        "A list of IRouter plugins each for a matching segment during path "
        "traversal."
    )
    matchrouter = Attribute(
        "Final route, :class:`IRoute` instance, that matches the path "
        "remaining after traversal."
    )
    matchdict = Attribute(
        "If remaining path after traversal has matched during this request's "
        "url-routing, matched values by the URL pattern will be available as "
        "matchdict dictionary."
    )
    view_name = Attribute(
        "Name of the view that matched this request's url."
    )

    #---- Others
    receivedat = Attribute(
        "Timestamp when request was recieved"
    )
    finishedat = Attribute(
        "Timestamp when the request was finished."
    )

    def __init__( conn, method, uri, version, headers, body ):
        """Instance of plugin implementing this interface corresponds to a
        single HTTP request. Note that instantiating this class does not
        essentially mean the entire request is received. Only when
        :method:`IRequest.handle` is called complete request is available
        and partially parsed.

        ``conn``,
            HTTP socket returned as a result of accepting the connection.
        ``method``,
            HTTP request method. 
        ``uri``,
            Parsed uri from request start line. A UserDict object as returned
            by :func:`parse_url()` function.
        ``version``,
            HTTP version string freom request start line.
        ``headers``,
            HTTP request headers that comes after start_line and before an
            optional body.
        ``body``,
            Optional HTTP body. If request body is not found pass this as
            None.
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

    def get_cookie( name, default=None ):
        """Gets the value of the cookie with the given name, else default."""

    def get_secure_cookie( name, value=None ):
        """Returns the given signed cookie if it validates, or None."""

    def onfinish():
        """Callback for asyncrhonous finish()."""

    def urlfor( name, *traverse, **matchdict ) :
        """Use request.webapp.urlfor to generate the url."""

    def pathfor( name, *traverse, **matchdict ) :
        """Use request.webapp.pathfor to generate the url."""

    def appurl( appname, name, *traverse, **matchdict ) :
        """Generate url for different web-application identified by
        ``appname``.  Use request.webapp.urlfor to generate the url."""

    def query_plugins( interface, *args, **kwargs ):
        """Query plugins in the request's context. Since every request is
        under the context of an web-application, appname will be used to make
        the actual query. Will be using `IRequest.appname` attribute"""

    def query_plugin( interface, name, *args, **kwargs ):
        """Query plugin in the request's context. Since every request is
        under the context of an web-application, appname will be used to make
        the actual query. Will be using `IRequest.appname` attribute"""


class IController( Interface ):

    methods = Attribute(
        "Request handler can override this attribute to provide a sequence of "
        "HTTP Methods supported by the plugin. "
    )

    def __call__( request ):
        """In the absence of method specific attributes or if the resolver
        cannot find an instance attribute to apply the handler call back, the
        object will simply be called.
        
        ``request``,
            Object instance implementing :class:`IRequest` interface.
        """

    def head( request, c ):
        """Callback method for HEAD request. 
        
        ``request``,
            Object instance implementing :class:`IRequest` interface.
        ``c``,
            Dictionary like context object. Refers to ``request.context`` and
            available inside HTML templates.
        """

    def get( request, c ):
        """Callback method for GET request. 
        
        ``request``,
            Object instance implementing :class:`IRequest` interface.
        ``c``,
            Dictionary like context object. Refers to ``request.context`` and
            available inside HTML templates.
        """

    def post( request, c ):
        """Callback method for POST request. 
        
        ``request``,
            Object instance implementing :class:`IRequest` interface.
        ``c``,
            Dictionary like context object. Refers to ``request.context`` and
            available inside HTML templates.
        """

    def delete( request, c ):
        """Callback method for DELETE request. 
        
        ``request``,
            Object instance implementing :class:`IRequest` interface.
        ``c``,
            Dictionary like context object. Refers to ``request.context`` and
            available inside HTML templates.
        """

    def put( request, c ):
        """Callback method for PUT request. 
        
        ``request``,
            Object instance implementing :class:`IRequest` interface.
        ``c``,
            Dictionary like context object. Refers to ``request.context`` and
            available inside HTML templates.
        """

    def onfinish():
        """Called after the end of a request, after the response has been sent
        to the client. Note that this is not the same as close callback, which
        is called when the connection get closed. In this case the connection
        may or may not remain open. Refer to HTTP/1.1 spec."""


class IResponse( Interface ):
    """Response object to send reponse status, headers and body."""

    cookies = Attribute(
        "A dictionary of Cookie.Morsel objects representing response cookies "
        "to be sent from server."
    )
    request = Attribute(
        "Plugin instance implementing :class:`IRequest` interface."
    )
    context = Attribute(
        "A dictionary like object that will be passed to resource objects and "
        "view callables, and eventually to template code."
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

    def set_cookie( name, value, **kwargs ) :
        """Sets the given cookie name/value with the given options. Key-word
        arguments typically contains,
          domain, expires_days, expires, path
        Additional keyword arguments are set on the Cookie.Morsel directly.

        By calling this method cookies attribute will be updated inplace.

        See http://docs.python.org/library/cookie.html#morsel-objects
        for available attributes.
        """

    def set_secure_cookie( name, value, expires_days=30, **kwargs ):
        """Signs and timestamps a cookie so it cannot be forged.

        You must specify the ``cookie_secret`` setting in your `class`:WebApp
        to use this method. It should be a long, random sequence of bytes
        to be used as the HMAC secret for the signature.

        To read a cookie set with this method, use `get_secure_cookie()`.

        Note that the ``expires_days`` parameter sets the lifetime of the
        cookie in the browser, but is independent of the ``max_age_days``
        parameter to `get_secure_cookie`.
        """

    def clear_cookie( name, path="/", domain=None ):
        """Deletes the cookie with the given name."""

    def clear_all_cookies():
        """Deletes all the cookies the user sent with this request."""

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

    def flush( finishing=False, callback=None ):
        """Flushes the current output buffer to the network. If ``finishing``
        is True, it signifies that the flush is the last chunk to be
        transferred for this chunk. Will be used by output transformers
        implementing :class:`IResponseTransformer` interface.

        The ``callback`` argument, if given, can be used for flow control:
        it will be run when all flushed data has been written to the socket.
        Note that only one flush callback can be outstanding at a time;
        if another flush occurs before the previous flush's callback
        has been run, the previous callback will be discarded.
        """

    def finish():
        """Finishes this HTTP response on the open connection and initiates a
        finish sequence starting from app's onfinish() interface"""

    def onfinish():
        """Callback for asynchronous writes and flushes."""

    def httperror( status_code=500, **kwargs ):
        """Sends the given HTTP error code to the browser.

        If `flush()` has already been called, it is not possible to send
        an error, so this method will simply terminate the response.
        If output has been written but not yet flushed, it will be discarded
        and replaced with the error page.

        It is the caller's responsibility to finish the request, by calling
        finish()."""

    def redirect( url, permanent=False, status=None ):
        """Sends a redirect to the given (optionally relative) URL.

        If the ``status`` argument is specified, that value is used as the
        HTTP status code; otherwise either 301 (permanent) or 302
        (temporary) is chosen based on the ``permanent`` argument.
        The default is 302 (temporary).

        It is the responsibility of the caller to finish the request by
        calling :method:`IResponse.finish`.
        """

    def render( templatefile, request, c ):
        """Render ``templatefile`` under ``context`` to generate response body
        for http ``request``. Picks a plugin implementing :class:`IRenderer`
        to generate the html. 

        It is the responsibility of the caller to finish the request by
        calling :method:`IResponse.finish`.

        The render call writes the response body using
        :method:`IResponse.write`

        ``templatefile``,
            File path for html template in asset-specification format.
        ``request``,
            Plugin instance implementing :class:`IRequest` interface. Same as
            the one passed to :class:`IController` methods.
        ``c``,
            Dictionary like context object. Typically populated by
            :class:`IController` methods and made availabe inside HTML
            templates.
        """

    def set_close_callback( callback ):
        """Set a call back function to be called when remote client close 
        the connection on this request/response or when no-keep-alive is 
        true, hence closing the connection after the response."""

    def on_connection_close():
        """Call back from http-server. Typically, plugin implementing this
        method should in-turn call the callback function registered via
        :method:`set_close_callback`."""


class IResponseTransformer( Interface ):
    """Specification to transform response headers and body. A chain of
    transforms can be configured with plugins implementing 
    :class:`IResponse`."""

    def start_transform( headers, chunk, finished=False ):
        """Start transformation using complete list of response headers and
        first ``chunk`` of response body, if ``finished`` is False. If
        ``finished`` is True, then ``chunk`` becomes the first and last part
        of response body."""

    def transform( self, chunk, finished=False ):
        """Continue with the current transformation with subsequent chunks in
        response body. If ``finished`` is True, then ``chunk is the last chunk
        of response body."""


class IRenderer( Interface ):
    """Attributes and methods to render a page using a supplied context."""

    def render( templatefile, request, c ):
        """Render ``templatefile`` under ``context`` to generate response body
        for http ``request``.

        The render call writes the response body using 
        :method:`IResponse.write`

        ``templatefile``,
            File path for html template in asset-specification format.
        ``request``,
            Plugin instance implementing :class:`IRequest` interface. Same as
            the one passed to :class:`IController` methods.
        ``c``,
            Dictionary like context object. Typically populated by
            :class:`IController` methods and made availabe inside HTML
            templates.
        """


class IErrorPage( Interface ):

    def render( request, status_code, c ):
        """Use ``status_code``, typically an error code, and a collection of
        arguments ``c`` to generate error page for ``request``. This is
        called as a result of :method:`IResponse.httperror` method.

        If this error was caused by an uncaught exception, an ``exc_info``
        triple can be passed as ``c["exc_info"]``. Note that this
        exception may not be the "current" exception for purposes of
        methods like ``sys.exc_info()`` or ``traceback.format_exc``. Note that
        exception rendering happens only when application's `debug` settings is
        `True`.

        The render call writes the response body using 
        :method:`IResponse.write`
        """


