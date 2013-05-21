.. _glossary:

Glossary
========

.. glossary::
  :sorted:

  asset
    Any file contained within a Python :term:`package` which is *not*
    a Python source code file.

  asset specification
    A colon-delimited identifier for an :term:`asset`.  The colon
    separates a Python :term:`package` name from a package subpath.
    For example, the asset specification
    ``mypackage:static/baz.css`` identifies the file named
    ``baz.css`` in the ``static`` subdirectory of the ``mypackage``
    Python :term:`package`.

  plugin name
    Lower case name of the plugin class. For eg, if class by name
    ``HTTPEPollServer`` derives from base :class:`Plugin`, then its
    plugin-name is ``httpepollserver``.

  plugin canonical name
    Lower case name of the plugin class prefixed with package in which the
    class is defiend. For eg, if class ``HTTPEPollServer`` plugin is
    implemented by ``pluggdapps`` package, then the canonical name of the
    plugin is ``pluggdapps.httpepollserver``.

  interface
    An interface specification is a python psuedo-class defining a
    collection of attributes and methods, where methods are mostly used as
    callbacks and attributes are used to preserve context across callbacks.
    Once interfaces are defined, they are implemented by one or more plugin
    classes.

  plugins
    A plugin class can implement one or more interfaces. When a plugin 
    implements an interface, it should define methods and attributes
    specified by that interface. Plugin developers must stick to the
    semantic meaning of the interface(s) implemented by the plugin.
    
  configuration
    Every plugin is a dictionary of configuration settings. Plugin classes
    pre-define configurable parameters by implementing
    :class:`pluggdapps.plugin.ISettings` interface. Pluggdapps platform
    takes care of aggregating and merging configuration from several sources
    like .ini file(s) and database backend.

  package
    Installable python project. Typically distributed as .egg file. A
    package is considered to be part of pluggdapps platform when it
    implements pluggdapps entrypoint. In which case, all interfaces and
    plugins defined in the package will automatically be loaded when
    pluggdapps platform is booted.

  platform
    An environment to develop, distribute and install plugins. Pluggdapps
    platform also takes care of initializing plugins with configuration
    settings.

  environment
    Python run-time and package environment. In normal cases python packages
    are installed in system-wide installation directories like `/usr/lib/`.
    It is also possible to create a virtual environment where packages will
    be installed in user-directories.

  component architecture
    A blue print of interface specification and plugin definitions in an
    environment across several packages. This blue print will be used when
    plugins are queried / instantiated.

  scaffold
    A template of source files / program code that help users get started
    writing a web-application project or a plugin fairly quickly.
    Scaffolds are usually invoked as a sub-command to `pa-script`.

