# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

from pluggdapps.plugin import Interface

__all__ = [
    'IHTTPResource', 'IHTTPRouter', 'IHTTPEtag', 'IHTTPCookie', 'IHTTPRequest', 
    'IHTTPResponse', 'IHTTPView', 'IHTTPRenderer',
]

class IHTTPRouter( Interface ):
    """Interface specification for resolving application request to view
    callable.  An `IHTTPRouter` plugin typically compares request's url,
    method and few other header fields with router mapping and resolves view
    callable. The router plugin will be instantiated by the web-application
    during boot time and re-used till the platform is shutdown."""
    
    def onboot():
        """Chained call from :meth:`IWebApp.startapp`. Implementation 
        can chain this onboot() call further down.

        Typically, url route-mapping is constructed here either
        programatically or by parsing a mapper file. By the end of this
        method, require route-mapping must be compiled and cached for
        resolving request's view-callables."""

    def route( request, c ):
        """Resolve ``request`` view-callable. For a successful match,
        populate relevant attributes, like `matchdict` and `view`, in 
        ``request`` plugin.  A view-callable can be a plain python callable
        that accepts request and context arguments or a plugin implementing
        :class:`IHTTPView` interface.

        ``request``,
            Plugin instance implementing :class:`IHTTPRequest` interface.

        ``c``
            Context dictionary for response, and templates.
        """


    def urlpath( request, *args, **kwargs ):
        """Generate path, including query and fragment (aka anchor), for
        `request` using arguments, using ``args`` and ``kwargs``, to learn
        specific signature of positional and key-word arguments refer to
        corresponding router plugin. Returns urlpath string. This does not
        include SCRIPT_NAME, netlocation and scheme.

        ``request``,
            Plugin instance implementing :class:`IHTTPRequest` interface.
        """


class IHTTPResource( Interface ):
    """Interface specification for resource or model plugins."""

    def __call__( request, c ):
        """Resource object to gather necessary data, before a request is
        handled by the view (and templates). Return updated :class:`Context`.
        The context dictionary is also preserved in the :class:`IHTTPResponse`
        plugin for chunked transdfer-encoding.

        ``request``,
            Plugin instance implementing :class:`IHTTPRequest` interface.

        ``c``,
           :class:`Context` dictionary to be passed on to view callables and
           eventually to view-templates.
        """


class IHTTPEtag( Interface ):
    """Interface specification to compute entity-tags for HTTP response
    messages."""

    def compute( response, weak=False ):
        """Compute entity-tag for :class:`IHTTPResponse` object `response`.
        Typically payload data will be used to compute ETAG.
        
        If `weak` True, compute ETAG for two entities of a resource if the
        entities are equivalent and could be substituted for each other with
        no significant change in semantics. Refer RFC1616 for more
        information."""


class IHTTPCookie( Interface ):
    """Handle HTTP cookies. This specification is compatible with IHTTPRequest
    and python's Cookie standard library."""

    def parse_cookies( headers ):
        """Use HTTP `headers` dictionary, to parse cookie name/value pairs, 
        along with its meta-information, into Cookie Morsels, ::
            
            headers.get( 'cookie', '' ) 

        should give the cookie string from `headers`. Return a
        ``SimpleCookie`` object from python's standard-library.
        """

    def set_cookie( cookies, name, morsel, **kwargs ) :
        """Update ``cookies`` dictionary with cookie ``name`` and its
        ``morsel``. Optional Key-word arguments typically contains,
        ``domain``, ``expires_days``, ``expires``, ``path``, which are 
        set on the Cookie.Morsel directly.

        ``cookies``,
            Dictionary like object mapping cookie name and its morsel.
            It is updated inplace and returned back

        ``name``,
            cookie name as string value.

        ``morsel``,
            A string value or http.cookies morsel from python's standard
            library.

        See http://docs.python.org/library/cookie.html#morsel-objects
        for available attributes.
        """

    def create_signed_value( name, value ):
        """Encode `name` and `value` string into byte-string using
        webapp['encoding'] settings, convert value into base64 and return a
        byte-string like,::

          <base64-encoded-value>|<timestamp>|<signature>

        <signature> is generated using `secret`, `name`, base64 encoded 
        ``value`` and timestamp-in-seconds and return as string.
        """

    def decode_signed_value( name, value ):
        """Reverse of `create_signed_value`. Returns orignal value string."""


class IHTTPSession( Interface ):
    """Handle cookie based user-sessions."""


class IHTTPRequest( Interface ):
    """Interface specification for a request object."""

    # ---- Socket Attributes
    httpconn = None
    """:class:`IHTTPConnection` plugin instance."""

    # ---- HTTP Attributes
    method = b''
    """HTTP request method, e.g. b'GET' or b'POST'"""

    uri = b''
    """HTTP Request URI in byte-string as found in request start-line"""

    version = b''
    """HTTP protocol version found in request start-line, e.g. b'HTTP/1.1'"""

    headers = {}
    """Dictionary-like object for HTTP headers. Key name are in string, while 
    values are in byte-string."""

    body = b''
    """Request body, if present, as a byte string."""

    chunks = []
    """List of request chunks. Matching view-callable will be called for every
    request chunk, stored as the last element in this list, that are received.
    It is upto the application logic to clear previous chunks or to preserve
    them, until the request is finished."""

    trailers = {}
    """Similar to `headers` attribute. But received after the last chunk of
    request in chunked transfer-coding."""

    #---- Processed attributes
    uriparts = {}
    """UserDict object of uri parts in decoded, parsed and unquoted form.
    `scheme`, `netloc`, `path`, `query`, `fragment`, `username`, `password`,
    `hostname`, `port`, `script`, keys are available.  Except query, which is
    a dictionary of query arguments, all other values are in string."""

    cookies = {}
    """A dictionary of http.cookies.Morsel objects representing request "
    cookies from client."""

    getparams = {}
    """GET arguments are available in the params property, which maps
    parameter names to lists of values (to support multiple values for
    individual names). Names and values are are of type `str`."""

    postparams = {}
    """POST arguments are available in the params property, which maps
    parameter names to lists of values (to support multiple values for
    individual names). Names and values are of type `str`."""

    multiparts = {}
    """POST arguments in multipart format (like uploaded file content) are 
    available as a dictionary of name,value pairs."""

    params = {}
    """Combined arguments of GET/POST, which maps parameter names to lists of
    values (to support multiple values for individual names). Names and values
    are of type `str`."""

    files = {}
    """File uploads are available in this attribute as a dictionary of name 
    and a list of files submited under name. File is a dictionary of,::

      { 'filename' : ...,
        'value' : ...,
        'content-type' : ... }
    """

    #---- Framework attributes
    session = None
    """If a session factory has been configured, this attribute will represent
    the current user's session object."""

    cookie = None
    """:class:`IHTTPCookie` plugin instance to handle request and response 
    cookies."""

    response = None
    """Response object corresponding to this request. The object is an 
    instance of plugin implementing :class:`IHTTPResponse` interface."""


    #---- Routing attributes
    router = None
    """:class:`IHTTPRouter` plugin resolving this request."""

    matchdict = {}
    """Optinal dictionary attribute that contains maps a variable portion 
    of url with matched value."""

    view = None
    """A view-callable resolved for this request."""

    #---- Others
    receivedat = 0
    """Timestamp when request was recieved"""

    finishedat = 0
    """Timestamp when the request was finished."""

    def __init__( httpconn, method, uriparts, version, headers ):
        """Instance of plugin implementing this interface corresponds to a
        single HTTP request. Note that instantiating this class does not
        essentially mean the entire request is received. Only when
        :method:`IHTTPRequest.handle` is called complete request is available
        and partially parsed.

        ``httpconn``,
            :class:`IHTTPConnection` plugin instance

        ``method``,
            Request method in byte-string.

        ``uriparts``,
            Request URI in byte-string or dictionary of uriparts.

        ``version``,
            Request version in byte-string.

        ``headers``,
            Dictionary request headers. Key names in this dictionary will be
            decoded to string-type. Value names will be preserved as
            byte-string.

        When a request object is instantiated no assumption should be made
        about the web application framework. Only processing of request init
        parameters are allowed."""

    def supports_http_1_1():
        """Returns True if this request supports HTTP/1.1 semantics"""

    def get_ssl_certificate():
        """Returns the client's SSL certificate, if any. To use client 
        certificates, `cert_reqs` configuration value must be set to 
        ssl.CERT_REQUIRED. The return value is a dictionary, see
        SSLSocket.getpeercert() in the standard library for more details.
        http://docs.python.org/library/ssl.html#sslsocket-objects."""

    def get_cookie( name, default=None ):
        """Gets the value of the cookie with the given ``name``, else return 
        ``default``."""

    def get_secure_cookie( name, value=None ):
        """Returns a signed cookie if it validates, or None."""

    def ischunked() :
        """Returns True if this request is received using `chunked`
        Transfer-Encoding.
        """

    def has_finished():
        """Return True if this request is considered finished, which is, when
        the flush( finishing=True ) method is called on :class:`IHTTPResponse`.
        """

    def handle( body=None, chunk=None, trailers=None, ):
        """Once a `request` is instantiated, this method is called before
        resolving and dispatching it to view-callable.
        
        ``body``,
            Optional kwarg, if request body is present. Passed as byte-string.

        ``chunk``,
            Optional kwarg, if request is received in chunks. Chunk received
            as a tuple of, ``(chunk_size, chunk_ext, chunk_data)``.

        ``trailers``,
            Optional kwarg, if chunked-request is over and final trailer is
            being received.
        """

    def onfinish():
        """Callback for asyncrhonous finish(). Means the response is sent and
        the request is forgotten."""

    def urlfor( name, **matchdict ) :
        """Use request.webapp.urlfor() to generate the url."""

    def pathfor( name, **matchdict ) :
        """Use request.webapp.pathfor() to generate the url."""

    def appurl( instkey, name, **matchdict ) :
        """Generate url for a different web-application identified by
        ``instkey``. Typically uses webapp.appurl().
        
        ``instkey``,
            A tuple of ``(appsec, netpath, configini)`` indexes into platform's 
            `webapps` attribute
        """


class IHTTPResponse( Interface ):
    """Interface specification for a response object."""

    #---- HTTP attributes
    statuscode = b''
    """Response status code in byte-string."""

    reason = b''
    """Reason byte-string for response status."""

    version = b''
    """HTTP protocol version, in byte-string, supported by this server."""

    headers = {}
    """HTTP header dictionary to sent in the response message."""

    body = b''
    """Response body, if present, as a byte string."""

    chunk_generator = None
    """A python generate which returns a response chunk for every 
    iteration."""

    trailers = {}
    """In chunked transfer-coding, HTTP header dictionary to be sent after the 
    last chunk is transfered."""

    #---- Processed attributes
    setcookies = {}
    """A dictionary of Cookie.Morsel objects representing a new set of 
    cookies to be set on the client side."""

    #---- Framework attributes
    request = None
    """Plugin instance implementing :class:`IHTTPRequest` interface."""

    etag = None
    """class:`IHTTPEtag` plugin to be used for response Etag computation."""

    context = None
    """A dictionary like object that will be passed to resource objects and 
    view callables, and eventually to template code."""

    def __init__( request ):
        """Instantiate a response plugin for a corresponding ``request``
        plugin.

        ``request``,
            Is an instance object for plugin implementing :class:`IHTTPResponse`
            interface.
        """

    def set_status( code ):
        """Set a response status code. By default it will be 200."""

    def set_header( name, value ):
        """Sets the given response header ``name`` and ``value``. If there is 
        already a response header by `name` present, it will be overwritten.
        Returns the new value for header name as byte-string.

        ``name``,
            byte-string of header field name, in lower case.

        ``value``,
            any type, which can be converted to string.
        """

    def add_header( name, value ):
        """Similar to set_header() except that, if there is already a response
        header by ``name`` present, ``value`` will be appended to existing
        value using ',' seperator. Returns the new value for header name as
        byte-string.

        ``name``,
            byte-string of header field name, in lower case.

        ``value``,
            Any type which can be converted to string.
        """

    def set_trailers( name, value ):
        """Sets the given chunk trailing header, ``name`` and ``value``. If 
        there is already a trailing header by ``name`` present, it will be
        overwritten. Returns the new value for header name as byte-string.

        ``name``,
            byte-string of header field name, in lower case.

        ``value``,
            any type, which can be converted to string.
        """

    def add_trailer( name, value ):
        """Similar to set_trailer() except that, if there is already a
        trailing header by ``name`` present, ``value`` will be appended to
        existing value using ',' seperator. Returns the new value for header
        name as byte-string.

        ``name``,
            byte-string of header field name, in lower case.

        ``value``,
            any type, which can be converted to string.
        """

    def set_cookie( name, value, **kwargs ) :
        """Set cookie `name`/`value` with optional ``kwargs``. Key-word
        arguments typically contains, ``domain``, ``expires_days``,
        ``expires``, ``path``. Additional keyword arguments are set on the
        Cookie.Morsel directly. By calling this method cookies attribute will
        be updated inplace. See
        http://docs.python.org/library/cookie.html#morsel-objects for
        available attributes.
        """

    def set_secure_cookie( name, value, **kwargs ):
        """Similar to set_cookie() method, additionally signs and timestamps a
        cookie value so it cannot be forged.  Uses
        :meth:`IHTTPCookie.create_signed_value` method to sign the cookie. To
        read a cookie set with this method, use `get_secure_cookie()`.
        """

    def clear_cookie( name, path="/", domain=None ):
        """Deletes the cookie with the given name. Note that :attr:`setcookies`
        will still contain cookie-name `name`, only that it is set to expire
        in the client side. Return the original value of the cookie.
        """

    def clear_all_cookies():
        """Deletes all the cookies the user sent with this request."""

    def set_finish_callback( callback ):
        """Subscribe a ``callback`` function, to be called when this response is
        finished."""

    def has_finished():
        """Return True if finish() method is called on :class:`IHTTPResponse`.
        """

    def ischunked() :
        """Returns True if this response is transferred using `chunked`
        Transfer-Encoding.
        """

    def write( data ):
        """Writes the given chunk to the output buffer. To actually write the
        output to the network, use the flush() method below.

        ``data``,
            byte-string of data to buffer for writing to socket. 
        """

    def flush( finishing=False, callback=None ):
        """Flushes the response-header (if not written already) to the socket
        connection. Then flushes the write-buffer to the socket connection.

        ``finishing``,
            If True, signifies that data written since the last flush() on
            this response instance is the last chunk. In non-chunked mode, it
            is signifies that the body is done. It will also flush the
            trailers at the end of the chunked response.

        ``callback``,
            If given, can be used for flow control it will be run when all
            flushed data has been written to the socket.
        """

    def httperror( status_code=500, message=b'' ):
        """Sends the given HTTP error code to the browser.

        If `flush()` has already been called, it is not possible to send
        an error, so this method will simply terminate the response.
        If output has been written but not yet flushed, it will be discarded
        and replaced with the error page.

        It is the caller's responsibility to finish the request, by calling
        finish()."""

    def render( *args, **kwargs ):
        """Use the view configuration parameter 'IHTTPRenderer' to invoke the
        view plugin and apply IHTTPRenderer.render() method with ``request``,
        ``c``, ``args`` and ``kwargs``.
        """

    def chunk_generator( callback, request, c ):
        """Return a generator, which, for every iteration will call the
        ``callback`` function with ``request`` and ``c`` arguments, which are
        preserved till the iteration is over. The call back should return a
        a tuple representing a chunk, ``(chunk_size, chunk_ext, chunk_data)``
        this will formatted into a response chunk and sent across the
        connection.
        """

class IHTTPView( Interface ):

    viewname = ''
    """String name that maps into IHTTPRouter.views dictionary."""

    view = {}
    """Dictionary of view predicates for which this view-callbale was
    resolved."""

    def __init__( viewname, view ):
        """Instantiate plugin with `viewname` and `view` attributes."""

    def __call__( request, c ):
        """In the absence of method specific attributes or if the resolver
        cannot find an instance attribute to apply the handler call back, the
        object will simply be called.
        
        ``request``,
            Plugin instance implementing :class:`IHTTPRequest` interface.

        ``c``,
            Dictionary like context object. Typically populated by
            :class:`IHTTPResource` and view-callable. Made availabe inside 
            HTML templates.
        """

    def onfinish( request ):
        """Optional callable attribute, if present will be called at the end
        of a request, after the response has been sent to the client. Note
        that this is not the same as close callback, which
        is called when the connection get closed. In this case the connection
        may or may not remain open. Refer to HTTP/1.1 spec.
        
        ``request``,
            Plugin instance implementing :class:`IHTTPRequest` interface.
        """


class IHTTPOutBound( Interface ):
    """Specification to transform response headers and body. A chain of
    transforms can be configured with plugins implementing 
    :class:`IHTTPResponse`."""

    def start_transform( headers, chunk, finishing=False ):
        """Start transformation using complete list of response headers and
        first ``chunk`` of response body, if ``finishing`` is False. If
        ``finishing`` is True, then ``chunk`` becomes the first and last part
        of response body."""

    def transform( self, chunk, finishing=False ):
        """Continue with the current transformation with subsequent chunks in
        response body. If ``finishing`` is True, then ``chunk is the last chunk
        of response body."""


class IHTTPRenderer( Interface ): 
    """Attributes and methods to render a page using a supplied context."""

    def render( request, c, *args, **kwargs ):
        """Implementing plugin should interpret `args` and ``kwargs``
        arguments and invoke one or more rendering resource (like templates).
        ``request``,
            Plugin instance implementing :class:`IHTTPRequest` interface. Same
            as the one passed to view-callable.

        ``c``,
            Dictionary like context object. Typically populated by
            :class:`IHTTPResource` and view-callable, made 
            availabe inside HTML templates.
        """
