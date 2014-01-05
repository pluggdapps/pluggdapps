# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

"""Core module for pluggdapps plugin framework. It uses metaclassing to
automagically load and register a blue-print of interfaces and plugins into
query-able classes. Developers can create plugin by deriving their class from
:class:`Plugin`. A plugin is expected to implement, by calling
:meth:`implement()` function, one or more interfaces inside their plugin
class' scope. The base class :class:`Plugin` itself is a plugin implementing
:class:`ISettings` interface, thus all configuration related methods are
automatically added to the plugin. To provide configurable plugins, authors
need to override methods from :class:`ISettings` interface.

There is also a :class:`Singleton` base class available for plugin authors to
create singleton plugins. A singleton plugin is created only once for the
entire life time of the python environment, they are instantiated when the 
plugin is queried for the first time. Subsequent queries will fetch the 
singleton instance of the plugin.

As mentioned else-where all plugins are but a dictionary of configuration
settings gathered from sources like package-defaults, ini-files and
backend-config-store. Platform classes will aggregate these configuration
settings during statup-time and make them available during plugins
instantiation.  Refer :mod:`pluggdapps.platform` to learn more.

Plugins are instantiated by quering with APIs like `query_plugin()` or
`query_plugins()`. These APIs are automatically avilable on every instantiated
plugin and platform objects from :class:`Pluggdapps`.


Plugin inheritance
------------------

It is also possible to create a plugin by deriving from another plugin class.
Remember that a plugin class is any class that derives from the
:class:`Plugin`. For example,

.. code-block:: python
    :linenos:

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
class it uses a special method, ``_super_init()`` instead of using the builtin
`super()`.
"""

import sys, inspect
from   os.path      import isfile, abspath

import pluggdapps.utils as h

# TODO :
#   1. Unit test cases.

__all__ = [ 
    # Plugin System
    'Plugin', 'Singleton', 'Interface', 'Attribute', 'implements', 
    # Interfaces
    'ISettings',
    # API functions
    'isimplement',  'isplugin', 'interfaces', 'interface', 'plugin_info',
    'interface_info', 'pluginnames', 'canonical_name', 'pluginclass',
    'webapps', 'whichmodule', 'plugin_init',
]

#---- Plugin meta framework

core_classes = [ 'Interface', 'PluginBase', 'Plugin', 'Singleton' ]

class PluginMeta( type ):
    """Plugin component manager. Tracks interface specifications, plugin
    definitions and plugins implementing interfaces. All interfaces and
    plugins defined across pluggdapps are blueprinted and handles
    instantiation of plugins via one of the query_*() methods.
    Also responsibile for making plugin's configuration settings available as
    a dictionary of settings."""

    _pluginmap = {}
    """A map of plugin's canonical-name to its information dictionary."""

    _interfmap = {}
    """A map of interface's canonical-name to its information dictionary."""

    _implementers = {}
    """A map of interface class object to a map of plugin names and its 
    class implementing the interface. Plugin-names are in canonical format.
    If a plugin sub-class derives from Singleton then query_* methods and
    functions will return the same object all the time."""

    # Error messages
    err1 = 'Class `%s` derives both Interface and Plugin'
    err2 = 'Plugin/Interface %r defined multiple times, previously %r'

    def __new__( cls, name='', bases=(), d={} ):
        new_class = super().__new__( cls, name, bases, d )
        new_class.caname = caname = canonical_name(new_class)
        new_class._interfs = []

        if name in core_classes :
            return new_class

        mro_bases = list( new_class.mro() )

        if Interface in mro_bases and PluginBase in mro_bases :
            raise Exception( PluginMeta.err1 % name )
        x = PluginMeta._interfmap.get( 
                caname, PluginMeta._pluginmap.get( caname, None ))
        if x :
            raise Exception( PluginMeta.err2 % (caname, x['file']) )

        if Interface in mro_bases : # For Interface sub-classes
            PluginMeta._interfmap[caname] = \
                    PluginMeta._interf( new_class, name, bases, d )

        elif PluginBase in mro_bases : # For Plugin sub-classes
            PluginMeta._pluginmap[caname] = \
                    PluginMeta._plugin( new_class, name, bases, d )
            # Register deriving plugin for interfaces implemented by its base
            # classes
            for b in mro_bases[:-1] :   # Skip <class 'object'>
                for i, pmap in list( PluginMeta._implementers.items() ) :
                    if b.caname in pmap :
                        pmap.setdefault( caname, '-na-' )

            # Hook masterinit() as __init__
            init = d.get( '__init__', None )
            if init == None :
                # Because we're replacing the initializer, we need to make
                # sure that any inherited initializers are also called.
                for b in mro_bases :
                    if issubclass(b, PluginBase) and '__init__' in vars(b) :
                        init = b.__init__._original
                        break

            def masterinit( self, pa, *args, **kwargs ) :
                """Plugin Init function hooked in by PluginMeta.
                Initialize plugin with *args and **kwargs parameters."""
                # Check for instantiated singleton, if so return.
                if hasattr( self, 'settings' ): return

                self._settngx = {}

                (args, kwargs) = pa.masterinit( self, *args, **kwargs )

                # Call the original plugin's __init__. Avoid calling the
                # masterinit of the super class.
                if init and hasattr( init, '_original' ) :
                    _original( self, *args, **kwargs )
                elif init :
                    init( self, *args, **kwargs )

            def super_init( self, cls, *args, **kwargs ):
                """__init__ overloading is controlled by PluginMeta. So for 
                plugin inheritance to call base classes method, instead of 
                using,
                    super().__init__( *args, **kwargs )
                use,
                    self.__super_init__( __class__, *args, **kwargs )

                Other overloaded methods that are called as is.
                """
                baseinit = getattr( cls.mro()[1], '__init__', None )
                if baseinit and hasattr( baseinit, '_original' ) :
                    baseinit._original( self, *args, **kwargs )
                elif baseinit :
                    baseinit( self, *args, **kwargs )

            masterinit._original = init
            new_class.__init__ = masterinit
            new_class.__super_init__ = super_init

        else :
            raise Exception(
              "Weird, class derives neither from Interface or PluginBase !!" )

        return new_class

    @classmethod
    def _interf( cls, new_class, name, bases, d ):
        """`new_class` is class deriving from Interface baseclass and provides 
        specification for interface `name`."""
        clsmod = whichmodule( new_class )
        info = {
            'cls'       : new_class,
            'name'      : name,
            'caname'    : new_class.caname,
            'file'      : clsmod.__file__ if clsmod else '',
            'assetspec' : '',
            'attributes': {},   # Map of attribute names and its value
            'methods'   : {},   # Map of method names and method object
        }

        # Collect attributes and methods specified by `interface` class.
        for k in vars(new_class) :
            v = getattr(new_class, k)
            if callable(v) :
                info['methods'][k] = v
            else :
                info['attributes'][k] = v
        return info

    @classmethod
    def _plugin( cls, new_class, name, bases, d ):
        """`new_class` is class deriving from Plugin baseclass and implements
        interface specifications.
        """
        clsmod = whichmodule( new_class )
        info = {
            'cls'       : new_class,
            'name'      : name,
            'caname'    : new_class.caname,
            'file'      : clsmod.__file__ if clsmod else '',
            'assetspec' : '',
        }
        return info


#---- plugin core access functions.

def isimplement( plugin, interface ):
    """Check whether ``plugin`` implements the interface ``interface``."""
    return interface in  plugin._interfs

def isplugin( plugin ):
    """Return True if ``plugin`` is a plugin-object."""
    caname = plugin if isinstance(plugin, str) else plugin.caname
    return caname in PluginMeta._pluginmap

def interfaces():
    """Return a complete list of interface classes defined in this
    environment."""
    return [ x['cls'] for x in PluginMeta._interfmap.values() ]

def interface( interf ):
    """Return the interface class specified by name ``interf``."""
    if isinstance(interf, str) :
        return PluginMeta._interfmap[interf]['cls'] 
    else :
        return interf

def plugin_info( *args ):
    """Return information dictionary gathered by :class:`PluginMeta` for 
    a plugin class `nm`, where nm is the first argument in `args`. The second
    argument is optional, and if provided is the default value to be returned
    if a plugin by name `nm` is not found."""
    caname = args[0] if isinstance(args[0], str) else args[0].caname
    return PluginMeta._pluginmap.get( caname, *args[1:] )

def interface_info( *args ):
    """Return information dictionary gathered by :class:`PluginMeta` for an
    interface class `interf`, where `interf` is the first argument in `args`.
    The second argument is optional, and if provided is the default value to
    be returned if an interface by name `interf` is not found."""
    caname = args[0] if isinstance(args[0], str) else args[0].caname
    return PluginMeta._interfmap.get( caname, *args[1:] )

def pluginnames( interface=None ):
    """Return a list of plugin names implementing ``interface``. If
    `interface` is None, then return a list of all plugins"""
    if interface :
        return list( PluginMeta._implementers[interface].keys() )
    else :
        return list( PluginMeta._pluginmap.keys() )

def canonical_name( cls ):
    """Canonical names for plugins are defined as,

    .. code-block::

        <pkgname>.<plugin-class-name>

    where the entire string is lower-cased. This function is to be called only
    by PluginMeta class when a plugin class is about to be blue-printed.
    """
    # TODO : This is a hack specific to tayra template file. Make it generic.
    mod = sys.modules.get( cls.__module__ )
    f = getattr( mod, '_ttlfile', getattr(mod, '__file__', None) )
    if f and isfile(f) :
        return (h.packagedin( abspath(f) )  + '.' + cls.__name__).lower()
    else :
        return cls.__name__.lower()

def pluginclass( interface, name ):
    """Return the plugin class by ``name`` implementing ``interface``."""
    return PluginMeta._implementers.get( interface, {} ).get( name, None )

def webapps():
    """Return a list of application names (which are actually plugins
    implementing :class:`IWebApp` interface."""
    from pluggdapps.interfaces import IWebApp
    return list( PluginMeta._implementers.get( IWebApp, {} ).keys() )

def whichmodule( attr ):
    """Try to fetch the module name in which ``attr`` is defined."""
    modname = getattr( attr, '__module__' )
    return sys.modules.get( modname, None ) if modname else None


class PluginBase( object, metaclass=PluginMeta ):
    """Base class for all plugin classes. Plugin-classes are metaclassed by
    PluginMeta via this base class."""

    _singletons = {}
    """A map of plugin name and its singleton instance."""

    def __new__( cls, *args, **kwargs ):
        if issubclass( cls, Singleton ):
            caname = getattr(cls, 'caname', None)
            singleton = PluginBase._singletons.get( caname, None )
            if singleton == None :
                if isinstance(cls, object) :
                    self = super().__new__( cls )
                else :
                    self = super().__new__( cls, *args, **kwargs )
                singleton = PluginBase._singletons.setdefault(self.caname, self)
            return singleton
        else :
            if isinstance(cls, object) :
                self = super().__new__( cls )
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
    """Doc specifier for interface attributes.
    
    IMPORTANT : Deprecated !!! 
    """
    def __init__( self, docstring ):
        self.docstring = docstring


def implements( *interfaces ):
    """Plugin classes can use this function to declare ``interfaces`` that
    are implemented by them. This function can be called only inside the scope
    of a class deriving from :class:`Plugin`."""
    frame = sys._getframe(1)

    if frame.f_code.co_name in core_classes : return # Skip

    # TODO : This is a hack specific to tayra template file. Make it generic.
    filen = frame.f_globals.get('_ttlfile', None)
    pkg = h.packagedin( abspath(filen) if filen else frame.f_code.co_filename )
    nm = (pkg + '.' + frame.f_code.co_name).lower()
    for i in interfaces :
        if isinstance(i, str) :
            i = PluginMeta._interfmap[i]['cls']
        if nm in list( PluginMeta._implementers.get(i, {}).keys() ) :
            raise Exception( 
                'Plugin %r implements interface %r twice' % (nm, i) )
        PluginMeta._implementers.setdefault( i, {} ).setdefault( nm, '-na-' )


#---- Interfaces

class ISettings( Interface ):
    """Every plugin is a dictionary of configuration. And its configuration
    settings are implicitly implemented via :class:`Plugin` base class, which
    is the base class for all plugins, and provides default methods for 
    configuration settings which can later be overriden by deriving plugins.

    While instantiating plugins via `query_plugin()`, `query_plugins()`,
    `query_pluginr()` methods, passing a ``settings`` key-word argument will
    override plugin's settings defined by ini files and backend-store.

    All the attributes specified in this interface will automagically be
    initialised by :class:`PluginMeta`.
    """

    pa = None
    """Platfrom instance, of :class:`Pluggdapps` or one of its derivatives."""

    caname = None
    """Canonical name of plugin. For example, canonical name for 
    plugin class `ConfigSqlite3DB` defined under `pluggdapps` package will be,
    `pluggdapps.ConfigSqlite3DB`."""

    _settngx = {}
    """Hidden dictionary of configuration settings. Settings information is
    gathered from different sources and initialized during plugin
    instantiation. Every plugin provide a dictionary-like interface to access
    the settings.
    
    IMPORTANT : Do not access this attribute directly.
    """

    @classmethod
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

    @classmethod
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

    @classmethod
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
    from built in type `dict` because dictionary methods from dict
    type might clash with one or more interface methods implemented by the
    derving plugin class. Instead, it provides necessary operator methods, to
    access plugin instances as a dictionary of settings.

    Every other plugin class `must` derive from this class and can override
    the interface specification methods defined by :class:`ISettings`.
    Deriving plugins can assume that plugin's settings will be
    consolidated from web-backend, ini-files and default_settings() method, in
    the order of decreasing priority, and made available as a dictionary of 
    key,value pairs on plugin instance.

    **Important Note**

    * All plugin classes must be defined at module top-level.
    * For the plugins to be automatically available for querying, make sure to
      import the module implementing the plugin inside <package>/__init__.py

    Similarly to facilitate meth:`query_plugins`, interfaces implemented by a
    plugin class (and all of its base classes) are saved under the plugin
    class attribute :attr:`_interfs`,

    <plugin-cls>._interfs = [ <interface-class>, ... ]

    A list of methods supplied to access plugin instance like a dictionary,

    * __len__, a count of configurable parameters.
    * __getitem__, access settings like ``self['item']``.
    * __setitem__, update settings like ``self['item'] = value``.
    * __delitem__, delete settings like ``del self['item']``.
    * __iter__, iterate on settings like ``[ ... for item in self ]``.
    * __contains__, membership check like ``item in self``
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
        return h.ConfigDict()

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

def plugin_init():
    """It is a chicken egg situation in pluggdapp's component system.

    * The plugin class objects are not available until the classes are fully
      parsed and loaded.
    * PluginMeta._implementers need to save plugin class object based on
      the plugin class's implements() calls which happens during class
      loading.

    Additionally,

    * Every plugin class object's `_interfs` attribute is populated with a
      list of interfaces implemented by the class.

    Hence the automagic of plugin system is supplemented by a call to this
    function, once during startup, after all pluggdapps packages are loaded.
    """
    from pluggdapps import papackages

    # Re-initialize _interfs list for each plugin class, so that plugin_init()
    # will not create duplicate entries.
    [ setattr(info['cls'], '_interfs', []) 
            for _, info in PluginMeta._pluginmap.items() ]

    # Optimize _implementers and _interfs for query_*
    d = {}
    for i, pmap in PluginMeta._implementers.items() :
        x = {}
        for nm in pmap :
            cls = PluginMeta._pluginmap[nm]['cls']
            x[nm] = cls
            cls._interfs.append(i)
        d[i] = x
    # All plugins, because they derive from :class:`Plugin`, implement
    # ISettings interface.
    d[ ISettings ] = { nm : info['cls'] 
                       for nm, info in PluginMeta._pluginmap.items() }
    PluginMeta._implementers = d

    # Compute asset-specification for all interfaces and plugins
    for nm, info in PluginMeta._interfmap.items() :
        assetspec = h.asset_spec_from_abspath( info['file'], papackages )
        if assetspec :
            info['assetspec'] = assetspec
        
    for nm, info in PluginMeta._pluginmap.items() :
        assetspec = h.asset_spec_from_abspath( info['file'], papackages )
        if assetspec :
            info['assetspec'] = assetspec
