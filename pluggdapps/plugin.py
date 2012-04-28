# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

import sys, inspect, logging
from   copy import deepcopy

# TODO :
#   1. How to check for multiple plugins by name defined for same Interface.

__all__ = [ 
    # API functions
    'implements', 'plugin_init', 'plugin_info',
    'query_plugin', 'query_plugins', 'pluginname', 'pluginnames',
    'pluginclass', 'default_settings', 'applications',
    # Classes
    'Interface', 'Attribute'
]

log = logging.getLogger(__name__)

def whichmodule( attr ):
    """Try to fetch the module name in which `attr` is defined."""
    modname = getattr( attr, '__module__' )
    return sys.modules.get( modname, None ) if modname else None


class PluginMeta( type ):
    """Plugin component manager."""

    _pluginmap = {}
    """A map from plugin names (which is name of the class deriving Plugin base
    class) to its information dictionary."""

    _interfmap = {}
    """A map from interface names (which is name of the class deriving 
    Interface base class) to its information dictionary."""

    _implementers = {}
    """A map from interface class object to a map of plugin names and its 
    class. If a plugin sub-class derives from Singleton then query_* methods
    and functions will return the same object all the time."""

    _singletons = {}
    """A map of plugin name and its singleton instance."""

    _applications = []
    """List of application plugin names."""

    # Error messages
    err1 = 'Class `%s` derives both Interface and Plugin'
    err2 = 'Interface %r defined multiple times in %s'

    def __new__( cls, name='', bases=(), d={} ):
        new_class = type.__new__( cls, name, bases, d )

        if name in [ 'Interface', 'PluginBase', 'Singleton' ] :
            return new_class

        PluginMeta._sanitizecls( name, bases, d )

        nm = pluginname(name)
        if Interface in bases :
            # Interface's information dictionary
            PluginMeta._interfmap[name] = \
                    PluginMeta._interf( new_class, name, bases, d )
        elif any([ issubclass(b, PluginBase) for b in bases ]) :
            # Plugin's information dictionary
            PluginMeta._pluginmap[nm] = \
                    PluginMeta._plugin( new_class, nm, bases, d )
            # Register deriving plugin for interfaces implemented by its base
            # classes
            for b in new_class.mro() :
                for (i,pmap) in PluginMeta._implementers.items() :
                    if pluginname(b) in pmap :
                        pmap.setdefault( nm, '-na-' )
            # Hook masterinit() for __init__ call
            init = d.get( '__init__', None )
            if init == None :
                # Because we're replacing the initializer, we need to make sure
                # that any inherited initializers are also called.
                for b in new_class.mro() :
                    if issubclass(b, PluginBase) and '__init__' in b.__dict__ :
                        init = b.__init__._original
                        break

            def masterinit( self, app, *args, **kwargs ) :
                """Component Init function hooked in by ComponentMeta."""
                from  pluggdapps.config import app2sec
                from  pluggdapps.compat import string_types
                
                pluginnm = pluginname(self)
                if isinstance(app, string_types) :
                    appname, app = app, None
                else :
                    appname = pluginname(app)

                if pluginnm in PluginMeta._applications :
                    self.appname, self.app = pluginnm, self
                    self.settings = args[0][pluginnm]
                elif not app :
                    self.appname = appname
                    self.app = query_plugin( appname, IApplication, appname )
                    self.settings = deepcopy( self.app.settings )
                # Plugin settings
                sett = {}
                if pluginnm in PluginMeta._implementers[IApplication] :
                    sett.update( self.settings['DEFAULT'] )
                else :
                    sett.update( self.settings['plugin:'+pluginnm] )
                sett.update( kwargs.pop( 'settings', {} ))
                self._settngx = sett
                # Call the original plugin's __init__
                if init :
                    init( self, *args, **kwargs )

            masterinit._original = init
            new_class.__init__ = masterinit
        return new_class

    @staticmethod
    def _sanitizecls( name, bases, d ):
        """Perform sanitory checks on :class:`Plugin` derived classes."""
        if Interface in bases :
            if PluginBase in bases :
                raise Exception( PluginMeta.err1 % name )
            interf = PluginMeta._interfmap.get( pluginname(name), None )
            if interf :
                raise Exception( PluginMeta.err2 % (name, interf['file']) )

    @staticmethod
    def _interf( cls, name, bases, d ):
        """`cls` is class deriving from Interface baseclass and provides 
        specification for interface `name`."""
        clsmod = whichmodule( cls )
        info = {
            'cls' : cls,
            'name' : name,
            'file' : clsmod.__file__ if clsmod else '',
            'config' : {},      # Configuration dictionary for interface
            'attributes' : {},  # Map of attribute names and Attribute() object
            'methods' : {},     # Map of method names and method object
        }

        """Collect attributes and methods specified by `interface` class."""
        for k in dir(cls) :
            if k.startswith('__') : continue
            v = getattr(cls, k)
            if isinstance(v, Attribute) :
                info['attributes'][k] = v
            elif inspect.ismethod(v) :
                info['methods'][k] = v
        return info

    @staticmethod
    def _plugin( cls, nm, bases, d ):
        """`cls` is class deriving from Plugin baseclass and implements
        interface specifications.
        """
        clsmod = whichmodule( cls )
        info = {
            'cls'    : cls,
            'name'   : nm,
            'file'   : clsmod.__file__ if clsmod else '',
            'config' : {}       # Configuration dictionary for plugin
        }
        return info


class PluginBase( object ):
    """Base class for plugin classes. All plugin-classes are metaclassed by
    PluginMeta."""
    __metaclass__ = PluginMeta

    def __new__( cls, *args, **kwargs ):
        return super( PluginBase, cls ).__new__( cls )


class Singleton( PluginBase ):
    """If a plugin sub-class inherits from this Singleton class, then query_*
    methods / functions for plugins will always return a singleton instance of
    the plugin sub-class."""
    pass


class Interface( object ):
    """Base class for all interface specifications. All interface
    specification classes are metaclassed by PluginMeta.

    Interface is specifying a bunch of attributes and methods that provides 
    an agreement between the implementing plugins and the host that is going 
    to consume the plugin's functionality."""
    __metaclass__ = PluginMeta

    def __new__( cls, *args, **kwargs ):
        return super( Interface, cls ).__new__( cls )
        

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
    if IApplication in interfaces :
        PluginMeta._applications.append( nm )
    for i in interfaces :
        if nm in PluginMeta._implementers.get(i, {}).keys() :
            raise Exception( 
                'Plugin %r implements interface %r twice' % (nm, i) )
        PluginMeta._implementers.setdefault( i, {} ).setdefault( nm, '-na-' )


def plugin_init():
    """It is a chicken egg situation here.
    * The plugin class objects are not availabe until the class is fully
      parsed and loaded.
    * PluginMeta._implementers need to save plugin class object based on
      the plugin class's implements() calls which happens during class
      loading.
    Additionally,
    * It is expected to be called after process global `appsettings`
      dictionary is populated so that configuration values gathered from
      different sources are normalized to python data types.
    """
    # Optimize _implementers for query_*
    d = {}
    for i, pmap in PluginMeta._implementers.items()[:] :
        d[i] = dict([ (nm, PluginMeta._pluginmap[nm]['cls']) for nm in pmap ])
    PluginMeta._implementers = d
    log.info( '%r plugins implementing %r interfaces', 
              len(PluginMeta._pluginmap.keys()),
              len(PluginMeta._interfmap.keys()) )

def plugin_info( *args ):
    """Return information dictionary gathered by :class:`PluginMeta` for 
    a plugin class `nm`, where nm is the first argument in `args`. The second
    argument is optional, and if provided is the default value to be returned
    if a plugin by name `nm` is not found."""
    nm = args[0]
    if isinstance( nm, basestring ) :
        return PluginMeta._pluginmap.get( *args )
    elif issubclass( type(nm), PluginBase ) :
        nm = pluginname( type(nm) )
        return PluginMeta._pluginmap.get( *args )
    else :
        raise Exception( "Could not get plugin information for %r " % nm )


def interface_info( *args ):
    """Return information dictionary gathered by :class:`PluginMeta` for an
    interface class `interf`, where `interf` is the first argument in `args`.
    The second argument is optional, and if provided is the default value to
    be returned if an interface by name `interf` is not found."""
    interf = args[0]
    if isinstance( interf, basestring ):
        return PluginMeta._interfmap.get( *args )
    else :
        interf = interf.__name__
        return PluginMeta._interfmap.get( *args )


def pluginnames( interface ):
    """Return a list of plugin names implementing `interface`."""
    return PluginMeta._implementers[interface].keys()


def pluginclass( interface, name ):
    """Return the plugin class by ``name`` implementing interface."""
    nm = pluginname( name )
    return PluginMeta._implementers.get( interface, {} ).get( nm, None )


def pluginname( o ):
    """Plugin names are nothing but normalized form of plugin's class name,
    where normalization is done by lower casing plugin's class name.
    
    `o` can be one of the following,
      * basestring
      * plugin class
      * plugin class instance
    """
    if isinstance(o, basestring) :
        return o.lower()
    elif inspect.isclass(o) :
        return o.__name__.lower()
    else :
        return o.__class__.__name__.lower()
    return name


def default_settings():
    """Return dictionary default settings for every loaded plugin."""
    psetts = dict([ ( info['name'], info['cls'].default_settings() )
                    for info in PluginMeta._pluginmap.values() ])
    return psetts


def applications():
    """Return a list of application names (which are actually plugins
    implementing :class:`IApplication` interface."""
    from  pluggdapps import ROOTAPP
    return PluginMeta._applications


def plugins():
    """Returns a list of plugin names."""
    return sorted( PluginMeta._pluginmap.keys() )


# Core Interfaces

class IApplication( Interface ):
    """In pluggdapps, an application is a plugin, whereby, a plugin is a bunch
    of configuration parameters implementing one or more interface
    specification."""

    appscript = Attribute(
        "The script name on which the application was mounted. If the "
        "application is mounted on a sub-domain this will be ``None``"
    )
    appdomain = Attribute(
        "The subdomain name on which the application was mounted. If the "
        "application is mounted on a script name this will be ``None``"
    )

    def onboot( settings ):
        """Do necessary activities to boot this applications. Called at
        platform boot-time.

        ``settings``,
            configuration dictionary for this application. Dictionary is a
            collection of sections and its settings. Plugin section names will
            follow the following format, 'plugin:<pluginname>'. There is a
            special section by name 'DEFAULT', whose settings are global to
            all other section settings.
        """

    def start( request ):
        """Once a `request` is resolved for an application, this method is the
        entry point for the request into the resolved application. Typically 
        this method will be implemented by :class:`Application` base class 
        which automatically does url route-mapping and invokes the configured 
        request handler."""

    def router( request ):
        """Return the router plugin implementing :class:`IRouter` 
        interface."""

    def onfinish( request ):
        """A finish is called on the response. And this call back is issued to 
        Start a finish sequence for this ``request`` in the application's 
        context. Plugin's implementing this method must call
        request.onfinish()."""

    def shutdown( settings ):
        """Shutdown this application. Reverse of boot.
        
        ``settings``,
            configuration dictionary for this application. Dictionary is a
            collection of sections and its settings. Plugin section names will
            follow the following format, 'plugin:<pluginname>'. There is a
            special section by name 'DEFAULT', whose settings are global to
            all other section settings.
        """


class ISettings( Interface ):
    """ISettings is a mixin interface implemented by the base class 
    :class:`Plugin`. Since every plugin is nothing but a bunch of configuration
    settings, a default implementation is provided by the base class 
    :class:`Plugin`. Deriving plugin classes can override this interface 
    methods.
    
    While instantiating plugins via `query_plugin()` or `query_plugins()`
    method, passing a ``settings`` key-word argument will override plugin's
    settings defined by ini files and web-admin.
    """
    appname = Attribute(
        "Application name under whose context the plugin was instantiated. "
        "Every plugin is instantiated under an application's context. If no "
        "application is involved (or resolved) then `ROOTAPP` is used as the "
        "plugin's application context."
    )
    app = Attribute(
        "Application instance deriving from :class:`Plugin` implementing "
        ":class:`IApplication` interface. The plugin implementing should be "
        "correspondingly same to that of appname."
    )
    settings = Attribute(
        "Read only copy of application's settings"
    )

    def normalize_settings( settings ):
        """Class method.
        ``settings`` is a dictionary of configuration parameters. This method
        will be called after aggregating all configuration parameters for a
        plugin and before updating the plugin instance with its configuration
        parameters.

        Use this method to do any post processing on plugin's configuration
        parameter and return the final form of configuration parameters.
        Processed parameters in ``settings`` are updated in-pace."""

    def default_settings():
        """Class method.
        Return instance of :class:`ConfigDict` providing meta data
        associated with each configuration parameters supported by the plugin,
        like, default value, value type, help text, whether web configuration
        is allowed, optional values, etc ...
        
        To be implemented by classed deriving :class:`Plugin`.
        """

    def web_admin( settings ):
        """Class method.
        Plugin settings can be configured via web interfaces and stored in
        a backend like database, files etc ... Use this method for the
        following,
        
        * To update the in-memory configuration settings with new `settings`
        * To persist new `settings` in a backend data-store.
       
        Web-admin settings will override settings from ini-files.
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
    """

    implements( ISettings )

    # Dictionary like interface to plugin instances
    def __len__( self ):
        return self._settngx.__len__()

    def __nonzero__( self ):
        return self._settngx.__nonzero__()

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


def query_plugins( appname, interface, *args, **kwargs ):
    """Use this API to query for plugins using the `interface` class it
    implements. Positional and keyword arguments will be used to instantiate
    the plugin object.

    If ``settings`` key-word argument is present, it will be used to override
    default plugin settings.

    Returns a list of plugin instance implementing `interface`
    """
    from pluggdapps import ROOTAPP
    plugins = []
    appname = appname or ROOTAPP
    for pcls in PluginMeta._implementers.get(interface, {}).values() :
        if issubclass(pcls, Singleton) :
            pname = pluginname(pcls) 
            if pname not in PluginMeta._singletons :
                PluginMeta._singletons[pname] = pcls(appname, *args, **kwargs)
            plugins.append( PluginMeta._singletons[pname] )
        else :
            plugins.append( pcls( appname, *args, **kwargs ))
    return plugins


def query_plugin( appname, interface, name, *args, **kwargs ):
    """Same as queryPlugins, but returns a single plugin instance as opposed
    an entire list. Positional and keyword arguments will be used to 
    instantiate the plugin object.

    If ``settings`` key-word argument is present, it will be used to override
    default plugin settings.

    Return a single Plugin instance.
    """
    from pluggdapps import ROOTAPP
    appname = appname or ROOTAPP
    nm = pluginname( name )
    cls = PluginMeta._implementers.get( interface, {} ).get( nm, None )
    if issubclass(cls, Singleton) :
        if nm not in PluginMeta._singletons :
            PluginMeta._singletons[nm] = cls( appname, *args, **kwargs )
        plugin = PluginMeta._singletons[nm]
    else : 
        plugin = cls( appname, *args, **kwargs )
    return plugin


# Unit-test
from pluggdapps.unittest import UnitTestBase

class UnitTest_Plugin( UnitTestBase ):

    def test( self ):
        self.test_whichmodule()

    def test_whichmodule( self ):
        log.info("Testing whichmodule() ...")
        assert whichmodule(UnitTest_Plugin).__name__ == 'pluggdapps.plugin'
        assert whichmodule(self).__name__ == 'pluggdapps.plugin'
        assert whichmodule(whichmodule).__name__ == 'pluggdapps.plugin'
