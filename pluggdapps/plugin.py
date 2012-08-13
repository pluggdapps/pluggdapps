# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 Netscale Computing

"""Core module for pluggdapps plugin framework. It uses metaclassing to
automagically register and load plugins into query-able classes. The basic 
idea is that developers can create plugin by deriving their class from 
:class:`Plugin`. A plugin is expected to implement one or more interfaces 
using the following declaration inside their plugin class' scope.
    implements( ISettings )

The base class :class:`Plugin` itself is a plugin implementing
:class:`ISettings` interface, thus all configuration related functions are
auto-magically added to the plugin.

There is also a :class:`Singleton` base class available for plugin authors to
create singleton plugins. A singleton plugin is created only once for the
entire life time of the python environment, they are instantiated when the 
plugin is queried for the first time. Subsequent queries will fetch the 
singleton instance of the plugin.

Web-applications are plugins as well. Before any plugin can be queried, 
all application plugins must be instantiated and booted (which is done by the
:mod:`platform`). Note that there can be any number of instances for a single
WebApp derived class.

Every other plugins must be instantiated in the context of an web-application.

Another interesting point to be noted is, all plugins are nothing but a bunch
of configuration settings gathered from sources like package-defaults,
ini-files and web-admin backend. Refer :mod:`pluggdapps.config` to learn more.

While instantiating plugins via `query_plugin()` or `query_plugins()` method,
passing a ``settings`` key-word argument will override plugin's settings
defined by ini files and web-admin.

Following data structures are preserved in memory (under the scope of
class:`PluginMeta`),

PluginMeta._interfmap =
    { <name> : <information-dictionary>,
      ...
    }

PluginMeta._pluginmap =
    { <name> : <information-dictionary>,
      ...
    }

PluginMeta._implementers =
    { <interface-class> : { <plugin-name> : <plugin-class> ,
                            ...
                          },
      ...
    }

    plugin-name is lower-cased plugin class name.

Similarly to facilitate meth:`query_plugins`, interfaces implemented by a
plugin class (and all of its base classes) are saved under the plugin class
attribute :attr:`_interfs`,

<plugin-cls>._interfs = [ <interface-class>, ... ]


About plugins
-------------

A plugin is a bunch of configuration. In other words, every plugin is a
dictionary of configuration settings pertaining to that plugin configurable
via `plugin:<pluginname>` section of the ini file. In case of web-application
plugin, it is configurable via `webapp:<appname>` section of ini file.

Added to this,

    `<plugin-inst>.appsettings` will provide the settings value for web-app
instance (and all of its plugins) under which <plugin-inst> is instantiated.
    Similarly, `<plugin-inst>.settings` will provide the global settings
comprising full configuration.

Deriving a plugin from another plugin class
-------------------------------------------

It is also possible to create a plugin by deriving from another plugin class.
Remember that a plugin class is any class that derives from the
:class:`Plugin`. For example,

class YourPlugin( Plugin ):
    def __init__( self, arg2, arg3 ):
        pass

class MyPlugin( YourPlugin ):
    def __init__( self, arg1, arg2, arg3 ):
        self._super_init( __class__, arg2, arg3 )

`YourPlugin` is a plugin class (since it derives from :class:`Plugin`) with
accepts two constructor arguments.

Another class `MyPlugin` wants to extend `YourPlugin`, hence can simply derive
from `YourPlugin` class. And thus automatically becomes a plugin class. Note
that MyPlugin class accepts 3 constructor arguments and to initialize the base
class it uses a special method, _super_init() instead of using the builtin
super(). 

"""

import sys, inspect, io
from   copy             import deepcopy
from   pprint           import pprint

from   pluggdapps.const     import ROOTAPP
from   pluggdapps.config    import app2sec, plugin2sec

# TODO :
#   1. Unit test cases.

__all__ = [ 
    # Plugin Classes
    'Plugin', 'Singleton', 'Interface', 'Attribute', 
    # Interfaces
    'ISettings', 'IWebApp',
    # API functions
    'implements', 
    'isimplement', 'interfaces', 'interface', 'plugin_init', 'plugin_info',
    'interface_info', 'pluginnames', 'pluginclass', 'default_settings',
    'applications', 'plugins', 'query_plugin', 'query_plugins',
    # Helper functions
    'whichmodule', 'pluginname',
]

#---- plugin core access functions.

def isimplement( plugin, interface ):
    """Is ``interface`` implemented by ``plugin``."""
    return interface in  plugin._interfs

def interfaces():
    """Return a list of interfaces defined in this environment."""
    return [ x['cls'] for x in PluginMeta._interfmap.values() ]

def interface( interf ):
    """Return the interface class specified by string ``interf``."""
    if isinstance(interf, str) :
        return PluginMeta._interfmap[interf]['cls'] 
    else :
        return interf

def plugin_info( *args ):
    """Return information dictionary gathered by :class:`PluginMeta` for 
    a plugin class `nm`, where nm is the first argument in `args`. The second
    argument is optional, and if provided is the default value to be returned
    if a plugin by name `nm` is not found."""
    nm = args[0]
    if isinstance( nm, str ) :
        return PluginMeta._pluginmap.get( nm, *args[1:] )
    else :
        nm = pluginname(nm)
        return PluginMeta._pluginmap.get( nm, *args[1:] )
    raise Exception( "Could not get plugin information for %r " % nm )

def interface_info( *args ):
    """Return information dictionary gathered by :class:`PluginMeta` for an
    interface class `interf`, where `interf` is the first argument in `args`.
    The second argument is optional, and if provided is the default value to
    be returned if an interface by name `interf` is not found."""
    interf = args[0]
    if isinstance( interf, str ):
        return PluginMeta._interfmap.get( interf, *args[1:] )
    else :
        interf = interf.__name__
        return PluginMeta._interfmap.get( interf, *args[1:] )

def pluginnames( interface=None ):
    """Return a list of plugin names implementing `interface`. If `interface`
    is None, then return a list of all plugins"""
    if interface :
        return list( PluginMeta._implementers[interface].keys() )
    else :
        return list( PluginMeta._pluginmap.keys() )

def pluginclass( interface, name ):
    """Return the plugin class by ``name`` implementing interface."""
    nm = pluginname( name )
    return PluginMeta._implementers.get( interface, {} ).get( nm, None )

def default_settings():
    """Return dictionary default settings for every loaded plugin."""
    d = {}
    for info in PluginMeta._pluginmap.values() :
        for b in reversed( info['cls'].mro() ) :
            if hasattr(b, 'default_settings') :
                d.setdefault( info['name'], {} 
                            ).update( dict( b.default_settings().items() ))
    return d

def applications():
    """Return a list of application names (which are actually plugins
    implementing :class:`IWebApp` interface."""
    return PluginMeta._implementers[ IWebApp ]

def plugins():
    """Return the complete list of loaded plugin names."""
    return sorted( PluginMeta._pluginmap.keys() )
 
def whichmodule( attr ):
    """Try to fetch the module name in which `attr` is defined."""
    modname = getattr( attr, '__module__' )
    return sys.modules.get( modname, None ) if modname else None

def pluginname( o ):
    """Plugin names are nothing but normalized form of plugin's class name,
    where normalization is done by lower casing plugin's class name.
    
    `o` can be one of the following,
      * string
      * plugin class
      * plugin class instance
    """
    if isinstance(o, str) :
        return o.lower()
    elif inspect.isclass(o) :
        return o.__name__.lower()
    else :
        return o.__class__.__name__.lower()
    return name


#---- Plugin meta framework

core_classes = [ 'Interface', 'PluginBase', 'Singleton' ]

class PluginMeta( type ):
    """Plugin component manager. Tracks interface specifications, plugin
    definitions, plugins implementing interfaces and web-application 
    plugins."""

    _pluginmap = {}
    """A map of plugin name (which is lower-cased name of the plugin class)
    to its information dictionary."""

    _interfmap = {}
    """A map of interface name (which is name of the class deriving from
    Interface base class) to its information dictionary."""

    _implementers = {}
    """A map of interface class object to a map of plugin names and its 
    class. If a plugin sub-class derives from Singleton then query_* methods
    and functions will return the same object all the time."""

    def __new__( cls, name='', bases=(), d={} ):
        new_class = super().__new__( cls, name, bases, d )

        if name in core_classes :
            return new_class

        new_class._interfs = []
        mro_bases = list( new_class.mro() )
        PluginMeta._sanitizecls( name, mro_bases, d )

        if Interface in mro_bases :
            # Interface's information dictionary
            PluginMeta._interfmap[name] = \
                    PluginMeta._interf( new_class, name, bases, d )

        elif PluginBase in mro_bases :
            nm = pluginname(name)
            # Plugin's information dictionary
            PluginMeta._pluginmap[nm] = \
                    PluginMeta._plugin( new_class, nm, bases, d )
            # Register deriving plugin for interfaces implemented by its base
            # classes
            for b in mro_bases :
                for i, pmap in list( PluginMeta._implementers.items() ) :
                    if pluginname(b) in pmap :
                        pmap.setdefault( nm, '-na-' )
            # Hook masterinit() for __init__ call
            init = d.get( '__init__', None )
            if init == None :
                # Because we're replacing the initializer, we need to make sure
                # that any inherited initializers are also called.
                for b in mro_bases :
                    if issubclass(b, PluginBase) and '__init__' in vars(b) :
                        init = b.__init__._original
                        break

            def masterinit( self, webapp, *args, **kwargs ) :
                """Plugin Init function hooked in by PluginMeta.
                Consumes ``webapp`` argument and initialize plugin with
                *args and **kwargs parameters. It also handles the special
                case of instantiating IWebApp plugins."""
                # TODO : Optimize the following imports
                from pluggdapps.platform import settings

                # TODO : make `self.appsettings` into a read only copy

                # Check for instantiated singleton, if so return.
                if hasattr( self, 'settings' ): return

                self._settngx = {}
                pluginnm = pluginname(self)

                if isinstance( webapp, tuple ) :
                    appsec, t, v, configini = webapp
                    self.appsettings = settings[ webapp ]
                    self._settngx.update( self.appsettings[appsec] )
                    self.webapp = None
                elif webapp :
                    self.appsettings = webapp.appsettings
                    self._settngx.update( self.appsettings[plugin2sec(pluginnm)] )
                    self.webapp = webapp
                else :
                    self.appsettings = {}
                    self._settngx.update( 
                            settings.get( plugin2sec(pluginnm), {} ))
                    self.webapp = None
                self.settings = settings

                # Plugin settings
                self._settngx.update( kwargs.pop( 'settings', {} ))

                # Call the original plugin's __init__. Avoid calling the
                # masterinit of the super class.
                if init and hasattr( init, '_original' ) :
                    _original( self, *args, **kwargs )
                elif init :
                    init( self, *args, **kwargs )

            def _super_init( self, cls, *args, **kwargs ):
                """__init__ overloading is controlled by PluginMeta. So for 
                plugin inheritance to call base classes method, instead of 
                using,
                    super().__init__( *args, **kwargs )
                use,
                    self._super_init( *args, **kwargs )

                Other methods that are overloaded as called as is.
                """
                baseinit = getattr( cls.mro()[1], '__init__', None )
                if baseinit and hasattr( baseinit, '_original' ) :
                    baseinit._original( self, *args, **kwargs )
                elif baseinit :
                    baseinit( self, *args, **kwargs )

            masterinit._original = init
            new_class.__init__ = masterinit
            new_class._super_init = _super_init

        else :
            raise Exception(
                "Weird, class derives neither from Interface or PluginBase !!" )

        return new_class

    # Error messages
    err1 = 'Class `%s` derives both Interface and Plugin'
    err2 = 'Interface %r defined multiple times in %s'

    @classmethod
    def _sanitizecls( cls, name, bases, d ):
        """Perform sanitory checks on :class:`Plugin` derived classes."""
        if Interface in bases :
            if PluginBase in bases :
                raise Exception( err1 % name )
            interf = PluginMeta._interfmap.get( pluginname(name), None )
            if interf :
                raise Exception( err2 % (name, interf['file']) )

    @classmethod
    def _interf( cls, newcls, name, bases, d ):
        """`newcls` is class deriving from Interface baseclass and provides 
        specification for interface `name`."""
        clsmod = whichmodule( newcls )
        info = {
            'cls' : newcls,
            'name' : name,
            'file' : clsmod.__file__ if clsmod else '',
            'attributes' : {},  # Map of attribute names and Attribute() object
            'methods' : {},     # Map of method names and method object
        }

        # Collect attributes and methods specified by `interface` class.
        for k in vars(newcls) :
            v = getattr(newcls, k)
            if isinstance(v, Attribute) :
                info['attributes'][k] = v
            elif callable(v) :
                info['methods'][k] = v
        return info

    @classmethod
    def _plugin( cls, newcls, nm, bases, d ):
        """`newcls` is class deriving from Plugin baseclass and implements
        interface specifications.
        """
        clsmod = whichmodule( newcls )
        info = {
            'cls'    : newcls,
            'name'   : nm,
            'file'   : clsmod.__file__ if clsmod else '',
        }
        return info


class PluginBase( object, metaclass=PluginMeta ):
    """Base class for all plugin classes. Plugin-classes are metaclassed by
    PluginMeta via this base class."""

    _singletons = {}
    """A map of plugin name and its singleton instance."""

    def __new__( cls, *args, **kwargs ):
        if issubclass( cls, Singleton ):
            name = pluginname(cls)
            singleton = PluginBase._singletons.get( name, None )
            if singleton == None :
                self = super().__new__( cls, *args, **kwargs )
                singleton = PluginBase._singletons.setdefault( name, self )
            return singleton
        else :
            self = super().__new__( cls, *args, **kwargs )
            return self


#---- Plugin framework

class Interface( object, metaclass=PluginMeta ):
    """Base class for all interface specifications. Interface specification
    classes are metaclassed by PluginMeta.

    An `interface` specify a bunch of attributes and methods that provides 
    an agreement between the implementing plugins and the host that is going 
    to consume the plugin's function."""

    def __new__( cls, *args, **kwargs ):
        return super().__new__( cls, *args, **kwargs )
        

class Attribute( object ):
    """Doc specifier for interface attributes."""
    def __init__( self, docstring ):
        self.docstring = docstring


def implements( *interfaces ):
    """Plugin classes can use this function to declare interfaces that are 
    implemented by them. This function can be called only in the context 
    of a class deriving from :class:`Plugin`."""
    frame = sys._getframe(1)
    nm = pluginname( frame.f_code.co_name )
    for i in interfaces :
        if nm in list( PluginMeta._implementers.get(i, {}).keys() ) :
            raise Exception( 
                'Plugin %r implements interface %r twice' % (nm, i) )
        PluginMeta._implementers.setdefault( i, {} ).setdefault( nm, '-na-' )


#---- Default Interfaces for all plugins

class ISettings( Interface ):
    """Every plugin is a dictionary of configuration. And its configuration
    settings are implicitly implemented via :class:`Plugin` base class, which
    is the base class for all plugins, and provides default methods for 
    configuration settings which can later be overriden by deriving plugins.

    While instantiating plugins via `query_plugin()` or `query_plugins()`
    method, passing a ``settings`` key-word argument will override plugin's
    settings defined by ini files and web-admin.

    All the attributes specified in this interface will automagically be
    initialised by :class:`PluginMeta`.
    """

    webapp = Attribute(
        "Optional web-Application instance deriving from :class:`Plugin`, "
        "implementing :class:`IWebApp` interface."
    )
    appsettings = Attribute(
        "Read only copy of application's settings."
    )
    settings = Attribute(
        "Read only copy of global settings."
    )

    def default_settings():
        """Class method.
        Return instance of :class:`ConfigDict` providing meta data
        associated with each configuration parameters supported by the plugin,
        like, default value, value type, help text, whether web configuration
        is allowed, optional values, etc ...
        
        To be implemented by classes deriving :class:`Plugin`.

        Note that ConfigDict will be used to describe settings that are
        understood by the plugin and publish configuration manuals for users.
        """

    def normalize_settings( settings ):
        """Class method.
        ``settings`` is a dictionary of configuration parameters. This method
        will be called after aggregating all configuration parameters for a
        plugin and before updating the plugin instance with its configuration
        parameters.

        Override this method to do any post processing on plugin's 
        configuration parameter and return the final form of configuration 
        parameters. Processed parameters in ``settings`` are updated 
        in-pace and returned."""

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


class Plugin( PluginBase ):     # Plugin base class implementing ISettings
    """Every plugin must derive from this class.

    A plugin is a dictionary of configuration settings, that also implements
    one or more interface. Note that class:`Plugin` does not directly derive
    from built in type :type:`dict` because dictionary methods from dict
    type might clash with one or more interface methods implemented by the
    derving plugin class. Instead, it provides necessary operator methods, to
    morph plugin instances into settings dictionaries.

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


#---- Special interfaces

class IWebApp( Interface ):
    """In pluggdapps, Web-Application is a plugin, whereby, a plugin is a bunch
    of configuration parameters implementing one or more interface
    specification. Note that application plugins are singletons are the first
    ones to be instantiated along with platform singleton. Attributes,
        `pa`, `script`, `subdomain`
    are initialized by platform initialization code. 

    There is a base class :class:`WebApp` which implements this interface
    and provides necessary support functions for application creators.
    Therefore application plugins must derive from this base class.
    """

    pa = Attribute(
        "Platfrom plugin instance. It is a singleton object accessible to all "
        "plugins via its :attr:`ISettings.webapp` attribute."
    )
    instkey = Attribute(
        "Index into global settings"
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
        Instantiate :attr:`router` attribute."""

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


#---- Query APIs

def query_plugins( webapp, interface, *args, **kwargs ):
    """Use this API to query for plugins using the `interface` class it
    implements. Positional and keyword arguments will be used to instantiate
    the plugin object.

    If ``settings`` key-word argument is present, it will be used to override
    default plugin settings.

    Returns a list of plugin instance implementing `interface`
    """
    plugins = [ pcls( webapp, *args, **kwargs )
                for pcls in PluginMeta._implementers[interface].values() ]
    return plugins


def query_plugin( webapp, interface, name, *args, **kwargs ):
    """Same as queryPlugins, but returns a single plugin instance as opposed
    an entire list. Positional and keyword arguments will be used to 
    instantiate the plugin object.

    If ``settings`` key-word argument is present, it will be used to override
    default plugin settings.

    Return a single Plugin instance.
    """
    nm = pluginname(name)
    cls = PluginMeta._implementers[interface][nm]
    return cls( webapp, *args, **kwargs )


#---- Formated output for internal data-structures.

def format_interfaces() :
    """Return a list of formated 80 column output of interfaces."""
    f = io.StringIO()
    for name, info in PluginMeta._interfmap.items() :
        format_interface( name, info, f )
        f.write("\n")
    return f.getvalue()

def format_interface( name, info, f ):
    print( name, info['file'], file=f )
    print( '  attributes :' )
    pprint( info['attributes'], stream=f, indent=2 )
    print( '  methods :' )
    pprint( info['methods'], stream=f, indent=2 )

def format_plugins() :
    """Return a list of formated 80 column output of plugins."""
    f = io.StringIO()
    for name, info in PluginMeta._pluginmap.items() :
        format_plugin( name, info, f )
        f.write("\n")
    return f.getvalue()

def format_plugin( name, info, f ):
    print( name, info['file'], file=f )

def format_implementers():
    """Return a list of formated 80 column output of plugin implementation
    dictionary."""
    f = io.StringIO()
    for i, pmap in PluginMeta._implementers.items() :
        format_implementer(i, pmap)
        f.write('\n')
    return f.getvalue()

def format_implementer(i, pmap, f):
    print( i.__class__.__name__, file=f )
    pprint( pmap, stream=f, indent=2 )

