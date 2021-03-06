Web server
==========

Pluggdapps come with a built-in web server. Like everything else in
pluggdapps web-server is also a plugin. From developer's point of view, web 
service in pluggdapps is defined by two interfaces,

  * :class:`IHTTPServer` interface specification.
  * :class:`IHTTPConnection` interface specification.

The server provides interfaces to start() and stop() the web server. The scope
of the web server is to bind to a service port and listen for HTTP client
connection. It is also responsibile for closing individual connection.

Connections
-----------

HTTP is a connection oriented protocol. A connection is made when a new client
tries to access the web-server. Every new connection involves several back and 
forth packet exchange between the client and the server. Once established 
client and the server can exchange several request and response on the same
connection, unless otherwise the connecting nodes are using an older version
or the connection nodes specify to close the connection after the current
messasge transfer. Pluggdapps is compliant with HTTP/1.1 version. Connection 
plugins must also handle all read and writes on the connection, including 
``https`` connections.

:class:`HTTPEPollServer` executes in single process, single threaded mode,
that is, every connection is handled in the same thread. On the other hand,
it uses linux-epoll API to support large number of simultaneous connections 
and faster response.

Ways to start the server
------------------------

Use the following command to start the server in production mode.

.. code-block:: bash
    :linenos:

    $ pa -w -c etc/master.ini serve

Normally this is done after entering into the virtual environment, Refer to
`command line <./command_line.rst>_` document for more information.

In development mode it is possible to configure web-server to monitor for
changing files and restart the system automatically. Make sure to pass the 
following switches while invoking the server,

.. code-block:: bash
    :linenos:

    $ pa-env/bin/pa -w -m -c etc/master.ini serve -r

``-m``,
    To start the server in monitor mode where a separate process will be
    forked to run the HTTP server. When file modification is detected, the
    forked process returns with a pre-defined exit status. All python modules,
    master ini files, application ini files and template files will be
    monitored for changes.

``-r``
    The forked process will further launch a thread to periodically check for
    file modifications.

Please note that these two switches are essential to enable automatic restart.
