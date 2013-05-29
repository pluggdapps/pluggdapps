**Pluggdapps platform**

A platform is a base system on which we can develop programs, and
package and distribute them to other users who can then install the
programs on machines having the same platform. In case of
pluggdapps, it uses python's standard-library, virtual-environment and
setuptools to create the notion of platform. On-top of that, packages are
expected to define standard entry-points to make them compatible with
pluggdapps. Like,::

  [pluggdapps]
    package=<module.path.to.callable.object>

Inside the package, developers can specify `interfaces` and define
`plugins` implementing one or more interfaces specified in other packages.
Plugins are always instantiated in the context of a platform which can add
more context to the plugin environment.

**Plugin system**

From developer's point of view, pluggdapps' component system is reduced to
two types of objects, :class:`pluggdapps.plugin.Interface` and 
:class:`pluggdapps.plugin.Plugin`. They are
like two sides of the same coin. If part of a program can be customized,
and the customizable portion had to be developed (like wise packaged and 
distributed) independantly from the original program, plugins are the way
to go. In pluggdapps, application authors can abstract the customizable
parts into one or more interfaces. These interfaces specify how the
plugins need to behave when called by the application logic.

Other than the platform objects and the configuration system it provides,
we expect every other logic to go inside one plugin or the other. Thats
right, even a web-application is a plugin. Actually pluggdapps ships with
a platform class :class:`pluggdapps.platform.Webapps` that can host more
than one
web-application inside the same instance of the web-framework.

**Interface specification**

Specifying interfaces are fairly straight forward. It is defined as a
python class deriving from base class called 
:class:`pluggdapps.plugin.Interface`, but other than specifying attributes,
methods and their doc-strings explaining the semantics of the interface,
the developers don't get to do much with interface classes. They are 
automatically meta-classed and blue-printed by the component system.
An example interface class that provide a blue-print for sub-command 
plugins::

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

**Bootstrapping the plugin system**

Plugins are also python classes deriving from a base class called
:class:`pluggdapps.plugin.Plugin`, like 
:class:`pluggdapps.plugin.Interface` classes they are also meta classes 
and blue-printed inside the component architecture. But unlike 
:class:`pluggdapps.plugin.Interface` classes plugin classes can be
instantiated and used like regular python classes, which a minor but
important difference.

Plugins are always instantiated using query_plugin(), query_plugins() or
query_pluginr() APIs. For developers who work on the insides of pluggdapps'
component architecture these APIs are available on the platform classes
like :class:`pluggdapps.platform.Pluggdapps` and
:class:`pluggdapps.platform.Webapps` (Refer :mod:`pluggdapps.platform`).
But for most part developers need not worry about the platform classes,
for them the query_* methods are automatically hitched to every plugin
that are instantiated and have the following signatures.

To query for a plugin by name ``name`` and ``interface`` it implements,::

    plugin.query_plugin( IHTTPResource, 'userpreference', username )

where ``IHTTPResource`` is the interface that we are interested in, and
``userpreference`` is the plugin name that is implementing the interface.
Remaining arguments (like ``username``) and key-word arguments are passed
on to the plugin constructor (the ``__init__`` method).

To query for all plugins implementing ``interfaces``,::

    subcommands = plugin.query_plugins( ICommand )

simlar to query_plugin() except for the difference that all plugins
implementing ``ICommand`` will be instantiated and returned as a list of
sub-command plugins.

There is also a query_pluginr() API, note the ``r`` suffix, that will allow
developers to query plugins by accepting a regular-expression pattern,::

    subcommands = plugin.query_pluginr( ICommand, pattern )

returns a list of plugin instances whose canonical-name matches the supplied
`pattern`.

In essence, developers while authoring their applications, can happily
query for plugins, pass around the instantiated plugins which can be used 
else where to query for more plugins.

Configuration system
--------------------

Another fundamental aspect of software systems is to provide a way to
configure and customize their programs. Pluggdapps provide a wonderful
configuration system. It is the responsibility of platform to gather
configuration settings from various sources (like ini-files, data-base etc..)
and make them available for plugins.

So how are these configuration settings related to a plugin ? Well, a plugin
is nothing but a dictionary like object, whose (key,value) pairs are nothing
but its configuration settings. If the settings for the plugin are changed in
the ini-file or in the data-base, it is automatically made available as a
key,value inside the plugin. For example, 
:class:`pluggdapps.web.server.HTTPEPollServer` plugin has configurable 
parameters like, host, port, backlog etc ... When the settings are configured
in the ini-file like,::

    [plugin:HTTPEPollServer]
    host = mysite.com
    port = 80
    backlog = 10
    ...

these settings are automatically made available inside the plugin 
(refered by ``self``) logic like,::

    ....
    sock.listen( self['backlog'] )
    print( "Server listening host and port" % (self['host'], self['port']) )
    ...

A little bit of inside details. When a plugin class derives from
:class:`pluggdapps.plugin.Plugin`, which is how they become a plugin, it
automatically implements an interface called 
:class:`pluggdapps.plugin.ISettings`. This interface specifies a bunch of 
methods that handles configuration settings for the plugin class.  While the 
platform is booted, the configuration settings are gathered from different 
sources, organised and normalized for plugins' consumption. And when the 
plugins get instantiated (queried by query_*() methods), these settings are 
populated inside the plugin-dictionary.

Web framework
-------------

A frame-work is a software system encouraging a specific set of design pattern
for program development, which can be developed independantly, while still be
able inter-operate with other programs that are being developed using the same
framework. In pluggdapps, frameworks are defined by specifying interfaces
that can inter-operate with each other, and by putting together desired set of 
interfaces we get a complete framework similar to Rails or Django.

Right now we have a web-framework packaged along with pluggdapps, whose
framework interfaces are specified in :mod:`pluggdapps.web.webinterfaces` and
a more fundamental interface specified in 
:class:`pluggdapps.interfaces.IWebApp`. Putting together they define
pluggdapps web-framework. And the framework is implemented by a
collection of plugins under :mod:`pluggdapps.web` directory. Other than 
learning to configure them, developers, for most part, shouldn't worry about 
the supplied interfaces or plugins. Only when there is a need to customize or
replace part of the frame-work definition or its implementation, we expect
them to dig deeper.

Savvy developers can jump to module documentation, built with sphinx, and
learn the nuts and bolts of pluggdapps' web-framework. Others had to wait for 
a more eloborate, easy to read, articles on pluggdapps web-application
development. Just to tickle your interest, we might add that **pluggdapps is
aiming to unify the MVC design pattern and a plugin system - seamlessly.**


Scaffolding
-----------

While working with frameworks, developers are expected to organise and stitch
together their programs in a particular way. Since this is common for all
programs that are developed using the framework it is typical for frameworks
to supply scaffolding logics to get developers started. In pluggdapps,
scaffolding logic is specified by :class:`pluggdapps.interfaces.IScaffold`
interface, and there is a collection of plugins implementing that interface
supplying different types of scaffolding logic. Typically these plugins also
implement :class:`pluggdapps.interfaces.ICommand` interface so that scaffolding 
templates can be invoked directly from pa-script command line.

Can I start using pluggdapps ?
------------------------------

Yes you can ! I have been working on pluggdapps since 2011 and I have created
few applications for myself with it. It has gone through several iteration of
design changes removing more lines of code than there is now. I believe the
design aspects of pluggdapps is almost perfect. But keep in mind that it is
not yet battle tested and might break in corner cases. I would love to fix
them as well, so post me if something goes bad.

