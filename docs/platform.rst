Platform
========

Pluggdapps is a component system in python. It provides a platform to
specify interfaces and define plugins that can implement one or more of those
interfaces. 

Pluggdapps platform
-------------------

A platform is a base system on which we can develop programs, package and 
distribute them to other users who can then install the programs on machines
having the same platform. In case of pluggdapps, it uses python's
standard-library, virtual-environment and setuptools to create the notion of
platform. On-top of that, packages are expected to define standard entry-points
to make them compatible with pluggdapps. Like,

.. code-block:: ini
    :linenos:

    [pluggdapps]
    package=<module.path.to.callable.object>

Inside the package, developers can specify `interfaces` and define
`plugins` implementing one or more interfaces specified in other packages.
Plugins are always instantiated in the context of a platform which can add
more context to the plugin environment.

Plugin system
-------------

From developer's point of view, pluggdapps' component system is reduced to
two types of objects, :class:`pluggdapps.plugin.Interface` and 
:class:`pluggdapps.plugin.Plugin`. They are like two sides of the same coin.
If part of a program can be customized, and the customizable portion had to
be developed (like wise packaged and distributed) independantly from the 
original application, plugins are the way to go. In pluggdapps, application 
authors can abstract the customizable parts into one or more interfaces. These
interfaces specify how the plugins need to behave when called by the 
application logic.

Other than the platform objects and the configuration system it provides,
we expect every other logic to go inside one plugin or the other. Even a 
web-application is a plugin. Actually pluggdapps ships with a platform class 
:class:`pluggdapps.platform.Webapps` that can host more than one 
web-application inside the same instance of the web-framework.

Interface specification
-----------------------

Specifying interfaces are fairly straight forward. It is defined as a
python class deriving from base class called 
:class:`pluggdapps.plugin.Interface`, but other than specifying attributes,
methods and their doc-strings explaining the semantics of the interface,
developers don't get to do much with interface classes. They are 
automatically meta-classed and blue-printed by the component system.
An example interface class that provide a blue-print for sub-command 
plugins

.. code-block:: python
    :linenos:

    class ICommand( Interface ):
        """Handle sub-commands issued from command line script. The general
        purpose is to parse the command line string arguments into `options`
        and `arguments` and handle sub-commands as pluggable functions."""

        description = ''
        """Text to display before the argument help."""

        usage = ''
        """String describing the program usage"""

        cmd = ''
        """Name of the command"""

        def subparser( parser, subparsers ):
            """Use ``subparsers`` to create a sub-command parser. The
            `subparsers` object would have been created using ArgumentParser
            object ``parser``.
            """

        def handle( args ):
            """While :meth:`subparser` is invoked, the sub-command plugin
            can use set_default() method on subparser to set `handler`
            attribute to this method. So that this handler will
            automatically be invoked if the sub-command is used on the 
            command line.

            ``args``,
                parsed args from ArgumentParser's parse_args() method.
            """

Bootstrapping the plugin system
-------------------------------

Plugins are also python classes deriving from a base class called
:class:`pluggdapps.plugin.Plugin`, like :class:`pluggdapps.plugin.Interface` 
classes they are also meta classes and blue-printed by the component 
system. But unlike the `Interface` classes plugin classes can be 
instantiated and used like regular python classes, which a minor but important 
difference explained next.

Plugins are always instantiated using query_plugin() or query_plugins()
(plural form) APIs. For developers who work on the insides of pluggdapps'
component architecture these APIs are available on the platform classes,
:class:`pluggdapps.platform.Pluggdapps` and 
:class:`pluggdapps.platform.Webapps` (Refer :mod:`pluggdapps.platform`).
But for most part developers need not worry about the platform classes,
for them the query_* methods are automatically hitched to every plugin
that are instantiated and have the following signatures.

To query for a plugin by name ``name`` and ``interface`` it implements,

.. code-block:: python

    plugin.query_plugin( IHTTPResource, 'datapkg.userpreference', username )

where ``IHTTPResource`` is the interface that we are interested in, and
``datapkg.userpreference`` is :term:`plugin canonical name`, that is
implementing the interface.  Remaining arguments (like ``username``) and
key-word arguments are passed on to the plugin constructor (the ``__init__``
method). The method will return a single plugin object instantiated from
``UserPreference`` plugin class.

To query for all plugins implementing ``interfaces``,

.. code-block:: python

    subcommands = plugin.query_plugins( ICommand )

simlar to query_plugin() except for the difference that all plugins
implementing ``ICommand`` will be instantiated and returned as a list of
sub-command plugins.

In essence, developers while authoring their applications, can happily
query for plugins, pass around the instantiated plugins which can be used 
else where to query for more plugins.

