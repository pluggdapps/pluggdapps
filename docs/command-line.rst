Using the ``pa`` script
=======================

Installing pluggdapps will automatically install ``pa`` script under the
`bin/` directory. The script itself is a wrapper around many sub-commands
following :class:`ICommand` interface specification, so it is possible to
extend pa script with any number of sub-commands. To list available
sub-commands,

.. code-block:: bash

    pa commands # Will list available sub-commands with a short description.

Options that are passed before the sub-command are treated as script options 
and those that follow the sub-command are specific to sub-command. To learn 
more about script options,

.. code-block:: bash

    pa --help

To learn about options that are specific to a <sub-command>, 

.. code-block:: bash

    pa <sub-command> --help

Starting the built-in web server
--------------------------------

Pluggdapps come with a built in web server and like everything else in
pluggdapps, the web-server is also a plugin. This makes the framework more
flexible, in the sense that it is not only possible to use a different
server plugin, it is also possible forgo a server as long as there is a way to
marshal web request into the system and marshal the response back. To launch a
server,

.. code-block:: bash

    pa -w -c etc/master.ini serve

the ``serve`` sub-command by default uses the ``HTTPEPollServer`` plugin as
the web server. The default server executes as a single process without using
multi-threading primitives. But it runs in epoll mode to support a large
number of simultaneous connection. web-server can be configured in the master
ini file under the section,

.. code-block:: ini

    [plugin:HTTPEPollServer]
    host = localhost
    port = 8080
    ...
    backlog = 200
    poll_threshold = 2000
    ...

Refer to http://<hostname>/webadmin/config for more information on
configuration settings.

Automatic module reloading
--------------------------

In development mode it is possible to configure web-server to monitor for
changing files and restart the system automatically. Make sure to pass the 
following switches while invoking the server,

.. code-block:: bash

    pa-env/bin/pa -w -m -c etc/master.ini serve -r

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
