Using the ``pa`` script
=======================

Installing pluggdapps will automatically install ``pa`` script under the
`bin/` directory. The script itself is a wrapper around many sub-commands,
each sub-command implementing the :class:`ICommand` interface specification.
It is possible to extend pa script with any number of sub-commands and can be
developed as separate packages. In case you want to develop a sub-command
refer one of the sub-command plugin implemented in pluggdapps. To list 
available sub-commands,

.. code-block:: bash

    $ pa commands # Will list available sub-commands with a short description.

Options that are passed before the sub-command are treated as script options 
and those that follow the sub-command are specific to sub-command. To learn 
more about script options,

.. code-block:: bash

    $ pa --help

    usage: pa [-h] [-m] [-c CONFIG] [-w]

    Pluggdapps command line script.

    optional arguments:
      -h, --help  show this help message and exit
      -m          Start monitor process.
      -c CONFIG   Specify config file.
      -w          Load platform with web-framework

To learn about options that are specific to a <sub-command>, 

.. code-block:: bash

    $ pa <sub-command> --help

Virtual environment
-------------------

We expect pluggdapps to be launched in a virtual environment, whether as a
standalone server or as part of popular web server, like via mod_wsgi in
apache2.

To facilitate the setup of virtual environment we have created a public
repository which can be cloned from,

.. code-block:: bash

    $ git clone https://github.com/prataprc/paenv.git paenv

Once cloned, execute the following commands to setup the virtual environment.

.. code-block:: bash

    $ cd paenv
    $ make setup
    $ source pa-env/bin/activate

When the last command is executed your shell will move to the virtual
environment from where you can install pluggdapps package and use this ``pa``
script.


To List information about pluggdapps environment, ``ls`` sub-command can be
used to probe the internal state, like summary, list of interfaces, plugins
available, web-applications installed under pluggdapps environment. Use the
following command to learn available options,

.. code-block:: bash

    $ pa ls --help

Built-in web server
-------------------

Pluggdapps come with a built in web server and like everything else in
pluggdapps, web-server is also a plugin. This makes the framework more
flexible, in the sense that it is not only possible to use a different
server plugin, it is also possible to forego the server as long as there is a
way to marshal web request into the system and marshal the response back. To
launch the server,

.. code-block:: bash

    $ pa -w -c etc/master.ini serve

the ``serve`` sub-command by default uses the ``HTTPEPollServer`` plugin as
the web server. The default server executes as a single process without using
multi-threading primitives. But it runs in epoll mode to support a large
number of simultaneous connection. Web-server can be configured in the 
master-ini file under the section,

.. code-block:: ini
    :linenos:

    [plugin:pluggdapps.HTTPEPollServer]
    host = localhost
    port = 8080
    backlog = 200
    poll_threshold = 2000

If your server is running under `<hostname>` listening on `<port>` refer to its
url `http://<hostname>:<port>/webadmin/config` for more information on 
configuration settings. Learn more about `configuration system <config.html>`_
in pluggdapps.

Automatic module reload
-----------------------

In development mode it is possible to configure web-server to monitor for
changing files and restart the system automatically. Make sure to pass the 
following switches while invoking the server,

.. code-block:: bash

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

Scaffolds
---------

While working with frameworks, developers are expected to organise and stitch
together their programs in a particular way. Since this is common for all
programs that are developed under a framework it is typical for frameworks
to supply scaffolding logic to aid developers.

In pluggdapps, scaffolding logic is specified by 
:class:`pluggdapps.interfaces.IScaffold` interface. Typically plugins
implementing the scaffolding logic will also implement the
:class:`pluggdapps.interfaces.ICommand` interface so that scaffolding
templates can be invoked via pa-script. There are couple of such plugins
pre-packaged with pluggdapps. Refer to 
`api documentation <./modules/scaffolds.html>`_ for more information on
available scaffolds.
