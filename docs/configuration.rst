Catalog of plugin configuration.
================================
catchanddebug
-------------

xmlhttp_key
    When this key is in the request GET variables (not POST!), expect that
    this is an XMLHttpRequest, and the response will be more minimal; it
    shall not be a complete HTML page.

show_revision
    Show revision information from frame.

html
    Format exception in html and return back an interactive debug page as
    response.

limit
    Maximum number of trace back frames to display in the debug page.

template
    Template file to render the error page. Refer to the plugin to know
    more about the context available to the template.


commandcommands
---------------

description_width
    Maximum width of description column.

command_width
    Maximum width of command name column.


commandconfdoc
--------------

-- configuration is not supported by plugin --

commandenv
----------

target_dir
    Target directory to place the scaffolding logic.

host_name
    Host name for the environment :

template_dir
    Obsolute file path of template source-tree to be used for the
    scaffolding logic.


commandls
---------

-- configuration is not supported by plugin --

commandpviews
-------------

-- configuration is not supported by plugin --

commandserve
------------

reload.poll_interval
    Relevant when the sub-command is invoked with monitor and reload
    switch. Number of seconds to poll for file modifications. When a file
    is modified, server is restarted.

IHTTPServer
    Plugin name implementing :class:`IHTTPServer`. This is the actual web
    server that will be started by the sub-command. Can be modified only
    in the .ini file.

reload.config
    Relevant when the sub-command is invoked with monitor and reload
    switch. Specifies whether the server should be restarted when a
    configuration file (.ini) is changed.


commandunittest
---------------

-- configuration is not supported by plugin --

commandwebapp
-------------

target_dir
    Target directory to place the generated modules and directories. If
    not specified uses the current working directory.

webapp_name
    Name of the web application. Since a web application is also a plugin,
    it must be a unique name.

template_dir
    Obsolute file path of template source-tree to be used for the
    scaffolding logic.


configsqlite3db
---------------

url
    Location of sqlite3 backend file. Will be passed to sqlite3.connect()
    API. Can be modified only in the .ini file.


docroot
-------

IHTTPRouter
    IHTTPRouter plugin. Base router plugin for resolving requests to view-
    callable.

language
    Default language to use in content negotiation. This can be customized
    for each view (or resource-variant)

encoding
    Default character encoding to use on HTTP response. This can be
    customized for each view (or resource-variant)

IHTTPCookie
    Plugin implementing IHTTPCookie interface spec. Methods from this
    plugin will be used to process both request cookies and response
    cookies.

IHTTPOutBound
    A string of comma seperated value, where each value names a
    IHTTPOutBound plugin. Transforms will be applied in specified order.

rootloc
    Root location containing the web-site documents.

favicon
    To use a different file for favorite icon, configure the file path
    here. File path must be relative to ``rootloc``.

IHTTPRequest
    Name of the plugin to encapsulate HTTP request.

IHTTPLiveDebug
    Plugin implementing IHTTPLiveDebug interface spec. Will be used to
    catch application exception and render them on browser. Provides
    browser based debug interface.

index_page
    Specify the index page for the hosted site.

IHTTPResponse
    Name of the plugin to encapsulate HTTP response.

IHTTPSession
    Plugin implementing IHTTPSession interface spec. Will be used to
    handle cookie based user-sessions.

IHTTPInBound
    A string of comma seperated value, where each value names a
    IHTTPInBound plugin. Transforms will be applied in specified order.


docrootrouter
-------------

routemapper
    Route mapper file in asset specification format. A python file
    containing a list of dictionaries, where each dictionary element will
    be converted to add_view() method-call on the router plugin.

IHTTPNegotiator
    If configured, will be used to handle server side http negotiation for
    best matching resource variant.

defaultview
    Default view callable plugin. Will be used when request cannot be
    resolved to a valid view-callable.


docrootview
-----------

max_age
    How long this file can remain fresh in a HTTP cache.


gzipoutbound
------------

level
    Compression level while applying gzip.


httpconnection
--------------

read_chunk_size
    Chunk of data, size in bytes, to read at a time.

connection_timeout
    Timeout in seconds after which an idle connection is gracefully
    closed.

no_keep_alive
    HTTP /1.1, whether to close the connection after every request.

max_buffer_size
    Maximum size of read / write buffer in bytes.


httpcookie
----------

secret
    Use this to sign the cookie value before sending it with the response.

max_age_seconds
    Maximum age, in seconds, for a cookie to live after its creation time.
    The default is 30 days.

value_encoding
    While computing signed cookie value, use this encoding before return
    the value.


httpepollserver
---------------

ssl.cert_reqs
    Whether a certificate is required from the other side of the
    connection, and whether it will be validated if provided. It must be
    one of the three values CERT_NONE (certificates ignored),
    CERT_OPTIONAL (not required, but validated if provided), or
    CERT_REQUIRED (required and validated). If the value of this value is
    not CERT_NONE, then the `ca_certs` parameter must point to a file of
    CA certificates. SSL options can be set only in the .ini file.

IHTTPConnection
    Plugin to handle client connections.

family
    Family may be set to either ``AF_INET`` or ``AF_INET6`` to restrict to
    ipv4 or ipv6 addresses, otherwise both will be used if available.

ssl.certfile
    SSL Certificate file location. SSL options can be set only in the .ini
    file.

ssl.keyfile
    SSL Key file location. SSL options can be set only in the .ini file.

host
    Address may be either an IP address or hostname.  If it's a hostname,
    the server will listen on all IP addresses associated with the name.
    Address may be an empty string or None to listen on all available
    interfaces. Family may be set to either ``socket.AF_INET`` or
    ``socket.AF_INET6`` to restrict to ipv4 or ipv6 addresses, otherwise
    both will be used if available. If left empty `host` parameter from
    [pluggdapps] section will be used.

ssl.ca_certs
    The ca_certs file contains a set of concatenated certification
    authority. certificates, which are used to validate certificates
    passed from the other end of the connection. SSL options can be set
    only in the .ini file.

poll_timeout
    Poll instance will timeout after the specified number of seconds and
    perform callbacks (if any) and start a fresh poll. Will be used by
    HTTPIOLoop definition

scheme
    HTTP Scheme to use, either `http` or `https`. If left empty `scheme`
    parameter from [pluggdapps] section will be used.

port
    Port addres to bind the http server. If left empty `port` paramter
    from [pluggdapps] section will be used.

backlog
    Back log of http request that can be queued at listening port. This
    option is directly passed to socket.listen().

poll_threshold
    A warning limit for number of descriptors being polled by a single
    poll instance. Will be used by HTTPIOLoop plugin.


httpnegotiator
--------------

-- configuration is not supported by plugin --

httprequest
-----------

-- configuration is not supported by plugin --

httpresponse
------------

-- configuration is not supported by plugin --

matchrouter
-----------

routemapper
    Route mapper file in asset specification format. A python file
    containing a list of dictionaries, where each dictionary element will
    be converted to add_view() method-call on the router plugin.

defaultview
    Default view callable plugin. Will be used when request cannot be
    resolved to a valid view-callable.

IHTTPNegotiator
    If configured, will be used to handle server side http negotiation for
    best matching resource variant.


responseheaders
---------------

-- configuration is not supported by plugin --

staticview
----------

max_age
    Response max_age in seconds. How long this file can remain fresh in a
    HTTP cache.


webadmin
--------

IHTTPRouter
    IHTTPRouter plugin. Base router plugin for resolving requests to view-
    callable.

language
    Default language to use in content negotiation. This can be customized
    for each view (or resource-variant)

encoding
    Default character encoding to use on HTTP response. This can be
    customized for each view (or resource-variant)

IHTTPCookie
    Plugin implementing IHTTPCookie interface spec. Methods from this
    plugin will be used to process both request cookies and response
    cookies.

IHTTPOutBound
    A string of comma seperated value, where each value names a
    IHTTPOutBound plugin. Transforms will be applied in specified order.

IHTTPRequest
    Name of the plugin to encapsulate HTTP request.

IHTTPLiveDebug
    Plugin implementing IHTTPLiveDebug interface spec. Will be used to
    catch application exception and render them on browser. Provides
    browser based debug interface.

IHTTPResponse
    Name of the plugin to encapsulate HTTP response.

IHTTPSession
    Plugin implementing IHTTPSession interface spec. Will be used to
    handle cookie based user-sessions.

IHTTPInBound
    A string of comma seperated value, where each value names a
    IHTTPInBound plugin. Transforms will be applied in specified order.


webadminrouter
--------------

routemapper
    Route mapper file in asset specification format. A python file
    containing a list of dictionaries, where each dictionary element will
    be converted to add_view() method-call on the router plugin.

IHTTPNegotiator
    If configured, will be used to handle server side http negotiation for
    best matching resource variant.

defaultview
    Default view callable plugin. Will be used when request cannot be
    resolved to a valid view-callable.


webapp
------

IHTTPRouter
    IHTTPRouter plugin. Base router plugin for resolving requests to view-
    callable.

language
    Default language to use in content negotiation. This can be customized
    for each view (or resource-variant)

encoding
    Default character encoding to use on HTTP response. This can be
    customized for each view (or resource-variant)

IHTTPInBound
    A string of comma seperated value, where each value names a
    IHTTPInBound plugin. Transforms will be applied in specified order.

IHTTPOutBound
    A string of comma seperated value, where each value names a
    IHTTPOutBound plugin. Transforms will be applied in specified order.

IHTTPRequest
    Name of the plugin to encapsulate HTTP request.

IHTTPLiveDebug
    Plugin implementing IHTTPLiveDebug interface spec. Will be used to
    catch application exception and render them on browser. Provides
    browser based debug interface.

IHTTPResponse
    Name of the plugin to encapsulate HTTP response.

IHTTPSession
    Plugin implementing IHTTPSession interface spec. Will be used to
    handle cookie based user-sessions.

IHTTPCookie
    Plugin implementing IHTTPCookie interface spec. Methods from this
    plugin will be used to process both request cookies and response
    cookies.


