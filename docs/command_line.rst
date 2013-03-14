Using the ``pa`` script
=======================

Installing pluggdapps will automatically install ``pa`` script under the
`bin/` directory. The script itself is a wrapper around many sub-commands
following :class:`ICommand` interface specification, so it is possible to
extend pa script with any number of sub-commands. To list available
sub-commands,

.. code-block:: bash
    :linenos:

    $ pa commands # Will list available sub-commands with a short description.

Options that are passed before the sub-command are treated as script options 
and those that follow the sub-command are specific to sub-command. To learn 
more about script options,

.. code-block:: bash
    :linenos:

    $ pa --help

To learn about options that are specific to a <sub-command>, 

.. code-block:: bash
    :linenos:

    $ pa <sub-command> --help

Virtual environment
-------------------

We expect pluggdapps to be launched in a virtual environment, whether as a
standalone server or as part of popular web server, like via mod_wsgi in
apache2.

To facilitate the setup of virtual environment we have created a public
repository which can be cloned from,

.. code-block:: bash
    :linenos:

    $ git clone https://github.com/prataprc/paenv.git paenv

Once cloned, execute the following commands to setup the virtual environment.

.. code-block:: bash
    :linenos:

    $ cd paenv
    $ make setup
    $ source pa-env/bin/activate

When the last command is executed your shell will move to the virtual
environment that contains the pa script and rest of pluggdapps package.


List information about pluggdapps environment
---------------------------------------------

``ls`` sub-command can be used to probe the internal state, like summary, 
list of interfaces and plugins available, web-application, installed under
pluggdapps environment. Use the following command to learn available options,

.. code-block:: bash
    :linenos:

    $ pa ls --help

Start built-in web server
-------------------------

Pluggdapps come with a built in web server and like everything else in
pluggdapps, the web-server is also a plugin. This makes the framework more
flexible, in the sense that it is not only possible to use a different
server plugin, it is also possible forgo a server as long as there is a way to
marshal web request into the system and marshal the response back. To launch a
server,

.. code-block:: bash
    :linenos:

    $ pa -w -c etc/master.ini serve

the ``serve`` sub-command by default uses the ``HTTPEPollServer`` plugin as
the web server. The default server executes as a single process without using
multi-threading primitives. But it runs in epoll mode to support a large
number of simultaneous connection. web-server can be configured in the master
ini file under the section,

.. code-block:: ini
    :linenos:

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

Scaffolding
===========

While working with frameworks, developers are expected to organise and stitch
together their programs in a particular way. Since this is common for all
programs that are developed using the framework it is typical for frameworks
to supply scaffolding logics to get developers started.

In pluggdapps, scaffolding logic is specified by 
:class:`pluggdapps.interfaces.IScaffold` interface and the plugin implementing
the scaffolding logic also implements the
:class:`pluggdapps.interfaces.ICommand` interface so that scaffolding
templates can be invoked via pa-script. There couple of plugins pre-packaged
with pluggdapps.

Create a new web-application
----------------------------

Inside a pluggapps package, more than one web-application can be defined.
Typically a web-application must implement a bunch of plugins to handle
:class:`IWebApp` interface methods, to map url patterns to views and resource
plugins to handle database backend if any. To facilitate this repeatitive
activity, pa-script provides a command to create webapp source tree base on
few parameters.

.. code-block:: bash
    :linenos:

    $ pa -c <master.ini> webapp [-t TARGET_DIR] <webapp-name>

to learn more options on this sub-command use ``--help``.


Developing a sub-command plugin
-------------------------------

Sub commands for pa-script are defined by implementing :class:`ICommand`
interface specification. New sub-commands can be defined by any one who knows
how to implement the :class:`ICommand` interface. Also note that these plugins
can be implemented and distributed as separate package. A simple example can
be found in :mod:`pluggdapps.commands.commands` module. The name of the
sub-command plugin's class name must always be prefixed with `Command`. The
rest of the module along with its interface specification is self explanatory.

