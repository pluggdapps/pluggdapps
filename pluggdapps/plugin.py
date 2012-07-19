# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 Netscale Computing

"""Makes use of :mod:`pluggdapps.core` and provides a easy interface for rest
of the source code to access plugin architecture."""

import sys, inspect, logging
from   copy import deepcopy

from   pluggdapps.const import ROOTAPP
from   pluggdapps.core  import PluginBase, PluginMeta, Interface, Attribute, \
                               implements, pluginname

log = logging.getLogger( __name__ )

__all__ = [ 
    # Interfaces
    'ISettings', 'IWebApp',
    # Classes
    'Plugin', 'Singleton',
    # API functions
    'isimplement', 'interfaces', 'interface', 'plugin_init', 'plugin_info',
    'interface_info', 'pluginnames', 'pluginclass', 'default_settings',
    'applications', 'plugins', 'query_plugin', 'query_plugins',
]

# Core Interfaces

class ISettings( Interface ):
    """Every plugin is a dictionary of configuration. And its configuration
    settings are implicitly implemented via :class:`Plugin` base class. The
    base class provides default methods for configuration settings which can
    later be overriden by deriving plugins.

    While instantiating plugins via `query_plugin()` or `query_plugins()`
    method, passing a ``settings`` key-word argument will override plugin's
    settings defined by ini files and web-admin.

    All the attributes specified in this interface will be automagically 
    initialised by :class:`PluginMeta`.
    """
    appname = Attribute(
        "Web-Application name under whose context the plugin was instantiated. "
        "Every plugin is instantiated under an application's context. If no "
        "application is involved (or resolved) then `ROOTAPP` is used as the "
        "plugin's application context."
    )
    app = Attribute(
        "Web-Application instance deriving from :class:`Plugin` implementing "
        ":class:`IWebApp` interface. The plugin implementing should be "
        "correspondingly same to that of appname."
    )
    settings = Attribute(
        "Read only copy of application's settings"
    )

    def default_settings():
        """Class method.
        Return instance of :class:`ConfigDict` providing meta data
        associated with each configuration parameters supported by the plugin,
        like, default value, value type, help text, whether web configuration
        is allowed, optional values, etc ...
        
        To be implemented by classes deriving :class:`Plugin`."""

    def normalize_settings( settings ):
        """Class method.
        ``settings`` is a dictionary of configuration parameters. This method
        will be called after aggregating all configuration parameters for a
        plugin and before updating the plugin instance with its configuration
        parameters.

        Override this method to do any post processing on plugin's 
        configuration parameter and return the final form of configuration 
        parameters. Processed parameters in ``settings`` are updated 
        in-pace."""

    def web_admin( settings ):
        """Class method. 
        Plugin settings can be configured via web interfaces and stored in
        a backend like database, files etc ... Use this method for the
        following,
        
        * To update the in-memory configuration settings with new `settings`
        * To persist new `settings` in a backend data-store.
       
        Web-admin settings will override settings from ini-files.

        Important : This feature is still evolving.
        """


class IWebApp( Interface ):
    """In pluggdapps, Web-Application is a plugin, whereby, a plugin is a bunch
    of configuration parameters implementing one or more interface
    specification. Note that application plugins are singletons are the first
    ones to be instantiated along with platform singleton. Attributes,
        `platform`, `script`, `subdomain`
    are initialized by platform initialization code. 

    There is a base class :class:`WebApp` which implements this interface
    and provides necessary support functions for application creators.
    Therefore application plugins must derive from this base class.
    """

    platform = Attribute(
        "Platfrom plugin instance. It is a singleton object accessible to all "
        "plugins via its :attr:`ISettings.app` attribute."
    )
    script = Attribute(
        "The script name on which the application will be mounted. If the "
        "application is mounted on a sub-domain this will be ``None``"
    )
    subdomain = Attribute(
        "The subdomain name on which the application will be mounted. If the "
        "application is mounted on a script name this will be ``None``"
    )
    router = Attribute(
        "Plugin instance implementing :class:`IRouter` interface. This is the "
        "root router using which request urls will be resolved to a view "
        "callable. Should be instantiated during boot time inside "
        ":meth:`onboot` method."
    )

    def onboot():
        """Boot this applications. Called at platform boot-time. 
        
        Instantiate :attr:`router` attribute with root router for the
        application. The root router can be chained further down the line with
        other IRouter plugins, for every path segments, and are collectively 
        responsible for traversing and matching request-urls."""

    def shutdown():
        """Shutdown this application. Reverse of boot."""

    def start( request ):
        """Once a `request` is resolved to an application, this method is the
        entry point for the application. Typically this method will be
        implemented by :class:`Application` base class which will resolve
        url-routing and finally match with a route-mapping to invoke
        :class:`IController` plugin."""

    def onfinish( request ):
        """When a finish is called on the response. And this call back is 
        issued beginning a finish sequence for this ``request`` in the 
        application's context. Plugin's implementing this method must call
        request.onfinish()."""

    def urlfor( appname, request, name, *traverse, **matchdict ):
        """Generate url (full url) identified by routing-name `name`. Use
        `pathfor` method to generate the relative url and join the result
        with the `base_url` for application.
        """

    def pathfor( request, name, *traverse, **matchdict ):
        """Generate relative url for application request using a route
        definition.

        ``appname``,
            name of the application for which the url needs to be generated.
            If supplied as None, url will be generate for _this_ application.

        ``name``,
            Name of the route definition to use. Note that the path will be
            prefixed with *traverse segments before using name and matchdict
            arguments.

        ``request``,
            The :class:`IRequest` object for which url is generated.

        ``traverse``,
            Tuple of :class:`IRouter` plugin-names to prefix the path.

        ``matchdict``,
            A dictionary of variables in url-patterns and their corresponding
            value string. Every route definition will have variable (aka
            dynamic components in path segments) that will be matched with
            url. If matchdict contains the following keys,

            `_remains`, its value, which must be a string, will be appended 
            (suffixed) to the url-path.

            `_query`, its value, which must be a dictionary similar to 
            :attr:`IRequest.getparams`, will be interpreted as query
            parameters and encoded to query string.

            `_anchor`, its value will be attached at the end of the url as
            "#<fragment".
        """


# Plugin base class implementing ISettings
class Plugin( PluginBase ):
    """Every plugin must derive from this class.

    A plugin is a dictionary of configuration settings, that also implements
    one or more interface. Note that class:`Plugin` does not directly derive
    from built in type :type:`dict` because dictionary methods from dict
    type might clash with one or more interface methods implemented by the
    derving plugin class.

    Every other plugin class `must` derive from this class and can override
    the interface specification methods defined by :class:`ISettings`.
    Deriving plugins can assume that plugin's settings will be
    consolidated from web-backend, ini-files and default_settings() method, in
    the order of decreasing priority, and made available as a dictionary of 
    key,value pairs on plugin instance.

    Important Note :
    * All plugin classes must be defined at module top-level.
    * For the plugins to be automatically available for querying, make sure to
      import the module implementing the plugin inside <package>/__init.py
    """
    implements( ISettings )

    # Dictionary like interface to plugin instances
    def __len__( self ):
        return self._settngx.__len__()

    def __getitem__( self, key ):
        return self._settngx[key]

    def __setitem__( self, key, value ):
        return self._settngx.__setitem__( key, value )

    def __delitem__( self, key ):
        return self._settngx.__delitem__( key )

    def __iter__( self ):
        return self._settngx.__iter__()

    def __contains__( self, item ):
        return self._settngx.__contains__( item )

    # :class:`ISettings` interface methods
    @classmethod
    def default_settings( cls ):
        return {}

    @classmethod
    def normalize_settings( cls, settings ):
        return settings

    @classmethod
    def web_admin( cls, settings ):
        return settings


class Singleton( Plugin ):
    """If a plugin sub-class inherits from this Singleton class, then query_*
    methods / functions for plugins will always return a singleton instance of
    the plugin sub-class."""
    pass


def isimplement( plugin, interface ):
    """Is ``interface`` implemented by ``plugin``."""
    return interface in  plugin._interfs


def interfaces():
    """Return a list of interfaces defined in this environment."""
    return [ x['cls'] for x in PluginMeta.interfmap.values() ]


def interface( interf ):
    """Return the interface class specified by string ``interf``."""
    c = PluginMeta.interfmap[interf]['cls'] if isinstance(i, str) else interf
    return c


def plugin_init():
    """It is a chicken egg situation here.
    * The plugin class objects are not availabe until the class is fully
      parsed and loaded.
    * PluginMeta._implementers need to save plugin class object based on
      the plugin class's implements() calls which happens during class
      loading.
    Additionally,
    * Every plugin class object's `_interfs` attribute is populated with a
      list of interfaces implemented by the class.
    """
    # Optimize _implementers and _interfs for query_*
    d = {}
    for i, pmap in PluginMeta._implementers.items() :
        x = {}
        for nm in pmap :
            cls = PluginMeta._pluginmap[nm]['cls']
            x[nm] = cls
            cls._interfs.append(i)
        d[i] = x
    PluginMeta._implementers = d


def plugin_info( *args ):
    """Return information dictionary gathered by :class:`PluginMeta` for 
    a plugin class `nm`, where nm is the first argument in `args`. The second
    argument is optional, and if provided is the default value to be returned
    if a plugin by name `nm` is not found."""
    nm = args[0]
    if isinstance( nm, str ) :
        return PluginMeta._pluginmap.get( *args )
    elif issubclass( type(nm), PluginBase ) :
        nm = pluginname(nm)
        return PluginMeta._pluginmap.get( nm, *args[1:] )
    else :
        raise Exception( "Could not get plugin information for %r " % nm )


def interface_info( *args ):
    """Return information dictionary gathered by :class:`PluginMeta` for an
    interface class `interf`, where `interf` is the first argument in `args`.
    The second argument is optional, and if provided is the default value to
    be returned if an interface by name `interf` is not found."""
    interf = args[0]
    if isinstance( interf, str ):
        return PluginMeta._interfmap.get( *args )
    else :
        interf = interf.__name__
        return PluginMeta._interfmap.get( *args )


def pluginnames( interface ):
    """Return a list of plugin names implementing `interface`."""
    return list( PluginMeta._implementers[interface].keys() )


def pluginclass( interface, name ):
    """Return the plugin class by ``name`` implementing interface."""
    nm = pluginname( name )
    return PluginMeta._implementers.get( interface, {} ).get( nm, None )


def default_settings():
    """Return dictionary default settings for every loaded plugin."""
    return { info['name'] : info['cls'].default_settings()
             for info in PluginMeta._pluginmap.values() }


def applications():
    """Return a list of application names (which are actually plugins
    implementing :class:`IWebApp` interface."""
    return PluginMeta._implementers[IWebApp]


def plugins():
    """Return the complete list of loaded plugin names."""
    return sorted( PluginMeta._pluginmap.keys() )


def query_plugins( appname, interface, *args, **kwargs ):
    """Use this API to query for plugins using the `interface` class it
    implements. Positional and keyword arguments will be used to instantiate
    the plugin object.

    If ``settings`` key-word argument is present, it will be used to override
    default plugin settings.

    Returns a list of plugin instance implementing `interface`
    """
    appname = appname or ROOTAPP
    plugins = [ pcls( appname, *args, **kwargs )
                for pcls in PluginMeta._implementers[interface].values() ]
    return plugins


def query_plugin( appname, interface, name, *args, **kwargs ):
    """Same as queryPlugins, but returns a single plugin instance as opposed
    an entire list. Positional and keyword arguments will be used to 
    instantiate the plugin object.

    If ``settings`` key-word argument is present, it will be used to override
    default plugin settings.

    Return a single Plugin instance.
    """
    appname = appname or ROOTAPP
    nm = pluginname(name)
    cls = PluginMeta._implementers[interface][nm]
    return cls( appname, *args, **kwargs )


