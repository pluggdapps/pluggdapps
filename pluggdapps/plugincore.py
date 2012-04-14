# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

import sys, types

import pluggdapps.util       as h

# TODO :
#   1. How to check for multiple plugins by name defined for same Interface.

__all__ = [ 
    # API functions
    'implements', 'plugin_init', 'plugin_info',
    'query_plugin', 'query_plugins', 'pluginname', 'pluginnames',
    'pluginclass',
    # Classes
    'Interface', 'Attribute'
]

class PluginMeta( type ):
    """Plugin component manager."""

    _pluginmap = {}
    """A map from plugin names (which is name of the class deriving Plugin base
    class) to its information dictionary."""

    _interfmap = {}
    """A map from interface names (which is name of the class deriving Interface
    base class) to its information dictionary."""

    _implementers = {}
    """A map from interface class object to a map of plugin names and its 
    class."""

    # Error messages
    err1 = 'Class `%s` derives both Interface and Plugin'
    err2 = 'Interface %r defined multiple times in %s'

    def __new__( cls, name='', bases=(), d={} ):
        new_class = type.__new__( cls, name, bases, d )

        if name in [ 'Interface', 'PluginBase' ] :
            return new_class

        PluginMeta._sanitizecls( cls, name, bases, d )

        nm = pluginname(name)
        if Interface in bases :
            # Interface's information dictionary
            PluginMeta._interfmap[name] = PluginMeta._interf( new_class, name, bases, d )
        elif any([ issubclass(b, PluginBase) for b in bases ]) :
            # Plugin's information dictionary
            PluginMeta._pluginmap[nm] = PluginMeta._plugin( new_class, nm, bases, d )
            # Register deriving plugin for interfaces implemented by its base
            # classes
            [ pmap.setdefault( nm, '-na-' )
              for b in bases 
              for (i,pmap) in PluginMeta._implementers.items() 
                if pluginname(b) in pmap ]
        return new_class

    @classmethod
    def _sanitizecls( _cls, cls, name, bases, d ):
        """Perform sanitory checks on plugin implementers."""
        if Interface in bases :
            if PluginBase in bases :
                raise Exception( PluginMeta.err1 % name )
            interf = PluginMeta._interfmap.get( pluginname(name), None )
            if interf :
                raise Exception( PluginMeta.err2 % (name, interf['file']) )

    @classmethod
    def _interf( _cls, new_class, name, bases, d ):
        """`new_class` is class deriving from Interface baseclass and provides 
        specification for interface `name`.
        """
        clsmod = h.whichmodule( new_class )
        info = {
            'cls' : new_class,
            'name' : name,
            'file' : clsmod.__file__ if clsmod else '',
            'config' : {},      # Configuration dictionary for interface
            'attributes' : {},  # Map of attribute names and Attribute() object
            'methods' : {},     # Map of method names and method object
        }

        """Collect attributes and methods specified by `interface` class."""
        for k in dir(new_class) :
            if k.startswith('__') : continue
            v = getattr(new_class, k)
            if isinstance(v, Attribute) :
                info['attributes'][k] = v
            elif isinstance(v, types.MethodType) :
                info['methods'][k] = v
        return info

    @classmethod
    def _plugin( _cls, new_class, nm, bases, d ):
        """`new_class` is class deriving from Plugin baseclass and implements
        interface specifications.
        """
        clsmod = h.whichmodule( new_class )
        info = {
            'cls'    : new_class,
            'name'   : nm,
            'file'   : clsmod.__file__ if clsmod else '',
            'config' : {}       # Configuration dictionary for plugin
        }
        return info


class Interface( object ):
    """Base class for interface specifying classes. All interface-classes are
    metaclassed by PluginMeta.

    An interface is a bunch of attributes and methods that provides an
    agreement between the implementing plugins and the host that is going to
    consume the plugin functionality.
    """
    __metaclass__ = PluginMeta

    def __new__( cls, *args, **kwargs ):
        return super( Interface, cls ).__new__( cls )
        

class PluginBase( object ):
    """Base class for plugin classes. All plugin-classes are metaclassed by
    PluginMeta.
    
    A plugin is a dictionary of configuration parameters, that also implements
    one or more interface. Note that class:`Plugin` does not directly derive
    from built in type :type:`dict` because dictionary methods from dict
    type might clash with one or more interface methods implemented by the
    derving plugin class.
    """
    __metaclass__ = PluginMeta

    def __new__( cls, *args, **kwargs ):
        return super( PluginBase, cls ).__new__( cls )


class Attribute( object ):
    """Doc specifier for interface attributes."""
    def __init__( self, docstring ):
        self.docstring = docstring


def implements( *interfaces ):
    """Declare interfaces implemented by class. This function can be called
    only in the context of a class deriving from Plugin class."""
    frame = sys._getframe(1)
    nm = pluginname( frame.f_code.co_name )
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
    from pluggdapps import appsettings
    # Normalize plugin settings
    for appname, setts in appsettings.items()[:] :
        for p, sett in setts :
            info = PluginMeta._pluginmap.get( p, {} )
            cls = info.get('cls', None)
            s = {}
            s.update( cls.default_settings() ) if cls else None
            s.update( sett )
            cls.normalize_settings( s ) if cls else None
            appsettings[appname][p] = s
    # Optimize _implementers for query_*
    d = {}
    for i, pmap in PluginMeta._implementers.items()[:] :
        d[i] = dict([ (nm, PluginMeta._pluginmap[nm]['cls']) for nm in pmap ])
    PluginMeta._implementers = d

def plugin_info( nm ):
    if isinstance( nm, basestring ) :
        return PluginMeta._pluginmap.get( nm, {} )
    elif issubclass(type(nm), PluginBase) :
        nm = pluginname( type(nm) )
        return PluginMeta._pluginmap.get( nm, {} )
    else :
        raise Exception( "Could not get plugin information for %r " % nm )


def pluginnames( interface ):
    """Return a list of plugin names implementing `interface`."""
    return PluginMeta._implementers[interface].keys()

def pluginclass( interface, name ):
    nm = pluginname( name )
    return PluginMeta._implementers.get( interface, {} ).get( nm, None )

def pluginname( o ):
    """Plugin names are nothing but normalized form of plugin's class name,
    where normalization is done by lower casing plugin's class name."""
    if isinstance(o, basestring) :
        return o
    elif issubclass(o, PluginBase) :
        return o.__name__.lower()
    else :
        return o.__class__.__name__.lower()


# Plugin base class

class ISettings( Interface ):
    """ISettings is a mixin interface that can be implemented of any plugin.
    Especially plugins that support configuration. Note that a plugin is a
    bunch of configuration parameters implementing one or more interface
    specification.
    """

    def normalize_settings( settings ):
        """Static interface method.
        `settings` is a dictionary of configuration parameters. This method 
        will be called after aggregating all configuration parameters for a
        plugin and before updating the plugin instance with its configuration
        parameters.

        Use this method to do any post processing on plugin's configuration
        parameter and return the final form of configuration parameters.
        Processed parameters are updated in-pace"""

    def default_settings():
        """Static interface method.
        Return instance of :class:`ConfigDict` providing meta data
        associated with each configuration parameters supported by the plugin.
        Like - default value, value type, help text, wether web configuration
        is allowed, optional values, etc ...
        
        To be implemented by classed deriving :class:`Plugin`.
        """

    def web_admin( settings ):
        """Plugin settings can be configured via web interfaces and stored in
        a backend like database, files etc ... Use this method for the
        following,
        
        * To update the in-memory configuration settings with new `settings`
        * To persist new `settings` in a backend data-store."""


class Plugin( PluginBase ):
    """Every plugin must derive from this class.

    A plugin is a dictionary of configuration parameters, that also implements
    one or more interface. Note that class:`Plugin` does not directly derive
    from built in type :type:`dict` because dictionary methods from dict
    type might clash with one or more interface methods implemented by the
    derving plugin class.
    """

    implements( ISettings )

    # Dictionary like interface to plugin instances
    def __len__( self ):
        return self._settngx.__len__()

    def __nonzero__( self ):
        return self._settngx.__nonzero__()

    def __getitem__( self, key ):
        return self._settngx[item]

    def __setitem__( self, key, value ):
        return self._settngx.__setitem__( key, value )

    def __delitem__( self, key ):
        return self._settngx.__delitem__( key )

    def __iter__( self ):
        return self._settngx.__iter__()

    def __contains__( self, item ):
        return self._settngx.__contains__( item )

    # Plugin constructor and instantiater methods.
    def __init__( self, appname, *args, **kwargs ):
        from  pluggdapps import appsettings
        self.appname = appname
        sett = {}
        sett.update( appsettings[appname][pluginname(self)] )
        sett.update( kwargs.pop( 'settings', {} ))
        self._settngx = sett

    # :class:`ISettings` interface methods
    def normalize_settings( self, settings ):
        return settings

    def default_settings( self ):
        return {}

    def web_admin( self, settings ):
        pass


def query_plugins( appname, interface, *args, **kwargs ):
    """Use this API to query for plugins using the `interface` class it
    implements. Positional and keyword arguments will be used to instantiate
    the plugin object.

    If ``settings`` key-word argument is present, it will be used to override
    default plugin settings.

    Returns a list of plugin instance implementing `interface`
    """
    from pluggdapps import ROOTAPP
    appname = appname or ROOTAPP
    return [ cls( appname, *args, **kwargs )
             for pcls in PluginMeta._implementers.get(interface, {}).values() ]


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
    return cls( appname, *args, **kwargs ) if cls else None


